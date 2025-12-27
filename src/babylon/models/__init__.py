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
    IdeologicalComponent,
    MaterialComponent,
    OrganizationComponent,
    SpatialComponent,
    VitalityComponent,
)
from babylon.models.config import SimulationConfig

# Entity Models (migrated from old dataclasses)
from babylon.models.entities import (
    Contradiction,
    ContradictionState,
    Effect,
    GlobalEconomy,
    IdeologicalProfile,
    Relationship,
    ResolutionOutcome,
    SocialClass,
    Trigger,
    TriggerCondition,
)
from babylon.models.enums import (
    EdgeType,
    IntensityLevel,
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
    "ContradictionState",
    "ResolutionOutcome",
    "Contradiction",
    "Trigger",
    "TriggerCondition",
    # Component System (Material Ontology)
    "Component",
    "MaterialComponent",
    "VitalityComponent",
    "SpatialComponent",
    "IdeologicalComponent",
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
]
