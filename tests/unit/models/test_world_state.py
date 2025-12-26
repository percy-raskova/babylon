"""Tests for babylon.models.world_state.

TDD Red Phase: These tests define the contract for WorldState.
WorldState is an immutable snapshot of the simulation at a specific tick.
It wraps NetworkX for graph operations while maintaining Pydantic validation.

Sprint 4: WorldState with NetworkX integration for Phase 2 game loop.
Sprint 3.5.3: Territory integration for Layer 0.
"""

import networkx as nx
import pytest
from pydantic import ValidationError

from babylon.models import EdgeType, Relationship, SocialClass, SocialRole
from babylon.models.entities.territory import Territory
from babylon.models.enums import OperationalProfile, SectorType
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


# =============================================================================
# TERRITORY TESTS (Sprint 3.5.3)
# =============================================================================


@pytest.fixture
def university_territory() -> Territory:
    """Create a university district territory."""
    return Territory(
        id="T001",
        name="University District",
        sector_type=SectorType.UNIVERSITY,
        profile=OperationalProfile.HIGH_PROFILE,
        heat=0.3,
        population=5000,
    )


@pytest.fixture
def docks_territory() -> Territory:
    """Create a docks territory."""
    return Territory(
        id="T002",
        name="Docks",
        sector_type=SectorType.DOCKS,
        profile=OperationalProfile.LOW_PROFILE,
        heat=0.1,
        population=2000,
    )


@pytest.mark.topology
class TestWorldStateTerritoriesField:
    """WorldState should support a territories dict field."""

    def test_empty_state_has_empty_territories(self) -> None:
        """Empty WorldState has empty territories dict."""
        state = WorldState(tick=0)
        assert len(state.territories) == 0

    def test_state_with_territories(
        self,
        university_territory: Territory,
        docks_territory: Territory,
    ) -> None:
        """Can create WorldState with territories."""
        state = WorldState(
            tick=0,
            territories={
                "T001": university_territory,
                "T002": docks_territory,
            },
        )
        assert len(state.territories) == 2
        assert "T001" in state.territories
        assert "T002" in state.territories

    def test_territories_and_entities_coexist(
        self,
        worker: SocialClass,
        university_territory: Territory,
    ) -> None:
        """Territories and entities can coexist in WorldState."""
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": university_territory},
        )
        assert len(state.entities) == 1
        assert len(state.territories) == 1
        assert "C001" in state.entities
        assert "T001" in state.territories


@pytest.mark.topology
class TestWorldStateAddTerritory:
    """WorldState.add_territory() should return new state with territory added."""

    def test_add_territory_returns_new_state(
        self,
        university_territory: Territory,
    ) -> None:
        """add_territory() returns a new WorldState instance."""
        state = WorldState(tick=0)
        new_state = state.add_territory(university_territory)
        assert new_state is not state

    def test_add_territory_preserves_original(
        self,
        university_territory: Territory,
    ) -> None:
        """add_territory() does not modify the original state."""
        state = WorldState(tick=0)
        new_state = state.add_territory(university_territory)
        assert len(state.territories) == 0
        assert len(new_state.territories) == 1

    def test_add_territory_includes_new_territory(
        self,
        university_territory: Territory,
    ) -> None:
        """add_territory() includes the new territory."""
        state = WorldState(tick=0)
        new_state = state.add_territory(university_territory)
        assert "T001" in new_state.territories
        assert new_state.territories["T001"].name == "University District"

    def test_add_territory_preserves_tick(
        self,
        university_territory: Territory,
    ) -> None:
        """add_territory() preserves the tick."""
        state = WorldState(tick=10)
        new_state = state.add_territory(university_territory)
        assert new_state.tick == 10

    def test_add_territory_preserves_existing_territories(
        self,
        university_territory: Territory,
        docks_territory: Territory,
    ) -> None:
        """add_territory() preserves existing territories."""
        state = WorldState(tick=0, territories={"T001": university_territory})
        new_state = state.add_territory(docks_territory)
        assert "T001" in new_state.territories
        assert "T002" in new_state.territories


