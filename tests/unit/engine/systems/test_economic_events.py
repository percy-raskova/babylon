"""Tests for ImperialRentSystem event emission.

RED Phase: These tests define the contract for SURPLUS_EXTRACTION events.
The ImperialRentSystem must emit events when imperial rent is extracted,
enabling the AI Narrative layer to react to economic exploitation dynamics.

Test Intent:
- SURPLUS_EXTRACTION event emitted when rent > 0.01
- No event when rent is negligible (floating point noise)
- Event payload contains source_id, target_id, amount, mechanism
"""

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, EventType


class TestImperialRentSystemEvents:
    """Test event emission from ImperialRentSystem."""

    @pytest.mark.unit
    def test_rent_extraction_emits_event(self) -> None:
        """SURPLUS_EXTRACTION event emitted when rent > 0.01."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("worker", wealth=0.5, ideology=0.0)
        graph.add_node("owner", wealth=0.5)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 5}
        system = ImperialRentSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        assert len(events) == 1
        event = events[0]
        assert event.type == EventType.SURPLUS_EXTRACTION
        assert event.tick == 5
        assert event.payload["source_id"] == "worker"
        assert event.payload["target_id"] == "owner"
        assert event.payload["amount"] > 0.01
        assert event.payload["mechanism"] == "imperial_rent"

    @pytest.mark.unit
    def test_no_event_on_zero_rent(self) -> None:
        """No event when rent is negligible (< 0.01)."""
        # Arrange: Worker with 0 wealth = 0 rent
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("worker", wealth=0.0, ideology=0.0)
        graph.add_node("owner", wealth=0.5)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = ImperialRentSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        assert len(events) == 0
