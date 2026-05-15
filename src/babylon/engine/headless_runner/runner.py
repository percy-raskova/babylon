"""Core headless simulation runner — orchestrates Postgres + tick loop + artifacts.

Spec: 064-headless-sim-runner (T028-T035).

The runner is intentionally thin: it composes pre-existing pieces from
``babylon.persistence`` (PostgresRuntime, ``initialize_session``,
``persist_tick_atomic``) and emits the contracted artifact bundle. The
simulation math itself is whatever the configured engine step performs
on the persisted state — this MVP carries hex state forward unchanged
so the pipeline (hex hydration → tick loop → trace view → CSV) ships as
a single executable e2e contract. Future specs can plug richer
per-tick advancement in via the ``step_function`` seam (currently
private; exposed when needed).

Exit code semantics live in ``contracts/cli_contract.yaml``. Stderr
formatting on non-zero exits follows the
``ERROR <NAME>: <message> | partial_artifacts=<path-or-NONE>`` template.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import logging
import os
import shutil
import signal
import statistics
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - tqdm is a hard dep
    tqdm = None  # type: ignore[assignment,misc]

from babylon.engine.headless_runner.argparse_cli import build_parser
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.engine.headless_runner.event_capture import EventCapture
from babylon.engine.headless_runner.manifest import build_manifest
from babylon.engine.headless_runner.models import (
    AuditEntry,
    ExitReason,
    PerformanceBreakdown,
    SimulationRunConfig,
    SimulationRunResult,
)
from babylon.engine.headless_runner.run_summary import (
    aggregate_external_node_flows,
    build_summary,
)
from babylon.engine.headless_runner.scopes import (
    UnknownScopeError,
    resolve_scope,
)
from babylon.engine.headless_runner.trace_emitter import TRACE_COLUMNS, TraceEmitter

_LOG = logging.getLogger("babylon.engine.headless_runner")

# Module-level cooperative-shutdown flag set by the SIGINT handler.
# Reset to False at the top of every :func:`run` invocation.
_interrupt_requested = False

# Severity mapping: Postgres conservation_audit_log uses (ok, warn, alarm);
# the summary.json contract uses (info, warning, error, critical).
_AUDIT_SEVERITY_MAP = {
    "ok": "info",
    "warn": "warning",
    "alarm": "error",
}


class RunnerError(Exception):
    """Base class for runner-side preflight errors."""

    exit_code: int = 1
    exit_name: str = "ENGINE_FAILURE"


class ConfigError(RunnerError):
    exit_code = 2
    exit_name = "CONFIG_ERROR"


class ReferenceDataMissingError(RunnerError):
    exit_code = 3
    exit_name = "REFERENCE_DATA_MISSING"


class PostgresUnreachableError(RunnerError):
    exit_code = 4
    exit_name = "POSTGRES_UNREACHABLE"


class _StrictAbort(RunnerError):
    """Raised by the tick loop when --strict is set and an alarm row appears.

    Spec-065 T050. Translated to exit code 1 by the outer try/except.
    """

    exit_code = 1
    exit_name = "ENGINE_FAILURE"

    def __init__(self, tick: int, invariant_name: str) -> None:
        super().__init__(
            f"critical conservation violation at tick {tick}: {invariant_name}"
        )
        self.tick = tick
        self.invariant_name = invariant_name


def _install_sigint_handler() -> None:
    """Install a one-shot cooperative SIGINT handler (research R3)."""
    global _interrupt_requested
    _interrupt_requested = False

    def _handler(_signum: int, _frame: Any) -> None:
        global _interrupt_requested
        _interrupt_requested = True
        # Restore default so a second Ctrl-C aborts immediately.
        with suppress(Exception):
            signal.signal(signal.SIGINT, signal.SIG_DFL)

    with suppress(ValueError):  # signals can only be installed on main thread
        signal.signal(signal.SIGINT, _handler)


def _resolve_scope_from_args(
    args: argparse.Namespace,
) -> tuple[str, frozenset[str], frozenset[str]]:
    """Resolve ``(scope_name, scope_fips, external_node_ids)`` from CLI args."""
    if args.fips is not None:
        raw = [p.strip() for p in args.fips.split(",") if p.strip()]
        bad = [f for f in raw if not (len(f) == 5 and f.isdigit())]
        if bad:
            raise ConfigError(
                f"--fips contains malformed code(s): {sorted(bad)[:5]}; "
                "expected 5-digit FIPS strings."
            )
        scope_name = "custom"
        scope_fips = frozenset(raw)
    else:
        try:
            scope = resolve_scope(args.scope, sqlite_path=args.sqlite_path)
        except UnknownScopeError as exc:
            raise ConfigError(str(exc)) from exc
        scope_name = args.scope
        scope_fips = scope.scope_fips

    external_raw = [p.strip() for p in args.external.split(",") if p.strip()]
    external_node_ids = frozenset(external_raw)
    return scope_name, scope_fips, external_node_ids


def _default_output_dir() -> Path:
    """Timestamp-based default artifact directory."""
    stamp = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return Path("reports") / "sim-runs" / stamp


def _build_config(args: argparse.Namespace) -> SimulationRunConfig:
    """Compose a frozen :class:`SimulationRunConfig` from CLI args."""
    scope_name, scope_fips, external_node_ids = _resolve_scope_from_args(args)
    output_dir = args.output_dir if args.output_dir is not None else _default_output_dir()
    return SimulationRunConfig(
        ticks=args.ticks,
        start_year=args.start_year,
        random_seed=args.seed,
        scope_name=scope_name,
        scope_fips=scope_fips,
        external_node_ids=external_node_ids,
        sqlite_reference_path=args.sqlite_path,
        output_dir=output_dir,
        defines_overlay_path=args.defines,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def _prepare_output_dir(path: Path) -> None:
    """Create the output directory, silently overwriting existing contents (FR-007)."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _open_postgres_pool() -> Any:
    """Open a psycopg ConnectionPool from ``BABYLON_PG_DSN`` / ``BABYLON_TEST_PG_DSN``."""
    dsn = os.environ.get("BABYLON_PG_DSN") or os.environ.get("BABYLON_TEST_PG_DSN")
    if not dsn:
        raise PostgresUnreachableError(
            "No Postgres DSN found in BABYLON_PG_DSN or BABYLON_TEST_PG_DSN."
        )
    try:
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
        return pool
    except Exception as exc:  # pragma: no cover - connectivity errors are runtime
        raise PostgresUnreachableError(
            f"Connection pool failed to open ({exc.__class__.__name__}: {exc})"
        ) from exc


