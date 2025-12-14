"""Narrative Terminal UI component for typewriter-style narrative display.

This module provides the NarrativeTerminal class, which displays AI-generated
narrative from the NarrativeDirector observer with a typewriter animation effect.

Aesthetic: "Bunker Constructivism" - Void black background, data green text, monospace.

Example:
    >>> from babylon.ui.terminal import NarrativeTerminal
    >>> terminal = NarrativeTerminal()
    >>> terminal.log("The proletariat stirs...")  # Triggers typewriter animation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    from collections.abc import Sequence

    from babylon.engine.observer import SimulationObserver


class NarrativeTerminal:
    """Terminal with typewriter animation for AI-generated narrative.

    The NarrativeTerminal provides:
    - Message queue for incoming narrative entries
    - Character-by-character typewriter reveal animation
    - Auto-scrolling to newest content
    - Bunker Constructivism aesthetic styling

    Styling:
        - Container: bg-[#050505] border border-[#404040] p-4 h-64 overflow-auto
        - Text: text-[#39FF14] font-mono text-sm
        - Typewriter interval: 30ms per character

    Args:
        None

    Example:
        >>> terminal = NarrativeTerminal()
        >>> terminal.log("Revolution begins...")  # Typewriter animation starts
    """

    # Styling constants for Bunker Constructivism aesthetic
    CONTAINER_CLASSES = "bg-[#050505] border border-[#404040] p-4 w-full overflow-auto"
    CONTAINER_STYLE = "flex: 1; min-height: 0"
    TEXT_CLASSES = "text-[#39FF14] font-mono text-sm"
    TYPEWRITER_INTERVAL = 0.03  # 30ms per character

    def __init__(self) -> None:
        """Initialize the NarrativeTerminal with empty state."""
        # Message queue state
        self._message_queue: list[str] = []
        self._current_text: str = ""
        self._is_typing: bool = False
        self._displayed_index: int = 0

        # UI element references (initialized in _build_ui)
        self._current_label: Any = None

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the UI elements."""
        with (
            ui.scroll_area()
            .classes(self.CONTAINER_CLASSES)
            .style(self.CONTAINER_STYLE) as scroll_area
        ):
            self.scroll_area: Any = scroll_area
            with ui.column().classes("w-full"):
                self._content_column: Any = ui.column().classes("w-full")

    def log(self, text: str) -> None:
        """Add message to queue and start typing if idle.

        Args:
            text: The narrative message to display.
        """
        self._message_queue.append(text)
        if not self._is_typing:
            self._is_typing = True
            self._process_queue()

    def _process_queue(self) -> None:
        """Pop next message from queue and begin typewriter reveal.

        If the queue is empty, sets typing state to False.
        """
        if not self._message_queue:
            self._is_typing = False
            return

        self._current_text = self._message_queue.pop(0)
        self._displayed_index = 0

        # Create new label for this message within the content column
        with self._content_column:
            self._current_label = ui.markdown("").classes(self.TEXT_CLASSES)

        self._reveal_next_character()

    def _reveal_next_character(self) -> None:
        """Reveal next character, auto-scroll, and schedule next reveal.

        Increments displayed_index, updates the label content,
        scrolls to bottom, and schedules the next character reveal.
        When the message is complete, calls _process_queue() for the next message.
        """
        if self._displayed_index < len(self._current_text):
            self._displayed_index += 1
            self._current_label.set_content(self._current_text[: self._displayed_index])
            self.scroll_area.scroll_to(percent=1.0)
            ui.timer(self.TYPEWRITER_INTERVAL, self._reveal_next_character, once=True)
        else:
            # Current message complete, process next in queue
            self._process_queue()


def find_narrative_director(
    observers: Sequence[SimulationObserver],
) -> SimulationObserver | None:
    """Find the NarrativeDirector by name in a list of observers.

    Searches through the observers for one with name == "NarrativeDirector".

    Args:
        observers: Sequence of SimulationObserver objects to search.

    Returns:
        The NarrativeDirector observer if found, None otherwise.
    """
    for observer in observers:
        if observer.name == "NarrativeDirector":
            return observer
    return None


def poll_narrative_director(
    director: Any,
    last_index: int,
) -> tuple[list[str], int]:
    """Poll the NarrativeDirector for new narrative entries.

    Compares current narrative_log length to last_index and returns
    any new entries since that index.

    Args:
        director: The NarrativeDirector observer (must have narrative_log property).
        last_index: The last known index into the narrative_log.

    Returns:
        A tuple of (new_entries, new_index) where:
        - new_entries: List of new narrative strings since last_index
        - new_index: The updated index (current log length)
    """
    log = director.narrative_log
    current_length = len(log)

    if current_length > last_index:
        new_entries = log[last_index:current_length]
        return (new_entries, current_length)

    return ([], last_index)
