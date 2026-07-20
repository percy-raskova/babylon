"""Track 1 / Task 6 (2026-07-18, branch fix/null-play-coupling): SOLIDARITY
edges as literal lines on the map, fogged at the serialization boundary.

Unlike every other Track 1 fog surface (``_serialize_territory``/
``_serialize_organization``/hex rollups), which mask POLITICAL FIELDS on a
node that still appears, a SOLIDARITY edge's very EXISTENCE is political
information — so an out-of-reach edge must be OMITTED from the payload
entirely, never emitted with masked fields (there is no "masked edge" shape;
there is only "edge present" or "edge absent").

**Design decision (pinned by ``TestBothEndpointsRequired`` below): an edge is
visible only when BOTH endpoints are in organizing reach.** The ``either``
alternative was considered and rejected: if a class inside reach and a class
outside reach were joined by a visible edge, the payload would reveal that
the far class EXISTS and is a solidarity partner of the near one — exactly
the information the fog is meant to protect, leaked through the edge's mere
presence even with every field on the far class itself still masked
elsewhere. The map looking artificially severed at the reach boundary (an
organizer sees their own front go dark past its edge) is the accepted cost;
a false-negative (an edge invisible when it need not have been) is a UX
rough edge, but a false-positive (an edge visible when it should not have
been) is an intelligence leak. ``both`` errs toward the never-leak side,
consistent with Constitution III.11 and every other Track 1 gate's
default-deny posture.

Reuses ``_current_organizing_reach``/``organizing_reach`` (Task 2) — no new
BFS. Non-SOLIDARITY edges (EXPLOITATION/WAGES/TENANCY/TRIBUTE/ADJACENCY/...)
are MATERIAL, never gated, regardless of reach — mirrors every other Track 1
material/political split (``POLITICAL_FIELDS`` lists ``"solidarity"``, not
any other edge-type name).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from babylon.models.entities.relationship import Relationship
from babylon.models.enums import EdgeType

pytestmark = pytest.mark.unit


def _rel(
    source_id: str,
    target_id: str,
    edge_type: EdgeType = EdgeType.SOLIDARITY,
    solidarity_strength: float = 0.0,
) -> Relationship:
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        solidarity_strength=solidarity_strength,
    )


class TestFilterEdgesByReach:
    """The pure filter over already-serialized edge dicts
    (``_serialize_edge``'s output shape)."""

    def test_default_no_reach_is_unfogged_backward_compat(self) -> None:
        """Every pre-existing caller of ``_serialize_edge`` (e.g.
        ``_persist_snapshots_safe`` — an internal persistence path that MUST
        keep writing TRUE state) never threads ``reach`` at all — passing
        none must keep every edge, byte-identical to before this task."""
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        edges = [_serialize_edge(_rel("C1", "C2", solidarity_strength=0.7))]
        out = _filter_edges_by_reach(edges)

        assert out == edges

    def test_solidarity_edge_outside_reach_is_omitted_entirely(self) -> None:
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        edges = [_serialize_edge(_rel("C1", "C2", solidarity_strength=0.7))]
        out = _filter_edges_by_reach(edges, reach=frozenset())

        assert out == []

    def test_solidarity_edge_with_both_endpoints_in_reach_is_kept(self) -> None:
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        edges = [_serialize_edge(_rel("C1", "C2", solidarity_strength=0.7))]
        out = _filter_edges_by_reach(edges, reach=frozenset({"C1", "C2"}))

        assert out == edges
        assert out[0]["repression_flow"] == pytest.approx(0.7)

    def test_material_edge_stays_regardless_of_reach(self) -> None:
        """EXPLOITATION/WAGES/TENANCY/... are never gated — only SOLIDARITY
        edge existence is political."""
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        edges = [_serialize_edge(_rel("C1", "C2", edge_type=EdgeType.EXPLOITATION))]
        out = _filter_edges_by_reach(edges, reach=frozenset())

        assert out == edges

    def test_mixed_list_keeps_material_and_visible_solidarity_drops_the_rest(
        self,
    ) -> None:
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        visible_solidarity = _serialize_edge(_rel("C1", "C2", solidarity_strength=0.5))
        hidden_solidarity = _serialize_edge(_rel("C3", "C4", solidarity_strength=0.9))
        material = _serialize_edge(_rel("C1", "C5", edge_type=EdgeType.WAGES))

        out = _filter_edges_by_reach(
            [visible_solidarity, hidden_solidarity, material],
            reach=frozenset({"C1", "C2"}),
        )

        assert visible_solidarity in out
        assert material in out
        assert hidden_solidarity not in out
        assert len(out) == 2


class TestBothEndpointsRequired:
    """Pins the either-vs-both design decision explicitly, from both sides
    of the asymmetry (source-only-in-reach and target-only-in-reach)."""

    def test_only_source_in_reach_is_not_enough(self) -> None:
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        edges = [_serialize_edge(_rel("C1", "C2", solidarity_strength=0.7))]
        out = _filter_edges_by_reach(edges, reach=frozenset({"C1"}))

        assert out == []

    def test_only_target_in_reach_is_not_enough(self) -> None:
        from game.engine_bridge import _filter_edges_by_reach, _serialize_edge

        edges = [_serialize_edge(_rel("C1", "C2", solidarity_strength=0.7))]
        out = _filter_edges_by_reach(edges, reach=frozenset({"C2"}))

        assert out == []


class TestStateToSnapshotEdgesFog:
    """Integration through ``_state_to_snapshot`` — the real
    ``_current_organizing_reach(graph)`` call site (:func:`_state_to_snapshot`
    around line 9724), with a real graph establishing a non-trivial reach via
    the composed PRESENCE -> TENANCY -> SOLIDARITY traversal (Task 2)."""

    @staticmethod
    def _graph() -> Any:
        """ORGP has PRESENCE into T_IN, TENANCY-tenanted by C1. C1's
        SOLIDARITY ally C2 is in reach (radius-1 hop). C2's OWN ally C3 is
        one SOLIDARITY hop further out — NOT in reach at the default
        radius=1 (``defines.yaml``'s ``organizing_reach_radius``). This is
        the exact boundary ``TestBothEndpointsRequired`` pins in isolation,
        reproduced here through the real reach primitive rather than a
        hand-fed frozenset."""
        from babylon.models.enums import NodeType
        from babylon.topology.graph import BabylonGraph

        graph = BabylonGraph()
        graph.add_node("ORGP", NodeType.ORGANIZATION, name="Player Org")
        graph.set_graph_attr("player_org_id", "ORGP")
        graph.add_node("T_IN", NodeType.TERRITORY, name="In Reach")
        graph.add_edge("ORGP", "T_IN", edge_type="presence")
        graph.add_node("C1", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_node("C2", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_node("C3", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_edge("C1", "T_IN", edge_type="tenancy")
        graph.add_edge("C1", "C2", edge_type="solidarity", solidarity_strength=0.6)
        graph.add_edge("C2", "C3", edge_type="solidarity", solidarity_strength=0.4)
        return graph

    def test_in_reach_solidarity_edge_appears_in_the_snapshot(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _state_to_snapshot

        state = WorldState(
            tick=1,
            relationships=[_rel("C1", "C2", solidarity_strength=0.6)],
        )
        snapshot = _state_to_snapshot(state, uuid.uuid4(), graph=self._graph())

        edge_ids = {e["id"] for e in snapshot["edges"]}
        assert "C1-C2-solidarity" in edge_ids

    def test_boundary_solidarity_edge_is_omitted_from_the_snapshot(self) -> None:
        """C2 is in reach; C3 is one SOLIDARITY hop further than the
        radius=1 default covers. The C2<->C3 edge must be ABSENT — not
        present-with-masked-fields — from the snapshot's edges list."""
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _state_to_snapshot

        state = WorldState(
            tick=1,
            relationships=[_rel("C2", "C3", solidarity_strength=0.4)],
        )
        snapshot = _state_to_snapshot(state, uuid.uuid4(), graph=self._graph())

        edge_ids = {e["id"] for e in snapshot["edges"]}
        assert "C2-C3-solidarity" not in edge_ids
        assert snapshot["edges"] == []

    def test_material_edge_survives_alongside_a_hidden_solidarity_edge(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _state_to_snapshot

        state = WorldState(
            tick=1,
            relationships=[
                _rel("C2", "C3", solidarity_strength=0.4),  # hidden
                _rel("C3", "C1", edge_type=EdgeType.EXPLOITATION),  # material, kept
            ],
        )
        snapshot = _state_to_snapshot(state, uuid.uuid4(), graph=self._graph())

        edge_ids = {e["id"] for e in snapshot["edges"]}
        assert "C2-C3-solidarity" not in edge_ids
        assert "C3-C1-exploitation" in edge_ids


class TestBuildSolidarityEdgeLines:
    """The cockpit map layer's data source: territory-anchored SOLIDARITY
    edges for ``get_map_snapshot``'s metadata block, reusing
    ``_collect_solidarity_edges``/``_class_to_territory`` (the same
    territory-anchoring pattern already established for
    ``_build_field_state_edges``)."""

    @staticmethod
    def _graph() -> Any:
        from babylon.models.enums import NodeType
        from babylon.topology.graph import BabylonGraph

        graph = BabylonGraph()
        graph.add_node("ORGP", NodeType.ORGANIZATION, name="Player Org")
        graph.set_graph_attr("player_org_id", "ORGP")
        graph.add_node("T_IN", NodeType.TERRITORY, name="In Reach")
        graph.add_node("T_OUT", NodeType.TERRITORY, name="Out of Reach")
        graph.add_edge("ORGP", "T_IN", edge_type="presence")
        graph.add_node("C1", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_node("C2", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_node("C3", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_edge("C1", "T_IN", edge_type="tenancy")
        graph.add_edge("C3", "T_OUT", edge_type="tenancy")
        graph.add_edge("C1", "C2", edge_type="solidarity", solidarity_strength=0.6)
        graph.add_edge("C2", "C3", edge_type="solidarity", solidarity_strength=0.4)
        return graph

    def test_visible_edge_is_territory_anchored_with_its_strength(self) -> None:
        from game.engine_bridge import (
            _build_solidarity_edge_lines,
            _class_to_territory,
            _current_organizing_reach,
            _tenancy_members_by_territory,
        )

        graph = self._graph()
        reach = _current_organizing_reach(graph)
        class_territory = _class_to_territory(_tenancy_members_by_territory(graph))

        lines = _build_solidarity_edge_lines(graph, reach, class_territory)

        visible = [line for line in lines if {line["source"], line["target"]} == {"C1", "C2"}]
        assert len(visible) == 1
        assert visible[0]["source_territory"] == "T_IN"
        assert visible[0]["solidarity_strength"] == pytest.approx(0.6)

    def test_boundary_edge_omitted_never_a_masked_stub(self) -> None:
        from game.engine_bridge import (
            _build_solidarity_edge_lines,
            _class_to_territory,
            _current_organizing_reach,
            _tenancy_members_by_territory,
        )

        graph = self._graph()
        reach = _current_organizing_reach(graph)
        class_territory = _class_to_territory(_tenancy_members_by_territory(graph))

        lines = _build_solidarity_edge_lines(graph, reach, class_territory)

        hidden = [line for line in lines if {line["source"], line["target"]} == {"C2", "C3"}]
        assert hidden == []

    def test_no_reach_hides_every_edge(self) -> None:
        from game.engine_bridge import _build_solidarity_edge_lines, _class_to_territory

        graph = self._graph()
        class_territory = _class_to_territory({})

        lines = _build_solidarity_edge_lines(graph, frozenset(), class_territory)

        assert lines == []


class TestGetMapSnapshotSolidarityEdgesWiring:
    """The literal ``get_map_snapshot`` call site named in the task's file
    list — mirrors ``test_engine_bridge.py``'s
    ``TestBalkanizationMapFields`` mocking pattern (no real Django DB)."""

    @staticmethod
    def _graph() -> Any:
        from babylon.models.enums import NodeType
        from babylon.topology.graph import BabylonGraph

        graph = BabylonGraph()
        graph.graph["tick"] = 10
        graph.add_node("ORGP", NodeType.ORGANIZATION, name="Player Org")
        graph.set_graph_attr("player_org_id", "ORGP")
        graph.add_node("T_IN", NodeType.TERRITORY, name="In Reach")
        graph.add_node("T_OUT", NodeType.TERRITORY, name="Out of Reach")
        graph.add_edge("ORGP", "T_IN", edge_type="presence")
        graph.add_node("C1", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_node("C2", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_node("C3", NodeType.SOCIAL_CLASS, role="proletariat")
        graph.add_edge("C1", "T_IN", edge_type="tenancy")
        graph.add_edge("C3", "T_OUT", edge_type="tenancy")
        graph.add_edge("C1", "C2", edge_type="solidarity", solidarity_strength=0.6)
        graph.add_edge("C2", "C3", edge_type="solidarity", solidarity_strength=0.4)
        return graph

    def _get_snapshot(self) -> dict[str, Any]:
        from unittest.mock import MagicMock, patch

        from game.engine_bridge import EngineBridge

        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = self._graph()

        with patch("game.models.GameSession") as mock_session_model:
            mock_session_row = MagicMock()
            mock_session_row.current_tick = 10
            mock_session_row.scenario = "default"
            mock_session_model.objects.get.return_value = mock_session_row
            with patch("game.models.HexState") as mock_hex_state:
                mock_hex_state.objects.filter.return_value = []
                bridge = EngineBridge(mock_persistence)
                return bridge.get_map_snapshot(uuid.uuid4())

    def test_in_reach_edge_appears_territory_anchored_in_map_metadata(self) -> None:
        result = self._get_snapshot()

        edges = result["metadata"]["solidarity_edges"]
        visible = [e for e in edges if {e["source"], e["target"]} == {"C1", "C2"}]
        assert len(visible) == 1
        assert visible[0]["source_territory"] == "T_IN"
        assert visible[0]["solidarity_strength"] == pytest.approx(0.6)

    def test_boundary_edge_absent_from_map_metadata(self) -> None:
        result = self._get_snapshot()

        edges = result["metadata"]["solidarity_edges"]
        hidden = [e for e in edges if {e["source"], e["target"]} == {"C2", "C3"}]
        assert hidden == []
