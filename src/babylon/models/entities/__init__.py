"""Entity models for the Babylon simulation.

Entities are the objects that make up the simulation:
- SocialClass: Phase 1 node - a social class in the world system
- Territory: Phase 3.5 node - a strategic sector in the world system
- Effect: Atomic state modifications
- ContradictionState: Dialectical tension state
- ResolutionOutcome: Result of contradiction resolution
- Contradiction: Full contradiction with entities and methods
- Trigger: Event triggering conditions
- TriggerCondition: Individual condition within a trigger

All models use Pydantic v2 with Sprint 1 constrained types.
"""

from babylon.models.entities.contradiction import (
    Contradiction,
    ContradictionState,
    ResolutionOutcome,
)
from babylon.models.entities.effect import Effect
from babylon.models.entities.relationship import FlowComponent, Relationship
from babylon.models.entities.social_class import (
    EconomicComponent,
    IdeologicalComponent,
    IdeologicalProfile,
    MaterialConditionsComponent,
    SocialClass,
    SurvivalComponent,
)
from babylon.models.entities.territory import Territory
from babylon.models.entities.trigger import Trigger, TriggerCondition

__all__ = [
    # Phase 1 Nodes
    "SocialClass",
    # Phase 3.5 Nodes (Layer 0 - Territory)
    "Territory",
    # Phase 1 Edges
    "Relationship",
    # Effect
    "Effect",
    # Contradiction
    "ContradictionState",
    "ResolutionOutcome",
    "Contradiction",
    # Trigger
    "Trigger",
    "TriggerCondition",
    # Component Models
    "EconomicComponent",
    "IdeologicalComponent",
    "IdeologicalProfile",  # Sprint 3.4.3 - George Jackson Refactor
    "SurvivalComponent",
    "MaterialConditionsComponent",
    "FlowComponent",
]
