"""Contract tests for :func:`babylon.projection.tick_summary.build_tick_summary_kwargs`.

Port of ``web/game/engine_bridge.py::_build_tick_summary`` (T5 Unit U2, the
same dormant-construct pattern T3 closed for field-state): same field
semantics, no redesign. The market-axis and county-series-aggregate cases
below reuse the EXACT golden values from
``tests/unit/web/test_engine_bridge.py``'s ``TestBuildTickSummaryMarketAxis``
/ ``TestBuildTickSummarySeriesAggregates`` — the ported logic is checked
against the SAME numbers, not independently re-derived ones.
"""

from __future__ import annotations

import pytest

from babylon.engine.factories import create_proletariat
from babylon.kernel.event_bus import Event
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.organization import CivilSocietyOrg
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import IdeologicalProfile
from babylon.models.enums import ClassCharacter, EdgeType, EventType, ServiceType
from babylon.models.enums.topology import NodeType
from babylon.models.market import MarketState
from babylon.models.world_state import WorldState
from babylon.projection.tick_summary import build_tick_summary_kwargs
from babylon.topology import BabylonGraph

_ALWAYS_NULL_KEYS = (
    "year",
    "total_c",
    "total_v",
    "total_s",
    "exploitation_rate",
    "profit_rate",
    "co_optive_edge_count",
    "conservation_check",
)


class TestAlwaysNullColumns:
    """No engine system computes these yet — the ported source's own honest gap."""

    def test_never_fabricated(self) -> None:
        summary = build_tick_summary_kwargs(WorldState(tick=1))
        for key in _ALWAYS_NULL_KEYS:
            assert summary[key] is None, key


class TestImperialRent:
    def test_reads_the_economy_pool(self) -> None:
        world = WorldState(tick=5, economy=GlobalEconomy(imperial_rent_pool=1.25))
        summary = build_tick_summary_kwargs(world)
        assert summary["imperial_rent"] == pytest.approx(1.25)


class TestAvgConsciousness:
    def test_none_with_no_entities(self) -> None:
        summary = build_tick_summary_kwargs(WorldState(tick=1))
        assert summary["avg_consciousness"] is None

    def test_averages_class_consciousness_across_entities(self) -> None:
        e1 = create_proletariat(
            id="C001",
            ideology=IdeologicalProfile(class_consciousness=0.8, national_identity=0.2),
        )
        e2 = create_proletariat(
            id="C002",
            ideology=IdeologicalProfile(class_consciousness=0.4, national_identity=0.5),
        )
        world = WorldState(tick=1, entities={"C001": e1, "C002": e2})
        summary = build_tick_summary_kwargs(world)
        assert summary["avg_consciousness"] == pytest.approx(0.6)


class TestEdgeCounts:
    def test_counts_solidarity_and_exploitation_edges_only(self) -> None:
        world = WorldState(
            tick=1,
            relationships=[
                Relationship(source_id="C001", target_id="C002", edge_type=EdgeType.SOLIDARITY),
                Relationship(source_id="C001", target_id="C003", edge_type=EdgeType.SOLIDARITY),
                Relationship(source_id="C002", target_id="C003", edge_type=EdgeType.EXPLOITATION),
                Relationship(source_id="C002", target_id="C001", edge_type=EdgeType.WAGES),
            ],
        )
        summary = build_tick_summary_kwargs(world)
        assert summary["solidarity_edge_count"] == 2
        assert summary["antagonistic_edge_count"] == 1


class TestOrgCounts:
    @staticmethod
    def _org(org_id: str) -> CivilSocietyOrg:
        return CivilSocietyOrg(
            id=org_id,
            name=org_id,
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
        )

    def test_org_count_and_player_org_count(self) -> None:
        world = WorldState(
            tick=1,
            organizations={"ORG1": self._org("ORG1"), "ORG2": self._org("ORG2")},
            player_org_id="ORG2",
        )
        summary = build_tick_summary_kwargs(world)
        assert summary["org_count"] == 2
        assert summary["player_org_count"] == 1

    def test_player_org_count_zero_with_no_player_org_set(self) -> None:
        world = WorldState(tick=1, organizations={"ORG1": self._org("ORG1")})
        summary = build_tick_summary_kwargs(world)
        assert summary["org_count"] == 1
        assert summary["player_org_count"] == 0


class TestEventCounts:
    """REVIEW FIX (T5 U2): counts the ``events=`` kernel bus history, NEVER
    ``WorldState.events`` — ``WorldState.from_graph()`` never restamps
    ``graph.graph['events']`` per tick, so on the real Archive path
    ``world.events`` is always ``[]`` and these two columns would silently
    fabricate a ``0`` (Constitution III.11) instead of reporting the truth.
    """

    def test_counts_uprising_and_repression_bus_events_only(self) -> None:
        events = [
            Event(type=EventType.UPRISING, tick=1, payload={}),
            Event(type=EventType.UPRISING, tick=1, payload={}),
            Event(type=EventType.STATE_REPRESSION, tick=1, payload={}),
            Event(type=EventType.LIFECYCLE_TRANSITION, tick=1, payload={}),
        ]
        summary = build_tick_summary_kwargs(WorldState(tick=1), events=events)
        assert summary["uprising_count"] == 2
        assert summary["repression_count"] == 1

    def test_world_events_are_never_read_for_these_counts(self) -> None:
        """A populated ``world.events`` must NOT leak into the count when a
        real ``events=`` bus history is also supplied — the two counts come
        from ONE source, never a union of both."""
        from babylon.models.events import SimulationEvent

        world = WorldState(
            tick=1,
            events=[
                SimulationEvent(event_type=EventType.UPRISING, tick=1),
                SimulationEvent(event_type=EventType.STATE_REPRESSION, tick=1),
            ],
        )
        summary = build_tick_summary_kwargs(
            world, events=[Event(type=EventType.UPRISING, tick=1, payload={})]
        )
        assert summary["uprising_count"] == 1
        assert summary["repression_count"] == 0

    def test_no_events_threaded_is_honest_null_not_zero(self) -> None:
        summary = build_tick_summary_kwargs(WorldState(tick=1))
        assert summary["uprising_count"] is None
        assert summary["repression_count"] is None


