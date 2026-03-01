"""Tests for OODASystem orchestrator (Feature 032).

Verifies three-phase orchestration, system registration, and naming.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import networkx as nx

from babylon.config.defines import GameDefines
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import OrgType


def _make_services() -> MagicMock:
    """Create a mock ServiceContainer with real defines."""
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


def _make_graph_with_orgs() -> nx.DiGraph[str]:
    """Create a graph with a mix of org types."""
    graph: nx.DiGraph[str] = nx.DiGraph()

    # Business org
    graph.add_node(
        "ford",
        _node_type="organization",
        org_type=OrgType.BUSINESS.value,
        territory_ids=["detroit"],
        ooda_profile={"action_points": 3, "decision_mode": "autocratic"},
    )

    # Political faction
    graph.add_node(
        "rev_workers",
        _node_type="organization",
        org_type=OrgType.POLITICAL_FACTION.value,
        territory_ids=["detroit"],
        consciousness_tendency="revolutionary",
        ooda_profile={"action_points": 4, "decision_mode": "autocratic"},
    )

    # State apparatus
    graph.add_node(
        "fbi",
        _node_type="organization",
        org_type=OrgType.STATE_APPARATUS.value,
        territory_ids=["detroit"],
        jurisdiction="national",
        ooda_profile={"action_points": 5, "decision_mode": "autocratic"},
    )

    # Territory node (not an org)
    graph.add_node("detroit", _node_type="territory")

    return graph


class TestOODASystemProperties:
    """System name and protocol conformance."""

    def test_name(self) -> None:
        system = OODASystem()
        assert system.name == "ooda"

    def test_step_accepts_dict_context(self) -> None:
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = {"tick": 0}
        # Should not raise
        system.step(graph, services, context)


class TestThreePhaseOrchestration:
    """Verify Layer 0 → Action Phase → Layer 3 execution."""

    def test_layer0_processes_business(self) -> None:
        """Business orgs are handled in Layer 0."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = {"tick": 1}
        system.step(graph, services, context)

        # Event bus should have been called at least once
        assert services.event_bus.publish.called

    def test_action_phase_processes_non_business(self) -> None:
        """Non-Business orgs get NPC actions in action phase."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = {"tick": 1}
        system.step(graph, services, context)

        # Verify event was published with action counts
        call_args = services.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.payload["org_count"] >= 1

    def test_empty_graph_no_error(self) -> None:
        """Empty graph should not crash."""
        system = OODASystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        services = _make_services()
        context = {"tick": 0}
        system.step(graph, services, context)


class TestSystemRegistration:
    """Verify OODASystem is registered in simulation engine."""

    def test_registered_in_default_systems(self) -> None:
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

        system_names = [s.name for s in _DEFAULT_SYSTEMS]
        assert "ooda" in system_names

    def test_registered_after_edge_transition(self) -> None:
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

        system_names = [s.name for s in _DEFAULT_SYSTEMS]
        edge_idx = system_names.index("edge_transition")
        ooda_idx = system_names.index("ooda")
        assert ooda_idx > edge_idx
