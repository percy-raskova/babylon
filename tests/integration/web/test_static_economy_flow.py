"""Spec-109 A7 (owner item 25 pt. 2): the county-level economy moves every tick.

TickDynamicsSystem's annual pipeline previously only touched territory
``tick_``-prefixed state on year boundaries (``tick % 52 == 0``); between
boundaries every county-level economic figure was frozen. This lane adds
per-tick FLOW accrual (``flow_phi_accrued`` / ``flow_wage_accrued``) that
moves every tick, at ``annual_value / WEEKS_PER_YEAR`` — see
``babylon.economics.tick.system.TickDynamicsSystem._accrue_flows``.

Structural finding (verified by reading ``babylon.engine.simulation_engine
.step`` end to end, not inferred): ``EngineBridge.resolve_tick`` advances the
simulation via the module-level ``step(state, ...)`` function, which does a
full ``WorldState.to_graph() -> run_tick() -> WorldState.from_graph()``
round-trip on **every call**, and ``resolve_tick`` passes a **fresh**
``persistent_context={}`` on every call (no caller threads one across
requests — see ``test_full_persistence.py``'s ``bridge.resolve_tick(session_id)``
call sites, no second argument). ``_reconstruct_territory`` drops every
``tick_``/``flow_``-prefixed attr because ``Territory`` has ``extra="forbid"``
and they are not real Territory fields (the b57faee6 tick-52 fix, extended by
this lane). ``_restore_graph_context``/``_save_graph_context`` only thread
``graph.graph["tick_dynamics"]`` (a *graph-level* dict) through
``persistent_context`` — never *territory-node-level* attrs. The net effect:
**no territory-node-level ``tick_``/``flow_`` state survives across two
separate ``resolve_tick()`` calls for any web session today** — a pre-existing
gap in cross-call ``persistent_context`` threading, orthogonal to this lane
and out of its scope to fix (see the worktree's final report `unresolved`).

``TestWayneCountyResolveDoesNotRegress`` proves the real ``EngineBridge``
production path (Postgres, ``wayne_county`` scenario) still resolves cleanly
with A7's change wired into the default system order — a regression-safety
gate, per the bridge-fixture pattern in ``test_full_persistence.py``.

``TestFlowAccrualAcrossConsecutiveTicks`` proves the actual G3 symptom — a
county-level economic value MOVING tick over tick — through the same
persistent-in-memory-graph model the headless runner uses
(``babylon.engine.headless_runner.bridge.WorldStateBridge`` calls
``engine.run_tick(graph, ...)`` directly in a loop, never round-tripping
through ``WorldState`` mid-run), which is the actual live code path where
TickDynamics state persists across ticks.
"""

from __future__ import annotations

import os

import pytest

from babylon.economics.tick.graph_bridge import write_tick_state_to_graph
from babylon.economics.tick.types import (
    ClassDistribution,
    CountyEconomicState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)
from babylon.engine.context import TickContext
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.formulas.constants import HOURS_PER_YEAR, WEEKS_PER_YEAR
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, OperationalProfile, SectorType
from babylon.models.world_state import WorldState

WAYNE_FIPS = "26163"