class TestMarketAxis:
    """Golden parity with ``TestBuildTickSummaryMarketAxis`` (web bridge)."""

    def test_market_axis_flows_into_summary_columns(self) -> None:
        world = WorldState(
            tick=3,
            market=MarketState(
                price_log=0.25,
                price_velocity=0.0,
                fictitious_log=-0.1,
                fictitious_velocity=0.0,
                surplus_ema=1.0,
                value_ema=4.0,
                tick=3,
            ),
        )
        summary = build_tick_summary_kwargs(world)
        assert summary["price_log"] == pytest.approx(0.25)
        assert summary["fictitious_log"] == pytest.approx(-0.1)
        assert summary["market_corrections"] == 0  # ledger present with the axis

    def test_correction_ledger_flows_into_summary(self) -> None:
        world = WorldState(
            tick=12,
            market=MarketState(
                price_log=0.1,
                price_velocity=0.0,
                fictitious_log=0.2,
                fictitious_velocity=0.0,
                surplus_ema=1.0,
                value_ema=4.0,
                tick=12,
                corrections=2,
                last_correction_tick=11,
            ),
        )
        summary = build_tick_summary_kwargs(world)
        assert summary["market_corrections"] == 2

    def test_absent_axis_is_honest_null(self) -> None:
        summary = build_tick_summary_kwargs(WorldState(tick=1))
        assert summary["price_log"] is None
        assert summary["fictitious_log"] is None
        assert summary["market_corrections"] is None


class TestCountySeriesAggregates:
    """Golden parity with ``TestBuildTickSummarySeriesAggregates`` (web bridge)."""

    _SERIES_KEYS = (
        "crisis_pop_share",
        "bifurcation_score_mean",
        "wage_compression_mean",
        "capital_stock_total",
        "unemployment_rate_mean",
    )

    @staticmethod
    def _graph_with_two_counties() -> BabylonGraph:
        graph = BabylonGraph()
        # T1/T2 share one county and carry IDENTICAL county-level stamps —
        # they must count ONCE (the _county_flow_snapshot N-fold-inflation
        # hazard), never once per territory.
        graph.add_node(
            "T1",
            NodeType.TERRITORY,
            county_fips="26163",
            population=1_000_000,
            tick_crisis_phase="deep",
            tick_bifurcation_score=-0.5,
            tick_wage_compression=0.2,
            tick_capital_stock=1e9,
            tick_unemployment_rate=0.10,
        )
        graph.add_node(
            "T2",
            NodeType.TERRITORY,
            county_fips="26163",
            population=500_000,
            tick_crisis_phase="deep",
            tick_bifurcation_score=-0.5,
            tick_wage_compression=0.2,
            tick_capital_stock=1e9,
            tick_unemployment_rate=0.10,
        )
        graph.add_node(
            "T3",
            NodeType.TERRITORY,
            county_fips="26125",
            population=500_000,
            tick_crisis_phase="normal",
            tick_bifurcation_score=0.3,
            tick_wage_compression=0.0,
            tick_capital_stock=2e9,
            tick_unemployment_rate=0.05,
        )
        return graph

    def test_aggregates_are_county_deduped_and_population_weighted(self) -> None:
        summary = build_tick_summary_kwargs(
            WorldState(tick=52), graph=self._graph_with_two_counties()
        )

        # Wayne pop 1.5M (deep) vs 26125 pop 0.5M (normal): 1.5/2.0.
        assert summary["crisis_pop_share"] == pytest.approx(0.75)
        # Weighted over COUNTIES: (-0.5 * 1.5e6 + 0.3 * 0.5e6) / 2e6.
        assert summary["bifurcation_score_mean"] == pytest.approx(-0.3)
        assert summary["wage_compression_mean"] == pytest.approx(0.15)
        # Extensive sum, ONE term per county: 1e9 + 2e9 — never 1e9*2 + 2e9.
        assert summary["capital_stock_total"] == pytest.approx(3e9)
        assert summary["unemployment_rate_mean"] == pytest.approx(0.0875)

    def test_no_graph_or_no_boundary_yet_is_honest_null(self) -> None:
        no_graph = build_tick_summary_kwargs(WorldState(tick=1))
        bare_graph = BabylonGraph()
        bare_graph.add_node("T1", NodeType.TERRITORY, county_fips="26163", population=10)
        pre_boundary = build_tick_summary_kwargs(WorldState(tick=1), graph=bare_graph)

        for key in self._SERIES_KEYS:
            assert no_graph[key] is None, f"{key} must be NULL without a graph"
            assert pre_boundary[key] is None, f"{key} must be NULL before the first boundary"


class TestDeterminism:
    """Identical inputs yield identical kwargs dicts."""

    def test_double_call_is_identical(self) -> None:
        world = WorldState(
            tick=1,
            economy=GlobalEconomy(imperial_rent_pool=2.0),
            relationships=[
                Relationship(source_id="C001", target_id="C002", edge_type=EdgeType.SOLIDARITY),
            ],
        )
        graph = TestCountySeriesAggregates._graph_with_two_counties()

        first = build_tick_summary_kwargs(world, graph=graph)
        second = build_tick_summary_kwargs(world, graph=graph)

        assert first == second
