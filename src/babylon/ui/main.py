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

import asyncio

from nicegui import ui

from babylon.engine.observer import SimulationObserver
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent
from babylon.models.world_state import WorldState
from babylon.ui.components import StateInspector, SystemLog, TrendPlotter
from babylon.ui.controls import ControlDeck
from babylon.ui.terminal import NarrativeTerminal, find_narrative_director, poll_narrative_director

# Module-level state
simulation: Simulation | None = None
is_playing: bool = False
control_deck: ControlDeck | None = None
terminal: NarrativeTerminal | None = None
last_narrative_index: int = 0

# New Synopticon panel state (Sprint 4)
system_log: SystemLog | None = None
trend_plotter: TrendPlotter | None = None
state_inspector: StateInspector | None = None
last_event_index: int = 0


def init_simulation() -> None:
    """Initialize or reset the simulation."""
    global simulation
    state, config, defines = create_two_node_scenario()
    simulation = Simulation(state, config, defines=defines)


async def on_step() -> None:
    """Handle STEP button click.

    Uses asyncio.to_thread() to run simulation step in a background thread,
    preventing GUI freeze during potentially slow operations (e.g., AI inference).
    """
    if simulation is not None:
        await asyncio.to_thread(simulation.step)
        refresh_ui()


def on_play() -> None:
    """Handle PLAY button click."""
    global is_playing
    is_playing = True


def on_pause() -> None:
    """Handle PAUSE button click."""
    global is_playing
    is_playing = False


def on_reset() -> None:
    """Handle RESET button click."""
    global is_playing, last_narrative_index, last_event_index
    is_playing = False
    last_narrative_index = 0  # Reset narrative polling index
    last_event_index = 0  # Reset event tracking index
    init_simulation()
    refresh_ui()


def _get_narrative_director() -> SimulationObserver | None:
    """Find the NarrativeDirector among simulation observers.

    Returns:
        The NarrativeDirector observer if found, None otherwise.
    """
    if simulation is None:
        return None
    return find_narrative_director(simulation.observers)


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
    global last_narrative_index, last_event_index

    if simulation is None:
        return

    state = simulation.current_state

    # 1. Update tick counter (existing)
    if control_deck is not None:
        control_deck.update_tick(state.tick)

    # 2. Poll NarrativeDirector -> NarrativeTerminal (existing)
    if terminal is not None:
        director = _get_narrative_director()
        if director is not None:
            new_entries, last_narrative_index = poll_narrative_director(
                director, last_narrative_index
            )
            for entry in new_entries:
                terminal.log(entry)

    # 3. Push metrics -> TrendPlotter (NEW)
    if trend_plotter is not None:
        rent = float(state.economy.imperial_rent_pool)
        tension = _calculate_global_tension(state)
        trend_plotter.push_data(state.tick, rent, tension)

    # 4. Update StateInspector with C001 entity (NEW)
    if state_inspector is not None:
        entity = state.entities.get("C001")
        if entity is not None:
            state_inspector.refresh(entity.model_dump())

    # 5. Log new events -> SystemLog (NEW)
    if system_log is not None:
        new_events = state.events[last_event_index:]
        for event in new_events:
            level = _event_to_log_level(event)
            system_log.log(f"[{event.event_type.value}] tick={event.tick}", level)
        last_event_index = len(state.events)


def run_loop() -> None:
    """Timer callback for continuous play mode."""
    if is_playing and simulation is not None:
        simulation.step()
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
    global control_deck, terminal, system_log, trend_plotter, state_inspector
    ui.dark_mode().enable()

    # Header row: Title + ControlDeck (wet_concrete background)
    with ui.row().classes("w-full items-center justify-between p-4 bg-[#1A1A1A]"):
        ui.label("BABYLON v0.3").classes("text-[#9D00FF] font-mono text-2xl")
        control_deck = ControlDeck(
            on_step=on_step,
            on_play=on_play,
            on_pause=on_pause,
            on_reset=on_reset,
        )

    # 3-column grid: 25% - 50% - 25%
    with (
        ui.grid(columns="1fr 2fr 1fr")
        .classes("w-full gap-4 p-4")
        .style("height: calc(100vh - 80px)")
    ):
        # Left panel: TrendPlotter (full height)
        with ui.column().classes("gap-2").style("height: 100%"):
            ui.label("METRICS").classes("text-[#C0C0C0] font-mono uppercase tracking-wider text-xs")
            with ui.element("div").style("flex: 1; min-height: 0"):
                trend_plotter = TrendPlotter()

        # Center panel: NarrativeTerminal (top 50%) + SystemLog (bottom 50%)
        with ui.column().classes("gap-4").style("height: 100%"):
            # Narrative panel (top half)
            with ui.column().classes("gap-2").style("flex: 1; min-height: 0"):
                ui.label("NARRATIVE").classes(
                    "text-[#9D00FF] font-mono uppercase tracking-wider text-xs"
                )
                with ui.element("div").style("flex: 1; min-height: 0; display: flex"):
                    terminal = NarrativeTerminal()
            # System Log panel (bottom half)
            with ui.column().classes("gap-2").style("flex: 1; min-height: 0"):
                ui.label("SYSTEM LOG").classes(
                    "text-[#39FF14] font-mono uppercase tracking-wider text-xs"
                )
                with ui.element("div").style("flex: 1; min-height: 0; display: flex"):
                    system_log = SystemLog()

        # Right panel: StateInspector (full height)
        with ui.column().classes("gap-2").style("height: 100%"):
            ui.label("STATE: C001").classes(
                "text-[#C0C0C0] font-mono uppercase tracking-wider text-xs"
            )
            with ui.element("div").style("flex: 1; min-height: 0"):
                state_inspector = StateInspector()

    # Timer for play mode (1 tick per second) - MUST be inside root function
    ui.timer(interval=1.0, callback=run_loop)

    # One-shot timer to populate initial data after UI renders
    # Without this, dashboard shows empty components at tick 0
    # See: tests/unit/ui/test_main.py::TestMainPageInitialDataLoad
    ui.timer(interval=0.1, callback=refresh_ui, once=True)


# Initialize simulation on module load
init_simulation()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(main_page, title="Babylon v0.3", dark=True, reload=False, port=6969)
