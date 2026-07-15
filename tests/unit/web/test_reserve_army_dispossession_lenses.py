"""Feature 021 lens pair: ``wage_pressure`` (Reserve Army wage-discipline
gauge, System #5 ``ReserveArmySystem``) and ``dispossession_intensity``
(composite carceral/eviction intensity, System #10
``DispossessionEventSystem``) as selectable ``/map/`` lenses.

Both are already serialized on ``/state/`` (``_serialize_territory``, via
``_territory_graph_attr`` off the identically-named graph-only attrs) — this
module tests the ``/map/`` lens plumbing: the contract entry, the two
hex_latest JSONB attribute sites (``_build_hex_state_attributes`` /write,
``_hex_feature_properties`` /read), the county-zoom population-weighted-mean
aggregation (``_aggregate_hex_features``), ``stub_bridge.py`` parity, and the
bridge-side round-trip carry (``_carry_reserve_army_dispossession``).

Mirrors ``tests/unit/web/test_epistemic_horizon_lenses.py``'s structure (the
Wave 5 receptivity-lens precedent this pair follows line-for-line), including
the carry-function class: both attrs are ``TERRITORY_EXCLUDED_FIELDS``, so
``ReserveArmySystem``/``DispossessionEventSystem`` (positions #5/#10) write
them during ``step`` only for ``WorldState.from_graph`` to drop them before
``new_state.to_graph`` — without a carry the lenses render honestly-empty on
every resolved tick. Unlike ``EpistemicHorizonSystem`` (position 27, last),
these run mid-pipeline, but every input the two coefficients depend on is a
real ``Territory`` field that survives the round trip untouched and no later
system mutates it, so a bridge-side RECOMPUTE (not a stash) is byte-identical
to the engine's own in-tick value (Constitution III.7).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _hex_row_stub(
    *,
    h3_index: str = "h1",
    county_fips: str = "26163",
    pop_total: int = 1000,
    wage_pressure: float | None = 0.2,
    dispossession_intensity: float | None = 0.3,
) -> Any:
    from types import SimpleNamespace

    attributes: dict[str, Any] = {}
    if wage_pressure is not None:
        attributes["wage_pressure"] = wage_pressure
    if dispossession_intensity is not None:
        attributes["dispossession_intensity"] = dispossession_intensity
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


def _territory_graph(
    *,
    reserve_ratio: float = 0.15,
    foreclosure_rate: float = 0.2,
    eviction_rate: float = 0.1,
    displacement_rate: float = 0.05,
    concentrated_ownership: float = 0.3,
    absentee_landlord_share: float = 0.25,
    median_wage: float = 1000.0,
    wealth: float = 500.0,
) -> Any:
    """Single territory T1 carrying the reserve-army + dispossession input
    rates — all real ``Territory`` model fields that survive the WorldState
    round trip. Mirrors ``test_epistemic_horizon_lenses._graph_with_tenant``."""
    from babylon.topology.graph import BabylonGraph

    graph = BabylonGraph()
    graph.add_node(
        "T1",
        _node_type="territory",
        id="T1",
        name="T1",
        reserve_ratio=reserve_ratio,
        foreclosure_rate=foreclosure_rate,
        eviction_rate=eviction_rate,
        displacement_rate=displacement_rate,
        concentrated_ownership=concentrated_ownership,
        absentee_landlord_share=absentee_landlord_share,
        median_wage=median_wage,
        wealth=wealth,
    )
    return graph


class TestCarryReserveArmyDispossession:
    """``_carry_reserve_army_dispossession`` recomputes ``wage_pressure`` and
    ``dispossession_intensity`` onto ``new_graph`` — the bridge-side fix for
    the same ``TERRITORY_EXCLUDED_FIELDS`` altitude gap
    ``_carry_epistemic_horizon`` fixes for the receptivity pair."""

    def test_recomputes_both_coefficients(self) -> None:
        from babylon.config.defines import GameDefines
        from game.engine_bridge import _carry_reserve_army_dispossession

        graph = _territory_graph()
        _carry_reserve_army_dispossession(graph, GameDefines())

        node = graph.nodes["T1"]
        assert node["wage_pressure"] > 0.0
        assert 0.0 <= node["dispossession_intensity"] <= 1.0
        # Side-effect-free: the input rates, median_wage and wealth are
        # untouched (the systems' wage reduction / wealth transfer already
        # happened in-tick and survive on the round-tripped graph).
        assert node["median_wage"] == pytest.approx(1000.0)
        assert node["wealth"] == pytest.approx(500.0)

    def test_matches_engine_systems_own_computation_byte_identical(self) -> None:
        """The recompute must reproduce EXACTLY what ``ReserveArmySystem`` and
        ``DispossessionEventSystem`` compute on the same inputs — no drift
        between the two call sites (Constitution III.7)."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.dispossession_events import DispossessionEventSystem
        from babylon.engine.systems.reserve_army import ReserveArmySystem
        from game.engine_bridge import _carry_reserve_army_dispossession

        services = ServiceContainer.create()
        engine_graph = _territory_graph()
        ReserveArmySystem().step(engine_graph, services, {"tick": 1})
        DispossessionEventSystem().step(engine_graph, services, {"tick": 1})
        expected = dict(engine_graph.nodes["T1"])

        bridge_graph = _territory_graph()
        _carry_reserve_army_dispossession(bridge_graph, services.defines)
        actual = bridge_graph.nodes["T1"]

        assert actual["wage_pressure"] == pytest.approx(expected["wage_pressure"])
        assert actual["dispossession_intensity"] == pytest.approx(
            expected["dispossession_intensity"]
        )

    def test_territory_without_rates_carries_as_absence(self) -> None:
        """Constitution III.11: a territory with no ``reserve_ratio`` and no
        dispossession rates gets neither attr — no fabricated ``0.0``."""
        from babylon.config.defines import GameDefines
        from game.engine_bridge import _carry_reserve_army_dispossession

        graph = _territory_graph(
            reserve_ratio=0.0,
            foreclosure_rate=0.0,
            eviction_rate=0.0,
            displacement_rate=0.0,
        )
        _carry_reserve_army_dispossession(graph, GameDefines())

        node = graph.nodes["T1"]
        assert "wage_pressure" not in node
        assert "dispossession_intensity" not in node


