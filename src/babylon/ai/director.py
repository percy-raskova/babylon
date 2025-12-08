"""Narrative Director - AI Game Master observing the simulation.

The NarrativeDirector implements the SimulationObserver protocol to
generate narrative from state changes. It sits in the Ideological
Superstructure layer and cannot modify simulation state.

Design Philosophy:
- Observer, not controller: watches state transitions
- Narrative from material: derives story from state changes
- Fail-safe: errors don't propagate to simulation (ADR003)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState

logger = logging.getLogger(__name__)


class NarrativeDirector:
    """AI Game Master that observes simulation and generates narrative.

    The Director watches state transitions and produces human-readable
    narrative describing the class struggle dynamics.

    Attributes:
        name: Observer identifier ("NarrativeDirector").
        use_llm: Whether to use LLM for narrative (False = template-based).

    Example:
        >>> from babylon.ai import NarrativeDirector
        >>> from babylon.engine import Simulation
        >>>
        >>> director = NarrativeDirector()
        >>> sim = Simulation(initial_state, config, observers=[director])
        >>> sim.run(10)  # Director logs narrative for each tick
        >>> sim.end()    # Director logs summary
    """

    def __init__(self, use_llm: bool = False) -> None:
        """Initialize the NarrativeDirector.

        Args:
            use_llm: If True, use LLM for narrative generation.
                     If False, use template-based generation (default).
                     LLM integration is planned for future sprints.
        """
        self._use_llm = use_llm
        self._config: SimulationConfig | None = None

    @property
    def name(self) -> str:
        """Return observer identifier.

        Returns:
            The string "NarrativeDirector".
        """
        return "NarrativeDirector"

    @property
    def use_llm(self) -> bool:
        """Return whether LLM is enabled.

        Returns:
            True if LLM-based narrative is enabled, False otherwise.
        """
        return self._use_llm

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Initialize narrative context at simulation start.

        Logs the simulation start event with initial state info.

        Args:
            initial_state: The WorldState at tick 0.
            config: The SimulationConfig for this run.
        """
        # Store config for potential future use in narrative generation
        self._config = config
        logger.info(
            "[%s] Simulation started at tick %d with %d entities",
            self.name,
            initial_state.tick,
            len(initial_state.entities),
        )

    def on_tick(
        self,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Analyze state change and log narrative.

        Detects new events added during this tick and logs them.

        Args:
            previous_state: WorldState before the tick.
            new_state: WorldState after the tick.
        """
        # Detect new events added this tick
        num_new_events = len(new_state.event_log) - len(previous_state.event_log)

        if num_new_events > 0:
            new_events = new_state.event_log[-num_new_events:]
            self._process_events(new_events, new_state.tick)

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Generate summary at simulation end.

        Logs the simulation end event with final state info.

        Args:
            final_state: The final WorldState when simulation ends.
        """
        logger.info(
            "[%s] Simulation ended at tick %d with %d total events",
            self.name,
            final_state.tick,
            len(final_state.event_log),
        )

    def _process_events(self, events: list[str], tick: int) -> None:
        """Process and log new events.

        Args:
            events: List of new event strings from this tick.
            tick: The current tick number.
        """
        for event in events:
            logger.info("[%s] Tick %d: %s", self.name, tick, event)
