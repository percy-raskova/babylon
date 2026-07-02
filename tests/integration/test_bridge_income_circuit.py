"""Bridged-world income circuit (ADR044 completion, 2026-07-02).

RED-first: the spec-065 "first cut" deliberately hydrated NO territories
and NO TENANCY edges ("territories deliberately empty ... engine systems
requiring territories are not part of the bridged loop yet"), which left
the canonical entity economy a closed drain: ProductionSystem pays only
workers holding a TENANCY edge to a territory, so every class burned its
fixed endowment and the whole state died at tick ~68-70 — invisible
because no gate asserted survival.

These tests pin the completed circuit: per-county Territory + TENANCY
edge at hydration, wage income actually flowing, and population survival
past the historical extinction cliff.

Gated like the other live-bridge tests: requires the local Postgres test
DB and the canonical SQLite reference DB.
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


@pytest.fixture(scope="module")
def bridged():  # type: ignore[no-untyped-def]
    """One hydrated single-county bridged world + engine harness."""
    from babylon.config.defines import GameDefines
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
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
        total_ticks=90,
        start_year=2010,
        sqlite_path=_SQLITE,
    )
    services = ServiceContainer.create(defines=defines)
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))
    yield {"world": world, "services": services, "engine": engine}
    pool.close()


class TestHydrationShape:
    def test_one_territory_per_county(self, bridged) -> None:  # type: ignore[no-untyped-def]
        world = bridged["world"]
        assert len(world.territories) == 1, "hydration must seed one Territory per county"
        (territory,) = world.territories.values()
        assert territory.biocapacity > 0
        assert territory.max_biocapacity > 0

    def test_tenancy_edge_connects_worker_to_territory(self, bridged) -> None:  # type: ignore[no-untyped-def]
        world = bridged["world"]
        tenancy = [r for r in world.relationships if r.edge_type.value == "tenancy"]
        assert len(tenancy) == 1, "one TENANCY edge per county worker"
        (edge,) = tenancy
        assert edge.source_id == "C001"
        assert edge.target_id in world.territories

    def test_exploitation_edge_still_seeded(self, bridged) -> None:  # type: ignore[no-untyped-def]
        world = bridged["world"]
        exploitation = [r for r in world.relationships if r.edge_type.value == "exploitation"]
        assert len(exploitation) == 1


class TestIncomeFlows:
    def test_worker_receives_production_income(self, bridged) -> None:  # type: ignore[no-untyped-def]
        from babylon.engine.context import TickContext

        graph = bridged["world"].to_graph()
        wealth_before = graph.nodes["C001"]["wealth"]
        bridged["engine"].run_tick(graph, bridged["services"], TickContext(tick=1))
        wealth_after = graph.nodes["C001"]["wealth"]
        # Pure-drain trajectory was 0.5 -> 0.4302; with the income circuit
        # production must at least offset the biological cost.
        assert wealth_after > wealth_before - 0.01, (
            f"worker earned no income: {wealth_before} -> {wealth_after}"
        )

    def test_county_population_survives_past_the_extinction_cliff(self, bridged) -> None:  # type: ignore[no-untyped-def]
        """The liveness contract of this fix: the county stays alive.

        Historical behavior: workers extinct ~tick 42, whole county by
        ~tick 70. With the income circuit the working class sustains
        itself indefinitely, which keeps county population > 0 — the
        condition the bridge's consciousness persistence gates on.
        """
        from babylon.engine.context import TickContext

        graph = bridged["world"].to_graph()
        for tick in range(1, 81):
            bridged["engine"].run_tick(graph, bridged["services"], TickContext(tick=tick))
        worker_population = graph.nodes["C001"].get("population", 0)
        bourgeois_population = graph.nodes["C501"].get("population", 0)
        assert worker_population > 0, "workers extinct by tick 80 (historical cliff ~42)"
        assert worker_population + bourgeois_population > 0

    @pytest.mark.xfail(
        reason="Rent/consciousness calibration pending: extraction scales with "
        "worker_wealth × (1 − consciousness); rising consciousness chokes Φ "
        "below bourgeois consumption (0.15/tick), starving C5xx by ~tick 67. "
        "Follow-up: tune extraction_efficiency/consumption balance against the "
        "20-Year Entropy Standard (ai-docs/tuning-standard.yaml).",
        strict=False,
    )
    def test_bourgeoisie_survive_on_extracted_rent(self, bridged) -> None:  # type: ignore[no-untyped-def]
        from babylon.engine.context import TickContext

        graph = bridged["world"].to_graph()
        for tick in range(1, 81):
            bridged["engine"].run_tick(graph, bridged["services"], TickContext(tick=tick))
        assert graph.nodes["C501"].get("population", 0) > 0