def _apply_migrations(pool: Any) -> None:
    """Apply every migration in src/babylon/persistence/migrations/."""
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


def _validate_preflight(config: SimulationRunConfig) -> None:
    """Check on-disk reference data + Postgres DSN before any heavy work."""
    if not config.sqlite_reference_path.exists():
        raise ReferenceDataMissingError(
            f"SQLite reference DB not found at {config.sqlite_reference_path}"
        )


def _check_strict_alarms(
    *,
    runtime: Any,
    session_id: UUID,
    up_to_tick: int,
) -> tuple[int, str] | None:
    """Spec-065 T050: scan conservation_audit_log for alarm-severity rows.

    Used by the tick loop when ``config.strict`` is True. Returns
    ``(tick, invariant_name)`` of the first alarm row found, or None.

    Polls the same table the trace view + _query_audit_log read. Only
    one round trip per tick — acceptable overhead.
    """
    with runtime._pool.connection() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT tick, invariant_name "
            "FROM conservation_audit_log "
            "WHERE session_id = %s AND tick <= %s AND severity = 'alarm' "
            "ORDER BY tick, invariant_name "
            "LIMIT 1",
            (str(session_id), up_to_tick),
        ).fetchone()
    if row is None:
        return None
    return int(row[0]), str(row[1])


def _advance_tick(
    *,
    bridge: WorldStateBridge,
    world: Any,
    tick: int,
    determinism_hash: str,
) -> None:
    """Spec-065 T042: real per-tick advancement via the bridge.

    The runner now invokes ``bridge.persist_tick(world, tick, hash)``
    on every tick, replacing the spec-064 MVP's no-op carry-forward.
    Per-tick rows are written to the spec-065 subsystem state tables
    (consciousness/demographics/employment) plus hex_state +
    external_node templates re-emitted with the new tick number.

    Per spec-065 research.md §R10, the bridge is a derivation/aggregation
    adapter — its persist_tick computes per-county subsystem rows from
    the in-memory WorldState + SQLite reference data each tick.

    Engine system integration (calling ``engine.run_tick(world.graph,
    services, context)`` to mutate ``world`` between ticks) is deferred
    to a follow-up spec — the engine system surface (15 systems +
    ServiceContainer) is large enough to deserve its own integration
    work. Tick-over-tick variance for SC-004 follows from that future
    integration; today, the bridge correctly persists whatever world
    state exists.
    """
    bridge.persist_tick(world, tick, determinism_hash)


