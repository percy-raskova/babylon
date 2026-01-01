"""Tests for LA Decomposition - Terminal Crisis Dynamics Phase 4.

When SUPERWAGE_CRISIS occurs (C_b can't afford wages), the Labor Aristocracy
decomposes into two fractions (tunable via GameDefines.carceral):
- 15% become CARCERAL_ENFORCER (guards, cops, prison staff) [default]
- 85% fall into INTERNAL_PROLETARIAT (precariat, unemployed, incarcerated) [default]

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


def _create_test_context(
    tick: int = 1,
    *,
    include_superwage_tick: bool = True,
) -> dict[str, object]:
    """Create a test context with required persistent data.

    The DecompositionSystem requires _superwage_crisis_tick to know when
    SUPERWAGE_CRISIS occurred so it can enforce the decomposition_delay.
    For unit tests, we set this to a tick far enough in the past that
    the delay (52 ticks default) has already elapsed.

    Args:
        tick: Current tick number.
        include_superwage_tick: If True, set _superwage_crisis_tick so
            decomposition fires immediately. Set False to test behavior
            when no crisis has occurred.
    """
    context: dict[str, object] = {"tick": tick}
    if include_superwage_tick:
        # Crisis happened 100 ticks ago, well past the 52-tick delay
        context["_superwage_crisis_tick"] = tick - 100
    return context


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
        population=1000,  # Will split: 150 enforcer, 850 proletariat (15/85 default)
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


@pytest.mark.unit
class TestLADecomposition:
    """LA decomposes into enforcers + internal proletariat on crisis."""

    def test_decomposition_splits_population_15_85(self, services: ServiceContainer) -> None:
        """LA population splits 15% enforcer / 85% proletariat (default).

        Given LA with population=1000:
        - 150 go to CARCERAL_ENFORCER (added to existing 50 = 200 total)
        - 850 go to INTERNAL_PROLETARIAT (was dormant at 0 = 850 total)
        - LA becomes inactive (pop remains but entity dead)
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        # Capture original populations
        la_pop_before = graph.nodes["C_w"]["population"]
        enforcer_pop_before = graph.nodes["Enforcer"]["population"]

        # Create system - context indicates crisis already happened and delay elapsed
        system = DecompositionSystem()

        # Process decomposition (no need to trigger event, context has _superwage_crisis_tick)
        system.step(graph, services, _create_test_context())

        # Verify LA is now inactive
        assert graph.nodes["C_w"]["active"] is False, "LA should be deactivated"

        # Verify enforcer population grew by 15% of LA (default from GameDefines)
        expected_enforcer_gain = int(la_pop_before * 0.15)
        expected_enforcer_total = enforcer_pop_before + expected_enforcer_gain
        assert graph.nodes["Enforcer"]["population"] == expected_enforcer_total

        # Verify internal proletariat activated with 85% of LA (default from GameDefines)
        expected_proletariat = int(la_pop_before * 0.85)
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
        system.step(graph, services, _create_test_context())

        assert len(captured_events) == 1, "Should emit CLASS_DECOMPOSITION"
        event = captured_events[0]
        assert event.payload["source_class"] == "C_w"
        assert event.payload["enforcer_fraction"] == 0.15  # GameDefines default
        assert event.payload["proletariat_fraction"] == 0.85  # GameDefines default
        assert "population_transferred" in event.payload

    def test_no_decomposition_without_crisis(self, services: ServiceContainer) -> None:
        """LA remains stable if no SUPERWAGE_CRISIS occurs."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        la_pop_before = graph.nodes["C_w"]["population"]
        enforcer_pop_before = graph.nodes["Enforcer"]["population"]

        system = DecompositionSystem()

        # Step WITHOUT crisis (no _superwage_crisis_tick in context)
        system.step(graph, services, _create_test_context(include_superwage_tick=False))

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

        # First crisis - decomposition happens (context tracks completion)
        context = _create_test_context(tick=1)
        system.step(graph, services, context)

        enforcer_after_first = graph.nodes["Enforcer"]["population"]
        proletariat_after_first = graph.nodes["Int_P"]["population"]

        # Second step - should NOT decompose again (_decomposition_complete is set)
        context["tick"] = 2  # type: ignore[typeddict-unknown-key]
        system.step(graph, services, context)

        # Populations unchanged from first decomposition
        assert graph.nodes["Enforcer"]["population"] == enforcer_after_first
        assert graph.nodes["Int_P"]["population"] == proletariat_after_first

    def test_decomposition_handles_missing_enforcer(self, services: ServiceContainer) -> None:
        """If no CARCERAL_ENFORCER exists, decomposition still works.

        LA still decomposes, but enforcer population is lost (no target).
        Internal proletariat still receives 85% (default from GameDefines).
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        # Remove the enforcer entity
        graph.remove_node("Enforcer")

        system = DecompositionSystem()
        system.step(graph, services, _create_test_context())

        # LA still decomposes
        assert graph.nodes["C_w"]["active"] is False

        # Internal proletariat still activated
        assert graph.nodes["Int_P"]["active"] is True
        assert graph.nodes["Int_P"]["population"] == 850  # 85% of 1000

    def test_decomposition_handles_missing_internal_proletariat(
        self, services: ServiceContainer
    ) -> None:
        """If no INTERNAL_PROLETARIAT exists, decomposition still works.

        Enforcers get their 15% (default from GameDefines), proletariat portion is lost.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        # Remove the internal proletariat entity
        graph.remove_node("Int_P")

        system = DecompositionSystem()
        system.step(graph, services, _create_test_context())

        # LA still decomposes
        assert graph.nodes["C_w"]["active"] is False

        # Enforcers get their share
        assert graph.nodes["Enforcer"]["population"] == 200  # 50 + 15% of 1000

    def test_decomposition_transfers_wealth_proportionally(
        self, services: ServiceContainer
    ) -> None:
        """Wealth is transferred along with population."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_pre_crisis_circuit(graph)

        la_wealth_before = graph.nodes["C_w"]["wealth"]  # 500.0
        enforcer_wealth_before = graph.nodes["Enforcer"]["wealth"]  # 100.0

        system = DecompositionSystem()
        system.step(graph, services, _create_test_context())

        # Enforcer gets 15% of LA wealth added to existing (default from GameDefines)
        expected_enforcer_wealth = enforcer_wealth_before + (la_wealth_before * 0.15)
        assert graph.nodes["Enforcer"]["wealth"] == pytest.approx(expected_enforcer_wealth)

        # Internal proletariat gets 85% of LA wealth (default from GameDefines)
        expected_proletariat_wealth = la_wealth_before * 0.85
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
        system.step(graph, services, _create_test_context())

        assert len(captured_events) == 1
        assert "narrative_hint" in captured_events[0].payload
