"""Audit Wave 4 straggler (task #76): the ``centrality`` ``/map/`` lens.

The audit's Wave 4 core landed ``get_org_network``'s per-node
``centrality``/``percolation_ratio`` at NETWORK scope (AW4-R1, commit
c312e62d) but left the map choropleth dark — "Native graph algorithms
surfaced for gameplay" / "Topology legibility" wanted a "critical_nodes"
MAP lens, not just the Network takeover's node-link view.

Verified reality (2026-07-15) before writing this: the org network's typed
contract carries ORGANIZATION/INSTITUTION/TERRITORY nodes only (no
social_class) — territory nodes ARE literal nodes in that network (via
PRESENCE/HOUSES edges), so they carry their own real degree-centrality
reading directly, no TENANCY projection needed. Confirmed non-degenerate on
``wayne_county`` (its only shipped scenario with real ``Organization`` rows,
``_legacy_wayne.py``): 3 PRESENCE-linked territories split 0.25/0.5/0.5
degree. Every OTHER shipped scenario (``us``/``high_tension``/
``imperial_circuit``/``labor_aristocracy``/``two_node``) seeds ZERO
organizations, so the lens is honestly empty everywhere else today — the
same "sparse, TENANCY/PRESENCE-gated" shape ``dominant_class``/
``solidarity_index`` already have.

Mirrors ``test_wave2_map_lenses.py``'s structure (the W2.4
throughput_position/agitation/territory_type precedent this straggler
explicitly follows) — graph-walk helper, ``_hex_state_row``/
``_hex_feature_properties``/``_aggregate_hex_features`` threading,
``map_contract.py``, ``StubEngineBridge`` parity.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _wayne_bridge() -> tuple[Any, Any]:
    """Real wayne_county scenario graph — organizations ORG001/ORG002,
    real territories (mirrors test_org_network.py's own helper)."""
    from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    graph = state.to_graph()
    mock_persistence = MagicMock()
    mock_persistence.hydrate_graph.return_value = graph
    return EngineBridge(mock_persistence), graph


class TestCentralityByTerritory:
    def test_non_degenerate_on_real_wayne_county_topology(self) -> None:
        """Verified finding: the hub territory both orgs share reads a
        distinctly higher degree than the one only ORG002 touches — a real
        structural signal, not a decorative constant."""
        from game.engine_bridge import _build_initial_state_for_scenario, _centrality_by_territory

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()

        index = _centrality_by_territory(state, graph)

        assert len(index) == 3  # exactly the 3 PRESENCE-linked territories
        assert len(set(index.values())) > 1  # non-degenerate — not a flat constant
        assert all(0.0 <= v <= 1.0 for v in index.values())

    def test_matches_org_network_endpoints_own_centrality_reading(self) -> None:
        """The map lens and the get_org_network endpoint must agree — same
        underlying _org_network_centrality computation, no drift."""
        from game.engine_bridge import _build_initial_state_for_scenario, _centrality_by_territory

        bridge, graph = _wayne_bridge()
        state = _build_initial_state_for_scenario("wayne_county")

        index = _centrality_by_territory(state, graph)
        org_network = bridge.get_org_network(uuid.uuid4())

        territory_nodes = {n["id"] for n in org_network["nodes"] if n["type"] == "territory"}
        assert set(index) == territory_nodes
        for territory_id in territory_nodes:
            assert index[territory_id] == pytest.approx(
                org_network["centrality"][territory_id]["degree"]
            )

    def test_org_less_scenario_is_honestly_empty(self) -> None:
        """Verified finding: every scenario except wayne_county seeds ZERO
        organizations, so the org network — and this lens — is honestly
        empty, never a fabricated 0.0 for territories with no org presence."""
        from game.engine_bridge import _build_initial_state_for_scenario, _centrality_by_territory

        state = _build_initial_state_for_scenario("wayne_county")
        state = state.model_copy(update={"organizations": {}, "institutions": {}})
        graph = state.to_graph()

        index = _centrality_by_territory(state, graph)

        assert index == {}

    def test_territory_filter_is_not_applied_state_wide_computation(self) -> None:
        """The map lens computes centrality over the WHOLE session's org
        network (unfiltered) so a territory's reading is comparable across
        the entire map — never one request's scoped subgraph."""
        from game.engine_bridge import _build_initial_state_for_scenario, _centrality_by_territory

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()

        index = _centrality_by_territory(state, graph)

        # Both ORG001's and ORG002's territories appear — not just one org's.
        assert len(index) == 3


class TestHexStateRowCentrality:
    def test_centrality_written_into_attributes_when_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163"},
            centrality=0.5,
        )
        assert row is not None
        assert row["attributes"]["centrality"] == pytest.approx(0.5)

    def test_centrality_absent_from_attributes_when_not_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(), 3, {"h3_index": "872a30d8affffff", "county_fips": "26163"}
        )
        assert row is not None
        assert "centrality" not in row["attributes"]


def _hex_row_stub(
    *,
    h3_index: str = "h1",
    county_fips: str = "26163",
    pop_total: int = 1000,
    centrality: float | None = 0.4,
) -> Any:
    attributes: dict[str, Any] = {}
    if centrality is not None:
        attributes["centrality"] = centrality
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


class TestHexFeaturePropertiesCentrality:
    def test_centrality_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(centrality=0.62))
        assert props["centrality"] == pytest.approx(0.62)

    def test_missing_centrality_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(centrality=None))
        assert props["centrality"] is None


class TestAggregateHexFeaturesCentrality:
    def test_centrality_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, centrality=0.2),
            _hex_row_stub(h3_index="h1b", pop_total=3000, centrality=1.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (1000*0.2 + 3000*1.0) / 4000 = (200 + 3000) / 4000 = 0.8
        assert features[0]["properties"]["centrality"] == pytest.approx(0.8)

    def test_centrality_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", centrality=None),
            _hex_row_stub(h3_index="h1b", centrality=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["centrality"] is None

    def test_centrality_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", centrality=0.9),
            _hex_row_stub(h3_index="h1b", centrality=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["centrality"] == pytest.approx(0.9)


class TestMapContractIncludesCentrality:
    def test_centrality_is_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "centrality" in MAP_METRIC_PROPERTIES

    def test_valid_map_layers_derives_from_the_contract(self) -> None:
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)

    def test_centrality_not_in_history_replayable_set(self) -> None:
        """hex_latest is a current-tick-only cache — centrality has no
        append-only historical store, same as agitation/throughput_position."""
        from game.map_contract import MAP_HISTORY_REPLAYABLE_METRICS

        assert "centrality" not in MAP_HISTORY_REPLAYABLE_METRICS


class TestStubBridgeParityCentrality:
    def test_hex_zoom_features_carry_centrality(self) -> None:
        from game.stub_bridge import _make_hex_features

        features = _make_hex_features(tick=0)
        assert features
        for feature in features:
            assert "centrality" in feature["properties"]

    def test_aggregated_features_carry_centrality(self) -> None:
        from game.stub_bridge import _make_aggregated_features

        features = _make_aggregated_features("county", tick=0)
        assert features
        for feature in features:
            assert "centrality" in feature["properties"]

    def test_available_metrics_advertises_centrality(self) -> None:
        from game.stub_bridge import StubEngineBridge

        bridge = StubEngineBridge()
        session_id = bridge.create_game(scenario="wayne_county")
        snapshot = bridge.get_map_snapshot(session_id, zoom="county")

        assert "centrality" in snapshot["metadata"]["available_metrics"]
