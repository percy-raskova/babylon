"""Observer protocol for simulation state change notifications.

The Observer Pattern separates the Material Base (simulation mechanics)
from the Ideological Superstructure (AI narrative generation).

Observers are notified AFTER each tick completes and receive both the
previous and new state for delta analysis. All state objects are frozen
and immutable - observers cannot modify simulation state.

Design Decisions (Sprint 3.1):
- Observer location: Simulation facade ONLY (step() remains pure)
- Notification order: After state reconstruction
- Error handling: Log and ignore (ADR003: "AI failures don't break game")
- Lifecycle hooks: on_simulation_start, on_tick, on_simulation_end
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


@runtime_checkable
class SimulationObserver(Protocol):
    """Protocol for entities observing simulation state changes.

    Observers receive notifications at three lifecycle points:
    1. on_simulation_start() - when simulation begins (first step)
    2. on_tick() - after each tick completes
    3. on_simulation_end() - when simulation ends (explicit end() call)

    Note: All state objects (WorldState) are frozen and immutable.
    Attempting to modify them will raise AttributeError.

    Example:
        >>> class MyObserver:
        ...     @property
        ...     def name(self) -> str:
        ...         return "MyObserver"
        ...
        ...     def on_simulation_start(
        ...         self, initial_state: WorldState, config: SimulationConfig
        ...     ) -> None:
        ...         print(f"Started at tick {initial_state.tick}")
        ...
        ...     def on_tick(
        ...         self, previous_state: WorldState, new_state: WorldState
        ...     ) -> None:
        ...         print(f"Tick {previous_state.tick} -> {new_state.tick}")
        ...
        ...     def on_simulation_end(self, final_state: WorldState) -> None:
        ...         print(f"Ended at tick {final_state.tick}")
    """

    @property
    def name(self) -> str:
        """Observer identifier for logging and debugging.

        Returns:
            A string identifying this observer instance.
        """
        ...

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Called when simulation begins (on first step call).

        Use this hook to initialize resources, establish context,
        or prepare for observing the simulation run.

        Args:
            initial_state: The WorldState at tick 0 (before any steps).
            config: The SimulationConfig for this run.
        """
        ...

    def on_tick(
        self,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes with both states for delta analysis.

        This is the primary notification hook. Observers receive both the
        previous and new state to enable delta analysis (what changed).

        Args:
            previous_state: WorldState before the tick.
            new_state: WorldState after the tick.
        """
        ...

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends (on explicit end() call).

        Use this hook to cleanup resources, generate summaries,
        or finalize any accumulated data.

        Args:
            final_state: The final WorldState when simulation ends.
        """
        ...
