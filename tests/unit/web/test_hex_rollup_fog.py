"""Track 1 / Task 5 (2026-07-18, branch fix/null-play-coupling): gate the
hex-rollup pair — ``_hex_feature_properties`` (hex zoom) AND
``_aggregate_hex_features`` (every aggregated zoom) — through the SAME
``apply_fog``/``POLITICAL_FIELDS`` gate Task 4 wired onto
``_serialize_territory``/``get_inspector_*``.

The defect this task exists to close: gating only the hex-zoom composer
would leave every aggregated zoom level (county/bea/msa/state) leaking
``heat``/``dominant_class``/``solidarity_index``/``agitation`` verbatim,
since ``_aggregate_hex_features`` used to independently re-derive those same
four fields straight off the raw ``HexState`` rows with no gate at all. The
``TestAggregateHexFeaturesFog`` class below is the load-bearing suite: it
constructs the AGGREGATE path explicitly (not just the per-hex path) and
proves a masked hex's political values never leak into the group mean/mode.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _hex_row(**overrides: Any) -> SimpleNamespace:
    """A minimal ``hex_latest``-row stand-in (mirrors test_map_aggregation.py's
    ``_hex()``/test_map_dominant_class_solidarity.py's ``_hex_row_stub()``)."""
    base: dict[str, Any] = {
        "county_fips": "26163",
        "state_fips": "26",
        "bea_ea_code": "EA1",
        "msa_code": "MSA1",
        "county_name": "Wayne",
        "pop_total": 1000,
        "profit_rate": 0.2,
        "exploitation_rate": 1.5,
        "occ": 3.0,
        "imperial_rent": 0.0001,
        "heat": 0.8,
        "org_count": 1,
        "dominant_class": "core_proletariat",
        "attributes": {"solidarity_index": 0.6, "agitation": 0.9},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestHexFeaturePropertiesFog:
    """The hex-zoom half of the pipeline."""

    def test_default_no_reach_is_unfogged(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row(h3_index="h1"))

        assert props["heat"] == 0.8
        assert props["dominant_class"] == "core_proletariat"
        assert props["solidarity_index"] == pytest.approx(0.6)
        assert props["agitation"] == pytest.approx(0.9)
        assert "vision_masked" not in props

    def test_outside_reach_masks_the_four_political_fields(self) -> None:
        from game.engine_bridge import _hex_feature_properties
        from game.fog.ledger import IntelLedger

        props = _hex_feature_properties(
            _hex_row(h3_index="h1"),
            territory_id="T1",
            reach=frozenset(),  # T1 not in reach
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
        )

        assert props["heat"] is None
        assert props["dominant_class"] is None
        assert props["solidarity_index"] is None
        assert props["agitation"] is None
        assert set(props["vision_masked"]) == {
            "heat",
            "dominant_class",
            "solidarity_index",
            "agitation",
        }

    def test_inside_reach_stays_exact(self) -> None:
        from game.engine_bridge import _hex_feature_properties
        from game.fog.ledger import IntelLedger

        props = _hex_feature_properties(
            _hex_row(h3_index="h1"),
            territory_id="T1",
            reach=frozenset({"T1"}),
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
        )

        assert props["heat"] == 0.8
        assert props["dominant_class"] == "core_proletariat"
        assert props["solidarity_index"] == pytest.approx(0.6)
        assert props["agitation"] == pytest.approx(0.9)
        assert props["vision_masked"] == []

    def test_material_fields_never_masked(self) -> None:
        from game.engine_bridge import _hex_feature_properties
        from game.fog.ledger import IntelLedger

        props = _hex_feature_properties(
            _hex_row(h3_index="h1"),
            territory_id="T1",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
        )

        assert props["profit_rate"] == 0.2
        assert props["exploitation_rate"] == 1.5
        assert props["occ"] == 3.0
        assert props["imperial_rent"] == pytest.approx(0.0001)
        assert props["org_presence"] == 1
        assert props["population"] == 1000

    def test_unresolvable_territory_id_denies_by_default(self) -> None:
        """territory_id=None (h3_index -> territory_id map missed this hex)
        must fog, never crash or fabricate visibility."""
        from game.engine_bridge import _hex_feature_properties
        from game.fog.ledger import IntelLedger

        props = _hex_feature_properties(
            _hex_row(h3_index="h1"),
            territory_id=None,
            reach=frozenset({"T1"}),  # some OTHER territory is in reach
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
        )

        assert props["heat"] is None
        assert props["dominant_class"] is None


class TestAggregateHexFeaturesFog:
    """THE load-bearing suite: the aggregated-zoom half of the pipeline.

    Gating only ``_hex_feature_properties`` would miss every one of these —
    a test that only drove the hex-zoom path would pass against the OLD
    broken code and prove nothing. Each test here calls
    ``EngineBridge._aggregate_hex_features`` directly, the exact same
    function ``get_map_snapshot`` calls for county/bea/msa/state zoom.
    """

    def test_default_no_reach_is_unfogged_backward_compat(self) -> None:
        """Every pre-existing call site (test_map_aggregation.py,
        test_map_dominant_class_solidarity.py) calls this with just
        ``(hex_states, zoom)`` — must stay byte-identical."""
        from game.engine_bridge import EngineBridge

        rows = [_hex_row(h3_index="h1"), _hex_row(h3_index="h2")]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        props = features[0]["properties"]
        assert props["heat"] == pytest.approx(0.8)
        assert props["dominant_class"] == "core_proletariat"
        assert props["solidarity_index"] == pytest.approx(0.6)
        assert props["agitation"] == pytest.approx(0.9)

    def test_group_entirely_outside_reach_has_all_four_masked_in_the_aggregate(
        self,
    ) -> None:
        """The zoom-level test: a group whose every hex maps to a territory
        OUTSIDE reach must read as honest-unknown in the ROLLUP — not the
        real weighted value, not a fabricated 0.0."""
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelLedger

        rows = [
            _hex_row(h3_index="h1", heat=0.8, dominant_class="core_proletariat"),
            _hex_row(h3_index="h2", heat=0.6, dominant_class="core_proletariat"),
        ]
        h3_to_territory = {"h1": "T1", "h2": "T1"}

        features = EngineBridge._aggregate_hex_features(
            rows,
            "county",
            reach=frozenset(),  # T1 not in reach
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
            h3_to_territory=h3_to_territory,
        )

        props = features[0]["properties"]
        assert props["heat"] is None
        assert props["dominant_class"] is None
        assert props["solidarity_index"] is None
        assert props["agitation"] is None

    def test_group_entirely_inside_reach_stays_exact_in_the_aggregate(self) -> None:
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelLedger

        rows = [
            _hex_row(h3_index="h1", heat=0.8, pop_total=1000),
            _hex_row(h3_index="h2", heat=0.6, pop_total=1000),
        ]
        h3_to_territory = {"h1": "T1", "h2": "T1"}

        features = EngineBridge._aggregate_hex_features(
            rows,
            "county",
            reach=frozenset({"T1"}),
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
            h3_to_territory=h3_to_territory,
        )

        props = features[0]["properties"]
        # population-weighted mean of 0.8/0.6 at equal population -> 0.7
        assert props["heat"] == pytest.approx(0.7)
        assert props["dominant_class"] == "core_proletariat"

    def test_material_fields_survive_fog_at_the_aggregate_level(self) -> None:
        """Material fields (production/wages/rent/demographics) are NEVER
        gated, at any zoom, regardless of reach."""
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelLedger

        rows = [_hex_row(h3_index="h1", profit_rate=0.2, imperial_rent=0.0001)]
        features = EngineBridge._aggregate_hex_features(
            rows,
            "county",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
            h3_to_territory={"h1": "T1"},
        )

        props = features[0]["properties"]
        assert props["profit_rate"] == pytest.approx(0.2)
        assert props["imperial_rent"] == pytest.approx(0.0001)
        assert props["org_presence"] == 1
        assert props["population"] == 1000

    def test_mixed_reach_group_averages_only_the_visible_hexes(self) -> None:
        """One hex in reach (heat=0.8), one masked (heat=0.6, hidden) —
        the group mean must reflect ONLY the visible hex's heat (0.8), not
        a blended 0.7, and never silently treat the masked hex as 0.0."""
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelLedger

        rows = [
            _hex_row(h3_index="h_in", heat=0.8, pop_total=1000),
            _hex_row(h3_index="h_out", heat=0.6, pop_total=1000),
        ]
        h3_to_territory = {"h_in": "T_IN", "h_out": "T_OUT"}

        features = EngineBridge._aggregate_hex_features(
            rows,
            "county",  # both hexes share county_fips -> one group
            reach=frozenset({"T_IN"}),
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
            h3_to_territory=h3_to_territory,
        )

        assert len(features) == 1
        props = features[0]["properties"]
        assert props["heat"] == pytest.approx(0.8)
        # population is a MATERIAL field — both hexes still counted.
        assert props["population"] == 2000

    def test_unresolvable_territory_id_denies_by_default_in_the_aggregate(self) -> None:
        """A hex whose h3_index is missing from h3_to_territory must fog,
        never crash or leak."""
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelLedger

        rows = [_hex_row(h3_index="h_unmapped", heat=0.8)]

        features = EngineBridge._aggregate_hex_features(
            rows,
            "county",
            reach=frozenset({"T1"}),
            ledger=IntelLedger(),
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
            h3_to_territory={},  # h_unmapped resolves to nothing
        )

        assert features[0]["properties"]["heat"] is None

    def test_ledger_entry_serves_exact_political_values_outside_reach(self) -> None:
        """A fresh IntelLedger entry (INVESTIGATE resolution) makes a
        masked-by-reach hex's political fields exact again, in the
        aggregate — the ledger path works at this zoom too, not just reach."""
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelEntry, IntelLedger

        rows = [_hex_row(h3_index="h1", heat=0.8, dominant_class="core_proletariat")]
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=10,
                value_snapshot={"heat": 0.8, "dominant_class": "core_proletariat"},
            )
        )

        features = EngineBridge._aggregate_hex_features(
            rows,
            "county",
            reach=frozenset(),
            ledger=ledger,
            tick=10,
            staleness_ticks=5,
            unknown_ticks=20,
            h3_to_territory={"h1": "T1"},
        )

        props = features[0]["properties"]
        assert props["heat"] == pytest.approx(0.8)
        assert props["dominant_class"] == "core_proletariat"


