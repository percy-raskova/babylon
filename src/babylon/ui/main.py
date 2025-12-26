"""Main Babylon UI application.

This module provides the entry point for the Babylon simulation UI,
implementing the 4-panel Synopticon dashboard layout:

- Left panel: TrendPlotter (Imperial Rent + Global Tension)
- Center top: NarrativeTerminal (typewriter animation)
- Center bottom: SystemLog (raw events, instant append)
- Right panel: StateInspector (JSON viewer for C001 entity)

Run with:
    python -m babylon.ui.main

Or:
    poetry run python src/babylon/ui/main.py
"""

from __future__ import annotations

from nicegui import ui

from babylon.engine.observer import SimulationObserver
from babylon.engine.observers.metrics import MetricsCollector
from babylon.engine.runner import AsyncSimulationRunner
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent
from babylon.models.world_state import WorldState
from babylon.ui.components import StateInspector, SystemLog, TrendPlotter
from babylon.ui.controls import ControlDeck
from babylon.ui.terminal import NarrativeTerminal, find_narrative_director, poll_narrative_director


class DashboardState:
    """Encapsulates all mutable state for the Babylon Developer Dashboard.

    This class manages simulation state, UI components, and tracking indices
    to avoid module-level mutable state that can cause issues with testing,
    concurrency, and state management.

    Attributes:
        simulation: The active Simulation instance.
        runner: AsyncSimulationRunner for non-blocking execution.
        control_deck: ControlDeck component for tick display and controls.
        terminal: NarrativeTerminal component for narrative display.
        last_narrative_index: Tracking index for narrative polling.
        system_log: SystemLog component for event logging.
        trend_plotter: TrendPlotter component for metrics visualization.
        state_inspector: StateInspector component for entity state display.
        last_event_index: Tracking index for event logging.
        metrics_collector: MetricsCollector observer for unified metrics.
    """

    def __init__(self) -> None:
        """Initialize DashboardState with all fields set to None or default values."""
        self.simulation: Simulation | None = None
        self.runner: AsyncSimulationRunner | None = None
        self.control_deck: ControlDeck | None = None
        self.terminal: NarrativeTerminal | None = None
        self.last_narrative_index: int = 0
        self.system_log: SystemLog | None = None
        self.trend_plotter: TrendPlotter | None = None
        self.state_inspector: StateInspector | None = None
        self.last_event_index: int = 0
        self.metrics_collector: MetricsCollector | None = None


# Module-level state instance
_state = DashboardState()


