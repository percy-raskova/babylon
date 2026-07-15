"""Wave 2 Round 2 (W2.4): the three new ``/map/`` lenses — ``throughput_position``
(numeric), ``agitation`` (numeric), ``territory_type`` (categorical).

Covers the graph-walk helper (``_agitation_index_by_territory``), the
``_hex_state_row``/``_hex_feature_properties``/``_aggregate_hex_features``
threading (population-weighted MEAN for the two numeric lenses,
population-weighted MODE for the categorical one — owner ruling 4), the
``map_contract.py`` contract, ``get_inspector_hex`` parity, and
``StubEngineBridge`` parity — mirroring
``tests/unit/web/test_map_dominant_class_solidarity.py``'s structure for
spec-113 Lane D.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph_with_two_tenants(
    t1_pop: int = 100,
    t2_pop: int = 50,
    *,
    c1_agitation: float | None = 0.2,
    c2_agitation: float | None = 0.8,
) -> BabylonGraph:
    """T1 tenanted by C1 (proletariat, t1_pop) and C2 (bourgeoisie, t2_pop)."""
    graph = BabylonGraph()
    c1_attrs: dict[str, Any] = {
        "node_type": "social_class",
        "role": "proletariat",
        "population": t1_pop,
    }
    if c1_agitation is not None:
        c1_attrs["ideology"] = {"agitation": c1_agitation}
    c2_attrs: dict[str, Any] = {
        "node_type": "social_class",
        "role": "bourgeoisie",
        "population": t2_pop,
    }
    if c2_agitation is not None:
        c2_attrs["ideology"] = {"agitation": c2_agitation}
    graph.add_node("C1", **c1_attrs)
    graph.add_node("C2", **c2_attrs)
    graph.add_node("T1", node_type="territory")
    graph.add_edge("C1", "T1", edge_type="tenancy")
    graph.add_edge("C2", "T1", edge_type="tenancy")
    return graph


class TestAgitationIndexByTerritory:
    def test_population_weighted_mean_of_agitation(self) -> None:
        from game.engine_bridge import _agitation_index_by_territory, _tenancy_members_by_territory

        # C1: pop=100, agitation=0.2; C2: pop=50, agitation=0.8
        # weighted mean = (100*0.2 + 50*0.8) / 150 = (20 + 40) / 150 = 0.4
        graph = _graph_with_two_tenants(t1_pop=100, t2_pop=50, c1_agitation=0.2, c2_agitation=0.8)
        members = _tenancy_members_by_territory(graph)

        index = _agitation_index_by_territory(graph, members)

        assert index == {"T1": pytest.approx(0.4)}

    def test_real_zero_agitation_is_a_real_zero_not_missing(self) -> None:
        """Owner ruling: agitation is LEGITIMATELY 0.0 at tick 0 in every
        scenario — a real 0.0 weighted mean, never absent/None."""
        from game.engine_bridge import _agitation_index_by_territory, _tenancy_members_by_territory

        graph = _graph_with_two_tenants(c1_agitation=0.0, c2_agitation=0.0)
        members = _tenancy_members_by_territory(graph)

        index = _agitation_index_by_territory(graph, members)

        assert index == {"T1": 0.0}

    def test_member_with_no_ideology_dict_is_excluded_not_zeroed(self) -> None:
        from game.engine_bridge import _agitation_index_by_territory

        graph = BabylonGraph()
        graph.add_node("C1", node_type="social_class", population=100)  # no ideology at all
        graph.add_node("T1", node_type="territory")
        graph.add_edge("C1", "T1", edge_type="tenancy")
        members = {"T1": ["C1"]}

        index = _agitation_index_by_territory(graph, members)

        assert index == {}

    def test_territory_absent_from_tenancy_members_is_absent_here_too(self) -> None:
        from game.engine_bridge import _agitation_index_by_territory

        graph = _graph_with_two_tenants()
        index = _agitation_index_by_territory(graph, {})

        assert index == {}

    def test_zero_total_population_is_absent_not_a_divide_by_zero(self) -> None:
        from game.engine_bridge import _agitation_index_by_territory

        graph = BabylonGraph()
        graph.add_node(
            "C1",
            node_type="social_class",
            role="proletariat",
            population=0,
            ideology={"agitation": 0.5},
        )
        graph.add_node("T1", node_type="territory")
        graph.add_edge("C1", "T1", edge_type="tenancy")
        members = {"T1": ["C1"]}

        index = _agitation_index_by_territory(graph, members)

        assert index == {}


class TestHexStateRowNewLenses:
    def test_agitation_written_into_attributes_when_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163"},
            agitation=0.65,
        )
        assert row is not None
        assert row["attributes"]["agitation"] == pytest.approx(0.65)

    def test_agitation_absent_from_attributes_when_not_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(), 3, {"h3_index": "872a30d8affffff", "county_fips": "26163"}
        )
        assert row is not None
        assert "agitation" not in row["attributes"]

    def test_throughput_position_read_off_territory_dict_into_attributes(self) -> None:
        """Unlike agitation, throughput_position is NOT a separate caller
        arg — it rides the territory dict's own key (like profit_rate/occ),
        set by _serialize_territory off the tick_throughput_position graph attr."""
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "throughput_position": 0.85,
            },
        )
        assert row is not None
        assert row["attributes"]["throughput_position"] == pytest.approx(0.85)

    def test_throughput_position_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "throughput_position": None},
        )
        assert row is not None
        assert "throughput_position" not in row["attributes"]

    def test_territory_type_read_off_territory_dict_into_attributes(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "territory_type": "periphery",
            },
        )
        assert row is not None
        assert row["attributes"]["territory_type"] == "periphery"

    def test_territory_type_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "territory_type": None},
        )
        assert row is not None
        assert "territory_type" not in row["attributes"]


def _hex_row_stub(
    *,
    h3_index: str = "h1",
    county_fips: str = "26163",
    pop_total: int = 1000,
    throughput_position: float | None = 0.9,
    agitation: float | None = 0.3,
    territory_type: str | None = "core",
) -> Any:
    attributes: dict[str, Any] = {}
    if throughput_position is not None:
        attributes["throughput_position"] = throughput_position
    if agitation is not None:
        attributes["agitation"] = agitation
    if territory_type is not None:
        attributes["territory_type"] = territory_type
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
        dominant_class=None,
        pop_total=pop_total,
        attributes=attributes,
    )


class TestHexFeaturePropertiesNewLenses:
    def test_throughput_position_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(throughput_position=0.77))
        assert props["throughput_position"] == pytest.approx(0.77)

    def test_missing_throughput_position_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(throughput_position=None))
        assert props["throughput_position"] is None

    def test_agitation_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(agitation=0.44))
        assert props["agitation"] == pytest.approx(0.44)

    def test_territory_type_passthrough(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(territory_type="penal_colony"))
        assert props["territory_type"] == "penal_colony"

    def test_missing_territory_type_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(territory_type=None))
        assert props["territory_type"] is None


class TestAggregateHexFeaturesNewLenses:
    def test_throughput_position_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, throughput_position=0.4),
            _hex_row_stub(h3_index="h1b", pop_total=1000, throughput_position=0.8),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        assert features[0]["properties"]["throughput_position"] == pytest.approx(0.6)

    def test_throughput_position_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", throughput_position=None),
            _hex_row_stub(h3_index="h1b", throughput_position=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["throughput_position"] is None

    def test_throughput_position_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", throughput_position=0.9),
            _hex_row_stub(h3_index="h1b", throughput_position=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["throughput_position"] == pytest.approx(0.9)

    def test_agitation_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, agitation=0.2),
            _hex_row_stub(h3_index="h1b", pop_total=3000, agitation=1.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (1000*0.2 + 3000*1.0) / 4000 = (200 + 3000) / 4000 = 0.8
        assert features[0]["properties"]["agitation"] == pytest.approx(0.8)

    def test_agitation_real_zero_across_all_hexes_is_a_real_zero(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", agitation=0.0),
            _hex_row_stub(h3_index="h1b", agitation=0.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["agitation"] == 0.0

    def test_territory_type_population_weighted_mode(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, territory_type="core"),
            _hex_row_stub(h3_index="h1b", pop_total=1000, territory_type="core"),
            _hex_row_stub(h3_index="h1c", pop_total=500, territory_type="periphery"),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        assert features[0]["properties"]["territory_type"] == "core"

    def test_territory_type_tie_breaks_lexicographically_greatest(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, territory_type="core"),
            _hex_row_stub(h3_index="h1b", pop_total=1000, territory_type="periphery"),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # Equal population -> max((pop, value)) picks the lexicographically
        # greatest value ("periphery" > "core") — deterministic, matching
        # dominant_class's own tie-break convention.
        assert features[0]["properties"]["territory_type"] == "periphery"

    def test_territory_type_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", territory_type=None),
            _hex_row_stub(h3_index="h1b", territory_type=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["territory_type"] is None


class TestMapContractIncludesWave2Lenses:
    def test_all_three_new_lenses_are_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "throughput_position" in MAP_METRIC_PROPERTIES
        assert "agitation" in MAP_METRIC_PROPERTIES
        assert "territory_type" in MAP_METRIC_PROPERTIES

    def test_valid_map_layers_derives_from_the_contract(self) -> None:
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)


class TestGetInspectorHexWave2Lenses:
    """Real wayne_county tick-0 graph — no mocking of engine internals,
    matching TestGetInspectorHex's own established pattern."""

    def _wayne_bridge(self) -> tuple[Any, Any]:
        from unittest.mock import MagicMock

        from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        return EngineBridge(mock_persistence), graph

    def test_throughput_position_is_none_before_any_year_boundary(self) -> None:
        from game.engine_bridge import _build_initial_state_for_scenario

        bridge, _graph = self._wayne_bridge()
        state = _build_initial_state_for_scenario("wayne_county")
        territory = next(iter(state.territories.values()))

        result = bridge.get_inspector_hex(uuid.uuid4(), territory.h3_index)

        assert result["throughput_position"] is None

    def test_agitation_is_a_real_value_not_missing(self) -> None:
        from game.engine_bridge import _build_initial_state_for_scenario

        bridge, _graph = self._wayne_bridge()
        state = _build_initial_state_for_scenario("wayne_county")
        territory = next(iter(state.territories.values()))

        result = bridge.get_inspector_hex(uuid.uuid4(), territory.h3_index)

        # wayne_county seeds real TENANCY-linked social_class members with a
        # real (tick-0, zero) ideology.agitation — a real 0.0, not None.
        assert result["agitation"] is not None
        assert result["agitation"] >= 0.0

    def test_territory_type_is_a_real_enum_value(self) -> None:
        from babylon.models.enums.territory import TerritoryType
        from game.engine_bridge import _build_initial_state_for_scenario

        bridge, _graph = self._wayne_bridge()
        state = _build_initial_state_for_scenario("wayne_county")
        territory = next(iter(state.territories.values()))

        result = bridge.get_inspector_hex(uuid.uuid4(), territory.h3_index)

        assert result["territory_type"] in {t.value for t in TerritoryType}


