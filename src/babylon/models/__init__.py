"""Pydantic models for the Babylon simulation engine.

This package contains the type system foundation:
- enums: Categorical types (SocialRole, EdgeType, etc.)
- types: Constrained value types (Probability, Currency, etc.)
- entities: Game objects (Effect, Contradiction, Trigger, etc.)
- components: Entity-Component system (Material, Vitality, Spatial, etc.)

All game state flows through these validated types.
"""

# Sprint 1: Enums and Value Types
# Sprint 3: Simulation Configuration
# Component Models (Entity-Component architecture)
from babylon.models.components import (
    Component,
    MaterialComponent,
    OrganizationComponent,
    SpatialComponent,
    VitalityComponent,
)
from babylon.models.config import SimulationConfig

# Entity Models (migrated from old dataclasses)
from babylon.models.entities import (
    Contradiction,
    ContradictionFrame,
    Effect,
    GlobalEconomy,
    IdeologicalProfile,
    Relationship,
    SocialClass,
    Trigger,
    TriggerCondition,
)
from babylon.models.entities.community import (
    CommunityConsciousness,
    CommunityMembership,
    CommunityState,
)
from babylon.models.entities.consciousness import (
    OrgContribution,
    ProvenanceLevel,
    SubstrateFloor,
    TernaryConsciousness,
)

# Entity Registry (single source of truth for entity IDs)
from babylon.models.entity_registry import (
    ALL_ENTITY_IDS,
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    ENTITY_ID_TO_ROLE,
    ENTITY_SLOT_NAMES,
    LABOR_ARISTOCRACY_ID,
    METRICS_ENTITY_IDS,
    PERIPHERY_WORKER_ID,
    ROLE_TO_ENTITY_ID,
    entity_id_to_role,
    get_slot_name,
    role_to_entity_id,
)
from babylon.models.enums import (
    CommunityType,
    ConsciousnessTendency,
    ContradictionType,
    EdgeType,
    HyperedgeCategory,
    IntensityLevel,
    LegalStatus,
    MembershipRole,
    ResolutionType,
    SocialRole,
)

# Slice 1.7: Graph Abstraction Layer
from babylon.models.graph import (
    EdgeFilter,
    GraphEdge,
    GraphNode,
    NodeFilter,
    TraversalQuery,
    TraversalResult,
)

# Sprint 4.1: Unified Metrics (MetricsCollector observer)
from babylon.models.metrics import EdgeMetrics, EntityMetrics, SweepSummary, TickMetrics

# Scenario configuration for multiverse simulation
from babylon.models.scenario import ScenarioConfig

# MVP Simulation Engine: Snapshot types
from babylon.models.snapshots import (
    EdgeState,
    HexState,
    SimulationSnapshot,
    SnapshotEdgeType,
    TerritoryState,
)

# Sprint 3.1: Topology Metrics
from babylon.models.topology_metrics import ResilienceResult, TopologySnapshot
from babylon.models.types import (
    Coefficient,
    Currency,
    Ideology,
    Intensity,
    Probability,
    Ratio,
)

# Sprint 4: World State
from babylon.models.world_state import WorldState

__all__ = [
    # Enums
    "SocialRole",
    "EdgeType",
    "IntensityLevel",
    "ResolutionType",
    # Value Types
    "Probability",
    "Ideology",
    "Currency",
    "Intensity",
    "Coefficient",
    "Ratio",
    # Sprint 3: Configuration
    "SimulationConfig",
    # Multiverse Protocol: Scenario Configuration
    "ScenarioConfig",
    # Sprint 4: World State
    "WorldState",
    # Phase 1 Entities
    "SocialClass",
    "Relationship",
    "IdeologicalProfile",  # Sprint 3.4.3 - George Jackson Refactor
    "GlobalEconomy",  # Sprint 3.4.4 - Dynamic Balance
    # Other Entities
    "Effect",
    "ContradictionFrame",
    "Contradiction",
    "Trigger",
    "TriggerCondition",
    # Component System (Material Ontology)
    "Component",
    "MaterialComponent",
    "VitalityComponent",
    "SpatialComponent",
    "OrganizationComponent",
    # Sprint 3.1: Topology Metrics
    "TopologySnapshot",
    "ResilienceResult",
    # Sprint 4.1: Unified Metrics (MetricsCollector observer)
    "EntityMetrics",
    "EdgeMetrics",
    "TickMetrics",
    "SweepSummary",
    # Slice 1.7: Graph Abstraction Layer
    "GraphNode",
    "GraphEdge",
    "EdgeFilter",
    "NodeFilter",
    "TraversalQuery",
    "TraversalResult",
    # Entity Registry (single source of truth for entity IDs)
    "PERIPHERY_WORKER_ID",
    "COMPRADOR_ID",
    "CORE_BOURGEOISIE_ID",
    "LABOR_ARISTOCRACY_ID",
    "ROLE_TO_ENTITY_ID",
    "ENTITY_ID_TO_ROLE",
    "ENTITY_SLOT_NAMES",
    "METRICS_ENTITY_IDS",
    "ALL_ENTITY_IDS",
    "role_to_entity_id",
    "entity_id_to_role",
    "get_slot_name",
    # MVP Simulation Engine: Snapshot types
    "HexState",
    "EdgeState",
    "TerritoryState",
    "SimulationSnapshot",
    "SnapshotEdgeType",
    # Community Layer (Feature 022)
    "CommunityType",
    "LegalStatus",
    "MembershipRole",
    "CommunityState",
    "CommunityMembership",
    # Community Hyperedge Upgrade (Feature 029)
    "HyperedgeCategory",
    "ConsciousnessTendency",
    "CommunityConsciousness",
    "ContradictionType",
    # Ternary Consciousness (Feature 034)
    "TernaryConsciousness",
    "SubstrateFloor",
    "ProvenanceLevel",
    "OrgContribution",
]
