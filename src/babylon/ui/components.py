"""Reusable UI components for the Babylon simulation.

This module provides UI components that are used across the Babylon
dashboard, following the "Bunker Constructivism" design system.

Components:
    SystemLog: Raw event log with instant display (NO typewriter animation).
    TrendPlotter: Real-time EChart line graph for simulation metrics.
    StateInspector: JSON viewer for raw entity state inspection.
    WirePanel: Dual narrative display panel (The Gramscian Wire).

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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nicegui import ui

from babylon.models.events import SimulationEvent

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
    # h-full fills flex container; min-h-0 allows shrinking below content height
    CONTAINER_CLASSES = "bg-[#050505] border border-[#404040] p-4 w-full h-full min-h-0 overflow-auto font-mono text-sm"

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
            ui.label(text).classes(f"text-[{color}] break-all")

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
    # h-full fills flex container; min-h-0 allows shrinking below content height
    CONTAINER_CLASSES = (
        "bg-[#050505] border border-[#404040] p-2 w-full h-full min-h-0 overflow-auto"
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

    Styling (from ai-docs/design-system.yaml):
        - Background: void (#050505)
        - Border: dark_metal (#404040)
        - Labels: silver_dust (#C0C0C0)
        - Healthy values: data_green (#39FF14)
        - Critical values: phosphor_burn_red (#D40000)

    Args:
        title: Optional title displayed on the gauge.
        value: Initial value to display. Defaults to 0.
        max_value: Maximum value for the gauge range. Defaults to 1.0.
        threshold: Optional threshold for color change. Values at or above
            threshold display in red; values below display in green.

    Example:
        >>> gauge = GaugePanel(title="Overshoot", max_value=2.0, threshold=1.0)
        >>> gauge.update(0.75)  # Green - below threshold
        >>> gauge.update(1.5)   # Red - above threshold
    """

    # Design System color palette (from ai-docs/design-system.yaml)
    VOID: str = "#050505"
    DARK_METAL: str = "#404040"
    SILVER_DUST: str = "#C0C0C0"
    DATA_GREEN: str = "#39FF14"
    PHOSPHOR_BURN_RED: str = "#D40000"

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

    Overshoot Ratio = Consumption / Biocapacity:
    - Ratio < 1.0: Sustainable (within planetary limits)
    - Ratio >= 1.0: Overshoot (ecological debt)

    Styling:
        - Sustainable (< 1.0): data_green (#39FF14)
        - Overshoot (>= 1.0): phosphor_burn_red (#D40000)

    Example:
        >>> gauge = MetabolicGauge()
        >>> gauge.refresh(overshoot_ratio=0.75)  # Green - sustainable
        >>> gauge.refresh(overshoot_ratio=1.5)   # Red - overshoot
    """

    # Design system colors
    SUSTAINABLE_COLOR: str = "#39FF14"
    OVERSHOOT_COLOR: str = "#D40000"

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

    Consciousness Gap = p_w.consciousness - c_w.consciousness:
    - Positive gap: Periphery Worker more class-conscious (revolutionary potential)
    - Negative gap: Labor Aristocracy more conscious (false consciousness dominant)
    - Zero gap: Ideological convergence (unusual equilibrium)

    Styling:
        - Positive (> 0): data_green (#39FF14) - revolutionary consciousness
        - Negative (< 0): phosphor_burn_red (#D40000) - false consciousness
        - Zero (= 0): silver_dust (#C0C0C0) - neutral/equilibrium

    Example:
        >>> gauge = ConsciousnessGapGauge()
        >>> gauge.refresh(consciousness_gap=0.3)   # Green - P_W more conscious
        >>> gauge.refresh(consciousness_gap=-0.2)  # Red - C_W more conscious
        >>> gauge.refresh(consciousness_gap=0.0)   # Silver - equilibrium
    """

    # Design system colors
    POSITIVE_COLOR: str = "#39FF14"  # data_green
    NEGATIVE_COLOR: str = "#D40000"  # phosphor_burn_red
    NEUTRAL_COLOR: str = "#C0C0C0"  # silver_dust

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
                "backgroundColor": "#050505",
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
                                "color": [[1, "#404040"]],
                            }
                        },
                        "splitLine": {
                            "length": 10,
                            "lineStyle": {"color": "#404040"},
                        },
                        "axisTick": {
                            "length": 5,
                            "lineStyle": {"color": "#404040"},
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
    - C001 (Periphery Worker): The exploited class
    - C002 (Comprador): Intermediary class
    - C003 (Core Bourgeoisie): The exploiter class
    - C004 (Labor Aristocracy): The bought-off class

    Maintains a rolling window of the last MAX_POINTS ticks.

    Styling (from ai-docs/design-system.yaml):
        - Background: void (#050505)
        - Axes/Grid: dark_metal (#404040)
        - Labels/Legend: silver_dust (#C0C0C0)
        - P_W line: grow_light_purple (#9D00FF)
        - P_C line: exposed_copper (#FFD700)
        - C_B line: goldenrod (#DAA520)
        - C_W line: royal_blue (#4169E1)

    Example:
        >>> panel = WealthTrendPanel()
        >>> panel.push_data(tick=1, p_w_wealth=100, p_c_wealth=200,
        ...                 c_b_wealth=500, c_w_wealth=150)
    """

    # Rolling window size
    MAX_POINTS: int = 50

    # Design System color palette
    VOID: str = "#050505"
    DARK_METAL: str = "#404040"
    SILVER_DUST: str = "#C0C0C0"

    # Class line colors
    PW_COLOR: str = "#39FF14"  # data_green - Periphery Worker (the carrier)
    PC_COLOR: str = "#FFD700"  # exposed_copper - Comprador
    CB_COLOR: str = "#D40000"  # phosphor_burn_red - Core Bourgeoisie (exploiter)
    CW_COLOR: str = "#4169E1"  # royal_blue - Labor Aristocracy

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
