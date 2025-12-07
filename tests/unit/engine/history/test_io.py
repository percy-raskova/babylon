"""Tests for babylon.engine.history.io.

TDD Red Phase: Define contracts for file I/O operations.
All I/O uses atomic writes (temp file + rename) for safety.

Sprint C: File I/O with ~20 tests.
"""

from pathlib import Path

import pytest

from babylon.models import SimulationConfig, WorldState

# =============================================================================
# EXCEPTION TESTS
# =============================================================================


@pytest.mark.ledger
class TestIOExceptions:
    """Test custom exception hierarchy."""

    def test_checkpoint_io_error_exists(self) -> None:
        """CheckpointIOError exception exists."""
        from babylon.engine.history.io import CheckpointIOError

        error = CheckpointIOError("test")
        assert isinstance(error, Exception)

    def test_checkpoint_not_found_is_io_error(self) -> None:
        """CheckpointNotFoundError is a CheckpointIOError."""
        from babylon.engine.history.io import (
            CheckpointIOError,
            CheckpointNotFoundError,
        )

        error = CheckpointNotFoundError("test")
        assert isinstance(error, CheckpointIOError)

    def test_checkpoint_corrupted_is_io_error(self) -> None:
        """CheckpointCorruptedError is a CheckpointIOError."""
        from babylon.engine.history.io import (
            CheckpointCorruptedError,
            CheckpointIOError,
        )

        error = CheckpointCorruptedError("test")
        assert isinstance(error, CheckpointIOError)

    def test_checkpoint_schema_is_io_error(self) -> None:
        """CheckpointSchemaError is a CheckpointIOError."""
        from babylon.engine.history.io import (
            CheckpointIOError,
            CheckpointSchemaError,
        )

        error = CheckpointSchemaError("test")
        assert isinstance(error, CheckpointIOError)


# =============================================================================
# SAVE STATE TESTS
# =============================================================================


@pytest.mark.ledger
class TestSaveState:
    """save_state should persist WorldState to disk."""

    def test_save_state_creates_file(self, tmp_path: Path, sample_world_state: WorldState) -> None:
        """save_state creates the file."""
        from babylon.engine.history.io import save_state

        file_path = tmp_path / "state.json"
        result = save_state(sample_world_state, file_path)

        assert result.exists()
        assert result == file_path

    def test_save_state_creates_parent_directories(
        self, tmp_path: Path, sample_world_state: WorldState
    ) -> None:
        """save_state creates parent directories if needed."""
        from babylon.engine.history.io import save_state

        file_path = tmp_path / "deep" / "nested" / "state.json"
        result = save_state(sample_world_state, file_path)

        assert result.exists()

    def test_save_state_content_is_valid_json(
        self, tmp_path: Path, sample_world_state: WorldState
    ) -> None:
        """save_state writes valid JSON."""
        import json

        from babylon.engine.history.io import save_state

        file_path = tmp_path / "state.json"
        save_state(sample_world_state, file_path)

        content = file_path.read_text()
        data = json.loads(content)  # Should not raise
        assert "tick" in data

    def test_save_state_overwrites_existing(
        self, tmp_path: Path, sample_world_state: WorldState
    ) -> None:
        """save_state overwrites existing file."""
        from babylon.engine.history.io import save_state

        file_path = tmp_path / "state.json"
        file_path.write_text("old content")

        save_state(sample_world_state, file_path)

        content = file_path.read_text()
        assert "old content" not in content


# =============================================================================
# LOAD STATE TESTS
# =============================================================================