@pytest.mark.topology
class TestWorldStateToGraphWithTerritories:
    """WorldState.to_graph() should include territories with _node_type marker."""

    def test_to_graph_includes_territories(
        self,
        university_territory: Territory,
    ) -> None:
        """to_graph() includes territory nodes."""
        state = WorldState(tick=0, territories={"T001": university_territory})
        G = state.to_graph()
        assert "T001" in G.nodes

    def test_to_graph_marks_territory_node_type(
        self,
        university_territory: Territory,
    ) -> None:
        """Territory nodes have _node_type='territory' marker."""
        state = WorldState(tick=0, territories={"T001": university_territory})
        G = state.to_graph()
        assert G.nodes["T001"]["_node_type"] == "territory"

    def test_to_graph_marks_entity_node_type(
        self,
        worker: SocialClass,
    ) -> None:
        """Entity nodes have _node_type='social_class' marker."""
        state = WorldState(tick=0, entities={"C001": worker})
        G = state.to_graph()
        assert G.nodes["C001"]["_node_type"] == "social_class"

    def test_to_graph_preserves_territory_data(
        self,
        university_territory: Territory,
    ) -> None:
        """Territory nodes have all territory data as attributes."""
        state = WorldState(tick=0, territories={"T001": university_territory})
        G = state.to_graph()
        assert G.nodes["T001"]["name"] == "University District"
        assert G.nodes["T001"]["sector_type"] == SectorType.UNIVERSITY
        assert G.nodes["T001"]["heat"] == 0.3
        assert G.nodes["T001"]["population"] == 5000

    def test_to_graph_mixed_nodes(
        self,
        worker: SocialClass,
        university_territory: Territory,
    ) -> None:
        """to_graph() handles mixed entity and territory nodes."""
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": university_territory},
        )
        G = state.to_graph()
        assert G.number_of_nodes() == 2
        assert G.nodes["C001"]["_node_type"] == "social_class"
        assert G.nodes["T001"]["_node_type"] == "territory"


@pytest.mark.topology
class TestWorldStateFromGraphWithTerritories:
    """WorldState.from_graph() should reconstruct territories based on _node_type."""

    def test_from_graph_reconstructs_territories(
        self,
        university_territory: Territory,
    ) -> None:
        """from_graph() reconstructs territories correctly."""
        state = WorldState(tick=0, territories={"T001": university_territory})
        G = state.to_graph()
        restored = WorldState.from_graph(G, tick=1)
        assert len(restored.territories) == 1
        assert "T001" in restored.territories
        assert restored.territories["T001"].name == "University District"

    def test_from_graph_reconstructs_mixed_nodes(
        self,
        worker: SocialClass,
        university_territory: Territory,
    ) -> None:
        """from_graph() reconstructs both entities and territories."""
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": university_territory},
        )
        G = state.to_graph()
        restored = WorldState.from_graph(G, tick=1)
        assert len(restored.entities) == 1
        assert len(restored.territories) == 1
        assert "C001" in restored.entities
        assert "T001" in restored.territories

    def test_round_trip_preserves_territories(
        self,
        university_territory: Territory,
        docks_territory: Territory,
    ) -> None:
        """to_graph() -> from_graph() round trip preserves territories."""
        state = WorldState(
            tick=0,
            territories={
                "T001": university_territory,
                "T002": docks_territory,
            },
        )
        G = state.to_graph()
        restored = WorldState.from_graph(G, tick=state.tick)

        assert len(restored.territories) == 2
        for territory_id in state.territories:
            assert territory_id in restored.territories
            original = state.territories[territory_id]
            restored_territory = restored.territories[territory_id]
            assert restored_territory.name == original.name
            assert restored_territory.sector_type == original.sector_type
            assert restored_territory.heat == pytest.approx(original.heat)
            assert restored_territory.population == original.population


# =============================================================================
# SPRINT 3.4.4 - GLOBAL ECONOMY INTEGRATION (Dynamic Balance)
# =============================================================================


