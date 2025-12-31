"""Unit tests for VitalitySystem - The Reaper.

TDD tests for the Material Reality Refactor.
Entities die when wealth < consumption_needs (s_bio + s_class).
Death is marked by setting active=False and emitting ENTITY_DEATH event.

These tests are written BEFORE implementation (RED phase of TDD).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.vitality import VitalitySystem
from babylon.models.enums import EventType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.event_bus import Event


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_entity_node(
    graph: nx.DiGraph,
    node_id: str,
    role: SocialRole = SocialRole.PERIPHERY_PROLETARIAT,
    wealth: float = 1.0,
    s_bio: float = 0.01,
    s_class: float = 0.0,
    active: bool = True,
) -> None:
    """Add an entity node to the graph with vitality-relevant attributes.

    Args:
        graph: The graph to add the node to.
        node_id: The node ID.
        role: Social role of the entity.
        wealth: Current wealth.
        s_bio: Biological minimum consumption (default 0.01).
        s_class: Social reproduction consumption (default 0.0).
        active: Whether entity is alive (default True).
    """
    graph.add_node(
        node_id,
        role=role,
        wealth=wealth,
        s_bio=s_bio,
        s_class=s_class,
        active=active,
        _node_type="social_class",
    )


@pytest.mark.unit
class TestVitalitySystem:
    """Tests for VitalitySystem death mechanics."""

    def test_starving_entity_dies(self, services: ServiceContainer) -> None:
        """Entity with wealth=0 and positive consumption_needs should die.

        consumption_needs = s_bio + s_class = 0.01 + 0.0 = 0.01
        wealth (0.0) < consumption_needs (0.01) → DEATH
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.0,  # Starving
            s_bio=0.01,  # Needs food
            s_class=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity is now dead
        assert graph.nodes["C001"]["active"] is False
        # Assert: ENTITY_DEATH event emitted
        assert len(events) == 1
        assert events[0].payload["entity_id"] == "C001"
        assert events[0].payload["wealth"] == 0.0
        assert events[0].payload["consumption_needs"] == pytest.approx(0.01)

    def test_wealthy_entity_survives(self, services: ServiceContainer) -> None:
        """Entity with wealth >= consumption_needs should survive.

        wealth (0.1) >= consumption_needs (0.01) → SURVIVE
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.1,  # Has enough
            s_bio=0.01,
            s_class=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity survives
        assert graph.nodes["C001"]["active"] is True
        # Assert: No death event
        assert len(events) == 0

    def test_only_starving_entities_die(self, services: ServiceContainer) -> None:
        """Multiple entities: only those with wealth < consumption_needs die."""
        graph: nx.DiGraph = nx.DiGraph()

        # Rich entity (survives)
        _create_entity_node(graph, "C001", wealth=10.0, s_bio=0.01)
        # Poor entity (dies)
        _create_entity_node(graph, "C002", wealth=0.0, s_bio=0.01)
        # Borderline entity (survives - wealth == consumption_needs)
        _create_entity_node(graph, "C003", wealth=0.01, s_bio=0.01)

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Only C002 died
        assert graph.nodes["C001"]["active"] is True
        assert graph.nodes["C002"]["active"] is False
        assert graph.nodes["C003"]["active"] is True

        # Assert: Only one death event (for C002)
        assert len(events) == 1
        assert events[0].payload["entity_id"] == "C002"

    def test_already_dead_entities_skipped(self, services: ServiceContainer) -> None:
        """Entities with active=False should not trigger additional death events."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.0,
            s_bio=0.01,
            active=False,  # Already dead
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: No death event (already dead)
        assert len(events) == 0
        # Assert: Still dead
        assert graph.nodes["C001"]["active"] is False

    def test_non_entity_nodes_skipped(self, services: ServiceContainer) -> None:
        """Territory nodes and other non-entity nodes should be skipped."""
        graph: nx.DiGraph = nx.DiGraph()

        # Add territory (not an entity)
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
        )
        # Add entity for comparison
        _create_entity_node(graph, "C001", wealth=0.0, s_bio=0.01)

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Only entity died, territory unchanged
        assert graph.nodes["C001"]["active"] is False
        assert len(events) == 1
        assert events[0].payload["entity_id"] == "C001"

    def test_high_s_class_increases_death_threshold(self, services: ServiceContainer) -> None:
        """Entity with high social reproduction costs dies at higher wealth.

        consumption_needs = s_bio + s_class = 0.01 + 0.09 = 0.10
        wealth (0.05) < consumption_needs (0.10) → DEATH
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.05,  # Has some wealth
            s_bio=0.01,
            s_class=0.09,  # High social reproduction needs
        )

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity died despite having some wealth
        assert graph.nodes["C001"]["active"] is False

    def test_vitality_system_name(self) -> None:
        """VitalitySystem should have correct name property."""
        system = VitalitySystem()
        assert system.name == "vitality"