def _query_audit_log(*, pool: Any, session_id: UUID) -> list[AuditEntry]:
    """Project ``conservation_audit_log`` rows into :class:`AuditEntry` list."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT tick, invariant_name, severity, "
            "computed_value, expected_value, residual, scale "
            "FROM conservation_audit_log "
            "WHERE session_id = %s "
            "ORDER BY tick, invariant_name",
            (str(session_id),),
        )
        rows = cur.fetchall()
    out: list[AuditEntry] = []
    for tick, name, sev_raw, computed, expected, residual, scale in rows:
        sev = _AUDIT_SEVERITY_MAP.get(sev_raw, "warning")
        out.append(
            AuditEntry(
                tick=tick,
                invariant_name=name,
                severity=sev,  # type: ignore[arg-type]
                details={
                    "computed_value": computed,
                    "expected_value": expected,
                    "residual": residual,
                    "scale": scale,
                },
            )
        )
    return out


def _query_trace(
    *,
    pool: Any,
    session_id: UUID,
    start_year: int,
    ticks_completed: int,
) -> list[dict[str, Any]]:
    """Query the trace-emission view across all persisted ticks.

    Spec-065 T044: tick-virtualization removed. The bridge now
    persists per-tick subsystem + hex rows, so this query reads the
    actual rows for every tick in [0, ticks_completed). The
    ``simulated_year`` is computed in Python from start_year + tick/52.
    """
    select_cols = ", ".join(c for c in TRACE_COLUMNS if c not in {"simulated_year"})
    sql = (
        f"SELECT {select_cols} FROM view_runtime_trace_emission "
        "WHERE session_id = %s AND tick < %s ORDER BY tick, entity_id"
    )
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (str(session_id), max(ticks_completed, 1)))
        colnames = [d.name for d in cur.description] if cur.description else []
        rows = cur.fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        record = dict(zip(colnames, row, strict=True))
        tick_val = int(record.get("tick", 0))
        record["simulated_year"] = start_year + tick_val / 52.0
        out.append(record)
    return out


def _query_terminal_aggregates(
    *,
    pool: Any,
    session_id: UUID,
    terminal_tick: int,
) -> dict[str, Any]:
    """Aggregate terminal-tick state across all counties from the trace view.

    Spec-065 T044: reads the actual terminal tick rather than tick 0.
    The bridge persists per-tick rows so the terminal aggregate
    reflects whatever final state the simulation reached.
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FILTER (WHERE v > 0), "
            "       SUM(v), SUM(c), SUM(s), SUM(k) "
            "FROM view_runtime_trace_emission "
            "WHERE session_id = %s AND tick = %s",
            (str(session_id), terminal_tick),
        )
        row = cur.fetchone()
    counties_alive = int(row[0] or 0) if row else 0
    return {
        "tick": terminal_tick,
        "counties_alive": counties_alive,
        "total_population": None,
        "total_v": float(row[1] or 0.0) if row else 0.0,
        "total_c": float(row[2] or 0.0) if row else 0.0,
        "total_s": float(row[3] or 0.0) if row else 0.0,
        "total_k": float(row[4] or 0.0) if row else 0.0,
        "mean_p_acquiescence": None,
        "mean_p_revolution": None,
        "mean_ideology_r": None,
        "mean_ideology_l": None,
        "mean_ideology_f": None,
    }


