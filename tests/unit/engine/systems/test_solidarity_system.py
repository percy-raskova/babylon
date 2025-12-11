"""Tests for SolidaritySystem - Proletarian Internationalism.

Sprint 3.4.2: The Counterforce to Imperial Rent Bribery.

TDD Red Phase: These tests define the contract for the SolidaritySystem.

Test Intent:
- Consciousness transmission via SOLIDARITY edges
- Unidirectional flow (Periphery -> Core)
- solidarity_strength stored on edge (NOT auto-calculated)
- CONSCIOUSNESS_TRANSMISSION event emitted
- MASS_AWAKENING event when target crosses threshold
- Fascist Bifurcation: no transmission when solidarity_strength=0
"""

import networkx as nx
import pytest

from babylon.config.defines import GameDefines, SolidarityDefines
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.models.enums import EdgeType, EventType


@pytest.mark.unit
class TestSolidaritySystemBasic:
    """Test basic consciousness transmission behavior."""

    def test_system_has_name(self) -> None:
        """SolidaritySystem should have a descriptive name."""
        system = SolidaritySystem()
        assert system.name == "Solidarity"

    def test_consciousness_transmission_basic(self) -> None:
        """Consciousness transmits from high source to low target.

        Scenario A: Revolutionary
        - P_w consciousness = 0.9 (revolutionary)
        - C_w consciousness = 0.1 (passive)
        - solidarity_strength = 0.8 (strong infrastructure)

        Expected: delta = 0.8 * (0.9 - 0.1) = 0.64
        New C_w consciousness = 0.1 + 0.64 = 0.74
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # P_w: Periphery worker in revolutionary struggle (consciousness 0.9)
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # C_w: Core worker (passive consumer, consciousness 0.1)
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        # SOLIDARITY edge with strong infrastructure
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert
        # New consciousness = 0.1 + 0.64 = 0.74
        new_ideology = graph.nodes["C_w"]["ideology"]
        assert new_ideology["class_consciousness"] == pytest.approx(0.74, abs=0.01)

    def test_no_transmission_below_activation_threshold(self) -> None:
        """No transmission if source consciousness below activation threshold."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # P_w: consciousness = 0.2 (below 0.3 threshold)
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.2, "national_identity": 0.8, "agitation": 0.0}
        )
        # C_w: consciousness 0.1
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No change (below activation threshold)
        assert graph.nodes["C_w"]["ideology"]["class_consciousness"] == pytest.approx(0.1, abs=0.01)


