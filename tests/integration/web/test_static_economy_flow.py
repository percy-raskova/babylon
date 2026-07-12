"""Spec-109 A7 (owner item 25 pt. 2): the county-level economy moves every tick.

TickDynamicsSystem's annual pipeline previously only touched territory
``tick_``-prefixed state on year boundaries (``tick % 52 == 0``); between
boundaries every county-level economic figure was frozen. This lane adds
per-tick FLOW accrual (``flow_phi_accrued`` / ``flow_wage_accrued``) that
moves every tick, at ``annual_value / WEEKS_PER_YEAR`` — see
``babylon.domain.economics.tick.system.TickDynamicsSystem._accrue_flows``.

Structural finding (verified by reading ``babylon.engine.simulation_engine
.step`` end to end, not inferred): ``EngineBridge.resolve_tick`` advances the
simulation via the module-level ``step(state, ...)`` function, which does a
full ``WorldState.to_graph() -> run_tick() -> WorldState.from_graph()``
round-trip on **every call**, and (at the time A7 landed) passed a **fresh**
``persistent_context={}`` on every call. ``_reconstruct_territory`` drops every
``tick_``/``flow_``-prefixed attr because ``Territory`` has ``extra="forbid"``
and they are not real Territory fields (the b57faee6 tick-52 fix, extended by
this lane). ``_restore_graph_context``/``_save_graph_context`` only thread
``graph.graph["tick_dynamics"]`` (a *graph-level* dict) through
``persistent_context`` — never *territory-node-level* attrs. Net effect at
the time: no territory-node-level ``tick_``/``flow_`` state survived across
two separate ``resolve_tick()`` calls for any web session, and the
``wayne_county`` scenario's territories were hex-only (``county_fips=None``
everywhere), so the county pipeline had nothing to compute even if it had
survived.

**Resolved by owner item 30** (the web half of item 25): ``resolve_tick``
now wires the ``melt``/``gamma`` calculators when a session has
county-resolution territory (:func:`game.engine_bridge
._has_county_resolution_territory` /
:func:`game.engine_bridge._bridge_economics_overrides`), the
``wayne_county`` scenario stamps every one of its 81 territories with the
real Wayne County FIPS at the bridge scenario-build layer
(:func:`game.engine_bridge._seed_wayne_county_fips` — deliberately ALL 81,
not one "designated" territory; see that function's docstring for why),
and :func:`game.engine_bridge._carry_tick_dynamics_flows` re-applies the
territory-node ``tick_``/``flow_`` state that ``step()``'s round-trip would
otherwise strip, by mutating the raw graph directly before
``persist_tick`` (bridge-only — zero ``Territory``/engine changes; the
headless path is untouched, since it never calls this function).
``TestWayneCountyFlowSurvivesWebResolve`` below is the literal acceptance
test this unblocks: a real economic value (``flow_wage_accrued``, surfaced
via ``get_economy_dashboard``'s ``county_flow`` field) MOVES between two
consecutive ``resolve_tick`` calls, through the full
resolve->persist->hydrate->resolve cycle. ``phi_hour`` (and hence
``flow_phi_accrued``) stays 0.0 — the Spec-057 Leontief imperial-rent
pipeline is unwired in both the headless runner and this bridge, out of
this lane's scope (see ``_bridge_economics_overrides``'s docstring).

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

from babylon.domain.economics.tick.graph_bridge import write_tick_state_to_graph
from babylon.domain.economics.tick.types import (
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

    Wiring ``TickDynamicsSystem``'s two-mode ``step()`` into the default
    engine pipeline, plus owner item 30's calculator wiring + county-FIPS
    scenario seeding, does not crash or otherwise regress a real bridged
    ``wayne_county`` session. (Before owner item 30, this test's docstring
    noted the session's territories were hex-only and this gate could not
    exercise cross-tick flow accrual at all — see
    ``TestWayneCountyFlowSurvivesWebResolve`` below for that coverage now.)
    """

    def test_two_resolves_on_a_wayne_county_session_do_not_crash(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)

        first = bridge.resolve_tick(session_id)
        second = bridge.resolve_tick(session_id)

        assert first is not None
        assert second is not None
        ts = bridge.get_game_timeseries(session_id)
        assert ts["ticks"] == [0, 1, 2]


@pytest.mark.requires_postgres
@pytest.mark.skipif(
    not os.environ.get("POSTGRES_HOST"),
    reason="PostgreSQL not configured (set POSTGRES_HOST)",
)
class TestWayneCountyFlowSurvivesWebResolve:
    """Owner item 30 acceptance gate: a real economic value MOVES between
    two consecutive ``resolve_tick`` calls on a ``wayne_county`` web
    session, through the full resolve->persist->hydrate->resolve cycle —
    the literal G3 target this module's docstring previously reported as
    unreachable.

    Tick 0->1 is a ``TickDynamicsSystem`` year boundary (``tick % 52 ==
    0``): the annual pipeline runs (calculators wired by owner item 30)
    and ``_carry_tick_dynamics_flows`` resets the flow counters to 0.0 —
    the "true-up" half of the binding design. Tick 1->2 is NOT a boundary:
    ``_carry_tick_dynamics_flows`` carries forward the boundary-
    authoritative ``tick_median_wage``/``tick_employment`` from the tick-1
    graph (loaded fresh from Postgres by tick 2's ``hydrate_state``) and
    accrues one ``annual_value / WEEKS_PER_YEAR`` slice.
    """

    def test_wage_flow_moves_between_tick_1_and_tick_2(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)

        first = bridge.resolve_tick(session_id)
        assert first["tick"] == 1
        after_tick_1 = bridge.get_economy_dashboard(session_id)["county_flow"]
        assert after_tick_1["wage_accrued_this_year"] == pytest.approx(0.0)

        second = bridge.resolve_tick(session_id)
        assert second["tick"] == 2
        after_tick_2 = bridge.get_economy_dashboard(session_id)["county_flow"]

        assert after_tick_2["wage_accrued_this_year"] > after_tick_1["wage_accrued_this_year"]

        # Byte-for-byte the same formula as TickDynamicsSystem._accrue_flows,
        # applied to the engine's own bootstrap defaults (median_wage=21.0
        # $/hr, employment=100_000.0 — CountyEconomicState's documented
        # graceful-degradation defaults; Vol I's wage-pressure calculator
        # and the Spec-057 imperial-rent pipeline are both unwired in this
        # bridge, mirroring the headless runner).
        annual_wage = 21.0 * HOURS_PER_YEAR * 100_000.0
        assert after_tick_2["wage_accrued_this_year"] == pytest.approx(annual_wage / WEEKS_PER_YEAR)

        # phi_hour stays 0.0 — the Leontief imperial-rent pipeline is
        # unwired (out of scope; see _bridge_economics_overrides).
        assert after_tick_2["phi_accrued_this_year"] == pytest.approx(0.0)

    def test_flow_keeps_accruing_across_a_third_resolve(self, bridge: object) -> None:
        """Two full slices after tick 3 — the accrual is not a one-shot."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        bridge.resolve_tick(session_id)
        bridge.resolve_tick(session_id)
        third = bridge.resolve_tick(session_id)
        assert third["tick"] == 3

        flow = bridge.get_economy_dashboard(session_id)["county_flow"]
        annual_wage = 21.0 * HOURS_PER_YEAR * 100_000.0
        assert flow["wage_accrued_this_year"] == pytest.approx(2 * annual_wage / WEEKS_PER_YEAR)
