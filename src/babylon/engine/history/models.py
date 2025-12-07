"""Pydantic models for the History Stack system.

These models provide:
- CheckpointMetadata: Context for saved checkpoints (timestamp, tick, description)
- Checkpoint: Full state bundle (metadata + WorldState + SimulationConfig)
- HistoryEntry: Single state snapshot for the history stack
- HistoryStack: Immutable stack of history entries with undo/redo support
- CheckpointConfig: Configuration for auto-checkpointing

All models are frozen (immutable) for functional transformation patterns.
The state is pure data; transformations create new instances.

Sprint A: History Stack models for Phase 3 persistence layer.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState


class CheckpointMetadata(BaseModel):
    """Metadata for a saved checkpoint.

    Captures context about when and why a checkpoint was created.
    Used for checkpoint listing and identification.

    Attributes:
        created_at: UTC timestamp when the checkpoint was created.
        tick: The simulation tick at checkpoint time.
        description: Optional human-readable description of the checkpoint.
        version: Schema version for compatibility checking.
    """

    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(
        ...,
        description="UTC timestamp when checkpoint was created",
    )
    tick: int = Field(
        ...,
        ge=0,
        description="Simulation tick at checkpoint time",
    )
    description: str = Field(
        default="",
        description="Human-readable checkpoint description",
    )
    version: str = Field(
        default="1.0.0",
        description="Schema version for compatibility",
    )


class Checkpoint(BaseModel):
    """Complete checkpoint bundle for save/load.

    Contains everything needed to fully restore simulation state:
    - Metadata for identification and context
    - WorldState with all entities and relationships
    - SimulationConfig with all formula coefficients

    Attributes:
        metadata: Checkpoint identification and context.
        state: The WorldState snapshot.
        config: The SimulationConfig active at checkpoint time.
    """

    model_config = ConfigDict(frozen=True)

    metadata: CheckpointMetadata = Field(
        ...,
        description="Checkpoint identification and context",
    )
    state: WorldState = Field(
        ...,
        description="The WorldState snapshot",
    )
    config: SimulationConfig = Field(
        ...,
        description="SimulationConfig at checkpoint time",
    )


class HistoryEntry(BaseModel):
    """Single entry in the history stack.

    Represents one state snapshot with its tick number.
    Used by the history stack for undo/redo operations.

    Attributes:
        tick: The simulation tick for this state.
        state: The WorldState snapshot.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(
        ...,
        description="Simulation tick for this state",
    )
    state: WorldState = Field(
        ...,
        description="The WorldState snapshot",
    )


class HistoryStack(BaseModel):
    """Immutable history stack for undo/redo operations.

    Maintains a list of history entries with a current position indicator.
    All operations return new HistoryStack instances (functional pattern).

    The stack supports:
    - Linear timeline (push after undo truncates future)
    - Protected ticks that survive pruning
    - Configurable maximum depth

    Attributes:
        entries: List of history entries (oldest first).
        current_index: Index of current state (-1 if empty).
        max_depth: Maximum number of entries to retain.
        protected_ticks: Tick numbers that cannot be pruned.
    """

    model_config = ConfigDict(frozen=True)

    entries: list[HistoryEntry] = Field(
        default_factory=list,
        description="History entries (oldest first)",
    )
    current_index: int = Field(
        default=-1,
        description="Index of current state (-1 if empty)",
    )
    max_depth: int = Field(
        default=100,
        gt=0,
        description="Maximum entries to retain",
    )
    protected_ticks: frozenset[int] = Field(
        default_factory=frozenset,
        description="Tick numbers that cannot be pruned",
    )


class CheckpointConfig(BaseModel):
    """Configuration for auto-checkpointing behavior.

    Controls when and where checkpoints are automatically created.

    Attributes:
        enabled: Whether auto-checkpointing is enabled.
        interval: Number of ticks between auto-checkpoints.
        checkpoint_dir: Directory path for checkpoint files.
        max_checkpoints: Maximum checkpoints to retain (0 = unlimited).
    """

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(
        default=True,
        description="Whether auto-checkpointing is enabled",
    )
    interval: int = Field(
        default=10,
        gt=0,
        description="Ticks between auto-checkpoints",
    )
    checkpoint_dir: str = Field(
        default="checkpoints",
        description="Directory for checkpoint files",
    )
    max_checkpoints: int = Field(
        default=10,
        ge=0,
        description="Maximum checkpoints to retain (0 = unlimited)",
    )
