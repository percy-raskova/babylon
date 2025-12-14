"""Control Deck UI component for simulation control.

This module provides the ControlDeck class, which renders simulation
control buttons (STEP, PLAY, PAUSE, RESET) and a tick counter display.

Aesthetic: "Cybernetic Terminal" - Dark background, green text, monospace font.

Example:
    >>> from babylon.ui.controls import ControlDeck
    >>> deck = ControlDeck(
    ...     on_step=lambda: print("Step!"),
    ...     on_play=lambda: print("Play!"),
    ... )
    >>> deck.update_tick(42)  # Updates display to "TICK: 042"
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from nicegui import ui  # type: ignore[import-not-found]

# Type alias for callbacks that can be sync or async
# NiceGUI buttons accept both synchronous and async callbacks
ButtonCallback = Callable[[], None] | Callable[[], Coroutine[Any, Any, None]]


class ControlDeck:
    """Simulation control panel with cybernetic terminal aesthetic.

    The ControlDeck provides:
    - STEP button: Advance simulation by one tick
    - PLAY button: Start continuous simulation
    - PAUSE button: Stop continuous simulation
    - RESET button: Reset simulation to initial state
    - Tick counter: Displays current tick as "TICK: NNN"

    Styling:
        - Container: bg-gray-900 p-4 rounded
        - Buttons: border border-green-600 text-green-400 font-mono px-4 py-2
        - Tick Counter: text-green-400 font-mono text-xl

    Args:
        on_step: Callback invoked when STEP button is clicked.
        on_play: Callback invoked when PLAY button is clicked.
        on_pause: Callback invoked when PAUSE button is clicked.
        on_reset: Callback invoked when RESET button is clicked.

    Example:
        >>> deck = ControlDeck(on_step=lambda: sim.step())
        >>> deck.update_tick(5)  # Shows "TICK: 005"
    """

    # Styling constants for cybernetic terminal aesthetic
    CONTAINER_CLASSES = "bg-gray-900 p-4 rounded"
    BUTTON_CLASSES = "border border-green-600 text-green-400 font-mono px-4 py-2"
    TICK_COUNTER_CLASSES = "text-green-400 font-mono text-xl"

    def __init__(
        self,
        on_step: ButtonCallback | None = None,
        on_play: ButtonCallback | None = None,
        on_pause: ButtonCallback | None = None,
        on_reset: ButtonCallback | None = None,
    ) -> None:
        """Initialize the ControlDeck with optional callbacks.

        Callbacks can be synchronous or async - NiceGUI handles both.

        Args:
            on_step: Callback for STEP button (sync or async).
            on_play: Callback for PLAY button (sync or async).
            on_pause: Callback for PAUSE button (sync or async).
            on_reset: Callback for RESET button (sync or async).
        """
        # Store callbacks
        self._on_step = on_step
        self._on_play = on_play
        self._on_pause = on_pause
        self._on_reset = on_reset

        # Initialize state
        self._current_tick: int = 0

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the UI elements."""
        # Container row with styling
        with ui.row().classes(self.CONTAINER_CLASSES) as container:
            self.container: Any = container

            # Control buttons
            self.step_button: Any = (
                ui.button("STEP", on_click=self._handle_step)
                .classes(self.BUTTON_CLASSES)
                .props("flat")
            )

            self.play_button: Any = (
                ui.button("PLAY", on_click=self._handle_play)
                .classes(self.BUTTON_CLASSES)
                .props("flat")
            )

            self.pause_button: Any = (
                ui.button("PAUSE", on_click=self._handle_pause)
                .classes(self.BUTTON_CLASSES)
                .props("flat")
            )

            self.reset_button: Any = (
                ui.button("RESET", on_click=self._handle_reset)
                .classes(self.BUTTON_CLASSES)
                .props("flat")
            )

            # Tick counter display
            self.tick_counter: Any = ui.label(self._format_tick(0)).classes(
                self.TICK_COUNTER_CLASSES
            )

    def _format_tick(self, tick: int) -> str:
        """Format tick number for display.

        Args:
            tick: The tick number to format.

        Returns:
            Formatted string like "TICK: 000" or "TICK: 042".
        """
        return f"TICK: {tick:03d}"

    def _handle_step(self) -> None:
        """Handle STEP button click."""
        if self._on_step is not None:
            self._on_step()

    def _handle_play(self) -> None:
        """Handle PLAY button click."""
        if self._on_play is not None:
            self._on_play()

    def _handle_pause(self) -> None:
        """Handle PAUSE button click."""
        if self._on_pause is not None:
            self._on_pause()

    def _handle_reset(self) -> None:
        """Handle RESET button click."""
        if self._on_reset is not None:
            self._on_reset()

    def update_tick(self, tick: int) -> None:
        """Update the tick counter display.

        Args:
            tick: The new tick number to display.
        """
        self._current_tick = tick
        self.tick_counter.set_text(self._format_tick(tick))
