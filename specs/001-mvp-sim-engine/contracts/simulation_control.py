"""SimulationControl protocol definition.

This protocol defines the write interface for simulation control.
GUI code should depend ONLY on this protocol for control operations.

The protocol is defined here in the spec for documentation purposes.
The actual implementation will be in src/babylon/protocols/simulation_control.py

Implementation References
-------------------------
- step() logic: See plan.md#Per-Tick Update Rule for profit_rate formula
- step() logic: See research.md#5. Profit Rate Dynamics for formula rationale
- reset() logic: Restores initial state from from_sqlite() hydration
- Implementation: src/babylon/engine/simulation.py (Simulation class implements this)
- Usage examples: See quickstart.md#Reset to Initial State
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SimulationControl(Protocol):
    """Write interface to simulation control.

    This protocol defines how GUI code controls simulation execution.
    Methods modify simulation state (advance tick, reset).

    The protocol enables:
    - GUI code to type-check against a stable interface
    - Simulation internals to evolve without breaking GUI
    - Multiple implementations (mock, real, replay)

    Example:
        >>> def on_step_button_click(sim: SimulationControl) -> None:
        ...     sim.step()
        ...     update_display()
        ...
        >>> def on_reset_button_click(sim: SimulationControl) -> None:
        ...     sim.reset()
        ...     update_display()
    """

    def step(self, n: int = 1) -> None:
        """Advance the simulation by n ticks.

        Each tick:
        1. Computes new state from current state (deterministic)
        2. Increments tick counter
        3. Updates internal state

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

        Implementation note: reset() restores CACHED initial state, not by
        re-querying SQLite. This ensures:
        - Fast reset (no I/O)
        - Deterministic behavior regardless of database state changes
        - Identical behavior to creating a new simulation with same parameters

        Example:
            >>> sim.step(100)
            >>> sim.reset()
            >>> assert sim.get_current_tick() == 0  # type: ignore[attr-defined]
        """
        ...