class TestFlowAccrualAcrossConsecutiveTicks:
    """The real symptom: a county-level economic value moves tick over tick.

    Mirrors the headless runner's actual usage (one persistent in-memory
    graph, ``engine.run_tick`` called directly per tick — see
    ``WorldStateBridge`` / ``.mise.toml``'s ``qa:e2e-regression`` task) rather
    than the web bridge's round-tripping ``step()``, per the structural
    finding in this module's docstring.
    """

    def _wayne_county_state(self) -> WorldState:
        """A minefield-shaped WorldState (worker + owner + territory) with
        the territory carrying real ``county_fips`` — the b57faee6 shape."""
        worker = create_proletariat(id="C000", county_fips=WAYNE_FIPS)
        owner = create_bourgeoisie(id="C001", county_fips=WAYNE_FIPS)
        territory = Territory(
            id="T001",
            name="Wayne County",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
            biocapacity=500.0,
            county_fips=WAYNE_FIPS,
        )
        relationships = [
            Relationship(
                source_id="C000",
                target_id="C001",
                edge_type=EdgeType.EXPLOITATION,
                value_flow=5.0,
                tension=0.4,
            ),
            Relationship(
                source_id="C000",
                target_id="T001",
                edge_type=EdgeType.TENANCY,
            ),
        ]
        return WorldState(
            tick=0,
            entities={"C000": worker, "C001": owner},
            territories={"T001": territory},
            relationships=relationships,
        )

    def _seed_boundary_state(self, graph: object) -> None:
        """Stamp the territory node with boundary-authoritative ``tick_``
        state — as if TickDynamicsSystem's annual pipeline had already run
        once for this county (the realistic post-tick-52 shape a longer
        detroit-tri-county-style run reaches; see the module docstring for
        why a fresh web session can't reach this state within 2 ticks)."""
        dist = ClassDistribution(
            fips=WAYNE_FIPS,
            year=2011,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        county = CountyEconomicState(
            fips=WAYNE_FIPS,
            year=2011,
            capital_stock=1e9,
            throughput_position=0.90,
            supply_chain_depth=2.1,
            unemployment_rate=0.053,
            u6_rate=0.10,
            pter_rate=0.04,
            nilf_rate=0.06,
            median_wage=21.0,
            employment=500_000.0,
            class_distribution=dist,
            phi_hour=3.50,
        )
        params = NationalTickParameters(
            year=2011,
            tau=62.0,
            gamma_basket=0.68,
            gamma_basket_raw=0.68,
            gamma_III=0.33,
            gamma_III_raw=0.33,
            tau_effective=42.16,
            v_reproduction=12.0,
            estimated=True,
        )
        coeff = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
            is_initialized=True,
        )
        state = SimulationTickState(
            year=2011,
            national_params=params,
            county_states={WAYNE_FIPS: county},
            coefficients=coeff,
        )
        write_tick_state_to_graph(graph, state)  # type: ignore[arg-type]

    def test_flow_phi_accrued_moves_between_tick_1_and_tick_2(self) -> None:
        """The G3 symptom: flow_phi_accrued on the Wayne County territory
        node is strictly greater after tick 2 than after tick 1, driven
        through the FULL 26-system default engine pipeline (not just
        TickDynamicsSystem in isolation) on ONE persistent graph object —
        exactly how the headless runner's bridge loop operates."""
        state = self._wayne_county_state()
        graph = state.to_graph()
        self._seed_boundary_state(graph)
        services = ServiceContainer.create()
        engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

        engine.run_tick(graph, services, TickContext(tick=1))
        after_tick_1 = graph.nodes["T001"]["flow_phi_accrued"]

        engine.run_tick(graph, services, TickContext(tick=2))
        after_tick_2 = graph.nodes["T001"]["flow_phi_accrued"]

        assert after_tick_1 > 0
        assert after_tick_2 > after_tick_1

        annual_phi = 3.50 * HOURS_PER_YEAR
        assert after_tick_1 == pytest.approx(annual_phi / WEEKS_PER_YEAR)
        assert after_tick_2 == pytest.approx(2 * annual_phi / WEEKS_PER_YEAR)

    def test_boundary_authoritative_level_stays_flat_across_the_same_ticks(self) -> None:
        """Companion assertion: capital_stock (a LEVEL) does NOT move across
        the same two ticks — only FLOW quantities do (binding design)."""
        state = self._wayne_county_state()
        graph = state.to_graph()
        self._seed_boundary_state(graph)
        services = ServiceContainer.create()
        engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

        engine.run_tick(graph, services, TickContext(tick=1))
        k_after_1 = graph.nodes["T001"]["tick_capital_stock"]
        engine.run_tick(graph, services, TickContext(tick=2))
        k_after_2 = graph.nodes["T001"]["tick_capital_stock"]

        assert k_after_1 == pytest.approx(k_after_2)
        assert k_after_1 == pytest.approx(1e9)


@pytest.fixture
def _django_setup() -> None:
    """Ensure Django is configured before running tests."""
    import django
    from django.conf import settings

    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babylon_web.settings.development")
        django.setup()


@pytest.fixture
def bridge(_django_setup: None) -> object:
    """Create an EngineBridge connected to PostgreSQL (test_full_persistence.py pattern)."""
    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    conninfo = (
        f"dbname={os.environ.get('POSTGRES_DB', 'babylon_test')} "
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"user={os.environ.get('POSTGRES_USER', 'babylon')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'babylon')}"
    )
    pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=2, open=True)
    persistence = PostgresRuntime(pool)

    from game.engine_bridge import EngineBridge

    return EngineBridge(persistence)


@pytest.mark.requires_postgres
@pytest.mark.skipif(
    not os.environ.get("POSTGRES_HOST"),
    reason="PostgreSQL not configured (set POSTGRES_HOST)",
)
class TestWayneCountyResolveDoesNotRegress:
    """Regression-safety gate through the REAL production path.

    Per this module's structural finding, a fresh ``wayne_county`` web
    session's territories are hex-resolution (no real ``county_fips``) and
    ``resolve_tick`` round-trips through Pydantic ``Territory`` on every
    call — so this does not (and structurally cannot, today) exercise
    cross-tick flow accrual. What it DOES prove: wiring
    ``TickDynamicsSystem``'s new two-mode ``step()`` into the default engine
    pipeline does not crash or otherwise regress a real bridged session.
    """

    def test_two_resolves_on_a_wayne_county_session_do_not_crash(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)

        first = bridge.resolve_tick(session_id)
        second = bridge.resolve_tick(session_id)

        assert first is not None
        assert second is not None
        ts = bridge.get_game_timeseries(session_id)
        assert ts["ticks"] == [0, 1, 2]
