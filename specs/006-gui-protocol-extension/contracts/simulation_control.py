"""SimulationControl protocol contract for GUI Protocol Extension.

This file defines the EXTENDED protocol interface for simulation control.
The Simulation class must implement all methods defined here.

Feature: 006-gui-protocol-extension
Date: 2026-01-31

Changes from baseline:
- Added register_observer() for GUI callback registration
- Added unregister_observer() for GUI callback removal
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.protocols import SimulationState

# Type alias for GUI observer callbacks
ObserverCallback = Callable[[int, "SimulationState"], None]


@runtime_checkable
class SimulationControl(Protocol):
    """Write interface to simulation control with observer support.

    This protocol defines how GUI code controls simulation execution
    AND registers for state change notifications.

    Example:
        >>> def on_tick(tick: int, state: SimulationState) -> None:
        ...     print(f"Tick {tick}: {len(state.get_snapshot().territories)} territories")
        ...
        >>> sim: SimulationControl = get_simulation()
        >>> sim.register_observer(on_tick)
        >>> sim.step(10)  # on_tick called 10 times
        >>> sim.unregister_observer(on_tick)
    """

    def step(self, n: int = 1) -> None:
        """Advance the simulation by n ticks.

        Each tick:
        1. Computes new state from current state (deterministic)
        2. Increments tick counter
        3. Updates internal state
        4. Notifies all registered observers (NEW)

        Args:
            n: Number of ticks to advance. Must be positive.

        Raises:
            ValueError: If n <= 0.
        """
        ...

    def reset(self) -> None:
        """Reset simulation to initial state (tick 0).

        Restores the simulation to its state immediately after initialization.
        Does NOT notify observers (reset is not a tick event).
        """
        ...

    def register_observer(self, callback: ObserverCallback) -> None:
        """Register a callback for tick notifications.

        The callback will be invoked at the end of every step() call
        with the current tick number and a reference to SimulationState.

        Callbacks are invoked in registration order. Duplicate registration
        is idempotent (callback invoked once per tick).

        Args:
            callback: Function to call after each tick.
                      Signature: (tick: int, state: SimulationState) -> None

        Example:
            >>> def my_callback(tick: int, state: SimulationState) -> None:
            ...     snapshot = state.get_snapshot()
            ...     print(f"Tick {tick}: {len(snapshot.territories)} territories")
            ...
            >>> sim.register_observer(my_callback)
            >>> sim.step()  # my_callback invoked once
        """
        ...

    def unregister_observer(self, callback: ObserverCallback) -> None:
        """Remove a previously registered callback.

        If the callback was not registered, this is a no-op (no error raised).

        Args:
            callback: The callback function to remove.

        Example:
            >>> sim.unregister_observer(my_callback)
            >>> sim.step()  # my_callback NOT invoked
        """
        ...
