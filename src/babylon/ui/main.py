"""Main Babylon UI application.

This module provides the entry point for the Babylon simulation UI,
wiring the ControlDeck to the Simulation engine.

Run with:
    python -m babylon.ui.main

Or:
    poetry run python src/babylon/ui/main.py
"""

from __future__ import annotations

from nicegui import ui  # type: ignore[import-not-found]

from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.ui.controls import ControlDeck

# Module-level state
simulation: Simulation | None = None
is_playing: bool = False
control_deck: ControlDeck | None = None


def init_simulation() -> None:
    """Initialize or reset the simulation."""
    global simulation
    state, config, defines = create_two_node_scenario()
    simulation = Simulation(state, config, defines=defines)


def on_step() -> None:
    """Handle STEP button click."""
    if simulation is not None:
        simulation.step()
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
    global is_playing
    is_playing = False
    init_simulation()
    refresh_ui()


def refresh_ui() -> None:
    """Update UI to reflect current simulation state."""
    if control_deck is not None and simulation is not None:
        control_deck.update_tick(simulation.current_state.tick)


def run_loop() -> None:
    """Timer callback for continuous play mode."""
    if is_playing and simulation is not None:
        simulation.step()
        refresh_ui()


def main_page() -> None:
    """Render the main application page."""
    global control_deck
    ui.dark_mode().enable()

    with ui.column().classes("w-full items-center p-4"):
        ui.label("BABYLON v0.3").classes("text-green-400 font-mono text-2xl mb-4")
        control_deck = ControlDeck(
            on_step=on_step,
            on_play=on_play,
            on_pause=on_pause,
            on_reset=on_reset,
        )
        # Placeholder for narrative terminal
        ui.label("TERMINAL OFFLINE").classes("text-gray-500 font-mono mt-8")

    # Timer for play mode (1 tick per second) - MUST be inside root function
    ui.timer(interval=1.0, callback=run_loop)


# Initialize simulation on module load
init_simulation()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(main_page, title="Babylon v0.3", dark=True, reload=False, port=6969)
