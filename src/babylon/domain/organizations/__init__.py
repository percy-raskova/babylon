"""Organization Base Model for the Babylon simulation (Feature 031).

Provides a unified Organization agent model with four frozen Pydantic subtypes
(StateApparatus, Business, PoliticalFaction, CivilSocietyOrg), composition
calculators, consciousness effect formula, topology classification, and legacy
migration utilities.
"""

# Composition calculators
from babylon.domain.organizations.composition import (
    class_composition,
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

# Topology classification
from babylon.domain.organizations.topology import (
    classify_topology,
    cohesion_loss_on_removal,
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
    "effective_capacity",
    "lifecycle_composition",
    # Consciousness
    "tendency_modifier",
    # Topology
    "classify_topology",
    "cohesion_loss_on_removal",
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
