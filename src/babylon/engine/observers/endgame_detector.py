"""EndgameDetector observer for game ending detection (Slice 1.6).

The EndgameDetector is a SimulationObserver that monitors WorldState for
three possible game ending conditions:

1. REVOLUTIONARY_VICTORY: percolation >= threshold AND class_consciousness > threshold
   - The masses have achieved critical organization AND ideological clarity
   - This represents successful proletarian revolution

2. ECOLOGICAL_COLLAPSE: overshoot_ratio > threshold for N consecutive ticks
   - Sustained ecological overshoot leads to irreversible collapse
   - Capital's metabolic rift has become fatal

3. FASCIST_CONSOLIDATION: national_identity > class_consciousness for M+ nodes
   - Fascist ideology has captured the majority of the population
   - False consciousness prevents class-based organization

Priority when multiple conditions are met:
    REVOLUTIONARY_VICTORY > ECOLOGICAL_COLLAPSE > FASCIST_CONSOLIDATION

The detector implements the Observer Pattern: it receives state change
notifications but cannot modify simulation state.

Thresholds are configurable via GameDefines.endgame for scenario customization.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.config.defines import EndgameDefines, GameDefines
from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.engine.topology_monitor import (
    calculate_component_metrics,
    extract_solidarity_subgraph,
)
from babylon.models.enums import ColonialStance, ExtractionPolicy, GameOutcome
from babylon.models.events import EndgameEvent

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


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
    - Configurable thresholds via GameDefines.endgame

    Attributes:
        name: Observer identifier ("EndgameDetector").
        outcome: Current GameOutcome (starts as IN_PROGRESS).
        is_game_over: Boolean indicating if game has ended.
        defines: EndgameDefines containing threshold configuration.

    Example:
        >>> from babylon.engine.observers.endgame_detector import EndgameDetector
        >>> detector = EndgameDetector()
        >>> detector.outcome
        <GameOutcome.IN_PROGRESS: 'in_progress'>
        >>> detector.is_game_over
        False

        >>> # Custom thresholds via GameDefines
        >>> from babylon.config.defines import GameDefines, EndgameDefines
        >>> custom = GameDefines(endgame=EndgameDefines(
        ...     revolutionary_percolation_threshold=0.5,
        ...     fascist_majority_threshold=5,
        ... ))
        >>> detector = EndgameDetector(defines=custom)
        >>> detector.defines.revolutionary_percolation_threshold
        0.5
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        defines: GameDefines | None = None,
    ) -> None:
        """Initialize EndgameDetector.

        Args:
            logger: Logger instance for endgame notifications.
                Defaults to module-level logger if not provided.
            defines: GameDefines containing endgame thresholds.
                Defaults to GameDefines() with standard thresholds.
        """
        self._logger: logging.Logger = logger or logging.getLogger(__name__)
        self._defines: EndgameDefines = (defines or GameDefines()).endgame
        # Spec-070 thresholds (FR-031/032/032a/033 + FR-031a SC-016).
        self._balkanization: BalkanizationDefines = BalkanizationDefines()
        self._outcome: GameOutcome = GameOutcome.IN_PROGRESS
        self._overshoot_consecutive_ticks: int = 0
        self._pending_events: list[EndgameEvent] = []
        self._endgame_event_emitted: bool = False
        # Spec-070 FR-032 RED_OGV: rolling habitability window for slope.
        self._habitability_history: list[float] = []
        # Spec-070 FR-032a FRAGMENTED_COLLAPSE: count consecutive ticks
        # the no-majority + ≥3 sovereigns + insurgent/occupation/emergency
        # configuration has persisted.
        self._fragmented_consecutive_ticks: int = 0

    @property
    def defines(self) -> EndgameDefines:
        """Return the endgame threshold configuration.

        Returns:
            EndgameDefines containing all threshold values.
        """
        return self._defines

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
        self._habitability_history.clear()
        self._fragmented_consecutive_ticks = 0

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

        # Maintain habitability rolling window for RED_OGV slope check.
        self._update_habitability_history(new_state)

        # Spec-070 FR-033 priority order: RED_OGV → FRAGMENTED_COLLAPSE →
        # ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY.
        # First-match-wins (FR-033 last sentence).
        if self._check_red_ogv(new_state):
            self._outcome = GameOutcome.RED_OGV
            self._emit_endgame_event(new_state)
            return

        if self._check_fragmented_collapse(new_state):
            self._outcome = GameOutcome.FRAGMENTED_COLLAPSE
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

        if self._check_revolutionary_victory(new_state):
            self._outcome = GameOutcome.REVOLUTIONARY_VICTORY
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
        """Check if revolutionary victory conditions are met (FR-031 augmented).

        Existing conditions (preserved):
        - percolation_ratio >= defines.revolutionary_percolation_threshold
        - average class_consciousness > defines.revolutionary_consciousness_threshold

        Spec-070 FR-031 augmentations:
        - ABOLISH-aligned Sovereign majority (≥0.5 of active Territories)
        - aggregate_extraction_policy == CEASE
        - habitability_slope_window >= 0

        Spec-070 FR-031a (SC-016) cross-divide solidarity gate:
        - count of EdgeType.SOLIDARITY edges between settler and
          non-settler entities ≥ revolutionary_victory_min_cross_divide_solidarity_edges.

        If any spec-070 gate fails on a state that satisfies the existing
        conditions, this method returns False and the run routes to RED_OGV
        in the priority cascade.

        Args:
            state: Current WorldState to analyze.

        Returns:
            True if every gate (existing + augmented) holds.
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

        if percolation_ratio < self._defines.revolutionary_percolation_threshold:
            return False

        # Calculate average class consciousness across all social_class nodes
        total_consciousness = 0.0
        consciousness_count = 0

        for entity in state.entities.values():
            ideology = getattr(entity, "ideology", None)
            consciousness = (
                getattr(ideology, "class_consciousness", 0.0) if ideology is not None else 0.0
            )
            total_consciousness += consciousness
            consciousness_count += 1

        if consciousness_count == 0:
            return False

        average_consciousness = total_consciousness / consciousness_count
        if average_consciousness <= self._defines.revolutionary_consciousness_threshold:
            return False

        # Spec-070 FR-031 augmentations.
        if not self._has_stance_majority(state, ColonialStance.ABOLISH):
            return False
        if not self._aggregate_extraction_policy_is(state, ExtractionPolicy.CEASE):
            return False
        if self._habitability_slope() < 0:
            return False
        # Spec-070 FR-031a cross-divide solidarity gate (SC-016).
        return (
            self._count_cross_divide_solidarity_edges(state)
            >= self._balkanization.revolutionary_victory_min_cross_divide_solidarity_edges
        )

    def _check_ecological_collapse(self, state: WorldState) -> bool:
        """Check if ecological collapse conditions are met.

        Conditions:
        - overshoot_ratio > defines.ecological_overshoot_threshold for
          defines.ecological_sustained_ticks consecutive ticks

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

        if overshoot_ratio > self._defines.ecological_overshoot_threshold:
            self._overshoot_consecutive_ticks += 1
        else:
            self._overshoot_consecutive_ticks = 0

        return self._overshoot_consecutive_ticks >= self._defines.ecological_sustained_ticks

    def _check_fascist_consolidation(self, state: WorldState) -> bool:
        """Check if fascist consolidation conditions are met (FR-031 augmented).

        EITHER of two routes fires this outcome:

        Existing false-consciousness route (preserved):
        - national_identity > class_consciousness for
          defines.fascist_majority_threshold or more nodes.

        Spec-070 FR-031 political-violence route (added):
        - UPHOLD-aligned Sovereign majority AND
        - state_violence_index == max AND
        - aggregate_extraction_policy == INTENSIFY.

        Args:
            state: Current WorldState to analyze.

        Returns:
            True if either route holds.
        """
        # Existing route.
        fascist_node_count = 0
        for entity in state.entities.values():
            ideology = getattr(entity, "ideology", None)
            if ideology is not None:
                national_identity = getattr(ideology, "national_identity", 0.0)
                class_consciousness = getattr(ideology, "class_consciousness", 0.0)
            else:
                national_identity = 0.0
                class_consciousness = 0.0
            if national_identity > class_consciousness:
                fascist_node_count += 1
        if fascist_node_count >= self._defines.fascist_majority_threshold:
            return True

        # Spec-070 political-violence route.
        if not self._has_stance_majority(state, ColonialStance.UPHOLD):
            return False
        if not self._aggregate_extraction_policy_is(state, ExtractionPolicy.INTENSIFY):
            return False
        # state_violence_index sourced from graph_attr written by spec-039
        # StateApparatusAI; if absent, the political-violence route is
        # inactive (existing false-consciousness route remains the
        # only way to fire FASCIST_CONSOLIDATION).
        graph = state.to_graph()
        violence = graph.graph.get("state_violence_index", 0.0)
        violence_max = graph.graph.get("state_violence_index_max", 1.0)
        return float(violence) >= float(violence_max)

    def _check_red_ogv(self, state: WorldState) -> bool:
        """Spec-070 FR-032 RED_OGV predicate (the settler-socialist trap).

        Conditions (all four):
        - IGNORE-aligned Sovereign majority
        - class_tension < BalkanizationDefines.red_ogv_class_tension_floor
        - aggregate_habitability < red_ogv_habitability_floor
        - habitability_slope_window < 0 (negative slope confirms ecological decline)

        Returns:
            True iff RED_OGV holds.
        """
        if not self._has_stance_majority(state, ColonialStance.IGNORE):
            return False
        if self._class_tension(state) >= self._balkanization.red_ogv_class_tension_floor:
            return False
        if self._aggregate_habitability(state) >= self._balkanization.red_ogv_habitability_floor:
            return False
        return self._habitability_slope() < 0

    def _check_fragmented_collapse(self, state: WorldState) -> bool:
        """Spec-070 FR-032a FRAGMENTED_COLLAPSE predicate.

        Conditions (all four):
        - no Faction holds the supermajority
        - active sovereign count ≥ fragmented_collapse_min_sovereigns (default 3)
        - ≥1 Sovereign of type {INSURGENT, OCCUPATION, EMERGENCY}
        - configuration has persisted ≥ fragmented_collapse_min_duration_ticks
          consecutive ticks (default 10).

        Returns:
            True iff FRAGMENTED_COLLAPSE holds.
        """
        graph = state.to_graph()
        sovereigns = [
            data
            for _node_id, data in graph.nodes(data=True)
            if data.get("_node_type") == "sovereign"
        ]
        survivor_count = len(sovereigns)
        if survivor_count < self._balkanization.fragmented_collapse_min_sovereigns:
            self._fragmented_consecutive_ticks = 0
            return False
        crisis_types = {"insurgent", "occupation", "emergency"}
        has_crisis = any(str(s.get("sovereignty_type", "")) in crisis_types for s in sovereigns)
        if not has_crisis:
            self._fragmented_consecutive_ticks = 0
            return False
        # No supermajority Faction (under any active stance).
        stance_counts: dict[str, int] = {}
        for s in sovereigns:
            stance = self._lookup_sovereign_stance(state, s)
            if stance is None:
                continue
            stance_counts[stance.value] = stance_counts.get(stance.value, 0) + 1
        total = sum(stance_counts.values())
        if total > 0 and max(stance_counts.values()) / total >= 0.5:
            self._fragmented_consecutive_ticks = 0
            return False
        self._fragmented_consecutive_ticks += 1
        return (
            self._fragmented_consecutive_ticks
            >= self._balkanization.fragmented_collapse_min_duration_ticks
        )

    # ─────────────────────────────────────────────────────────────────
    # Spec-070 helpers (FR-031 / FR-031a / FR-032 / FR-032a)
    # ─────────────────────────────────────────────────────────────────

    def _update_habitability_history(self, state: WorldState) -> None:
        habitability = self._aggregate_habitability(state)
        self._habitability_history.append(habitability)
        window = self._balkanization.red_ogv_slope_window_ticks
        if len(self._habitability_history) > window:
            self._habitability_history = self._habitability_history[-window:]

    def _habitability_slope(self) -> float:
        """Linear slope of the rolling habitability window. Positive ⇒
        recovering. Negative ⇒ declining."""

        history = self._habitability_history
        if len(history) < 2:
            return 0.0
        return history[-1] - history[0]

    @staticmethod
    def _aggregate_habitability(state: WorldState) -> float:
        territories = list(state.territories.values()) if hasattr(state, "territories") else []
        if not territories:
            return 1.0
        total = sum(float(getattr(t, "habitability", 1.0)) for t in territories)
        return total / len(territories)

    @staticmethod
    def _class_tension(state: WorldState) -> float:
        """Mean ``ideology.class_consciousness`` across entities — the
        proxy for class tension used by FR-032's RED_OGV predicate."""

        consciousness_values: list[float] = []
        for entity in state.entities.values():
            ideology = getattr(entity, "ideology", None)
            if ideology is None:
                continue
            consciousness_values.append(float(getattr(ideology, "class_consciousness", 0.0)))
        if not consciousness_values:
            return 0.0
        return sum(consciousness_values) / len(consciousness_values)

    def _has_stance_majority(self, state: WorldState, target_stance: ColonialStance) -> bool:
        """Return True if the share of Territories controlled by Sovereigns
        whose ruling_faction has ``target_stance`` is ≥ 0.5."""

        graph = state.to_graph()
        sovereigns = {
            node_id: data
            for node_id, data in graph.nodes(data=True)
            if data.get("_node_type") == "sovereign"
        }
        if not sovereigns:
            return False
        # Build sovereign → stance map.
        sov_stance: dict[str, ColonialStance] = {}
        for sov_id, sov_data in sovereigns.items():
            stance = self._lookup_sovereign_stance(state, sov_data)
            if stance is not None:
                sov_stance[sov_id] = stance
        # Count territories controlled by each stance.
        target_territories = 0
        total_territories = 0
        for source, _target, data in graph.edges(data=True):
            if data.get("_edge_type") != "claims":
                continue
            total_territories += 1
            if sov_stance.get(source) is target_stance:
                target_territories += 1
        if total_territories == 0:
            return False
        return target_territories / total_territories >= 0.5

    def _aggregate_extraction_policy_is(
        self, state: WorldState, target_policy: ExtractionPolicy
    ) -> bool:
        """Return True if the majority of CLAIMS edges originate from
        Sovereigns whose extraction_policy is ``target_policy``."""

        graph = state.to_graph()
        match_count = 0
        total = 0
        for source, _target, data in graph.edges(data=True):
            if data.get("_edge_type") != "claims":
                continue
            total += 1
            sov_data = graph.nodes[source] if source in graph else {}
            policy_raw = sov_data.get("extraction_policy", "")
            if isinstance(policy_raw, ExtractionPolicy):
                policy = policy_raw
            else:
                try:
                    policy = ExtractionPolicy(str(policy_raw))
                except ValueError:
                    continue
            if policy is target_policy:
                match_count += 1
        if total == 0:
            return False
        return match_count / total >= 0.5

    def _count_cross_divide_solidarity_edges(self, state: WorldState) -> int:
        """Count active SOLIDARITY edges that cross the settler/non-settler
        colonial divide (FR-031a)."""

        graph = state.to_graph()
        # Sample heuristic: a SOLIDARITY edge is "cross-divide" when the
        # source SocialClass entity's `social_function` indicates settler
        # (e.g., labor_aristocracy) and the target's does not (or vice
        # versa). This implementation reads social-class roles from the
        # entity attributes; absent finer-grained settler-flag wiring at
        # this layer, we fall back to a count of all SOLIDARITY edges
        # crossing entities whose `national_identity > class_consciousness`
        # boundary.
        count = 0
        for source, target, data in graph.edges(data=True):
            if data.get("_edge_type") != "solidarity":
                continue
            src = state.entities.get(source) if hasattr(state, "entities") else None
            tgt = state.entities.get(target) if hasattr(state, "entities") else None
            if src is None or tgt is None:
                continue
            src_settler = self._is_settler_aligned(src)
            tgt_settler = self._is_settler_aligned(tgt)
            if src_settler != tgt_settler:
                count += 1
        return count

    @staticmethod
    def _is_settler_aligned(entity: object) -> bool:
        """Best-effort settler-alignment check on a SocialClass entity.

        Uses `ideology.national_identity > ideology.class_consciousness`
        as the proxy. Returns False if the entity has no ideology.
        """

        ideology = getattr(entity, "ideology", None)
        if ideology is None:
            return False
        ni = float(getattr(ideology, "national_identity", 0.0))
        cc = float(getattr(ideology, "class_consciousness", 0.0))
        return ni > cc

    @staticmethod
    def _lookup_sovereign_stance(
        state: WorldState, sov_data: dict[str, object]
    ) -> ColonialStance | None:
        """Resolve a Sovereign's ruling Faction → ColonialStance, or None
        when the Sovereign has no ruling_faction or the Faction is absent."""

        faction_id = sov_data.get("ruling_faction_id")
        if not isinstance(faction_id, str):
            return None
        # Look up the Faction node in the graph.
        graph = state.to_graph()
        if faction_id not in graph:
            return None
        stance_raw = graph.nodes[faction_id].get("colonial_stance")
        if not isinstance(stance_raw, str):
            return None
        try:
            return ColonialStance(stance_raw)
        except ValueError:
            return None

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