class TestGetInspectorHexFog:
    """The single-hex drill-down half of Task 5's file list."""

    def _graph_with_org_reach(self) -> BabylonGraph:
        """One player org, two territories: T_IN carries a PRESENCE edge
        from the org (in reach), T_OUT does not. Both are TENANCY-tenanted
        by C1 so dominant_class/solidarity_index/agitation are real,
        non-None values on both — proving FOG hides T_OUT's, not absence."""
        graph = BabylonGraph()
        graph.add_node("ORGP", node_type="organization", name="Player Org")
        graph.graph["player_org_id"] = "ORGP"
        graph.add_node(
            "T_IN",
            node_type="territory",
            h3_index="871_in",
            name="In Reach",
            biocapacity=1.0,
            max_biocapacity=1.0,
        )
        graph.add_node(
            "T_OUT",
            node_type="territory",
            h3_index="871_out",
            name="Out of Reach",
            biocapacity=1.0,
            max_biocapacity=1.0,
        )
        graph.add_edge("ORGP", "T_IN", edge_type="presence")
        graph.add_node(
            "C1",
            node_type="social_class",
            role="proletariat",
            population=100,
            ideology={"agitation": 0.5},
        )
        graph.add_edge("C1", "T_IN", edge_type="tenancy")
        graph.add_edge("C1", "T_OUT", edge_type="tenancy")
        return graph

    def _bridge(self, graph: BabylonGraph) -> Any:
        from unittest.mock import MagicMock

        from game.engine_bridge import EngineBridge

        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        return EngineBridge(mock_persistence)

    def test_out_of_reach_territory_masks_political_fields(self) -> None:
        import uuid

        graph = self._graph_with_org_reach()
        bridge = self._bridge(graph)

        result = bridge.get_inspector_hex(uuid.uuid4(), "871_out")

        assert result["dominant_class"] is None
        assert result["solidarity_index"] is None
        assert result["agitation"] is None
        assert set(result["vision_masked"]) >= {
            "dominant_class",
            "solidarity_index",
            "agitation",
        }

    def test_in_reach_territory_is_exact(self) -> None:
        import uuid

        graph = self._graph_with_org_reach()
        bridge = self._bridge(graph)

        result = bridge.get_inspector_hex(uuid.uuid4(), "871_in")

        assert result["dominant_class"] == "proletariat"
        assert result["agitation"] == pytest.approx(0.5)
        assert result["vision_masked"] == []

    def test_material_fields_present_regardless_of_reach(self) -> None:
        import uuid

        graph = self._graph_with_org_reach()
        bridge = self._bridge(graph)

        result = bridge.get_inspector_hex(uuid.uuid4(), "871_out")

        assert result["id"] == "T_OUT"
        assert result["h3_index"] == "871_out"
        assert result["habitability"] == pytest.approx(1.0)
        assert "org_presence" in result
