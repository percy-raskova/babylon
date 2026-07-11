"""Bridged Lawverian contradiction pipeline (Phase C1.6 gate).

The forensic failure the Lawverian rewrite exists to kill (project/06 §2): by
~t100 edge ``tension`` pinned at exactly 1.0 on every edge and the
``contradiction_field`` table had 0 rows ever. This gated integration test
pins the fix over a 50-tick bridged run:

- edge ``tension`` is NOT saturated at 1.0 at t50 (it is a fresh, scale-free
  per-edge gap now, not an add-only accumulator);
- the capital_labor opposition gap stays in the open interval (0, 1) and is
  NON-CONSTANT across the run (it moves as wealth moves — the inertness is
  gone);
- ``contradiction_field`` receives at least ``oppositions × engine-ticks`` rows
  (the persistence path that had zero callers now flows).

Gated like the other live-bridge tests: requires the local Postgres test DB
and the canonical SQLite reference DB.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SQLITE = _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite"
_PG_DSN = "host=localhost port=5433 dbname=babylon_test user=test password=test"
_TICKS = 50

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.slow]

if not _SQLITE.exists():  # pragma: no cover - environment guard
    pytest.skip("live reference DB absent", allow_module_level=True)

psycopg = pytest.importorskip("psycopg", reason="psycopg required")
psycopg_pool = pytest.importorskip("psycopg_pool", reason="psycopg_pool required")


def _pg_available() -> bool:
    try:
        pool = psycopg_pool.ConnectionPool(_PG_DSN, min_size=1, max_size=1, open=True, timeout=5)
        pool.close()
    except Exception:
        return False
    return True


if not _pg_available():  # pragma: no cover - environment guard
    pytest.skip("local Postgres test DB unavailable", allow_module_level=True)


@pytest.fixture(scope="module")
def bridged_run():  # type: ignore[no-untyped-def]
    """One hydrated single-county bridged world, driven engine+persist for 50 ticks."""
    from babylon.config.defines import GameDefines
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.engine.context import TickContext
    from babylon.engine.headless_runner.bridge import WorldStateBridge
    from babylon.engine.headless_runner.runner import EventCapture
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
    from babylon.kernel.event_bus import EventBus
    from babylon.models.world_state import WorldState
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.conservation_audit import ConservationAuditor
    from babylon.persistence.postgres_initialization import initialize_session

    pool = psycopg_pool.ConnectionPool(_PG_DSN, min_size=1, max_size=2, open=True)
    runtime = PostgresRuntime(pool=pool)
    defines = GameDefines.load_default()
    session_id = uuid.uuid4()
    initialize_session(
        session_id=session_id,
        sqlite_path=_SQLITE,
        runtime=runtime,
        defines=defines,
        start_year=2010,
        scenario_length_years=2,
        counties=["26163"],
        hex_hydration_counties={"26163"},
    )
    bridge = WorldStateBridge(
        runtime=runtime,
        defines=defines,
        boundary_register=BoundaryFlowRegister(),
        event_bus=EventBus(),
        auditor=ConservationAuditor(epsilon=defines.economy.epsilon_conservation, rng_seed=2010),
    )
    world = bridge.hydrate_initial(
        session_id=session_id,
        scope_fips={"26163"},
        event_capture=EventCapture(),
        total_ticks=_TICKS + 5,
        start_year=2010,
        sqlite_path=_SQLITE,
    )
    services = ServiceContainer.create(defines=defines)
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))
    graph = world.to_graph()

    capital_labor_gaps: list[float] = []
    for tick in range(1, _TICKS + 1):
        engine.run_tick(graph, services, TickContext(tick=tick))
        world = WorldState.from_graph(graph, tick=tick)
        opposition_states = graph.graph.get("opposition_states")
        determinism_hash = hashlib.sha256(f"{session_id}:{tick}:2010".encode()).hexdigest()
        bridge.persist_tick(world, tick, determinism_hash, opposition_states)
        cap = (opposition_states or {}).get("capital_labor", {})
        capital_labor_gaps.append(float(cap.get("gap", 0.0)))

    # Final edge tensions off the live graph.
    final_tensions = [
        float(d["tension"])
        for _u, _v, d in graph.edges(data=True)
        if isinstance(d.get("tension"), (int, float))
    ]

    yield {
        "pool": pool,
        "session_id": session_id,
        "capital_labor_gaps": capital_labor_gaps,
        "final_tensions": final_tensions,
    }
    pool.close()


def test_edge_tension_not_pinned_at_one_at_t50(bridged_run) -> None:  # type: ignore[no-untyped-def]
    """The forensic bug: tension == 1.0 on every edge. It must not saturate."""
    tensions = bridged_run["final_tensions"]
    assert tensions, "expected at least one edge carrying a tension value at t50"
    assert all(t < 1.0 for t in tensions), (
        f"edge tension saturated at 1.0 (the inertness bug): {tensions}"
    )


def test_capital_labor_gap_in_open_interval_and_non_constant(bridged_run) -> None:  # type: ignore[no-untyped-def]
    """The capital_labor gap lives in (0, 1) and MOVES over the run."""
    gaps = bridged_run["capital_labor_gaps"]
    assert len(gaps) == _TICKS
    assert all(0.0 < g < 1.0 for g in gaps), f"gap left the open interval (0,1): {gaps}"
    assert max(gaps) - min(gaps) > 1e-3, (
        f"capital_labor gap is (near-)constant over 50 ticks — inertness not fixed: "
        f"min={min(gaps):.4f} max={max(gaps):.4f}"
    )


def test_contradiction_field_rows_flow(bridged_run) -> None:  # type: ignore[no-untyped-def]
    """contradiction_field (0 rows ever, historically) now receives the snapshot."""
    with psycopg.connect(_PG_DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), count(DISTINCT field_name), count(DISTINCT tick) "
            "FROM contradiction_field WHERE session_id = %s",
            (bridged_run["session_id"],),
        )
        row_count, field_names, ticks = cur.fetchone()
    # Five oppositions bound in the default catalog, one row each per engine tick.
    assert field_names == 5, f"expected 5 oppositions, got {field_names}"
    assert ticks == _TICKS, f"expected {_TICKS} ticks persisted, got {ticks}"
    assert row_count >= field_names * ticks, f"expected >= oppositions*ticks rows, got {row_count}"
