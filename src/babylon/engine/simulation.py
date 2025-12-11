"""Simulation facade class for running multi-tick simulations.

This module provides a Simulation class that wraps the ServiceContainer
and step() function, providing a convenient API for:
- Running simulations over multiple ticks
- Preserving history of all WorldState snapshots
- Maintaining a persistent ServiceContainer across ticks
- Observer pattern for AI narrative generation (Sprint 3.1)

Observer Pattern Integration (Sprint 3.1):
- Observers are registered via constructor or add_observer()
- Notifications occur AFTER state reconstruction (per design decision)
- Observer errors are logged but don't halt simulation (ADR003)
- Lifecycle hooks: on_simulation_start, on_tick, on_simulation_end
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.config.defines import GameDefines
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    from babylon.engine.observer import SimulationObserver

logger = logging.getLogger(__name__)


class Simulation:
    """Facade class for running multi-tick simulations with history preservation.

    The Simulation class provides a stateful wrapper around the pure step() function,
    managing:
    - Current WorldState
    - History of all previous states
    - Persistent ServiceContainer for dependency injection
    - Observer notifications for AI/narrative components (Sprint 3.1)

    Example:
        >>> from babylon.engine.factories import create_proletariat, create_bourgeoisie
        >>> from babylon.models import WorldState, SimulationConfig, Relationship, EdgeType
        >>>
        >>> worker = create_proletariat()
        >>> owner = create_bourgeoisie()
        >>> exploitation = Relationship(
        ...     source_id=worker.id, target_id=owner.id,
        ...     edge_type=EdgeType.EXPLOITATION
        ... )
        >>> state = WorldState(entities={worker.id: worker, owner.id: owner},
        ...                    relationships=[exploitation])
        >>> config = SimulationConfig()
        >>>
        >>> sim = Simulation(state, config)
        >>> sim.run(100)
        >>> print(f"Worker wealth after 100 ticks: {sim.current_state.entities[worker.id].wealth}")

    With observers:
        >>> from babylon.ai import NarrativeDirector
        >>> director = NarrativeDirector()
        >>> sim = Simulation(state, config, observers=[director])
        >>> sim.run(10)
        >>> sim.end()  # Triggers on_simulation_end
    """

    def __init__(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
        observers: list[SimulationObserver] | None = None,
        defines: GameDefines | None = None,
    ) -> None:
        """Initialize simulation with initial state and configuration.

        Args:
            initial_state: Starting WorldState at tick 0
            config: Simulation configuration with formula coefficients
            observers: Optional list of SimulationObserver instances to notify
            defines: Optional custom GameDefines for scenario-specific coefficients.
                     If None, loads from default defines.yaml location.
        """
        self._config = config
        self._defines = defines if defines is not None else GameDefines.load_default()
        self._services = ServiceContainer.create(config, self._defines)
        self._current_state = initial_state
        self._history: list[WorldState] = [initial_state]
        self._observers: list[SimulationObserver] = list(observers or [])
        self._started = False
        # Persistent context that spans across ticks (Sprint 3.4.3)
        # Used for tracking state between ticks like previous_wages
        self._persistent_context: dict[str, object] = {}

    @property
    def config(self) -> SimulationConfig:
        """Return the simulation configuration."""
        return self._config

    @property
    def defines(self) -> GameDefines:
        """Return the game defines."""
        return self._defines

    @property
    def services(self) -> ServiceContainer:
        """Return the persistent ServiceContainer."""
        return self._services

    @property
    def current_state(self) -> WorldState:
        """Return the current WorldState."""
        return self._current_state

    @property
    def observers(self) -> list[SimulationObserver]:
        """Return copy of registered observers.

        Returns a copy to preserve encapsulation - modifying the
        returned list does not affect the internal observer list.

        Returns:
            A copy of the list of registered observers.
        """
        return list(self._observers)

    def add_observer(self, observer: SimulationObserver) -> None:
        """Register an observer for simulation notifications.

        Observers added after simulation has started will not
        receive on_simulation_start, but will receive on_tick
        and on_simulation_end notifications.

        Args:
            observer: Observer implementing SimulationObserver protocol.
        """
        self._observers.append(observer)

    def remove_observer(self, observer: SimulationObserver) -> None:
        """Remove an observer. No-op if observer not present.

        Args:
            observer: Observer to remove from notifications.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_observers_start(self) -> None:
        """Notify observers of simulation start.

        Errors in observers are logged but do not halt simulation (ADR003).
        """
        for observer in self._observers:
            try:
                observer.on_simulation_start(self._current_state, self._config)
            except Exception as e:
                logger.warning(
                    "Observer %s failed on_simulation_start: %s",
                    observer.name,
                    e,
                )

    def _notify_observers_tick(
        self,
        previous: WorldState,
        new: WorldState,
    ) -> None:
        """Notify observers of tick completion.

        Errors in observers are logged but do not halt simulation (ADR003).

        Args:
            previous: WorldState before the tick.
            new: WorldState after the tick.
        """
        for observer in self._observers:
            try:
                observer.on_tick(previous, new)
            except Exception as e:
                logger.warning(
                    "Observer %s failed on_tick: %s",
                    observer.name,
                    e,
                )

    def _notify_observers_end(self) -> None:
        """Notify observers of simulation end.

        Errors in observers are logged but do not halt simulation (ADR003).
        """
        for observer in self._observers:
            try:
                observer.on_simulation_end(self._current_state)
            except Exception as e:
                logger.warning(
                    "Observer %s failed on_simulation_end: %s",
                    observer.name,
                    e,
                )

    def step(self) -> WorldState:
        """Advance simulation by one tick.

        Applies the step() function to transform the current state,
        records the new state in history, updates current_state, and
        notifies registered observers.

        On first step, observers receive on_simulation_start before on_tick.

        The persistent context is passed to step() to maintain state
        across ticks (e.g., previous_wages for bifurcation mechanic).

        Returns:
            The new WorldState after one tick of simulation.
        """
        # On first step, notify observers of simulation start
        if not self._started:
            self._notify_observers_start()
            self._started = True

        previous_state = self._current_state
        # Pass persistent context to preserve state across ticks (Sprint 3.4.3)
        # Pass custom defines for scenario-specific coefficients
        new_state = step(previous_state, self._config, self._persistent_context, self._defines)
        self._current_state = new_state
        self._history.append(new_state)

        # Notify observers after state reconstruction (per design decision)
        self._notify_observers_tick(previous_state, new_state)

        return new_state

    def run(self, ticks: int) -> WorldState:
        """Run simulation for N ticks.

        Args:
            ticks: Number of ticks to advance the simulation

        Returns:
            The final WorldState after all ticks complete.

        Raises:
            ValueError: If ticks is negative
        """
        if ticks < 0:
            error_message = f"ticks must be non-negative, got {ticks}"
            raise ValueError(error_message)

        for _ in range(ticks):
            self.step()

        return self._current_state

    def get_history(self) -> list[WorldState]:
        """Return all WorldState snapshots from initial to current.

        The history includes:
        - Index 0: Initial state (tick 0)
        - Index N: State after N steps (tick N)

        Returns:
            List of WorldState snapshots in chronological order.
        """
        return list(self._history)

    def update_state(self, new_state: WorldState) -> None:
        """Update the current state mid-simulation.

        This allows modifying the simulation state (e.g., changing relationships)
        while preserving the persistent context across ticks. Useful for testing
        scenarios like wage cuts where the previous_wages context must be preserved.

        Args:
            new_state: New WorldState to use as current state.
                       The tick should match the expected continuation tick.

        Note:
            This does NOT add the new state to history - history reflects
            actual simulation progression, not manual state updates.
        """
        self._current_state = new_state

    def end(self) -> None:
        """Signal simulation end and notify observers.

        Calls on_simulation_end on all registered observers with
        the current (final) state.

        No-op if simulation has not started (no step() calls made).
        Can be called multiple times, but only the first call after
        step() will notify observers.
        """
        if self._started:
            self._notify_observers_end()
            self._started = False
