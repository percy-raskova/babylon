"""Tests for babylon.engine.history.models.

TDD Red Phase: Define contracts for history-related Pydantic models.
All models must be frozen (immutable) for functional transformation.

Sprint A: History Stack models with ~20 tests.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from babylon.models import SimulationConfig, WorldState

# =============================================================================
# CHECKPOINT METADATA TESTS
# =============================================================================


@pytest.mark.topology
class TestCheckpointMetadataCreation:
    """CheckpointMetadata should capture checkpoint context."""

    def test_can_create_with_required_fields(self, sample_datetime: datetime) -> None:
        """Can create metadata with datetime and tick."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=5)
        assert metadata.created_at == sample_datetime
        assert metadata.tick == 5

    def test_description_defaults_to_empty_string(self, sample_datetime: datetime) -> None:
        """Description should default to empty string."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        assert metadata.description == ""

    def test_version_defaults_to_1_0_0(self, sample_datetime: datetime) -> None:
        """Version should default to 1.0.0."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        assert metadata.version == "1.0.0"

    def test_tick_must_be_non_negative(self, sample_datetime: datetime) -> None:
        """Tick must be >= 0."""
        from babylon.engine.history.models import CheckpointMetadata

        with pytest.raises(ValidationError):
            CheckpointMetadata(created_at=sample_datetime, tick=-1)

    def test_can_set_custom_description(self, sample_datetime: datetime) -> None:
        """Can set custom description."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(
            created_at=sample_datetime,
            tick=10,
            description="Manual save before battle",
        )
        assert metadata.description == "Manual save before battle"

    def test_can_set_custom_version(self, sample_datetime: datetime) -> None:
        """Can set custom version."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(
            created_at=sample_datetime,
            tick=10,
            version="2.0.0",
        )
        assert metadata.version == "2.0.0"


@pytest.mark.topology
class TestCheckpointMetadataImmutability:
    """CheckpointMetadata should be immutable (frozen)."""

    def test_created_at_is_frozen(self, sample_datetime: datetime) -> None:
        """Cannot modify created_at after creation."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        with pytest.raises(ValidationError):
            metadata.created_at = datetime.now(UTC)  # type: ignore[misc]

    def test_tick_is_frozen(self, sample_datetime: datetime) -> None:
        """Cannot modify tick after creation."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        with pytest.raises(ValidationError):
            metadata.tick = 10  # type: ignore[misc]


# =============================================================================
# CHECKPOINT TESTS
# =============================================================================


@pytest.mark.topology
class TestCheckpointCreation:
    """Checkpoint should bundle state, config, and metadata."""

    def test_can_create_checkpoint(
        self,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
        sample_datetime: datetime,
    ) -> None:
        """Can create a checkpoint with all required fields."""
        from babylon.engine.history.models import Checkpoint, CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        checkpoint = Checkpoint(
            metadata=metadata,
            state=sample_world_state,
            config=sample_config,
        )
        assert checkpoint.metadata.tick == 0
        assert checkpoint.state.tick == 0
        assert checkpoint.config.extraction_efficiency == 0.8

    def test_checkpoint_requires_metadata(
        self,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
    ) -> None:
        """Checkpoint requires metadata."""
        from babylon.engine.history.models import Checkpoint

        with pytest.raises(ValidationError):
            Checkpoint(state=sample_world_state, config=sample_config)  # type: ignore[call-arg]

    def test_checkpoint_requires_state(
        self,
        sample_config: SimulationConfig,
        sample_datetime: datetime,
    ) -> None:
        """Checkpoint requires state."""
        from babylon.engine.history.models import Checkpoint, CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        with pytest.raises(ValidationError):
            Checkpoint(metadata=metadata, config=sample_config)  # type: ignore[call-arg]

    def test_checkpoint_requires_config(
        self,
        sample_world_state: WorldState,
        sample_datetime: datetime,
    ) -> None:
        """Checkpoint requires config."""
        from babylon.engine.history.models import Checkpoint, CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        with pytest.raises(ValidationError):
            Checkpoint(metadata=metadata, state=sample_world_state)  # type: ignore[call-arg]


@pytest.mark.topology
class TestCheckpointImmutability:
    """Checkpoint should be immutable (frozen)."""

    def test_metadata_is_frozen(
        self,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
        sample_datetime: datetime,
    ) -> None:
        """Cannot replace metadata after creation."""
        from babylon.engine.history.models import Checkpoint, CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        checkpoint = Checkpoint(
            metadata=metadata,
            state=sample_world_state,
            config=sample_config,
        )
        new_metadata = CheckpointMetadata(created_at=sample_datetime, tick=10)
        with pytest.raises(ValidationError):
            checkpoint.metadata = new_metadata  # type: ignore[misc]


# =============================================================================
# HISTORY ENTRY TESTS
# =============================================================================