class TestHexStateRowWagePressureDispossessionIntensity:
    """Like mass_receptivity/throughput_position — both are NATIVE
    per-territory graph attrs, so they ride the territory dict's own key
    (set by _serialize_territory), not a separate caller arg."""

    def test_wage_pressure_read_off_territory_dict_into_attributes(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "wage_pressure": 0.35,
            },
        )
        assert row is not None
        assert row["attributes"]["wage_pressure"] == pytest.approx(0.35)

    def test_wage_pressure_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "wage_pressure": None},
        )
        assert row is not None
        assert "wage_pressure" not in row["attributes"]

    def test_dispossession_intensity_read_off_territory_dict_into_attributes(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "dispossession_intensity": 0.55,
            },
        )
        assert row is not None
        assert row["attributes"]["dispossession_intensity"] == pytest.approx(0.55)

    def test_dispossession_intensity_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "dispossession_intensity": None,
            },
        )
        assert row is not None
        assert "dispossession_intensity" not in row["attributes"]


class TestHexFeaturePropertiesWagePressureDispossessionIntensity:
    def test_wage_pressure_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(wage_pressure=0.42))
        assert props["wage_pressure"] == pytest.approx(0.42)

    def test_missing_wage_pressure_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(wage_pressure=None))
        assert props["wage_pressure"] is None

    def test_dispossession_intensity_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(dispossession_intensity=0.61))
        assert props["dispossession_intensity"] == pytest.approx(0.61)

    def test_missing_dispossession_intensity_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(dispossession_intensity=None))
        assert props["dispossession_intensity"] is None


class TestAggregateHexFeaturesWagePressureDispossessionIntensity:
    def test_wage_pressure_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, wage_pressure=0.2),
            _hex_row_stub(h3_index="h1b", pop_total=3000, wage_pressure=1.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (1000*0.2 + 3000*1.0) / 4000 = (200 + 3000) / 4000 = 0.8
        assert features[0]["properties"]["wage_pressure"] == pytest.approx(0.8)

    def test_wage_pressure_real_zero_across_all_hexes_is_a_real_zero(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", wage_pressure=0.0),
            _hex_row_stub(h3_index="h1b", wage_pressure=0.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["wage_pressure"] == 0.0

    def test_wage_pressure_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", wage_pressure=None),
            _hex_row_stub(h3_index="h1b", wage_pressure=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["wage_pressure"] is None

    def test_wage_pressure_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", wage_pressure=0.9),
            _hex_row_stub(h3_index="h1b", wage_pressure=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["wage_pressure"] == pytest.approx(0.9)

    def test_dispossession_intensity_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, dispossession_intensity=0.1),
            _hex_row_stub(h3_index="h1b", pop_total=1000, dispossession_intensity=0.5),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (1000*0.1 + 1000*0.5) / 2000 = 0.3
        assert features[0]["properties"]["dispossession_intensity"] == pytest.approx(0.3)

    def test_dispossession_intensity_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", dispossession_intensity=None),
            _hex_row_stub(h3_index="h1b", dispossession_intensity=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["dispossession_intensity"] is None

    def test_dispossession_intensity_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", dispossession_intensity=0.7),
            _hex_row_stub(h3_index="h1b", dispossession_intensity=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["dispossession_intensity"] == pytest.approx(0.7)


class TestMapContractIncludesFeature021Lenses:
    def test_both_new_lenses_are_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "wage_pressure" in MAP_METRIC_PROPERTIES
        assert "dispossession_intensity" in MAP_METRIC_PROPERTIES

    def test_valid_map_layers_derives_from_the_contract(self) -> None:
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)

    def test_neither_lens_is_history_replayable(self) -> None:
        """hex_latest is a current-tick-only cache — same as agitation/
        mass_receptivity, these have no append-only historical store."""
        from game.map_contract import MAP_HISTORY_REPLAYABLE_METRICS

        assert "wage_pressure" not in MAP_HISTORY_REPLAYABLE_METRICS
        assert "dispossession_intensity" not in MAP_HISTORY_REPLAYABLE_METRICS


class TestStubBridgeParityFeature021:
    def test_hex_zoom_features_carry_both_new_properties(self) -> None:
        from game.stub_bridge import _make_hex_features

        features = _make_hex_features(tick=0)
        assert features
        for feature in features:
            assert "wage_pressure" in feature["properties"]
            assert "dispossession_intensity" in feature["properties"]

    def test_aggregated_features_carry_both_new_properties(self) -> None:
        from game.stub_bridge import _make_aggregated_features

        features = _make_aggregated_features("county", tick=0)
        assert features
        for feature in features:
            assert "wage_pressure" in feature["properties"]
            assert "dispossession_intensity" in feature["properties"]

    def test_available_metrics_advertises_both(self) -> None:
        from game.stub_bridge import StubEngineBridge

        bridge = StubEngineBridge()
        session_id = bridge.create_game(scenario="wayne_county")
        snapshot = bridge.get_map_snapshot(session_id, zoom="county")

        assert "wage_pressure" in snapshot["metadata"]["available_metrics"]
        assert "dispossession_intensity" in snapshot["metadata"]["available_metrics"]
