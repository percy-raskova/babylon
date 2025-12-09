"""WorldState model for the Babylon simulation.

WorldState is an immutable snapshot of the entire simulation at a specific tick.
It encapsulates:
- All entities (social classes) as nodes
- All territories (strategic sectors) as nodes
- All relationships (value flows, tensions) as edges
- A tick counter for temporal tracking
- An event log for narrative/debugging

The state is designed for functional transformation:
    new_state = step(old_state, config)

Sprint 4: Phase 2 game loop state container with NetworkX integration.
Sprint 3.5.3: Territory integration for Layer 0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field

from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, OperationalProfile, SectorType

if TYPE_CHECKING:
    pass


class WorldState(BaseModel):
    """Immutable snapshot of the simulation at a specific tick.

    WorldState follows the Data/Logic separation principle:
    - State holds WHAT exists (pure data)
    - Engine determines HOW it transforms (pure logic)

    This enables:
    - Determinism: Same state + same engine = same output
    - Replayability: Save initial state, replay entire history
    - Counterfactuals: Modify a parameter, run forward, compare
    - Testability: Feed state in, assert on state out

    Attributes:
        tick: Current turn number (0-indexed)
        entities: Map of entity ID to SocialClass (the nodes)
        territories: Map of territory ID to Territory (Layer 0 nodes)
        relationships: List of Relationship edges (the edges)
        event_log: Recent events for narrative/debugging
        economy: Global economic state for dynamic balance (Sprint 3.4.4)
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(
        default=0,
        ge=0,
        description="Current turn number (0-indexed)",
    )

    entities: dict[str, SocialClass] = Field(
        default_factory=dict,
        description="Map of entity ID to SocialClass (graph nodes)",
    )

    territories: dict[str, Territory] = Field(
        default_factory=dict,
        description="Map of territory ID to Territory (Layer 0 nodes)",
    )

    relationships: list[Relationship] = Field(
        default_factory=list,
        description="List of relationships (graph edges)",
    )

    event_log: list[str] = Field(
        default_factory=list,
        description="Recent events for narrative/debugging",
    )

    economy: GlobalEconomy = Field(
        default_factory=GlobalEconomy,
        description="Global economic state for dynamic balance (Sprint 3.4.4)",
    )

    # =========================================================================
    # NetworkX Conversion
    # =========================================================================

    def to_graph(self) -> nx.DiGraph[str]:
        """Convert state to NetworkX DiGraph for formula application.

        Nodes are entity/territory IDs with all fields as attributes.
        A _node_type marker distinguishes between node types:
        - _node_type='social_class' for SocialClass nodes
        - _node_type='territory' for Territory nodes

        Edges are relationships with all Relationship fields as attributes.

        Graph metadata (G.graph) contains:
        - economy: GlobalEconomy state (Sprint 3.4.4)

        Returns:
            NetworkX DiGraph with nodes and edges from this state.

        Example:
            G = state.to_graph()
            for node_id, data in G.nodes(data=True):
                if data["_node_type"] == "social_class":
                    data["wealth"] += 10  # Modify entity
            new_state = WorldState.from_graph(G, tick=state.tick + 1)
        """
        G: nx.DiGraph[str] = nx.DiGraph()

        # Store economy in graph metadata (Sprint 3.4.4)
        G.graph["economy"] = self.economy.model_dump()

        # Add entity nodes with _node_type marker
        for entity_id, entity in self.entities.items():
            G.add_node(entity_id, _node_type="social_class", **entity.model_dump())

        # Add territory nodes with _node_type marker
        for territory_id, territory in self.territories.items():
            G.add_node(territory_id, _node_type="territory", **territory.model_dump())

        # Add edges with relationship data
        for rel in self.relationships:
            source, target = rel.edge_tuple
            G.add_edge(source, target, **rel.edge_data)

        return G

    @classmethod
    def from_graph(
        cls,
        G: nx.DiGraph[str],
        tick: int,
        event_log: list[str] | None = None,
    ) -> WorldState:
        """Reconstruct WorldState from NetworkX DiGraph.

        Args:
            G: NetworkX DiGraph with node/edge data
            tick: The tick number for the new state
            event_log: Optional event log to preserve

        Returns:
            New WorldState with entities, territories, and relationships from graph.

        Example:
            G = state.to_graph()
            # ... modify graph ...
            new_state = WorldState.from_graph(G, tick=state.tick + 1)
        """
        # Reconstruct economy from graph metadata (Sprint 3.4.4)
        # Falls back to default GlobalEconomy if not present (backward compatibility)
        economy_data = G.graph.get("economy")
        economy = GlobalEconomy(**economy_data) if economy_data is not None else GlobalEconomy()

        # Reconstruct entities and territories from nodes based on _node_type
        entities: dict[str, SocialClass] = {}
        territories: dict[str, Territory] = {}

        for node_id, data in G.nodes(data=True):
            node_type = data.get("_node_type", "social_class")
            # Create a copy without _node_type for model construction
            node_data = {k: v for k, v in data.items() if k != "_node_type"}

            if node_type == "territory":
                # Reconstruct Territory
                # Convert enum strings back to enums if needed
                sector_type = node_data.get("sector_type")
                if isinstance(sector_type, str):
                    node_data["sector_type"] = SectorType(sector_type)
                profile = node_data.get("profile")
                if isinstance(profile, str):
                    node_data["profile"] = OperationalProfile(profile)
                territories[node_id] = Territory(**node_data)
            else:
                # Reconstruct SocialClass (default for backward compatibility)
                entities[node_id] = SocialClass(**node_data)

        # Reconstruct relationships from edges
        relationships: list[Relationship] = []
        for source_id, target_id, data in G.edges(data=True):
            # Reconstruct edge_type from stored value
            edge_type = data.get("edge_type", EdgeType.EXPLOITATION)
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            relationships.append(
                Relationship(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                    value_flow=data.get("value_flow", 0.0),
                    tension=data.get("tension", 0.0),
                    description=data.get("description", ""),
                    # Imperial Circuit parameters (Sprint 3.4.1)
                    subsidy_cap=data.get("subsidy_cap", 0.0),
                    # Solidarity parameters (Sprint 3.4.2)
                    solidarity_strength=data.get("solidarity_strength", 0.0),
                )
            )

        return cls(
            tick=tick,
            entities=entities,
            territories=territories,
            relationships=relationships,
            event_log=event_log or [],
            economy=economy,
        )

    # =========================================================================
    # Immutable Mutation Methods
    # =========================================================================

    def add_entity(self, entity: SocialClass) -> WorldState:
        """Return new state with entity added.

        Args:
            entity: SocialClass to add

        Returns:
            New WorldState with the entity included.

        Example:
            new_state = state.add_entity(worker)
        """
        new_entities = {**self.entities, entity.id: entity}
        return self.model_copy(update={"entities": new_entities})

    def add_territory(self, territory: Territory) -> WorldState:
        """Return new state with territory added.

        Args:
            territory: Territory to add (Layer 0 node)

        Returns:
            New WorldState with the territory included.

        Example:
            new_state = state.add_territory(university_district)
        """
        new_territories = {**self.territories, territory.id: territory}
        return self.model_copy(update={"territories": new_territories})

    def add_relationship(self, relationship: Relationship) -> WorldState:
        """Return new state with relationship added.

        Args:
            relationship: Relationship edge to add

        Returns:
            New WorldState with the relationship included.

        Example:
            new_state = state.add_relationship(exploitation_edge)
        """
        new_relationships = [*self.relationships, relationship]
        return self.model_copy(update={"relationships": new_relationships})

    def add_event(self, event: str) -> WorldState:
        """Return new state with event appended to log.

        Args:
            event: Event description string

        Returns:
            New WorldState with event in log.

        Example:
            new_state = state.add_event("Worker crossed poverty threshold")
        """
        new_log = [*self.event_log, event]
        return self.model_copy(update={"event_log": new_log})
