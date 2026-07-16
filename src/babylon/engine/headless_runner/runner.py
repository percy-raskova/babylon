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

from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
from babylon.domain.economics.county_exposure import load_county_exposure_map
from babylon.engine.context import TickContext
from babylon.engine.headless_runner.argparse_cli import build_parser
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.engine.headless_runner.event_capture import EventCapture
from babylon.engine.headless_runner.manifest import build_manifest
from babylon.engine.headless_runner.models import (
    AuditEntry,
    ExitReason,
    PerformanceBreakdown,
    ScheduledBlocShock,
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
from babylon.engine.headless_runner.storage_probe import query_storage_footprint
from babylon.engine.headless_runner.trace_emitter import TRACE_COLUMNS, TraceEmitter
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.kernel.event_bus import EventBus
from babylon.kernel.services import ServicesProtocol
from babylon.models.world_state import WorldState

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


class TerminalAggregateResolutionError(RunnerError):
    """Spec-102 STEP 0: hex rows exist but county resolution yielded zero.

    Guards ``_query_terminal_aggregates`` / ``_county_terminal_snapshot``
    against the hex_spatial_map resolution gap (spec-088 S3, session-scoped
    by migration 0028): hex rows persist with inline ``county_fips=NULL``
    by design — county resolution depends on the session-scoped
    ``hex_spatial_map`` table. If the hydrator didn't populate
    ``hex_spatial_map`` for this session (or it was truncated),
    ``COALESCE(m.county_fips,
    h.county_fips)`` resolves to NULL for every hex row, and
    ``view_runtime_trace_emission`` silently reports
    ``counties_alive=0``/``total_v=0`` — a garbage terminal aggregate that
    looks like a legitimate all-dead-population outcome. This exact bug
    once nearly shipped as spec-101's auto-refreshed baseline (caught only
    by manual review). Raising here converts the silent zero into a loud,
    diagnosable failure instead.
    """

    exit_code = 5
    exit_name = "TERMINAL_AGGREGATE_RESOLUTION_FAILURE"


class _StrictAbort(RunnerError):
    """Raised by the tick loop when --strict is set and an alarm row appears.

    Spec-065 T050. Translated to exit code 1 by the outer try/except.
    """

    exit_code = 1
    exit_name = "ENGINE_FAILURE"

    def __init__(self, tick: int, invariant_name: str) -> None:
        super().__init__(f"critical conservation violation at tick {tick}: {invariant_name}")
        self.tick = tick
        self.invariant_name = invariant_name


class LivenessGateFailure(RunnerError):
    """Spec-105: runtime liveness gate assertion failure.

    Raised by ``_assert_liveness_or_raise`` when the terminal aggregate's
    county count or population liveness fails the generalized gate. Unlike
    the STEP-0 guard (spec-102's :class:`TerminalAggregateResolutionError`,
    which catches the hex-rows-exist-but-zero-counties contention bug),
    this gate catches silent county drops and population death at any scale
    (tri-county N=3, Michigan N=83, national N=3156).
    """

    exit_code = 6
    exit_name = "LIVENESS_GATE_FAILURE"


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
        strict=getattr(args, "strict", False),
        liveness_gate=getattr(args, "liveness_gate", False),
        endgame_detector=getattr(args, "endgame_detector", None),
        write_baseline_to=getattr(args, "write_baseline", None),
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
    """Apply every migration in babylon/persistence/migrations/.

    Resolved relative to the installed package, NOT the process CWD — a
    runner launched outside the repo root used to glob an absent directory
    and silently apply zero migrations.
    """
    migrations_dir = Path(__file__).resolve().parents[2] / "persistence" / "migrations"
    sql_files = sorted(migrations_dir.glob("00*.sql"))
    if not sql_files:
        raise RunnerError(f"No migrations found at {migrations_dir} — refusing to run unmigrated")
    with pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sql_files:
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
    auditor: Any = None,
) -> tuple[int, str] | None:
    """Spec-065 T050: scan for the first alarm-severity audit row.

    Used by the tick loop when ``config.strict`` is True. Returns
    ``(tick, invariant_name)`` of the first alarm row found, or None.

    Spec-065 T049 / T050: if an ``auditor`` is supplied (the canonical
    path from ``runner.run()``), the in-memory ``audit_log_buffer`` is
    consulted first — no Postgres round-trip needed. The SQL fallback
    is retained for callers (unit tests, externally-injected rows) that
    write directly to ``conservation_audit_log``.
    """
    # Fast path: in-memory auditor buffer (T049).
    if auditor is not None:
        for row in auditor.audit_log_buffer:
            if (
                row.tick <= up_to_tick
                and str(getattr(row.severity, "value", row.severity)) == "alarm"
            ):
                return int(row.tick), str(row.invariant_name)
    # Fallback: SQL polling of conservation_audit_log.
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
    engine: SimulationEngine | None = None,
    services: ServicesProtocol | None = None,
    graph: Any = None,
    session_id: UUID | None = None,
    county_exposure_by_external: dict[str, dict[str, float]] | None = None,
    external_nodes_phi: dict[str, float] | None = None,
) -> Any:
    """Spec-066 T035: per-tick engine.run_tick() then bridge.persist_tick().

    When ``engine`` + ``services`` + ``graph`` are provided (the standard
    spec-066 path), the order is:

      1. ``engine.run_tick(graph, services, context)`` mutates ``graph``
         in place — all 21 engine systems execute (ImperialRent →
         Consciousness → Struggle → ...) and the per-tick auditor (if
         configured) runs end-of-tick.
      2. ``world = WorldState.from_graph(graph, tick=tick)`` reconstitutes
         the typed model from the mutated graph for ``persist_tick`` to read.
      3. ``bridge.persist_tick(world, tick, hash)`` derives + writes the
         per-county subsystem rows.

    When ``engine`` is None, falls back to the spec-065 behavior
    (persist-only, engine bypassed) for tests that exercise the bridge
    in isolation.

    Returns:
        The (possibly-reconstructed) ``WorldState`` for the caller to
        continue using as input to subsequent ticks.
    """
    opposition_states: dict[str, Any] | None = None
    if engine is not None and services is not None and graph is not None:
        context = TickContext(tick=tick)
        # Spec-101: populate the dormant TickContext keys so
        # ImperialRentSystem._invoke_phi_distribution_if_wired records DRAIN_EDGE
        # rows every tick (they were a silent no-op while these were absent). The
        # register is the same instance the bridge flushes in persist_tick.
        if (
            session_id is not None
            and county_exposure_by_external is not None
            and external_nodes_phi is not None
        ):
            context["session_id"] = session_id
            context["boundary_flow_register"] = services.boundary_register
            context["external_nodes_phi"] = external_nodes_phi
            context["county_exposure_by_external"] = county_exposure_by_external
        engine.run_tick(graph, services, context)
        world = WorldState.from_graph(graph, tick=tick)
        # C1.4: hand ContradictionSystem's per-tick OppositionRegistry snapshot
        # (graph attribute `opposition_states`, written at position 18) to
        # persist_tick so contradiction_field rows flow. WorldState.from_graph
        # does not carry arbitrary graph attrs, so read it off the graph here.
        opposition_states = graph.graph.get("opposition_states")
    bridge.persist_tick(world, tick, determinism_hash, opposition_states)
    return world


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


