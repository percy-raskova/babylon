"""Dear PyGui dashboard runner for Babylon simulation.

This module provides a native GPU-accelerated desktop interface for the
Babylon simulation engine using Dear PyGui. The dashboard displays:

- Narrative Feed: Scrolling log of simulation narratives
- Telemetry: Time-series plots of Imperial Rent and Labor Aristocracy stability
- Controls: STEP, PLAY, PAUSE, RESET buttons

The interface uses the "Cockpit" metaphor - a dark-mode engineering dashboard
suitable for observing the simulation's evolution.

Example:
    Run the dashboard from command line::

        poetry run python -m babylon.ui.dpg_runner

    Or via mise::

        mise run ui
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import dearpygui.dearpygui as dpg  # type: ignore[import-not-found]

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import MockLLM
from babylon.engine.observers import MetricsCollector
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation import Simulation
from babylon.engine.topology_monitor import TopologyMonitor
from babylon.models.enums import EventType
from babylon.ui.design_system import DPGColors
from babylon.utils.recorder import SessionRecorder

if TYPE_CHECKING:
    pass


# =============================================================================
# CONSTANTS
# =============================================================================

TICK_INTERVAL: float = 1.0  # seconds between ticks in PLAY mode
ROLLING_WINDOW: int = 50  # number of data points to keep in plots

# Phase state colors (percolation theory)
PHASE_COLORS: dict[str, tuple[int, int, int, int]] = {
    "gaseous": DPGColors.SILVER_DUST,  # Atomized, weak solidarity
    "transitional": DPGColors.EXPOSED_COPPER,  # In flux
    "liquid": DPGColors.DATA_GREEN,  # Organized, strong solidarity
    "solid": DPGColors.ROYAL_BLUE,  # Crystallized class consciousness
}

# Event type colors for Event Log
EVENT_TYPE_COLORS: dict[EventType, tuple[int, int, int, int]] = {
    EventType.SURPLUS_EXTRACTION: DPGColors.EXPOSED_COPPER,
    EventType.IMPERIAL_SUBSIDY: DPGColors.EXPOSED_COPPER,
    EventType.ECONOMIC_CRISIS: DPGColors.WARNING_AMBER,
    EventType.EXCESSIVE_FORCE: DPGColors.PHOSPHOR_RED,
    EventType.UPRISING: DPGColors.PHOSPHOR_RED,
    EventType.RUPTURE: DPGColors.PHOSPHOR_RED,
    EventType.SOLIDARITY_SPIKE: DPGColors.GROW_PURPLE,
    EventType.SOLIDARITY_AWAKENING: DPGColors.GROW_PURPLE,
    EventType.CONSCIOUSNESS_TRANSMISSION: DPGColors.DATA_GREEN,
    EventType.MASS_AWAKENING: DPGColors.DATA_GREEN,
    EventType.PHASE_TRANSITION: DPGColors.ROYAL_BLUE,
    EventType.ECOLOGICAL_OVERSHOOT: DPGColors.WARNING_AMBER,
    EventType.ENDGAME_REACHED: DPGColors.SILVER_DUST,
}

# Wealth trend colors per class
WEALTH_COLORS: dict[str, tuple[int, int, int, int]] = {
    "p_w": DPGColors.DATA_GREEN,  # Periphery Worker (exploited)
    "p_c": DPGColors.EXPOSED_COPPER,  # Comprador
    "c_b": DPGColors.PHOSPHOR_RED,  # Core Bourgeoisie (exploiter)
    "c_w": DPGColors.ROYAL_BLUE,  # Labor Aristocracy
}


# =============================================================================
# STATE MANAGEMENT
# =============================================================================


@dataclass
class DashboardState:
    """Encapsulates all mutable dashboard state.

    This class holds the simulation instance, UI state flags, and time-series
    data for plots. Using a dataclass ensures all state is centralized and
    avoids module-level globals.

    Attributes:
        simulation: The active Simulation instance.
        simulation_running: Whether the simulation is in PLAY mode.
        tick: Current simulation tick.
        last_tick_time: Timestamp of the last tick execution.
        last_narrative_idx: Index for polling new narratives.
        rent_data_x: X-axis data for Imperial Rent plot (tick numbers).
        rent_data_y: Y-axis data for Imperial Rent plot (rent values).
        la_data_x: X-axis data for LA Stability plot (tick numbers).
        la_data_y: Y-axis data for LA Stability plot (P(S|A) values).
    """

    simulation: Simulation | None = None
    simulation_running: bool = False
    tick: int = 0
    last_tick_time: float = 0.0
    last_narrative_idx: int = 0

    # Time series data for plots
    rent_data_x: list[float] = field(default_factory=list)
    rent_data_y: list[float] = field(default_factory=list)
    la_data_x: list[float] = field(default_factory=list)
    la_data_y: list[float] = field(default_factory=list)

    # Wealth trend data (4 classes)
    pw_wealth_x: list[float] = field(default_factory=list)
    pw_wealth_y: list[float] = field(default_factory=list)
    pc_wealth_x: list[float] = field(default_factory=list)
    pc_wealth_y: list[float] = field(default_factory=list)
    cb_wealth_x: list[float] = field(default_factory=list)
    cb_wealth_y: list[float] = field(default_factory=list)
    cw_wealth_x: list[float] = field(default_factory=list)
    cw_wealth_y: list[float] = field(default_factory=list)

    # Event log tracking
    last_event_idx: int = 0


# Global state instance (initialized in main())
_state: DashboardState | None = None


def get_state() -> DashboardState:
    """Get the global dashboard state instance.

    Returns:
        The current DashboardState instance.

    Raises:
        RuntimeError: If state has not been initialized.
    """
    if _state is None:
        raise RuntimeError("Dashboard state not initialized. Call main() first.")
    return _state


# =============================================================================
# SIMULATION FACTORY
# =============================================================================


def create_simulation() -> Simulation:
    """Create a fresh simulation with observers.

    Creates a new Simulation instance with MetricsCollector, NarrativeDirector,
    and TopologyMonitor observers attached. Uses the Imperial Circuit scenario
    as the initial state.

    Returns:
        A configured Simulation instance ready for stepping.
    """
    initial_state, config, defines = create_imperial_circuit_scenario()
    metrics = MetricsCollector(mode="interactive", rolling_window=ROLLING_WINDOW)

    # MockLLM for narrative generation (offline MVP, no API costs)
    llm = MockLLM(
        responses=[
            ">>> TRANSMISSION <<<\nWorkers organize against exploitation.",
            "Authorities maintain order during civil disturbance.",
            ">>> SIGNAL <<<\nSolidarity networks strengthen across sectors.",
            "Economic indicators show market confidence recovering.",
            ">>> BROADCAST <<<\nMass mobilization detected in industrial zones.",
        ]
    )
    narrative = NarrativeDirector(use_llm=True, llm=llm)

    # Session recorder for black box debugging
    recorder = SessionRecorder(
        metrics_collector=metrics,
        narrative_director=narrative,
    )

    topology = TopologyMonitor(resilience_test_interval=5)
    return Simulation(
        initial_state, config, observers=[metrics, recorder, narrative, topology], defines=defines
    )


# =============================================================================
# UI HELPERS
# =============================================================================


def _create_series_theme(color: tuple[int, int, int, int]) -> int:
    """Create a DPG theme for a line series with specified color.

    Args:
        color: RGBA tuple for the line color.

    Returns:
        DPG theme ID to bind to a line series.
    """
    theme: int = dpg.add_theme()
    component = dpg.add_theme_component(dpg.mvLineSeries, parent=theme)
    dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots, parent=component)
    return theme


# =============================================================================
# UI BUILDERS
# =============================================================================


def build_narrative_feed(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Narrative Feed window.

    Creates a scrollable child window that displays narrative log entries
    as they are generated by the NarrativeDirector observer.

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(
        label="Narrative Feed", tag="narrative_window", width=width, height=height, pos=pos
    )
    dpg.add_child_window(
        tag="narrative_scroll",
        autosize_x=True,
        autosize_y=True,
        horizontal_scrollbar=True,
        parent="narrative_window",
    )
    dpg.add_text(
        "Waiting for simulation events...", tag="narrative_placeholder", parent="narrative_scroll"
    )


def build_telemetry_panel(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Telemetry window with plots.

    Creates two time-series plots:
    1. Imperial Rent over time
    2. Labor Aristocracy Stability (P(S|A)) over time

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(label="Telemetry", tag="telemetry_window", width=width, height=height, pos=pos)

    # Calculate plot height to fit two plots with spacing
    plot_height = (height - 80) // 2

    # Plot 1: Imperial Rent
    dpg.add_plot(
        label="Imperial Rent",
        height=plot_height,
        width=-1,
        tag="rent_plot",
        parent="telemetry_window",
    )
    dpg.add_plot_legend(parent="rent_plot")
    dpg.add_plot_axis(dpg.mvXAxis, label="Tick", tag="rent_x", parent="rent_plot")
    dpg.add_plot_axis(dpg.mvYAxis, label="Rent", tag="rent_y", parent="rent_plot")
    dpg.add_line_series([], [], label="Imperial Rent", tag="rent_series", parent="rent_y")

    dpg.add_spacer(height=10, parent="telemetry_window")

    # Plot 2: Labor Aristocracy Stability
    dpg.add_plot(
        label="LA Stability",
        height=plot_height,
        width=-1,
        tag="la_plot",
        parent="telemetry_window",
    )
    dpg.add_plot_legend(parent="la_plot")
    dpg.add_plot_axis(dpg.mvXAxis, label="Tick", tag="la_x", parent="la_plot")
    dpg.add_plot_axis(dpg.mvYAxis, label="P(S|A)", tag="la_y", parent="la_plot")
    dpg.add_line_series([], [], label="Stability", tag="la_series", parent="la_y")


def build_control_panel(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Control panel with simulation buttons.

    Creates STEP, PLAY, PAUSE, RESET buttons and a tick counter display.

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(
        label="Controls",
        tag="control_window",
        width=width,
        height=height,
        pos=pos,
        no_close=True,
    )
    dpg.add_group(horizontal=True, parent="control_window", tag="control_group")
    dpg.add_button(label="STEP", callback=on_step, tag="btn_step", width=70, parent="control_group")
    dpg.add_button(label="PLAY", callback=on_play, tag="btn_play", width=70, parent="control_group")
    dpg.add_button(
        label="PAUSE", callback=on_pause, tag="btn_pause", width=70, parent="control_group"
    )
    dpg.add_button(
        label="RESET", callback=on_reset, tag="btn_reset", width=70, parent="control_group"
    )
    dpg.add_spacer(width=20, parent="control_group")
    dpg.add_button(
        label="EXPORT",
        callback=on_export_logs,
        tag="btn_export",
        width=70,
        parent="control_group",
    )
    dpg.add_spacer(width=20, parent="control_group")
    dpg.add_text("TICK: 0", tag="tick_display", color=DPGColors.DATA_GREEN, parent="control_group")


def build_status_bar(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Status Bar window.

    Displays phase state, pool ratio, and bifurcation trend.
    The status bar provides at-a-glance system state information.

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(
        label="Status",
        tag="status_window",
        width=width,
        height=height,
        pos=pos,
        no_close=True,
    )
    dpg.add_group(horizontal=True, parent="status_window", tag="status_group")
    dpg.add_text("PHASE: ", color=DPGColors.SILVER_DUST, parent="status_group")
    dpg.add_text(
        "GASEOUS (0.00)", tag="phase_display", color=DPGColors.SILVER_DUST, parent="status_group"
    )
    dpg.add_spacer(width=40, parent="status_group")
    dpg.add_text("POOL: ", color=DPGColors.SILVER_DUST, parent="status_group")
    dpg.add_text(
        "0.00", tag="pool_ratio_display", color=DPGColors.DATA_GREEN, parent="status_group"
    )
    dpg.add_spacer(width=40, parent="status_group")
    dpg.add_text("TREND: ", color=DPGColors.SILVER_DUST, parent="status_group")
    dpg.add_text("STABLE", tag="trend_display", color=DPGColors.SILVER_DUST, parent="status_group")


def build_event_log(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Event Log window.

    Displays typed simulation events with color coding by EventType.
    Events are shown in a scrollable list with newest at the bottom.

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(label="Event Log", tag="event_log_window", width=width, height=height, pos=pos)
    dpg.add_child_window(
        tag="event_scroll",
        autosize_x=True,
        autosize_y=True,
        horizontal_scrollbar=True,
        parent="event_log_window",
    )
    dpg.add_text(
        "Waiting for events...",
        tag="event_placeholder",
        color=DPGColors.SILVER_DUST,
        parent="event_scroll",
    )


def build_wealth_trend_panel(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Wealth Trend panel with 4-line plot.

    Displays wealth over time for all four social classes:
    P_w (Periphery Worker), P_c (Comprador), C_b (Core Bourgeoisie), C_w (Labor Aristocracy).

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(label="Wealth Trend", tag="wealth_window", width=width, height=height, pos=pos)
    dpg.add_plot(
        label="Class Wealth", height=-1, width=-1, tag="wealth_plot", parent="wealth_window"
    )
    dpg.add_plot_legend(parent="wealth_plot")
    dpg.add_plot_axis(dpg.mvXAxis, label="Tick", tag="wealth_x", parent="wealth_plot")
    dpg.add_plot_axis(dpg.mvYAxis, label="Wealth", tag="wealth_y", parent="wealth_plot")

    # Create line series with explicit colors from WEALTH_COLORS
    dpg.add_line_series([], [], label="P_w (Worker)", tag="pw_series", parent="wealth_y")
    dpg.bind_item_theme("pw_series", _create_series_theme(WEALTH_COLORS["p_w"]))

    dpg.add_line_series([], [], label="P_c (Comprador)", tag="pc_series", parent="wealth_y")
    dpg.bind_item_theme("pc_series", _create_series_theme(WEALTH_COLORS["p_c"]))

    dpg.add_line_series([], [], label="C_b (Bourgeoisie)", tag="cb_series", parent="wealth_y")
    dpg.bind_item_theme("cb_series", _create_series_theme(WEALTH_COLORS["c_b"]))

    dpg.add_line_series([], [], label="C_w (Labor Arist.)", tag="cw_series", parent="wealth_y")
    dpg.bind_item_theme("cw_series", _create_series_theme(WEALTH_COLORS["c_w"]))


def build_key_metrics_panel(pos: tuple[int, int], width: int, height: int) -> None:
    """Build the Key Metrics panel.

    Displays key simulation metrics as text values:
    - Consciousness Gap
    - Wealth Gap
    - Global Tension
    - Pool Ratio
    - Repression Level

    Args:
        pos: (x, y) position for the window.
        width: Window width in pixels.
        height: Window height in pixels.
    """
    dpg.add_window(
        label="Key Metrics",
        tag="metrics_window",
        width=width,
        height=height,
        pos=pos,
        no_close=True,
    )
    dpg.add_text("Consciousness Gap:", color=DPGColors.SILVER_DUST, parent="metrics_window")
    dpg.add_text(
        "0.00", tag="consciousness_gap_value", color=DPGColors.DATA_GREEN, parent="metrics_window"
    )
    dpg.add_spacer(height=5, parent="metrics_window")
    dpg.add_text("Wealth Gap:", color=DPGColors.SILVER_DUST, parent="metrics_window")
    dpg.add_text(
        "0.00", tag="wealth_gap_value", color=DPGColors.EXPOSED_COPPER, parent="metrics_window"
    )
    dpg.add_spacer(height=5, parent="metrics_window")
    dpg.add_text("Global Tension:", color=DPGColors.SILVER_DUST, parent="metrics_window")
    dpg.add_text(
        "0.00", tag="tension_value", color=DPGColors.WARNING_AMBER, parent="metrics_window"
    )
    dpg.add_spacer(height=5, parent="metrics_window")
    dpg.add_text("Pool Ratio:", color=DPGColors.SILVER_DUST, parent="metrics_window")
    dpg.add_text(
        "0.00", tag="pool_ratio_value", color=DPGColors.ROYAL_BLUE, parent="metrics_window"
    )
    dpg.add_spacer(height=5, parent="metrics_window")
    dpg.add_text("Repression:", color=DPGColors.SILVER_DUST, parent="metrics_window")
    dpg.add_text(
        "0.00", tag="repression_value", color=DPGColors.PHOSPHOR_RED, parent="metrics_window"
    )


# =============================================================================
# CALLBACKS
# =============================================================================


def on_step() -> None:
    """Handle STEP button click.

    Executes a single simulation tick and updates the UI.
    """
    state = get_state()
    if state.simulation is None:
        return

    try:
        state.simulation.step()
        state.tick = state.simulation.current_state.tick
        update_all_ui()
    except Exception as e:
        log_to_narrative(f"[ERROR] {type(e).__name__}: {e}", DPGColors.PHOSPHOR_RED)


def on_play() -> None:
    """Handle PLAY button click.

    Sets the simulation to continuous running mode (1 tick/second).
    """
    state = get_state()
    state.simulation_running = True
    state.last_tick_time = time.time()


def on_pause() -> None:
    """Handle PAUSE button click.

    Stops the continuous simulation mode.
    """
    state = get_state()
    state.simulation_running = False


def on_reset() -> None:
    """Handle RESET button click.

    Creates a fresh simulation and clears all UI state.
    """
    state = get_state()
    state.simulation_running = False
    state.simulation = create_simulation()
    state.tick = 0
    state.last_narrative_idx = 0
    state.last_event_idx = 0

    # Clear time series data
    state.rent_data_x.clear()
    state.rent_data_y.clear()
    state.la_data_x.clear()
    state.la_data_y.clear()

    # Clear wealth trend data
    state.pw_wealth_x.clear()
    state.pw_wealth_y.clear()
    state.pc_wealth_x.clear()
    state.pc_wealth_y.clear()
    state.cb_wealth_x.clear()
    state.cb_wealth_y.clear()
    state.cw_wealth_x.clear()
    state.cw_wealth_y.clear()

    # Update plots with empty data
    dpg.set_value("rent_series", [[], []])
    dpg.set_value("la_series", [[], []])
    dpg.set_value("pw_series", [[], []])
    dpg.set_value("pc_series", [[], []])
    dpg.set_value("cb_series", [[], []])
    dpg.set_value("cw_series", [[], []])

    # Reset tick display
    dpg.set_value("tick_display", "TICK: 0")

    # Reset status bar
    dpg.set_value("phase_display", "GASEOUS (0.00)")
    dpg.set_value("pool_ratio_display", "0.00")
    dpg.set_value("trend_display", "STABLE")

    # Reset key metrics
    dpg.set_value("consciousness_gap_value", "0.00")
    dpg.set_value("wealth_gap_value", "0.00")
    dpg.set_value("tension_value", "0.00")
    dpg.set_value("pool_ratio_value", "0.00")
    dpg.set_value("repression_value", "0.00")

    # Clear narrative feed
    if dpg.does_item_exist("narrative_scroll"):
        children = dpg.get_item_children("narrative_scroll", 1)
        if children:
            for child in children:
                dpg.delete_item(child)
        dpg.add_text(
            "Simulation reset. Waiting for events...",
            parent="narrative_scroll",
            color=DPGColors.SILVER_DUST,
        )

    # Clear event log
    if dpg.does_item_exist("event_scroll"):
        children = dpg.get_item_children("event_scroll", 1)
        if children:
            for child in children:
                dpg.delete_item(child)
        dpg.add_text(
            "Waiting for events...",
            parent="event_scroll",
            tag="event_placeholder",
            color=DPGColors.SILVER_DUST,
        )


def on_export_logs() -> None:
    """Handle EXPORT LOGS button click.

    Finds the SessionRecorder observer and exports the session data
    to a ZIP archive for debugging and sharing.
    """
    state = get_state()
    if state.simulation is None:
        log_to_narrative("No simulation running", DPGColors.WARNING_AMBER)
        return

    # Find SessionRecorder in observers
    recorder = None
    for observer in state.simulation._observers:
        if hasattr(observer, "export_package"):
            recorder = observer
            break

    if recorder is None:
        log_to_narrative("No recorder found", DPGColors.WARNING_AMBER)
        return

    try:
        zip_path = recorder.export_package()
        log_to_narrative(f"Debug logs exported to: {zip_path}", DPGColors.DATA_GREEN)
        # Show modal with path
        dpg.set_value("export_path_text", str(zip_path))
        dpg.configure_item("export_modal", show=True)
    except Exception as e:
        log_to_narrative(f"[ERROR] Export failed: {e}", DPGColors.PHOSPHOR_RED)


# =============================================================================
# UI UPDATE FUNCTIONS
# =============================================================================


def log_to_narrative(message: str, color: tuple[int, int, int, int] | None = None) -> None:
    """Add a message to the narrative feed.

    Args:
        message: The text to display.
        color: RGBA color tuple (default: DATA_GREEN).
    """
    if color is None:
        color = DPGColors.DATA_GREEN

    # Remove placeholder if it exists
    if dpg.does_item_exist("narrative_placeholder"):
        dpg.delete_item("narrative_placeholder")

    dpg.add_text(message, parent="narrative_scroll", color=color, wrap=340)

    # Auto-scroll to bottom
    dpg.set_y_scroll("narrative_scroll", dpg.get_y_scroll_max("narrative_scroll"))


def update_telemetry() -> None:
    """Update telemetry plots with latest metrics.

    Pulls data from MetricsCollector and updates the Imperial Rent and
    LA Stability plots.
    """
    state = get_state()
    if state.simulation is None:
        return

    # Find MetricsCollector observer
    metrics_collector = None
    for observer in state.simulation._observers:
        if isinstance(observer, MetricsCollector):
            metrics_collector = observer
            break

    if metrics_collector is None or metrics_collector.latest is None:
        return

    tick_metrics = metrics_collector.latest

    # Update Imperial Rent data
    state.rent_data_x.append(float(tick_metrics.tick))
    state.rent_data_y.append(float(tick_metrics.imperial_rent_pool))

    # Get Labor Aristocracy (C004/c_w) acquiescence probability
    # TickMetrics has p_w, p_c, c_b, c_w for the 4 entity types
    p_acquiescence = 0.0
    if tick_metrics.c_w is not None:
        p_acquiescence = float(tick_metrics.c_w.p_acquiescence)
    state.la_data_x.append(float(tick_metrics.tick))
    state.la_data_y.append(p_acquiescence)

    # Keep only last ROLLING_WINDOW points
    if len(state.rent_data_x) > ROLLING_WINDOW:
        state.rent_data_x = state.rent_data_x[-ROLLING_WINDOW:]
        state.rent_data_y = state.rent_data_y[-ROLLING_WINDOW:]
        state.la_data_x = state.la_data_x[-ROLLING_WINDOW:]
        state.la_data_y = state.la_data_y[-ROLLING_WINDOW:]

    # Update plot series
    dpg.set_value("rent_series", [state.rent_data_x, state.rent_data_y])
    dpg.set_value("la_series", [state.la_data_x, state.la_data_y])

    # Auto-fit axes
    dpg.fit_axis_data("rent_x")
    dpg.fit_axis_data("rent_y")
    dpg.fit_axis_data("la_x")
    dpg.fit_axis_data("la_y")


def update_narrative_feed() -> None:
    """Poll NarrativeDirector for new narratives.

    Fetches any new narrative log entries since the last poll and
    displays them in the narrative feed.
    """
    state = get_state()
    if state.simulation is None:
        return

    # Find NarrativeDirector observer
    narrative_director = None
    for observer in state.simulation._observers:
        if isinstance(observer, NarrativeDirector):
            narrative_director = observer
            break

    if narrative_director is None:
        return

    # Poll for new narratives
    narrative_log = narrative_director.narrative_log
    for idx in range(state.last_narrative_idx, len(narrative_log)):
        entry = narrative_log[idx]
        log_to_narrative(entry, DPGColors.GROW_PURPLE)

    state.last_narrative_idx = len(narrative_log)


def update_tick_display() -> None:
    """Update the tick counter display."""
    state = get_state()
    dpg.set_value("tick_display", f"TICK: {state.tick}")


def update_status_bar() -> None:
    """Update status bar with current phase and metrics.

    Fetches phase state from TopologyMonitor and pool ratio from MetricsCollector.
    """
    state = get_state()
    if state.simulation is None:
        return

    # Find TopologyMonitor for phase state
    topology_monitor = None
    for observer in state.simulation._observers:
        if isinstance(observer, TopologyMonitor):
            topology_monitor = observer
            break

    # Update phase display (phase is tracked internally by TopologyMonitor)
    if topology_monitor is not None and topology_monitor.history:
        latest = topology_monitor.history[-1]
        # Phase is stored in _previous_phase after each tick
        phase = topology_monitor._previous_phase or "gaseous"
        ratio = latest.percolation_ratio
        color = PHASE_COLORS.get(phase, DPGColors.SILVER_DUST)
        dpg.set_value("phase_display", f"{phase.upper()} ({ratio:.2f})")
        dpg.configure_item("phase_display", color=color)

        # Update trend based on bifurcation direction
        trend = "STABLE"
        if len(topology_monitor.history) >= 2:
            prev_ratio = topology_monitor.history[-2].percolation_ratio
            if ratio > prev_ratio + 0.01:
                trend = "RISING"
            elif ratio < prev_ratio - 0.01:
                trend = "FALLING"
        dpg.set_value("trend_display", trend)

    # Find MetricsCollector for pool ratio
    metrics_collector = None
    for observer in state.simulation._observers:
        if isinstance(observer, MetricsCollector):
            metrics_collector = observer
            break

    if metrics_collector is not None and metrics_collector.latest is not None:
        pool_ratio = float(metrics_collector.latest.pool_ratio)
        dpg.set_value("pool_ratio_display", f"{pool_ratio:.2f}")


def log_event(event_type: EventType, message: str) -> None:
    """Add an event to the event log with color coding.

    Args:
        event_type: The type of event for color selection.
        message: The text to display.
    """
    color = EVENT_TYPE_COLORS.get(event_type, DPGColors.SILVER_DUST)

    # Remove placeholder if it exists
    if dpg.does_item_exist("event_placeholder"):
        dpg.delete_item("event_placeholder")

    dpg.add_text(message, parent="event_scroll", color=color, wrap=340)

    # Auto-scroll to bottom
    dpg.set_y_scroll("event_scroll", dpg.get_y_scroll_max("event_scroll"))


def update_event_log() -> None:
    """Poll WorldState for new events and display them.

    Fetches simulation events since last poll and displays with color coding.
    """
    state = get_state()
    if state.simulation is None:
        return

    # Get current events from world state
    current_state = state.simulation.current_state
    events = current_state.events

    # Display new events since last check
    for idx in range(state.last_event_idx, len(events)):
        event = events[idx]
        # Format event type name for display (e.g., SURPLUS_EXTRACTION -> Surplus Extraction)
        event_name = event.event_type.name.replace("_", " ").title()
        msg = f"[T{event.tick}] {event_name}"
        log_event(event.event_type, msg)

    state.last_event_idx = len(events)


def update_wealth_trend() -> None:
    """Update wealth trend plot with latest class wealth data.

    Pulls wealth from EntityMetrics for all four classes and updates
    the 4-line plot.
    """
    state = get_state()
    if state.simulation is None:
        return

    # Find MetricsCollector observer
    metrics_collector = None
    for observer in state.simulation._observers:
        if isinstance(observer, MetricsCollector):
            metrics_collector = observer
            break

    if metrics_collector is None or metrics_collector.latest is None:
        return

    tick_metrics = metrics_collector.latest
    tick = float(tick_metrics.tick)

    # Extract wealth from entity metrics
    if tick_metrics.p_w is not None:
        state.pw_wealth_x.append(tick)
        state.pw_wealth_y.append(float(tick_metrics.p_w.wealth))
    if tick_metrics.p_c is not None:
        state.pc_wealth_x.append(tick)
        state.pc_wealth_y.append(float(tick_metrics.p_c.wealth))
    if tick_metrics.c_b is not None:
        state.cb_wealth_x.append(tick)
        state.cb_wealth_y.append(float(tick_metrics.c_b.wealth))
    if tick_metrics.c_w is not None:
        state.cw_wealth_x.append(tick)
        state.cw_wealth_y.append(float(tick_metrics.c_w.wealth))

    # Keep only last ROLLING_WINDOW points
    if len(state.pw_wealth_x) > ROLLING_WINDOW:
        state.pw_wealth_x = state.pw_wealth_x[-ROLLING_WINDOW:]
        state.pw_wealth_y = state.pw_wealth_y[-ROLLING_WINDOW:]
        state.pc_wealth_x = state.pc_wealth_x[-ROLLING_WINDOW:]
        state.pc_wealth_y = state.pc_wealth_y[-ROLLING_WINDOW:]
        state.cb_wealth_x = state.cb_wealth_x[-ROLLING_WINDOW:]
        state.cb_wealth_y = state.cb_wealth_y[-ROLLING_WINDOW:]
        state.cw_wealth_x = state.cw_wealth_x[-ROLLING_WINDOW:]
        state.cw_wealth_y = state.cw_wealth_y[-ROLLING_WINDOW:]

    # Update plot series
    dpg.set_value("pw_series", [state.pw_wealth_x, state.pw_wealth_y])
    dpg.set_value("pc_series", [state.pc_wealth_x, state.pc_wealth_y])
    dpg.set_value("cb_series", [state.cb_wealth_x, state.cb_wealth_y])
    dpg.set_value("cw_series", [state.cw_wealth_x, state.cw_wealth_y])

    # Auto-fit axes
    dpg.fit_axis_data("wealth_x")
    dpg.fit_axis_data("wealth_y")


def update_key_metrics() -> None:
    """Update key metrics panel with latest values.

    Displays consciousness_gap, wealth_gap, global_tension, pool_ratio,
    and current_repression_level from TickMetrics.
    """
    state = get_state()
    if state.simulation is None:
        return

    # Find MetricsCollector observer
    metrics_collector = None
    for observer in state.simulation._observers:
        if isinstance(observer, MetricsCollector):
            metrics_collector = observer
            break

    if metrics_collector is None or metrics_collector.latest is None:
        return

    tick_metrics = metrics_collector.latest

    # Update text values
    dpg.set_value("consciousness_gap_value", f"{tick_metrics.consciousness_gap:.3f}")
    dpg.set_value("wealth_gap_value", f"{tick_metrics.wealth_gap:.2f}")
    dpg.set_value("tension_value", f"{tick_metrics.global_tension:.3f}")
    dpg.set_value("pool_ratio_value", f"{tick_metrics.pool_ratio:.3f}")
    dpg.set_value("repression_value", f"{tick_metrics.current_repression_level:.3f}")


def update_all_ui() -> None:
    """Update all UI components after a simulation step."""
    update_tick_display()
    update_telemetry()
    update_narrative_feed()
    update_status_bar()
    update_event_log()
    update_wealth_trend()
    update_key_metrics()


# =============================================================================
# THEME SETUP
# =============================================================================


def setup_dark_theme() -> None:
    """Configure the dark theme for the dashboard.

    Applies Bunker Constructivism colors to the global DPG theme.
    """
    global_theme = dpg.add_theme()
    theme_component = dpg.add_theme_component(dpg.mvAll, parent=global_theme)

    # Window backgrounds
    dpg.add_theme_color(
        dpg.mvThemeCol_WindowBg,
        DPGColors.VOID,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    dpg.add_theme_color(
        dpg.mvThemeCol_ChildBg,
        DPGColors.WET_CONCRETE,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    # Frames
    dpg.add_theme_color(
        dpg.mvThemeCol_FrameBg,
        DPGColors.WET_CONCRETE,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    # Text
    dpg.add_theme_color(
        dpg.mvThemeCol_Text,
        DPGColors.SILVER_DUST,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    # Borders
    dpg.add_theme_color(
        dpg.mvThemeCol_Border,
        DPGColors.DARK_METAL,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    # Title bar
    dpg.add_theme_color(
        dpg.mvThemeCol_TitleBg,
        DPGColors.WET_CONCRETE,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    dpg.add_theme_color(
        dpg.mvThemeCol_TitleBgActive,
        DPGColors.DARK_METAL,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    # Buttons
    dpg.add_theme_color(
        dpg.mvThemeCol_Button,
        DPGColors.DARK_METAL,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    dpg.add_theme_color(
        dpg.mvThemeCol_ButtonHovered,
        DPGColors.WET_CONCRETE,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    dpg.add_theme_color(
        dpg.mvThemeCol_ButtonActive,
        (*DPGColors.DATA_GREEN[:3], 100),
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    # Scrollbar
    dpg.add_theme_color(
        dpg.mvThemeCol_ScrollbarBg,
        DPGColors.VOID,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )
    dpg.add_theme_color(
        dpg.mvThemeCol_ScrollbarGrab,
        DPGColors.DARK_METAL,
        category=dpg.mvThemeCat_Core,
        parent=theme_component,
    )

    dpg.bind_theme(global_theme)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main() -> None:
    """Run the Dear PyGui dashboard.

    This is the main entry point for the Babylon dashboard. It:
    1. Initializes DPG context
    2. Creates the simulation with observers
    3. Builds the UI layout
    4. Runs the main render loop with 1 tick/second timing
    5. Cleans up on exit
    """
    global _state

    # Initialize state
    _state = DashboardState()

    # Create DPG context
    dpg.create_context()

    # Create simulation
    _state.simulation = create_simulation()

    # Setup theme before creating windows
    setup_dark_theme()

    # ==========================================================================
    # LAYOUT CONFIGURATION
    # ==========================================================================
    # Layout pattern from reference screenshot:
    # - Left column: Wealth Trend (top), Telemetry (bottom)
    # - Right column: Status + Controls (top row), Narrative Feed + Key Metrics
    #   (middle), Event Log (bottom)
    #
    # Viewport: 1460w x 820h (matching screenshot proportions)
    # Left column: ~500px wide
    # Right column: ~960px wide starting at x=500
    # ==========================================================================

    viewport_w, viewport_h = 1460, 820
    left_col_w = 500
    right_col_x = left_col_w
    gap = 5  # Small gap between windows

    # Left column dimensions
    wealth_h = 460
    telemetry_h = viewport_h - wealth_h - gap

    # Right column top row (Status + Controls)
    top_row_h = 80
    status_w = 400
    controls_w = 400

    # Right column middle (Narrative Feed + Key Metrics)
    middle_y = top_row_h + gap
    metrics_w = 220
    narrative_w = right_col_x + (viewport_w - right_col_x) - metrics_w - gap
    narrative_h = 450

    # Right column bottom (Event Log)
    event_y = middle_y + narrative_h + gap
    event_h = viewport_h - event_y - gap

    # Build UI windows with explicit positions
    # Left column
    build_wealth_trend_panel(pos=(0, 0), width=left_col_w, height=wealth_h)
    build_telemetry_panel(pos=(0, wealth_h + gap), width=left_col_w, height=telemetry_h)

    # Right column - top row
    build_status_bar(pos=(right_col_x, 0), width=status_w, height=top_row_h)
    build_control_panel(pos=(right_col_x + status_w + gap, 0), width=controls_w, height=top_row_h)

    # Right column - middle row
    build_narrative_feed(pos=(right_col_x, middle_y), width=narrative_w, height=narrative_h)
    build_key_metrics_panel(
        pos=(right_col_x + narrative_w + gap, middle_y), width=metrics_w, height=narrative_h
    )

    # Right column - bottom row
    build_event_log(pos=(right_col_x, event_y), width=narrative_w + metrics_w + gap, height=event_h)

    # Export confirmation modal
    with dpg.window(
        label="Export Complete",
        modal=True,
        show=False,
        tag="export_modal",
        width=500,
        height=120,
        pos=(viewport_w // 2 - 250, viewport_h // 2 - 60),
        no_close=True,
    ):
        dpg.add_text("Debug logs exported to:", color=DPGColors.SILVER_DUST)
        dpg.add_text("", tag="export_path_text", color=DPGColors.DATA_GREEN, wrap=480)
        dpg.add_spacer(height=10)
        dpg.add_button(
            label="OK",
            width=100,
            callback=lambda: dpg.configure_item("export_modal", show=False),
        )

    # Create viewport
    dpg.create_viewport(title="Babylon Synopticon", width=viewport_w, height=viewport_h)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Main render loop
    while dpg.is_dearpygui_running():
        current_time = time.time()

        # Execute simulation tick if in PLAY mode and interval has elapsed
        if (
            _state.simulation_running
            and (current_time - _state.last_tick_time >= TICK_INTERVAL)
            and _state.simulation is not None
        ):
            try:
                _state.simulation.step()
                _state.tick = _state.simulation.current_state.tick
                _state.last_tick_time = current_time
                update_all_ui()
            except Exception as e:
                log_to_narrative(f"[ERROR] {type(e).__name__}: {e}", DPGColors.PHOSPHOR_RED)
                _state.simulation_running = False  # Auto-pause on error

        dpg.render_dearpygui_frame()

    # Cleanup
    if _state.simulation is not None:
        _state.simulation.end()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
