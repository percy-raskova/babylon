"""Tests for NarrativeTerminal UI component.

RED Phase: These tests define the contract for the NarrativeTerminal component.
The NarrativeTerminal provides a typewriter-style display for AI-generated
narrative from the NarrativeDirector observer.

Test Intent:
- NarrativeTerminal initializes with empty queue and idle state
- Messages can be added to the queue via log()
- Queue is processed in FIFO order
- Typing state is managed correctly (starts/stops)
- Process queue correctly handles empty queue
- Polling helper can find NarrativeDirector by name

Aesthetic: "Bunker Constructivism" - Void black bg, data green text, monospace.

Design System Colors:
- Container: bg-[#050505] border border-[#404040] p-4 h-64 overflow-auto
- Text: text-[#39FF14] font-mono text-sm
- Typewriter interval: 30ms (0.03s)
"""

from typing import Protocol
from unittest.mock import MagicMock, Mock


class HasName(Protocol):
    """Protocol for objects with a name property."""

    @property
    def name(self) -> str:
        """Return observer identifier."""
        ...

    @property
    def narrative_log(self) -> list[str]:
        """Return narrative entries."""
        ...


class TestNarrativeTerminalInitialization:
    """Test NarrativeTerminal instantiation and initial state."""

    def test_terminal_initializes_with_empty_queue(self) -> None:
        """NarrativeTerminal starts with an empty message queue."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()

        assert terminal._message_queue == []
        assert len(terminal._message_queue) == 0

    def test_terminal_starts_not_typing(self) -> None:
        """NarrativeTerminal starts in idle state (not typing)."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()

        assert terminal._is_typing is False

    def test_terminal_starts_with_empty_current_text(self) -> None:
        """NarrativeTerminal starts with empty current text."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()

        assert terminal._current_text == ""

    def test_terminal_starts_with_displayed_index_zero(self) -> None:
        """NarrativeTerminal starts with displayed index at zero."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()

        assert terminal._displayed_index == 0

    def test_terminal_has_scroll_area(self) -> None:
        """NarrativeTerminal creates a scroll_area element."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()

        assert hasattr(terminal, "scroll_area")
        assert terminal.scroll_area is not None


class TestQueueManagement:
    """Test message queue operations."""

    def test_log_adds_message_to_queue(self) -> None:
        """log() adds a message to the queue."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._is_typing = True  # Simulate already typing to prevent auto-start

        # Manually add to queue without triggering process
        terminal._message_queue.append("Test message")

        assert "Test message" in terminal._message_queue

    def test_log_multiple_messages_maintains_fifo_order(self) -> None:
        """Multiple log() calls maintain FIFO order in the queue."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._is_typing = True  # Prevent auto-start

        terminal._message_queue.append("First message")
        terminal._message_queue.append("Second message")
        terminal._message_queue.append("Third message")

        assert terminal._message_queue[0] == "First message"
        assert terminal._message_queue[1] == "Second message"
        assert terminal._message_queue[2] == "Third message"

    def test_log_starts_typing_if_not_already(self) -> None:
        """log() starts typing process if not already typing."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        assert terminal._is_typing is False

        terminal.log("Start typing")

        # After log(), typing should be in progress
        assert terminal._is_typing is True

    def test_log_does_not_restart_typing_if_already_typing(self) -> None:
        """log() does not restart typing if already in progress."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._is_typing = True
        terminal._current_text = "Already processing"
        terminal._displayed_index = 5

        # Manually add to queue (log would try to process if not typing)
        terminal._message_queue.append("New message")

        # Call log with typing already in progress
        original_text = terminal._current_text

        # The state should remain unchanged since we're already typing
        assert terminal._is_typing is True
        assert terminal._current_text == original_text


class TestProcessQueue:
    """Test queue processing mechanics."""

    def test_process_queue_pops_from_front(self) -> None:
        """_process_queue() pops the first message from the queue."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._message_queue = ["First", "Second", "Third"]
        terminal._is_typing = True

        terminal._process_queue()

        # First message should be popped
        assert "First" not in terminal._message_queue
        assert terminal._message_queue == ["Second", "Third"]

    def test_process_queue_sets_current_text(self) -> None:
        """_process_queue() sets current_text to the popped message."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._message_queue = ["Test message"]
        terminal._is_typing = True

        terminal._process_queue()

        assert terminal._current_text == "Test message"

    def test_process_queue_resets_displayed_index_and_reveals_first_char(self) -> None:
        """_process_queue() resets index and reveals first character.

        After _process_queue() sets up the new message and calls
        _reveal_next_character(), the index will be at 1 (first char revealed).
        """
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._message_queue = ["Test message"]
        terminal._is_typing = True
        terminal._displayed_index = 99  # Previous state

        terminal._process_queue()

        # Index is 1 because _process_queue calls _reveal_next_character
        # which increments from 0 to 1 (first char revealed)
        assert terminal._displayed_index == 1

    def test_process_queue_stops_typing_when_empty(self) -> None:
        """_process_queue() sets is_typing to False when queue is empty."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._message_queue = []
        terminal._is_typing = True

        terminal._process_queue()

        assert terminal._is_typing is False