def _query_external_nodes_phi(*, pool: Any, session_id: UUID) -> dict[str, float]:
    """Read ``{node_id: phi_year_inflow}`` from the tick-0 external-node rows.

    Spec-101 FR-101-3. The session bootstrap persists one
    ``dynamic_external_node_state`` row per node at tick 0 carrying the attributed
    national Φ (spec-101 D3). This is the same Φ map the conservation auditor
    reads (via the bridge), so the ``Σ DRAIN_EDGE ≡ Φ_week`` identity is
    self-consistent.

    Args:
        pool: Postgres connection pool.
        session_id: Active session UUID.

    Returns:
        ``{node_id: phi_year_inflow}`` for all external nodes at tick 0.
    """
    # Spec-101 review minor (III.7 determinism): ORDER BY node_id — Postgres
    # SELECT order is otherwise unspecified, and the returned dict's
    # insertion order drives the boundary-register write order downstream
    # (economic.py's ``_invoke_phi_distribution_if_wired``).
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT node_id, phi_year_inflow FROM dynamic_external_node_state "
            "WHERE session_id = %s AND tick = 0 ORDER BY node_id",
            (str(session_id),),
        ).fetchall()
    return {str(node_id): float(phi) for node_id, phi in rows}


def _build_shock_timeline(
    shock_schedule: tuple[ScheduledBlocShock, ...],
) -> dict[int, tuple[ScheduledBlocShock, ...]]:
    """Group a run's scheduled shocks by tick, sorted deterministically.

    Spec-102 SLICE B. Within a tick, shocks are sorted by ``bloc`` so
    ``_apply_due_shocks`` iterates in a fixed, reproducible order — no
    dependence on ``shock_schedule``'s (caller-supplied) input order.

    Args:
        shock_schedule: The run config's declared shocks (any order).

    Returns:
        ``{tick: (shocks sorted by bloc, ...)}``. Empty dict for an empty
        schedule (the canonical-scenario default).
    """
    by_tick: dict[int, list[ScheduledBlocShock]] = {}
    for shock in sorted(shock_schedule, key=lambda s: (s.tick, s.bloc)):
        by_tick.setdefault(shock.tick, []).append(shock)
    return {tick: tuple(shocks) for tick, shocks in by_tick.items()}


def _apply_due_shocks(
    *,
    tick: int,
    shock_timeline: dict[int, tuple[ScheduledBlocShock, ...]],
    active_multipliers: dict[str, float],
) -> None:
    """Update ``active_multipliers`` in-place for shocks scheduled at ``tick``.

    Spec-102 SLICE B. Level-set semantics: a shock REPLACES (not
    accumulates onto) the bloc's active multiplier, and the new value
    persists on every subsequent tick until a later shock for the same
    bloc supersedes it — ``active_multipliers`` is a plain dict threaded
    through the tick-loop closure across iterations, never reset per tick.
    Pure and deterministic: no RNG, sorted iteration (via
    :func:`_build_shock_timeline`).

    Args:
        tick: Current simulation tick.
        shock_timeline: Output of :func:`_build_shock_timeline`.
        active_multipliers: Mutable ``{bloc: multiplier}`` state, updated
            in-place.
    """
    for shock in shock_timeline.get(tick, ()):
        active_multipliers[shock.bloc] = shock.phi_multiplier