@pytest.mark.topology
class TestWorldStateEconomyIntegration:
    """Tests for GlobalEconomy integration with WorldState.

    Sprint 3.4.4: Dynamic Balance - economy state flows through graph metadata.
    """

    def test_world_state_has_default_economy(self) -> None:
        """WorldState has default GlobalEconomy."""
        from babylon.models.entities.economy import GlobalEconomy

        state = WorldState()
        assert hasattr(state, "economy")
        assert isinstance(state.economy, GlobalEconomy)
        assert state.economy.imperial_rent_pool == 100.0

    def test_world_state_with_custom_economy(
        self,
        worker: SocialClass,
    ) -> None:
        """WorldState can be created with custom GlobalEconomy."""
        from babylon.models.entities.economy import GlobalEconomy

        custom_economy = GlobalEconomy(
            imperial_rent_pool=50.0,
            current_super_wage_rate=0.15,
            current_repression_level=0.7,
        )
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            economy=custom_economy,
        )
        assert state.economy.imperial_rent_pool == 50.0
        assert state.economy.current_super_wage_rate == 0.15
        assert state.economy.current_repression_level == 0.7

    def test_to_graph_stores_economy_in_metadata(
        self,
        worker: SocialClass,
    ) -> None:
        """to_graph() stores economy in G.graph['economy']."""
        from babylon.models.entities.economy import GlobalEconomy

        custom_economy = GlobalEconomy(
            imperial_rent_pool=75.0,
            current_super_wage_rate=0.25,
            current_repression_level=0.6,
        )
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            economy=custom_economy,
        )
        G = state.to_graph()

        assert "economy" in G.graph
        economy_data = G.graph["economy"]
        assert economy_data["imperial_rent_pool"] == 75.0
        assert economy_data["current_super_wage_rate"] == 0.25
        assert economy_data["current_repression_level"] == 0.6

    def test_from_graph_reconstructs_economy(
        self,
        worker: SocialClass,
    ) -> None:
        """from_graph() reconstructs GlobalEconomy from metadata."""
        from babylon.models.entities.economy import GlobalEconomy

        custom_economy = GlobalEconomy(
            imperial_rent_pool=60.0,
            current_super_wage_rate=0.30,
            current_repression_level=0.4,
        )
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            economy=custom_economy,
        )
        G = state.to_graph()
        restored = WorldState.from_graph(G, tick=1)

        assert restored.economy.imperial_rent_pool == 60.0
        assert restored.economy.current_super_wage_rate == 0.30
        assert restored.economy.current_repression_level == 0.4

    def test_from_graph_default_economy_when_missing(self) -> None:
        """from_graph() uses default economy when metadata missing (backward compat)."""
        import networkx as nx

        G: nx.DiGraph[str] = nx.DiGraph()
        # No economy in G.graph - simulates old graph without economy support
        restored = WorldState.from_graph(G, tick=0)

        assert restored.economy.imperial_rent_pool == 100.0
        assert restored.economy.current_super_wage_rate == 0.20
        assert restored.economy.current_repression_level == 0.5

    def test_economy_round_trip(
        self,
        worker: SocialClass,
        owner: SocialClass,
    ) -> None:
        """Economy survives to_graph() -> from_graph() round trip."""
        from babylon.models.entities.economy import GlobalEconomy
        from babylon.models.entities.relationship import Relationship
        from babylon.models.enums import EdgeType

        custom_economy = GlobalEconomy(
            imperial_rent_pool=125.0,
            current_super_wage_rate=0.10,
            current_repression_level=0.8,
        )
        relationship = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )
        state = WorldState(
            tick=5,
            entities={"C001": worker, "C002": owner},
            relationships=[relationship],
            economy=custom_economy,
        )
        G = state.to_graph()
        restored = WorldState.from_graph(G, tick=6)

        # Verify full state preservation
        assert len(restored.entities) == 2
        assert len(restored.relationships) == 1
        assert restored.economy.imperial_rent_pool == 125.0
        assert restored.economy.current_super_wage_rate == 0.10
        assert restored.economy.current_repression_level == 0.8


# =============================================================================
# METABOLIC AGGREGATE TESTS (Slice 1.4)
# =============================================================================


