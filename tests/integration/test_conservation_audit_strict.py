"""Spec-065 T047/T048: --strict CLI flag integration tests.

T047: Inject a critical audit row mid-run; --strict on → exit 1, partial.
T048: Same injection without --strict → exit 0 + violation visible in summary.

Both tests use a fixture that runs the runner to a configured tick,
INSERTs a fake alarm row, then continues — verifying the runner picks
up the alarm via _check_strict_alarms.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
from pathlib import Path
from uuid import UUID

import pytest

PG_DSN_ENV = "BABYLON_TEST_PG_DSN"
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
DEFAULT_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"


def _postgres_reachable() -> bool:
    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    try:
        import psycopg

        psycopg.connect(dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _postgres_reachable(), reason="Postgres test DB not reachable"),
    pytest.mark.skipif(
        not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}"
    ),
]


def _inject_alarm_row(session_id: UUID, tick: int) -> None:
    """INSERT a fake alarm-severity audit row directly into Postgres.

    Bypasses the engine — we're testing the runner's --strict polling
    behavior, not the auditor itself.
    """
    import psycopg

    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            INSERT INTO conservation_audit_log (
                session_id, tick, scale, invariant_name,
                computed_value, expected_value, residual, severity,
                determinism_hash, created_at_utc
            ) VALUES (
                %s, %s, 'global_phi', 'test_injected_critical',
                1.0, 0.0, 1.0, 'alarm',
                %s, %s
            ) ON CONFLICT (session_id, tick, scale, invariant_name) DO NOTHING
            """,
            (
                str(session_id),
                tick,
                "0" * 64,
                _dt.datetime.now(_dt.UTC),
            ),
        )
        conn.commit()


def _build_config(*, strict: bool, ticks: int = 10) -> tuple:
    from babylon.engine.headless_runner.models import SimulationRunConfig
    from babylon.engine.headless_runner.scopes import resolve_scope

    sc = resolve_scope("detroit-tri-county")
    out = Path(tempfile.mkdtemp(prefix=f"sim_strict_{strict}_"))
    return SimulationRunConfig(
        ticks=ticks,
        start_year=2010,
        random_seed=2010,
        scope_name="detroit-tri-county",
        scope_fips=sc.scope_fips,
        external_node_ids=sc.external_node_ids,
        sqlite_reference_path=SQLITE_REF,
        output_dir=out,
        strict=strict,
    )


def _ensure_pg_dsn_env() -> None:
    os.environ.setdefault(PG_DSN_ENV, DEFAULT_DSN)


@pytest.fixture
def inject_alarm_first_tick(monkeypatch):
    """Patch _advance_tick to INSERT an alarm row at tick 1."""
    from babylon.engine.headless_runner import runner as runner_module

    real_advance = runner_module._advance_tick
    bridge_session_holder: list[UUID] = []

    def patched_advance(*, bridge, world, tick, determinism_hash, **extra):
        # **extra forwards whatever keyword parameters _advance_tick grows
        # (engine/services/graph today) — this shim intercepts, it must not
        # pin the production signature (that drift broke it 2026-07-16).
        if not bridge_session_holder:
            bridge_session_holder.append(bridge._session_id)
        # Inject alarm at tick 1, BEFORE the bridge persist (so the
        # alarm row exists when --strict polls afterwards).
        if tick == 1 and bridge._session_id is not None:
            _inject_alarm_row(bridge._session_id, tick=1)
        return real_advance(
            bridge=bridge,
            world=world,
            tick=tick,
            determinism_hash=determinism_hash,
            **extra,
        )

    monkeypatch.setattr(runner_module, "_advance_tick", patched_advance)
    return bridge_session_holder


def test_strict_exits_one_on_critical(inject_alarm_first_tick) -> None:
    """T047: --strict + injected alarm at tick 1 → exit_reason=ERRORED."""
    _ensure_pg_dsn_env()
    from babylon.engine.headless_runner.models import ExitReason
    from babylon.engine.headless_runner.runner import run as runner_run

    config = _build_config(strict=True, ticks=10)
    result = runner_run(config)

    assert result.exit_reason == ExitReason.ERRORED, f"expected ERRORED, got {result.exit_reason}"
    # Loop aborted after tick 1 (the injected alarm tick).
    assert result.ticks_completed <= 3, (
        f"expected early abort at tick ~1, got ticks_completed={result.ticks_completed}"
    )


def test_non_strict_continues_on_critical(inject_alarm_first_tick) -> None:
    """T048: --strict OFF + injected alarm → exit 0 but violation visible."""
    _ensure_pg_dsn_env()
    from babylon.engine.headless_runner.models import ExitReason
    from babylon.engine.headless_runner.runner import run as runner_run

    config = _build_config(strict=False, ticks=5)
    result = runner_run(config)

    assert result.exit_reason == ExitReason.COMPLETED, (
        f"expected COMPLETED, got {result.exit_reason}"
    )
    assert result.ticks_completed == 5

    # Violation should appear in summary.json.conservation_audit
    assert result.artifact_dir is not None
    summary = json.loads((result.artifact_dir / "summary.json").read_text())
    audit = summary.get("conservation_audit", [])
    error_entries = [e for e in audit if e.get("severity") in ("error", "critical")]
    assert error_entries, f"expected at least one error/critical audit entry; got {audit}"
