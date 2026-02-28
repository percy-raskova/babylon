"""Organization Base Model for the Babylon simulation (Feature 031).

Provides a unified Organization agent model with four frozen Pydantic subtypes
(StateApparatus, Business, PoliticalFaction, CivilSocietyOrg), composition
calculators, consciousness effect formula, topology classification, key figure
identification, and legacy migration utilities.
"""

# Composition calculators
from babylon.organizations.composition import (
    class_composition,
    community_composition,
    effective_capacity,
    lifecycle_composition,
)

# Consciousness effect formula
from babylon.organizations.consciousness import (
    aggregate_consciousness_effects,
    consciousness_effect,
    derive_credibility,
)

# Legacy migration
from babylon.organizations.migration import (
    migrate_all,
    migrate_faction,
    migrate_institution,
)

# Topology classification + key figures
from babylon.organizations.topology import (
    classify_topology,
    cohesion_loss_on_removal,
    identify_key_figures,
)

# Computed types
from babylon.organizations.types import (
    AggregatedEffect,
    CompositionResult,
    ConsciousnessDelta,
    TopologyClassification,
)

__all__ = [
    # Composition
    "class_composition",
    "community_composition",
    "effective_capacity",
    "lifecycle_composition",
    # Consciousness
    "aggregate_consciousness_effects",
    "consciousness_effect",
    "derive_credibility",
    # Topology
    "classify_topology",
    "cohesion_loss_on_removal",
    "identify_key_figures",
    # Migration
    "migrate_all",
    "migrate_faction",
    "migrate_institution",
    # Types
    "AggregatedEffect",
    "CompositionResult",
    "ConsciousnessDelta",
    "TopologyClassification",
]
