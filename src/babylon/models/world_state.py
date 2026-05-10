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

from typing import TYPE_CHECKING, Any, Final

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.models.entities.contradiction import ContradictionFrame
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.industry import IndustryHyperedge
from babylon.models.entities.institution import (
    Institution,
    InstitutionOrgRelation,
)
from babylon.models.entities.organization import (
    KeyFigure,
    OrganizationType,
)
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.state_finance import StateFinance
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, OperationalProfile, OrgType, SectorType
from babylon.models.events import EVENT_CLASS_MAP, SimulationEvent, TickEventAdapter
from babylon.models.types import Currency

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# from_graph exclude rules — single source of truth (Spec 055 T006 / FR-010)
# ---------------------------------------------------------------------------
# Computed / non-reconstructable fields per node-type. Lifted to module scope
# so external consumers (the Spec 055 round-trip property test) can read them
# at runtime without re-grepping for in-method literals.

SOCIAL_CLASS_COMPUTED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "consumption_needs",
    }
)

TERRITORY_EXCLUDED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "p_acquiescence",
        "p_revolution",
        "dpd_state",
        "dependency_ratio",
        "legitimation_index",
        "legitimation_crisis",
        "legitimation_state",
        "mobility_params",
        "adjusted_p_to_d_prime",
        "transmitted_ideology",
        "differential_p_to_d_prime",
    }
)

INSTITUTION_EXCLUDED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "hegemonic_fraction",
        "reproduction_capacity",
    }
)

ORGANIZATION_EXCLUDED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "effective_capacity",
        "composition_cache",
    }
)


def _validate_event(data: dict[str, Any]) -> SimulationEvent:
    """Deserialize an event dict via TickEventAdapter.

    Spec 059 US2 / FR-006 / SC-003: replaces the deleted ``deserialize_event``
    shim. For events serialized before US2 (lacking the ``kind`` discriminator
    field), inject ``kind`` from ``event_type`` since both fields use identical
    string values across the EventType enum.
    """
    if "kind" not in data and "event_type" in data:
        et = data["event_type"]
        # Mutate in place: event_type values map 1:1 to kind values
        data = {**data, "kind": et if isinstance(et, str) else et.value}
    if "kind" in data:
        return TickEventAdapter.validate_python(data)
    # Fallback: bare SimulationEvent (no kind, no event_type) — preserve
    # historical behaviour
    et = data.get("event_type")
    et_str: str | None = None
    if isinstance(et, str):
        et_str = et
    elif et is not None and hasattr(et, "value"):
        et_str = str(et.value)
    cls: type[SimulationEvent] = (
        EVENT_CLASS_MAP.get(et_str, SimulationEvent) if et_str else SimulationEvent
    )
    return cls.model_validate(data)


def _reconstruct_institution(node_data: dict[str, Any]) -> Institution:
    """Reconstruct an Institution from graph node data (Feature 040).

    Excludes computed fields and converts list-serialized frozenset fields
    back to frozenset for Pydantic validation.

    Args:
        node_data: Node attribute dict without _node_type key.

    Returns:
        Reconstructed Institution instance.
    """
    inst_data = {k: v for k, v in node_data.items() if k not in INSTITUTION_EXCLUDED_FIELDS}
    # Convert list back to frozenset for frozenset fields
    if "legal_authorities" in inst_data and isinstance(inst_data["legal_authorities"], list):
        inst_data["legal_authorities"] = frozenset(inst_data["legal_authorities"])
    if "jurisdiction" in inst_data and isinstance(inst_data["jurisdiction"], list):
        inst_data["jurisdiction"] = frozenset(inst_data["jurisdiction"])
    return Institution(**inst_data)


def _reconstruct_territory(node_data: dict[str, Any]) -> Territory:
    """Reconstruct a Territory from graph node data."""
    territory_data = {k: v for k, v in node_data.items() if k not in TERRITORY_EXCLUDED_FIELDS}
    sector_type = territory_data.get("sector_type")
    if isinstance(sector_type, str):
        territory_data["sector_type"] = SectorType(sector_type)
    profile = territory_data.get("profile")
    if isinstance(profile, str):
        territory_data["profile"] = OperationalProfile(profile)
    return Territory(**territory_data)


