"""Tests for Layer 3 consequence propagation (Feature 032).

Verifies consciousness aggregation, heat propagation, edge transitions,
infrastructure effects, and contestation stacking.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, EdgeType, EventType
from babylon.ooda.layer3 import process_layer3
from babylon.ooda.types import Action, ActionResult


def _make_result(
    action_type: ActionType,
    target_id: str = "comm_1",
    org_id: str = "org_1",
    direct_effects: dict[str, Any] | None = None,
    events: list[str] | None = None,
) -> ActionResult:
    """Create an ActionResult for layer3 testing."""
    action = Action(
        org_id=org_id,
        action_type=action_type,
        target_id=target_id,
    )

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=None,
        direct_effects=direct_effects or {},
        events_generated=events or [EventType.ORGANIZATIONAL_ACTION.value],
    )


def _make_community_graph(
    community_id: str = "comm_1",
    ci: float = 0.3,
    heat: float = 0.0,
    infrastructure: float = 0.5,
    contestation: float = 0.2,
) -> nx.DiGraph[str]:
    """Create a graph with a community node."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node(
        community_id,
        _node_type="community",
        id=community_id,
        collective_identity=ci,
        heat=heat,
        infrastructure=infrastructure,
        ideological_contestation=contestation,
    )
    return graph


class TestDerivedConsciousness:
    """Feature 034: consciousness and contestation are derived quantities."""

    def test_consciousness_not_directly_mutated(self) -> None:
        """process_layer3 does not directly mutate collective_identity."""
        graph = _make_community_graph(ci=0.3)
        results = [_make_result(ActionType.EDUCATE)]

        summary = process_layer3(results, graph, OODADefines())

        # CI unchanged — consciousness is now derived from org landscape
        assert graph.nodes["comm_1"]["collective_identity"] == pytest.approx(0.3)
        assert summary["consciousness"] == 0

    def test_contestation_not_directly_mutated(self) -> None:
        """process_layer3 does not directly mutate ideological_contestation."""
        graph = _make_community_graph(contestation=0.2)
        results = [
            _make_result(
                ActionType.AGITATE,
                direct_effects={"contestation_delta": 0.05},
            )
        ]

        summary = process_layer3(results, graph, OODADefines())

        # Contestation unchanged — now Shannon entropy of (r, l, f)
        assert graph.nodes["comm_1"]["ideological_contestation"] == pytest.approx(0.2)
        assert summary["contestation_updates"] == 0


class TestHeatPropagation:
    """SURVEIL/REPRESS actions increase community heat."""

    def test_repress_increases_heat(self) -> None:
        """REPRESS action increases target community heat."""
        graph = _make_community_graph(heat=0.1)
        results = [
            _make_result(
                ActionType.REPRESS,
                direct_effects={"backfire": True},
                events=[EventType.STATE_REPRESSION.value],
            )
        ]

        process_layer3(results, graph, OODADefines())

        new_heat = graph.nodes["comm_1"]["heat"]
        assert new_heat > 0.1

    def test_surveil_increases_heat(self) -> None:
        """SURVEIL action increases target community heat."""
        graph = _make_community_graph(heat=0.1)
        results = [
            _make_result(
                ActionType.SURVEIL,
                direct_effects={"backfire": True},
                events=[EventType.STATE_SURVEILLANCE.value],
            )
        ]

        process_layer3(results, graph, OODADefines())

        new_heat = graph.nodes["comm_1"]["heat"]
        assert new_heat > 0.1

    def test_heat_clamped_at_one(self) -> None:
        """Heat never exceeds 1.0."""
        graph = _make_community_graph(heat=0.95)
        results = [
            _make_result(
                ActionType.REPRESS,
                direct_effects={"backfire": True},
                events=[EventType.STATE_REPRESSION.value],
            )
        ]

        process_layer3(results, graph, OODADefines())

        new_heat = graph.nodes["comm_1"]["heat"]
        assert new_heat <= 1.0


class TestEdgeTransitions:
    """ORGANIZE triggers edge type transitions."""

    def test_organize_transitions_edge(self) -> None:
        """ORGANIZE action transitions TRANSACTIONAL edges to SOLIDARISTIC."""
        graph = _make_community_graph()
        graph.add_node("org_1", _node_type="organization")
        graph.add_edge(
            "org_1",
            "comm_1",
            edge_type=EdgeType.TRANSACTIONAL.value,
        )
        results = [_make_result(ActionType.ORGANIZE)]

        summary = process_layer3(results, graph, OODADefines())

        edge_data = graph.edges["org_1", "comm_1"]
        assert edge_data["edge_type"] == EdgeType.SOLIDARISTIC.value
        assert summary.get("edge_transitions", 0) >= 1

    def test_no_edge_no_transition(self) -> None:
        """ORGANIZE with no TRANSACTIONAL edge does nothing."""
        graph = _make_community_graph()
        results = [_make_result(ActionType.ORGANIZE)]

        summary = process_layer3(results, graph, OODADefines())

        assert summary.get("edge_transitions", 0) == 0


class TestInfrastructureEffects:
    """BUILD/ATTACK modify community infrastructure."""

    def test_build_increases_infrastructure(self) -> None:
        """BUILD_INFRASTRUCTURE increases community infrastructure."""
        graph = _make_community_graph(infrastructure=0.5)
        results = [_make_result(ActionType.BUILD_INFRASTRUCTURE)]

        process_layer3(results, graph, OODADefines())

        new_infra = graph.nodes["comm_1"]["infrastructure"]
        assert new_infra > 0.5

    def test_attack_decreases_infrastructure(self) -> None:
        """ATTACK_INFRASTRUCTURE decreases community infrastructure."""
        graph = _make_community_graph(infrastructure=0.5)
        results = [_make_result(ActionType.ATTACK_INFRASTRUCTURE)]

        process_layer3(results, graph, OODADefines())

        new_infra = graph.nodes["comm_1"]["infrastructure"]
        assert new_infra < 0.5

    def test_infrastructure_clamped_zero_to_one(self) -> None:
        """Infrastructure stays in [0, 1]."""
        graph = _make_community_graph(infrastructure=0.05)
        results = [_make_result(ActionType.ATTACK_INFRASTRUCTURE)]

        process_layer3(results, graph, OODADefines())

        new_infra = graph.nodes["comm_1"]["infrastructure"]
        assert 0.0 <= new_infra <= 1.0
