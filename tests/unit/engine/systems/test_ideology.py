"""Tests for ConsciousnessSystem - Wealth Extraction Tracking.

TDD Red Phase: Periphery Dynamics Fix.

The ConsciousnessSystem currently only tracks wage_change between ticks.
Periphery workers experience wealth extraction via EXPLOITATION edges,
not wage cuts. This test suite verifies that the system:

1. Tracks wealth changes between ticks (like it does for wages)
2. Detects wealth extraction as a crisis condition
3. Generates agitation from wealth loss (not just wage cuts)

This enables periphery workers (who have no incoming WAGES edges)
to develop consciousness from their material exploitation.
"""

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem


@pytest.mark.unit
class TestConsciousnessSystemWealthTracking:
    """Tests for wealth extraction detection in ConsciousnessSystem.

    These tests will FAIL until:
    1. ConsciousnessSystem tracks previous_wealth in persistent context
    2. calculate_ideological_routing accepts wealth_change parameter
    """

    def test_system_tracks_wealth_between_ticks(self) -> None:
        """ConsciousnessSystem should track wealth changes between ticks.

        Similar to how it tracks wage_change, the system should:
        1. Store previous wealth in persistent context
        2. Calculate wealth_change = current_wealth - previous_wealth
        3. Pass wealth_change to the ideological routing formula
        """
        # Arrange: Graph with a periphery worker
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )

        services = ServiceContainer.create()
        system = ConsciousnessSystem()
        # When using dict context, system stores directly in the dict (not nested)
        context: dict[str, object] = {"tick": 0}

        # Act: First tick establishes baseline
        system.step(graph, services, context)

        # Verify: Previous wealth should be stored in persistent context
        assert "previous_wealth" in context
        previous_wealth = context["previous_wealth"]
        assert isinstance(previous_wealth, dict)
        assert previous_wealth["C001"] == 1.0

    def test_wealth_extraction_generates_agitation(self) -> None:
        """Wealth loss between ticks should generate agitation.

        Scenario: Periphery worker C001
        - Tick 0: wealth = 1.0 (baseline established)
        - Between ticks: EXPLOITATION edge extracts 0.5 wealth
        - Tick 1: wealth = 0.5 (wealth_change = -0.5)
        - Expected: agitation increases due to material loss
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )

        services = ServiceContainer.create()
        system = ConsciousnessSystem()
        context: dict[str, object] = {"tick": 0}

        # First tick: establishes baseline wealth
        system.step(graph, services, context)

        # Simulate extraction: wealth reduced between ticks
        graph.nodes["C001"]["wealth"] = 0.5  # Lost 0.5 wealth

        # Second tick: should detect wealth loss
        context["tick"] = 1
        system.step(graph, services, context)

        # Assert: Agitation should increase OR ideology should shift
        # (routing depends on solidarity pressure)
        ideology = graph.nodes["C001"]["ideology"]
        # Either agitation increases OR national_identity increases (fascist path)
        has_response = ideology["agitation"] > 0.0 or ideology["national_identity"] > 0.5
        assert has_response, "Wealth extraction should generate agitation or ideology shift"

    def test_wealth_extraction_routes_to_fascism_without_solidarity(self) -> None:
        """Wealth loss without solidarity should route to national_identity.

        When a periphery worker experiences wealth extraction but has no
        incoming SOLIDARITY edges, the agitation routes to national_identity
        (fascist path) rather than class_consciousness.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )
        # No incoming SOLIDARITY edges - isolated worker

        services = ServiceContainer.create()
        system = ConsciousnessSystem()
        context: dict[str, object] = {"tick": 0}

        # First tick
        system.step(graph, services, context)

        # Simulate extraction
        graph.nodes["C001"]["wealth"] = 0.3  # Major extraction

        # Second tick
        context["tick"] = 1
        system.step(graph, services, context)

        # Assert: national_identity should increase (fascist bifurcation)
        ideology = graph.nodes["C001"]["ideology"]
        assert ideology["national_identity"] > 0.5, (
            "Without solidarity, wealth extraction routes to fascism"
        )

    def test_wealth_extraction_routes_to_revolution_with_solidarity(self) -> None:
        """Wealth loss with solidarity should route to class_consciousness.

        When a periphery worker experiences wealth extraction and HAS
        incoming SOLIDARITY edges from revolutionary sources, the agitation
        routes to class_consciousness (revolutionary path).
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        # C001: Periphery worker (target of solidarity)
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )

        # C004: Revolutionary source with high consciousness
        graph.add_node(
            "C004",
            wealth=0.5,
            ideology={
                "class_consciousness": 0.9,  # Revolutionary consciousness
                "national_identity": 0.1,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )

        # SOLIDARITY edge from revolutionary source to C001
        from babylon.models.enums import EdgeType

        graph.add_edge(
            "C004",
            "C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,  # Strong infrastructure
        )

        services = ServiceContainer.create()
        system = ConsciousnessSystem()
        context: dict[str, object] = {"tick": 0}

        # First tick
        system.step(graph, services, context)

        # Simulate extraction
        graph.nodes["C001"]["wealth"] = 0.3  # Major extraction

        # Second tick
        context["tick"] = 1
        system.step(graph, services, context)

        # Assert: class_consciousness should increase (revolutionary path)
        ideology = graph.nodes["C001"]["ideology"]
        assert ideology["class_consciousness"] > 0.5, (
            "With solidarity, wealth extraction routes to revolution"
        )

    def test_no_wealth_change_produces_no_new_agitation(self) -> None:
        """Stable wealth should not generate new agitation.

        If wealth doesn't change between ticks, no crisis is detected
        and no new agitation is generated (existing agitation decays).
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.2,  # Pre-existing agitation
            },
            _node_type="social_class",
        )

        services = ServiceContainer.create()
        system = ConsciousnessSystem()
        context: dict[str, object] = {"tick": 0}

        # First tick
        system.step(graph, services, context)
        initial_agitation = graph.nodes["C001"]["ideology"]["agitation"]

        # Wealth stays the same (no extraction)
        # graph.nodes["C001"]["wealth"] = 1.0  # unchanged

        # Second tick
        context["tick"] = 1
        system.step(graph, services, context)

        # Assert: agitation should decay, not increase
        final_agitation = graph.nodes["C001"]["ideology"]["agitation"]
        assert final_agitation <= initial_agitation, (
            "Stable wealth should not generate new agitation"
        )


@pytest.mark.unit
class TestConsciousnessSystemPersistentContext:
    """Tests for persistent context handling in ConsciousnessSystem."""

    def test_handles_tick_context_format(self) -> None:
        """System should handle TickContext with persistent_data attribute."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )

        services = ServiceContainer.create()
        system = ConsciousnessSystem()

        # TickContext-style with persistent_data as attribute
        class MockTickContext:
            tick = 0
            persistent_data: dict[str, object] = {}

        context = MockTickContext()

        # Act: Should not raise
        system.step(graph, services, context)  # type: ignore[arg-type]

        # Assert: Wealth should be tracked in persistent_data
        assert "previous_wealth" in context.persistent_data

    def test_handles_dict_context_format(self) -> None:
        """System should handle plain dict context."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            wealth=1.0,
            ideology={
                "class_consciousness": 0.5,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
            _node_type="social_class",
        )

        services = ServiceContainer.create()
        system = ConsciousnessSystem()
        context: dict[str, object] = {"tick": 0}

        # Act: Should not raise
        system.step(graph, services, context)

        # Assert: Wealth should be tracked in context dict
        assert "previous_wealth" in context