def _reconstruct_organization(node_data: dict[str, Any]) -> OrganizationType:
    """Reconstruct an Organization subtype from graph node data."""
    # Import subtypes for dispatch
    from babylon.models.entities.organization import (
        Business,
        CivilSocietyOrg,
        PoliticalFaction,
        StateApparatus,
    )

    org_data = {k: v for k, v in node_data.items() if k not in ORGANIZATION_EXCLUDED_FIELDS}

    org_type_raw = org_data.get("org_type")
    if org_type_raw is None:
        raise KeyError("Organization node missing org_type")
    org_type_enum = OrgType(org_type_raw) if isinstance(org_type_raw, str) else org_type_raw

    subtype_map: dict[
        OrgType,
        type[StateApparatus] | type[Business] | type[PoliticalFaction] | type[CivilSocietyOrg],
    ] = {
        OrgType.STATE_APPARATUS: StateApparatus,
        OrgType.BUSINESS: Business,
        OrgType.POLITICAL_FACTION: PoliticalFaction,
        OrgType.CIVIL_SOCIETY: CivilSocietyOrg,
    }
    org_cls = subtype_map[org_type_enum]
    return org_cls(**org_data)


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
        event_log: Recent events for narrative/debugging (string format)
        events: Structured simulation events for analysis (Sprint 3.1)
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

    events: list[SimulationEvent] = Field(
        default_factory=list,
        description="Structured simulation events for analysis (Sprint 3.1)",
    )

    economy: GlobalEconomy = Field(
        default_factory=GlobalEconomy,
        description="Global economic state for dynamic balance (Sprint 3.4.4)",
    )

    state_finances: dict[str, StateFinance] = Field(
        default_factory=dict,
        description="Financial state for each sovereign entity (Epoch 1: The Ledger)",
    )

    contradiction_frames: dict[str, ContradictionFrame] = Field(
        default_factory=dict,
        description="Map of scope ID to active ContradictionFrame (Feature: Fractal Contradictions)",
    )

    # Organization Base Model (Feature 031)
    organizations: dict[str, OrganizationType] = Field(
        default_factory=dict,
        description="Map of organization ID to Organization subtype (Feature 031)",
    )
    key_figures: dict[str, KeyFigure] = Field(
        default_factory=dict,
        description="Map of key figure ID to KeyFigure (Feature 031)",
    )

    # Institution Base Model (Feature 040)
    institutions: dict[str, Institution] = Field(
        default_factory=dict,
        description="Map of institution ID to Institution (Feature 040)",
    )
    institution_relations: list[InstitutionOrgRelation] = Field(
        default_factory=list,
        description="Institution-Organization housing relationships (Feature 040)",
    )

    # Industry Hyperedge (Feature: ECONOMIC_SECTOR)
    industries: dict[str, IndustryHyperedge] = Field(
        default_factory=dict,
        description="Map of industry ID to IndustryHyperedge (Feature: ECONOMIC_SECTOR)",
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

        Example::

            G = state.to_graph()
            for node_id, data in G.nodes(data=True):
                if data["_node_type"] == "social_class":
                    data["wealth"] += 10  # Modify entity
            new_state = WorldState.from_graph(G, tick=state.tick + 1)
        """
        G: nx.DiGraph[str] = nx.DiGraph()

        # Store economy in graph metadata (Sprint 3.4.4)
        G.graph["economy"] = self.economy.model_dump()

        # Store state finances in graph metadata (Epoch 1: The Ledger)
        G.graph["state_finances"] = {
            state_id: finance.model_dump() for state_id, finance in self.state_finances.items()
        }

        # Store contradiction frames in graph metadata
        G.graph["contradiction_frames"] = {
            scope: frame.model_dump() for scope, frame in self.contradiction_frames.items()
        }

        # Store events in graph metadata for lossless round-trip (Sprint 1.X D2)
        G.graph["events"] = [e.model_dump() for e in self.events]
        G.graph["event_log"] = list(self.event_log)

        # Add entity nodes with _node_type marker
        for entity_id, entity in self.entities.items():
            G.add_node(entity_id, _node_type="social_class", **entity.model_dump())

        # Add territory nodes with _node_type marker
        for territory_id, territory in self.territories.items():
            G.add_node(territory_id, _node_type="territory", **territory.model_dump())

        # Add organization nodes with _node_type marker (Feature 031)
        for org_id, org in self.organizations.items():
            G.add_node(org_id, _node_type="organization", **org.model_dump())
            # Create PRESENCE edges for all territory_ids
            for tid in org.territory_ids:
                if tid in G:
                    G.add_edge(org_id, tid, edge_type=EdgeType.PRESENCE.value)

        # Add key figure nodes with _node_type marker (Feature 031)
        for kf_id, kf in self.key_figures.items():
            G.add_node(kf_id, _node_type="key_figure", **kf.model_dump())

        # Add institution nodes with _node_type marker (Feature 040)
        for inst_id, inst in self.institutions.items():
            G.add_node(inst_id, _node_type="institution", **inst.model_dump())
            # Create PRESENCE edges to territory_ids
            for tid in inst.territory_ids:
                if tid in G:
                    G.add_edge(inst_id, tid, edge_type=EdgeType.PRESENCE.value)
            # Create HOUSES edges to housed_org_ids
            for org_id in inst.housed_org_ids:
                if org_id in G:
                    G.add_edge(inst_id, org_id, edge_type=EdgeType.HOUSES.value)

        # Add industry nodes with _node_type marker (Feature: ECONOMIC_SECTOR)
        for ind_id, ind in self.industries.items():
            G.add_node(ind_id, _node_type="industry", **ind.model_dump())

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
        events: list[SimulationEvent] | None = None,
    ) -> WorldState:
        """Reconstruct WorldState from NetworkX DiGraph.

        Args:
            G: NetworkX DiGraph with node/edge data
            tick: The tick number for the new state
            event_log: Optional event log to preserve (backward compatibility)
            events: Optional structured events to include (Sprint 3.1)

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

        # Reconstruct state_finances from graph metadata (Epoch 1: The Ledger)
        # Falls back to empty dict if not present (backward compatibility)
        sf_data = G.graph.get("state_finances", {})
        state_finances = {state_id: StateFinance(**data) for state_id, data in sf_data.items()}

        # Reconstruct contradiction frames
        cf_data = G.graph.get("contradiction_frames", {})
        contradiction_frames = {
            scope: ContradictionFrame(**data) for scope, data in cf_data.items()
        }

        # Reconstruct events from graph metadata (Sprint 1.X D2: Lossless Round-Trip)
        # Only use graph metadata if events parameter was not explicitly provided
        if events is None:
            events_data = G.graph.get("events", [])
            if events_data:
                # Spec 059 US2 / FR-006 / SC-003: use TickEventAdapter directly
                # (replaced the deserialize_event shim deleted in this commit).
                # Backward-compat: legacy events serialized before US2 lack a
                # ``kind`` field; inject it from ``event_type`` (the kind values
                # mirror the EventType enum strings 1:1) so the discriminated
                # adapter can dispatch correctly.
                events = [_validate_event(e) for e in events_data]

        # Reconstruct event_log from graph metadata (Sprint 1.X D2)
        # Only use graph metadata if event_log parameter was not explicitly provided
        if event_log is None:
            event_log_data = G.graph.get("event_log", [])
            if event_log_data:
                event_log = list(event_log_data)

        # Reconstruct entities and territories from nodes based on _node_type
        entities: dict[str, SocialClass] = {}
        territories: dict[str, Territory] = {}
        organizations: dict[str, OrganizationType] = {}
        key_figures_dict: dict[str, KeyFigure] = {}
        institutions_dict: dict[str, Institution] = {}
        industries_dict: dict[str, IndustryHyperedge] = {}

        for node_id, data in G.nodes(data=True):
            node_type = data.get("_node_type", "social_class")
            # Create a copy without _node_type for model construction
            node_data = {k: v for k, v in data.items() if k not in ("_node_type", "type")}

            if node_type == "territory":
                territories[node_id] = _reconstruct_territory(node_data)
            elif node_type == "organization":
                organizations[node_id] = _reconstruct_organization(node_data)
            elif node_type == "key_figure":
                key_figures_dict[node_id] = KeyFigure(**node_data)
            elif node_type == "institution":
                institutions_dict[node_id] = _reconstruct_institution(node_data)
            elif node_type == "industry":
                industries_dict[node_id] = IndustryHyperedge(**node_data)
            else:
                # Reconstruct SocialClass (default for backward compatibility)
                # Filter out computed fields that shouldn't be passed to constructor
                entity_data = {
                    k: v for k, v in node_data.items() if k not in SOCIAL_CLASS_COMPUTED_FIELDS
                }
                entities[node_id] = SocialClass(**entity_data)

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
            events=events or [],
            economy=economy,
            state_finances=state_finances,
            contradiction_frames=contradiction_frames,
            organizations=organizations,
            key_figures=key_figures_dict,
            institutions=institutions_dict,
            industries=industries_dict,
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

    # =========================================================================
    # Metabolic Aggregates (Slice 1.4)
    # =========================================================================

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_biocapacity(self) -> Currency:
        """Global sum of territory biocapacity."""
        return Currency(sum(t.biocapacity for t in self.territories.values()))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_consumption(self) -> Currency:
        """Global sum of consumption needs."""
        return Currency(sum(e.consumption_needs for e in self.entities.values()))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overshoot_ratio(self) -> float:
        """Global ecological overshoot ratio."""
        if self.total_biocapacity <= 0:
            return 999.0
        return float(self.total_consumption / self.total_biocapacity)