@pytest.mark.ledger
class TestLoadState:
    """load_state should restore WorldState from disk."""

    def test_load_state_returns_world_state(
        self, tmp_path: Path, sample_world_state: WorldState
    ) -> None:
        """load_state returns a WorldState."""
        from babylon.engine.history.io import load_state, save_state

        file_path = tmp_path / "state.json"
        save_state(sample_world_state, file_path)

        result = load_state(file_path)

        assert isinstance(result, WorldState)

    def test_load_state_preserves_data(
        self, tmp_path: Path, sample_world_state: WorldState
    ) -> None:
        """load_state preserves all state data."""
        from babylon.engine.history.io import load_state, save_state

        file_path = tmp_path / "state.json"
        save_state(sample_world_state, file_path)

        result = load_state(file_path)

        assert result.tick == sample_world_state.tick
        assert len(result.entities) == len(sample_world_state.entities)
        assert len(result.relationships) == len(sample_world_state.relationships)

    def test_load_state_file_not_found(self, tmp_path: Path) -> None:
        """load_state raises CheckpointNotFoundError for missing file."""
        from babylon.engine.history.io import CheckpointNotFoundError, load_state

        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(CheckpointNotFoundError):
            load_state(file_path)

    def test_load_state_corrupted_json(self, tmp_path: Path) -> None:
        """load_state raises CheckpointCorruptedError for invalid JSON."""
        from babylon.engine.history.io import CheckpointCorruptedError, load_state

        file_path = tmp_path / "state.json"
        file_path.write_text("not valid json {{{")

        with pytest.raises(CheckpointCorruptedError):
            load_state(file_path)

    def test_load_state_schema_mismatch(self, tmp_path: Path) -> None:
        """load_state raises CheckpointSchemaError for invalid schema."""
        from babylon.engine.history.io import CheckpointSchemaError, load_state

        file_path = tmp_path / "state.json"
        # tick must be >= 0, so -1 triggers validation error
        file_path.write_text('{"tick": -1}')

        with pytest.raises(CheckpointSchemaError):
            load_state(file_path)


# =============================================================================
# SAVE CHECKPOINT TESTS
# =============================================================================


