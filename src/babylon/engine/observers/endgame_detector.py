"""EndgameDetector observer for game ending detection (Slice 1.6).

The EndgameDetector is a SimulationObserver that monitors WorldState for
three possible game ending conditions:

1. REVOLUTIONARY_VICTORY: percolation >= 0.7 AND class_consciousness > 0.8
   - The masses have achieved critical organization AND ideological clarity
   - This represents successful proletarian revolution

2. ECOLOGICAL_COLLAPSE: overshoot_ratio > 2.0 for 5 consecutive ticks
   - Sustained ecological overshoot leads to irreversible collapse
   - Capital's metabolic rift has become fatal

3. FASCIST_CONSOLIDATION: national_identity > class_consciousness for 3+ nodes
   - Fascist ideology has captured the majority of the population
   - False consciousness prevents class-based organization

Priority when multiple conditions are met:
    REVOLUTIONARY_VICTORY > ECOLOGICAL_COLLAPSE > FASCIST_CONSOLIDATION

The detector implements the Observer Pattern: it receives state change
notifications but cannot modify simulation state.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.engine.topology_monitor import (
    calculate_component_metrics,
    extract_solidarity_subgraph,
)
from babylon.models.enums import GameOutcome
from babylon.models.events import EndgameEvent

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


# =============================================================================
# CONSTANTS
# =============================================================================

# Revolutionary victory thresholds
PERCOLATION_THRESHOLD = 0.7  # 70% of nodes in giant component
CONSCIOUSNESS_THRESHOLD = 0.8  # Average consciousness > 0.8

# Ecological collapse thresholds
OVERSHOOT_THRESHOLD = 2.0  # Consumption > 2x biocapacity
OVERSHOOT_CONSECUTIVE_TICKS = 5  # Must persist for 5 ticks

# Fascist consolidation thresholds
FASCIST_NODES_THRESHOLD = 3  # At least 3 nodes with national_identity > class_consciousness


# =============================================================================
# ENDGAME DETECTOR OBSERVER
# =============================================================================


class EndgameDetector:
    """Observer detecting game ending conditions.

    Implements SimulationObserver protocol to receive state change
    notifications and check for endgame conditions after each tick.

    The detector maintains:
    - Current outcome (IN_PROGRESS until game ends)
    - Consecutive overshoot tick counter (for ecological collapse)
    - Pending events list (for ENDGAME_REACHED event emission)

    Attributes:
        name: Observer identifier ("EndgameDetector").
        outcome: Current GameOutcome (starts as IN_PROGRESS).
        is_game_over: Boolean indicating if game has ended.

    Example:
        >>> from babylon.engine.observers.endgame_detector import EndgameDetector
        >>> detector = EndgameDetector()
        >>> detector.outcome
        <GameOutcome.IN_PROGRESS: 'in_progress'>
        >>> detector.is_game_over
        False
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize EndgameDetector.

        Args:
            logger: Logger instance for endgame notifications.
                Defaults to module-level logger if not provided.
        """
        self._logger: logging.Logger = logger or logging.getLogger(__name__)
        self._outcome: GameOutcome = GameOutcome.IN_PROGRESS
        self._overshoot_consecutive_ticks: int = 0
        self._pending_events: list[EndgameEvent] = []
        self._endgame_event_emitted: bool = False

    @property
    def name(self) -> str:
        """Return observer identifier.

        Returns:
            String "EndgameDetector" for logging and debugging.
        """
        return "EndgameDetector"

    @property
    def outcome(self) -> GameOutcome:
        """Return current game outcome.

        Returns:
            GameOutcome enum value (IN_PROGRESS, REVOLUTIONARY_VICTORY,
            ECOLOGICAL_COLLAPSE, or FASCIST_CONSOLIDATION).
        """
        return self._outcome

    @property
    def is_game_over(self) -> bool:
        """Return True if game has ended.

        Returns:
            Boolean indicating if outcome is not IN_PROGRESS.
        """
        return self._outcome != GameOutcome.IN_PROGRESS

    def get_pending_events(self) -> list[EndgameEvent]:
        """Return and clear pending events for collection by Simulation facade.

        Observer events cannot be emitted directly to WorldState because
        observers run AFTER WorldState is frozen. Instead, pending events
        are collected by the Simulation facade and injected into the
        NEXT tick's WorldState.

        Returns:
            List of pending SimulationEvent objects (cleared after return).
        """
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def on_simulation_start(
        self,
        initial_state: WorldState,  # noqa: ARG002
        config: SimulationConfig,  # noqa: ARG002
    ) -> None:
        """Called when simulation begins.

        Resets detector to initial state, allowing reuse across
        multiple simulation runs.

        Args:
            initial_state: WorldState at tick 0.
            config: SimulationConfig for this run (unused).
        """
        self._outcome = GameOutcome.IN_PROGRESS
        self._overshoot_consecutive_ticks = 0
        self._pending_events.clear()
        self._endgame_event_emitted = False

    def on_tick(
        self,
        previous_state: WorldState,  # noqa: ARG002
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes with both states for delta analysis.

        Checks for endgame conditions in priority order:
        1. Revolutionary victory (highest priority - the people won)
        2. Ecological collapse
        3. Fascist consolidation (lowest priority)

        If game has already ended, this is a no-op.

        Args:
            previous_state: WorldState before the tick (unused).
            new_state: WorldState after the tick.
        """
        # If game already ended, don't check again
        if self.is_game_over:
            return

        # Check conditions in priority order
        if self._check_revolutionary_victory(new_state):
            self._outcome = GameOutcome.REVOLUTIONARY_VICTORY
            self._emit_endgame_event(new_state)
            return

        if self._check_ecological_collapse(new_state):
            self._outcome = GameOutcome.ECOLOGICAL_COLLAPSE
            self._emit_endgame_event(new_state)
            return

        if self._check_fascist_consolidation(new_state):
            self._outcome = GameOutcome.FASCIST_CONSOLIDATION
            self._emit_endgame_event(new_state)
            return

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends.

        No-op for EndgameDetector. Endgame state is already determined.

        Args:
            final_state: Final WorldState when simulation ends (unused).
        """
        pass

    def _check_revolutionary_victory(self, state: WorldState) -> bool:
        """Check if revolutionary victory conditions are met.

        Conditions:
        - percolation_ratio >= 0.7 (70% in giant component)
        - average class_consciousness > 0.8 across proletariat nodes

        Args:
            state: Current WorldState to analyze.

        Returns:
            True if revolutionary victory conditions are met.
        """
        graph = state.to_graph()

        # Count social_class nodes
        social_class_nodes = [
            node_id
            for node_id, data in graph.nodes(data=True)
            if data.get("_node_type") == "social_class"
        ]
        total_nodes = len(social_class_nodes)

        if total_nodes == 0:
            return False

        # Calculate percolation ratio
        solidarity_graph = extract_solidarity_subgraph(graph)
        _, _, percolation_ratio = calculate_component_metrics(solidarity_graph, total_nodes)

        if percolation_ratio < PERCOLATION_THRESHOLD:
            return False

        # Calculate average class consciousness across all social_class nodes
        # Access class_consciousness from the ideology.class_consciousness nested field
        total_consciousness = 0.0
        consciousness_count = 0

        for entity in state.entities.values():
            ideology = getattr(entity, "ideology", None)
            if ideology is not None:
                consciousness = getattr(ideology, "class_consciousness", 0.0)
            else:
                consciousness = 0.0
            total_consciousness += consciousness
            consciousness_count += 1

        if consciousness_count == 0:
            return False

        average_consciousness = total_consciousness / consciousness_count

        return average_consciousness > CONSCIOUSNESS_THRESHOLD

    def _check_ecological_collapse(self, state: WorldState) -> bool:
        """Check if ecological collapse conditions are met.

        Conditions:
        - overshoot_ratio > 2.0 for 5 consecutive ticks

        overshoot_ratio = total_consumption / total_biocapacity

        Args:
            state: Current WorldState to analyze.

        Returns:
            True if ecological collapse conditions are met.
        """
        # Calculate total consumption and biocapacity
        total_consumption = 0.0
        total_biocapacity = 0.0

        # Sum consumption from all entities (s_bio + s_class)
        for entity in state.entities.values():
            s_bio = getattr(entity, "s_bio", 0.0)
            s_class = getattr(entity, "s_class", 0.0)
            total_consumption += s_bio + s_class

        # Sum biocapacity from all territories
        for territory in state.territories.values():
            biocapacity = getattr(territory, "biocapacity", 0.0)
            total_biocapacity += biocapacity

        # Guard against division by zero
        if total_biocapacity <= 0.0:
            self._overshoot_consecutive_ticks = 0
            return False

        overshoot_ratio = total_consumption / total_biocapacity

        if overshoot_ratio > OVERSHOOT_THRESHOLD:
            self._overshoot_consecutive_ticks += 1
        else:
            self._overshoot_consecutive_ticks = 0

        return self._overshoot_consecutive_ticks >= OVERSHOOT_CONSECUTIVE_TICKS

    def _check_fascist_consolidation(self, state: WorldState) -> bool:
        """Check if fascist consolidation conditions are met.

        Conditions:
        - national_identity > class_consciousness for 3+ nodes

        Args:
            state: Current WorldState to analyze.

        Returns:
            True if fascist consolidation conditions are met.
        """
        fascist_node_count = 0

        for entity in state.entities.values():
            # Access ideology fields from the nested IdeologicalProfile
            ideology = getattr(entity, "ideology", None)
            if ideology is not None:
                national_identity = getattr(ideology, "national_identity", 0.0)
                class_consciousness = getattr(ideology, "class_consciousness", 0.0)
            else:
                national_identity = 0.0
                class_consciousness = 0.0

            if national_identity > class_consciousness:
                fascist_node_count += 1

        return fascist_node_count >= FASCIST_NODES_THRESHOLD

    def _emit_endgame_event(self, state: WorldState) -> None:
        """Emit ENDGAME_REACHED event when game ends.

        Only emits once per game ending. Subsequent calls are no-ops.

        Args:
            state: WorldState at endgame moment.
        """
        if self._endgame_event_emitted:
            return

        event = EndgameEvent(
            tick=state.tick,
            outcome=self._outcome,
        )
        self._pending_events.append(event)
        self._endgame_event_emitted = True

        self._logger.info(
            "[ENDGAME] Game ended at tick %d with outcome: %s",
            state.tick,
            self._outcome.value,
        )