def __getattr__(name: str) -> object:
    """Provide module-level access to DashboardState attributes.

    This enables backward compatibility with tests that access module-level
    variables like `main.simulation`, `main.trend_plotter`, etc.

    Args:
        name: The attribute name to get.

    Returns:
        The attribute value from the _state instance.

    Raises:
        AttributeError: If the attribute doesn't exist on DashboardState.
    """
    if hasattr(_state, name):
        return getattr(_state, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def init_simulation() -> None:
    """Initialize or reset the simulation and runner."""
    scenario_state, config, defines = create_two_node_scenario()

    # Sprint 4.1: Create MetricsCollector in interactive mode with rolling window
    # matching TrendPlotter.MAX_POINTS for consistent visualization
    _state.metrics_collector = MetricsCollector(mode="interactive", rolling_window=50)

    _state.simulation = Simulation(
        scenario_state, config, observers=[_state.metrics_collector], defines=defines
    )
    _state.runner = AsyncSimulationRunner(_state.simulation, tick_interval=1.0)


async def on_step() -> None:
    """Handle STEP button click.

    Uses AsyncSimulationRunner.step_once() which internally uses asyncio.to_thread()
    to run simulation step in a background thread, preventing GUI freeze.
    """
    if _state.runner is not None:
        await _state.runner.step_once()
        refresh_ui()


async def on_play() -> None:
    """Handle PLAY button click.

    Starts the AsyncSimulationRunner background loop.
    """
    if _state.runner is not None:
        await _state.runner.start()


async def on_pause() -> None:
    """Handle PAUSE button click.

    Stops the AsyncSimulationRunner background loop.
    """
    if _state.runner is not None:
        await _state.runner.stop()


async def on_reset() -> None:
    """Handle RESET button click.

    Stops the runner, resets state indices, reinitializes simulation and runner.
    """
    if _state.runner is not None:
        await _state.runner.stop()
    _state.last_narrative_index = 0  # Reset narrative polling index
    _state.last_event_index = 0  # Reset event tracking index
    init_simulation()
    refresh_ui()


def _get_narrative_director() -> SimulationObserver | None:
    """Find the NarrativeDirector among simulation observers.

    Returns:
        The NarrativeDirector observer if found, None otherwise.
    """
    if _state.simulation is None:
        return None
    return find_narrative_director(_state.simulation.observers)


def _calculate_global_tension(state: WorldState) -> float:
    """Calculate average tension across all relationships.

    This metric provides a single-number summary of system-wide tension,
    useful for trend visualization and phase transition detection.

    Args:
        state: The current world state containing relationships.

    Returns:
        Average tension value (0.0 to 1.0), or 0.0 if no relationships.
    """
    if not state.relationships:
        return 0.0
    return sum(r.tension for r in state.relationships) / len(state.relationships)


def _event_to_log_level(event: SimulationEvent) -> str:
    """Map event type to log level for SystemLog display.

    Critical events (ECONOMIC_CRISIS, UPRISING, RUPTURE) map to ERROR.
    Warning events (EXCESSIVE_FORCE, IMPERIAL_SUBSIDY) map to WARN.
    All other events map to INFO.

    Args:
        event: The simulation event to classify.

    Returns:
        Log level string: "ERROR", "WARN", or "INFO".
    """
    critical_events = {
        EventType.ECONOMIC_CRISIS,
        EventType.UPRISING,
        EventType.RUPTURE,
    }
    warning_events = {
        EventType.EXCESSIVE_FORCE,
        EventType.IMPERIAL_SUBSIDY,
    }

    if event.event_type in critical_events:
        return "ERROR"
    elif event.event_type in warning_events:
        return "WARN"
    return "INFO"


def refresh_ui() -> None:
    """Update all Synopticon panels with current simulation state.

    This function pushes data to all four panels:

    1. ControlDeck: Update tick counter
    2. NarrativeTerminal: Poll NarrativeDirector for new narrative entries
    3. TrendPlotter: Push Imperial Rent and Global Tension metrics
    4. StateInspector: Update with C001 entity state
    5. SystemLog: Log new simulation events with appropriate severity levels
    """
    if _state.simulation is None:
        return

    sim_state = _state.simulation.current_state

    # 1. Update tick counter (existing)
    if _state.control_deck is not None:
        _state.control_deck.update_tick(sim_state.tick)

    # 2. Poll NarrativeDirector -> NarrativeTerminal (existing)
    if _state.terminal is not None:
        director = _get_narrative_director()
        if director is not None:
            new_entries, _state.last_narrative_index = poll_narrative_director(
                director, _state.last_narrative_index
            )
            for entry in new_entries:
                _state.terminal.log(entry)

    # 3. Push metrics -> TrendPlotter via MetricsCollector (Sprint 4.1)
    # Uses unified metrics collection instead of hardcoded extraction
    # Falls back to direct state access if collector hasn't received data yet
    if _state.trend_plotter is not None:
        if _state.metrics_collector is not None and _state.metrics_collector.latest is not None:
            latest = _state.metrics_collector.latest
            _state.trend_plotter.push_data(latest.tick, latest.imperial_rent_pool, latest.global_tension)
        else:
            # Fallback for initial render before first step
            rent = float(sim_state.economy.imperial_rent_pool)
            tension = _calculate_global_tension(sim_state)
            _state.trend_plotter.push_data(sim_state.tick, rent, tension)

    # 4. Update StateInspector with C001 entity (full entity, not just metrics)
    # StateInspector shows complete entity state including id, name, role etc.
    if _state.state_inspector is not None:
        entity = sim_state.entities.get("C001")
        if entity is not None:
            _state.state_inspector.refresh(entity.model_dump())

    # 5. Log new events -> SystemLog (NEW)
    if _state.system_log is not None:
        new_events = sim_state.events[_state.last_event_index:]
        for event in new_events:
            level = _event_to_log_level(event)
            _state.system_log.log(f"[{event.event_type.value}] tick={event.tick}", level)
        _state.last_event_index = len(sim_state.events)


async def poll_runner() -> None:
    """Timer callback for consuming states from runner queue.

    Replaces the old run_loop() - instead of directly stepping, we poll
    the queue for states pushed by the background runner. This decouples
    the UI update from the simulation step execution.
    """
    if _state.runner is None:
        return

    # Drain all available states (usually 0 or 1)
    # Each state triggers a UI refresh
    while True:
        sim_state = await _state.runner.get_state()
        if sim_state is None:
            break
        refresh_ui()


def main_page() -> None:
    """Render the Synopticon 4-panel dashboard.

    Layout (from ai-docs/synopticon-spec.yaml):

    .. code-block:: text

        +---------------------------------------------------------------------+
        |  BABYLON v0.3              [STEP] [PLAY] [PAUSE] [RESET] TICK:042   |
        +---------------+-------------------------------+---------------------+
        |               |    NarrativeTerminal (Top)    |                     |
        |  TrendPlotter |   -------------------------   |   StateInspector    |
        |  (25%)        |      SystemLog (Bottom)       |   (25%)             |
        |  EChart:      |   Raw events, instant append  |   json_editor for   |
        | -Imperial Rent|   Color-coded by level        |   C001 entity       |
        | -Global Tension|                              |                     |
        +---------------+-------------------------------+---------------------+

    Design System Colors (from ai-docs/design-system.yaml):
        - wet_concrete: #1A1A1A (header background)
        - silver_dust: #C0C0C0 (section labels)
        - grow_light_purple: #9D00FF (title, NARRATIVE label)
        - data_green: #39FF14 (SYSTEM LOG label)
    """
    ui.dark_mode().enable()

    # Header row: Title + ControlDeck (wet_concrete background)
    with ui.row().classes("w-full items-center justify-between p-4 bg-[#1A1A1A]"):
        ui.label("BABYLON v0.3").classes("text-[#9D00FF] font-mono text-2xl")
        _state.control_deck = ControlDeck(
            on_step=on_step,
            on_play=on_play,
            on_pause=on_pause,
            on_reset=on_reset,
        )

    # 3-column grid: 25% - 50% - 25%
    # CRITICAL: grid-template-rows: 1fr ensures the single row fills the grid height
    # Without this, rows default to 'auto' sizing which collapses to content height
    with (
        ui.grid(columns="1fr 2fr 1fr")
        .classes("w-full gap-4 p-4")
        .style("height: calc(100vh - 80px); grid-template-rows: 1fr")
    ):
        # Left panel: TrendPlotter (full height)
        # h-full stretches column to fill grid cell; w-full + flex-1 fills remaining space
        with ui.column().classes("gap-2 h-full w-full"):
            ui.label("METRICS").classes("text-[#C0C0C0] font-mono uppercase tracking-wider text-xs")
            with ui.element("div").classes("flex-1 min-h-0 w-full"):
                _state.trend_plotter = TrendPlotter()

        # Center panel: NarrativeTerminal (top 50%) + SystemLog (bottom 50%)
        # h-full + w-full stretches to grid cell; children use flex-1 to split evenly
        with ui.column().classes("gap-4 h-full w-full"):
            # Narrative panel (top half) - flex-1 takes 50% of available space
            with ui.column().classes("gap-2 flex-1 min-h-0 w-full"):
                ui.label("NARRATIVE").classes(
                    "text-[#9D00FF] font-mono uppercase tracking-wider text-xs"
                )
                with ui.element("div").classes("flex-1 min-h-0 w-full"):
                    _state.terminal = NarrativeTerminal()
            # System Log panel (bottom half) - flex-1 takes other 50%
            with ui.column().classes("gap-2 flex-1 min-h-0 w-full"):
                ui.label("SYSTEM LOG").classes(
                    "text-[#39FF14] font-mono uppercase tracking-wider text-xs"
                )
                with ui.element("div").classes("flex-1 min-h-0 w-full"):
                    _state.system_log = SystemLog()

        # Right panel: StateInspector (full height)
        # h-full + w-full stretches column to fill grid cell; flex-1 fills remaining space
        with ui.column().classes("gap-2 h-full w-full"):
            ui.label("STATE: C001").classes(
                "text-[#C0C0C0] font-mono uppercase tracking-wider text-xs"
            )
            with ui.element("div").classes("flex-1 min-h-0 w-full"):
                _state.state_inspector = StateInspector()

    # Timer for polling runner queue - MUST be inside root function
    # Poll at 100ms for responsive UI updates (runner controls tick rate)
    ui.timer(interval=0.1, callback=poll_runner)

    # One-shot timer to populate initial data after UI renders
    # Without this, dashboard shows empty components at tick 0
    # See: tests/unit/ui/test_main.py::TestMainPageInitialDataLoad
    ui.timer(interval=0.1, callback=refresh_ui, once=True)


# Initialize simulation on module load
init_simulation()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(main_page, title="Babylon v0.3", dark=True, reload=False, port=6969)
