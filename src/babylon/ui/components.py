"""Reusable UI components for the Babylon simulation.

This module provides UI components that are used across the Babylon
dashboard, following the "Bunker Constructivism" design system.

Components:
    SystemLog: Raw event log with instant display (NO typewriter animation).
    TrendPlotter: Real-time EChart line graph for simulation metrics.
    StateInspector: JSON viewer for raw entity state inspection.

Example:
    >>> from babylon.ui.components import SystemLog, TrendPlotter, StateInspector
    >>> log = SystemLog()
    >>> log.log("Revolution begins", level="INFO")
    >>> log.log("Warning: tension rising", level="WARN")
    >>> log.log("RUPTURE EVENT", level="ERROR")

    >>> plotter = TrendPlotter()
    >>> plotter.push_data(tick=1, rent=100.0, tension=0.5)

    >>> inspector = StateInspector()
    >>> inspector.refresh({"id": "C001", "wealth": 100.0})
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


class TrendPlotter:
    """Real-time EChart line graph for simulation metrics.

    Displays:
        - Global Imperial Rent (green line)
        - Global Tension (red line)

    Maintains rolling window of last 50 ticks.

    Styling (from ai-docs/design-system.yaml):
        - Chart background: void (#050505)
        - Axis lines/grid: dark_metal (#404040)
        - Axis labels/legend: silver_dust (#C0C0C0)
        - Imperial Rent line: data_green (#39FF14)
        - Global Tension line: phosphor_burn_red (#D40000)

    Args:
        None

    Example:
        >>> plotter = TrendPlotter()
        >>> plotter.push_data(tick=1, rent=100.0, tension=0.5)
        >>> plotter.push_data(tick=2, rent=150.0, tension=0.6)
    """

    # Rolling window size
    MAX_POINTS = 50

    # Design System color palette (from ai-docs/design-system.yaml)
    VOID = "#050505"
    DARK_METAL = "#404040"
    SILVER_DUST = "#C0C0C0"
    DATA_GREEN = "#39FF14"
    PHOSPHOR_BURN_RED = "#D40000"

    def __init__(self) -> None:
        """Initialize the TrendPlotter with empty data."""
        # Internal state: lists for tick numbers and metric values
        self._ticks: list[int] = []
        self._rent_data: list[float] = []
        self._tension_data: list[float] = []

        # Build UI elements
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the EChart UI element."""
        self.echart: Any = ui.echart(
            {
                "backgroundColor": self.VOID,
                "xAxis": {
                    "type": "category",
                    "data": [],
                    "axisLabel": {"color": self.SILVER_DUST},
                    "axisLine": {"lineStyle": {"color": self.DARK_METAL}},
                },
                "yAxis": {
                    "type": "value",
                    "axisLabel": {"color": self.SILVER_DUST},
                    "axisLine": {"lineStyle": {"color": self.DARK_METAL}},
                    "splitLine": {"lineStyle": {"color": self.DARK_METAL}},
                },
                "legend": {
                    "data": ["Imperial Rent", "Global Tension"],
                    "textStyle": {"color": self.SILVER_DUST},
                },
                "series": [
                    {
                        "name": "Imperial Rent",
                        "type": "line",
                        "data": [],
                        "lineStyle": {"color": self.DATA_GREEN},
                        "itemStyle": {"color": self.DATA_GREEN},
                    },
                    {
                        "name": "Global Tension",
                        "type": "line",
                        "data": [],
                        "lineStyle": {"color": self.PHOSPHOR_BURN_RED},
                        "itemStyle": {"color": self.PHOSPHOR_BURN_RED},
                    },
                ],
            }
        ).classes("w-full h-full")

    def push_data(self, tick: int, rent: float, tension: float) -> None:
        """Add data point, maintaining rolling window of MAX_POINTS.

        Appends the new data point to all three lists. If the lists exceed
        MAX_POINTS (50), the oldest values are removed from the front.

        Args:
            tick: The simulation tick number.
            rent: Global Imperial Rent value for this tick.
            tension: Global Tension value for this tick.
        """
        # Append new data
        self._ticks.append(tick)
        self._rent_data.append(rent)
        self._tension_data.append(tension)

        # Enforce rolling window (max 50 points)
        if len(self._ticks) > self.MAX_POINTS:
            self._ticks.pop(0)
            self._rent_data.pop(0)
            self._tension_data.pop(0)

        # Update EChart options
        self.echart.options["xAxis"]["data"] = self._ticks
        self.echart.options["series"][0]["data"] = self._rent_data
        self.echart.options["series"][1]["data"] = self._tension_data
        self.echart.update()


class StateInspector:
    """JSON viewer for raw entity state inspection.

    Displays entity data in a read-only JSON editor format.
    Used to inspect C001 (Periphery Worker) entity state.

    The StateInspector provides:
        - Read-only JSON display (no editing allowed)
        - Full replacement on refresh (no merging)
        - Support for nested dicts, lists, and numeric values
        - Bunker Constructivism aesthetic styling

    Styling (from ai-docs/design-system.yaml):
        - Container: bg-[#050505] border border-[#404040] p-2 overflow-auto
        - Background: void (#050505)
        - Border: dark_metal (#404040)

    Args:
        None

    Example:
        >>> inspector = StateInspector()
        >>> inspector.refresh({"id": "C001", "wealth": 100.0})
        >>> inspector.refresh({"id": "C001", "wealth": 150.0})  # replaces previous
    """

    # Design System: Bunker Constructivism JSON viewer component
    CONTAINER_CLASSES = "bg-[#050505] border border-[#404040] p-2 overflow-auto"

    def __init__(self) -> None:
        """Initialize the StateInspector with empty state."""
        # Internal state: current entity data being displayed
        self._current_data: dict[str, Any] = {}

        # Build UI elements
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the UI elements."""
        with ui.element("div").classes(self.CONTAINER_CLASSES):
            self.json_editor: Any = ui.json_editor(
                {"content": {"json": self._current_data}},
            ).classes("w-full h-full")
            # Set read-only mode
            self.json_editor.run_editor_method("updateProps", {"readOnly": True})

    def refresh(self, entity_data: dict[str, Any]) -> None:
        """Update displayed entity data.

        Completely replaces the current data with the new entity_data.
        No merging is performed - this is a full replacement.

        Args:
            entity_data: Dictionary containing entity state to display.
        """
        self._current_data = entity_data
        self.json_editor.run_editor_method("set", {"json": entity_data})