def _effective_external_nodes_phi(
    *,
    base_external_nodes_phi: dict[str, float],
    active_multipliers: dict[str, float],
) -> dict[str, float]:
    """Recompute the per-tick effective Φ map (base × active multiplier).

    Spec-102 SLICE B. Pure function — does not mutate ``base_external_nodes_phi``.
    Blocs absent from ``active_multipliers`` pass through unchanged
    (multiplier defaults to 1.0), so an empty ``active_multipliers`` (the
    no-shocks-yet or no-shock-schedule-at-all case) returns a map
    value-equal to the base — byte-identical Φ distribution behavior to
    pre-spec-102 spec-101.

    Args:
        base_external_nodes_phi: The static ``{node_id: phi_year_inflow}``
            map read once at session setup (spec-101 FR-101-3).
        active_multipliers: Current ``{bloc: multiplier}`` state.

    Returns:
        A new ``{node_id: phi_year_inflow}`` dict with shocked blocs scaled.
    """
    return {
        node: phi * active_multipliers.get(node, 1.0)
        for node, phi in base_external_nodes_phi.items()
    }


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
        f"SELECT {select_cols} FROM view_runtime_trace_emission "  # noqa: S608 — TRACE_COLUMNS is an imported constant; values use %s placeholders
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


def _query_max_tension(
    *,
    pool: Any,
    session_id: UUID,
) -> float:
    """Spec-065 T080: MAX(tension) over EXPLOITATION edges across all ticks.

    Reads ``dynamic_relationship_state`` (migration 0024). Returns 0.0
    when the table is empty for this session — which is the spec-065
    first-cut state, since ``WorldState.relationships`` is unused until
    spec-066 wires the engine through the bridge. The SQL aggregate is
    correct from day one.
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(tension) FROM dynamic_relationship_state "
            "WHERE session_id = %s AND edge_type = 'EXPLOITATION'",
            (str(session_id),),
        )
        row = cur.fetchone()
    if row is None or row[0] is None:
        return 0.0
    return float(row[0])


def _assert_county_resolution_or_raise(
    *,
    cur: Any,
    session_id: UUID,
    terminal_tick: int,
    resolved_county_count: int,
    null_entity_count: int = 0,
) -> None:
    """Spec-102 STEP 0: fail loud on hex-rows-exist-but-zero-counties-resolved.

    Also detects PARTIAL resolution gaps: when ``null_entity_count > 0``
    some hex rows have NULL entity_id (hex_spatial_map partially populated),
    which would leak bogus NULL-entity rows into downstream aggregates.

    Args:
        cur: Open cursor on the same connection/transaction.
        session_id: Session UUID being queried.
        terminal_tick: The tick being aggregated.
        resolved_county_count: Distinct non-NULL county count already
            observed by the caller's own query.
        null_entity_count: Number of rows with NULL entity_id (0 if
            the caller hasn't checked).

    Raises:
        TerminalAggregateResolutionError: If hex rows exist for this
            session/tick but zero counties resolved, or if any rows have
            NULL entity_id (partial resolution gap).
    """
    if null_entity_count > 0:
        cur.execute(
            "SELECT COUNT(*) FROM v_hex_state_asof WHERE session_id = %s AND tick = %s",
            (str(session_id), terminal_tick),
        )
        hex_row = cur.fetchone()
        hex_row_count = int(hex_row[0] or 0) if hex_row else 0
        raise TerminalAggregateResolutionError(
            f"session={session_id} tick={terminal_tick}: partial resolution gap — "
            f"{null_entity_count} row(s) have NULL entity_id out of "
            f"{resolved_county_count + null_entity_count} total rows "
            f"({hex_row_count} hex rows in v_hex_state_asof). "
            "Refusing to leak NULL-entity rows into downstream aggregates. "
            "This is the known hex_spatial_map/TIGER contention bug "
            "(spec-088 S3) in partial form."
        )
    if resolved_county_count > 0:
        return
    cur.execute(
        "SELECT COUNT(*) FROM v_hex_state_asof WHERE session_id = %s AND tick = %s",
        (str(session_id), terminal_tick),
    )
    hex_row = cur.fetchone()
    hex_row_count = int(hex_row[0] or 0) if hex_row else 0
    if hex_row_count > 0:
        raise TerminalAggregateResolutionError(
            f"session={session_id} tick={terminal_tick}: {hex_row_count} hex "
            "row(s) exist in v_hex_state_asof but county resolution "
            "(hex_spatial_map join in view_runtime_trace_emission) yielded "
            "ZERO counties. Refusing to emit a silent counties_alive=0/"
            "total_v=0 terminal aggregate — hex_spatial_map is not "
            "populated for this session (migration 0028 session-scoping). "
            "Re-run after confirming hex_spatial_map has rows for "
            f"session_id={session_id}."
        )


def _assert_liveness_or_raise(
    *,
    terminal_state: dict[str, Any],
    n_scope: int,
) -> None:
    """Spec-105: generalized liveness gate.

    Asserts that the terminal aggregate is not silently zeroed and that
    every econ-alive county still holds a living population. Unlike the
    baseline-dependent regression comparison (which reads expected
    ``counties_alive`` from a JSON baseline), this gate derives ``n_scope``
    from ``len(config.scope_fips)`` -- making it scope-agnostic (tri-county
    N=3, Michigan N=83, national N=3156).

    Raises:
        LivenessGateFailure: If ``counties_alive == 0`` (silent zero),
            ``counties_with_population != counties_alive`` (population
            death), ``total_v == 0`` (value zeroing), or
            ``counties_alive > n_scope`` (data corruption).

    A ``counties_alive < n_scope`` gap is logged as a WARNING (not a
    failure) -- some counties may lack hex cells (unhydrated territories
    with no TIGER data).
    """
    alive = int(terminal_state.get("counties_alive", 0))
    pop = int(terminal_state.get("counties_with_population", 0))
    total_v = float(terminal_state.get("total_v", 0.0))

    if alive == 0:
        raise LivenessGateFailure(
            f"liveness gate: counties_alive=0 (silent zero). "
            f"N_scope={n_scope}. Expected {n_scope} alive counties but "
            "got zero -- this indicates either the hex_spatial_map contention "
            "bug (spec-088 S3) or a total population extinction event."
        )

    if pop != alive:
        raise LivenessGateFailure(
            f"liveness gate: population death -- counties_with_population={pop} "
            f"!= counties_alive={alive}. {alive - pop} econ-alive "
            "county(ies) lost their living population at the terminal tick "
            "(closed-drain extinction class)."
        )

    if total_v == 0.0:
        raise LivenessGateFailure(
            f"liveness gate: total_v=0 with counties_alive={alive}. "
            "Value zeroing failure -- the engine produced no economic value "
            "despite alive counties."
        )

    if alive > n_scope:
        raise LivenessGateFailure(
            f"liveness gate: counties_alive={alive} exceeds N_scope={n_scope}. "
            "Data corruption -- more counties resolved than the scope defines."
        )

    if alive < n_scope:
        _LOG.warning(
            "Spec-105 liveness gate: counties_alive=%d < N_scope=%d "
            "(%d counties lack hex cells -- likely unhydrated territories)",
            alive,
            n_scope,
            n_scope - alive,
        )


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

    Raises:
        TerminalAggregateResolutionError: Spec-102 STEP 0 — hex rows exist
            for this session/tick but county resolution yielded zero
            counties (see :func:`_assert_county_resolution_or_raise`).
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FILTER (WHERE v > 0), "
            "       SUM(v), SUM(c), SUM(s), SUM(k), "
            "       COUNT(*) FILTER (WHERE ideology_r IS NOT NULL), "
            "       COUNT(DISTINCT entity_id) FILTER (WHERE entity_id IS NOT NULL), "
            "       COUNT(*) FILTER (WHERE entity_id IS NULL) "
            "FROM view_runtime_trace_emission "
            "WHERE session_id = %s AND tick = %s",
            (str(session_id), terminal_tick),
        )
        row = cur.fetchone()
        resolved_county_count = int(row[6] or 0) if row else 0
        null_entity_count = int(row[7] or 0) if row else 0
        _assert_county_resolution_or_raise(
            cur=cur,
            session_id=session_id,
            terminal_tick=terminal_tick,
            resolved_county_count=resolved_county_count,
            null_entity_count=null_entity_count,
        )
    counties_alive = int(row[0] or 0) if row else 0
    return {
        "tick": terminal_tick,
        "counties_alive": counties_alive,
        "counties_with_population": int(row[5] or 0) if row else 0,
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

    Raises:
        TerminalAggregateResolutionError: Spec-102 STEP 0 — hex rows exist
            for this session/tick but county resolution yielded zero
            counties (see :func:`_assert_county_resolution_or_raise`).
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
        resolved_county_count = sum(1 for entity_row in terminal if entity_row[0] is not None)
        null_entity_count = sum(1 for entity_row in terminal if entity_row[0] is None)
        _assert_county_resolution_or_raise(
            cur=cur,
            session_id=session_id,
            terminal_tick=terminal_tick,
            resolved_county_count=resolved_county_count,
            null_entity_count=null_entity_count,
        )
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


def _resolve_defines(config: SimulationRunConfig) -> Any:
    """Resolve the ``GameDefines`` a run executes against.

    Precedence (spec: optimization-package plumbing fix):

    1. ``config.defines`` — an in-process ``GameDefines`` supplied by a caller
       (e.g. a programmatic parameter sweep). Used verbatim.
    2. ``config.defines_overlay_path`` — a YAML overlay loaded + per-field-merged
       over the schema defaults via :meth:`GameDefines.load_from_yaml`.
    3. Neither set — :meth:`GameDefines.load_default` (the canonical on-disk
       ``defines.yaml``, else the compiled defaults).

    The default branch is byte-identical to the pre-fix behaviour, so the
    ``qa:regression`` baselines (which set neither override) are unaffected.

    Args:
        config: The run configuration.

    Returns:
        The resolved ``GameDefines`` instance.
    """
    from babylon.config.defines import GameDefines

    if config.defines is not None:
        return config.defines
    if config.defines_overlay_path is not None:
        return GameDefines.load_from_yaml(config.defines_overlay_path)
    return GameDefines.load_default()


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


def _build_economics_overrides(
    session_factory: Any = None,
    event_bus: Any = None,
    defines: Any = None,
) -> tuple[dict[str, Any], Any]:
    """Construct economics calculator overrides for ``ServiceContainer.create``.

    Spec E101: wires gamma (and melt when a session_factory is provided)
    into the headless runner so TickDynamicsSystem actually computes
    gamma instead of no-opping.

    Without these overrides, ``ServiceContainer.create()`` leaves
    ``gamma_calculator`` and ``melt_calculator`` at their default ``None``.
    TickDynamicsSystem guards on ``melt_calculator is not None`` (early
    return at ``tick/system/__init__.py:136``) and then reads
    ``gamma_calculator.compute(year)`` at line 387 — with both ``None``
    the entire system no-ops and gamma stays at the hardcoded 0.33 default.

    Program 17 / Item 1a: when ``event_bus`` and ``defines`` are also
    provided (alongside ``session_factory``), additionally wires the
    Spec-057 Leontief imperial-rent pipeline via
    :func:`babylon.domain.economics.factory.create_leontief_rent_services`
    so ``tick_phi_hour`` is genuinely computed per county instead of the
    permanent ``0.0`` stub.

    Args:
        session_factory: Optional SQLAlchemy session factory for the
            normalized reference DB. When provided, ``melt_calculator``
            is wired (required to pass the TickDynamicsSystem gate) and
            ``unemployment_source`` is wired (Wave 6 D8: per-county BLS
            LAUS U-3 instead of the frozen 0.05 prev-carry default).
            ``cpi_source`` is also wired (Wave 6 C4: real CPIAUCSL-based
            real-wage deflation instead of the frozen 1.0 nominal==real
            default). When ``None``, only the parameterless
            ``gamma_calculator`` is wired.
        event_bus: Optional EventBus for the Leontief pipeline's
            calibration-warning emission. Required (with ``defines``) to
            wire the Leontief overrides.
        defines: Optional ``GameDefines`` for the Leontief allocator's
            tunables (``defines.economy.leontief_rent``). Required (with
            ``event_bus``) to wire the Leontief overrides.

    Returns:
        A ``(overrides, leontief_session)`` tuple: ``overrides`` is a dict
        of service overrides suitable for ``**``-unpacking into
        :meth:`ServiceContainer.create`; ``leontief_session`` is the open
        SQLAlchemy session backing the Leontief overrides (``None`` when
        ``session_factory``/``event_bus``/``defines`` weren't all
        supplied) — the caller owns closing it.
    """
    from babylon.domain.economics.gamma.adapters import MVPUnpaidCareHoursSource, QCEWCareAdapter
    from babylon.domain.economics.gamma.gamma_iii import DefaultGammaIIICalculator

    unpaid_care = MVPUnpaidCareHoursSource()
    paid_care = QCEWCareAdapter()
    gamma = DefaultGammaIIICalculator(unpaid_care, paid_care)

    overrides: dict[str, Any] = {"gamma_calculator": gamma}
    leontief_session: Any = None

    if session_factory is not None:
        from babylon.domain.economics.melt import DefaultMELTCalculator
        from babylon.domain.economics.melt.adapters import (
            SQLiteBEANationalGDPSource,
            SQLiteCPISource,
            SQLiteQCEWNationalEmploymentSource,
        )
        from babylon.domain.economics.throughput.adapters import (
            SQLiteBLSUnemploymentSource,
            SQLiteQCEWCountyNAICSSource,
        )

        bea_national = SQLiteBEANationalGDPSource(session_factory)
        qcew_national = SQLiteQCEWNationalEmploymentSource(session_factory)
        melt = DefaultMELTCalculator(bea_national, qcew_national)
        overrides["melt_calculator"] = melt
        # Wave 6 D8: BLS LAUS U-3 per-county unemployment replaces the frozen
        # 0.05 prev-carry default in the tick pipeline (honest-data ruling).
        overrides["unemployment_source"] = SQLiteBLSUnemploymentSource(session_factory)
        # Item 60: real median-wage bootstrap (employment-weighted p50 over
        # QCEW 6-digit leaves) — initial condition only; dynamics own the rest.
        overrides["wage_source"] = SQLiteQCEWCountyNAICSSource(session_factory)
        # Wave 6 C4: real CPIAUCSL-based real-wage deflation series — closes
        # the "wages never naked" gap (mirrors _bridge_economics_overrides).
        overrides["cpi_source"] = SQLiteCPISource(session_factory)

        if event_bus is not None and defines is not None:
            from babylon.domain.economics.factory import create_leontief_rent_services

            leontief_overrides, leontief_session = create_leontief_rent_services(
                session_factory, event_bus, defines
            )
            overrides.update(leontief_overrides)

    return overrides, leontief_session


def run(config: SimulationRunConfig) -> SimulationRunResult:
    """Execute the headless simulation per ``config`` and emit artifacts.

    Returns:
        :class:`SimulationRunResult` describing the run outcome.
    """
    _install_sigint_handler()
    _validate_preflight(config)

    from babylon.persistence import PostgresRuntime
    from babylon.persistence.conservation_audit import (
        ConservationAuditor,
        PairedCrossBorderEmissionEvaluator,
        phi_week_conservation_evaluator,
    )
    from babylon.persistence.postgres_initialization import (
        INTERNATIONAL_NODES,
        initialize_session,
    )

    t_total = time.perf_counter()
    wallclock_start = _dt.datetime.now(_dt.UTC)
    session_id = uuid4()
    exit_reason = ExitReason.COMPLETED
    end_game_event: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None
    pool = _open_postgres_pool()
    runtime: Any = None
    leontief_session: Any = None
    ticks_completed = 0
    per_tick_durations: list[float] = []
    t_session = 0.0
    t_hex = 0.0

    try:
        _apply_migrations(pool)
        runtime = PostgresRuntime(pool=pool)
        defines = _resolve_defines(config)

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
        # T055: BoundaryFlowRegister is owned by the runner and injected into
        # the bridge so spec-066's engine.run_tick can reach it via
        # services.boundary_register.
        # T071: EventBus + EventCapture are constructed by the runner and
        # threaded into the bridge; bridge.hydrate_initial subscribes
        # event_capture.on_event to all known EventTypes on the bus.
        # T049: ConservationAuditor is constructed here, passed to the
        # bridge for per-tick audit_end_of_tick(...) invocation, and
        # consulted by _check_strict_alarms during the tick loop.
        boundary_register = BoundaryFlowRegister()
        event_bus = EventBus()
        event_capture = EventCapture()
        auditor = ConservationAuditor(
            epsilon=defines.economy.epsilon_conservation,
            rng_seed=config.random_seed,
        )
        # Spec-101 FR-101-5: the Σ DRAIN_EDGE ≡ Φ_week per-bloc identity.
        auditor.register_invariant(
            "imperial_rent_phi_week_distribution", phi_week_conservation_evaluator
        )
        # Spec-063 FR-030c / T043: every COMMUTE_OUT (dest_kind='external')
        # must carry its same-tick wage-repatriation TRADE_EDGE pair.
        auditor.register_invariant(
            "paired_cross_border_emission", PairedCrossBorderEmissionEvaluator()
        )
        bridge = WorldStateBridge(
            runtime=runtime,
            defines=defines,
            boundary_register=boundary_register,
            event_bus=event_bus,
            auditor=auditor,
            # Spec-101 review fix #3: raw national Φ, independent of the D3
            # attribution — feeds the auditor's aggregate coverage check.
            national_phi_reference=report.national_phi_reference,
        )
        world = bridge.hydrate_initial(
            session_id=session_id,
            scope_fips=config.scope_fips,
            event_capture=event_capture,
            total_ticks=config.ticks,
            start_year=config.start_year,
            sqlite_path=config.sqlite_reference_path,
        )

        # Spec-089 loud gate (Gate A): the bridge's resolved template must
        # match the hydrated frame. A mismatch means spec-088 S3 spatial-map
        # resolution failed (e.g. empty hex_spatial_map) — delta emission,
        # checkpoint frames, and the conservation auditor would all run
        # silently blind (the 2026-07-06 aborted-national-run failure mode).
        if bridge.hex_template_size != report.hex_count:
            raise RunnerError(
                f"Bridge hex template ({bridge.hex_template_size} rows) != "
                f"hydrated hex frame ({report.hex_count} rows) for session "
                f"{session_id} — refusing to run blind."
            )

        # Spec-066 T034/T036: construct ServiceContainer + SimulationEngine
        # ONCE before the tick loop. Share the bridge's event_bus / auditor /
        # boundary_register so engine systems can publish events that
        # EventCapture sees and emit conservation audit rows that the
        # auditor's buffer collects. A fresh SimulationEngine instance (not
        # the module-level _DEFAULT_ENGINE singleton) avoids test-isolation
        # contamination if multiple runs share a process.
        #
        # Spec-E101: wire gamma_III + MELT calculators into the
        # ServiceContainer so TickDynamicsSystem actually computes
        # reproductive visibility instead of no-opping on the hardcoded
        # 0.33 default. MELT is required to pass the
        # ``melt_calculator is not None`` gate at
        # ``tick/system/__init__.py:136`` before gamma is reached.
        #
        # Program 17 / Item 1a: also wires the Spec-057 Leontief
        # imperial-rent pipeline (periphery wages / final demand / county
        # allocation / production-chain calculator) so ``tick_phi_hour`` is
        # genuinely computed per county. Built ONCE here, before the tick
        # loop (mirrors the rest of this construction site); the session it
        # opens is closed in this function's ``finally`` teardown below.
        from babylon.reference.database import get_normalized_session_factory

        calc_session_factory = get_normalized_session_factory()
        economics_overrides, leontief_session = _build_economics_overrides(
            session_factory=calc_session_factory,
            event_bus=event_bus,
            defines=defines,
        )
        services = ServiceContainer.create(
            defines=defines,
            **economics_overrides,
        )
        services.event_bus = event_bus
        services.boundary_register = boundary_register
        services.auditor = auditor
        engine = SimulationEngine(_DEFAULT_SYSTEMS, auditor=auditor)

        # Spec-066 T035: snapshot the WorldState to a single BabylonGraph that
        # the engine mutates in-place across all ticks. The graph is the
        # source-of-truth between systems; world is reconstituted from it
        # after each engine.run_tick so persist_tick can read.
        graph = world.to_graph()

        # Spec-101 FR-101-1/2/3: assemble the Φ-distribution inputs once before
        # the tick loop. The exposure map is bloc-invariant (spec-100 R6), so ONE
        # scope-renormalised {fips: weight} map is broadcast to every
        # international node. external_nodes_phi is read from the tick-0
        # external-node rows the bootstrap persisted (they carry the attributed
        # national Φ, spec-101 D3). Both are static for the run.
        exposure_map = load_county_exposure_map(
            sqlite_path=config.sqlite_reference_path,
            year=config.start_year,
            scope_fips=config.scope_fips,
        )
        # Bloc-invariant broadcast: every international node shares the one
        # read-only exposure map (spec-100 R6 — the distribution is identical
        # across blocs; the map is never mutated downstream).
        county_exposure_by_external = dict.fromkeys(INTERNATIONAL_NODES, exposure_map)
        external_nodes_phi = _query_external_nodes_phi(pool=pool, session_id=session_id)

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
                    graph=graph,
                    engine=engine,
                    services=services,
                    runtime=runtime,
                    session_id=session_id,
                    config=config,
                    per_tick_durations=per_tick_durations,
                    county_exposure_by_external=county_exposure_by_external,
                    external_nodes_phi=external_nodes_phi,
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
        # Spec-065 T080: cross-tick MAX(tension) over EXPLOITATION edges.
        terminal_state["max_tension"] = _query_max_tension(
            pool=pool,
            session_id=session_id,
        )
        # Spec-105: generalized liveness gate. When config.liveness_gate
        # is True, assert counties_alive > 0, counties_with_population ==
        # counties_alive, and total_v > 0. Failure sets exit_reason=ERRORED
        # with a descriptive error payload (artifacts are still emitted).
        if config.liveness_gate and exit_reason == ExitReason.COMPLETED:
            try:
                _assert_liveness_or_raise(
                    terminal_state=terminal_state,
                    n_scope=len(config.scope_fips),
                )
            except LivenessGateFailure as exc:
                exit_reason = ExitReason.ERRORED
                error_payload = {
                    "name": exc.exit_name,
                    "message": str(exc),
                    "tick": terminal_tick,
                }
        snapshot = _county_terminal_snapshot(
            pool=pool,
            session_id=session_id,
            terminal_tick=terminal_tick,
        )
        wallclock_end = _dt.datetime.now(_dt.UTC)

        # Spec-065 T073: drain captured engine events for summary.events.
        captured_events = bridge.refresh_event_log()

        t_artifacts = time.perf_counter()
        # Spec-066 T030/T036: capture per-system wallclock from the engine
        # so summary.performance.per_system_ms is populated with one entry
        # per executed engine system class.
        per_system_ms = dict(engine.per_system_ms)

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
                per_system_ms=per_system_ms,
            ),
            defines=defines,
            pool=pool,
            end_game_event=end_game_event,
            error=error_payload,
            events=captured_events,
            bridge_db_reads={
                "population_db_reads": bridge.population_db_reads,
                "employment_db_reads": bridge.employment_db_reads,
                "total_db_reads": bridge.total_db_reads,
            },
            # C.8 (spec 2.R): attest whether TickDynamicsSystem computed gamma/MELT
            # from wired calculators or fell back to hardcoded coefficients.
            economics_fallbacks=services.economics_fallbacks.to_dict(),
        )
        artifact_emission_sec = time.perf_counter() - t_artifacts

        performance = _build_performance(
            total_start=t_total,
            session_init=t_session,
            hex_hydration=t_hex,
            tick_durations=per_tick_durations,
            artifact_emission=artifact_emission_sec,
            per_system_ms=per_system_ms,
        )

        # Spec-065 T085: write the artifact's summary.json to the
        # baseline path when the run completed successfully and the
        # caller requested it. The michigan-e2e CI gate reads from this
        # path; making the refresh atomic with the canonical run keeps
        # the operator workflow to a single command.
        if config.write_baseline_to is not None and exit_reason in (
            ExitReason.COMPLETED,
            ExitReason.EARLY_TERMINATED,
        ):
            summary_src = artifact_dir / "summary.json"
            if summary_src.exists():
                baseline_dest = config.write_baseline_to
                baseline_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(summary_src, baseline_dest)
                _LOG.info("Spec-065 T085: refreshed baseline %s", baseline_dest)

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
        if leontief_session is not None:
            with suppress(Exception):
                leontief_session.close()
        if runtime is not None:
            with suppress(Exception):
                runtime.close()
        else:
            with suppress(Exception):
                pool.close()


def _verify_tick0_commit_marker(
    *,
    runtime: Any,
    session_id: UUID,
    expected_hash: str,
    expected_hex_rows: int,
) -> None:
    """Spec-089 FR-003 loud gate (Gate B): read back the tick-0 marker.

    The committed ``(session, 0)`` ``tick_commit`` row must be the bridge's
    real marker — the runner's identity hash plus the full checkpoint frame
    count. This catches marker shadowing (an init-time placeholder claiming
    the primary key so the bridge's re-delivery is silently dropped by
    ``ON CONFLICT DO NOTHING``) and empty-frame emission in one read-back.
    Skipped gracefully on pre-0029 databases (no ``tick_commit`` table),
    mirroring :func:`get_last_committed_tick`'s ``to_regclass`` guard.

    Args:
        runtime: PostgresRuntime whose pool committed the tick-0 envelope.
        session_id: Active session UUID.
        expected_hash: The runner's tick-0 identity hash.
        expected_hex_rows: The bridge's resolved checkpoint frame size.

    Raises:
        RunnerError: Marker missing, hash mismatched, frame count wrong,
            or checkpoint flag unset.
    """
    with runtime._pool.connection() as conn:  # noqa: SLF001
        has_table = conn.execute("SELECT to_regclass('tick_commit')").fetchone()
        if has_table is None or has_table[0] is None:
            return  # pre-0029 database: no chain to verify
        row = conn.execute(
            "SELECT determinism_hash, hex_rows_written, is_checkpoint "
            "FROM tick_commit WHERE session_id = %s AND tick = 0",
            (str(session_id),),
        ).fetchone()
    if row is None:
        raise RunnerError(f"tick 0 committed no tick_commit marker for {session_id}")
    # determinism_hash is CHAR-typed in Postgres; strip the pad blanks.
    digest, hex_rows, is_checkpoint = str(row[0]).strip(), int(row[1]), bool(row[2])
    if digest != expected_hash or hex_rows != expected_hex_rows or not is_checkpoint:
        raise RunnerError(
            "tick-0 commit marker corrupt for "
            f"{session_id}: hash={digest[:12]}... (expected {expected_hash[:12]}...), "
            f"hex_rows_written={hex_rows} (expected {expected_hex_rows}), "
            f"is_checkpoint={is_checkpoint} — spec-089 FR-003 violated."
        )


def _tick_loop(
    *,
    bridge: WorldStateBridge,
    world: Any,
    runtime: Any,
    session_id: UUID,
    config: SimulationRunConfig,
    per_tick_durations: list[float],
    graph: Any = None,
    engine: SimulationEngine | None = None,
    services: ServicesProtocol | None = None,
    county_exposure_by_external: dict[str, dict[str, float]] | None = None,
    external_nodes_phi: dict[str, float] | None = None,
) -> tuple[int, dict[str, Any] | None]:
    """Drive the tick loop with tqdm + cooperative SIGINT.

    Spec-065 T042/T043: each tick now invokes ``bridge.persist_tick``
    to write the per-county subsystem rows + re-emit hex/external
    templates with the new tick number. Replaces spec-064's no-op
    carry-forward.

    Spec-065 T064: returns ``(ticks_completed, endgame_event_dict | None)``;
    a non-None endgame event signals early termination via the
    configured detector.

    Spec-102 SLICE B: ``config.shock_schedule`` (empty by default) is
    compiled once into a tick-indexed timeline; each tick applies any
    shocks due at that tick to a persistent ``active_multipliers`` map and
    recomputes the *effective* ``external_nodes_phi`` passed to
    ``_advance_tick`` for that tick. With an empty schedule this is a
    value-identical no-op — ``_effective_external_nodes_phi`` returns a map
    equal to ``external_nodes_phi`` — so canonical runs are unaffected.

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
    # Spec-089 loud gate (Gate B): the committed tick-0 marker must carry
    # the identity hash + the full checkpoint frame count — refuse to tick
    # forward on a shadowed/placeholder marker or an empty frame. The gate is
    # a Postgres read-back, so it is skipped when there is no runtime (the
    # pure tick-loop unit tests drive the loop with runtime=None).
    if runtime is not None:
        _verify_tick0_commit_marker(
            runtime=runtime,
            session_id=session_id,
            expected_hash=determinism_hash_t0,
            expected_hex_rows=bridge.hex_template_size,
        )

    # Spec-102 SLICE B: shock timeline + persistent per-bloc multiplier
    # state, threaded across tick-loop iterations (never reset per tick).
    shock_timeline = _build_shock_timeline(config.shock_schedule)
    active_shock_multipliers: dict[str, float] = {}

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
        # Spec-102 SLICE B: apply any shocks scheduled at this tick, then
        # recompute the effective (possibly shocked) external_nodes_phi.
        # Level-set semantics — active_shock_multipliers persists across
        # iterations, so a bloc's multiplier stays in effect on every tick
        # after its scheduled tick.
        effective_external_nodes_phi = external_nodes_phi
        if external_nodes_phi is not None:
            _apply_due_shocks(
                tick=tick,
                shock_timeline=shock_timeline,
                active_multipliers=active_shock_multipliers,
            )
            effective_external_nodes_phi = _effective_external_nodes_phi(
                base_external_nodes_phi=external_nodes_phi,
                active_multipliers=active_shock_multipliers,
            )
        # Spec-066 T035: _advance_tick now runs the engine when
        # engine+services+graph are provided. It returns the
        # reconstituted world from the mutated graph for subsequent ticks.
        world = _advance_tick(
            bridge=bridge,
            world=world,
            tick=tick,
            determinism_hash=determinism_hash,
            engine=engine,
            services=services,
            graph=graph,
            session_id=session_id,
            county_exposure_by_external=county_exposure_by_external,
            external_nodes_phi=effective_external_nodes_phi,
        )
        per_tick_durations.append(time.perf_counter() - t_tick)
        ticks_completed = tick + 1

        # Spec-065 T050: --strict early exit on alarm-severity audit row.
        if config.strict:
            alarm = _check_strict_alarms(
                runtime=runtime,
                session_id=session_id,
                up_to_tick=tick,
                auditor=bridge.auditor,
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
    per_system_ms: dict[str, float] | None = None,
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
        per_system_ms=per_system_ms or {},
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
    bridge_db_reads: dict[str, int] | None = None,
    economics_fallbacks: dict[str, Any] | None = None,
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
        external_node_flows=aggregate_external_node_flows(pool=pool, session_id=str(session_id)),
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
        bridge_db_reads=bridge_db_reads,
        # Spec-087 FR-009: best-effort storage footprint (None => key omitted).
        storage=query_storage_footprint(
            pool=pool,
            session_id=session_id,
            ticks_persisted=ticks_completed,
        ),
        # C.8 (spec 2.R): loud economics-fallback attestation (None => omitted).
        economics_fallbacks=economics_fallbacks,
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
    except TerminalAggregateResolutionError as exc:
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
