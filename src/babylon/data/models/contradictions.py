"""Contradiction system database models.

These models capture the dialectical contradictions that drive
systemic change in the Marxist framework. Contradictions are
the core engine of transformation in the game.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ContradictionType(PyEnum):
    """Types of contradictions in dialectical analysis."""
    
    ECONOMIC = "economic"
    POLITICAL = "political" 
    SOCIAL = "social"
    CULTURAL = "cultural"
    ENVIRONMENTAL = "environmental"
    CLASS = "class"


class ContradictionUniversality(PyEnum):
    """Universality level of contradictions."""
    
    UNIVERSAL = "universal"  # Present in all similar systems
    PARTICULAR = "particular"  # Specific to certain conditions
    SINGULAR = "singular"  # Unique to specific instance


class ContradictionAntagonism(PyEnum):
    """Antagonism level of contradictions."""
    
    ANTAGONISTIC = "antagonistic"  # Irreconcilable, requires systemic change
    NON_ANTAGONISTIC = "non_antagonistic"  # Can be resolved within system


class ContradictionIntensity(PyEnum):
    """Intensity levels of contradictions."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionState(PyEnum):
    """Current state of contradictions."""
    
    LATENT = "latent"  # Present but not yet manifesting
    ACTIVE = "active"  # Currently manifesting effects
    ESCALATING = "escalating"  # Increasing in intensity
    RESOLVING = "resolving"  # In process of resolution
    RESOLVED = "resolved"  # Resolved (temporarily or permanently)
    TRANSFORMED = "transformed"  # Led to systemic transformation


class Contradiction(Base):
    """Represents a dialectical contradiction in the system.
    
    Contradictions are the driving force of change in dialectical
    materialist analysis. They exist between opposing forces or
    aspects within the same phenomenon.
    """
    
    __tablename__ = "contradictions"
    __table_args__ = (
        Index("idx_contradiction_game_type", "game_id", "contradiction_type"),
        Index("idx_contradiction_intensity_state", "intensity", "state"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Contradiction identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contradiction_type: Mapped[ContradictionType] = mapped_column(
        Enum(ContradictionType), nullable=False
    )
    
    # Dialectical properties
    universality: Mapped[ContradictionUniversality] = mapped_column(
        Enum(ContradictionUniversality), default=ContradictionUniversality.PARTICULAR
    )
    antagonism: Mapped[ContradictionAntagonism] = mapped_column(
        Enum(ContradictionAntagonism), nullable=False
    )
    
    # Current state
    intensity: Mapped[ContradictionIntensity] = mapped_column(
        Enum(ContradictionIntensity), default=ContradictionIntensity.LOW
    )
    state: Mapped[ContradictionState] = mapped_column(
        Enum(ContradictionState), default=ContradictionState.LATENT
    )
    
    # Quantitative measures
    intensity_value: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    stability_impact: Mapped[float] = mapped_column(Float, default=0.0)  # Impact on system stability
    transformation_potential: Mapped[float] = mapped_column(Float, default=0.0)  # Potential for systemic change
    
    # Aspects of the contradiction
    principal_aspect: Mapped[Optional[str]] = mapped_column(String(200))
    secondary_aspect: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Related entities and systems
    affected_entities: Mapped[Optional[List[int]]] = mapped_column(JSON)  # Entity IDs
    related_systems: Mapped[Optional[List[str]]] = mapped_column(JSON)  # e.g., ["economic", "political"]
    
    # Resolution information
    resolution_methods: Mapped[Optional[dict]] = mapped_column(JSON)
    conditions_for_transformation: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Historical tracking
    first_observed_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    last_escalation_turn: Mapped[Optional[int]] = mapped_column(Integer)
    resolution_turn: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships to other contradictions
    parent_contradiction_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contradictions.id")
    )
    is_principal_contradiction: Mapped[bool] = mapped_column(default=False)
    
    # Additional data
    contradiction_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="contradictions")
    history: Mapped[List["ContradictionHistory"]] = relationship(
        "ContradictionHistory", back_populates="contradiction", cascade="all, delete-orphan"
    )
    child_contradictions: Mapped[List["Contradiction"]] = relationship(
        "Contradiction", remote_side=[parent_contradiction_id]
    )
    effects: Mapped[List["ContradictionEffect"]] = relationship(
        "ContradictionEffect", back_populates="contradiction", cascade="all, delete-orphan"
    )


