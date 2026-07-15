"""Wave-5 receptivity lens pair: honest-display ``mass_receptivity`` (numeric)
and ``vision_state`` (categorical) ``/map/`` lenses, plus ``intel_confidence``
as a territory-serializer/inspector-only row (no lens — see module docstring
in ``web/game/engine_bridge.py::_carry_epistemic_horizon``).

``EpistemicHorizonSystem`` (engine position 27, last) writes these three
transient territory attrs during a tick's internal graph mutation, but
``Territory.extra="forbid"`` means ``WorldState.from_graph()`` drops all
three (``TERRITORY_EXCLUDED_FIELDS``) before ``new_state.to_graph()`` ever
re-emits them — the same altitude gap ``_carry_tick_dynamics_flows`` fixes
for ``TickDynamicsSystem``'s ``tick_*``/``flow_*`` attrs. Unlike that carry,
this one is a genuine RECOMPUTE (not a ``persistent_context`` stash): every
input ``EpistemicHorizonSystem`` reads (``p_acquiescence``, ``ideology.
class_consciousness``, ``role``, ``population`` — real ``SocialClass`` model
fields — plus TENANCY/PRESENCE edges) survives the ``WorldState`` round trip
untouched, so re-running the same pure formula against ``new_graph``
reproduces byte-identical output.

Mirrors ``tests/unit/web/test_wave2_map_lenses.py``'s structure (the W2.4
throughput_position/agitation/territory_type precedent) and
``tests/unit/web/test_carry_derived_rates.py`` (the carry-function pattern).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines import GameDefines
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph_with_tenant(
    *,
    role: str = "periphery_proletariat",
    population: float = 1000.0,
    p_acquiescence: float = 0.2,
    class_consciousness: float = 0.7,
) -> BabylonGraph:
    """T1 tenanted by a single social_class C1 (mirrors
    test_epistemic_horizon.py's own ``_tenant`` helper)."""
    graph = BabylonGraph()
    graph.add_node("T1", _node_type="territory", id="T1", name="T1")
    graph.add_node(
        "C1",
        _node_type="social_class",
        id="C1",
        role=role,
        population=population,
        p_acquiescence=p_acquiescence,
        ideology={"class_consciousness": class_consciousness},
    )
    graph.add_edge("C1", "T1", edge_type=EdgeType.TENANCY)
    return graph


def _tenant_less_graph() -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node("T1", _node_type="territory", id="T1", name="T1")
    return graph


class TestCarryEpistemicHorizon:
    """``_carry_epistemic_horizon`` recomputes the 3 shadow attrs onto
    ``new_graph`` — the bridge-side fix for the altitude gap."""

    def test_recomputes_mass_receptivity_intel_confidence_vision_state(self) -> None:
        from game.engine_bridge import _carry_epistemic_horizon

        # (1 - 0.2) * 0.7 * 1.0 = 0.56 -> Mud
        new_graph = _graph_with_tenant(
            role="periphery_proletariat", p_acquiescence=0.2, class_consciousness=0.7
        )
        defines = GameDefines().epistemic_horizon

        _carry_epistemic_horizon(new_graph, defines)

        node = new_graph.nodes["T1"]
        assert node["mass_receptivity"] == pytest.approx(0.56)
        assert node["intel_confidence"] == pytest.approx(0.1)
        assert node["vision_state"] == "mud"

    def test_matches_engine_systems_own_computation_byte_identical(self) -> None:
        """The recompute must reproduce EXACTLY what EpistemicHorizonSystem
        itself would compute on the same inputs — no drift between the two
        call sites (Constitution III.7)."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.epistemic_horizon import EpistemicHorizonSystem
        from game.engine_bridge import _carry_epistemic_horizon

        engine_graph = _graph_with_tenant()
        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(engine_graph, services, {})
        expected = dict(engine_graph.nodes["T1"])

        bridge_graph = _graph_with_tenant()
        _carry_epistemic_horizon(bridge_graph, services.defines.epistemic_horizon)
        actual = bridge_graph.nodes["T1"]

        assert actual["mass_receptivity"] == pytest.approx(expected["mass_receptivity"])
        assert actual["intel_confidence"] == pytest.approx(expected["intel_confidence"])
        assert actual["vision_state"] == expected["vision_state"]

    def test_tenant_less_territory_carries_as_absence(self) -> None:
        """Constitution III.11: no tenant classes -> no fabricated attrs,
        even after the carry runs."""
        from game.engine_bridge import _carry_epistemic_horizon

        new_graph = _tenant_less_graph()
        defines = GameDefines().epistemic_horizon

        _carry_epistemic_horizon(new_graph, defines)

        node = new_graph.nodes["T1"]
        assert "mass_receptivity" not in node
        assert "intel_confidence" not in node
        assert "vision_state" not in node


class TestSerializeTerritoryEpistemicHorizon:
    def test_reads_all_three_off_the_live_graph(self) -> None:
        from game.engine_bridge import _serialize_territory

        graph = _graph_with_tenant()
        defines = GameDefines().epistemic_horizon
        from babylon.engine.systems.epistemic_horizon import compute_epistemic_horizon

        compute_epistemic_horizon(graph, defines)

        territory = SimpleNamespace(
            id="T1",
            name="T1",
            h3_index=None,
            county_fips="",
            heat=0.0,
            sector_type="industrial",
            territory_type="core",
            profile="low_profile",
            rent_level=0.0,
            population=1000,
            under_eviction=False,
            biocapacity=0.0,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            host_id=None,
            occupant_id=None,
            wealth=0.0,
            median_wage=0.0,
            reserve_ratio=0.0,
            foreclosure_rate=0.0,
            eviction_rate=0.0,
            displacement_rate=0.0,
            concentrated_ownership=0.0,
            absentee_landlord_share=0.0,
        )

        result = _serialize_territory(territory, graph=graph)

        assert result["mass_receptivity"] == pytest.approx(0.56)
        assert result["intel_confidence"] == pytest.approx(0.1)
        assert result["vision_state"] == "mud"

    def test_none_without_a_graph(self) -> None:
        from game.engine_bridge import _serialize_territory

        territory = SimpleNamespace(
            id="T1",
            name="T1",
            h3_index=None,
            county_fips="",
            heat=0.0,
            sector_type="industrial",
            territory_type="core",
            profile="low_profile",
            rent_level=0.0,
            population=1000,
            under_eviction=False,
            biocapacity=0.0,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            host_id=None,
            occupant_id=None,
            wealth=0.0,
            median_wage=0.0,
            reserve_ratio=0.0,
            foreclosure_rate=0.0,
            eviction_rate=0.0,
            displacement_rate=0.0,
            concentrated_ownership=0.0,
            absentee_landlord_share=0.0,
        )

        result = _serialize_territory(territory, graph=None)

        assert result["mass_receptivity"] is None
        assert result["intel_confidence"] is None
        assert result["vision_state"] is None


def _hex_row_stub(
    *,
    h3_index: str = "h1",
    county_fips: str = "26163",
    pop_total: int = 1000,
    mass_receptivity: float | None = 0.4,
    vision_state: str | None = "mud",
) -> Any:
    attributes: dict[str, Any] = {}
    if mass_receptivity is not None:
        attributes["mass_receptivity"] = mass_receptivity
    if vision_state is not None:
        attributes["vision_state"] = vision_state
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


class TestHexStateRowMassReceptivityVisionState:
    def test_mass_receptivity_read_off_territory_dict_into_attributes(self) -> None:
        """Like throughput_position/habitability — mass_receptivity is a
        NATIVE per-territory graph attr, so it rides the territory dict's
        own key (set by _serialize_territory), not a separate caller arg."""
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "mass_receptivity": 0.45,
            },
        )
        assert row is not None
        assert row["attributes"]["mass_receptivity"] == pytest.approx(0.45)

    def test_mass_receptivity_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "mass_receptivity": None},
        )
        assert row is not None
        assert "mass_receptivity" not in row["attributes"]

    def test_vision_state_read_off_territory_dict_into_attributes(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {
                "h3_index": "872a30d8affffff",
                "county_fips": "26163",
                "vision_state": "desert",
            },
        )
        assert row is not None
        assert row["attributes"]["vision_state"] == "desert"

    def test_vision_state_absent_when_territory_dict_has_none(self) -> None:
        from game.engine_bridge import _hex_state_row

        row = _hex_state_row(
            uuid.uuid4(),
            3,
            {"h3_index": "872a30d8affffff", "county_fips": "26163", "vision_state": None},
        )
        assert row is not None
        assert "vision_state" not in row["attributes"]


class TestHexFeaturePropertiesMassReceptivityVisionState:
    def test_mass_receptivity_read_from_attributes(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(mass_receptivity=0.62))
        assert props["mass_receptivity"] == pytest.approx(0.62)

    def test_missing_mass_receptivity_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(mass_receptivity=None))
        assert props["mass_receptivity"] is None

    def test_vision_state_passthrough(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(vision_state="water"))
        assert props["vision_state"] == "water"

    def test_missing_vision_state_is_none(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(vision_state=None))
        assert props["vision_state"] is None


class TestAggregateHexFeaturesMassReceptivityVisionState:
    def test_mass_receptivity_population_weighted_mean(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, mass_receptivity=0.2),
            _hex_row_stub(h3_index="h1b", pop_total=3000, mass_receptivity=1.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # (1000*0.2 + 3000*1.0) / 4000 = (200 + 3000) / 4000 = 0.8
        assert features[0]["properties"]["mass_receptivity"] == pytest.approx(0.8)

    def test_mass_receptivity_real_zero_across_all_hexes_is_a_real_zero(self) -> None:
        """M_r can be legitimately exactly 0.0 (e.g. a territory tenanted
        only by a role absent from the corpus's class-factor table) — a
        real 0.0 weighted mean, never treated as missing."""
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", mass_receptivity=0.0),
            _hex_row_stub(h3_index="h1b", mass_receptivity=0.0),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["mass_receptivity"] == 0.0

    def test_mass_receptivity_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", mass_receptivity=None),
            _hex_row_stub(h3_index="h1b", mass_receptivity=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["mass_receptivity"] is None

    def test_mass_receptivity_ignores_hexes_without_coverage(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", mass_receptivity=0.9),
            _hex_row_stub(h3_index="h1b", mass_receptivity=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["mass_receptivity"] == pytest.approx(0.9)

    def test_vision_state_population_weighted_mode(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, vision_state="mud"),
            _hex_row_stub(h3_index="h1b", pop_total=1000, vision_state="mud"),
            _hex_row_stub(h3_index="h1c", pop_total=500, vision_state="desert"),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        assert features[0]["properties"]["vision_state"] == "mud"

    def test_vision_state_tie_breaks_lexicographically_greatest(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", pop_total=1000, vision_state="desert"),
            _hex_row_stub(h3_index="h1b", pop_total=1000, vision_state="mud"),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        # Equal population -> max((pop, value)) picks the lexicographically
        # greatest value ("mud" > "desert") — same tie-break convention as
        # dominant_class/territory_type.
        assert features[0]["properties"]["vision_state"] == "mud"

    def test_vision_state_none_when_no_hex_has_data(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub(h3_index="h1a", vision_state=None),
            _hex_row_stub(h3_index="h1b", vision_state=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["vision_state"] is None


class TestMapContractIncludesReceptivityLenses:
    def test_both_new_lenses_are_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "mass_receptivity" in MAP_METRIC_PROPERTIES
        assert "vision_state" in MAP_METRIC_PROPERTIES

    def test_intel_confidence_is_not_in_the_contract(self) -> None:
        """intel_confidence rides the territory serializer/inspector only —
        uniformly 0.1 today (C_p=0 everywhere), so a flat lens would be
        decorative (see the program report's Phase-1 findings)."""
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "intel_confidence" not in MAP_METRIC_PROPERTIES

    def test_valid_map_layers_derives_from_the_contract(self) -> None:
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)

    def test_neither_lens_is_history_replayable(self) -> None:
        """hex_latest is a current-tick-only cache — same as agitation/
        territory_type, these have no append-only historical store."""
        from game.map_contract import MAP_HISTORY_REPLAYABLE_METRICS

        assert "mass_receptivity" not in MAP_HISTORY_REPLAYABLE_METRICS
        assert "vision_state" not in MAP_HISTORY_REPLAYABLE_METRICS


class TestGetInspectorHexEpistemicHorizon:
    """Real wayne_county tick-0 graph — no mocking of engine internals,
    matching TestGetInspectorHexWave2Lenses's own established pattern."""

    def _wayne_bridge(self) -> tuple[Any, Any]:
        from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        return EngineBridge(mock_persistence), graph

    def test_all_three_are_none_before_any_tick_has_resolved(self) -> None:
        """EpistemicHorizonSystem is engine position 27 — the freshly-seeded
        tick-0 graph has never been stepped, so this is honestly absent,
        the same shape as throughput_position before any year boundary."""
        from game.engine_bridge import _build_initial_state_for_scenario

        bridge, _graph = self._wayne_bridge()
        state = _build_initial_state_for_scenario("wayne_county")
        territory = next(iter(state.territories.values()))

        result = bridge.get_inspector_hex(uuid.uuid4(), territory.h3_index)

        assert result["mass_receptivity"] is None
        assert result["intel_confidence"] is None
        assert result["vision_state"] is None

    def test_real_values_once_the_graph_carries_them(self) -> None:
        from babylon.config.defines import GameDefines
        from babylon.engine.systems.epistemic_horizon import compute_epistemic_horizon
        from game.engine_bridge import _build_initial_state_for_scenario

        bridge, graph = self._wayne_bridge()
        compute_epistemic_horizon(graph, GameDefines().epistemic_horizon)
        state = _build_initial_state_for_scenario("wayne_county")
        territory = next(iter(state.territories.values()))

        result = bridge.get_inspector_hex(uuid.uuid4(), territory.h3_index)

        # wayne_county seeds real TENANCY-linked social_class members, so
        # every territory gets a real value (Phase-1 finding: 81/81 covered).
        assert result["mass_receptivity"] is not None
        assert result["intel_confidence"] is not None
        assert result["vision_state"] in {"desert", "mud", "water"}


class TestStubBridgeParityEpistemicHorizon:
    def test_hex_zoom_features_carry_both_new_properties(self) -> None:
        from game.stub_bridge import _make_hex_features

        features = _make_hex_features(tick=0)
        assert features
        for feature in features:
            assert "mass_receptivity" in feature["properties"]
            assert "vision_state" in feature["properties"]

    def test_aggregated_features_carry_both_new_properties(self) -> None:
        from game.stub_bridge import _make_aggregated_features

        features = _make_aggregated_features("county", tick=0)
        assert features
        for feature in features:
            assert "mass_receptivity" in feature["properties"]
            assert "vision_state" in feature["properties"]

    def test_stub_vision_state_uses_the_real_three_state_vocabulary(self) -> None:
        from game.stub_bridge import _make_hex_features

        real_values = {"desert", "mud", "water"}
        features = _make_hex_features(tick=0)
        for feature in features:
            assert feature["properties"]["vision_state"] in real_values

    def test_available_metrics_advertises_both(self) -> None:
        from game.stub_bridge import StubEngineBridge

        bridge = StubEngineBridge()
        session_id = bridge.create_game(scenario="wayne_county")
        snapshot = bridge.get_map_snapshot(session_id, zoom="county")

        assert "mass_receptivity" in snapshot["metadata"]["available_metrics"]
        assert "vision_state" in snapshot["metadata"]["available_metrics"]
