"""Tests for babylon.engine.history.stack.

TDD Red Phase: Define contracts for pure stack operations.
All functions are pure - they take a HistoryStack and return a new one.

Sprint B: Stack operations with ~20 tests.
"""

import pytest

from babylon.models import WorldState

# =============================================================================
# PUSH STATE TESTS
# =============================================================================


@pytest.mark.topology
class TestPushState:
    """push_state should add a new state to the history stack."""

    def test_push_to_empty_stack(self, sample_world_state: WorldState) -> None:
        """Can push state to empty stack."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import push_state

        stack = HistoryStack()
        new_stack = push_state(stack, sample_world_state)

        assert len(new_stack.entries) == 1
        assert new_stack.current_index == 0
        assert new_stack.entries[0].state.tick == sample_world_state.tick

    def test_push_increments_current_index(self, sample_world_state: WorldState) -> None:
        """Push increments current_index."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import push_state

        entry = HistoryEntry(tick=0, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)
        state_tick_1 = sample_world_state.model_copy(update={"tick": 1})

        new_stack = push_state(stack, state_tick_1)

        assert new_stack.current_index == 1
        assert len(new_stack.entries) == 2

    def test_push_preserves_existing_entries(self, sample_world_state: WorldState) -> None:
        """Push preserves existing entries."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import push_state

        entry = HistoryEntry(tick=0, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)
        state_tick_1 = sample_world_state.model_copy(update={"tick": 1})

        new_stack = push_state(stack, state_tick_1)

        assert new_stack.entries[0].tick == 0
        assert new_stack.entries[1].tick == 1

    def test_push_after_undo_truncates_future(self, sample_world_state: WorldState) -> None:
        """Push after undo truncates future entries (linear timeline)."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import push_state

        # Create stack with 3 entries, current at index 1 (after undo)
        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=1)

        # Push new state - should truncate entry at index 2
        new_state = sample_world_state.model_copy(update={"tick": 10})
        new_stack = push_state(stack, new_state)

        assert len(new_stack.entries) == 3  # 0, 1, new
        assert new_stack.entries[2].tick == 10
        assert new_stack.current_index == 2

    def test_push_enforces_max_depth(self, sample_world_state: WorldState) -> None:
        """Push enforces max_depth by pruning oldest entries."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import push_state

        # Create stack at max capacity
        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=2, max_depth=3)

        # Push should prune oldest
        new_state = sample_world_state.model_copy(update={"tick": 100})
        new_stack = push_state(stack, new_state)

        assert len(new_stack.entries) == 3
        assert new_stack.entries[0].tick == 1  # Oldest (0) was pruned
        assert new_stack.entries[2].tick == 100

    def test_push_does_not_prune_protected_ticks(self, sample_world_state: WorldState) -> None:
        """Push does not prune protected ticks."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import push_state

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(
            entries=entries,
            current_index=2,
            max_depth=3,
            protected_ticks=frozenset({0}),  # Protect tick 0
        )

        # Push new state
        new_state = sample_world_state.model_copy(update={"tick": 100})
        new_stack = push_state(stack, new_state)

        # Protected tick 0 should still be there
        assert any(e.tick == 0 for e in new_stack.entries)

    def test_push_returns_new_instance(self, sample_world_state: WorldState) -> None:
        """Push returns a new HistoryStack instance."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import push_state

        stack = HistoryStack()
        new_stack = push_state(stack, sample_world_state)

        assert new_stack is not stack


# =============================================================================
# UNDO TESTS
# =============================================================================


@pytest.mark.topology
class TestUndo:
    """undo should move back one state in history."""

    def test_undo_returns_previous_state(self, sample_world_state: WorldState) -> None:
        """Undo returns the previous state."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import undo

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=2)

        new_stack, state = undo(stack)

        assert state is not None
        assert state.tick == 1
        assert new_stack.current_index == 1

    def test_undo_on_empty_stack_returns_none(self) -> None:
        """Undo on empty stack returns None state."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import undo

        stack = HistoryStack()
        new_stack, state = undo(stack)

        assert state is None
        assert new_stack.current_index == -1

    def test_undo_at_start_returns_none(self, sample_world_state: WorldState) -> None:
        """Undo at start of history returns None (can't go further back)."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import undo

        entry = HistoryEntry(tick=0, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)

        new_stack, state = undo(stack)

        assert state is None
        assert new_stack.current_index == 0  # Unchanged

    def test_undo_preserves_entries(self, sample_world_state: WorldState) -> None:
        """Undo preserves all entries (for redo)."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import undo

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=2)

        new_stack, _ = undo(stack)

        assert len(new_stack.entries) == 3

    def test_multiple_undos(self, sample_world_state: WorldState) -> None:
        """Can perform multiple undos."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import undo

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(5)
        ]
        stack = HistoryStack(entries=entries, current_index=4)

        stack, state1 = undo(stack)
        stack, state2 = undo(stack)
        stack, state3 = undo(stack)

        assert state1 is not None and state1.tick == 3
        assert state2 is not None and state2.tick == 2
        assert state3 is not None and state3.tick == 1
        assert stack.current_index == 1


