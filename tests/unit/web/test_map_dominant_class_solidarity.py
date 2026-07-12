"""Unit tests for the two additive ``/map/`` properties (spec-113 Lane D):
``dominant_class`` and ``solidarity_index``.

Covers the graph-walk helpers, ``_hex_state_row``/``_hex_feature_properties``
threading, ``_aggregate_hex_features`` county-zoom aggregation (numeric
weighted mean for ``solidarity_index``, population-weighted mode for the
categorical ``dominant_class``), the ``map_contract.py`` contract, and
``StubEngineBridge`` parity.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph_with_two_tenants(t1_pop: int = 100, t2_pop: int = 50) -> BabylonGraph:
    """T1 tenanted by C1 (proletariat, t1_pop) and C2 (bourgeoisie, t2_pop)."""
    graph = BabylonGraph()
    graph.add_node("C1", node_type="social_class", role="proletariat", population=t1_pop)
    graph.add_node("C2", node_type="social_class", role="bourgeoisie", population=t2_pop)
    graph.add_node("T1", node_type="territory")
    graph.add_edge("C1", "T1", edge_type="tenancy")
    graph.add_edge("C2", "T1", edge_type="tenancy")
    return graph


class TestTenancyMembersByTerritory:
    def test_groups_social_class_members_by_target_territory(self) -> None:
        from game.engine_bridge import _tenancy_members_by_territory

        graph = _graph_with_two_tenants()
        members = _tenancy_members_by_territory(graph)

        assert members == {"T1": ["C1", "C2"]}

    def test_territory_with_no_tenancy_edges_is_absent(self) -> None:
        from game.engine_bridge import _tenancy_members_by_territory

        graph = BabylonGraph()
        graph.add_node("T1", node_type="territory")
        members = _tenancy_members_by_territory(graph)

        assert members == {}

    def test_non_social_class_tenants_are_excluded(self) -> None:
        """Only social_class nodes count — e.g. an org PRESENCE edge (a
        different EdgeType) must never be mistaken for TENANCY."""
        from game.engine_bridge import _tenancy_members_by_territory

        graph = BabylonGraph()
        graph.add_node("O1", node_type="organization")
        graph.add_node("T1", node_type="territory")
        graph.add_edge("O1", "T1", edge_type="tenancy")  # malformed data, still real-world-possible
        graph.nodes["O1"]["_node_type"] = "organization"
        members = _tenancy_members_by_territory(graph)

        assert members == {}


class TestDominantClassByTerritory:
    def test_higher_population_role_wins(self) -> None:
        from game.engine_bridge import _dominant_class_by_territory, _tenancy_members_by_territory

        graph = _graph_with_two_tenants(t1_pop=100, t2_pop=50)
        members = _tenancy_members_by_territory(graph)
        dominant = _dominant_class_by_territory(graph, members)

        assert dominant == {"T1": "proletariat"}

    def test_tie_breaks_by_role_name_deterministically(self) -> None:
        from game.engine_bridge import _dominant_class_by_territory, _tenancy_members_by_territory

        graph = _graph_with_two_tenants(t1_pop=100, t2_pop=100)
        members = _tenancy_members_by_territory(graph)
        dominant = _dominant_class_by_territory(graph, members)

        # Equal population -> max((pop, role)) picks the lexicographically
        # greatest role name ("proletariat" > "bourgeoisie") — deterministic,
        # not population-driven, for this tie.
        assert dominant == {"T1": "proletariat"}

    def test_member_with_no_role_is_ignored(self) -> None:
        from game.engine_bridge import _dominant_class_by_territory

        graph = BabylonGraph()
        graph.add_node("C1", node_type="social_class", population=10)  # no role
        graph.add_node("T1", node_type="territory")
        graph.add_edge("C1", "T1", edge_type="tenancy")
        members = {"T1": ["C1"]}

        dominant = _dominant_class_by_territory(graph, members)

        assert dominant == {}


class TestSolidarityIndexByTerritory:
    def test_mean_incident_solidarity_edges_per_tenant(self) -> None:
        from game.engine_bridge import _solidarity_index_by_territory

        graph = _graph_with_two_tenants()
        graph.add_edge("C1", "C2", edge_type="solidarity", solidarity_strength=0.5)
        members = {"T1": ["C1", "C2"]}

        index = _solidarity_index_by_territory(graph, members)

        # Each of C1/C2 has exactly 1 incident SOLIDARITY edge -> mean 1.0.
        assert index == {"T1": 1.0}

    def test_zero_solidarity_edges_is_a_real_zero_not_missing(self) -> None:
        from game.engine_bridge import _solidarity_index_by_territory

        graph = _graph_with_two_tenants()
        members = {"T1": ["C1", "C2"]}

        index = _solidarity_index_by_territory(graph, members)

        assert index == {"T1": 0.0}

    def test_territory_absent_from_tenancy_members_is_absent_here_too(self) -> None:
        from game.engine_bridge import _solidarity_index_by_territory

        graph = _graph_with_two_tenants()
        index = _solidarity_index_by_territory(graph, {})

        assert index == {}


class TestHexStateRowNewFields:
    def test_dominant_class_written_when_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163"},
            dominant_class="proletariat",
        )
        assert row is not None
        assert row["dominant_class"] == "proletariat"

    def test_dominant_class_key_absent_when_not_provided(self) -> None:
        """Matches every other unset column: absent from the dict entirely
        (Django model default takes over), not an explicit None."""
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(), 3, {"h3_index": "872a30d8affffff", "county_fips": "26163"}
        )
        assert row is not None
        assert "dominant_class" not in row

    def test_solidarity_index_written_into_attributes_when_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163"},
            solidarity_index=1.25,
        )
        assert row is not None
        assert row["attributes"]["solidarity_index"] == pytest.approx(1.25)

    def test_solidarity_index_absent_from_attributes_when_not_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(), 3, {"h3_index": "872a30d8affffff", "county_fips": "26163"}
        )
        assert row is not None
        assert "solidarity_index" not in row["attributes"]


def _hex_row_stub(
    *,
    h3_index: str = "h1",
    county_fips: str = "26163",
    pop_total: int = 1000,
    dominant_class: str | None = "proletariat",
    solidarity_index: float | None = 0.5,
) -> Any:
    return SimpleNamespace(
        h3_index=h3_index,
        county_fips=county_fips,
        county_name="Wayne",
        bea_ea_code=None,
        msa_code=None,
        profit_rate=None,
        exploitation_rate=None,
        occ=None,
        imperial_rent=None,
        heat=0.1,
        org_count=0,
        dominant_class=dominant_class,
        pop_total=pop_total,
        attributes=({"solidarity_index": solidarity_index} if solidarity_index is not None else {}),
    )


class TestHexFeaturePropertiesSolidarityIndex:
    def test_solidarity_index_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(solidarity_index=0.77))
        assert props["solidarity_index"] == pytest.approx(0.77)

    def test_missing_solidarity_index_is_none_not_zero(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(solidarity_index=None))
        assert props["solidarity_index"] is None

    def test_dominant_class_passthrough(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(dominant_class="core_bourgeoisie"))
        assert props["dominant_class"] == "core_bourgeoisie"


class TestAggregateHexFeaturesNewProperties:
    def test_solidarity_index_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, solidarity_index=0.4),
            _hex_row_stub(h3_index="h1b", pop_total=1000, solidarity_index=0.8),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        assert features[0]["properties"]["solidarity_index"] == pytest.approx(0.6)

    def test_solidarity_index_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", solidarity_index=None),
            _hex_row_stub(h3_index="h1b", solidarity_index=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["solidarity_index"] is None

    def test_solidarity_index_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", solidarity_index=0.9),
            _hex_row_stub(h3_index="h1b", solidarity_index=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["solidarity_index"] == pytest.approx(0.9)

    def test_dominant_class_population_weighted_mode(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, dominant_class="proletariat"),
            _hex_row_stub(h3_index="h1b", pop_total=1000, dominant_class="proletariat"),
            _hex_row_stub(h3_index="h1c", pop_total=500, dominant_class="core_bourgeoisie"),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        assert features[0]["properties"]["dominant_class"] == "proletariat"

    def test_dominant_class_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", dominant_class=None),
            _hex_row_stub(h3_index="h1b", dominant_class=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["dominant_class"] is None

    def test_every_contract_metric_key_present_including_new_ones(self) -> None:
        from game.engine_bridge import EngineBridge
        from game.map_contract import MAP_METRIC_PROPERTIES

        rows = [_hex_row_stub(h3_index="h1a"), _hex_row_stub(h3_index="h1b")]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        missing = [m for m in MAP_METRIC_PROPERTIES if m not in features[0]["properties"]]
        assert not missing


class TestMapContractIncludesNewProperties:
    def test_dominant_class_and_solidarity_index_are_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "dominant_class" in MAP_METRIC_PROPERTIES
        assert "solidarity_index" in MAP_METRIC_PROPERTIES

    def test_valid_map_layers_derives_from_the_contract(self) -> None:
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)


class TestRealWayneCountyScenario:
    """End-to-end against the real scenario-seeding pipeline (no mocking of
    engine internals) — same pattern as
    ``tests/integration/web/test_map_contract.py``'s
    ``_seeded_wayne_state_and_graph``."""

    def test_every_tenanted_territory_gets_a_real_dominant_class(self) -> None:
        from game.engine_bridge import (
            _build_initial_state_for_scenario,
            _dominant_class_by_territory,
            _tenancy_members_by_territory,
        )

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()

        tenancy_members = _tenancy_members_by_territory(graph)
        dominant = _dominant_class_by_territory(graph, tenancy_members)

        assert tenancy_members, "wayne_county seeds real TENANCY edges"
        assert dominant, "at least one territory gets a real (non-fabricated) dominant_class"
        for territory_id in tenancy_members:
            assert territory_id in dominant

    def test_solidarity_index_is_computable_and_non_negative(self) -> None:
        from game.engine_bridge import (
            _build_initial_state_for_scenario,
            _solidarity_index_by_territory,
            _tenancy_members_by_territory,
        )

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()

        tenancy_members = _tenancy_members_by_territory(graph)
        index = _solidarity_index_by_territory(graph, tenancy_members)

        for territory_id, value in index.items():
            assert territory_id in tenancy_members
            assert value >= 0.0


class TestStubBridgeParity:
    def test_hex_zoom_features_carry_both_new_properties(self) -> None:
        from game.stub_bridge import _make_hex_features

        features = _make_hex_features(tick=0)
        assert features
        for feature in features:
            assert "dominant_class" in feature["properties"]
            assert "solidarity_index" in feature["properties"]

    def test_aggregated_features_carry_both_new_properties(self) -> None:
        from game.stub_bridge import _make_aggregated_features

        features = _make_aggregated_features("county", tick=0)
        assert features
        for feature in features:
            assert "dominant_class" in feature["properties"]
            assert "solidarity_index" in feature["properties"]

    def test_available_metrics_advertises_both(self) -> None:
        from game.stub_bridge import StubEngineBridge

        bridge = StubEngineBridge()
        session_id = bridge.create_game(scenario="wayne_county")
        snapshot = bridge.get_map_snapshot(session_id, zoom="county")

        assert "dominant_class" in snapshot["metadata"]["available_metrics"]
        assert "solidarity_index" in snapshot["metadata"]["available_metrics"]
