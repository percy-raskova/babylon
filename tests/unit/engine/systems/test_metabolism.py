"""Tests for MetabolismSystem - The Metabolic Rift.

Slice 1.4: The ecological limits of capital accumulation.

TDD Red Phase: These tests define the contract for the MetabolismSystem.
The tests WILL FAIL initially because MetabolismSystem does not exist yet.
This is the correct Red phase outcome.

Test Intent:
- Biocapacity regeneration when extraction = 0
- Biocapacity depletion when extraction > regeneration
- ECOLOGICAL_OVERSHOOT event emitted when consumption > biocapacity
- No event when system is sustainable (consumption <= biocapacity)
- Biocapacity clamped at zero (cannot go negative)
- Biocapacity clamped at max (cannot exceed ceiling)
- Multiple territories aggregated correctly

Key Formulas (from src/babylon/systems/formulas.py):
- calculate_biocapacity_delta(regeneration_rate, max_biocapacity, extraction_intensity,
                               current_biocapacity, entropy_factor=1.2) -> float
- calculate_overshoot_ratio(total_consumption, total_biocapacity) -> float

Formula Behavior:
- regeneration = regeneration_rate * max_biocapacity (if current < max, else 0)
- extraction = extraction_intensity * current_biocapacity * entropy_factor
- delta = regeneration - extraction
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem  # Will fail - doesn't exist
from babylon.models.enums import EventType


@pytest.mark.unit
class TestMetabolismSystemBasic:
    """Test basic biocapacity dynamics behavior."""

    def test_system_has_name(self) -> None:
        """MetabolismSystem should have a descriptive name."""
        system = MetabolismSystem()
        assert system.name == "Metabolism"

    def test_regeneration_only(self) -> None:
        """Biocapacity regenerates when extraction = 0.

        Scenario: Nature heals when left alone
        - Territory at 50% capacity (biocapacity=50, max=100)
        - regeneration_rate=0.1, extraction_intensity=0.0
        - regeneration = 0.1 * 100 = 10
        - extraction = 0 (no extraction)
        - delta = 10 - 0 = 10
        - Expected: biocapacity becomes 60.0 (50 + 10)
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=50.0,
            max_biocapacity=100.0,
            regeneration_rate=0.1,
            extraction_intensity=0.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        new_biocapacity = graph.nodes["T001"]["biocapacity"]
        assert new_biocapacity == pytest.approx(60.0, abs=0.01)

    def test_extraction_degrades_capacity(self) -> None:
        """High extraction depletes biocapacity stock.

        Scenario: Industrial extraction exceeds regeneration
        - Territory at full capacity (biocapacity=100, max=100)
        - regeneration_rate=0.1, extraction_intensity=0.5
        - At max capacity, regeneration = 0 (per formula: no regen when current >= max)
        - extraction = 0.5 * 100 * 1.2 = 60
        - delta = 0 - 60 = -60
        - Expected: biocapacity becomes 40.0 (100 - 60)
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.1,
            extraction_intensity=0.5,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        new_biocapacity = graph.nodes["T001"]["biocapacity"]
        assert new_biocapacity == pytest.approx(40.0, abs=0.01)

    def test_biocapacity_clamped_at_zero(self) -> None:
        """Biocapacity cannot go negative, clamped to 0.0.

        Scenario: Extreme extraction that would result in negative
        - Small biocapacity (biocapacity=10, max=100)
        - Very high extraction (extraction_intensity=1.0)
        - extraction = 1.0 * 10 * 1.2 = 12 (more than available)
        - regeneration = 0.1 * 100 = 10
        - delta = 10 - 12 = -2, so 10 + (-2) = 8 (still positive in this case)
        - For a more extreme case, use extraction_intensity=1.0 with regen=0.0
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=5.0,
            max_biocapacity=100.0,
            regeneration_rate=0.0,  # No regeneration
            extraction_intensity=1.0,  # Maximum extraction
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: extraction = 1.0 * 5.0 * 1.2 = 6, delta = 0 - 6 = -6
        # new_biocapacity = 5 + (-6) = -1, clamped to 0
        new_biocapacity = graph.nodes["T001"]["biocapacity"]
        assert new_biocapacity == 0.0

    def test_biocapacity_clamped_at_max(self) -> None:
        """Biocapacity cannot exceed max_biocapacity ceiling.

        Scenario: High regeneration cannot exceed ceiling
        - biocapacity=95, max=100, regeneration_rate=0.1
        - regeneration = 0.1 * 100 = 10 (would push to 105)
        - Expected: clamped at max_biocapacity = 100
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=95.0,
            max_biocapacity=100.0,
            regeneration_rate=0.1,  # Would add 10
            extraction_intensity=0.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: 95 + 10 = 105, clamped to 100
        new_biocapacity = graph.nodes["T001"]["biocapacity"]
        assert new_biocapacity == 100.0


@pytest.mark.unit
class TestMetabolismSystemEvents:
    """Test event emission from MetabolismSystem."""

    def test_overshoot_event_trigger(self) -> None:
        """ECOLOGICAL_OVERSHOOT event emitted when consumption > biocapacity.

        Scenario: Warning light activates when overshooting
        - Low biocapacity territory (biocapacity=10.0)
        - High consumption class (s_bio=5.0, s_class=10.0, consumption_needs=15.0)
        - Overshoot ratio = 15 / 10 = 1.5 > 1.0
        - Expected: ECOLOGICAL_OVERSHOOT event published
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Territory with low biocapacity
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=10.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        # Social class with high consumption needs
        # consumption_needs = s_bio + s_class = 5 + 10 = 15
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=5.0,
            s_class=10.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 5}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 1

        event = overshoot_events[0]
        assert event.tick == 5
        assert event.payload["overshoot_ratio"] == pytest.approx(1.5, abs=0.01)
        assert event.payload["total_consumption"] == pytest.approx(15.0, abs=0.01)
        assert event.payload["total_biocapacity"] == pytest.approx(10.0, abs=0.01)

    def test_no_event_when_sustainable(self) -> None:
        """No ECOLOGICAL_OVERSHOOT event when consumption <= biocapacity.

        Scenario: System is healthy, no alarm needed
        - High biocapacity territory (biocapacity=100.0)
        - Low consumption class (s_bio=5.0, s_class=5.0, consumption_needs=10.0)
        - Overshoot ratio = 10 / 100 = 0.1 < 1.0
        - Expected: No events in event_bus history
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Territory with high biocapacity
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        # Social class with low consumption needs
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=5.0,
            s_class=5.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: No ECOLOGICAL_OVERSHOOT events
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 0

    def test_exactly_at_threshold_no_event(self) -> None:
        """No event when overshoot_ratio exactly equals 1.0.

        The threshold is > 1.0, not >= 1.0. Exact balance is sustainable.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        # Consumption exactly equals biocapacity
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=50.0,
            s_class=50.0,  # Total = 100
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: No event at exact threshold
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 0