# =============================================================================
# REDO TESTS
# =============================================================================


@pytest.mark.topology
class TestRedo:
    """redo should move forward one state in history."""

    def test_redo_returns_next_state(self, sample_world_state: WorldState) -> None:
        """Redo returns the next state."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import redo

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=1)

        new_stack, state = redo(stack)

        assert state is not None
        assert state.tick == 2
        assert new_stack.current_index == 2

    def test_redo_on_empty_stack_returns_none(self) -> None:
        """Redo on empty stack returns None state."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import redo

        stack = HistoryStack()
        new_stack, state = redo(stack)

        assert state is None
        assert new_stack.current_index == -1

    def test_redo_at_end_returns_none(self, sample_world_state: WorldState) -> None:
        """Redo at end of history returns None (nothing to redo)."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import redo

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=2)

        new_stack, state = redo(stack)

        assert state is None
        assert new_stack.current_index == 2  # Unchanged


# =============================================================================
# GET CURRENT STATE TESTS
# =============================================================================


@pytest.mark.topology
class TestGetCurrentState:
    """get_current_state should return the state at current_index."""

    def test_get_current_state_returns_state(self, sample_world_state: WorldState) -> None:
        """Returns the current state."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import get_current_state

        entry = HistoryEntry(tick=5, state=sample_world_state.model_copy(update={"tick": 5}))
        stack = HistoryStack(entries=[entry], current_index=0)

        state = get_current_state(stack)

        assert state is not None
        assert state.tick == 5

    def test_get_current_state_empty_returns_none(self) -> None:
        """Returns None for empty stack."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import get_current_state

        stack = HistoryStack()
        state = get_current_state(stack)

        assert state is None

    def test_get_current_state_after_undo(self, sample_world_state: WorldState) -> None:
        """Returns correct state after undo."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import get_current_state

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=1)

        state = get_current_state(stack)

        assert state is not None
        assert state.tick == 1


# =============================================================================
# GET STATE AT TICK TESTS
# =============================================================================