@pytest.mark.unit
class TestSolidaritySystemFascistBifurcation:
    """Test the Fascist Bifurcation scenario.

    CRITICAL DESIGN DECISION: solidarity_strength is stored on edge.

    When solidarity_strength=0, NO consciousness transmits even if
    periphery is in full revolutionary struggle. This enables the
    Fascist turn scenario where global capitalism crushes isolated revolts.
    """

    def test_zero_solidarity_strength_no_transmission(self) -> None:
        """Scenario B: Fascist - zero solidarity means no awakening.

        Same nodes as revolutionary scenario, but solidarity_strength=0.
        Result: Core workers remain passive consumers -> Fascist turn.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9 (revolutionary)
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # consciousness 0.1 (passive)
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        # SOLIDARITY edge but NO infrastructure (fascist scenario)
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,  # Key difference!
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No change despite revolutionary periphery
        assert graph.nodes["C_w"]["ideology"]["class_consciousness"] == pytest.approx(0.1, abs=0.01)

    def test_solidarity_strength_scales_transmission(self) -> None:
        """Higher solidarity_strength = stronger transmission."""
        results: dict[float, float] = {}

        for sigma in [0.2, 0.5, 0.8]:
            # Arrange
            graph: nx.DiGraph[str] = nx.DiGraph()
            # consciousness 0.9
            graph.add_node(
                "P_w",
                ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0},
            )
            # consciousness 0.1
            graph.add_node(
                "C_w",
                ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0},
            )

            graph.add_edge(
                "P_w",
                "C_w",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=sigma,
            )

            services = ServiceContainer.create()
            context: dict[str, int] = {"tick": 1}
            system = SolidaritySystem()

            # Act
            system.step(graph, services, context)

            # Store result - higher class_consciousness means more revolutionary
            results[sigma] = graph.nodes["C_w"]["ideology"]["class_consciousness"]

        # Assert: Higher sigma = higher class_consciousness (more revolutionary)
        assert results[0.8] > results[0.5] > results[0.2]


@pytest.mark.unit
class TestSolidaritySystemEvents:
    """Test event emission from SolidaritySystem."""

    def test_consciousness_transmission_emits_event(self) -> None:
        """CONSCIOUSNESS_TRANSMISSION event emitted when delta > 0.01."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # consciousness 0.1
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 5}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        # Should have at least CONSCIOUSNESS_TRANSMISSION
        transmission_events = [e for e in events if e.type == EventType.CONSCIOUSNESS_TRANSMISSION]
        assert len(transmission_events) >= 1

        event = transmission_events[0]
        assert event.tick == 5
        assert event.payload["source_id"] == "P_w"
        assert event.payload["target_id"] == "C_w"
        assert event.payload["delta"] == pytest.approx(0.64, abs=0.01)
        assert event.payload["solidarity_strength"] == 0.8

    def test_mass_awakening_event_when_threshold_crossed(self) -> None:
        """MASS_AWAKENING event when target crosses mass awakening threshold."""
        # Arrange: Start C_w just below mass_awakening_threshold (0.6)
        # consciousness 0.5 (below 0.6 threshold)
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # consciousness 0.5 (below 0.6 threshold)
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.5, "national_identity": 0.5, "agitation": 0.0}
        )

        # delta = 0.8 * (0.9 - 0.5) = 0.32
        # new_consciousness = 0.5 + 0.32 = 0.82 (crosses 0.6 threshold!)
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 10}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        awakening_events = [e for e in events if e.type == EventType.MASS_AWAKENING]
        assert len(awakening_events) == 1

        event = awakening_events[0]
        assert event.tick == 10
        assert event.payload["target_id"] == "C_w"
        assert event.payload["new_consciousness"] >= 0.6

    def test_no_event_on_negligible_transmission(self) -> None:
        """No event when delta is negligible (< 0.01)."""
        # Arrange: Almost equal consciousness
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # consciousness ~0.895 (very close)
        graph.add_node(
            "C_w",
            ideology={"class_consciousness": 0.895, "national_identity": 0.105, "agitation": 0.0},
        )

        # delta = 0.1 * (0.9 - 0.895) = 0.0005 (negligible)
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.1,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No transmission events (delta too small)
        events = services.event_bus.get_history()
        transmission_events = [e for e in events if e.type == EventType.CONSCIOUSNESS_TRANSMISSION]
        assert len(transmission_events) == 0


