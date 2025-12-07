"""Tests for babylon.models.world_state.

TDD Red Phase: These tests define the contract for WorldState.
WorldState is an immutable snapshot of the simulation at a specific tick.
It wraps NetworkX for graph operations while maintaining Pydantic validation.

Sprint 4: WorldState with NetworkX integration for Phase 2 game loop.
"""

import networkx as nx
import pytest
from pydantic import ValidationError

from babylon.models import EdgeType, Relationship, SocialClass, SocialRole
from babylon.models.world_state import WorldState

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
    )


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Core Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=0.5,
        ideology=0.0,
        organization=0.8,
        repression_faced=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.0,
        tension=0.0,
    )


@pytest.fixture
def two_node_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create a minimal WorldState with two nodes and one edge."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.topology
class TestWorldStateCreation:
    """WorldState should be createable with valid data."""

    def test_empty_state_creation(self) -> None:
        """Can create empty WorldState."""
        state = WorldState(tick=0)
        assert state.tick == 0
        assert len(state.entities) == 0
        assert len(state.relationships) == 0
        assert len(state.event_log) == 0

    def test_state_with_entities(self, worker: SocialClass, owner: SocialClass) -> None:
        """Can create WorldState with entities."""
        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
        )
        assert len(state.entities) == 2
        assert "C001" in state.entities
        assert "C002" in state.entities

    def test_state_with_relationships(
        self,
        worker: SocialClass,
        owner: SocialClass,
        exploitation_edge: Relationship,
    ) -> None:
        """Can create WorldState with relationships."""
        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )
        assert len(state.relationships) == 1
        assert state.relationships[0].source_id == "C001"
        assert state.relationships[0].target_id == "C002"

    def test_state_with_event_log(self) -> None:
        """Can create WorldState with event log."""
        state = WorldState(
            tick=5,
            event_log=["Event 1", "Event 2"],
        )
        assert len(state.event_log) == 2
        assert "Event 1" in state.event_log

    def test_tick_defaults_to_zero(self) -> None:
        """Tick defaults to 0 if not specified."""
        state = WorldState()
        assert state.tick == 0


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.topology
class TestWorldStateImmutability:
    """WorldState should be immutable (frozen)."""

    def test_tick_is_frozen(self, two_node_state: WorldState) -> None:
        """Cannot modify tick after creation."""
        with pytest.raises(ValidationError):
            two_node_state.tick = 5  # type: ignore[misc]

    def test_entities_dict_is_frozen(self, two_node_state: WorldState) -> None:
        """Cannot replace entities dict after creation."""
        with pytest.raises(ValidationError):
            two_node_state.entities = {}  # type: ignore[misc]

    def test_relationships_list_is_frozen(self, two_node_state: WorldState) -> None:
        """Cannot replace relationships list after creation."""
        with pytest.raises(ValidationError):
            two_node_state.relationships = []  # type: ignore[misc]


# =============================================================================
# NETWORKX CONVERSION TESTS
# =============================================================================


@pytest.mark.topology
class TestWorldStateToGraph:
    """WorldState.to_graph() should convert state to NetworkX DiGraph."""

    def test_to_graph_returns_digraph(self, two_node_state: WorldState) -> None:
        """to_graph() returns a NetworkX DiGraph."""
        G = two_node_state.to_graph()
        assert isinstance(G, nx.DiGraph)

    def test_to_graph_preserves_node_count(self, two_node_state: WorldState) -> None:
        """Graph has same number of nodes as entities."""
        G = two_node_state.to_graph()
        assert G.number_of_nodes() == 2

    def test_to_graph_preserves_edge_count(self, two_node_state: WorldState) -> None:
        """Graph has same number of edges as relationships."""
        G = two_node_state.to_graph()
        assert G.number_of_edges() == 1

    def test_to_graph_preserves_node_ids(self, two_node_state: WorldState) -> None:
        """Graph nodes have correct IDs."""
        G = two_node_state.to_graph()
        assert "C001" in G.nodes
        assert "C002" in G.nodes

    def test_to_graph_preserves_node_data(self, two_node_state: WorldState) -> None:
        """Graph nodes have entity data as attributes."""
        G = two_node_state.to_graph()
        assert G.nodes["C001"]["name"] == "Periphery Worker"
        assert G.nodes["C001"]["wealth"] == 0.5
        assert G.nodes["C002"]["name"] == "Core Owner"

    def test_to_graph_preserves_edge_direction(self, two_node_state: WorldState) -> None:
        """Graph edges have correct direction."""
        G = two_node_state.to_graph()
        assert G.has_edge("C001", "C002")
        assert not G.has_edge("C002", "C001")

    def test_to_graph_preserves_edge_data(self, two_node_state: WorldState) -> None:
        """Graph edges have relationship data as attributes."""
        G = two_node_state.to_graph()
        edge_data = G.edges["C001", "C002"]
        assert edge_data["edge_type"] == EdgeType.EXPLOITATION
        assert edge_data["value_flow"] == 0.0
        assert edge_data["tension"] == 0.0

    def test_empty_state_to_graph(self) -> None:
        """Empty state produces empty graph."""
        state = WorldState(tick=0)
        G = state.to_graph()
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0