@pytest.mark.topology
class TestGetStateAtTick:
    """get_state_at_tick should return state for a specific tick."""

    def test_get_state_at_tick_found(self, sample_world_state: WorldState) -> None:
        """Returns state at the specified tick."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import get_state_at_tick

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(5)
        ]
        stack = HistoryStack(entries=entries, current_index=4)

        state = get_state_at_tick(stack, 2)

        assert state is not None
        assert state.tick == 2

    def test_get_state_at_tick_not_found(self, sample_world_state: WorldState) -> None:
        """Returns None if tick not found."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import get_state_at_tick

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=2)

        state = get_state_at_tick(stack, 99)

        assert state is None

    def test_get_state_at_tick_empty_stack(self) -> None:
        """Returns None for empty stack."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import get_state_at_tick

        stack = HistoryStack()
        state = get_state_at_tick(stack, 0)

        assert state is None


# =============================================================================
# PRUNE HISTORY TESTS
# =============================================================================


@pytest.mark.topology
class TestPruneHistory:
    """prune_history should remove old entries while respecting protected ticks."""

    def test_prune_keeps_specified_count(self, sample_world_state: WorldState) -> None:
        """Prune keeps the specified number of most recent entries."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import prune_history

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(10)
        ]
        stack = HistoryStack(entries=entries, current_index=9)

        new_stack = prune_history(stack, keep_count=3)

        assert len(new_stack.entries) == 3
        # Should keep most recent: ticks 7, 8, 9
        assert new_stack.entries[0].tick == 7
        assert new_stack.entries[2].tick == 9

    def test_prune_respects_protected_ticks(self, sample_world_state: WorldState) -> None:
        """Prune keeps protected ticks even if they would be removed."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import prune_history

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(10)
        ]
        stack = HistoryStack(
            entries=entries,
            current_index=9,
            protected_ticks=frozenset({0, 3}),  # Protect ticks 0 and 3
        )

        new_stack = prune_history(stack, keep_count=3)

        # Should have: protected 0, protected 3, plus most recent entries
        tick_set = {e.tick for e in new_stack.entries}
        assert 0 in tick_set
        assert 3 in tick_set

    def test_prune_adjusts_current_index(self, sample_world_state: WorldState) -> None:
        """Prune adjusts current_index after removing entries."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import prune_history

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(10)
        ]
        stack = HistoryStack(entries=entries, current_index=9)

        new_stack = prune_history(stack, keep_count=3)

        # current_index should point to the same tick (9) but at new position
        assert new_stack.current_index == 2
        assert new_stack.entries[new_stack.current_index].tick == 9

    def test_prune_noop_if_under_count(self, sample_world_state: WorldState) -> None:
        """Prune is a no-op if entries <= keep_count."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import prune_history

        entries = [
            HistoryEntry(tick=i, state=sample_world_state.model_copy(update={"tick": i}))
            for i in range(3)
        ]
        stack = HistoryStack(entries=entries, current_index=2)

        new_stack = prune_history(stack, keep_count=5)

        assert len(new_stack.entries) == 3


# =============================================================================
# PROTECT TICK TESTS
# =============================================================================


@pytest.mark.topology
class TestProtectTick:
    """protect_tick should mark a tick as unremovable."""

    def test_protect_tick_adds_to_set(self, sample_world_state: WorldState) -> None:
        """Protect tick adds tick to protected set."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import protect_tick

        entry = HistoryEntry(tick=5, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)

        new_stack = protect_tick(stack, 5)

        assert 5 in new_stack.protected_ticks

    def test_protect_tick_preserves_existing_protected(
        self, sample_world_state: WorldState
    ) -> None:
        """Protect tick preserves existing protected ticks."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import protect_tick

        entry = HistoryEntry(tick=5, state=sample_world_state)
        stack = HistoryStack(
            entries=[entry],
            current_index=0,
            protected_ticks=frozenset({1, 2}),
        )

        new_stack = protect_tick(stack, 5)

        assert 1 in new_stack.protected_ticks
        assert 2 in new_stack.protected_ticks
        assert 5 in new_stack.protected_ticks

    def test_protect_tick_idempotent(self, sample_world_state: WorldState) -> None:
        """Protecting an already protected tick is a no-op."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import protect_tick

        entry = HistoryEntry(tick=5, state=sample_world_state)
        stack = HistoryStack(
            entries=[entry],
            current_index=0,
            protected_ticks=frozenset({5}),
        )

        new_stack = protect_tick(stack, 5)

        assert len(new_stack.protected_ticks) == 1
        assert 5 in new_stack.protected_ticks

    def test_protect_tick_returns_new_instance(self, sample_world_state: WorldState) -> None:
        """Protect tick returns new HistoryStack instance."""
        from babylon.engine.history.models import HistoryEntry, HistoryStack
        from babylon.engine.history.stack import protect_tick

        entry = HistoryEntry(tick=5, state=sample_world_state)
        stack = HistoryStack(entries=[entry], current_index=0)

        new_stack = protect_tick(stack, 5)

        assert new_stack is not stack


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.topology
class TestStackIntegration:
    """Integration tests for stack operations."""

    def test_full_undo_redo_cycle(self, sample_world_state: WorldState) -> None:
        """Can perform full undo/redo cycle."""
        from babylon.engine.history.models import HistoryStack
        from babylon.engine.history.stack import (
            get_current_state,
            push_state,
            redo,
            undo,
        )

        # Build history
        stack = HistoryStack()
        for i in range(5):
            state = sample_world_state.model_copy(update={"tick": i})
            stack = push_state(stack, state)

        # Undo twice
        stack, _ = undo(stack)
        stack, _ = undo(stack)
        assert get_current_state(stack) is not None
        assert get_current_state(stack).tick == 2  # type: ignore[union-attr]

        # Redo once
        stack, _ = redo(stack)
        assert get_current_state(stack) is not None
        assert get_current_state(stack).tick == 3  # type: ignore[union-attr]

        # Push new state - should truncate
        new_state = sample_world_state.model_copy(update={"tick": 100})
        stack = push_state(stack, new_state)

        assert len(stack.entries) == 5  # 0, 1, 2, 3, 100
        assert stack.entries[-1].tick == 100

        # Can't redo after push
        stack, state = redo(stack)
        assert state is None