@pytest.mark.unit
class TestSolidaritySystemEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_only_solidarity_edges_processed(self) -> None:
        """Only SOLIDARITY edge type triggers transmission."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # consciousness 0.1
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        # Non-SOLIDARITY edge with solidarity_strength set
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.8,  # Would transmit if SOLIDARITY
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No change (wrong edge type)
        assert graph.nodes["C_w"]["ideology"]["class_consciousness"] == pytest.approx(0.1, abs=0.01)

    def test_multiple_solidarity_edges(self) -> None:
        """Multiple solidarity edges accumulate transmissions."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w1",
            ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0},
        )
        # consciousness 0.8
        graph.add_node(
            "P_w2",
            ideology={"class_consciousness": 0.8, "national_identity": 0.2, "agitation": 0.0},
        )
        # consciousness 0.1
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        # Two solidarity edges pointing to same target
        graph.add_edge(
            "P_w1",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )
        graph.add_edge(
            "P_w2",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: C_w should be more revolutionary than single edge
        # Original: consciousness 0.1
        # delta1 = 0.3 * (0.9 - 0.1) = 0.24
        # After first: consciousness = 0.1 + 0.24 = 0.34
        # delta2 = 0.3 * (0.8 - 0.34) = 0.138
        # After second: consciousness = 0.34 + 0.138 = 0.478

        new_consciousness = graph.nodes["C_w"]["ideology"]["class_consciousness"]
        assert new_consciousness > 0.1  # More revolutionary than start
        assert new_consciousness == pytest.approx(0.478, abs=0.05)

    def test_consciousness_clamped_to_bounds(self) -> None:
        """Consciousness stays in [0, 1] range after transmission."""
        # Arrange: Extreme case that would exceed bounds
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 1.0
        graph.add_node(
            "P_w", ideology={"class_consciousness": 1.0, "national_identity": 0.0, "agitation": 0.0}
        )
        # consciousness 0.95
        graph.add_node(
            "C_w",
            ideology={"class_consciousness": 0.95, "national_identity": 0.05, "agitation": 0.0},
        )

        # delta = 1.0 * (1.0 - 0.95) = 0.05
        # new_consciousness = 0.95 + 0.05 = 1.0 (clamped)
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=1.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: class_consciousness clamped to valid range [0, 1]
        new_consciousness = graph.nodes["C_w"]["ideology"]["class_consciousness"]
        assert 0.0 <= new_consciousness <= 1.0

    def test_missing_ideology_defaults_to_zero(self) -> None:
        """Nodes without ideology attribute default to 0 consciousness (neutral)."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        graph.add_node("C_w")  # No ideology attribute - defaults to consciousness 0.0

        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: C_w should have ideology set now
        # Default consciousness = 0.0 (from missing ideology)
        # delta = 0.5 * (0.9 - 0.0) = 0.45
        # new_consciousness = 0.0 + 0.45 = 0.45
        assert "ideology" in graph.nodes["C_w"]
        assert graph.nodes["C_w"]["ideology"]["class_consciousness"] == pytest.approx(
            0.45, abs=0.01
        )


@pytest.mark.unit
class TestSolidaritySystemConfig:
    """Test that SolidaritySystem respects configuration parameters."""

    def test_custom_activation_threshold(self) -> None:
        """System uses config's solidarity_activation_threshold."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness = 0.35 (above default 0.3, below custom 0.4)
        graph.add_node(
            "P_w",
            ideology={"class_consciousness": 0.35, "national_identity": 0.65, "agitation": 0.0},
        )
        # consciousness 0.1
        graph.add_node(
            "C_w", ideology={"class_consciousness": 0.1, "national_identity": 0.9, "agitation": 0.0}
        )

        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        # Custom defines with higher threshold (now in GameDefines, not SimulationConfig)
        custom_solidarity = SolidarityDefines(activation_threshold=0.4)
        defines = GameDefines(solidarity=custom_solidarity)
        services = ServiceContainer.create(defines=defines)
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No transmission (below custom threshold)
        assert graph.nodes["C_w"]["ideology"]["class_consciousness"] == pytest.approx(0.1, abs=0.01)

    def test_custom_mass_awakening_threshold(self) -> None:
        """System uses defines' mass_awakening_threshold for events."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # consciousness 0.9
        graph.add_node(
            "P_w", ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0}
        )
        # consciousness = 0.45
        graph.add_node(
            "C_w",
            ideology={"class_consciousness": 0.45, "national_identity": 0.55, "agitation": 0.0},
        )

        # delta = 0.5 * (0.9 - 0.45) = 0.225
        # new_consciousness = 0.45 + 0.225 = 0.675 (above default 0.6)
        # But below custom 0.8 threshold
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )

        # Custom defines with higher threshold (now in GameDefines, not SimulationConfig)
        custom_solidarity = SolidarityDefines(mass_awakening_threshold=0.8)
        defines = GameDefines(solidarity=custom_solidarity)
        services = ServiceContainer.create(defines=defines)
        context: dict[str, int] = {"tick": 1}
        system = SolidaritySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No MASS_AWAKENING event (below custom threshold)
        events = services.event_bus.get_history()
        awakening_events = [e for e in events if e.type == EventType.MASS_AWAKENING]
        assert len(awakening_events) == 0