@pytest.mark.topology
class TestHistoryEntryCreation:
    """HistoryEntry should capture a single state snapshot."""

    def test_can_create_entry(self, sample_world_state: WorldState) -> None:
        """Can create a history entry with tick and state."""
        from babylon.engine.history.models import HistoryEntry

        entry = HistoryEntry(tick=0, state=sample_world_state)
        assert entry.tick == 0
        assert entry.state.tick == 0

    def test_entry_requires_tick(self, sample_world_state: WorldState) -> None:
        """HistoryEntry requires tick."""
        from babylon.engine.history.models import HistoryEntry

        with pytest.raises(ValidationError):
            HistoryEntry(state=sample_world_state)  # type: ignore[call-arg]

    def test_entry_requires_state(self) -> None:
        """HistoryEntry requires state."""
        from babylon.engine.history.models import HistoryEntry

        with pytest.raises(ValidationError):
            HistoryEntry(tick=0)  # type: ignore[call-arg]


@pytest.mark.topology
class TestHistoryEntryImmutability:
    """HistoryEntry should be immutable (frozen)."""

    def test_tick_is_frozen(self, sample_world_state: WorldState) -> None:
        """Cannot modify tick after creation."""
        from babylon.engine.history.models import HistoryEntry

        entry = HistoryEntry(tick=0, state=sample_world_state)
        with pytest.raises(ValidationError):
            entry.tick = 5  # type: ignore[misc]

    def test_state_is_frozen(self, sample_world_state: WorldState) -> None:
        """Cannot replace state after creation."""
        from babylon.engine.history.models import HistoryEntry

        entry = HistoryEntry(tick=0, state=sample_world_state)
        new_state = WorldState(tick=1)
        with pytest.raises(ValidationError):
            entry.state = new_state  # type: ignore[misc]


# =============================================================================
# HISTORY STACK TESTS
# =============================================================================


@pytest.mark.topology
class TestHistoryStackCreation:
    """HistoryStack should manage a list of history entries."""

    def test_can_create_empty_stack(self) -> None:
        """Can create empty history stack."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        assert len(stack.entries) == 0
        assert stack.current_index == -1

    def test_entries_default_to_empty_list(self) -> None:
        """Entries should default to empty list."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        assert stack.entries == []

    def test_current_index_defaults_to_minus_one(self) -> None:
        """Current index should default to -1 for empty stack."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        assert stack.current_index == -1

    def test_max_depth_defaults_to_100(self) -> None:
        """Max depth should default to 100."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        assert stack.max_depth == 100

    def test_max_depth_must_be_positive(self) -> None:
        """Max depth must be > 0."""
        from babylon.engine.history.models import HistoryStack

        with pytest.raises(ValidationError):
            HistoryStack(max_depth=0)

    def test_can_set_custom_max_depth(self) -> None:
        """Can set custom max depth."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack(max_depth=50)
        assert stack.max_depth == 50

    def test_protected_ticks_defaults_to_empty_frozenset(self) -> None:
        """Protected ticks should default to empty frozenset."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        assert stack.protected_ticks == frozenset()

    def test_can_set_protected_ticks(self) -> None:
        """Can set protected ticks as frozenset."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack(protected_ticks=frozenset({0, 10, 20}))
        assert 0 in stack.protected_ticks
        assert 10 in stack.protected_ticks
        assert 20 in stack.protected_ticks

    def test_can_create_with_entries(self, sample_world_state: WorldState) -> None:
        """Can create stack with entries."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack

        entry = HistoryEntry(tick=0, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)
        assert len(stack.entries) == 1
        assert stack.current_index == 0


@pytest.mark.topology
class TestHistoryStackImmutability:
    """HistoryStack should be immutable (frozen)."""

    def test_entries_is_frozen(self, sample_world_state: WorldState) -> None:
        """Cannot replace entries list after creation."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack

        entry = HistoryEntry(tick=0, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)
        with pytest.raises(ValidationError):
            stack.entries = []  # type: ignore[misc]

    def test_current_index_is_frozen(self) -> None:
        """Cannot modify current_index after creation."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        with pytest.raises(ValidationError):
            stack.current_index = 5  # type: ignore[misc]

    def test_max_depth_is_frozen(self) -> None:
        """Cannot modify max_depth after creation."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        with pytest.raises(ValidationError):
            stack.max_depth = 200  # type: ignore[misc]

    def test_protected_ticks_is_frozen(self) -> None:
        """Cannot replace protected_ticks after creation."""
        from babylon.engine.history.models import HistoryStack

        stack = HistoryStack()
        with pytest.raises(ValidationError):
            stack.protected_ticks = frozenset({1, 2, 3})  # type: ignore[misc]


# =============================================================================
# CHECKPOINT CONFIG TESTS
# =============================================================================


@pytest.mark.topology
class TestCheckpointConfigCreation:
    """CheckpointConfig should hold auto-checkpoint settings."""

    def test_can_create_with_defaults(self) -> None:
        """Can create config with all defaults."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        assert config.enabled is True
        assert config.interval == 10
        assert config.checkpoint_dir == "checkpoints"
        assert config.max_checkpoints == 10

    def test_enabled_defaults_to_true(self) -> None:
        """Enabled should default to True."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        assert config.enabled is True

    def test_interval_defaults_to_10(self) -> None:
        """Interval should default to 10."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        assert config.interval == 10

    def test_interval_must_be_positive(self) -> None:
        """Interval must be > 0."""
        from babylon.engine.history.models import CheckpointConfig

        with pytest.raises(ValidationError):
            CheckpointConfig(interval=0)

    def test_checkpoint_dir_defaults_to_checkpoints(self) -> None:
        """Checkpoint dir should default to 'checkpoints'."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        assert config.checkpoint_dir == "checkpoints"

    def test_max_checkpoints_defaults_to_10(self) -> None:
        """Max checkpoints should default to 10."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        assert config.max_checkpoints == 10

    def test_max_checkpoints_can_be_zero_for_unlimited(self) -> None:
        """Max checkpoints can be 0 for unlimited."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(max_checkpoints=0)
        assert config.max_checkpoints == 0

    def test_max_checkpoints_cannot_be_negative(self) -> None:
        """Max checkpoints cannot be negative."""
        from babylon.engine.history.models import CheckpointConfig

        with pytest.raises(ValidationError):
            CheckpointConfig(max_checkpoints=-1)

    def test_can_set_custom_values(self) -> None:
        """Can set custom values for all fields."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(
            enabled=False,
            interval=5,
            checkpoint_dir="/custom/path",
            max_checkpoints=20,
        )
        assert config.enabled is False
        assert config.interval == 5
        assert config.checkpoint_dir == "/custom/path"
        assert config.max_checkpoints == 20


