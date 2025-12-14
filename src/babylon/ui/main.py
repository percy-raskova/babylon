"""Main Babylon UI application.

This module provides the entry point for the Babylon simulation UI,
wiring the ControlDeck and NarrativeTerminal to the Simulation engine.

Run with:
    python -m babylon.ui.main

Or:
    poetry run python src/babylon/ui/main.py
"""

from __future__ import annotations

import asyncio

from nicegui import ui  # type: ignore[import-not-found]

from babylon.engine.observer import SimulationObserver
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.ui.controls import ControlDeck
from babylon.ui.terminal import NarrativeTerminal, find_narrative_director, poll_narrative_director

# Module-level state
simulation: Simulation | None = None
is_playing: bool = False
control_deck: ControlDeck | None = None
terminal: NarrativeTerminal | None = None
last_narrative_index: int = 0


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
    global is_playing, last_narrative_index
    is_playing = False
    last_narrative_index = 0  # Reset narrative polling index
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


def refresh_ui() -> None:
    """Update UI to reflect current simulation state.

    Updates the tick counter and polls the NarrativeDirector for new
    narrative entries, pushing them to the terminal for display.
    """
    global last_narrative_index

    if control_deck is not None and simulation is not None:
        control_deck.update_tick(simulation.current_state.tick)

    # Poll NarrativeDirector for new narrative entries
    if terminal is not None:
        director = _get_narrative_director()
        if director is not None:
            new_entries, last_narrative_index = poll_narrative_director(
                director, last_narrative_index
            )
            for entry in new_entries:
                terminal.log(entry)


def run_loop() -> None:
    """Timer callback for continuous play mode."""
    if is_playing and simulation is not None:
        simulation.step()
        refresh_ui()


def main_page() -> None:
    """Render the main application page."""
    global control_deck, terminal
    ui.dark_mode().enable()

    with ui.column().classes("w-full items-center p-4"):
        ui.label("BABYLON v0.3").classes("text-green-400 font-mono text-2xl mb-4")
        control_deck = ControlDeck(
            on_step=on_step,
            on_play=on_play,
            on_pause=on_pause,
            on_reset=on_reset,
        )
        # Narrative terminal with typewriter animation
        with ui.row().classes("w-full max-w-2xl mt-8"):
            terminal = NarrativeTerminal()

    # Timer for play mode (1 tick per second) - MUST be inside root function
    ui.timer(interval=1.0, callback=run_loop)


# Initialize simulation on module load
init_simulation()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(main_page, title="Babylon v0.3", dark=True, reload=False, port=6969)