@pytest.mark.unit
class TestMetabolismSystemAggregation:
    """Test aggregation of multiple territories and classes."""

    def test_multiple_territories_summed(self) -> None:
        """Total biocapacity is sum of all territory biocapacities.

        Scenario: Multiple territories aggregate correctly
        - T001: biocapacity=60.0
        - T002: biocapacity=40.0
        - Total biocapacity = 100.0
        - Consumption = 80.0
        - Overshoot ratio = 80/100 = 0.8 (sustainable)
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=60.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            biocapacity=40.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        # Single class with consumption = 80
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=30.0,
            s_class=50.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: No overshoot event (80/100 = 0.8 < 1.0)
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 0

    def test_multiple_classes_summed(self) -> None:
        """Total consumption is sum of all class consumption needs.

        Scenario: Multiple classes aggregate correctly
        - C001: s_bio=5, s_class=15 -> 20
        - C002: s_bio=5, s_class=25 -> 30
        - Total consumption = 50.0
        - Biocapacity = 40.0
        - Overshoot ratio = 50/40 = 1.25 (overshoot!)
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=40.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        # Two classes with combined consumption = 50
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=5.0,
            s_class=15.0,  # Total = 20
        )
        graph.add_node(
            "C002",
            _node_type="social_class",
            s_bio=5.0,
            s_class=25.0,  # Total = 30
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 10}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: Overshoot event (50/40 = 1.25 > 1.0)
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 1

        event = overshoot_events[0]
        assert event.payload["overshoot_ratio"] == pytest.approx(1.25, abs=0.01)
        assert event.payload["total_consumption"] == pytest.approx(50.0, abs=0.01)
        assert event.payload["total_biocapacity"] == pytest.approx(40.0, abs=0.01)