def _county_terminal_snapshot(
    *,
    pool: Any,
    session_id: UUID,
    terminal_tick: int,
) -> list[dict[str, Any]]:
    """Per-county terminal row + delta-vs-initial.

    Spec-065 T044: reads the actual terminal tick. Per-county
    consciousness/demographics/employment columns now flow from the
    bridge-persisted spec-065 subsystem state tables. ``delta_k_vs_initial``
    is computed from the difference between terminal-tick k and tick-0 k.
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT entity_id, v, c, s, k, "
            "       p_acquiescence, p_revolution, "
            "       ideology_r, ideology_l, ideology_f, "
            "       population "
            "FROM view_runtime_trace_emission "
            "WHERE session_id = %s AND tick = %s "
            "ORDER BY entity_id",
            (str(session_id), terminal_tick),
        )
        terminal = cur.fetchall()
        cur.execute(
            "SELECT entity_id, k FROM view_runtime_trace_emission "
            "WHERE session_id = %s AND tick = 0",
            (str(session_id),),
        )
        initial_k_by_entity = {entity_id: float(k or 0.0) for entity_id, k in cur.fetchall()}
    out: list[dict[str, Any]] = []
    for (
        entity_id,
        v,
        c,
        s,
        k,
        p_acq,
        p_rev,
        ideol_r,
        ideol_l,
        ideol_f,
        population,
    ) in terminal:
        k_now = float(k or 0.0)
        k_initial = initial_k_by_entity.get(entity_id, k_now)
        out.append(
            {
                "entity_id": entity_id,
                "v": float(v or 0.0),
                "c": float(c or 0.0),
                "s": float(s or 0.0),
                "k": k_now,
                "p_acquiescence": float(p_acq) if p_acq is not None else None,
                "p_revolution": float(p_rev) if p_rev is not None else None,
                "ideology_r": float(ideol_r) if ideol_r is not None else None,
                "ideology_l": float(ideol_l) if ideol_l is not None else None,
                "ideology_f": float(ideol_f) if ideol_f is not None else None,
                "population": int(population) if population is not None else None,
                "delta_k_vs_initial": k_now - k_initial,
            }
        )
    return out


def _defines_hash(defines: Any) -> str:
    """SHA-256 over the canonical model_dump() of a GameDefines instance."""
    try:
        payload = defines.model_dump(mode="json")
    except AttributeError:
        payload = {"_repr": repr(defines)}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _sqlite_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(config: SimulationRunConfig) -> SimulationRunResult:
    """Execute the headless simulation per ``config`` and emit artifacts.

    Returns:
        :class:`SimulationRunResult` describing the run outcome.
    """
    _install_sigint_handler()
    _validate_preflight(config)

    from babylon.config.defines import GameDefines
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.postgres_initialization import initialize_session

    t_total = time.perf_counter()
    wallclock_start = _dt.datetime.now(_dt.UTC)
    session_id = uuid4()
    exit_reason = ExitReason.COMPLETED
    end_game_event: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None
    pool = _open_postgres_pool()
    runtime: Any = None
    ticks_completed = 0
    per_tick_durations: list[float] = []
    t_session = 0.0
    t_hex = 0.0

    try:
        _apply_migrations(pool)
        runtime = PostgresRuntime(pool=pool)
        defines = GameDefines.load_default()

        t0 = time.perf_counter()
        report = initialize_session(
            session_id=session_id,
            sqlite_path=config.sqlite_reference_path,
            runtime=runtime,
            defines=defines,
            start_year=config.start_year,
            scenario_length_years=max(1, config.ticks // 52 + 1),
            counties=sorted(config.scope_fips),
            hex_hydration_counties=config.scope_fips,
        )
        t_session = time.perf_counter() - t0
        t_hex = t_session  # subset; refined when hex hydration exposes its own timer

        if report.hex_count == 0:
            raise ReferenceDataMissingError(
                "Hex hydration produced zero rows for the requested scope."
            )

        # Spec-065 T043: wire WorldStateBridge into the run.
        # T071: EventCapture is constructed and threaded into the bridge so
        # engine events fired during the tick loop can be drained into
        # summary.events at end-of-run.
        bridge = WorldStateBridge(runtime=runtime, defines=defines)
        event_capture = EventCapture()
        world = bridge.hydrate_initial(
            session_id=session_id,
            scope_fips=config.scope_fips,
            event_capture=event_capture,
            start_year=config.start_year,
            sqlite_path=config.sqlite_reference_path,
        )

        # Spec-065 T064: end-game detector (US4). Optional dotted path
        # resolved + instantiated; bridge.poll_endgame is called per tick.
        if config.endgame_detector:
            try:
                bridge.set_endgame_detector(config.endgame_detector)
            except ImportError as exc:
                raise ConfigError(f"--endgame-detector resolution failed: {exc}") from exc

        if config.dry_run:
            _LOG.info("Dry-run requested; skipping tick loop.")
        else:
            try:
                ticks_completed, endgame_event_payload = _tick_loop(
                    bridge=bridge,
                    world=world,
                    runtime=runtime,
                    session_id=session_id,
                    config=config,
                    per_tick_durations=per_tick_durations,
                )
                if endgame_event_payload is not None:
                    end_game_event = endgame_event_payload
                    exit_reason = ExitReason.EARLY_TERMINATED
            except _StrictAbort as exc:
                # Spec-065 T050: --strict early exit on critical violation.
                ticks_completed = exc.tick + 1
                exit_reason = ExitReason.ERRORED
                error_payload = {
                    "name": exc.exit_name,
                    "message": str(exc),
                    "tick": exc.tick,
                }
            if _interrupt_requested and ticks_completed < config.ticks:
                exit_reason = ExitReason.USER_INTERRUPTED

        terminal_tick = max(ticks_completed - 1, 0)
        audit_entries = _query_audit_log(pool=pool, session_id=session_id)
        terminal_state = _query_terminal_aggregates(
            pool=pool,
            session_id=session_id,
            terminal_tick=terminal_tick,
        )
        snapshot = _county_terminal_snapshot(
            pool=pool,
            session_id=session_id,
            terminal_tick=terminal_tick,
        )
        wallclock_end = _dt.datetime.now(_dt.UTC)

        # Spec-065 T073: drain captured engine events for summary.events.
        captured_events = bridge.refresh_event_log()

        t_artifacts = time.perf_counter()
        artifact_dir = _emit_artifacts(
            config=config,
            session_id=session_id,
            exit_reason=exit_reason,
            ticks_completed=ticks_completed,
            wallclock_start=wallclock_start,
            wallclock_end=wallclock_end,
            terminal_state=terminal_state,
            snapshot=snapshot,
            audit_entries=audit_entries,
            performance=_build_performance(
                total_start=t_total,
                session_init=t_session,
                hex_hydration=t_hex,
                tick_durations=per_tick_durations,
                artifact_emission=0.0,
            ),
            defines=defines,
            pool=pool,
            end_game_event=end_game_event,
            error=error_payload,
            events=captured_events,
        )
        artifact_emission_sec = time.perf_counter() - t_artifacts

        performance = _build_performance(
            total_start=t_total,
            session_init=t_session,
            hex_hydration=t_hex,
            tick_durations=per_tick_durations,
            artifact_emission=artifact_emission_sec,
        )

        return SimulationRunResult(
            session_id=session_id,
            config=config,
            ticks_completed=ticks_completed,
            exit_reason=exit_reason,
            end_game_tick=end_game_event.get("tick") if end_game_event else None,
            end_game_condition=end_game_event.get("condition") if end_game_event else None,
            wallclock_start=wallclock_start,
            wallclock_end=wallclock_end,
            performance=performance,
            conservation_audit=tuple(audit_entries),
            artifact_dir=artifact_dir,
            # Spec-065 T079: pass through terminal WorldState for legacy callers
            # via tools/shared.run_simulation.
            final_world_state=world,
            # Spec-065 T073: pass captured events for downstream consumers.
            events=tuple(
                {
                    "tick": e.tick,
                    "event_type": e.event_type,
                    "entity_ids": list(e.entity_ids),
                    "severity": e.severity,
                    "details": e.details,
                }
                for e in captured_events
            ),
        )
    finally:
        if runtime is not None:
            with suppress(Exception):
                runtime.close()
        else:
            with suppress(Exception):
                pool.close()


def _tick_loop(
    *,
    bridge: WorldStateBridge,
    world: Any,
    runtime: Any,
    session_id: UUID,
    config: SimulationRunConfig,
    per_tick_durations: list[float],
) -> tuple[int, dict[str, Any] | None]:
    """Drive the tick loop with tqdm + cooperative SIGINT.

    Spec-065 T042/T043: each tick now invokes ``bridge.persist_tick``
    to write the per-county subsystem rows + re-emit hex/external
    templates with the new tick number. Replaces spec-064's no-op
    carry-forward.

    Spec-065 T064: returns ``(ticks_completed, endgame_event_dict | None)``;
    a non-None endgame event signals early termination via the
    configured detector.

    Returns:
        ``(ticks_completed, endgame_event)``.
    """
    # Tick 0 was persisted by initialize_session via the hex hydrator
    # (hex_state rows only). Spec-065 also persists the tick-0 subsystem
    # rows as the first iteration of this loop, so the bridge call
    # below covers the full per-tick contract for every tick.
    ticks_completed = 1
    determinism_hash_t0 = hashlib.sha256(
        f"{session_id}:0:{config.random_seed}".encode()
    ).hexdigest()
    bridge.persist_tick(world, 0, determinism_hash_t0)

    tick_range = range(1, config.ticks)
    iterator: Any = tick_range
    if tqdm is not None:
        iterator = tqdm(
            tick_range,
            desc="ticks",
            file=sys.stderr,
            disable=not sys.stderr.isatty(),
            mininterval=1.0,
            unit="tick",
        )

    for tick in iterator:
        if _interrupt_requested:
            break
        t_tick = time.perf_counter()
        determinism_hash = hashlib.sha256(
            f"{session_id}:{tick}:{config.random_seed}".encode()
        ).hexdigest()
        # Spec-065 T072: tag subsequent EventCapture.on_event calls with
        # the current tick BEFORE the engine runs (engine.run_tick will
        # fire events through services.event_bus.publish).
        if bridge.event_capture is not None:
            bridge.event_capture.set_tick(tick)
        _advance_tick(
            bridge=bridge,
            world=world,
            tick=tick,
            determinism_hash=determinism_hash,
        )
        per_tick_durations.append(time.perf_counter() - t_tick)
        ticks_completed = tick + 1

        # Spec-065 T050: --strict early exit on alarm-severity audit row.
        if config.strict:
            alarm = _check_strict_alarms(
                runtime=runtime,
                session_id=session_id,
                up_to_tick=tick,
            )
            if alarm is not None:
                raise _StrictAbort(tick=alarm[0], invariant_name=alarm[1])

        # Spec-065 T064: end-game detector (US4). Halt loop if the
        # configured detector returns a non-None event.
        endgame = bridge.poll_endgame(world, tick)
        if endgame is not None:
            return ticks_completed, endgame
    return ticks_completed, None


def _build_performance(
    *,
    total_start: float,
    session_init: float,
    hex_hydration: float,
    tick_durations: list[float],
    artifact_emission: float,
) -> PerformanceBreakdown:
    total = time.perf_counter() - total_start
    tick_loop_sec = sum(tick_durations)
    if tick_durations:
        durations_ms = [d * 1000.0 for d in tick_durations]
        median_ms = statistics.median(durations_ms)
        p99_ms = (
            sorted(durations_ms)[int(len(durations_ms) * 0.99)]
            if len(durations_ms) > 1
            else durations_ms[0]
        )
        max_ms = max(durations_ms)
    else:
        median_ms = p99_ms = max_ms = 0.0
    return PerformanceBreakdown(
        total_wallclock_sec=total,
        session_init_sec=session_init,
        hex_hydration_sec=hex_hydration,
        tick_loop_sec=tick_loop_sec,
        artifact_emission_sec=artifact_emission,
        per_tick_median_ms=median_ms,
        per_tick_p99_ms=p99_ms,
        per_tick_max_ms=max_ms,
    )


def _emit_artifacts(
    *,
    config: SimulationRunConfig,
    session_id: UUID,
    exit_reason: ExitReason,
    ticks_completed: int,
    wallclock_start: _dt.datetime,
    wallclock_end: _dt.datetime,
    terminal_state: dict[str, Any],
    snapshot: list[dict[str, Any]],
    audit_entries: list[AuditEntry],
    performance: PerformanceBreakdown,
    defines: Any,
    pool: Any,
    end_game_event: dict[str, Any] | None,
    error: dict[str, Any] | None,
    events: tuple[Any, ...] = (),
) -> Path:
    """Write trace.csv + summary.json + manifest.json into ``config.output_dir``."""
    _prepare_output_dir(config.output_dir)
    artifact_dir = config.output_dir

    # trace.csv
    trace_rows = _query_trace(
        pool=pool,
        session_id=session_id,
        start_year=config.start_year,
        ticks_completed=ticks_completed,
    )
    trace_path = artifact_dir / "trace.csv"
    with TraceEmitter(trace_path) as emitter:
        for row in trace_rows:
            emitter.write_row(row)
        trace_row_count = emitter.row_count

    # summary.json
    summary_payload = build_summary(
        config=config,
        session_id=str(session_id),
        exit_reason=exit_reason,
        ticks_completed=ticks_completed,
        wallclock_start=wallclock_start,
        wallclock_end=wallclock_end,
        terminal_state=terminal_state,
        external_node_flows=aggregate_external_node_flows(
            pool=pool, session_id=str(session_id)
        ),
        county_terminal_snapshot=snapshot,
        conservation_audit=audit_entries,
        performance=performance,
        end_game_event=end_game_event,
        error=error,
    )
    # Spec-065 T073: emit captured engine events (FR-018 emission order).
    if events:
        summary_payload["events"] = [
            {
                "tick": e.tick,
                "event_type": e.event_type,
                "entity_ids": list(e.entity_ids),
                "severity": e.severity,
                "details": e.details,
            }
            for e in events
        ]
    else:
        summary_payload["events"] = []
    summary_path = artifact_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2, default=str))

    # manifest.json
    artifact_files = [
        ("trace.csv", "trace_csv_v1", trace_path.stat().st_size, trace_row_count),
        ("summary.json", "summary_json_v1", summary_path.stat().st_size, None),
    ]
    manifest_payload = build_manifest(
        config=config,
        session_id=str(session_id),
        exit_reason=exit_reason,
        wallclock_start=wallclock_start,
        wallclock_end=wallclock_end,
        artifact_dir=artifact_dir,
        artifact_files=artifact_files,
        defines_hash=_defines_hash(defines),
        data_versions={
            "tiger_vintage": "2024",
            "sqlite_sha256": _sqlite_sha256(config.sqlite_reference_path),
        },
    )
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest_payload, indent=2))
    return artifact_dir


def _exit_code_for(reason: ExitReason) -> int:
    """Map exit reason to CLI exit code (contracts/cli_contract.yaml)."""
    if reason == ExitReason.COMPLETED:
        return 0
    if reason == ExitReason.EARLY_TERMINATED:
        return 0
    if reason == ExitReason.USER_INTERRUPTED:
        return 130
    return 1


def _emit_error(exit_name: str, message: str, partial: Path | None) -> None:
    """Emit the canonical single-line stderr error message (FR-020)."""
    artifact_token = str(partial.resolve()) if partial else "NONE"
    print(
        f"ERROR {exit_name}: {message} | partial_artifacts={artifact_token}",
        file=sys.stderr,
        flush=True,
    )


def main_from_argv(args: argparse.Namespace) -> int:
    """Build config + dispatch + map exit code (T032).

    Reads CLI args, dispatches to :func:`run`, prints the artifact
    directory path on stdout for exit-0 runs, and emits the canonical
    error format on stderr for non-zero exits.
    """
    logging.basicConfig(level=getattr(logging, args.verbose), stream=sys.stderr)
    try:
        config = _build_config(args)
    except ConfigError as exc:
        _emit_error(exc.exit_name, str(exc), partial=None)
        return exc.exit_code

    try:
        result = run(config)
    except ConfigError as exc:
        _emit_error(exc.exit_name, str(exc), partial=None)
        return exc.exit_code
    except ReferenceDataMissingError as exc:
        _emit_error(exc.exit_name, str(exc), partial=None)
        return exc.exit_code
    except PostgresUnreachableError as exc:
        _emit_error(exc.exit_name, str(exc), partial=None)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - engine exceptions
        partial: Path | None = config.output_dir if config.output_dir.exists() else None
        _emit_error("ENGINE_FAILURE", f"{exc.__class__.__name__}: {exc}", partial=partial)
        return 1

    if result.artifact_dir is not None:
        print(str(result.artifact_dir.resolve()))
    return _exit_code_for(result.exit_reason)


__all__ = [
    "ConfigError",
    "PostgresUnreachableError",
    "ReferenceDataMissingError",
    "RunnerError",
    "build_parser",
    "main_from_argv",
    "run",
]