class TestStubBridgeParityWave2Lenses:
    def test_hex_zoom_features_carry_all_three_new_properties(self) -> None:
        from game.stub_bridge import _make_hex_features

        features = _make_hex_features(tick=0)
        assert features
        for feature in features:
            assert "throughput_position" in feature["properties"]
            assert "agitation" in feature["properties"]
            assert "territory_type" in feature["properties"]

    def test_aggregated_features_carry_all_three_new_properties(self) -> None:
        from game.stub_bridge import _make_aggregated_features

        features = _make_aggregated_features("county", tick=0)
        assert features
        for feature in features:
            assert "throughput_position" in feature["properties"]
            assert "agitation" in feature["properties"]
            assert "territory_type" in feature["properties"]

    def test_stub_territory_type_never_uses_the_legacy_vocabulary(self) -> None:
        """Do NOT conflate stub_bridge.py's legacy URBAN/SUBURBAN/PERIURBAN
        (_make_territories(), an unrelated field) with the real TerritoryType
        enum this map lens must use."""
        from babylon.models.enums.territory import TerritoryType
        from game.stub_bridge import _make_hex_features

        legacy_values = {"URBAN", "SUBURBAN", "PERIURBAN"}
        real_values = {t.value for t in TerritoryType}
        features = _make_hex_features(tick=0)

        for feature in features:
            value = feature["properties"]["territory_type"]
            assert value not in legacy_values
            assert value in real_values

    def test_available_metrics_advertises_all_three(self) -> None:
        from game.stub_bridge import StubEngineBridge

        bridge = StubEngineBridge()
        session_id = bridge.create_game(scenario="wayne_county")
        snapshot = bridge.get_map_snapshot(session_id, zoom="county")

        assert "throughput_position" in snapshot["metadata"]["available_metrics"]
        assert "agitation" in snapshot["metadata"]["available_metrics"]
        assert "territory_type" in snapshot["metadata"]["available_metrics"]