@pytest.mark.unit
class TestMetabolismSystemEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_no_territories_no_crash(self) -> None:
        """System handles empty graph gracefully.

        Edge case: Graph has no territory nodes.
        Expected: No crash, possibly no events or appropriate handling.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # Only a social class node, no territories
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=5.0,
            s_class=5.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act - should not raise
        system.step(graph, services, context)

        # Assert: No crash occurred, exact behavior TBD but should not error

    def test_no_social_classes_no_crash(self) -> None:
        """System handles graph with only territories.

        Edge case: Graph has no social class nodes.
        Expected: No crash, consumption = 0, no overshoot.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: No overshoot (consumption = 0)
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 0

    def test_zero_biocapacity_territory(self) -> None:
        """System handles depleted territory (biocapacity = 0).

        Edge case: Territory is already depleted.
        - regeneration = 0.02 * 100 = 2 (still regenerates)
        - extraction = 0 (nothing to extract from 0)
        - delta = 2 - 0 = 2
        - new_biocapacity = 0 + 2 = 2
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=0.0,  # Depleted
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.5,  # Trying to extract from nothing
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: Regeneration still works, extraction is 0.5 * 0 * 1.2 = 0
        # delta = 2 - 0 = 2, new_biocapacity = 0 + 2 = 2
        new_biocapacity = graph.nodes["T001"]["biocapacity"]
        assert new_biocapacity == pytest.approx(2.0, abs=0.01)

    def test_ignores_non_territory_nodes_for_biocapacity(self) -> None:
        """System only processes nodes with _node_type='territory' for biocapacity.

        Edge case: Graph has nodes without _node_type or with different type.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Real territory
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=50.0,
            max_biocapacity=100.0,
            regeneration_rate=0.1,
            extraction_intensity=0.0,
        )

        # Node without _node_type (should be ignored for biocapacity calc)
        graph.add_node(
            "X001",
            biocapacity=1000.0,  # Would skew results if counted
            max_biocapacity=1000.0,
            regeneration_rate=0.1,
            extraction_intensity=0.0,
        )

        # Social class with consumption = 60 (overshoot if only T001 counts)
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=20.0,
            s_class=40.0,  # Total = 60
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: Overshoot event because only T001's biocapacity counts
        # Overshoot ratio = 60 / 50 = 1.2 (if X001 counted: 60/1050 = 0.057)
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]

        # After regeneration: T001 goes from 50 to 60, so 60/60 = 1.0 exactly
        # But before biocapacity update, consumption check uses pre-update biocapacity
        # The exact behavior depends on implementation order.
        # For TDD, we assert what SHOULD happen: check after biocapacity update
        # At tick=1, biocapacity updates first: 50 + 10 = 60
        # Then overshoot check: 60/60 = 1.0, which is NOT > 1.0
        assert len(overshoot_events) == 0  # Sustainable after regeneration

    def test_ignores_non_social_class_nodes_for_consumption(self) -> None:
        """System only processes nodes with _node_type='social_class' for consumption.

        Edge case: Graph has nodes with different _node_type for consumption calc.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.0,
        )

        # Real social class
        graph.add_node(
            "C001",
            _node_type="social_class",
            s_bio=5.0,
            s_class=5.0,  # Total = 10
        )

        # Node with s_bio/s_class but wrong _node_type (should be ignored)
        graph.add_node(
            "X001",
            _node_type="faction",  # Not a social_class
            s_bio=1000.0,
            s_class=1000.0,  # Would cause overshoot if counted
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = MetabolismSystem()

        # Act
        system.step(graph, services, context)

        # Assert: No overshoot (only C001's consumption = 10, biocapacity = 100)
        events = services.event_bus.get_history()
        overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
        assert len(overshoot_events) == 0
