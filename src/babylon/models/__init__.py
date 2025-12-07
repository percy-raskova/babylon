"""Pydantic models for the Babylon simulation engine.

This package contains the type system foundation:
- enums: Categorical types (SocialRole, EdgeType, etc.)
- types: Constrained value types (Probability, Currency, etc.)
- entities: Game objects (Effect, Contradiction, Trigger, etc.)

All game state flows through these validated types.
"""

# Sprint 1: Enums and Value Types
from babylon.models.enums import (
    EdgeType,
    IntensityLevel,
    ResolutionType,
    SocialRole,
)
from babylon.models.types import (
    Coefficient,
    Currency,
    Ideology,
    Intensity,
    Probability,
    Ratio,
)

# Entity Models (migrated from old dataclasses)
from babylon.models.entities import (
    Contradiction,
    ContradictionState,
    Effect,
    Relationship,
    ResolutionOutcome,
    SocialClass,
    Trigger,
    TriggerCondition,
)

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
    # Phase 1 Entities
    "SocialClass",
    "Relationship",
    # Other Entities
    "Effect",
    "ContradictionState",
    "ResolutionOutcome",
    "Contradiction",
    "Trigger",
    "TriggerCondition",
]
