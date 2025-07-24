"""Database models for the Babylon game.

This module provides access to all database models used in the game,
including core game management, economic system, political system,
entity management, contradictions, and events.
"""

# Import all model classes
from .core import Game, Player, GameState, PlayerDecision
from .economic import (
    Economy,
    EconomicTimeSeries,
    ClassRelation,
    ProductionSector,
)
from .political import (
    PoliticalSystem,
    Policy,
    Institution,
    ElectionEvent,
)
from .entities import (
    Entity,
    EntityAttribute,
    EntityAttributeHistory,
    EntityRelationship,
    EntityEvent,
)
from .contradictions import (
    Contradiction,
    ContradictionHistory,
    ContradictionEffect,
    ContradictionNetwork,
    ContradictionResolution,
)
from .event import Event
from .trigger import Trigger

# Export all models
__all__ = [
    # Core models
    "Game",
    "Player", 
    "GameState",
    "PlayerDecision",
    
    # Economic models
    "Economy",
    "EconomicTimeSeries",
    "ClassRelation",
    "ProductionSector",
    
    # Political models
    "PoliticalSystem",
    "Policy",
    "Institution", 
    "ElectionEvent",
    
    # Entity models
    "Entity",
    "EntityAttribute",
    "EntityAttributeHistory",
    "EntityRelationship",
    "EntityEvent",
    
    # Contradiction models
    "Contradiction",
    "ContradictionHistory",
    "ContradictionEffect",
    "ContradictionNetwork",
    "ContradictionResolution",
    
    # Event models
    "Event",
    "Trigger",
]
