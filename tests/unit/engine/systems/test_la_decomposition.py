"""Tests for LA Decomposition - Terminal Crisis Dynamics Phase 4.

When SUPERWAGE_CRISIS occurs (C_b can't afford wages), the Labor Aristocracy
decomposes into two fractions:
- 30% become CARCERAL_ENFORCER (guards, cops, prison staff)
- 70% fall into INTERNAL_PROLETARIAT (precariat, unemployed, incarcerated)

This models the shift from productive jobs to carceral jobs as the imperial
economy contracts. The enforcers exist at genesis (not dormant) - they consume
a portion of LA jobs from the start.

See ai-docs/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.event_bus import Event
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.decomposition import DecompositionSystem
from babylon.models.enums import EdgeType, EventType, SocialRole


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_pre_crisis_circuit(graph: nx.DiGraph[str]) -> None:
    """Create circuit BEFORE LA decomposition.

    This simulates the moment after SUPERWAGE_CRISIS but before decomposition:
    - LA exists with population
    - CARCERAL_ENFORCER exists (guards always exist, not dormant)
    - INTERNAL_PROLETARIAT is dormant (pop=0, inactive)
    """
    # Labor aristocracy - about to decompose
    graph.add_node(
        "C_w",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=500.0,
        population=1000,  # Will split: 300 enforcer, 700 proletariat
        active=True,
        _node_type="social_class",
    )

    # Carceral enforcers - exist at genesis with small population
    graph.add_node(
        "Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=100.0,
        population=50,  # Small initial force - will grow during decomposition
        active=True,
        _node_type="social_class",
    )

    # Internal proletariat - dormant until decomposition activates them
    graph.add_node(
        "Int_P",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=0.0,
        population=0,
        active=False,  # Dormant until LA decomposition
        _node_type="social_class",
    )

    # Core bourgeoisie - needed for context
    graph.add_node(
        "C_b",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=5000.0,
        population=100,
        active=True,
        _node_type="social_class",
    )

    # WAGES edge (will be defunct after crisis)
    graph.add_edge(
        "C_b",
        "C_w",
        edge_type=EdgeType.WAGES,
        value_flow=0.0,
    )


def _trigger_superwage_crisis(
    services: ServiceContainer,
    la_id: str = "C_w",
) -> None:
    """Simulate SUPERWAGE_CRISIS event emission."""
    services.event_bus.publish(
        Event(
            type=EventType.SUPERWAGE_CRISIS,
            tick=1,
            payload={
                "payer_id": "C_b",
                "receiver_id": la_id,
                "desired_wages": 100.0,
                "available_pool": 0.0,
                "bourgeoisie_wealth": 5000.0,
                "narrative_hint": "Test crisis",
            },
        )
    )


@pytest.mark.unit
class TestLADecomposition:
    """LA decomposes into enforcers + internal proletariat on crisis."""

    def test_decomposition_splits_population_30_70(self, services: ServiceContainer) -> None:
        """LA population splits 30% enforcer / 70% proletariat.

        Given LA with population=1000:
        - 300 go to CARCERAL_ENFORCER (added to existing 50 = 350 total)
        - 700 go to INTERNAL_PROLETARIAT (was dormant at 0 = 700 total)
        - LA becomes inactive (pop remains but entity dead)
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        # Capture original populations
        la_pop_before = graph.nodes["C_w"]["population"]
        enforcer_pop_before = graph.nodes["Enforcer"]["population"]

        # Create system and wire up to event bus
        system = DecompositionSystem()
        system.register_handlers(services.event_bus)

        # Trigger crisis
        _trigger_superwage_crisis(services)

        # Process decomposition
        system.step(graph, services, {"tick": 1})

        # Verify LA is now inactive
        assert graph.nodes["C_w"]["active"] is False, "LA should be deactivated"

        # Verify enforcer population grew by 30% of LA
        expected_enforcer_gain = int(la_pop_before * 0.3)
        expected_enforcer_total = enforcer_pop_before + expected_enforcer_gain
        assert graph.nodes["Enforcer"]["population"] == expected_enforcer_total

        # Verify internal proletariat activated with 70% of LA
        expected_proletariat = int(la_pop_before * 0.7)
        assert graph.nodes["Int_P"]["active"] is True
        assert graph.nodes["Int_P"]["population"] == expected_proletariat

    def test_decomposition_emits_class_decomposition_event(
        self, services: ServiceContainer
    ) -> None:
        """CLASS_DECOMPOSITION event emitted with population details."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CLASS_DECOMPOSITION,
            lambda e: captured_events.append(e),
        )

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1, "Should emit CLASS_DECOMPOSITION"
        event = captured_events[0]
        assert event.payload["source_class"] == "C_w"
        assert event.payload["enforcer_fraction"] == 0.3
        assert event.payload["proletariat_fraction"] == 0.7
        assert "population_transferred" in event.payload

    def test_no_decomposition_without_crisis(self, services: ServiceContainer) -> None:
        """LA remains stable if no SUPERWAGE_CRISIS occurs."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        la_pop_before = graph.nodes["C_w"]["population"]
        enforcer_pop_before = graph.nodes["Enforcer"]["population"]

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)

        # Step WITHOUT triggering crisis
        system.step(graph, services, {"tick": 1})

        # Populations unchanged
        assert graph.nodes["C_w"]["population"] == la_pop_before
        assert graph.nodes["C_w"]["active"] is True
        assert graph.nodes["Enforcer"]["population"] == enforcer_pop_before
        assert graph.nodes["Int_P"]["active"] is False

    def test_decomposition_only_once_per_la(self, services: ServiceContainer) -> None:
        """LA can only decompose once - subsequent crises ignored."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)

        # First crisis - decomposition happens
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 1})

        enforcer_after_first = graph.nodes["Enforcer"]["population"]
        proletariat_after_first = graph.nodes["Int_P"]["population"]

        # Second crisis - should NOT decompose again (LA is inactive)
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 2})

        # Populations unchanged from first decomposition
        assert graph.nodes["Enforcer"]["population"] == enforcer_after_first
        assert graph.nodes["Int_P"]["population"] == proletariat_after_first

    def test_decomposition_handles_missing_enforcer(self, services: ServiceContainer) -> None:
        """If no CARCERAL_ENFORCER exists, decomposition still works.

        LA still decomposes, but enforcer population is lost (no target).
        Internal proletariat still receives 70%.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        # Remove the enforcer entity
        graph.remove_node("Enforcer")

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 1})

        # LA still decomposes
        assert graph.nodes["C_w"]["active"] is False

        # Internal proletariat still activated
        assert graph.nodes["Int_P"]["active"] is True
        assert graph.nodes["Int_P"]["population"] == 700  # 70% of 1000

    def test_decomposition_handles_missing_internal_proletariat(
        self, services: ServiceContainer
    ) -> None:
        """If no INTERNAL_PROLETARIAT exists, decomposition still works.

        Enforcers get their 30%, proletariat portion is lost.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        # Remove the internal proletariat entity
        graph.remove_node("Int_P")

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 1})

        # LA still decomposes
        assert graph.nodes["C_w"]["active"] is False

        # Enforcers get their share
        assert graph.nodes["Enforcer"]["population"] == 350  # 50 + 30% of 1000

    def test_decomposition_transfers_wealth_proportionally(
        self, services: ServiceContainer
    ) -> None:
        """Wealth is transferred along with population."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        la_wealth_before = graph.nodes["C_w"]["wealth"]  # 500.0
        enforcer_wealth_before = graph.nodes["Enforcer"]["wealth"]  # 100.0

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 1})

        # Enforcer gets 30% of LA wealth added to existing
        expected_enforcer_wealth = enforcer_wealth_before + (la_wealth_before * 0.3)
        assert graph.nodes["Enforcer"]["wealth"] == pytest.approx(expected_enforcer_wealth)

        # Internal proletariat gets 70% of LA wealth
        expected_proletariat_wealth = la_wealth_before * 0.7
        assert graph.nodes["Int_P"]["wealth"] == pytest.approx(expected_proletariat_wealth)

    def test_decomposition_includes_narrative_hint(self, services: ServiceContainer) -> None:
        """CLASS_DECOMPOSITION event includes narrative for AI observer."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CLASS_DECOMPOSITION,
            lambda e: captured_events.append(e),
        )

        system = DecompositionSystem()
        system.register_handlers(services.event_bus)
        _trigger_superwage_crisis(services)
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        assert "narrative_hint" in captured_events[0].payload