@pytest.mark.topology
class TestCheckpointConfigImmutability:
    """CheckpointConfig should be immutable (frozen)."""

    def test_enabled_is_frozen(self) -> None:
        """Cannot modify enabled after creation."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        with pytest.raises(ValidationError):
            config.enabled = False  # type: ignore[misc]

    def test_interval_is_frozen(self) -> None:
        """Cannot modify interval after creation."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        with pytest.raises(ValidationError):
            config.interval = 20  # type: ignore[misc]

    def test_checkpoint_dir_is_frozen(self) -> None:
        """Cannot modify checkpoint_dir after creation."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig()
        with pytest.raises(ValidationError):
            config.checkpoint_dir = "/new/path"  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.topology
class TestModelSerialization:
    """Models should serialize correctly for persistence."""

    def test_checkpoint_metadata_json_roundtrip(self, sample_datetime: datetime) -> None:
        """CheckpointMetadata survives JSON round-trip."""
        from babylon.engine.history.models import CheckpointMetadata

        metadata = CheckpointMetadata(
            created_at=sample_datetime,
            tick=5,
            description="Test save",
            version="1.0.0",
        )
        json_str = metadata.model_dump_json()
        restored = CheckpointMetadata.model_validate_json(json_str)
        assert restored.tick == metadata.tick
        assert restored.description == metadata.description

    def test_history_entry_json_roundtrip(self, sample_world_state: WorldState) -> None:
        """HistoryEntry survives JSON round-trip."""
        from babylon.engine.history.models import HistoryEntry

        entry = HistoryEntry(tick=0, state=sample_world_state)
        json_str = entry.model_dump_json()
        restored = HistoryEntry.model_validate_json(json_str)
        assert restored.tick == entry.tick
        assert len(restored.state.entities) == len(entry.state.entities)

    def test_history_stack_json_roundtrip(self, sample_world_state: WorldState) -> None:
        """HistoryStack survives JSON round-trip."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack

        entry = HistoryEntry(tick=0, state=sample_world_state)
        stack = HistoryStack(
            entries=[entry],
            current_index=0,
            max_depth=50,
            protected_ticks=frozenset({0}),
        )
        json_str = stack.model_dump_json()
        restored = HistoryStack.model_validate_json(json_str)
        assert len(restored.entries) == 1
        assert restored.current_index == 0
        assert restored.max_depth == 50
        assert 0 in restored.protected_ticks

    def test_checkpoint_json_roundtrip(
        self,
        sample_world_state: WorldState,
        sample_config: SimulationConfig,
        sample_datetime: datetime,
    ) -> None:
        """Checkpoint survives JSON round-trip."""
        from babylon.engine.history.models import Checkpoint, CheckpointMetadata

        metadata = CheckpointMetadata(created_at=sample_datetime, tick=0)
        checkpoint = Checkpoint(
            metadata=metadata,
            state=sample_world_state,
            config=sample_config,
        )
        json_str = checkpoint.model_dump_json()
        restored = Checkpoint.model_validate_json(json_str)
        assert restored.metadata.tick == checkpoint.metadata.tick
        assert len(restored.state.entities) == len(checkpoint.state.entities)

    def test_checkpoint_config_json_roundtrip(self) -> None:
        """CheckpointConfig survives JSON round-trip."""
        from babylon.engine.history.models import CheckpointConfig

        config = CheckpointConfig(
            enabled=False,
            interval=5,
            checkpoint_dir="/custom",
            max_checkpoints=20,
        )
        json_str = config.model_dump_json()
        restored = CheckpointConfig.model_validate_json(json_str)
        assert restored.enabled == config.enabled
        assert restored.interval == config.interval
        assert restored.checkpoint_dir == config.checkpoint_dir
        assert restored.max_checkpoints == config.max_checkpoints
