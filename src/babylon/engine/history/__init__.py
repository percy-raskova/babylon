"""History Stack module for the Babylon simulation engine.

This module provides:
- Pydantic models for history tracking and checkpointing
- Stack operations for undo/redo functionality
- File I/O for state persistence
- Auto-checkpointing for periodic saves

The historical record must survive state repression.
"""

from babylon.engine.history.auto_checkpoint import (
    AutoCheckpointer,
    create_checkpointed_step,
)
from babylon.engine.history.io import (
    CheckpointCorruptedError,
    CheckpointIOError,
    CheckpointNotFoundError,
    CheckpointSchemaError,
    list_checkpoints,
    load_checkpoint,
    load_state,
    save_checkpoint,
    save_state,
    validate_checkpoint_file,
)
from babylon.engine.history.models import (
    Checkpoint,
    CheckpointConfig,
    CheckpointMetadata,
    HistoryEntry,
    HistoryStack,
)
from babylon.engine.history.stack import (
    get_current_state,
    get_state_at_tick,
    protect_tick,
    prune_history,
    push_state,
    redo,
    undo,
)

__all__ = [
    # Models
    "CheckpointMetadata",
    "Checkpoint",
    "HistoryEntry",
    "HistoryStack",
    "CheckpointConfig",
    # Stack operations
    "push_state",
    "undo",
    "redo",
    "get_current_state",
    "get_state_at_tick",
    "prune_history",
    "protect_tick",
    # I/O exceptions
    "CheckpointIOError",
    "CheckpointNotFoundError",
    "CheckpointCorruptedError",
    "CheckpointSchemaError",
    # I/O functions
    "save_state",
    "load_state",
    "save_checkpoint",
    "load_checkpoint",
    "list_checkpoints",
    "validate_checkpoint_file",
    # Auto-checkpointing
    "AutoCheckpointer",
    "create_checkpointed_step",
]
