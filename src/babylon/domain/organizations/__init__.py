"""Organization Base Model for the Babylon simulation (Feature 031).

Provides a unified Organization agent model with four frozen Pydantic subtypes
(StateApparatus, Business, PoliticalFaction, CivilSocietyOrg), composition
calculators, consciousness effect formula, topology classification, key figure
identification, and legacy migration utilities.
"""

# Composition calculators
from babylon.domain.organizations.composition import (
    class_composition,
    community_composition,
    effective_capacity,
    lifecycle_composition,
)

# Consciousness tendency modifier (F7 survivor; the effect trio was retired)
from babylon.domain.organizations.consciousness import tendency_modifier

# Legacy migration
from babylon.domain.organizations.migration import (
    migrate_all,
    migrate_faction,
    migrate_institution,
)

# Topology classification + key figures
from babylon.domain.organizations.topology import (
    classify_topology,
    cohesion_loss_on_removal,
    identify_key_figures,
)

# Computed types
from babylon.domain.organizations.types import (
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
    "tendency_modifier",
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
