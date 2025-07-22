"""Political system database models.

These models capture the political structures, policies, and dynamics
that interact with the economic base in dialectical materialist theory.
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


class PolicyStatus(PyEnum):
    """Status of a policy."""
    
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REPEALED = "repealed"


class GovernmentType(PyEnum):
    """Types of government systems."""
    
    DEMOCRATIC = "democratic"
    AUTHORITARIAN = "authoritarian"
    SOCIALIST = "socialist"
    FASCIST = "fascist"
    ANARCHIST = "anarchist"


class PoliticalSystem(Base):
    """Represents the political system state for a game.
    
    Models the superstructure that arises from and influences
    the economic base according to historical materialist theory.
    """
    
    __tablename__ = "political_systems"
    __table_args__ = (
        Index("idx_political_game_turn", "game_id", "turn_number"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Government structure
    government_type: Mapped[GovernmentType] = mapped_column(
        Enum(GovernmentType), default=GovernmentType.DEMOCRATIC
    )
    ruling_party: Mapped[Optional[str]] = mapped_column(String(100))
    coalition_parties: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Political stability and legitimacy
    stability_index: Mapped[float] = mapped_column(Float, default=0.7)  # 0.0 to 1.0
    legitimacy_score: Mapped[float] = mapped_column(Float, default=0.6)
    popular_support: Mapped[float] = mapped_column(Float, default=0.5)
    
    # State apparatus
    bureaucracy_efficiency: Mapped[float] = mapped_column(Float, default=0.5)
    military_strength: Mapped[float] = mapped_column(Float, default=0.5)
    police_power: Mapped[float] = mapped_column(Float, default=0.5)
    
    # Democratic institutions (if applicable)
    democratic_institutions: Mapped[float] = mapped_column(Float, default=0.5)
    civil_liberties: Mapped[float] = mapped_column(Float, default=0.7)
    press_freedom: Mapped[float] = mapped_column(Float, default=0.7)
    
    # Political participation
    voter_turnout: Mapped[Optional[float]] = mapped_column(Float)
    political_engagement: Mapped[float] = mapped_column(Float, default=0.4)
    protest_activity: Mapped[float] = mapped_column(Float, default=0.1)
    
    # Ideological composition
    conservative_support: Mapped[float] = mapped_column(Float, default=0.3)
    liberal_support: Mapped[float] = mapped_column(Float, default=0.3)
    socialist_support: Mapped[float] = mapped_column(Float, default=0.2)
    radical_support: Mapped[float] = mapped_column(Float, default=0.1)
    
    # International relations
    international_standing: Mapped[float] = mapped_column(Float, default=0.5)
    diplomatic_relations: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Crisis indicators
    revolutionary_potential: Mapped[float] = mapped_column(Float, default=0.0)
    coup_risk: Mapped[float] = mapped_column(Float, default=0.0)
    civil_unrest_level: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    political_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="political_systems")
    policies: Mapped[List["Policy"]] = relationship("Policy", back_populates="political_system")
    institutions: Mapped[List["Institution"]] = relationship("Institution", back_populates="political_system")


class Policy(Base):
    """Represents a specific policy implemented by the political system.
    
    Policies are the concrete mechanisms through which the political
    superstructure influences the economic base and social relations.
    """
    
    __tablename__ = "policies"
    __table_args__ = (
        Index("idx_policy_system_status", "political_system_id", "status"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    political_system_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("political_systems.id"), nullable=False
    )
    
    # Policy identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100))  # e.g., "economic", "social", "military"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Policy status and lifecycle
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus), default=PolicyStatus.PROPOSED
    )
    implemented_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    repealed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Policy parameters
    policy_parameters: Mapped[Optional[dict]] = mapped_column(JSON)
    target_metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Effects and impacts
    economic_effects: Mapped[Optional[dict]] = mapped_column(JSON)
    social_effects: Mapped[Optional[dict]] = mapped_column(JSON)
    political_effects: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Implementation details
    implementation_cost: Mapped[Optional[float]] = mapped_column(Float)
    implementation_difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    public_support: Mapped[float] = mapped_column(Float, default=0.5)
    
    # Success metrics
    effectiveness_score: Mapped[Optional[float]] = mapped_column(Float)
    unintended_consequences: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))  # Player or system
    
    # Relationships
    political_system: Mapped["PoliticalSystem"] = relationship("PoliticalSystem", back_populates="policies")


class Institution(Base):
    """Represents political and social institutions.
    
    Models the institutional framework that mediates between
    the economic base and political superstructure.
    """
    
    __tablename__ = "institutions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    political_system_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("political_systems.id"), nullable=False
    )
    
    # Institution identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    institution_type: Mapped[str] = mapped_column(String(100))  # e.g., "legislative", "judicial", "executive"
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Institutional characteristics
    power_level: Mapped[float] = mapped_column(Float, default=0.5)
    independence: Mapped[float] = mapped_column(Float, default=0.5)
    efficiency: Mapped[float] = mapped_column(Float, default=0.5)
    legitimacy: Mapped[float] = mapped_column(Float, default=0.5)
    
    # Institutional health
    corruption_level: Mapped[float] = mapped_column(Float, default=0.1)
    bureaucratic_burden: Mapped[float] = mapped_column(Float, default=0.3)
    transparency: Mapped[float] = mapped_column(Float, default=0.5)
    
    # Functions and capabilities
    primary_functions: Mapped[Optional[List[str]]] = mapped_column(JSON)
    capabilities: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Resource allocation
    budget_allocation: Mapped[Optional[float]] = mapped_column(Float)
    personnel_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    established_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Additional data
    institutional_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Relationships
    political_system: Mapped["PoliticalSystem"] = relationship("PoliticalSystem", back_populates="institutions")


class ElectionEvent(Base):
    """Represents electoral processes and their outcomes.
    
    Models democratic participation and its effects on the
    political system and policy direction.
    """
    
    __tablename__ = "election_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Election details
    election_type: Mapped[str] = mapped_column(String(100))  # e.g., "presidential", "parliamentary", "local"
    election_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Participation metrics
    eligible_voters: Mapped[int] = mapped_column(Integer, default=0)
    votes_cast: Mapped[int] = mapped_column(Integer, default=0)
    turnout_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Results
    election_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    winning_party: Mapped[Optional[str]] = mapped_column(String(100))
    margin_of_victory: Mapped[Optional[float]] = mapped_column(Float)
    
    # Electoral conditions
    campaign_spending: Mapped[Optional[dict]] = mapped_column(JSON)
    major_issues: Mapped[Optional[List[str]]] = mapped_column(JSON)
    economic_context: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Post-election impacts
    government_formation: Mapped[Optional[dict]] = mapped_column(JSON)
    policy_mandate: Mapped[Optional[List[str]]] = mapped_column(JSON)
    legitimacy_impact: Mapped[Optional[float]] = mapped_column(Float)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    election_notes: Mapped[Optional[str]] = mapped_column(Text)