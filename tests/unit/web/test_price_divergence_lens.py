"""Program 23 / ADR078: the ``price_divergence`` ``/map/`` lens.

The territory's county-level log price-to-value ratio (``price_log``),
written onto TERRITORY graph nodes by ``MarketScissorsSystem`` (engine
position 17.8, ``_project_price_divergence``) — a NATIVE per-territory
graph attr, same shape as ``wage_pressure``/``mass_receptivity``, no
TENANCY-projection aggregation of its own. UNLIKE every other numeric lens
in the family, it is SIGNED (roughly ``[-2.0, 2.0]``, hard-clamped by
``max_abs_log``): 0 = prices at values, positive = price above value (the
scissors open upward — a bubble), negative = price below value.

Mirrors ``tests/unit/web/test_aw4_centrality_lens.py``'s single-metric
structure (the ``centrality`` precedent) rather than
``test_reserve_army_dispossession_lenses.py``'s paired one, since
``price_divergence`` is a single lens. Covers: the bridge-side round-trip
carry (``_carry_price_divergence``), the two hex_latest JSONB attribute
sites (``_build_hex_state_attributes`` /write, ``_hex_feature_properties``
/read), the county-zoom population-weighted-mean aggregation
(``_aggregate_hex_features``), the contract entry, and ``stub_bridge.py``
parity.

``price_divergence`` is a ``TERRITORY_EXCLUDED_FIELDS`` entry
(``babylon.models.world_state``) — ``MarketScissorsSystem`` writes it
during ``step()`` only for ``WorldState.from_graph`` to drop it before
``new_state.to_graph``, same altitude gap ``_carry_reserve_army_dispossession``
fixes for the Feature 021 pair. UNLIKE that pair (a genuine recompute
against pure calculators), the carry here is a plain re-projection: the
source of truth — ``new_state.market_county`` (keyed by ``county_fips``) —
is a REAL ``WorldState`` field that round-trips untouched (Program 23 /
ADR078), so no calculator needs re-invoking.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

pytestmark = pytest.mark.unit


class TestCarryPriceDivergence:
    """``_carry_price_divergence`` re-injects ``price_divergence`` onto
    ``new_graph`` from ``new_state.market_county`` — the bridge-side fix
    for the ``TERRITORY_EXCLUDED_FIELDS`` altitude gap."""

    def test_reinjects_from_matching_county(self) -> None:
        from babylon.models.market import MarketState
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import _carry_price_divergence

        graph = BabylonGraph()
        graph.add_node("T1", _node_type="territory", county_fips="26163")
        axis = MarketState(
            price_log=0.42,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=0.0,
            value_ema=1.0,
            tick=5,
        )

        _carry_price_divergence(graph, {"26163": axis})

        assert graph.nodes["T1"]["price_divergence"] == pytest.approx(0.42)

    def test_reinjects_negative_reading(self) -> None:
        """SIGNED — negative (price below value) must survive untouched,
        never coerced toward 0.0 or made positive."""
        from babylon.models.market import MarketState
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import _carry_price_divergence

        graph = BabylonGraph()
        graph.add_node("T1", _node_type="territory", county_fips="26163")
        axis = MarketState(
            price_log=-0.37,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=0.0,
            value_ema=1.0,
            tick=5,
        )

        _carry_price_divergence(graph, {"26163": axis})

        assert graph.nodes["T1"]["price_divergence"] == pytest.approx(-0.37)

    def test_no_market_county_carries_as_absence(self) -> None:
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import _carry_price_divergence

        graph = BabylonGraph()
        graph.add_node("T1", _node_type="territory", county_fips="26163")

        _carry_price_divergence(graph, None)

        assert "price_divergence" not in graph.nodes["T1"]

    def test_territory_without_county_fips_carries_as_absence(self) -> None:
        from babylon.models.market import MarketState
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import _carry_price_divergence

        graph = BabylonGraph()
        graph.add_node("T1", _node_type="territory")  # no county_fips
        axis = MarketState(
            price_log=0.5,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=0.0,
            value_ema=1.0,
            tick=5,
        )

        _carry_price_divergence(graph, {"26163": axis})

        assert "price_divergence" not in graph.nodes["T1"]

    def test_territory_with_unmatched_county_fips_carries_as_absence(self) -> None:
        """Constitution III.11: a territory whose county has no active
        wage/value substrate this tick (de-positioned, absent from
        market_county) gets no attr — never a stale/fabricated reading."""
        from babylon.models.market import MarketState
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import _carry_price_divergence

        graph = BabylonGraph()
        graph.add_node("T1", _node_type="territory", county_fips="06037")
        axis = MarketState(
            price_log=0.5,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=0.0,
            value_ema=1.0,
            tick=5,
        )

        _carry_price_divergence(graph, {"26163": axis})  # different county

        assert "price_divergence" not in graph.nodes["T1"]

    def test_ignores_non_territory_nodes(self) -> None:
        from babylon.models.market import MarketState
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import _carry_price_divergence

        graph = BabylonGraph()
        graph.add_node("C1", _node_type="social_class", county_fips="26163")
        axis = MarketState(
            price_log=0.5,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=0.0,
            value_ema=1.0,
            tick=5,
        )

        _carry_price_divergence(graph, {"26163": axis})

        assert "price_divergence" not in graph.nodes["C1"]


class TestHexStateRowPriceDivergence:
    def test_price_divergence_written_into_attributes_when_provided(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "price_divergence": 0.35},
        )
        assert row is not None
        assert row["attributes"]["price_divergence"] == pytest.approx(0.35)

    def test_negative_price_divergence_written_into_attributes(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "price_divergence": -0.28},
        )
        assert row is not None
        assert row["attributes"]["price_divergence"] == pytest.approx(-0.28)

    def test_price_divergence_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "price_divergence": None},
        )
        assert row is not None
        assert "price_divergence" not in row["attributes"]

    def test_price_divergence_absent_when_key_missing(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(), 3, {"h3_index": "872a30d8affffff", "county_fips": "26163"}
        )
        assert row is not None
        assert "price_divergence" not in row["attributes"]


def _hex_row_stub(
    *,
    h3_index: str = "h1",
    county_fips: str = "26163",
    pop_total: int = 1000,
    price_divergence: float | None = 0.2,
) -> Any:
    attributes: dict[str, Any] = {}
    if price_divergence is not None:
        attributes["price_divergence"] = price_divergence
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


class TestHexFeaturePropertiesPriceDivergence:
    def test_price_divergence_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(price_divergence=0.42))
        assert props["price_divergence"] == pytest.approx(0.42)

    def test_negative_price_divergence_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(price_divergence=-0.55))
        assert props["price_divergence"] == pytest.approx(-0.55)

    def test_missing_price_divergence_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(price_divergence=None))
        assert props["price_divergence"] is None


class TestAggregateHexFeaturesPriceDivergence:
    def test_price_divergence_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, price_divergence=0.2),
            _hex_row_stub(h3_index="h1b", pop_total=3000, price_divergence=1.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (1000*0.2 + 3000*1.0) / 4000 = (200 + 3000) / 4000 = 0.8
        assert features[0]["properties"]["price_divergence"] == pytest.approx(0.8)

    def test_price_divergence_weighted_mean_with_mixed_signs(self) -> None:
        """SIGNED — the weighted mean must be able to land negative when
        the negative-side population dominates, never clamped toward 0."""
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=3000, price_divergence=-0.6),
            _hex_row_stub(h3_index="h1b", pop_total=1000, price_divergence=0.2),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (3000*-0.6 + 1000*0.2) / 4000 = (-1800 + 200) / 4000 = -0.4
        assert features[0]["properties"]["price_divergence"] == pytest.approx(-0.4)

    def test_price_divergence_real_zero_across_all_hexes_is_a_real_zero(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", price_divergence=0.0),
            _hex_row_stub(h3_index="h1b", price_divergence=0.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["price_divergence"] == 0.0

    def test_price_divergence_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", price_divergence=None),
            _hex_row_stub(h3_index="h1b", price_divergence=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["price_divergence"] is None

    def test_price_divergence_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", price_divergence=-0.9),
            _hex_row_stub(h3_index="h1b", price_divergence=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["price_divergence"] == pytest.approx(-0.9)


class TestMapContractIncludesPriceDivergence:
    def test_price_divergence_is_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "price_divergence" in MAP_METRIC_PROPERTIES

    def test_valid_map_layers_derives_from_the_contract(self) -> None:
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)

    def test_price_divergence_not_in_history_replayable_set(self) -> None:
        """hex_latest is a current-tick-only cache — price_divergence has
        no append-only historical store, same as wage_pressure/habitability."""
        from game.map_contract import MAP_HISTORY_REPLAYABLE_METRICS

        assert "price_divergence" not in MAP_HISTORY_REPLAYABLE_METRICS


class TestStubBridgeParityPriceDivergence:
    def test_hex_zoom_features_carry_price_divergence(self) -> None:
        from game.stub_bridge import _make_hex_features

        features = _make_hex_features(tick=0)
        assert features
        for feature in features:
            assert "price_divergence" in feature["properties"]

    def test_aggregated_features_carry_price_divergence(self) -> None:
        from game.stub_bridge import _make_aggregated_features

        features = _make_aggregated_features("county", tick=0)
        assert features
        for feature in features:
            assert "price_divergence" in feature["properties"]

    def test_available_metrics_advertises_price_divergence(self) -> None:
        from game.stub_bridge import StubEngineBridge

        bridge = StubEngineBridge()
        session_id = bridge.create_game(scenario="wayne_county")
        snapshot = bridge.get_map_snapshot(session_id, zoom="county")

        assert "price_divergence" in snapshot["metadata"]["available_metrics"]
