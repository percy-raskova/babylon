"""Simulation facade class for running multi-tick simulations.

This module provides a Simulation class that wraps the ServiceContainer
and step() function, providing a convenient API for:
- Running simulations over multiple ticks
- Preserving history of all WorldState snapshots
- Maintaining a persistent ServiceContainer across ticks
"""

from __future__ import annotations

from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState


class Simulation:
    """Facade class for running multi-tick simulations with history preservation.

    The Simulation class provides a stateful wrapper around the pure step() function,
    managing:
    - Current WorldState
    - History of all previous states
    - Persistent ServiceContainer for dependency injection

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
    """

    def __init__(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Initialize simulation with initial state and configuration.

        Args:
            initial_state: Starting WorldState at tick 0
            config: Simulation configuration with formula coefficients
        """
        self._config = config
        self._services = ServiceContainer.create(config)
        self._current_state = initial_state
        self._history: list[WorldState] = [initial_state]

    @property
    def config(self) -> SimulationConfig:
        """Return the simulation configuration."""
        return self._config

    @property
    def services(self) -> ServiceContainer:
        """Return the persistent ServiceContainer."""
        return self._services

    @property
    def current_state(self) -> WorldState:
        """Return the current WorldState."""
        return self._current_state

    def step(self) -> WorldState:
        """Advance simulation by one tick.

        Applies the step() function to transform the current state,
        records the new state in history, and updates current_state.

        Returns:
            The new WorldState after one tick of simulation.
        """
        new_state = step(self._current_state, self._config)
        self._current_state = new_state
        self._history.append(new_state)
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
