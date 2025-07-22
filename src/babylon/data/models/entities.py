"""Entity system database models.

These models represent the general entity system used throughout
the game to represent various game objects, their attributes,
and relationships.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class EntityType(PyEnum):
    """Types of entities in the game."""
    
    ORGANIZATION = "organization"
    INSTITUTION = "institution"
    RESOURCE = "resource"
    COMMODITY = "commodity"
    TECHNOLOGY = "technology"
    INFRASTRUCTURE = "infrastructure"
    SOCIAL_GROUP = "social_group"
    GEOGRAPHICAL = "geographical"


class EntityStatus(PyEnum):
    """Status of an entity."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    DESTROYED = "destroyed"
    ARCHIVED = "archived"


class RelationType(PyEnum):
    """Types of relationships between entities."""
    
    OWNS = "owns"
    CONTROLS = "controls"
    INFLUENCES = "influences"
    DEPENDS_ON = "depends_on"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    COMPETES_WITH = "competes_with"
    COOPERATES_WITH = "cooperates_with"
    SUPPLIES = "supplies"
    LOCATED_IN = "located_in"


class Entity(Base):
    """Represents a game entity with attributes and relationships.
    
    This is the core entity model that represents all game objects
    that can have properties, relationships, and participate in events.
    """
    
    __tablename__ = "entities"
    __table_args__ = (
        Index("idx_entity_game_type", "game_id", "entity_type"),
        Index("idx_entity_name_game", "name", "game_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Entity identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Entity status and lifecycle
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus), default=EntityStatus.ACTIVE
    )
    created_turn: Mapped[int] = mapped_column(Integer, default=0)
    last_modified_turn: Mapped[int] = mapped_column(Integer, default=0)
    
    # Core attributes (stored as JSON for flexibility)
    attributes: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Entity metrics and properties
    influence_score: Mapped[float] = mapped_column(Float, default=0.0)
    resource_value: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_importance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Location and context
    location: Mapped[Optional[str]] = mapped_column(String(200))
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Additional data storage
    entity_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="entities")
    attributes_detailed: Mapped[List["EntityAttribute"]] = relationship(
        "EntityAttribute", back_populates="entity", cascade="all, delete-orphan"
    )
    outgoing_relationships: Mapped[List["EntityRelationship"]] = relationship(
        "EntityRelationship", 
        foreign_keys="EntityRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    incoming_relationships: Mapped[List["EntityRelationship"]] = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.target_entity_id", 
        back_populates="target_entity"
    )
    entity_events: Mapped[List["EntityEvent"]] = relationship(
        "EntityEvent", back_populates="entity"
    )


class EntityAttribute(Base):
    """Represents detailed attributes of entities with history tracking.
    
    This allows for tracking changes in entity attributes over time
    and provides more structured storage than the JSON field.
    """
    
    __tablename__ = "entity_attributes"
    __table_args__ = (
        UniqueConstraint("entity_id", "attribute_name", name="uq_entity_attribute"),
        Index("idx_attribute_entity_name", "entity_id", "attribute_name"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("entities.id"), nullable=False)
    
    # Attribute identification
    attribute_name: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_type: Mapped[str] = mapped_column(String(50))  # e.g., "numeric", "string", "boolean"
    
    # Attribute values (one will be used based on type)
    numeric_value: Mapped[Optional[float]] = mapped_column(Float)
    string_value: Mapped[Optional[str]] = mapped_column(String(500))
    json_value: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    last_updated_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Context and notes
    attribute_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    entity: Mapped["Entity"] = relationship("Entity", back_populates="attributes_detailed")
    history: Mapped[List["EntityAttributeHistory"]] = relationship(
        "EntityAttributeHistory", back_populates="attribute", cascade="all, delete-orphan"
    )


class EntityAttributeHistory(Base):
    """Tracks the history of changes to entity attributes.
    
    This provides a complete audit trail of how entity attributes
    change over time, useful for analysis and debugging.
    """
    
    __tablename__ = "entity_attribute_history"
    __table_args__ = (
        Index("idx_history_attribute_turn", "attribute_id", "turn_number"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attribute_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entity_attributes.id"), nullable=False
    )
    
    # Historical values
    old_numeric_value: Mapped[Optional[float]] = mapped_column(Float)
    new_numeric_value: Mapped[Optional[float]] = mapped_column(Float)
    old_string_value: Mapped[Optional[str]] = mapped_column(String(500))
    new_string_value: Mapped[Optional[str]] = mapped_column(String(500))
    old_json_value: Mapped[Optional[dict]] = mapped_column(JSON)
    new_json_value: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Change context
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(String(200))
    changed_by: Mapped[Optional[str]] = mapped_column(String(100))  # Player, event, system, etc.
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    attribute: Mapped["EntityAttribute"] = relationship("EntityAttribute", back_populates="history")


class EntityRelationship(Base):
    """Represents relationships between entities.
    
    Models the complex web of relationships between game entities,
    which is crucial for understanding systemic interactions.
    """
    
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id", "target_entity_id", "relationship_type",
            name="uq_entity_relationship"
        ),
        Index("idx_rel_source_type", "source_entity_id", "relationship_type"),
        Index("idx_rel_target_type", "target_entity_id", "relationship_type"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False
    )
    target_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False
    )
    
    # Relationship details
    relationship_type: Mapped[RelationType] = mapped_column(
        Enum(RelationType), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationship strength and properties
    strength: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0 to 1.0
    bidirectional: Mapped[bool] = mapped_column(default=False)
    
    # Lifecycle
    established_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    last_interaction_turn: Mapped[Optional[int]] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(default=True)
    
    # Additional relationship data
    relationship_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    source_entity: Mapped["Entity"] = relationship(
        "Entity", 
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships"
    )
    target_entity: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships"
    )


class EntityEvent(Base):
    """Links entities to events that affect them.
    
    This provides a many-to-many relationship between entities
    and events, allowing tracking of which entities are involved
    in or affected by specific events.
    """
    
    __tablename__ = "entity_events"
    __table_args__ = (
        UniqueConstraint("entity_id", "event_id", name="uq_entity_event"),
        Index("idx_entity_event_entity", "entity_id"),
        Index("idx_entity_event_event", "event_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("entities.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Role in event
    role: Mapped[str] = mapped_column(String(100))  # e.g., "target", "cause", "participant"
    impact_level: Mapped[float] = mapped_column(Float, default=0.0)  # -1.0 to 1.0
    
    # Impact details
    impact_description: Mapped[Optional[str]] = mapped_column(Text)
    attribute_changes: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    entity: Mapped["Entity"] = relationship("Entity", back_populates="entity_events")
    # Note: event relationship will be added when we import Event model