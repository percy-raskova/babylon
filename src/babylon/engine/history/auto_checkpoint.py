"""Auto-checkpointing for the History Stack system.

This module provides:
- AutoCheckpointer: A stateful class managing periodic checkpoint creation
- create_checkpointed_step: A wrapper for integrating checkpoints with game loop

The checkpointing system follows the Observer pattern:
- The game loop (step function) remains pure
- The AutoCheckpointer observes state changes and creates checkpoints as side effects

Sprint D: Auto-checkpointing for Phase 3 persistence layer.
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from babylon.engine.history.io import save_checkpoint
from babylon.engine.history.models import CheckpointConfig
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState


class AutoCheckpointer:
    """Stateful checkpoint manager for automatic periodic saves.

    AutoCheckpointer integrates with the game loop to create checkpoints
    at configurable intervals without modifying the pure step function.

    Attributes:
        config: The CheckpointConfig controlling behavior.
        checkpoint_dir: The directory where checkpoints are saved.
    """

    def __init__(
        self,
        config: CheckpointConfig,
        base_dir: Path | None = None,
    ) -> None:
        """Initialize the auto-checkpointer.

        Args:
            config: Configuration for checkpointing behavior.
            base_dir: Base directory for checkpoint storage. Defaults to current dir.
        """
        self._config = config
        self._base_dir = base_dir or Path(".")
        self._checkpoint_dir = self._base_dir / config.checkpoint_dir

    @property
    def checkpoint_dir(self) -> Path:
        """Get the checkpoint directory path."""
        return self._checkpoint_dir

    def on_step(
        self,
        state: WorldState,
        sim_config: SimulationConfig,
    ) -> Path | None:
        """Check if a checkpoint should be created after a step.

        Called after each simulation step. Creates a checkpoint if:
        - Auto-checkpointing is enabled
        - The current tick is a multiple of the interval (including 0)

        Args:
            state: The current WorldState after the step.
            sim_config: The SimulationConfig in use.

        Returns:
            Path to the created checkpoint, or None if no checkpoint was created.
        """
        if not self._config.enabled:
            return None

        # Check if we're at an interval tick
        if state.tick % self._config.interval == 0:
            path = self._create_checkpoint(state, sim_config)

            # Rotate old checkpoints
            self.rotate_checkpoints()

            return path

        return None

    def force_checkpoint(
        self,
        state: WorldState,
        sim_config: SimulationConfig,
        description: str = "",
    ) -> Path:
        """Force creation of a checkpoint regardless of interval.

        Useful for manual saves or important milestones.

        Args:
            state: The WorldState to checkpoint.
            sim_config: The SimulationConfig to include.
            description: Optional description for the checkpoint.

        Returns:
            Path to the created checkpoint.
        """
        return self._create_checkpoint(state, sim_config, description)

    def rotate_checkpoints(self) -> list[Path]:
        """Remove old checkpoints to stay within max_checkpoints limit.

        Removes the oldest checkpoints when the count exceeds max_checkpoints.
        If max_checkpoints is 0 (unlimited), no rotation occurs.

        Returns:
            List of paths that were removed.
        """
        # 0 means unlimited
        if self._config.max_checkpoints == 0:
            return []

        if not self._checkpoint_dir.exists():
            return []

        # Get all checkpoint files sorted by modification time (oldest first)
        checkpoints = sorted(
            self._checkpoint_dir.glob("checkpoint_*.json"),
            key=lambda p: p.stat().st_mtime,
        )

        # Remove oldest until we're at max
        removed: list[Path] = []
        while len(checkpoints) > self._config.max_checkpoints:
            oldest = checkpoints.pop(0)
            oldest.unlink()
            removed.append(oldest)

        return removed

    def get_latest_checkpoint(self) -> Path | None:
        """Get the path to the most recent checkpoint.

        Returns:
            Path to the newest checkpoint, or None if no checkpoints exist.
        """
        if not self._checkpoint_dir.exists():
            return None

        checkpoints = list(self._checkpoint_dir.glob("checkpoint_*.json"))
        if not checkpoints:
            return None

        # Return the one with the most recent modification time
        return max(checkpoints, key=lambda p: p.stat().st_mtime)

    def _create_checkpoint(
        self,
        state: WorldState,
        sim_config: SimulationConfig,
        description: str = "",
    ) -> Path:
        """Internal method to create a checkpoint file.

        Args:
            state: The WorldState to checkpoint.
            sim_config: The SimulationConfig to include.
            description: Optional description for the checkpoint.

        Returns:
            Path to the created checkpoint.
        """
        # Generate filename with timestamp and tick
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_{timestamp}_tick{state.tick}.json"
        path = self._checkpoint_dir / filename

        return save_checkpoint(state, sim_config, path, description)


def create_checkpointed_step(
    sim_config: SimulationConfig,
    checkpointer: AutoCheckpointer,
) -> Callable[[WorldState], tuple[WorldState, Path | None]]:
    """Create a wrapper function that checkpoints after each step.

    This enables integration of checkpointing with the pure game loop
    without modifying the step function itself.

    Usage:
        checkpointer = AutoCheckpointer(checkpoint_config)
        checkpointed_step = create_checkpointed_step(sim_config, checkpointer)

        for _ in range(100):
            state, checkpoint_path = checkpointed_step(state)
            # checkpoint_path is None unless a checkpoint was created

    Args:
        sim_config: The SimulationConfig for checkpoints.
        checkpointer: The AutoCheckpointer instance.

    Returns:
        A callable that takes WorldState and returns (WorldState, Path | None).
    """

    def wrapper(state: WorldState) -> tuple[WorldState, Path | None]:
        """Wrapper that returns state and optional checkpoint path.

        Note: This wrapper does NOT call step() - it just observes the state
        and creates checkpoints. The caller is responsible for calling step().

        Args:
            state: The current WorldState (after step has been called).

        Returns:
            Tuple of (state unchanged, checkpoint path or None).
        """
        checkpoint_path = checkpointer.on_step(state, sim_config)
        return state, checkpoint_path

    return wrapper
