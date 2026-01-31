"""SimulationControl protocol definition.

This protocol defines the write interface for simulation control.
GUI code should depend ONLY on this protocol for control operations.

The protocol enables:
- GUI code to type-check against a stable interface
- Simulation internals to evolve without breaking GUI
- Multiple implementations (mock, real, replay)

Implementation:
    The Simulation class in src/babylon/engine/simulation.py implements this protocol.

See Also:
    - plan.md#Per-Tick Update Rule: Profit rate formula
    - research.md#5: Profit rate dynamics rationale
    - quickstart.md#Reset to Initial State: Usage examples

Feature 006-gui-protocol-extension:
    Added register_observer() and unregister_observer() methods for GUI callback
    registration. Callbacks receive frozen SimulationSnapshot, not live references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.protocols import ObserverCallback


@runtime_checkable
class SimulationControl(Protocol):
    """Write interface to simulation control with observer support.

    This protocol defines how GUI code controls simulation execution
    AND registers for state change notifications.

    Methods modify simulation state (advance tick, reset) or manage
    observer callbacks.

    Example:
        >>> def on_step_button_click(sim: SimulationControl) -> None:
        ...     sim.step()
        ...     update_display()
        ...
        >>> def on_reset_button_click(sim: SimulationControl) -> None:
        ...     sim.reset()
        ...     update_display()
        ...
        >>> # Register for tick notifications
        >>> def on_tick(tick: int, snapshot: SimulationSnapshot) -> None:
        ...     print(f"Tick {tick}: {len(snapshot.territories)} territories")
        >>> sim.register_observer(on_tick)
        >>> sim.step(10)  # on_tick called 10 times
    """

    def step(self, n: int = 1) -> None:
        """Advance the simulation by n ticks.

        Each tick:
        1. Computes new state from current state (deterministic)
        2. Increments tick counter
        3. Updates internal state
        4. Notifies all registered observers with frozen snapshot

        Determinism guarantee: Calling step(n) from the same state
        always produces the same result.

        Args:
            n: Number of ticks to advance. Must be positive.
                Defaults to 1 for single-step operation.

        Raises:
            ValueError: If n <= 0.

        Example:
            >>> sim.step()       # Advance 1 tick
            >>> sim.step(10)     # Advance 10 ticks
        """
        ...

    def reset(self) -> None:
        """Reset simulation to initial state (tick 0).

        Restores the simulation to its state immediately after initialization:
        - tick = 0
        - All territory states reset to initial values
        - profit_rate returns to initial computed values

        Does NOT notify observers (reset is not a tick event).

        Implementation note: reset() restores CACHED initial state, not by
        re-querying SQLite. This ensures:
        - Fast reset (no I/O)
        - Deterministic behavior regardless of database state changes
        - Identical behavior to creating a new simulation with same parameters

        Example:
            >>> sim.step(100)
            >>> sim.reset()
            >>> assert sim.get_current_tick() == 0
        """
        ...

    def register_observer(self, callback: ObserverCallback) -> None:
        """Register a callback for tick notifications.

        The callback will be invoked at the end of every step() call
        with the current tick number and a frozen SimulationSnapshot.

        Thread Safety:
            Callbacks receive a frozen Pydantic model (SimulationSnapshot),
            not a live reference to mutable simulation state. This ensures
            GUI code cannot accidentally modify simulation internals and
            allows safe cross-thread access.

        Callbacks are invoked in registration order. Duplicate registration
        is idempotent (callback invoked once per tick).

        Args:
            callback: Function to call after each tick.
                      Signature: (tick: int, snapshot: SimulationSnapshot) -> None

        Example:
            >>> def my_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            ...     print(f"Tick {tick}: {len(snapshot.territories)} territories")
            ...
            >>> sim.register_observer(my_callback)
            >>> sim.step()  # my_callback invoked once with frozen snapshot
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
