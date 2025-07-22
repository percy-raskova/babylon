"""Core database models for game management and state."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class GameStatus(PyEnum):
    """Enum for game status."""
    
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Game(Base):
    """Represents a game session.
    
    A game is a complete playthrough session that tracks the overall
    state and progression of a player through the simulation.
    """
    
    __tablename__ = "games"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus), default=GameStatus.ACTIVE, nullable=False
    )
    
    # Game settings and configuration
    difficulty_level: Mapped[str] = mapped_column(String(50), default="normal")
    scenario: Mapped[Optional[str]] = mapped_column(String(100))
    initial_conditions: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_played_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Game progression
    current_turn: Mapped[int] = mapped_column(Integer, default=0)
    total_turns_played: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    players: Mapped[List["Player"]] = relationship("Player", back_populates="game")
    game_states: Mapped[List["GameState"]] = relationship("GameState", back_populates="game")
    economies: Mapped[List["Economy"]] = relationship("Economy", back_populates="game")
    political_systems: Mapped[List["PoliticalSystem"]] = relationship("PoliticalSystem", back_populates="game")
    contradictions: Mapped[List["Contradiction"]] = relationship("Contradiction", back_populates="game")
    entities: Mapped[List["Entity"]] = relationship("Entity", back_populates="game")


class Player(Base):
    """Represents a player in the game.
    
    Tracks player information, statistics, and their relationship
    to specific games and decisions made.
    """
    
    __tablename__ = "players"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Player identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    player_type: Mapped[str] = mapped_column(String(50), default="human")  # human, ai, bot
    
    # Player statistics
    decisions_made: Mapped[int] = mapped_column(Integer, default=0)
    objectives_completed: Mapped[int] = mapped_column(Integer, default=0)
    crises_survived: Mapped[int] = mapped_column(Integer, default=0)
    
    # Player preferences and strategy
    political_alignment: Mapped[Optional[str]] = mapped_column(String(100))
    economic_strategy: Mapped[Optional[str]] = mapped_column(String(100))
    preferred_policies: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="players")
    decisions: Mapped[List["PlayerDecision"]] = relationship("PlayerDecision", back_populates="player")


class GameState(Base):
    """Represents a snapshot of game state at a specific point in time.
    
    This allows for save/load functionality and historical analysis
    of how the game state evolved over time.
    """
    
    __tablename__ = "game_states"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # State identification
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state_name: Mapped[Optional[str]] = mapped_column(String(200))
    is_save_point: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Complete game state snapshot
    economic_state: Mapped[Optional[dict]] = mapped_column(JSON)
    political_state: Mapped[Optional[dict]] = mapped_column(JSON)
    entity_state: Mapped[Optional[dict]] = mapped_column(JSON)
    contradiction_state: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    checksum: Mapped[Optional[str]] = mapped_column(String(64))  # For data integrity
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="game_states")


class PlayerDecision(Base):
    """Records player decisions and their impacts on the game.
    
    This tracks all decisions made by players to enable analysis
    of decision patterns and their consequences.
    """
    
    __tablename__ = "player_decisions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Decision details
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False)
    decision_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Decision context and parameters
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Decision outcomes
    immediate_effects: Mapped[Optional[dict]] = mapped_column(JSON)
    long_term_effects: Mapped[Optional[dict]] = mapped_column(JSON)
    success_rating: Mapped[Optional[float]] = mapped_column()  # 0.0 to 1.0
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="decisions")