@pytest.mark.topology
class TestWorldStateFromGraph:
    """WorldState.from_graph() should reconstruct state from NetworkX DiGraph."""

    def test_from_graph_returns_world_state(self, two_node_state: WorldState) -> None:
        """from_graph() returns a WorldState."""
        G = two_node_state.to_graph()
        state = WorldState.from_graph(G, tick=5)
        assert isinstance(state, WorldState)

    def test_from_graph_sets_tick(self, two_node_state: WorldState) -> None:
        """from_graph() sets the tick parameter."""
        G = two_node_state.to_graph()
        state = WorldState.from_graph(G, tick=42)
        assert state.tick == 42

    def test_from_graph_preserves_entities(self, two_node_state: WorldState) -> None:
        """from_graph() reconstructs entities correctly."""
        G = two_node_state.to_graph()
        state = WorldState.from_graph(G, tick=0)
        assert len(state.entities) == 2
        assert "C001" in state.entities
        assert state.entities["C001"].name == "Periphery Worker"

    def test_from_graph_preserves_relationships(self, two_node_state: WorldState) -> None:
        """from_graph() reconstructs relationships correctly."""
        G = two_node_state.to_graph()
        state = WorldState.from_graph(G, tick=0)
        assert len(state.relationships) == 1
        assert state.relationships[0].source_id == "C001"
        assert state.relationships[0].target_id == "C002"

    def test_round_trip_preserves_state(self, two_node_state: WorldState) -> None:
        """to_graph() -> from_graph() round trip preserves state."""
        G = two_node_state.to_graph()
        restored = WorldState.from_graph(G, tick=two_node_state.tick)

        # Compare entities
        assert len(restored.entities) == len(two_node_state.entities)
        for entity_id in two_node_state.entities:
            assert entity_id in restored.entities
            original = two_node_state.entities[entity_id]
            restored_entity = restored.entities[entity_id]
            assert restored_entity.name == original.name
            assert restored_entity.wealth == pytest.approx(original.wealth)

        # Compare relationships
        assert len(restored.relationships) == len(two_node_state.relationships)


# =============================================================================
# MUTATION METHODS (IMMUTABLE PATTERN)
# =============================================================================


@pytest.mark.topology
class TestWorldStateAddEntity:
    """WorldState.add_entity() should return new state with entity added."""

    def test_add_entity_returns_new_state(self, worker: SocialClass) -> None:
        """add_entity() returns a new WorldState instance."""
        state = WorldState(tick=0)
        new_state = state.add_entity(worker)
        assert new_state is not state

    def test_add_entity_preserves_original(self, worker: SocialClass) -> None:
        """add_entity() does not modify the original state."""
        state = WorldState(tick=0)
        new_state = state.add_entity(worker)
        assert len(state.entities) == 0
        assert len(new_state.entities) == 1

    def test_add_entity_includes_new_entity(self, worker: SocialClass) -> None:
        """add_entity() includes the new entity."""
        state = WorldState(tick=0)
        new_state = state.add_entity(worker)
        assert "C001" in new_state.entities
        assert new_state.entities["C001"].name == "Periphery Worker"

    def test_add_entity_preserves_tick(
        self,
        worker: SocialClass,
    ) -> None:
        """add_entity() preserves the tick."""
        state = WorldState(tick=10)
        new_state = state.add_entity(worker)
        assert new_state.tick == 10

    def test_add_entity_preserves_existing_entities(
        self,
        worker: SocialClass,
        owner: SocialClass,
    ) -> None:
        """add_entity() preserves existing entities."""
        state = WorldState(tick=0, entities={"C001": worker})
        new_state = state.add_entity(owner)
        assert "C001" in new_state.entities
        assert "C002" in new_state.entities


