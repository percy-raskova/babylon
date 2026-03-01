"""Tests for Layer 3 consequence propagation (Feature 032).

Verifies consciousness aggregation, heat propagation, edge transitions,
infrastructure effects, and contestation stacking.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, ConsciousnessTendency, EdgeType, EventType
from babylon.ooda.layer3 import process_layer3
from babylon.ooda.types import Action, ActionResult
from babylon.organizations.types import ConsciousnessDelta


def _make_result(
    action_type: ActionType,
    target_id: str = "comm_1",
    org_id: str = "org_1",
    ci_delta: float | None = None,
    tendency: ConsciousnessTendency = ConsciousnessTendency.REVOLUTIONARY,
    direct_effects: dict[str, Any] | None = None,
    events: list[str] | None = None,
) -> ActionResult:
    """Create an ActionResult with optional consciousness delta."""
    action = Action(
        org_id=org_id,
        action_type=action_type,
        target_id=target_id,
    )

    consciousness_delta = None
    if ci_delta is not None:
        consciousness_delta = ConsciousnessDelta(
            collective_identity_delta=ci_delta,
            tendency_pressure=tendency,
            tendency_magnitude=abs(ci_delta),
            source_org_id=org_id,
        )

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=consciousness_delta,
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


class TestConsciousnessAggregation:
    """Consciousness deltas aggregate across multiple org actions."""

    def test_single_delta_updates_ci(self) -> None:
        """Single org's CI delta updates community collective_identity."""
        graph = _make_community_graph(ci=0.3)
        results = [_make_result(ActionType.EDUCATE, ci_delta=0.02)]

        summary = process_layer3(results, graph, OODADefines())

        new_ci = graph.nodes["comm_1"]["collective_identity"]
        assert new_ci == pytest.approx(0.32)
        assert "consciousness" in summary

    def test_multiple_deltas_aggregate(self) -> None:
        """Multiple orgs' CI deltas sum before application."""
        graph = _make_community_graph(ci=0.3)
        results = [
            _make_result(ActionType.EDUCATE, ci_delta=0.02, org_id="org_1"),
            _make_result(ActionType.EDUCATE, ci_delta=0.01, org_id="org_2"),
        ]

        process_layer3(results, graph, OODADefines())

        new_ci = graph.nodes["comm_1"]["collective_identity"]
        assert new_ci == pytest.approx(0.33)

    def test_ci_clamped_at_one(self) -> None:
        """CI never exceeds 1.0 after aggregation."""
        graph = _make_community_graph(ci=0.95)
        results = [_make_result(ActionType.EDUCATE, ci_delta=0.1)]

        process_layer3(results, graph, OODADefines())

        new_ci = graph.nodes["comm_1"]["collective_identity"]
        assert new_ci == pytest.approx(1.0)

    def test_ci_clamped_at_zero(self) -> None:
        """CI never goes below 0.0 after aggregation."""
        graph = _make_community_graph(ci=0.05)
        results = [
            _make_result(
                ActionType.EDUCATE,
                ci_delta=-0.1,
                tendency=ConsciousnessTendency.LIBERAL,
            )
        ]

        process_layer3(results, graph, OODADefines())

        new_ci = graph.nodes["comm_1"]["collective_identity"]
        assert new_ci == pytest.approx(0.0)

    def test_no_ci_delta_no_change(self) -> None:
        """Actions without CI delta don't change collective_identity."""
        graph = _make_community_graph(ci=0.3)
        results = [_make_result(ActionType.AGITATE, ci_delta=None)]

        process_layer3(results, graph, OODADefines())

        new_ci = graph.nodes["comm_1"]["collective_identity"]
        assert new_ci == pytest.approx(0.3)

    def test_multiple_communities_independent(self) -> None:
        """CI updates are independent across communities."""
        graph = _make_community_graph("comm_1", ci=0.3)
        graph.add_node(
            "comm_2",
            _node_type="community",
            id="comm_2",
            collective_identity=0.5,
            heat=0.0,
            infrastructure=0.5,
            ideological_contestation=0.2,
        )
        results = [
            _make_result(ActionType.EDUCATE, target_id="comm_1", ci_delta=0.02),
            _make_result(ActionType.EDUCATE, target_id="comm_2", ci_delta=0.05),
        ]

        process_layer3(results, graph, OODADefines())

        assert graph.nodes["comm_1"]["collective_identity"] == pytest.approx(0.32)
        assert graph.nodes["comm_2"]["collective_identity"] == pytest.approx(0.55)


class TestHeatPropagation:
    """SURVEIL/REPRESS actions increase community heat."""

    def test_repress_increases_heat(self) -> None:
        """REPRESS action increases target community heat."""
        graph = _make_community_graph(heat=0.1)
        results = [
            _make_result(
                ActionType.REPRESS,
                ci_delta=0.03,
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
                ci_delta=0.01,
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
                ci_delta=0.03,
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


class TestContestationPropagation:
    """AGITATE stacks contestation delta."""

    def test_agitate_increases_contestation(self) -> None:
        """AGITATE action increases target community ideological_contestation."""
        defines = OODADefines()
        graph = _make_community_graph(contestation=0.2)
        results = [
            _make_result(
                ActionType.AGITATE,
                direct_effects={"contestation_delta": defines.agitation_contestation_delta},
            )
        ]

        process_layer3(results, graph, defines)

        new_contest = graph.nodes["comm_1"]["ideological_contestation"]
        assert new_contest == pytest.approx(0.2 + defines.agitation_contestation_delta)

    def test_multiple_agitate_stack(self) -> None:
        """Multiple AGITATE actions stack contestation."""
        defines = OODADefines()
        graph = _make_community_graph(contestation=0.2)
        results = [
            _make_result(
                ActionType.AGITATE,
                org_id="org_1",
                direct_effects={"contestation_delta": defines.agitation_contestation_delta},
            ),
            _make_result(
                ActionType.AGITATE,
                org_id="org_2",
                direct_effects={"contestation_delta": defines.agitation_contestation_delta},
            ),
        ]

        process_layer3(results, graph, defines)

        new_contest = graph.nodes["comm_1"]["ideological_contestation"]
        expected = 0.2 + 2 * defines.agitation_contestation_delta
        assert new_contest == pytest.approx(expected)

    def test_contestation_clamped_at_one(self) -> None:
        """Contestation never exceeds 1.0."""
        defines = OODADefines()
        graph = _make_community_graph(contestation=0.95)
        results = [
            _make_result(
                ActionType.AGITATE,
                direct_effects={"contestation_delta": defines.agitation_contestation_delta},
            )
        ]

        process_layer3(results, graph, defines)

        new_contest = graph.nodes["comm_1"]["ideological_contestation"]
        assert new_contest <= 1.0
