"""Pure stack operations for the History Stack system.

All functions in this module are pure:
- They take a HistoryStack as input
- They return a new HistoryStack (and optionally a WorldState)
- They never mutate their inputs

This enables functional transformation patterns:
    new_stack = push_state(old_stack, state)
    new_stack, previous_state = undo(old_stack)

Sprint B: Stack operations for Phase 3 persistence layer.
"""

from babylon.engine.history.models import HistoryEntry, HistoryStack
from babylon.models.world_state import WorldState


def push_state(history: HistoryStack, state: WorldState) -> HistoryStack:
    """Add a new state to the history stack.

    Behavior:
    - If current_index is not at the end, truncates future entries (linear timeline)
    - Enforces max_depth by pruning oldest non-protected entries
    - Returns new stack with state added

    Args:
        history: The current history stack.
        state: The WorldState to add.

    Returns:
        New HistoryStack with the state added.
    """
    # Create new entry
    new_entry = HistoryEntry(tick=state.tick, state=state)

    # Truncate future if we're not at the end
    if history.current_index >= 0:
        # Keep entries up to and including current_index, then add new
        entries = list(history.entries[: history.current_index + 1])
    else:
        entries = []

    entries.append(new_entry)
    new_index = len(entries) - 1

    # Create intermediate stack for pruning
    intermediate = history.model_copy(
        update={
            "entries": entries,
            "current_index": new_index,
        }
    )

    # Enforce max_depth if needed
    if len(intermediate.entries) > intermediate.max_depth:
        # Find entries we can prune (oldest first, not protected)
        pruned_entries = _prune_to_depth(
            intermediate.entries,
            intermediate.max_depth,
            intermediate.protected_ticks,
            new_index,
        )

        # Recalculate current_index based on which tick it was pointing to
        current_tick = entries[new_index].tick
        new_current_index = _find_index_for_tick(pruned_entries, current_tick)
        if new_current_index == -1:
            new_current_index = len(pruned_entries) - 1

        return history.model_copy(
            update={
                "entries": pruned_entries,
                "current_index": new_current_index,
            }
        )

    return intermediate


def _prune_to_depth(
    entries: list[HistoryEntry],
    max_depth: int,
    protected_ticks: frozenset[int],
    current_index: int,
) -> list[HistoryEntry]:
    """Prune entries to max_depth while respecting protected ticks.

    Removes oldest non-protected entries first.
    """
    if len(entries) <= max_depth:
        return entries

    result: list[HistoryEntry] = []
    to_remove_count = len(entries) - max_depth

    # Build list keeping protected and most recent
    removed = 0
    for i, entry in enumerate(entries):
        is_protected = entry.tick in protected_ticks
        is_current = i == current_index

        # Keep if: protected, current, or haven't removed enough non-protected yet
        if is_protected or is_current or removed >= to_remove_count:
            result.append(entry)
        else:
            removed += 1

    return result


def _find_index_for_tick(entries: list[HistoryEntry], tick: int) -> int:
    """Find the index of an entry with the given tick."""
    for i, entry in enumerate(entries):
        if entry.tick == tick:
            return i
    return -1


def undo(history: HistoryStack) -> tuple[HistoryStack, WorldState | None]:
    """Move back one state in history.

    Behavior:
    - Returns the previous state (one before current)
    - Preserves all entries for potential redo
    - Returns None if at start or empty

    Args:
        history: The current history stack.

    Returns:
        Tuple of (new stack, previous state or None).
    """
    # Empty stack - nothing to undo
    if history.current_index < 0 or len(history.entries) == 0:
        return history, None

    # Already at the start - can't go further back
    if history.current_index == 0:
        return history, None

    # Move back one
    new_index = history.current_index - 1
    new_stack = history.model_copy(update={"current_index": new_index})

    return new_stack, history.entries[new_index].state


def redo(history: HistoryStack) -> tuple[HistoryStack, WorldState | None]:
    """Move forward one state in history.

    Behavior:
    - Returns the next state (one after current)
    - Returns None if at end or empty

    Args:
        history: The current history stack.

    Returns:
        Tuple of (new stack, next state or None).
    """
    # Empty stack - nothing to redo
    if history.current_index < 0 or len(history.entries) == 0:
        return history, None

    # Already at the end - nothing to redo
    if history.current_index >= len(history.entries) - 1:
        return history, None

    # Move forward one
    new_index = history.current_index + 1
    new_stack = history.model_copy(update={"current_index": new_index})

    return new_stack, history.entries[new_index].state


def get_current_state(history: HistoryStack) -> WorldState | None:
    """Get the state at the current position.

    Args:
        history: The history stack.

    Returns:
        Current WorldState or None if stack is empty.
    """
    if history.current_index < 0 or len(history.entries) == 0:
        return None

    return history.entries[history.current_index].state


def get_state_at_tick(history: HistoryStack, tick: int) -> WorldState | None:
    """Get the state for a specific tick.

    Args:
        history: The history stack.
        tick: The tick number to find.

    Returns:
        WorldState at that tick or None if not found.
    """
    for entry in history.entries:
        if entry.tick == tick:
            return entry.state
    return None


def prune_history(history: HistoryStack, keep_count: int) -> HistoryStack:
    """Remove old entries, keeping the most recent ones.

    Behavior:
    - Keeps the most recent `keep_count` entries
    - Protected ticks are never pruned (even if that exceeds keep_count)
    - Adjusts current_index to point to the same tick

    Args:
        history: The history stack.
        keep_count: Number of recent entries to keep.

    Returns:
        New HistoryStack with pruned entries.
    """
    if len(history.entries) <= keep_count:
        return history

    # Calculate how many to remove
    to_remove = len(history.entries) - keep_count

    # Get current tick for index adjustment
    current_tick = (
        history.entries[history.current_index].tick
        if history.current_index >= 0 and history.current_index < len(history.entries)
        else -1
    )

    # Build new entries list
    new_entries: list[HistoryEntry] = []
    removed = 0

    for entry in history.entries:
        is_protected = entry.tick in history.protected_ticks

        # Keep if protected, or if we've removed enough already
        if is_protected or removed >= to_remove:
            new_entries.append(entry)
        else:
            removed += 1

    # Find new current_index
    new_index = _find_index_for_tick(new_entries, current_tick)
    if new_index == -1 and len(new_entries) > 0:
        new_index = len(new_entries) - 1

    return history.model_copy(
        update={
            "entries": new_entries,
            "current_index": new_index,
        }
    )


def protect_tick(history: HistoryStack, tick: int) -> HistoryStack:
    """Mark a tick as protected (cannot be pruned).

    Args:
        history: The history stack.
        tick: The tick number to protect.

    Returns:
        New HistoryStack with the tick protected.
    """
    new_protected = history.protected_ticks | {tick}
    return history.model_copy(update={"protected_ticks": new_protected})
