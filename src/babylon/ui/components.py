"""Reusable UI components for the Babylon simulation.

This module provides UI components that are used across the Babylon
dashboard, following the "Bunker Constructivism" design system.

Components:
    SystemLog: Raw event log with instant display (NO typewriter animation).

Example:
    >>> from babylon.ui.components import SystemLog
    >>> log = SystemLog()
    >>> log.log("Revolution begins", level="INFO")
    >>> log.log("Warning: tension rising", level="WARN")
    >>> log.log("RUPTURE EVENT", level="ERROR")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    pass


class SystemLog:
    """Raw event log with instant display (NO typewriter animation).

    The SystemLog provides:
    - Instant append of log entries (no queue, no animation)
    - Color-coded log levels (INFO, WARN, ERROR)
    - Auto-scrolling to newest content
    - Bunker Constructivism aesthetic styling

    This is fundamentally different from NarrativeTerminal which uses
    typewriter animation. SystemLog is for raw system events that should
    appear immediately.

    Styling:
        - Container: bg-[#050505] border border-[#404040] p-4 overflow-auto font-mono text-sm
        - INFO: text-[#39FF14] (data_green)
        - WARN: text-[#FFD700] (exposed_copper)
        - ERROR: text-[#D40000] (phosphor_burn_red)

    Args:
        None

    Example:
        >>> log = SystemLog()
        >>> log.log("System initialized")  # INFO level (default)
        >>> log.log("Resources low", level="WARN")
        >>> log.log("Critical failure!", level="ERROR")
    """

    # Design System: Bunker Constructivism terminal_output component
    CONTAINER_CLASSES = "bg-[#050505] border border-[#404040] p-4 overflow-auto font-mono text-sm"

    # Design System color palette (from ai-docs/design-system.yaml)
    LEVEL_COLORS: dict[str, str] = {
        "INFO": "#39FF14",  # data_green
        "WARN": "#FFD700",  # exposed_copper
        "ERROR": "#D40000",  # phosphor_burn_red
    }

    def __init__(self) -> None:
        """Initialize the SystemLog with empty state."""
        # Internal state: list of (text, level) tuples
        self._entries: list[tuple[str, str]] = []

        # Build UI elements
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the UI elements."""
        with ui.scroll_area().classes(self.CONTAINER_CLASSES) as scroll_area:
            self.scroll_area: Any = scroll_area
            self._content_column: Any = ui.column().classes("w-full gap-0")

    def log(self, text: str, level: str = "INFO") -> None:
        """Add entry instantly (no animation). Auto-scrolls.

        Appends the entry immediately to the log display. No queuing,
        no typewriter animation - entries appear instantly.

        Args:
            text: The log message to display.
            level: Log level - one of "INFO", "WARN", "ERROR". Defaults to "INFO".
        """
        # Store entry in internal state
        self._entries.append((text, level))

        # Get color for this level (default to INFO color if unknown level)
        color = self.LEVEL_COLORS.get(level, self.LEVEL_COLORS["INFO"])

        # Create label immediately in content column
        with self._content_column:
            ui.label(text).classes(f"text-[{color}]")

        # Auto-scroll to bottom
        self.scroll_area.scroll_to(percent=1.0)
