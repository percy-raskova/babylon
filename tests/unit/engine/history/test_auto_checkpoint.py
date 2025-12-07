"""Tests for babylon.engine.history.auto_checkpoint.

TDD Red Phase: Define contracts for auto-checkpointing.
AutoCheckpointer is a stateful class that manages periodic checkpoint creation.

Sprint D: Auto-checkpointing with ~15 tests.
"""

from pathlib import Path

import pytest

from babylon.models import SimulationConfig, WorldState

# =============================================================================
# AUTO CHECKPOINTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestAutoCheckpointerCreation:
    """AutoCheckpointer should be configurable."""

    def test_can_create_with_config(self, tmp_path: Path) -> None:
        """Can create AutoCheckpointer with CheckpointConfig."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(interval=5)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        assert checkpointer is not None

    def test_uses_config_directory(self, tmp_path: Path) -> None:
        """AutoCheckpointer uses checkpoint_dir from config."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(checkpoint_dir="my_saves")
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Directory should be base_dir / checkpoint_dir
        expected = tmp_path / "my_saves"
        assert checkpointer.checkpoint_dir == expected


@pytest.mark.ledger
class TestAutoCheckpointerOnStep:
    """on_step should create checkpoints at configured intervals."""

    def test_on_step_creates_checkpoint_at_interval(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """on_step creates checkpoint when tick hits interval."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(interval=5)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Tick 5 should trigger checkpoint (0, 5, 10, ...)
        state = sample_world_state.model_copy(update={"tick": 5})
        result = checkpointer.on_step(state, sample_config)

        assert result is not None
        assert result.exists()

    def test_on_step_returns_none_between_intervals(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """on_step returns None when not at interval."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(interval=10)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Tick 3 should not trigger checkpoint
        state = sample_world_state.model_copy(update={"tick": 3})
        result = checkpointer.on_step(state, sample_config)

        assert result is None

    def test_on_step_respects_enabled_flag(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """on_step does nothing when enabled=False."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(enabled=False, interval=1)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Even at interval tick, should not create checkpoint
        state = sample_world_state.model_copy(update={"tick": 5})
        result = checkpointer.on_step(state, sample_config)

        assert result is None

    def test_on_step_at_tick_zero(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """on_step creates checkpoint at tick 0."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(interval=10)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Tick 0 should trigger initial checkpoint
        state = sample_world_state.model_copy(update={"tick": 0})
        result = checkpointer.on_step(state, sample_config)

        assert result is not None


@pytest.mark.ledger
class TestAutoCheckpointerForceCheckpoint:
    """force_checkpoint should always create a checkpoint."""

    def test_force_checkpoint_creates_file(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """force_checkpoint creates a file."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        result = checkpointer.force_checkpoint(sample_world_state, sample_config)

        assert result.exists()

    def test_force_checkpoint_with_description(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """force_checkpoint includes description in metadata."""
        import json

        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        result = checkpointer.force_checkpoint(
            sample_world_state,
            sample_config,
            description="Manual quicksave",
        )

        content = json.loads(result.read_text())
        assert content["metadata"]["description"] == "Manual quicksave"

    def test_force_checkpoint_ignores_enabled_flag(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """force_checkpoint works even when enabled=False."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(enabled=False)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        result = checkpointer.force_checkpoint(sample_world_state, sample_config)

        assert result.exists()


@pytest.mark.ledger
class TestAutoCheckpointerRotation:
    """rotate_checkpoints should remove old checkpoints."""

    def test_rotate_removes_oldest_checkpoints(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """rotate_checkpoints removes oldest when over max."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(max_checkpoints=2)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Create 3 checkpoints
        checkpointer.force_checkpoint(sample_world_state, sample_config)
        checkpointer.force_checkpoint(
            sample_world_state.model_copy(update={"tick": 1}),
            sample_config,
        )
        checkpointer.force_checkpoint(
            sample_world_state.model_copy(update={"tick": 2}),
            sample_config,
        )

        # Rotate should remove 1 checkpoint
        removed = checkpointer.rotate_checkpoints()

        assert len(removed) == 1
        remaining = list(checkpointer.checkpoint_dir.glob("*.json"))
        assert len(remaining) == 2

    def test_rotate_noop_when_under_max(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """rotate_checkpoints does nothing when under max."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(max_checkpoints=10)
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Create 2 checkpoints
        checkpointer.force_checkpoint(sample_world_state, sample_config)
        checkpointer.force_checkpoint(
            sample_world_state.model_copy(update={"tick": 1}),
            sample_config,
        )

        removed = checkpointer.rotate_checkpoints()

        assert len(removed) == 0

    def test_rotate_respects_unlimited(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """rotate_checkpoints does nothing when max=0 (unlimited)."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(max_checkpoints=0)  # 0 = unlimited
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Create many checkpoints
        for i in range(5):
            checkpointer.force_checkpoint(
                sample_world_state.model_copy(update={"tick": i}),
                sample_config,
            )

        removed = checkpointer.rotate_checkpoints()

        assert len(removed) == 0


@pytest.mark.ledger
class TestAutoCheckpointerGetLatest:
    """get_latest_checkpoint should return the most recent checkpoint."""

    def test_get_latest_returns_newest(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """get_latest_checkpoint returns the most recent checkpoint."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        # Create checkpoints
        checkpointer.force_checkpoint(sample_world_state, sample_config)
        latest_path = checkpointer.force_checkpoint(
            sample_world_state.model_copy(update={"tick": 10}),
            sample_config,
        )

        result = checkpointer.get_latest_checkpoint()

        assert result == latest_path

    def test_get_latest_returns_none_when_empty(self, tmp_path: Path) -> None:
        """get_latest_checkpoint returns None when no checkpoints exist."""
        from babylon.engine.history.auto_checkpoint import AutoCheckpointer
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        checkpointer = AutoCheckpointer(config, base_dir=tmp_path)

        result = checkpointer.get_latest_checkpoint()

        assert result is None


# =============================================================================
# CHECKPOINTED STEP WRAPPER TESTS
# =============================================================================


@pytest.mark.ledger
class TestCreateCheckpointedStep:
    """create_checkpointed_step should wrap step function with checkpointing."""

    def test_wrapper_returns_callable(
        self, tmp_path: Path, sample_config: SimulationConfig
    ) -> None:
        """create_checkpointed_step returns a callable."""
        from babylon.engine.history.auto_checkpoint import (
            AutoCheckpointer,
            create_checkpointed_step,
        )
        from babylon.engine.history.models import CheckpointConfig

        checkpoint_config = CheckpointConfig()
        checkpointer = AutoCheckpointer(checkpoint_config, base_dir=tmp_path)

        wrapped = create_checkpointed_step(sample_config, checkpointer)

        assert callable(wrapped)

    def test_wrapper_returns_state_and_path(
        self,
        tmp_path: Path,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """Wrapper returns tuple of (WorldState, Path | None)."""
        from babylon.engine.history.auto_checkpoint import (
            AutoCheckpointer,
            create_checkpointed_step,
        )
        from babylon.engine.history.models import CheckpointConfig

        checkpoint_config = CheckpointConfig(interval=1)
        checkpointer = AutoCheckpointer(checkpoint_config, base_dir=tmp_path)

        wrapped = create_checkpointed_step(sample_config, checkpointer)
        state, path = wrapped(sample_world_state)

        assert isinstance(state, WorldState)
        # At tick 0, should create checkpoint
        assert path is not None or sample_world_state.tick % 1 != 0