@pytest.mark.topology
class TestWorldStateMetabolicAggregates:
    """WorldState metabolic aggregate computed properties."""

    def test_total_biocapacity_empty_state(self) -> None:
        """Empty state has zero biocapacity."""
        state = WorldState()
        assert state.total_biocapacity == 0.0

    def test_total_biocapacity_single_territory(self) -> None:
        """Single territory contributes its biocapacity."""
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType

        territory = Territory(
            id="T001",
            name="Forest",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=75.0,
        )
        state = WorldState(territories={"T001": territory})
        assert state.total_biocapacity == 75.0

    def test_total_biocapacity_multiple_territories(self) -> None:
        """Multiple territories sum their biocapacity."""
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType

        t1 = Territory(
            id="T001",
            name="Forest",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=50.0,
        )
        t2 = Territory(
            id="T002",
            name="Farmland",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=30.0,
        )
        t3 = Territory(
            id="T003",
            name="Desert",
            sector_type=SectorType.GOVERNMENT,
            biocapacity=5.0,
        )
        state = WorldState(territories={"T001": t1, "T002": t2, "T003": t3})
        assert state.total_biocapacity == pytest.approx(85.0, abs=0.001)

    def test_total_consumption_empty_state(self) -> None:
        """Empty state has zero consumption."""
        state = WorldState()
        assert state.total_consumption == 0.0

    def test_total_consumption_single_entity(self) -> None:
        """Single entity contributes its consumption needs."""
        from babylon.models import SocialClass
        from babylon.models.enums import SocialRole

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.05,
            s_class=0.10,
        )
        state = WorldState(entities={"C001": worker})
        assert state.total_consumption == pytest.approx(0.15, abs=0.001)

    def test_total_consumption_multiple_entities(self) -> None:
        """Multiple entities sum their consumption needs."""
        from babylon.models import SocialClass
        from babylon.models.enums import SocialRole

        e1 = SocialClass(
            id="C001",
            name="Worker 1",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.02,
            s_class=0.03,
        )
        e2 = SocialClass(
            id="C002",
            name="Worker 2",
            role=SocialRole.LABOR_ARISTOCRACY,
            s_bio=0.02,
            s_class=0.08,
        )
        state = WorldState(entities={"C001": e1, "C002": e2})
        # 0.05 + 0.10 = 0.15
        assert state.total_consumption == pytest.approx(0.15, abs=0.001)

    def test_overshoot_ratio_sustainable(self) -> None:
        """Overshoot ratio < 1 when consumption < biocapacity."""
        from babylon.models import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType, SocialRole

        territory = Territory(
            id="T001",
            name="Forest",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=100.0,
        )
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.02,
            s_class=0.03,
        )
        state = WorldState(
            entities={"C001": worker},
            territories={"T001": territory},
        )
        # consumption = 0.05, biocapacity = 100.0
        # ratio = 0.05 / 100.0 = 0.0005
        assert state.overshoot_ratio < 1.0
        assert state.overshoot_ratio == pytest.approx(0.0005, abs=0.0001)

    def test_overshoot_ratio_overshoot(self) -> None:
        """Overshoot ratio > 1 when consumption > biocapacity."""
        from babylon.models import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType, SocialRole

        territory = Territory(
            id="T001",
            name="Depleted",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=0.01,  # Almost no biocapacity
        )
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.02,
            s_class=0.03,
        )
        state = WorldState(
            entities={"C001": worker},
            territories={"T001": territory},
        )
        # consumption = 0.05, biocapacity = 0.01
        # ratio = 0.05 / 0.01 = 5.0
        assert state.overshoot_ratio > 1.0
        assert state.overshoot_ratio == pytest.approx(5.0, abs=0.1)

    def test_overshoot_ratio_zero_biocapacity(self) -> None:
        """Overshoot ratio capped at 999 when biocapacity is zero."""
        from babylon.models import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType, SocialRole

        territory = Territory(
            id="T001",
            name="Dead Zone",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=0.0,
        )
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.01,
        )
        state = WorldState(
            entities={"C001": worker},
            territories={"T001": territory},
        )
        assert state.overshoot_ratio == 999.0

    def test_overshoot_ratio_no_consumption(self) -> None:
        """Overshoot ratio is 0 when no consumption."""
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType

        territory = Territory(
            id="T001",
            name="Pristine",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=100.0,
        )
        state = WorldState(territories={"T001": territory})
        assert state.overshoot_ratio == 0.0