class ContradictionHistory(Base):
    """Tracks the historical evolution of contradictions.
    
    This captures how contradictions develop, intensify, and resolve
    over time, providing insight into dialectical processes.
    """
    
    __tablename__ = "contradiction_history"
    __table_args__ = (
        Index("idx_contradiction_hist_turn", "contradiction_id", "turn_number"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Historical state
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_intensity: Mapped[Optional[ContradictionIntensity]] = mapped_column(
        Enum(ContradictionIntensity)
    )
    new_intensity: Mapped[ContradictionIntensity] = mapped_column(
        Enum(ContradictionIntensity), nullable=False
    )
    previous_state: Mapped[Optional[ContradictionState]] = mapped_column(
        Enum(ContradictionState)
    )
    new_state: Mapped[ContradictionState] = mapped_column(
        Enum(ContradictionState), nullable=False
    )
    
    # Quantitative changes
    intensity_change: Mapped[float] = mapped_column(Float, default=0.0)
    stability_impact_change: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Change triggers
    triggering_event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("events.id")
    )
    change_factors: Mapped[Optional[dict]] = mapped_column(JSON)
    change_description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    contradiction: Mapped["Contradiction"] = relationship("Contradiction", back_populates="history")


class ContradictionEffect(Base):
    """Represents the effects that contradictions have on the system.
    
    This models how contradictions manifest their influence on
    various aspects of the game world.
    """
    
    __tablename__ = "contradiction_effects"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Effect identification
    effect_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "economic", "political"
    effect_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Effect parameters
    target_system: Mapped[Optional[str]] = mapped_column(String(100))  # System affected
    target_entity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("entities.id")
    )
    
    # Effect magnitude and direction
    effect_magnitude: Mapped[float] = mapped_column(Float, default=0.0)
    effect_direction: Mapped[str] = mapped_column(String(20))  # "positive", "negative", "neutral"
    
    # Conditions and triggers
    trigger_conditions: Mapped[Optional[dict]] = mapped_column(JSON)
    effect_duration: Mapped[Optional[int]] = mapped_column(Integer)  # In turns, if limited
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    activation_turn: Mapped[Optional[int]] = mapped_column(Integer)
    deactivation_turn: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Additional effect data
    effect_parameters: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    contradiction: Mapped["Contradiction"] = relationship("Contradiction", back_populates="effects")


class ContradictionNetwork(Base):
    """Represents relationships between contradictions.
    
    Models how contradictions interact with and influence each other,
    creating complex networks of dialectical relationships.
    """
    
    __tablename__ = "contradiction_networks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    target_contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Relationship details
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "amplifies", "suppresses", "generates"
    relationship_strength: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Description and context
    description: Mapped[Optional[str]] = mapped_column(Text)
    conditions: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    discovered_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Additional relationship data
    network_data: Mapped[Optional[dict]] = mapped_column(JSON)


class ContradictionResolution(Base):
    """Records attempts to resolve contradictions and their outcomes.
    
    This tracks both successful and failed attempts to resolve
    contradictions, providing insight into what works and what doesn't.
    """
    
    __tablename__ = "contradiction_resolutions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Resolution attempt details
    resolution_method: Mapped[str] = mapped_column(String(200), nullable=False)
    attempted_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_by: Mapped[Optional[str]] = mapped_column(String(100))  # Player, system, event
    
    # Resolution approach
    approach_description: Mapped[str] = mapped_column(Text, nullable=False)
    resources_invested: Mapped[Optional[dict]] = mapped_column(JSON)
    policies_implemented: Mapped[Optional[List[int]]] = mapped_column(JSON)  # Policy IDs
    
    # Outcome
    success_level: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    actual_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    unintended_consequences: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Impact assessment
    intensity_reduction: Mapped[float] = mapped_column(Float, default=0.0)
    new_contradictions_created: Mapped[Optional[List[int]]] = mapped_column(JSON)  # IDs of new contradictions
    systemic_changes: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)