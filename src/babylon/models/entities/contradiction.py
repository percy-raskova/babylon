"""Contradiction models for dialectical simulation.

Contradictions are structural tensions between opposing forces.
They are the engine of historical change in the simulation.

This module consolidates:
- ContradictionState (was in systems/contradiction_analysis.py)
- ResolutionOutcome (was a dataclass in systems/contradiction_analysis.py)
- Contradiction (was a dataclass in data/models/contradiction.py)

All models now use Sprint 1 types for consistency.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from babylon.models.enums import IntensityLevel, ResolutionType
from babylon.models.types import Intensity, Probability

from .effect import Effect


class ContradictionState(BaseModel):
    """The current state of a dialectical contradiction.

    A contradiction is a structural tension between two forces
    that cannot both be satisfied within the current system.
    This is the primary model for tracking contradictions.

    Attributes:
        id: Unique identifier (flexible format for runtime use)
        name: Human-readable name
        description: Detailed explanation
        thesis: The dominant position
        antithesis: The opposing position
        tension: Current tension level [0, 1]
        momentum: Rate of change [-1, 1]
        is_principal: Is this the principal contradiction?
        resolved: Has this been resolved?
    """

    id: str = Field(..., description="Unique identifier for this contradiction")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Detailed explanation")

    # The opposing forces
    thesis: str = Field(..., description="The dominant position")
    antithesis: str = Field(..., description="The opposing position")

    # Intensity metrics using Sprint 1 types
    tension: Intensity = Field(
        default=0.0, description="Current tension level (0=dormant, 1=rupture)"
    )
    momentum: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Rate of change (-1=resolving, 1=intensifying)",
    )

    # Resolution state
    is_principal: bool = Field(
        default=False,
        description="Is this the principal contradiction of the current period?",
    )
    resolved: bool = Field(default=False, description="Has this contradiction been resolved?")

    model_config = {"extra": "forbid"}

    @property
    def intensity_level(self) -> IntensityLevel:
        """Convert continuous tension to discrete IntensityLevel."""
        if self.tension < 0.1:
            return IntensityLevel.DORMANT
        elif self.tension < 0.3:
            return IntensityLevel.LOW
        elif self.tension < 0.6:
            return IntensityLevel.MEDIUM
        elif self.tension < 0.9:
            return IntensityLevel.HIGH
        else:
            return IntensityLevel.CRITICAL

    @property
    def is_critical(self) -> bool:
        """Check if tension is at critical level (rupture imminent)."""
        return self.tension >= 0.9


class ResolutionOutcome(BaseModel):
    """The result of a contradiction reaching resolution.

    When a contradiction resolves (tension reaches 0 or 1),
    this model captures what happened and the consequences.

    Attributes:
        contradiction_id: ID of the resolved contradiction
        resolution_type: How it resolved (synthesis, rupture, suppression)
        new_contradictions: IDs of contradictions spawned by resolution
        system_changes: Metric deltas caused by resolution
    """

    contradiction_id: str = Field(..., description="ID of the resolved contradiction")
    resolution_type: ResolutionType = Field(..., description="How the contradiction resolved")
    new_contradictions: list[str] = Field(
        default_factory=list, description="IDs of contradictions spawned"
    )
    system_changes: dict[str, float] = Field(
        default_factory=dict, description="Metric deltas from resolution"
    )

    model_config = {"extra": "forbid"}


class Contradiction(BaseModel):
    """Full contradiction model with entities and resolution methods.

    This is a more detailed model for contradictions that includes
    references to entities and resolution mechanics. Used for
    game content definition.

    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Detailed explanation
        entity_ids: IDs of entities involved in this contradiction
        universality: Universal or Particular
        particularity: Domain (Economic, Political, etc.)
        principal_contradiction_id: ID of the principal contradiction (if this is secondary)
        principal_aspect_id: ID of the entity representing the principal aspect
        secondary_aspect_id: ID of the entity representing the secondary aspect
        antagonism: Primary or Secondary antagonism
        intensity: Current intensity level
        state: Active, Resolved, or Latent
        potential_for_transformation: How likely to transform
        conditions_for_transformation: What conditions must be met
        resolution_methods: Mapping of method names to Effects
    """

    id: str = Field(..., pattern=r"^CON[0-9]{3}$", description="Contradiction ID")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Detailed explanation")

    # Entities involved (stored as IDs for graph lookup)
    entity_ids: list[str] = Field(default_factory=list, description="Entity IDs involved")
    principal_aspect_id: str | None = Field(
        default=None, description="Entity ID of principal aspect"
    )
    secondary_aspect_id: str | None = Field(
        default=None, description="Entity ID of secondary aspect"
    )
    principal_contradiction_id: str | None = Field(
        default=None, description="ID of the principal contradiction if this is secondary"
    )

    # Classification
    universality: str = Field(
        default="Particular",
        pattern=r"^(Universal|Particular)$",
        description="Universal or Particular contradiction",
    )
    particularity: str = Field(
        default="Economic", description="Domain: Economic, Political, Cultural, etc."
    )
    antagonism: str = Field(
        default="Secondary",
        pattern=r"^(Primary|Secondary)$",
        description="Primary or Secondary antagonism",
    )

    # State using Sprint 1 types
    intensity: IntensityLevel = Field(
        default=IntensityLevel.LOW, description="Current intensity level"
    )
    state: str = Field(
        default="Active",
        pattern=r"^(Active|Resolved|Latent)$",
        description="Current state",
    )
    potential_for_transformation: IntensityLevel = Field(
        default=IntensityLevel.LOW, description="Likelihood of transformation"
    )

    # Transformation conditions
    conditions_for_transformation: list[str] = Field(
        default_factory=list, description="Conditions that must be met for transformation"
    )

    # Resolution mechanics
    resolution_methods: dict[str, list[Effect]] = Field(
        default_factory=dict, description="Mapping of resolution method names to their Effects"
    )

    # History
    intensity_history: list[Intensity] = Field(
        default_factory=list, description="Historical intensity values"
    )

    model_config = {"extra": "forbid"}

    @property
    def intensity_value(self) -> float:
        """Get numerical value for intensity."""
        intensity_map = {
            IntensityLevel.DORMANT: 0.0,
            IntensityLevel.LOW: 0.25,
            IntensityLevel.MEDIUM: 0.5,
            IntensityLevel.HIGH: 0.75,
            IntensityLevel.CRITICAL: 1.0,
        }
        return intensity_map.get(self.intensity, 0.0)

    def record_intensity(self) -> None:
        """Record current intensity in history."""
        self.intensity_history.append(self.intensity_value)
        # Keep last 10 entries
        if len(self.intensity_history) > 10:
            self.intensity_history.pop(0)