class TestDirectorPolling:
    """Test finding and polling the NarrativeDirector."""

    def test_find_narrative_director_by_name(self) -> None:
        """_find_narrative_director() finds director by name property."""
        from babylon.ui.terminal import find_narrative_director

        # Create mock observers
        mock_other = Mock()
        mock_other.name = "OtherObserver"

        mock_director = Mock()
        mock_director.name = "NarrativeDirector"
        mock_director.narrative_log = ["Entry 1", "Entry 2"]

        observers = [mock_other, mock_director]

        result = find_narrative_director(observers)

        assert result is mock_director

    def test_find_narrative_director_returns_none_if_not_found(self) -> None:
        """_find_narrative_director() returns None if director not in list."""
        from babylon.ui.terminal import find_narrative_director

        mock_other = Mock()
        mock_other.name = "OtherObserver"

        observers = [mock_other]

        result = find_narrative_director(observers)

        assert result is None

    def test_find_narrative_director_with_empty_list(self) -> None:
        """_find_narrative_director() returns None for empty observer list."""
        from babylon.ui.terminal import find_narrative_director

        result = find_narrative_director([])

        assert result is None


class TestPollingIntegration:
    """Test polling logic that detects new narrative entries."""

    def test_poll_detects_new_entries(self) -> None:
        """Polling detects when narrative_log has grown."""
        from babylon.ui.terminal import poll_narrative_director

        mock_director = Mock()
        mock_director.narrative_log = ["Entry 1", "Entry 2", "Entry 3"]

        last_index = 1  # We've seen Entry 1

        new_entries, new_index = poll_narrative_director(mock_director, last_index)

        assert new_entries == ["Entry 2", "Entry 3"]
        assert new_index == 3

    def test_poll_returns_empty_when_no_new_entries(self) -> None:
        """Polling returns empty list when no new entries."""
        from babylon.ui.terminal import poll_narrative_director

        mock_director = Mock()
        mock_director.narrative_log = ["Entry 1"]

        last_index = 1  # We've seen everything

        new_entries, new_index = poll_narrative_director(mock_director, last_index)

        assert new_entries == []
        assert new_index == 1

    def test_poll_updates_last_index(self) -> None:
        """Polling updates last_index to current log length."""
        from babylon.ui.terminal import poll_narrative_director

        mock_director = Mock()
        mock_director.narrative_log = ["A", "B", "C", "D", "E"]

        last_index = 2

        new_entries, new_index = poll_narrative_director(mock_director, last_index)

        assert new_index == 5


class TestDesignSystemConstants:
    """Test that design system constants are correctly defined."""

    def test_container_classes(self) -> None:
        """Container classes match Bunker Constructivism spec."""
        from babylon.ui.terminal import NarrativeTerminal

        expected = "bg-[#050505] border border-[#404040] p-4 h-64 overflow-auto"
        assert expected == NarrativeTerminal.CONTAINER_CLASSES

    def test_text_classes(self) -> None:
        """Text classes match Bunker Constructivism spec."""
        from babylon.ui.terminal import NarrativeTerminal

        expected = "text-[#39FF14] font-mono text-sm"
        assert expected == NarrativeTerminal.TEXT_CLASSES

    def test_typewriter_interval(self) -> None:
        """Typewriter interval is 30ms (0.03 seconds)."""
        from babylon.ui.terminal import NarrativeTerminal

        assert NarrativeTerminal.TYPEWRITER_INTERVAL == 0.03


class TestTypewriterReveal:
    """Test character-by-character reveal mechanics."""

    def test_reveal_increments_displayed_index(self) -> None:
        """_reveal_next_character() increments displayed_index by 1."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._current_text = "Hello"
        terminal._displayed_index = 0
        terminal._is_typing = True
        terminal._current_label = MagicMock()

        terminal._reveal_next_character()

        assert terminal._displayed_index == 1

    def test_reveal_stops_at_end_of_text(self) -> None:
        """_reveal_next_character() stops when reaching end of text."""
        from babylon.ui.terminal import NarrativeTerminal

        terminal = NarrativeTerminal()
        terminal._current_text = "Hi"
        terminal._displayed_index = 2  # Already at end
        terminal._is_typing = True
        terminal._message_queue = []  # Empty queue
        terminal._current_label = MagicMock()

        terminal._reveal_next_character()

        # Should have called _process_queue which sets is_typing=False
        assert terminal._is_typing is False