@pytest.mark.topology
class TestWorldStateAddRelationship:
    """WorldState.add_relationship() should return new state with relationship added."""

    def test_add_relationship_returns_new_state(
        self,
        worker: SocialClass,
        owner: SocialClass,
        exploitation_edge: Relationship,
    ) -> None:
        """add_relationship() returns a new WorldState instance."""
        state = WorldState(tick=0, entities={"C001": worker, "C002": owner})
        new_state = state.add_relationship(exploitation_edge)
        assert new_state is not state

    def test_add_relationship_preserves_original(
        self,
        worker: SocialClass,
        owner: SocialClass,
        exploitation_edge: Relationship,
    ) -> None:
        """add_relationship() does not modify the original state."""
        state = WorldState(tick=0, entities={"C001": worker, "C002": owner})
        new_state = state.add_relationship(exploitation_edge)
        assert len(state.relationships) == 0
        assert len(new_state.relationships) == 1

    def test_add_relationship_includes_new_edge(
        self,
        worker: SocialClass,
        owner: SocialClass,
        exploitation_edge: Relationship,
    ) -> None:
        """add_relationship() includes the new relationship."""
        state = WorldState(tick=0, entities={"C001": worker, "C002": owner})
        new_state = state.add_relationship(exploitation_edge)
        assert len(new_state.relationships) == 1
        assert new_state.relationships[0].source_id == "C001"


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.topology
class TestWorldStateSerialization:
    """WorldState should serialize correctly for save/load."""

    def test_json_round_trip(self, two_node_state: WorldState) -> None:
        """WorldState survives JSON round-trip."""
        json_str = two_node_state.model_dump_json()
        restored = WorldState.model_validate_json(json_str)

        assert restored.tick == two_node_state.tick
        assert len(restored.entities) == len(two_node_state.entities)
        assert len(restored.relationships) == len(two_node_state.relationships)

    def test_dict_round_trip(self, two_node_state: WorldState) -> None:
        """WorldState survives dict round-trip."""
        data = two_node_state.model_dump()
        restored = WorldState.model_validate(data)

        assert restored.tick == two_node_state.tick

    def test_model_copy_with_tick_update(self, two_node_state: WorldState) -> None:
        """WorldState can be copied with updated tick."""
        new_state = two_node_state.model_copy(update={"tick": 5})
        assert two_node_state.tick == 0
        assert new_state.tick == 5


# =============================================================================
# EVENT LOG TESTS
# =============================================================================


@pytest.mark.topology
class TestWorldStateEventLog:
    """WorldState should track events for narrative/debugging."""

    def test_add_event_returns_new_state(self, two_node_state: WorldState) -> None:
        """add_event() returns a new WorldState instance."""
        new_state = two_node_state.add_event("Test event")
        assert new_state is not two_node_state

    def test_add_event_appends_to_log(self, two_node_state: WorldState) -> None:
        """add_event() appends to the event log."""
        new_state = two_node_state.add_event("First event")
        new_state = new_state.add_event("Second event")
        assert len(new_state.event_log) == 2
        assert "First event" in new_state.event_log
        assert "Second event" in new_state.event_log

    def test_add_event_preserves_original(self, two_node_state: WorldState) -> None:
        """add_event() does not modify the original state."""
        new_state = two_node_state.add_event("Test event")
        assert len(two_node_state.event_log) == 0
        assert len(new_state.event_log) == 1
