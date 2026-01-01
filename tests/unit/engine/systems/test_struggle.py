"""Tests for StruggleSystem - Terminal Crisis Dynamics.

Peripheral Revolt Mechanic (Phase 2):
When P(S|R) > P(S|A) for PERIPHERY_PROLETARIAT, revolt severs EXPLOITATION edges.

This models the anti-colonial revolution that cuts off imperial extraction,
triggering the cascade: no extraction → no wages → LA decomposition → carceral turn.

See ai-docs/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.struggle import StruggleSystem
from babylon.models.enums import EdgeType, EventType, SocialRole


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_imperial_circuit(graph: nx.DiGraph[str]) -> None:
    """Create a minimal imperial circuit with EXPLOITATION edges.

    Nodes:
    - P_w: Periphery proletariat (source of extraction)
    - Comprador: Periphery bourgeoisie (intermediary)
    - C_b: Core bourgeoisie (receives tribute)
    - C_w: Labor aristocracy (receives super-wages)

    Edges:
    - P_w --EXPLOITATION--> Comprador (periphery extraction)
    - P_w --EXPLOITATION--> C_b (direct exploitation - for testing)
    """
    # Periphery proletariat
    graph.add_node(
        "P_w",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=100.0,
        population=1000,
        active=True,
        organization=0.3,
        repression_faced=0.5,
        p_acquiescence=0.2,  # Low - desperate
        p_revolution=0.6,  # High - organized
        _node_type="social_class",
    )

    # Comprador bourgeoisie
    graph.add_node(
        "Comprador",
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        wealth=500.0,
        population=10,
        active=True,
        _node_type="social_class",
    )

    # Core bourgeoisie
    graph.add_node(
        "C_b",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10000.0,
        population=100,
        active=True,
        _node_type="social_class",
    )

    # Labor aristocracy
    graph.add_node(
        "C_w",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=2000.0,
        population=500,
        active=True,
        _node_type="social_class",
    )

    # EXPLOITATION edges from periphery
    graph.add_edge(
        "P_w",
        "Comprador",
        edge_type=EdgeType.EXPLOITATION,
        extraction_rate=0.5,
    )
    graph.add_edge(
        "P_w",
        "C_b",
        edge_type=EdgeType.EXPLOITATION,
        extraction_rate=0.3,
    )


@pytest.mark.unit
class TestPeripheralRevolt:
    """Peripheral revolt severs EXPLOITATION edges when revolution > acquiescence."""

    def test_revolt_severs_exploitation_edges_when_p_rev_gt_p_acq(
        self, services: ServiceContainer
    ) -> None:
        """When P(S|R) > P(S|A), periphery severs EXPLOITATION edges.

        This models anti-colonial revolution cutting off imperial extraction.
        The periphery says: "We'd rather fight than accept these conditions."
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_imperial_circuit(graph)

        # Verify edges exist before revolt
        exploitation_edges_before = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges_before) == 2, "Should have 2 EXPLOITATION edges"

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # After revolt: EXPLOITATION edges from P_w should be severed
        exploitation_edges_after = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges_after) == 0, "Revolt should sever EXPLOITATION edges"

    def test_no_revolt_when_p_acq_gt_p_rev(self, services: ServiceContainer) -> None:
        """No revolt when P(S|A) > P(S|R) - acquiescence is rational.

        When conditions are survivable through compliance, revolt doesn't occur.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_imperial_circuit(graph)

        # Override P_w to be acquiescent (high P(S|A), low P(S|R))
        graph.nodes["P_w"]["p_acquiescence"] = 0.8  # Comfortable
        graph.nodes["P_w"]["p_revolution"] = 0.2  # Low org, high repression

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # EXPLOITATION edges should remain intact
        exploitation_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 2, "No revolt = edges remain"

    def test_revolt_emits_peripheral_revolt_event(self, services: ServiceContainer) -> None:
        """PERIPHERAL_REVOLT event emitted with edges_severed count."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_imperial_circuit(graph)

        captured_events: list = []
        services.event_bus.subscribe(
            EventType.PERIPHERAL_REVOLT,
            lambda e: captured_events.append(e),
        )

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1, "Should emit exactly one PERIPHERAL_REVOLT"
        event = captured_events[0]
        assert event.payload["node_id"] == "P_w"
        assert event.payload["edges_severed"] == 2

    def test_revolt_only_severs_outgoing_exploitation_edges(
        self, services: ServiceContainer
    ) -> None:
        """Revolt severs edges where the revolting entity is the SOURCE.

        EXPLOITATION edges point FROM exploited TO exploiter.
        P_w as SOURCE means "P_w is being exploited by target".
        Revolt severs these edges (P_w stops being exploited).
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_imperial_circuit(graph)

        # Add a non-exploitation edge that should NOT be severed
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # SOLIDARITY edge should remain
        solidarity_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.SOLIDARITY
        ]
        assert len(solidarity_edges) == 1, "SOLIDARITY edges preserved"

    def test_inactive_entity_does_not_revolt(self, services: ServiceContainer) -> None:
        """Dead/inactive entities cannot revolt."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_imperial_circuit(graph)

        # Mark P_w as inactive (dead)
        graph.nodes["P_w"]["active"] = False

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # Edges should remain (dead can't revolt)
        exploitation_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 2

    def test_revolt_occurs_at_threshold_equality(self, services: ServiceContainer) -> None:
        """Revolt does NOT occur when P(S|R) == P(S|A) (need strict >)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_imperial_circuit(graph)

        # Equal probabilities - not enough for revolt
        graph.nodes["P_w"]["p_acquiescence"] = 0.5
        graph.nodes["P_w"]["p_revolution"] = 0.5

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        exploitation_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 2, "Equality = no revolt"
