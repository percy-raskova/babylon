"""Tests for SUPERWAGE_CRISIS detection in ImperialRentSystem.

Terminal Crisis Dynamics Phase 3:
When the imperial rent pool is exhausted and C_b can't afford super-wages,
SUPERWAGE_CRISIS is emitted, signaling the beginning of LA decomposition.

This is triggered by peripheral revolt cutting off extraction.

See ai-docs/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, EventType, SocialRole


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_depleted_circuit(graph: nx.DiGraph[str]) -> None:
    """Create an imperial circuit AFTER peripheral revolt cut off extraction.

    This simulates:
    - NO EXPLOITATION edges (revolt severed them)
    - WAGES edge exists (infrastructure remains)
    - C_b has wealth (capital) but no income flow
    - Pool is empty (set to 0 in economy metadata)

    The crisis triggers because wage infrastructure exists but pool = 0.
    """
    # Set economy metadata with DEPLETED pool
    graph.graph["economy"] = {
        "imperial_rent_pool": 0.0,  # Pool exhausted!
        "current_super_wage_rate": 0.2,
        "current_repression_level": 0.3,
    }

    # Core bourgeoisie - has capital but no income
    graph.add_node(
        "C_b",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=1000.0,  # Has savings
        population=100,
        active=True,
        _node_type="social_class",
    )

    # Labor aristocracy - waiting for wages
    graph.add_node(
        "C_w",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=200.0,
        population=500,
        active=True,
        _node_type="social_class",
    )

    # WAGES edge exists (infrastructure) - but no pool to pay from
    graph.add_edge(
        "C_b",
        "C_w",
        edge_type=EdgeType.WAGES,
        value_flow=0.0,
    )


def _create_healthy_circuit(graph: nx.DiGraph[str]) -> None:
    """Create a healthy imperial circuit with tribute flowing."""
    # Comprador with tribute to send
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
        wealth=1000.0,
        population=100,
        active=True,
        _node_type="social_class",
    )

    # Labor aristocracy
    graph.add_node(
        "C_w",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=200.0,
        population=500,
        active=True,
        _node_type="social_class",
    )

    # Periphery proletariat (for exploitation)
    graph.add_node(
        "P_w",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=50.0,
        population=1000,
        active=True,
        _node_type="social_class",
    )

    # EXPLOITATION edge - P_w exploited by Comprador
    graph.add_edge(
        "P_w",
        "Comprador",
        edge_type=EdgeType.EXPLOITATION,
        extraction_rate=0.5,
    )

    # TRIBUTE edge - Comprador pays C_b
    graph.add_edge(
        "Comprador",
        "C_b",
        edge_type=EdgeType.TRIBUTE,
        value_flow=0.0,
    )

    # WAGES edge - C_b pays C_w
    graph.add_edge(
        "C_b",
        "C_w",
        edge_type=EdgeType.WAGES,
        value_flow=0.0,
    )


@pytest.mark.unit
class TestSuperwageCrisis:
    """SUPERWAGE_CRISIS emitted when pool exhausted but wages desired."""

    def test_crisis_emitted_when_pool_exhausted(self, services: ServiceContainer) -> None:
        """SUPERWAGE_CRISIS emitted when wage infrastructure exists but pool = 0.

        After peripheral revolt, there's no extraction/tribute.
        C_b has capital (wealth > 0) but no income (pool = 0).
        The WAGES edge exists, so wages SHOULD be paid, but can't.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_depleted_circuit(graph)

        captured_events: list = []
        services.event_bus.subscribe(
            EventType.SUPERWAGE_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ImperialRentSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1, "Should emit SUPERWAGE_CRISIS"
        event = captured_events[0]
        assert event.payload["payer_id"] == "C_b"
        assert event.payload["available_pool"] <= 0
        assert event.payload["bourgeoisie_wealth"] > 0  # C_b has capital but no income

    def test_no_crisis_when_wages_paid_normally(self, services: ServiceContainer) -> None:
        """No crisis when super-wages are paid from healthy pool."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_healthy_circuit(graph)

        captured_events: list = []
        services.event_bus.subscribe(
            EventType.SUPERWAGE_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ImperialRentSystem()
        system.step(graph, services, {"tick": 1})

        # Should NOT emit crisis - wages were paid
        superwage_crises = [e for e in captured_events if e.type == EventType.SUPERWAGE_CRISIS]
        assert len(superwage_crises) == 0, "No crisis when wages paid"

    def test_crisis_includes_narrative_hint(self, services: ServiceContainer) -> None:
        """SUPERWAGE_CRISIS payload includes narrative hint for AI observer."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_depleted_circuit(graph)

        captured_events: list = []
        services.event_bus.subscribe(
            EventType.SUPERWAGE_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ImperialRentSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        event = captured_events[0]
        assert "narrative_hint" in event.payload