@pytest.mark.ledger
class TestSaveCheckpoint:
    """save_checkpoint should persist full Checkpoint to disk."""

    def test_save_checkpoint_creates_file(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """save_checkpoint creates the file."""
        from babylon.engine.history.io import save_checkpoint

        file_path = tmp_path / "checkpoint.json"
        result = save_checkpoint(sample_world_state, sample_config, file_path)

        assert result.exists()

    def test_save_checkpoint_with_description(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """save_checkpoint includes description in metadata."""
        import json

        from babylon.engine.history.io import save_checkpoint

        file_path = tmp_path / "checkpoint.json"
        save_checkpoint(
            sample_world_state,
            sample_config,
            file_path,
            description="Manual save",
        )

        content = json.loads(file_path.read_text())
        assert content["metadata"]["description"] == "Manual save"

    def test_save_checkpoint_creates_parent_directories(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """save_checkpoint creates parent directories if needed."""
        from babylon.engine.history.io import save_checkpoint

        file_path = tmp_path / "deep" / "nested" / "checkpoint.json"
        result = save_checkpoint(sample_world_state, sample_config, file_path)

        assert result.exists()


# =============================================================================
# LOAD CHECKPOINT TESTS
# =============================================================================


@pytest.mark.ledger
class TestLoadCheckpoint:
    """load_checkpoint should restore full Checkpoint from disk."""

    def test_load_checkpoint_returns_checkpoint(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """load_checkpoint returns a Checkpoint."""
        from babylon.engine.history.io import load_checkpoint, save_checkpoint
        from babylon.engine.history.models import Checkpoint

        file_path = tmp_path / "checkpoint.json"
        save_checkpoint(sample_world_state, sample_config, file_path)

        result = load_checkpoint(file_path)

        assert isinstance(result, Checkpoint)

    def test_load_checkpoint_preserves_data(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """load_checkpoint preserves all checkpoint data."""
        from babylon.engine.history.io import load_checkpoint, save_checkpoint

        file_path = tmp_path / "checkpoint.json"
        save_checkpoint(
            sample_world_state,
            sample_config,
            file_path,
            description="Test checkpoint",
        )

        result = load_checkpoint(file_path)

        assert result.metadata.tick == sample_world_state.tick
        assert result.metadata.description == "Test checkpoint"
        assert result.state.tick == sample_world_state.tick
        assert result.config.extraction_efficiency == sample_config.extraction_efficiency

    def test_load_checkpoint_file_not_found(self, tmp_path: Path) -> None:
        """load_checkpoint raises CheckpointNotFoundError for missing file."""
        from babylon.engine.history.io import CheckpointNotFoundError, load_checkpoint

        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(CheckpointNotFoundError):
            load_checkpoint(file_path)


# =============================================================================
# LIST CHECKPOINTS TESTS
# =============================================================================


@pytest.mark.ledger
class TestListCheckpoints:
    """list_checkpoints should list all checkpoints in a directory."""

    def test_list_checkpoints_returns_list(self, tmp_path: Path) -> None:
        """list_checkpoints returns a list."""
        from babylon.engine.history.io import list_checkpoints

        result = list_checkpoints(tmp_path)

        assert isinstance(result, list)

    def test_list_checkpoints_empty_directory(self, tmp_path: Path) -> None:
        """list_checkpoints returns empty list for empty directory."""
        from babylon.engine.history.io import list_checkpoints

        result = list_checkpoints(tmp_path)

        assert result == []

    def test_list_checkpoints_finds_checkpoints(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """list_checkpoints finds checkpoint files."""
        from babylon.engine.history.io import list_checkpoints, save_checkpoint

        # Create some checkpoints
        save_checkpoint(sample_world_state, sample_config, tmp_path / "cp1.json")
        save_checkpoint(sample_world_state, sample_config, tmp_path / "cp2.json")

        result = list_checkpoints(tmp_path)

        assert len(result) == 2

    def test_list_checkpoints_returns_tuples_with_metadata(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """list_checkpoints returns (Path, CheckpointMetadata) tuples."""
        from babylon.engine.history.io import list_checkpoints, save_checkpoint
        from babylon.engine.history.models import CheckpointMetadata

        save_checkpoint(
            sample_world_state,
            sample_config,
            tmp_path / "cp1.json",
            description="First checkpoint",
        )

        result = list_checkpoints(tmp_path)

        assert len(result) == 1
        path, metadata = result[0]
        assert isinstance(path, Path)
        assert isinstance(metadata, CheckpointMetadata)
        assert metadata.description == "First checkpoint"

    def test_list_checkpoints_ignores_non_checkpoint_files(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """list_checkpoints ignores non-checkpoint JSON files."""
        from babylon.engine.history.io import list_checkpoints, save_checkpoint

        # Create a checkpoint
        save_checkpoint(sample_world_state, sample_config, tmp_path / "cp1.json")
        # Create a non-checkpoint file
        (tmp_path / "not_a_checkpoint.json").write_text('{"other": "data"}')

        result = list_checkpoints(tmp_path)

        # Should only find the valid checkpoint
        assert len(result) == 1


# =============================================================================
# VALIDATE CHECKPOINT TESTS
# =============================================================================


@pytest.mark.ledger
class TestValidateCheckpointFile:
    """validate_checkpoint_file should check if a file is a valid checkpoint."""

    def test_validate_valid_checkpoint(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """validate_checkpoint_file returns True for valid checkpoint."""
        from babylon.engine.history.io import (
            save_checkpoint,
            validate_checkpoint_file,
        )

        file_path = tmp_path / "checkpoint.json"
        save_checkpoint(sample_world_state, sample_config, file_path)

        result = validate_checkpoint_file(file_path)

        assert result is True

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        """validate_checkpoint_file returns False for missing file."""
        from babylon.engine.history.io import validate_checkpoint_file

        file_path = tmp_path / "nonexistent.json"

        result = validate_checkpoint_file(file_path)

        assert result is False

    def test_validate_invalid_json(self, tmp_path: Path) -> None:
        """validate_checkpoint_file returns False for invalid JSON."""
        from babylon.engine.history.io import validate_checkpoint_file

        file_path = tmp_path / "invalid.json"
        file_path.write_text("not json {{{")

        result = validate_checkpoint_file(file_path)

        assert result is False

    def test_validate_wrong_schema(self, tmp_path: Path) -> None:
        """validate_checkpoint_file returns False for wrong schema."""
        from babylon.engine.history.io import validate_checkpoint_file

        file_path = tmp_path / "wrong.json"
        file_path.write_text('{"tick": 0}')  # WorldState, not Checkpoint

        result = validate_checkpoint_file(file_path)

        assert result is False


# =============================================================================
# ATOMIC WRITE TESTS
# =============================================================================


@pytest.mark.ledger
class TestAtomicWrites:
    """File operations should use atomic writes."""

    def test_save_state_atomic(self, tmp_path: Path, sample_world_state: WorldState) -> None:
        """save_state uses atomic write pattern."""
        from babylon.engine.history.io import save_state

        file_path = tmp_path / "state.json"

        # Create original file
        file_path.write_text("original content")

        # Save should atomically replace
        save_state(sample_world_state, file_path)

        # No temp files should remain
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

        # Content should be valid
        content = file_path.read_text()
        assert "original content" not in content
