"""Reusable UI components for the Babylon simulation.

This module provides UI components that are used across the Babylon
dashboard, following the "Bunker Constructivism" design system.

Components:
    SystemLog: Raw event log with instant display (NO typewriter animation).
    TrendPlotter: Real-time EChart line graph for simulation metrics.
    StateInspector: JSON viewer for raw entity state inspection.
    WirePanel: Dual narrative display panel (The Gramscian Wire).
    GaugePanel: Reusable arc gauge visualization component.
    MetabolicGauge: Specialized gauge for overshoot_ratio metric.
    ConsciousnessGapGauge: Specialized gauge for consciousness differential.
    WealthTrendPanel: Multi-line trend chart for class wealth comparison.
    EndgamePanel: Game outcome display panel (Slice 1.6: Endgame Detection).

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

See Also:
    :mod:`babylon.ui.design_system`: Bunker Constructivism color palette.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nicegui import ui

from babylon.models.enums import GameOutcome
from babylon.models.events import SimulationEvent
from babylon.ui.design_system import BunkerPalette

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
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Container background: ``VOID`` (#050505)
        - Container border: ``DARK_METAL`` (#404040)
        - INFO level: ``DATA_GREEN`` (#39FF14)
        - WARN level: ``EXPOSED_COPPER`` (#FFD700)
        - ERROR level: ``PHOSPHOR_BURN_RED`` (#D40000)

    Attributes:
        scroll_area: NiceGUI scroll area element.
        CONTAINER_CLASSES: CSS class string for container styling.
        LEVEL_COLORS: Mapping of log level to hex color.

    Example:
        >>> log = SystemLog()
        >>> log.log("System initialized")  # INFO level (default)
        >>> log.log("Resources low", level="WARN")
        >>> log.log("Critical failure!", level="ERROR")

    See Also:
        :class:`~babylon.ui.terminal.NarrativeTerminal`: Typewriter-animated display.
    """

    # Design System: Bunker Constructivism terminal_output component
    # h-full fills flex container; min-h-0 allows shrinking below content height
    CONTAINER_CLASSES = (
        f"bg-[{BunkerPalette.VOID}] border border-[{BunkerPalette.DARK_METAL}] "
        "p-4 w-full h-full min-h-0 overflow-auto font-mono text-sm"
    )

    # Design System color palette (from BunkerPalette)
    LEVEL_COLORS: dict[str, str] = {
        "INFO": BunkerPalette.LOG_INFO,
        "WARN": BunkerPalette.LOG_WARN,
        "ERROR": BunkerPalette.LOG_ERROR,
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
            ui.label(text).classes(f"text-[{color}] break-all")

        # Auto-scroll to bottom
        self.scroll_area.scroll_to(percent=1.0)


class TrendPlotter:
    """Real-time EChart line graph for simulation metrics.

    Displays two key simulation metrics as line graphs:

    - **Imperial Rent** (green line): The surplus value extracted from periphery.
    - **Global Tension** (red line): Average tension across all relationships.

    The plotter maintains a rolling window of the last 50 ticks,
    automatically discarding older data points.

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Chart background: ``VOID`` (#050505)
        - Axis lines/grid: ``DARK_METAL`` (#404040)
        - Axis labels/legend: ``SILVER_DUST`` (#C0C0C0)
        - Imperial Rent line: ``DATA_GREEN`` (#39FF14)
        - Global Tension line: ``PHOSPHOR_BURN_RED`` (#D40000)

    Attributes:
        MAX_POINTS: Maximum data points in rolling window (50).
        echart: NiceGUI EChart element.

    Example:
        >>> plotter = TrendPlotter()
        >>> plotter.push_data(tick=1, rent=100.0, tension=0.5)
        >>> plotter.push_data(tick=2, rent=150.0, tension=0.6)

    See Also:
        :class:`WealthTrendPanel`: Multi-class wealth comparison chart.
    """

    # Rolling window size
    MAX_POINTS = 50

    # Design System color palette (from BunkerPalette)
    VOID = BunkerPalette.VOID
    DARK_METAL = BunkerPalette.DARK_METAL
    SILVER_DUST = BunkerPalette.SILVER_DUST
    DATA_GREEN = BunkerPalette.DATA_GREEN
    PHOSPHOR_BURN_RED = BunkerPalette.PHOSPHOR_BURN_RED

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
        # h-full and min-h-0 ensure chart fills flex container properly
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
                    "top": 0,
                    "left": "center",
                    "show": True,
                },
                "grid": {
                    "top": 40,
                    "bottom": 30,
                    "left": 50,
                    "right": 20,
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
        ).classes("w-full h-full min-h-0")

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

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Container background: ``VOID`` (#050505)
        - Container border: ``DARK_METAL`` (#404040)

    Attributes:
        json_editor: NiceGUI json_editor element.
        CONTAINER_CLASSES: CSS class string for container styling.

    Example:
        >>> inspector = StateInspector()
        >>> inspector.refresh({"id": "C001", "wealth": 100.0})
        >>> inspector.refresh({"id": "C001", "wealth": 150.0})  # replaces previous
    """

    # Design System: Bunker Constructivism JSON viewer component
    # h-full fills flex container; min-h-0 allows shrinking below content height
    CONTAINER_CLASSES = (
        f"bg-[{BunkerPalette.VOID}] border border-[{BunkerPalette.DARK_METAL}] "
        "p-2 w-full h-full min-h-0 overflow-auto"
    )

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
            ).classes("w-full h-full min-h-0")
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


@dataclass
class WirePanelEntry:
    """Entry in the WirePanel log.

    Attributes:
        event: The simulation event that triggered this entry.
        narratives: Optional dict with "corporate" and "liberated" keys.
        has_dual_narrative: Whether this entry has both narrative perspectives.
    """

    event: SimulationEvent
    narratives: dict[str, str] | None
    has_dual_narrative: bool


class WirePanel:
    """Dual narrative display panel (The Gramscian Wire).

    Displays side-by-side Corporate and Liberated narratives for significant
    simulation events, demonstrating "Neutrality is Hegemony" thesis.

    Layout::

        +----------------------+--------------------------+
        |  THE STATE           |  THE UNDERGROUND         |
        +----------------------+--------------------------+
        |  [Corporate text]    |  [Liberated text]        |
        +----------------------+--------------------------+

    Attributes:
        CORPORATE_BG: Background color for corporate panel.
        CORPORATE_TEXT: Text color for corporate panel.
        CORPORATE_BORDER: Border accent color for corporate panel.
        CORPORATE_FONT: Font family for corporate panel.
        LIBERATED_BG: Background color for liberated panel.
        LIBERATED_TEXT: Text color for liberated panel.
        LIBERATED_BORDER: Border accent color for liberated panel.
        LIBERATED_FONT: Font family for liberated panel.
    """

    # Corporate panel styling (The State)
    CORPORATE_BG: str = "#1a1a1a"
    CORPORATE_TEXT: str = "#ffffff"
    CORPORATE_BORDER: str = "#4a90d9"
    CORPORATE_FONT: str = "system-ui, sans-serif"

    # Liberated panel styling (The Underground)
    LIBERATED_BG: str = "#0d0d0d"
    LIBERATED_TEXT: str = "#00ff88"
    LIBERATED_BORDER: str = "#9b59b6"
    LIBERATED_FONT: str = "monospace"

    def __init__(self) -> None:
        """Initialize WirePanel with empty state."""
        self._entries: list[WirePanelEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the UI elements."""
        with ui.scroll_area().classes("w-full h-full min-h-0") as scroll:
            self.scroll_area: Any = scroll
            self._content = ui.column().classes("w-full gap-4")

    def log(
        self,
        event: SimulationEvent,
        narratives: dict[str, str] | None = None,
    ) -> None:
        """Log event with optional dual narratives.

        Args:
            event: The simulation event.
            narratives: Optional {"corporate": "...", "liberated": "..."} dict.
        """
        has_dual = (
            narratives is not None and "corporate" in narratives and "liberated" in narratives
        )
        entry = WirePanelEntry(
            event=event,
            narratives=narratives,
            has_dual_narrative=has_dual,
        )
        self._entries.append(entry)

        if has_dual and narratives is not None:
            self._render_dual(narratives)
        else:
            self._render_single(event)

        self.scroll_area.scroll_to(percent=1.0)

    def _render_dual(self, narratives: dict[str, str]) -> None:
        """Render side-by-side dual narrative view.

        Args:
            narratives: Dict with "corporate" and "liberated" keys.
        """
        with self._content, ui.row().classes("w-full gap-2"):
            # Corporate panel (THE STATE)
            with (
                ui.column()
                .classes("flex-1")
                .style(
                    f"background: {self.CORPORATE_BG}; "
                    f"border-left: 3px solid {self.CORPORATE_BORDER}; "
                    f"padding: 1rem;"
                )
            ):
                ui.label("THE STATE").classes("font-bold text-xs uppercase tracking-wider").style(
                    f"color: {self.CORPORATE_BORDER};"
                )
                ui.label(narratives["corporate"]).style(
                    f"color: {self.CORPORATE_TEXT}; font-family: {self.CORPORATE_FONT};"
                )

            # Liberated panel (THE UNDERGROUND)
            with (
                ui.column()
                .classes("flex-1")
                .style(
                    f"background: {self.LIBERATED_BG}; "
                    f"border-left: 3px solid {self.LIBERATED_BORDER}; "
                    f"padding: 1rem;"
                )
            ):
                ui.label("THE UNDERGROUND").classes(
                    "font-bold text-xs uppercase tracking-wider"
                ).style(f"color: {self.LIBERATED_BORDER};")
                ui.label(narratives["liberated"]).style(
                    f"color: {self.LIBERATED_TEXT}; font-family: {self.LIBERATED_FONT};"
                )

    def _render_single(self, event: SimulationEvent) -> None:
        """Render fallback single-panel view for events without narratives.

        Args:
            event: The simulation event to display.
        """
        with (
            self._content,
            ui.element("div").style(
                f"background: {self.CORPORATE_BG}; "
                f"border-left: 3px solid {self.CORPORATE_BORDER}; "
                f"padding: 1rem;"
            ),
        ):
            ui.label(f"[{event.event_type.value}] tick={event.tick}").style(
                f"color: {self.CORPORATE_TEXT}; font-family: {self.CORPORATE_FONT};"
            )


class GaugePanel:
    """Reusable arc gauge visualization component.

    The GaugePanel provides:

    - Arc/dial gauge visualization using ECharts
    - Configurable value range (0 to max_value)
    - Optional threshold for color transitions
    - Bunker Constructivism aesthetic styling

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Background: ``VOID`` (#050505)
        - Axis/tick marks: ``DARK_METAL`` (#404040)
        - Labels: ``SILVER_DUST`` (#C0C0C0)
        - Healthy values: ``DATA_GREEN`` (#39FF14)
        - Critical values: ``PHOSPHOR_BURN_RED`` (#D40000)

    Args:
        title: Optional title displayed on the gauge.
        value: Initial value to display. Defaults to 0.
        max_value: Maximum value for the gauge range. Defaults to 1.0.
        threshold: Optional threshold for color change. Values at or above
            threshold display in red; values below display in green.

    Attributes:
        echart: NiceGUI EChart element.

    Example:
        >>> gauge = GaugePanel(title="Overshoot", max_value=2.0, threshold=1.0)
        >>> gauge.update(0.75)  # Green - below threshold
        >>> gauge.update(1.5)   # Red - above threshold

    See Also:
        :class:`MetabolicGauge`: Overshoot ratio gauge.
        :class:`ConsciousnessGapGauge`: Consciousness differential gauge.
    """

    # Design System color palette (from BunkerPalette)
    VOID: str = BunkerPalette.VOID
    DARK_METAL: str = BunkerPalette.DARK_METAL
    SILVER_DUST: str = BunkerPalette.SILVER_DUST
    DATA_GREEN: str = BunkerPalette.DATA_GREEN
    PHOSPHOR_BURN_RED: str = BunkerPalette.PHOSPHOR_BURN_RED

    def __init__(
        self,
        title: str | None = None,
        value: float = 0,
        max_value: float = 1.0,
        threshold: float | None = None,
    ) -> None:
        """Initialize the GaugePanel with configurable parameters."""
        self._value = value
        self._max_value = max_value
        self._threshold = threshold
        self._title = title or ""

        self._build_ui()

    def _get_color_for_value(self, value: float) -> str:
        """Determine color based on value and threshold."""
        if self._threshold is None:
            return self.DATA_GREEN
        if value >= self._threshold:
            return self.PHOSPHOR_BURN_RED
        return self.DATA_GREEN

    def _build_ui(self) -> None:
        """Construct the EChart gauge UI element."""
        current_color = self._get_color_for_value(self._value)

        self.echart: Any = ui.echart(
            {
                "backgroundColor": self.VOID,
                "title": {
                    "text": self._title,
                    "left": "center",
                    "top": "bottom",
                    "textStyle": {"color": self.SILVER_DUST, "fontSize": 12},
                },
                "series": [
                    {
                        "type": "gauge",
                        "startAngle": 180,
                        "endAngle": 0,
                        "min": 0,
                        "max": self._max_value,
                        "splitNumber": 4,
                        "axisLine": {
                            "lineStyle": {
                                "width": 10,
                                "color": [[1, self.DARK_METAL]],
                            }
                        },
                        "splitLine": {
                            "length": 10,
                            "lineStyle": {"color": self.DARK_METAL},
                        },
                        "axisTick": {
                            "length": 5,
                            "lineStyle": {"color": self.DARK_METAL},
                        },
                        "axisLabel": {
                            "color": self.SILVER_DUST,
                            "fontSize": 10,
                        },
                        "pointer": {
                            "itemStyle": {"color": current_color},
                        },
                        "title": {
                            "show": bool(self._title),
                            "offsetCenter": [0, "70%"],
                            "color": self.SILVER_DUST,
                        },
                        "detail": {
                            "valueAnimation": True,
                            "formatter": "{value}",
                            "color": current_color,
                            "fontSize": 16,
                            "offsetCenter": [0, "40%"],
                        },
                        "data": [{"value": self._value}],
                    }
                ],
            }
        ).classes("w-full h-full min-h-0")

    def update(self, value: float) -> None:
        """Update the gauge to display a new value.

        Args:
            value: The new value to display on the gauge.
        """
        self._value = value
        current_color = self._get_color_for_value(value)

        # Update the data and colors
        self.echart.options["series"][0]["data"] = [{"value": value}]
        self.echart.options["series"][0]["pointer"]["itemStyle"]["color"] = current_color
        self.echart.options["series"][0]["detail"]["color"] = current_color
        self.echart.update()


class MetabolicGauge:
    """Specialized gauge for displaying overshoot_ratio metric.

    The MetabolicGauge displays the ecological overshoot ratio, indicating
    whether resource consumption exceeds biocapacity. Uses a threshold of 1.0
    to distinguish sustainable (green) from overshoot (red) states.

    The overshoot ratio is defined as::

        Overshoot Ratio = Consumption / Biocapacity

    Interpretation:

    - Ratio < 1.0: **Sustainable** - within planetary limits
    - Ratio >= 1.0: **Overshoot** - ecological debt accumulating

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Sustainable (< 1.0): ``DATA_GREEN`` (#39FF14)
        - Overshoot (>= 1.0): ``PHOSPHOR_BURN_RED`` (#D40000)

    Attributes:
        gauge: Underlying :class:`GaugePanel` instance.
        echart: NiceGUI EChart element (exposed from gauge).
        threshold: Overshoot threshold value (1.0).
        max_value: Maximum displayable value (3.0).
        title: Gauge title ("METABOLIC OVERSHOOT").

    Example:
        >>> gauge = MetabolicGauge()
        >>> gauge.refresh(overshoot_ratio=0.75)  # Green - sustainable
        >>> gauge.refresh(overshoot_ratio=1.5)   # Red - overshoot

    See Also:
        :class:`GaugePanel`: Base gauge component.
        :mod:`babylon.engine.systems.metabolism`: Metabolism system calculations.
    """

    # Design system colors (from BunkerPalette)
    SUSTAINABLE_COLOR: str = BunkerPalette.DATA_GREEN
    OVERSHOOT_COLOR: str = BunkerPalette.PHOSPHOR_BURN_RED

    # Configuration
    TITLE: str = "METABOLIC OVERSHOOT"
    THRESHOLD: float = 1.0
    MAX_VALUE: float = 3.0

    def __init__(self) -> None:
        """Initialize the MetabolicGauge with overshoot-specific settings."""
        self.threshold = self.THRESHOLD
        self.max_value = self.MAX_VALUE
        self.title = self.TITLE

        self.gauge = GaugePanel(
            title=self.TITLE,
            value=0,
            max_value=self.MAX_VALUE,
            threshold=self.THRESHOLD,
        )
        # Expose the echart for direct access
        self.echart = self.gauge.echart

    def refresh(self, overshoot_ratio: float) -> None:
        """Update the gauge with a new overshoot ratio value.

        Args:
            overshoot_ratio: The consumption/biocapacity ratio.
                Values < 1.0 are sustainable, >= 1.0 indicate overshoot.
        """
        self.gauge.update(overshoot_ratio)


class ConsciousnessGapGauge:
    """Specialized gauge for displaying consciousness differential.

    The ConsciousnessGapGauge displays the difference between Periphery
    Worker (C001) and Labor Aristocracy (C004) consciousness levels.

    The consciousness gap is defined as::

        Consciousness Gap = P_W.consciousness - C_W.consciousness

    Interpretation:

    - Positive gap (> 0): Periphery Worker more class-conscious (revolutionary potential)
    - Negative gap (< 0): Labor Aristocracy more conscious (false consciousness dominant)
    - Zero gap (= 0): Ideological convergence (unusual equilibrium)

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Positive (> 0): ``DATA_GREEN`` (#39FF14) - revolutionary consciousness
        - Negative (< 0): ``PHOSPHOR_BURN_RED`` (#D40000) - false consciousness
        - Zero (= 0): ``SILVER_DUST`` (#C0C0C0) - neutral/equilibrium

    Attributes:
        echart: NiceGUI EChart element.
        min_value: Minimum value on gauge scale (-1.0).
        max_value: Maximum value on gauge scale (1.0).
        title: Gauge title ("CONSCIOUSNESS GAP").

    Example:
        >>> gauge = ConsciousnessGapGauge()
        >>> gauge.refresh(consciousness_gap=0.3)   # Green - P_W more conscious
        >>> gauge.refresh(consciousness_gap=-0.2)  # Red - C_W more conscious
        >>> gauge.refresh(consciousness_gap=0.0)   # Silver - equilibrium

    See Also:
        :class:`GaugePanel`: Base gauge component.
        :mod:`babylon.engine.systems.ideology`: Consciousness system calculations.
    """

    # Design system colors (from BunkerPalette)
    POSITIVE_COLOR: str = BunkerPalette.DATA_GREEN
    NEGATIVE_COLOR: str = BunkerPalette.PHOSPHOR_BURN_RED
    NEUTRAL_COLOR: str = BunkerPalette.SILVER_DUST

    # Configuration
    TITLE: str = "CONSCIOUSNESS GAP"
    MIN_VALUE: float = -1.0
    MAX_VALUE: float = 1.0

    def __init__(self) -> None:
        """Initialize the ConsciousnessGapGauge with consciousness-specific settings."""
        self.min_value = self.MIN_VALUE
        self.max_value = self.MAX_VALUE
        self.title = self.TITLE
        self._current_value = 0.0

        self._build_ui()

    def _get_color_for_value(self, value: float) -> str:
        """Determine color based on gap value sign."""
        if value > 0:
            return self.POSITIVE_COLOR
        elif value < 0:
            return self.NEGATIVE_COLOR
        else:
            return self.NEUTRAL_COLOR

    def _build_ui(self) -> None:
        """Construct the EChart gauge UI element for bipolar range."""
        current_color = self._get_color_for_value(self._current_value)

        self.echart: Any = ui.echart(
            {
                "backgroundColor": BunkerPalette.VOID,
                "title": {
                    "text": self.TITLE,
                    "left": "center",
                    "top": "bottom",
                    "textStyle": {"color": self.NEUTRAL_COLOR, "fontSize": 12},
                },
                "series": [
                    {
                        "type": "gauge",
                        "startAngle": 180,
                        "endAngle": 0,
                        "min": self.MIN_VALUE,
                        "max": self.MAX_VALUE,
                        "splitNumber": 4,
                        "axisLine": {
                            "lineStyle": {
                                "width": 10,
                                "color": [[1, BunkerPalette.DARK_METAL]],
                            }
                        },
                        "splitLine": {
                            "length": 10,
                            "lineStyle": {"color": BunkerPalette.DARK_METAL},
                        },
                        "axisTick": {
                            "length": 5,
                            "lineStyle": {"color": BunkerPalette.DARK_METAL},
                        },
                        "axisLabel": {
                            "color": self.NEUTRAL_COLOR,
                            "fontSize": 10,
                        },
                        "pointer": {
                            "itemStyle": {"color": current_color},
                        },
                        "title": {
                            "show": True,
                            "offsetCenter": [0, "70%"],
                            "color": self.NEUTRAL_COLOR,
                        },
                        "detail": {
                            "valueAnimation": True,
                            "formatter": "{value}",
                            "color": current_color,
                            "fontSize": 16,
                            "offsetCenter": [0, "40%"],
                        },
                        "data": [{"value": self._current_value}],
                    }
                ],
            }
        ).classes("w-full h-full min-h-0")

    def refresh(self, consciousness_gap: float) -> None:
        """Update the gauge with a new consciousness gap value.

        Args:
            consciousness_gap: The difference between P_W and C_W consciousness.
                Positive = P_W more conscious, negative = C_W more conscious.
        """
        self._current_value = consciousness_gap
        current_color = self._get_color_for_value(consciousness_gap)

        # Update the data and colors
        self.echart.options["series"][0]["data"] = [{"value": consciousness_gap}]
        self.echart.options["series"][0]["pointer"]["itemStyle"]["color"] = current_color
        self.echart.options["series"][0]["detail"]["color"] = current_color
        self.echart.update()


class WealthTrendPanel:
    """Multi-line trend chart showing wealth for all four social classes.

    Displays comparative wealth trajectories for:

    - **C001 (Periphery Worker)**: The exploited class - green line
    - **C002 (Comprador)**: Intermediary class - gold line
    - **C003 (Core Bourgeoisie)**: The exploiter class - red line
    - **C004 (Labor Aristocracy)**: The bought-off class - blue line

    Maintains a rolling window of the last MAX_POINTS (50) ticks,
    automatically discarding older data points.

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors:

        - Background: ``VOID`` (#050505)
        - Axes/Grid: ``DARK_METAL`` (#404040)
        - Labels/Legend: ``SILVER_DUST`` (#C0C0C0)
        - Periphery Worker line: ``PW_COLOR`` (#39FF14 data_green)
        - Comprador line: ``PC_COLOR`` (#FFD700 exposed_copper)
        - Core Bourgeoisie line: ``CB_COLOR`` (#D40000 phosphor_burn_red)
        - Labor Aristocracy line: ``CW_COLOR`` (#4169E1 royal_blue)

    Attributes:
        MAX_POINTS: Maximum data points in rolling window (50).
        echart: NiceGUI EChart element.

    Example:
        >>> panel = WealthTrendPanel()
        >>> panel.push_data(tick=1, p_w_wealth=100, p_c_wealth=200,
        ...                 c_b_wealth=500, c_w_wealth=150)

    See Also:
        :class:`TrendPlotter`: Simplified two-metric trend chart.
    """

    # Rolling window size
    MAX_POINTS: int = 50

    # Design System color palette (from BunkerPalette)
    VOID: str = BunkerPalette.VOID
    DARK_METAL: str = BunkerPalette.DARK_METAL
    SILVER_DUST: str = BunkerPalette.SILVER_DUST

    # Class line colors (from BunkerPalette)
    PW_COLOR: str = BunkerPalette.PW_COLOR  # data_green - Periphery Worker
    PC_COLOR: str = BunkerPalette.PC_COLOR  # exposed_copper - Comprador
    CB_COLOR: str = BunkerPalette.CB_COLOR  # phosphor_burn_red - Core Bourgeoisie
    CW_COLOR: str = BunkerPalette.CW_COLOR  # royal_blue - Labor Aristocracy

    def __init__(self) -> None:
        """Initialize the WealthTrendPanel with empty data."""
        # Internal state: lists for tick numbers and wealth values
        self._ticks: list[int] = []
        self._pw_data: list[float] = []
        self._pc_data: list[float] = []
        self._cb_data: list[float] = []
        self._cw_data: list[float] = []

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the EChart UI element with four line series."""
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
                    "data": [
                        "Periphery Worker",
                        "Comprador",
                        "Core Bourgeoisie",
                        "Labor Aristocracy",
                    ],
                    "textStyle": {"color": self.SILVER_DUST},
                    "top": 0,
                    "left": "center",
                    "show": True,
                },
                "grid": {
                    "top": 40,
                    "bottom": 30,
                    "left": 50,
                    "right": 20,
                },
                "series": [
                    {
                        "name": "Periphery Worker",
                        "type": "line",
                        "data": [],
                        "lineStyle": {"color": self.PW_COLOR},
                        "itemStyle": {"color": self.PW_COLOR},
                    },
                    {
                        "name": "Comprador",
                        "type": "line",
                        "data": [],
                        "lineStyle": {"color": self.PC_COLOR},
                        "itemStyle": {"color": self.PC_COLOR},
                    },
                    {
                        "name": "Core Bourgeoisie",
                        "type": "line",
                        "data": [],
                        "lineStyle": {"color": self.CB_COLOR},
                        "itemStyle": {"color": self.CB_COLOR},
                    },
                    {
                        "name": "Labor Aristocracy",
                        "type": "line",
                        "data": [],
                        "lineStyle": {"color": self.CW_COLOR},
                        "itemStyle": {"color": self.CW_COLOR},
                    },
                ],
            }
        ).classes("w-full h-full min-h-0")

    def push_data(
        self,
        tick: int,
        p_w_wealth: float,
        p_c_wealth: float,
        c_b_wealth: float,
        c_w_wealth: float,
    ) -> None:
        """Add wealth data for a new tick, maintaining rolling window.

        Args:
            tick: The simulation tick number.
            p_w_wealth: Periphery Worker (C001) wealth value.
            p_c_wealth: Comprador (C002) wealth value.
            c_b_wealth: Core Bourgeoisie (C003) wealth value.
            c_w_wealth: Labor Aristocracy (C004) wealth value.
        """
        # Append new data
        self._ticks.append(tick)
        self._pw_data.append(p_w_wealth)
        self._pc_data.append(p_c_wealth)
        self._cb_data.append(c_b_wealth)
        self._cw_data.append(c_w_wealth)

        # Enforce rolling window (max MAX_POINTS points)
        if len(self._ticks) > self.MAX_POINTS:
            self._ticks.pop(0)
            self._pw_data.pop(0)
            self._pc_data.pop(0)
            self._cb_data.pop(0)
            self._cw_data.pop(0)

        # Update EChart options
        self.echart.options["xAxis"]["data"] = self._ticks
        self.echart.options["series"][0]["data"] = self._pw_data
        self.echart.options["series"][1]["data"] = self._pc_data
        self.echart.options["series"][2]["data"] = self._cb_data
        self.echart.options["series"][3]["data"] = self._cw_data
        self.echart.update()


class EndgamePanel:
    """Game outcome display panel (Slice 1.6: Endgame Detection).

    The EndgamePanel displays the game outcome when the simulation terminates.
    It provides visual feedback for each outcome type with appropriate styling.

    Styling:
        Uses :class:`~babylon.ui.design_system.BunkerPalette` colors per outcome:

        - REVOLUTIONARY_VICTORY: ``TRIUMPH_GREEN`` (#39FF14), victory message
        - ECOLOGICAL_COLLAPSE: ``WARNING_AMBER`` (#B8860B), collapse message
        - FASCIST_CONSOLIDATION: ``PHOSPHOR_BURN_RED`` (#D40000), defeat message
        - IN_PROGRESS: Panel hidden (no display needed)

    The panel is initially hidden and becomes visible when display_outcome()
    is called with a non-IN_PROGRESS outcome.

    Attributes:
        OUTCOME_STYLES: Dict mapping GameOutcome to style configuration.
        is_visible: Boolean indicating if panel is currently visible.
        current_outcome: Current GameOutcome being displayed.
        current_message: Current message text being displayed.
        current_color: Current color being used for styling.
        title: Title element for "GAME OVER" header.
        outcome_label: Label showing the outcome type.
        message_element: Label showing the detailed outcome message.

    Example:
        >>> panel = EndgamePanel()
        >>> panel.is_visible
        False
        >>> panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)
        >>> panel.is_visible
        True
        >>> panel.current_color
        '#39FF14'

    See Also:
        :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`: Detects outcomes.
        :class:`~babylon.models.enums.GameOutcome`: Outcome enum values.
    """

    # Design System colors (from BunkerPalette)
    TRIUMPH_GREEN: str = BunkerPalette.TRIUMPH_GREEN
    WARNING_AMBER: str = BunkerPalette.WARNING_AMBER
    DANGER_RED: str = BunkerPalette.PHOSPHOR_BURN_RED
    VOID: str = BunkerPalette.VOID
    SILVER_DUST: str = BunkerPalette.SILVER_DUST

    # Outcome-specific styling configuration
    OUTCOME_STYLES: dict[GameOutcome, dict[str, str]] = {
        GameOutcome.REVOLUTIONARY_VICTORY: {
            "color": BunkerPalette.TRIUMPH_GREEN,
            "label": "REVOLUTIONARY VICTORY",
            "message": (
                "The workers have triumphed! Through solidarity and class consciousness, "
                "the masses have liberated themselves from the chains of capital. "
                "A new world is born."
            ),
        },
        GameOutcome.ECOLOGICAL_COLLAPSE: {
            "color": BunkerPalette.WARNING_AMBER,
            "label": "ECOLOGICAL COLLAPSE",
            "message": (
                "The metabolic rift has proven fatal. Capital's relentless extraction "
                "has pushed the planet beyond recovery. Ecological collapse has rendered "
                "all other struggles moot."
            ),
        },
        GameOutcome.FASCIST_CONSOLIDATION: {
            "color": BunkerPalette.PHOSPHOR_BURN_RED,
            "label": "FASCIST CONSOLIDATION",
            "message": (
                "Darkness has fallen. False consciousness has triumphed over class solidarity. "
                "The fascists have consolidated power, and the workers' movement has been defeated. "
                "History has taken a tragic turn."
            ),
        },
        GameOutcome.IN_PROGRESS: {
            "color": BunkerPalette.SILVER_DUST,
            "label": "IN PROGRESS",
            "message": "The struggle continues...",
        },
    }

    def __init__(self) -> None:
        """Initialize EndgamePanel with hidden state."""
        self._is_visible: bool = False
        self._current_outcome: GameOutcome = GameOutcome.IN_PROGRESS
        self._current_message: str = ""
        self._current_color: str = self.SILVER_DUST

        # UI elements (initialized in _build_ui)
        self._container: Any = None
        self.title: Any = None
        self.outcome_label: Any = None
        self.message_element: Any = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the UI elements."""
        # Full-screen overlay container
        with ui.element("div").classes("hidden") as container:
            self._container = container
            # Center the content using nested context managers
            column = (
                ui.column()
                .classes("w-full h-full items-center justify-center")
                .style(f"background: {self.VOID}; min-height: 100vh;")
            )
            card = (
                ui.card()
                .classes("p-8 text-center max-w-2xl")
                .style(f"background: {self.VOID}; border: 2px solid {self.SILVER_DUST};")
            )
            with column, card:  # noqa: SIM117
                self.title = (
                    ui.label("GAME OVER")
                    .classes("text-4xl font-bold mb-4")
                    .style(f"color: {self.SILVER_DUST};")
                )

                self.outcome_label = (
                    ui.label("")
                    .classes("text-2xl font-bold mb-6")
                    .style(f"color: {self._current_color};")
                )

                self.message_element = (
                    ui.label("")
                    .classes("text-lg leading-relaxed")
                    .style(f"color: {self.SILVER_DUST};")
                )

    @property
    def is_visible(self) -> bool:
        """Return True if panel is currently visible.

        Returns:
            Boolean indicating visibility state.
        """
        return self._is_visible

    @property
    def current_outcome(self) -> GameOutcome:
        """Return current outcome being displayed.

        Returns:
            GameOutcome enum value.
        """
        return self._current_outcome

    @property
    def current_message(self) -> str:
        """Return current message text.

        Returns:
            String message for the current outcome.
        """
        return self._current_message

    @property
    def current_color(self) -> str:
        """Return current color being used.

        Returns:
            Hex color string for the current outcome.
        """
        return self._current_color

    def display_outcome(self, outcome: GameOutcome) -> None:
        """Update panel to show the specified outcome.

        If outcome is IN_PROGRESS, the panel is hidden.
        Otherwise, the panel becomes visible with outcome-specific styling.

        Args:
            outcome: GameOutcome to display.
        """
        self._current_outcome = outcome

        if outcome == GameOutcome.IN_PROGRESS:
            self.hide()
            return

        # Get styling for this outcome
        style = self.OUTCOME_STYLES.get(outcome, self.OUTCOME_STYLES[GameOutcome.IN_PROGRESS])
        self._current_color = style["color"]
        self._current_message = style["message"]

        # Update UI elements
        self.outcome_label.set_text(style["label"])
        self.outcome_label.style(f"color: {self._current_color};")

        self.message_element.set_text(self._current_message)

        # Show the panel
        self.show()

    def get_style_for_outcome(self, outcome: GameOutcome) -> str:
        """Get the color style string for a specific outcome.

        Args:
            outcome: GameOutcome to get style for.

        Returns:
            Hex color string for the outcome.
        """
        style = self.OUTCOME_STYLES.get(outcome, self.OUTCOME_STYLES[GameOutcome.IN_PROGRESS])
        return style["color"]

    def show(self) -> None:
        """Make the panel visible."""
        self._is_visible = True
        self._container.classes(remove="hidden")

    def hide(self) -> None:
        """Hide the panel."""
        self._is_visible = False
        self._container.classes(add="hidden")

    def reset(self) -> None:
        """Reset panel to initial state.

        Hides the panel and sets outcome to IN_PROGRESS.
        Useful for starting a new game without recreating the panel.
        """
        self._current_outcome = GameOutcome.IN_PROGRESS
        self._current_message = ""
        self._current_color = self.SILVER_DUST
        self.hide()
