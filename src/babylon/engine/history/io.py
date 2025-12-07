"""File I/O operations for the History Stack system.

This module provides save/load functionality for:
- WorldState snapshots (simple state persistence)
- Full Checkpoint bundles (state + config + metadata)

All writes use atomic patterns (temp file + rename) to prevent corruption.

Sprint C: File I/O for Phase 3 persistence layer.
"""

import contextlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from babylon.engine.history.models import Checkpoint, CheckpointMetadata
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState

# =============================================================================
# EXCEPTIONS
# =============================================================================


class CheckpointIOError(Exception):
    """Base exception for checkpoint I/O errors."""

    pass


class CheckpointNotFoundError(CheckpointIOError):
    """Raised when a checkpoint file is not found."""

    pass


class CheckpointCorruptedError(CheckpointIOError):
    """Raised when a checkpoint file contains invalid JSON."""

    pass


class CheckpointSchemaError(CheckpointIOError):
    """Raised when a checkpoint file has invalid schema."""

    pass


# =============================================================================
# STATE I/O (WorldState only)
# =============================================================================


def save_state(state: WorldState, path: Path) -> Path:
    """Save a WorldState to a JSON file.

    Uses atomic write pattern (temp file + rename) for safety.
    Creates parent directories if they don't exist.

    Args:
        state: The WorldState to save.
        path: The file path to save to.

    Returns:
        The path where the file was saved.
    """
    # Ensure parent directories exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize state to JSON
    json_content = state.model_dump_json(indent=2)

    # Atomic write: write to temp file, then rename
    _atomic_write(path, json_content)

    return path


def load_state(path: Path) -> WorldState:
    """Load a WorldState from a JSON file.

    Args:
        path: The file path to load from.

    Returns:
        The loaded WorldState.

    Raises:
        CheckpointNotFoundError: If the file doesn't exist.
        CheckpointCorruptedError: If the file contains invalid JSON.
        CheckpointSchemaError: If the JSON doesn't match WorldState schema.
    """
    if not path.exists():
        raise CheckpointNotFoundError(f"File not found: {path}")

    try:
        content = path.read_text()
    except OSError as e:
        raise CheckpointCorruptedError(f"Failed to read file: {e}") from e

    try:
        json.loads(content)  # Validate JSON first
    except json.JSONDecodeError as e:
        raise CheckpointCorruptedError(f"Invalid JSON: {e}") from e

    try:
        return WorldState.model_validate_json(content)
    except ValidationError as e:
        raise CheckpointSchemaError(f"Schema validation failed: {e}") from e


# =============================================================================
# CHECKPOINT I/O (Full bundle)
# =============================================================================


def save_checkpoint(
    state: WorldState,
    config: SimulationConfig,
    path: Path,
    description: str = "",
) -> Path:
    """Save a full Checkpoint to a JSON file.

    Creates a Checkpoint with current metadata and saves it atomically.
    Creates parent directories if they don't exist.

    Args:
        state: The WorldState to save.
        config: The SimulationConfig to save.
        path: The file path to save to.
        description: Optional description for the checkpoint.

    Returns:
        The path where the file was saved.
    """
    # Ensure parent directories exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create metadata with current timestamp
    metadata = CheckpointMetadata(
        created_at=datetime.now(UTC),
        tick=state.tick,
        description=description,
    )

    # Create checkpoint bundle
    checkpoint = Checkpoint(
        metadata=metadata,
        state=state,
        config=config,
    )

    # Serialize to JSON
    json_content = checkpoint.model_dump_json(indent=2)

    # Atomic write
    _atomic_write(path, json_content)

    return path


def load_checkpoint(path: Path) -> Checkpoint:
    """Load a full Checkpoint from a JSON file.

    Args:
        path: The file path to load from.

    Returns:
        The loaded Checkpoint.

    Raises:
        CheckpointNotFoundError: If the file doesn't exist.
        CheckpointCorruptedError: If the file contains invalid JSON.
        CheckpointSchemaError: If the JSON doesn't match Checkpoint schema.
    """
    if not path.exists():
        raise CheckpointNotFoundError(f"File not found: {path}")

    try:
        content = path.read_text()
    except OSError as e:
        raise CheckpointCorruptedError(f"Failed to read file: {e}") from e

    try:
        json.loads(content)  # Validate JSON first
    except json.JSONDecodeError as e:
        raise CheckpointCorruptedError(f"Invalid JSON: {e}") from e

    try:
        return Checkpoint.model_validate_json(content)
    except ValidationError as e:
        raise CheckpointSchemaError(f"Schema validation failed: {e}") from e


# =============================================================================
# CHECKPOINT LISTING AND VALIDATION
# =============================================================================


def list_checkpoints(directory: Path) -> list[tuple[Path, CheckpointMetadata]]:
    """List all valid checkpoints in a directory.

    Scans the directory for JSON files that are valid checkpoints.
    Returns a list of (path, metadata) tuples for valid checkpoints.

    Args:
        directory: The directory to scan.

    Returns:
        List of (Path, CheckpointMetadata) tuples for valid checkpoints.
    """
    if not directory.exists():
        return []

    result: list[tuple[Path, CheckpointMetadata]] = []

    for path in directory.glob("*.json"):
        if validate_checkpoint_file(path):
            try:
                checkpoint = load_checkpoint(path)
                result.append((path, checkpoint.metadata))
            except CheckpointIOError:
                # Skip files that fail to load (should not happen if validate passed)
                continue

    return result


def validate_checkpoint_file(path: Path) -> bool:
    """Check if a file is a valid checkpoint.

    Performs a quick validation without loading the full checkpoint.

    Args:
        path: The file path to validate.

    Returns:
        True if the file is a valid checkpoint, False otherwise.
    """
    if not path.exists():
        return False

    try:
        content = path.read_text()
    except OSError:
        return False

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return False

    # Check for required checkpoint structure
    if not isinstance(data, dict):
        return False

    # Must have metadata, state, and config keys
    required_keys = {"metadata", "state", "config"}
    if not required_keys.issubset(data.keys()):
        return False

    # Validate metadata has required fields
    metadata = data.get("metadata", {})
    metadata_keys = {"created_at", "tick"}
    return metadata_keys.issubset(metadata.keys())


# =============================================================================
# INTERNAL HELPERS
# =============================================================================


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically.

    Uses a temporary file in the same directory, then renames.
    This ensures the file is either fully written or not at all.

    Args:
        path: The target file path.
        content: The content to write.
    """
    # Create temp file in same directory for atomic rename
    dir_path = path.parent
    fd, temp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_path)

    try:
        # Write content
        with open(fd, "w") as f:
            f.write(content)

        # Atomic rename
        Path(temp_path).replace(path)
    except Exception:
        # Clean up temp file on error
        with contextlib.suppress(OSError):
            Path(temp_path).unlink()
        raise
