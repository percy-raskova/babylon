"""The value-form defect Φ live in the bridged income-circuit world (Phase D5).

The ``imperial`` opposition was NULL before Phase D. Rebound to the wage⇄value
counit defect over the per-class ``(w_paid, v_produced)`` accounting, it now
carries a real, non-zero gap once the income circuit pays super-wages every
tick, with a stable-positive balance — the pacification of the labor
aristocracy by imperial rent (W > V, the Fundamental Theorem). The ``wage``
opposition reads the same defect from the same accounting rather than from
endpoint wealth.

Gated exactly like ``test_bridge_income_circuit.py``: requires the local
Postgres test DB and the canonical SQLite reference DB.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SQLITE = _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite"
_PG_DSN = "host=localhost port=5433 dbname=babylon_test user=test password=test"

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.slow]

if not _SQLITE.exists():  # pragma: no cover - environment guard
    pytest.skip("live reference DB absent", allow_module_level=True)

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


def _asymmetry(w: float, v: float) -> tuple[float, float]:
    """Expected (gap, balance) of the (value=A, wage=B) asymmetry form."""
    total = w + v
    if total <= 1e-9:
        return (0.0, 0.0)
    gap = abs(w - v) / total
    balance = (w - v) / total
    return (gap, balance)


@pytest.fixture(scope="module")
def bridged_run():  # type: ignore[no-untyped-def]
    """Hydrate a single-county bridged world and run 30 ticks, capturing Φ."""
    from babylon.config.defines import GameDefines
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.engine.context import TickContext
    from babylon.engine.event_bus import EventBus
    from babylon.engine.headless_runner.bridge import WorldStateBridge
    from babylon.engine.headless_runner.runner import EventCapture
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
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
        total_ticks=30,
        start_year=2010,
        sqlite_path=_SQLITE,
    )
    services = ServiceContainer.create(defines=defines)
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

    graph = world.to_graph()
    imperial_history: list[dict[str, float]] = []
    for tick in range(1, 31):
        engine.run_tick(graph, services, TickContext(tick=tick))
        states = graph.graph.get("opposition_states", {})
        if "imperial" in states:
            imperial_history.append(dict(states["imperial"]))

    result = {
        "graph": graph,
        "final_states": dict(graph.graph["opposition_states"]),
        "imperial_history": imperial_history,
    }
    yield result
    pool.close()


class TestImperialGapLive:
    def test_imperial_gap_becomes_non_zero_once_phi_flows(self, bridged_run) -> None:  # type: ignore[no-untyped-def]
        imperial = bridged_run["final_states"]["imperial"]
        assert imperial["gap"] > 0.0, "imperial Φ gap stayed at the NULL-measure zero"

    def test_imperial_balance_is_stable_positive_pacification(self, bridged_run) -> None:  # type: ignore[no-untyped-def]
        # Every tick that carried a reading: wages exceed value (W > V) — the
        # imperial bribe, a positive balance held across the whole window.
        history = bridged_run["imperial_history"]
        assert history, "no imperial readings captured"
        assert all(s["balance"] > 0.0 for s in history), (
            f"imperial balance was not stable-positive: {[round(s['balance'], 4) for s in history]}"
        )

    def test_wage_state_matches_the_w_v_accounting(self, bridged_run) -> None:  # type: ignore[no-untyped-def]
        # The single paid worker class carries the (w_paid, v_produced) pair;
        # the wage opposition must read THAT defect, not endpoint wealth.
        graph = bridged_run["graph"]
        worker = graph.nodes["C001"]
        assert "w_paid" in worker and "v_produced" in worker
        expected_gap, expected_balance = _asymmetry(worker["w_paid"], worker["v_produced"])

        wage = bridged_run["final_states"]["wage"]
        assert wage["gap"] == pytest.approx(expected_gap, abs=1e-5)
        assert wage["balance"] == pytest.approx(expected_balance, abs=1e-5)

    def test_wage_and_imperial_share_the_defect(self, bridged_run) -> None:  # type: ignore[no-untyped-def]
        states = bridged_run["final_states"]
        assert states["wage"]["gap"] == pytest.approx(states["imperial"]["gap"], abs=1e-9)
        assert states["wage"]["balance"] == pytest.approx(states["imperial"]["balance"], abs=1e-9)
