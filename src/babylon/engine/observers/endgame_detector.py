"""EndgameDetector observer — endgame pattern recognizer (spec-116 FR-116-1).

The EndgameDetector is a SimulationObserver that monitors WorldState for
five recognized end-state patterns:

1. REVOLUTIONARY_VICTORY: percolation >= threshold AND class_consciousness > threshold
   (augmented by spec-070 FR-031/FR-031a gates: ABOLISH-aligned Sovereign
   majority, extraction CEASE, non-negative habitability slope, and a
   cross-divide solidarity floor).

2. ECOLOGICAL_COLLAPSE: overshoot_ratio > threshold for N consecutive ticks.

3. FASCIST_CONSOLIDATION: EITHER a fraction of ideology-bearing nodes with
   national_identity > class_consciousness reaches
   ``defines.endgame.fascist_majority_fraction`` (spec-116: fraction, not
   the scenario-size-degenerate absolute count), OR the spec-070 FR-031
   political-violence route (UPHOLD-aligned Sovereign majority + extraction
   INTENSIFY + state_violence_index at its max) holds.

4. RED_OGV (spec-070 FR-032): the settler-socialist trap — IGNORE-aligned
   Sovereign majority, low class tension, low aggregate habitability, and a
   declining habitability slope.

5. FRAGMENTED_COLLAPSE (spec-070 FR-032a): no Faction supermajority, ≥3
   surviving Sovereigns, an insurgent/occupation/emergency configuration,
   sustained for a minimum duration.

Priority when multiple patterns match in the same tick (spec-070 FR-033,
first-match-wins):
    RED_OGV > FRAGMENTED_COLLAPSE > ECOLOGICAL_COLLAPSE > FASCIST_CONSOLIDATION
    > REVOLUTIONARY_VICTORY

Owner ruling 2026-07-17 (spec-116 "Playability Spine"): these five patterns
are RECOGNIZED, never adjudicated — the game runs a fixed century horizon
and the detector's verdict does not terminate the simulation. ``on_tick``
re-evaluates all five axes every tick (no early return once a pattern is
recognized), so a pattern can dissolve as well as form. Each axis reports a
continuous ``progress`` in ``[0.0, 1.0]`` (the mean of that axis's clamped
gate ratios) alongside the boolean ``matched`` (every gate ratio clamped to
1.0), giving callers a live "how close" signal via :meth:`axis_progress`
instead of only a terminal yes/no.

The detector implements the Observer Pattern: it receives state change
notifications but cannot modify simulation state.

Thresholds are configurable via GameDefines.endgame / GameDefines.balkanization
for scenario customization.
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
    from babylon.topology.graph import BabylonGraph


_AXIS_KEYS: tuple[str, ...] = (
    "revolutionary_victory",
    "ecological_collapse",
    "fascist_consolidation",
    "red_ogv",
    "fragmented_collapse",
)


# =============================================================================
# ENDGAME DETECTOR OBSERVER
# =============================================================================


class EndgameDetector:
    """Observer recognizing endgame patterns (spec-116: recognizer, not adjudicator).

    Implements SimulationObserver protocol to receive state change
    notifications and re-evaluate all five endgame axes after each tick.

    The detector maintains:
    - The currently recognized pattern (``None`` if no axis is matched)
    - The tick since which the current pattern has held
    - Per-axis progress (mean clamped gate ratio) for the live "how close" HUD
    - Cross-tick counters (overshoot streak, fragmented-configuration streak,
      rolling habitability window) that several axes' gates depend on
    - Configurable thresholds via GameDefines.endgame / GameDefines.balkanization

    Attributes:
        name: Observer identifier ("EndgameDetector").
        recognized_pattern: Currently recognized GameOutcome, or None.
        pattern_since_tick: Tick at which recognized_pattern last changed, or None.
        defines: EndgameDefines containing threshold configuration.

    Example:
        >>> from babylon.engine.observers.endgame_detector import EndgameDetector
        >>> detector = EndgameDetector()
        >>> detector.recognized_pattern is None
        True
        >>> detector.pattern_since_tick is None
        True

        >>> # Custom thresholds via GameDefines
        >>> from babylon.config.defines import GameDefines, EndgameDefines
        >>> custom = GameDefines(endgame=EndgameDefines(
        ...     revolutionary_percolation_threshold=0.5,
        ...     fascist_majority_fraction=0.6,
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
        resolved_defines = defines or GameDefines()
        self._defines: EndgameDefines = resolved_defines.endgame
        # Spec-070 thresholds (FR-031/032/032a/033 + FR-031a SC-016).
        self._balkanization: BalkanizationDefines = resolved_defines.balkanization
        self._recognized: GameOutcome | None = None
        self._since_tick: int | None = None
        self._last_progress: dict[str, float] = self._zeroed_progress()
        self._overshoot_consecutive_ticks: int = 0
        self._pending_events: list[EndgameEvent] = []
        # Spec-070 FR-032 RED_OGV: rolling habitability window for slope.
        self._habitability_history: list[float] = []
        # Spec-070 FR-032a FRAGMENTED_COLLAPSE: count consecutive ticks
        # the no-majority + ≥3 sovereigns + insurgent/occupation/emergency
        # configuration has persisted.
        self._fragmented_consecutive_ticks: int = 0

    @staticmethod
    def _zeroed_progress() -> dict[str, float]:
        """Return a fresh 5-key axis-progress dict, all axes at 0.0."""
        return dict.fromkeys(_AXIS_KEYS, 0.0)

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
    def recognized_pattern(self) -> GameOutcome | None:
        """Return the currently recognized endgame pattern, or None.

        Returns:
            The first-matched GameOutcome in spec-070 FR-033 priority order,
            or None if no axis is currently matched. Patterns can dissolve:
            this is re-evaluated fresh every tick, never latched.
        """
        return self._recognized

    @property
    def pattern_since_tick(self) -> int | None:
        """Return the tick at which ``recognized_pattern`` last changed.

        Returns:
            The ``new_state.tick`` of the tick where ``recognized_pattern``
            most recently changed value (including a transition to None), or
            None if no pattern is currently recognized.
        """
        return self._since_tick

    def axis_progress(self) -> dict[str, float]:
        """Return this tick's per-axis progress, each in ``[0.0, 1.0]``.

        Returns:
            A dict with exactly the 5 keys ``revolutionary_victory``,
            ``ecological_collapse``, ``fascist_consolidation``, ``red_ogv``,
            ``fragmented_collapse``. Each value is the mean of that axis's
            clamped gate ratios; a pattern is matched iff its progress == 1.0.
        """
        return dict(self._last_progress)

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
        self._recognized = None
        self._since_tick = None
        self._last_progress = self._zeroed_progress()
        self._overshoot_consecutive_ticks = 0
        self._pending_events.clear()
        self._habitability_history.clear()
        self._fragmented_consecutive_ticks = 0

    def on_tick(
        self,
        previous_state: WorldState,  # noqa: ARG002
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes with both states for delta analysis.

        Re-evaluates all five endgame axes every tick (no early return —
        patterns can dissolve as well as form) against ONE serialized graph,
        then picks the first-matched axis in spec-070 FR-033 priority order:
        RED_OGV → FRAGMENTED_COLLAPSE → ECOLOGICAL_COLLAPSE →
        FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY.

        Args:
            previous_state: WorldState before the tick (unused).
            new_state: WorldState after the tick.
        """
        # Single graph serialization threaded through every axis evaluator
        # (previously each _check_* re-serialized independently — up to ~6
        # to_graph() calls/tick, a real cost at ~1100 territories). Hoisted
        # above the habitability-history update (Task R2) so the real
        # graph-sourced habitability feeds the RED_OGV slope window too —
        # pure serialization, no side effects, so the reorder changes
        # nothing observable.
        graph = new_state.to_graph()

        # Maintain habitability rolling window for RED_OGV slope check.
        self._update_habitability_history(graph)

        red_ogv_progress, red_ogv_matched = self._axis_red_ogv(new_state, graph)
        fragmented_progress, fragmented_matched = self._axis_fragmented_collapse(new_state, graph)
        ecological_progress, ecological_matched = self._axis_ecological_collapse(new_state, graph)
        fascist_progress, fascist_matched = self._axis_fascist_consolidation(new_state, graph)
        revolutionary_progress, revolutionary_matched = self._axis_revolutionary_victory(
            new_state, graph
        )

        self._last_progress = {
            "revolutionary_victory": revolutionary_progress,
            "ecological_collapse": ecological_progress,
            "fascist_consolidation": fascist_progress,
            "red_ogv": red_ogv_progress,
            "fragmented_collapse": fragmented_progress,
        }

        # Spec-070 FR-033 priority order: RED_OGV → FRAGMENTED_COLLAPSE →
        # ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY.
        # First-match-wins (FR-033 last sentence).
        if red_ogv_matched:
            new_pattern: GameOutcome | None = GameOutcome.RED_OGV
        elif fragmented_matched:
            new_pattern = GameOutcome.FRAGMENTED_COLLAPSE
        elif ecological_matched:
            new_pattern = GameOutcome.ECOLOGICAL_COLLAPSE
        elif fascist_matched:
            new_pattern = GameOutcome.FASCIST_CONSOLIDATION
        elif revolutionary_matched:
            new_pattern = GameOutcome.REVOLUTIONARY_VICTORY
        else:
            new_pattern = None

        if new_pattern is not self._recognized:
            self._recognized = new_pattern
            self._since_tick = new_state.tick if new_pattern is not None else None

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends.

        No-op for EndgameDetector. Endgame state is already determined.

        Args:
            final_state: Final WorldState when simulation ends (unused).
        """
        pass

    # ─────────────────────────────────────────────────────────────────
    # Gate-ratio helpers (spec-116 FR-116-1 conventions)
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _clamp01(value: float) -> float:
        """Clamp ``value`` into ``[0.0, 1.0]``."""
        return max(0.0, min(1.0, value))

    @classmethod
    def _gate_reach(cls, value: float, threshold: float) -> float:
        """Gate ratio for a "value must reach threshold T" predicate."""
        if threshold <= 0.0:
            return 1.0 if value >= threshold else 0.0
        return cls._clamp01(value / threshold)

    @classmethod
    def _gate_floor(cls, value: float, floor: float) -> float:
        """Gate ratio for a "value must stay at/below floor F" predicate."""
        if value <= floor:
            return 1.0
        if floor <= 0.0:
            return 0.0
        return cls._clamp01(floor / value)

    @staticmethod
    def _gate_binary(condition: bool) -> float:
        """Gate ratio for a binary predicate (slope sign, stance majority, ...)."""
        return 1.0 if condition else 0.0

    @classmethod
    def _gate_counter(cls, count: float, required: float) -> float:
        """Gate ratio for a counter predicate (sustained/duration)."""
        if required <= 0.0:
            return 1.0
        return cls._clamp01(count / required)

    @staticmethod
    def _progress_and_match(ratios: list[float]) -> tuple[float, bool]:
        """Combine per-gate ratios into an axis's (progress, matched) pair.

        ``progress`` is the mean of the clamped gate ratios; ``matched``
        holds iff every gate ratio has clamped to 1.0 (so matched ⟺
        progress == 1.0).
        """
        if not ratios:
            return 0.0, False
        matched = all(ratio >= 1.0 for ratio in ratios)
        progress = sum(ratios) / len(ratios)
        return progress, matched

    # ─────────────────────────────────────────────────────────────────
    # Axis evaluators: (state, graph) -> (progress, matched)
    # ─────────────────────────────────────────────────────────────────

    def _axis_revolutionary_victory(
        self, state: WorldState, graph: BabylonGraph
    ) -> tuple[float, bool]:
        """Revolutionary victory axis (FR-031 augmented).

        Gates (all contribute to progress; matched requires every gate to
        clamp to 1.0):
        - percolation_ratio reaches revolutionary_percolation_threshold
        - average class_consciousness reaches revolutionary_consciousness_threshold
        - ABOLISH-aligned Sovereign majority (≥0.5 of active Territories)
        - aggregate_extraction_policy == CEASE
        - habitability_slope_window >= 0
        - cross-divide SOLIDARITY edge count reaches the FR-031a (SC-016) floor

        Args:
            state: Current WorldState to analyze.
            graph: This tick's single serialized BabylonGraph.

        Returns:
            (progress, matched) per the spec-116 gate-ratio conventions.
        """
        social_class_nodes = [
            node_id
            for node_id, data in graph.nodes(data=True)
            if data.get("_node_type") == "social_class"
        ]
        total_nodes = len(social_class_nodes)
        if total_nodes == 0:
            return 0.0, False

        solidarity_graph = extract_solidarity_subgraph(graph)
        _, _, percolation_ratio = calculate_component_metrics(solidarity_graph, total_nodes)
        percolation_gate = self._gate_reach(
            percolation_ratio, self._defines.revolutionary_percolation_threshold
        )

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
            return 0.0, False
        average_consciousness = total_consciousness / consciousness_count
        consciousness_gate = self._gate_reach(
            average_consciousness, self._defines.revolutionary_consciousness_threshold
        )

        stance_gate = self._gate_binary(self._has_stance_majority(ColonialStance.ABOLISH, graph))
        extraction_gate = self._gate_binary(
            self._aggregate_extraction_policy_is(ExtractionPolicy.CEASE, graph)
        )
        slope_gate = self._gate_binary(self._habitability_slope() >= 0)
        cross_divide_gate = self._gate_counter(
            self._count_cross_divide_solidarity_edges(state, graph),
            self._balkanization.revolutionary_victory_min_cross_divide_solidarity_edges,
        )

        ratios = [
            percolation_gate,
            consciousness_gate,
            stance_gate,
            extraction_gate,
            slope_gate,
            cross_divide_gate,
        ]
        return self._progress_and_match(ratios)

    def _axis_ecological_collapse(
        self,
        state: WorldState,
        graph: BabylonGraph,  # noqa: ARG002
    ) -> tuple[float, bool]:
        """Ecological collapse axis: sustained overshoot counter gate.

        Args:
            state: Current WorldState to analyze.
            graph: This tick's single serialized BabylonGraph (unused — this
                axis reads consumption/biocapacity straight off WorldState).

        Returns:
            (progress, matched) — a single counter gate:
            clamp01(overshoot_consecutive_ticks / ecological_sustained_ticks).
        """
        total_consumption = 0.0
        for entity in state.entities.values():
            s_bio = getattr(entity, "s_bio", 0.0)
            s_class = getattr(entity, "s_class", 0.0)
            total_consumption += s_bio + s_class

        total_biocapacity = 0.0
        for territory in state.territories.values():
            total_biocapacity += getattr(territory, "biocapacity", 0.0)

        if total_biocapacity <= 0.0:
            self._overshoot_consecutive_ticks = 0
            return 0.0, False

        overshoot_ratio = total_consumption / total_biocapacity
        if overshoot_ratio > self._defines.ecological_overshoot_threshold:
            self._overshoot_consecutive_ticks += 1
        else:
            self._overshoot_consecutive_ticks = 0

        gate = self._gate_counter(
            self._overshoot_consecutive_ticks, self._defines.ecological_sustained_ticks
        )
        return gate, gate >= 1.0

    def _axis_fascist_consolidation(
        self, state: WorldState, graph: BabylonGraph
    ) -> tuple[float, bool]:
        """Fascist consolidation axis (FR-031 augmented, spec-116 fraction).

        EITHER route below contributes to this axis; the axis's overall
        progress is the better of the two routes and matches iff either
        route's gates all clamp to 1.0 (preserves the pre-existing "either
        route fires" semantics under the new gate-ratio model):

        False-consciousness route (spec-116: fraction, not absolute count):
        - fascist_fraction = fascist_node_count / max(1, ideology_bearing_nodes)
          reaches defines.endgame.fascist_majority_fraction.

        Political-violence route (spec-070 FR-031, unchanged):
        - UPHOLD-aligned Sovereign majority AND
        - aggregate_extraction_policy == INTENSIFY AND
        - state_violence_index == state_violence_index_max.

        Args:
            state: Current WorldState to analyze.
            graph: This tick's single serialized BabylonGraph.

        Returns:
            (progress, matched) per the spec-116 gate-ratio conventions.
        """
        fascist_node_count = 0
        ideology_bearing_nodes = 0
        for entity in state.entities.values():
            ideology = getattr(entity, "ideology", None)
            if ideology is not None:
                ideology_bearing_nodes += 1
                national_identity = getattr(ideology, "national_identity", 0.0)
                class_consciousness = getattr(ideology, "class_consciousness", 0.0)
            else:
                national_identity = 0.0
                class_consciousness = 0.0
            if national_identity > class_consciousness:
                fascist_node_count += 1
        fascist_fraction = fascist_node_count / max(1, ideology_bearing_nodes)
        false_consciousness_gate = self._gate_reach(
            fascist_fraction, self._defines.fascist_majority_fraction
        )
        false_consciousness_progress = false_consciousness_gate
        false_consciousness_matched = false_consciousness_gate >= 1.0

        stance_gate = self._gate_binary(self._has_stance_majority(ColonialStance.UPHOLD, graph))
        extraction_gate = self._gate_binary(
            self._aggregate_extraction_policy_is(ExtractionPolicy.INTENSIFY, graph)
        )
        # state_violence_index sourced from graph_attr written by spec-039
        # StateApparatusAI; if absent, this route's gate simply won't reach
        # 1.0 (the false-consciousness route remains independently viable).
        violence = graph.graph.get("state_violence_index", 0.0)
        violence_max = graph.graph.get("state_violence_index_max", 1.0)
        violence_gate = self._gate_binary(float(violence) >= float(violence_max))
        violence_route_progress, violence_route_matched = self._progress_and_match(
            [stance_gate, extraction_gate, violence_gate]
        )

        progress = max(false_consciousness_progress, violence_route_progress)
        matched = false_consciousness_matched or violence_route_matched
        return progress, matched

    def _axis_red_ogv(self, state: WorldState, graph: BabylonGraph) -> tuple[float, bool]:
        """RED_OGV axis (spec-070 FR-032, the settler-socialist trap).

        Gates:
        - IGNORE-aligned Sovereign majority
        - class_tension stays at/below red_ogv_class_tension_floor
        - aggregate_habitability stays at/below red_ogv_habitability_floor
        - habitability_slope_window < 0 (negative slope confirms decline)

        Args:
            state: Current WorldState to analyze.
            graph: This tick's single serialized BabylonGraph.

        Returns:
            (progress, matched) per the spec-116 gate-ratio conventions.
        """
        stance_gate = self._gate_binary(self._has_stance_majority(ColonialStance.IGNORE, graph))
        class_tension_gate = self._gate_floor(
            self._class_tension(state), self._balkanization.red_ogv_class_tension_floor
        )
        habitability_gate = self._gate_floor(
            self._aggregate_habitability(graph), self._balkanization.red_ogv_habitability_floor
        )
        slope_gate = self._gate_binary(self._habitability_slope() < 0)

        ratios = [stance_gate, class_tension_gate, habitability_gate, slope_gate]
        return self._progress_and_match(ratios)

    def _axis_fragmented_collapse(
        self,
        state: WorldState,  # noqa: ARG002
        graph: BabylonGraph,
    ) -> tuple[float, bool]:
        """FRAGMENTED_COLLAPSE axis (spec-070 FR-032a).

        Gates:
        - active sovereign count reaches fragmented_collapse_min_sovereigns
        - ≥1 Sovereign of type {INSURGENT, OCCUPATION, EMERGENCY}
        - no Faction holds the supermajority (stays at/below 0.5 share)
        - configuration has persisted ≥ fragmented_collapse_min_duration_ticks
          consecutive ticks

        Args:
            state: Current WorldState (unused — this axis is graph-native).
            graph: This tick's single serialized BabylonGraph.

        Returns:
            (progress, matched) per the spec-116 gate-ratio conventions.
        """
        sovereigns = [
            data
            for _node_id, data in graph.nodes(data=True)
            if data.get("_node_type") == "sovereign"
        ]
        survivor_count = len(sovereigns)
        survivor_gate = self._gate_reach(
            survivor_count, self._balkanization.fragmented_collapse_min_sovereigns
        )

        crisis_types = {"insurgent", "occupation", "emergency"}
        has_crisis = any(str(s.get("sovereignty_type", "")) in crisis_types for s in sovereigns)
        crisis_gate = self._gate_binary(has_crisis)

        stance_counts: dict[str, int] = {}
        for s in sovereigns:
            stance = self._lookup_sovereign_stance(s, graph)
            if stance is None:
                continue
            stance_counts[stance.value] = stance_counts.get(stance.value, 0) + 1
        total = sum(stance_counts.values())
        supermajority_share = max(stance_counts.values()) / total if total > 0 else 0.0
        supermajority_gate = self._gate_floor(supermajority_share, 0.5)

        conditions_hold = (
            survivor_count >= self._balkanization.fragmented_collapse_min_sovereigns
            and has_crisis
            and not (total > 0 and supermajority_share >= 0.5)
        )
        if conditions_hold:
            self._fragmented_consecutive_ticks += 1
        else:
            self._fragmented_consecutive_ticks = 0

        duration_gate = self._gate_counter(
            self._fragmented_consecutive_ticks,
            self._balkanization.fragmented_collapse_min_duration_ticks,
        )

        ratios = [survivor_gate, crisis_gate, supermajority_gate, duration_gate]
        return self._progress_and_match(ratios)

    # ─────────────────────────────────────────────────────────────────
    # Spec-070 helpers (FR-031 / FR-031a / FR-032 / FR-032a)
    # ─────────────────────────────────────────────────────────────────

    def _update_habitability_history(self, graph: BabylonGraph) -> None:
        habitability = self._aggregate_habitability(graph)
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
    def _aggregate_habitability(graph: BabylonGraph) -> float:
        """Mean ``habitability`` across the graph's ``territory`` nodes.

        ``habitability`` is a graph-only transient attribute (written by
        MetabolismSystem, excluded from the frozen ``Territory`` model's
        graph round-trip — see ``TERRITORY_EXCLUDED_FIELDS`` in
        ``world_state.py``), so it must be read here, not off
        ``state.territories`` (mirrors the graph-territory-node idiom in
        ``balkanization_projections.py``'s ``observe_sovereign``)."""
        habitability_values = [
            float(data.get("habitability", 1.0))
            for _node_id, data in graph.nodes(data=True)
            if data.get("_node_type") == "territory"
        ]
        if not habitability_values:
            return 1.0
        return sum(habitability_values) / len(habitability_values)

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

    def _has_stance_majority(self, target_stance: ColonialStance, graph: BabylonGraph) -> bool:
        """Return True if the share of Territories controlled by Sovereigns
        whose ruling_faction has ``target_stance`` is ≥ 0.5."""

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
            stance = self._lookup_sovereign_stance(sov_data, graph)
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
        self, target_policy: ExtractionPolicy, graph: BabylonGraph
    ) -> bool:
        """Return True if the majority of CLAIMS edges originate from
        Sovereigns whose extraction_policy is ``target_policy``."""

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

    def _count_cross_divide_solidarity_edges(self, state: WorldState, graph: BabylonGraph) -> int:
        """Count active SOLIDARITY edges that cross the settler/non-settler
        colonial divide (FR-031a)."""

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
        sov_data: dict[str, object], graph: BabylonGraph
    ) -> ColonialStance | None:
        """Resolve a Sovereign's ruling Faction → ColonialStance, or None
        when the Sovereign has no ruling_faction or the Faction is absent."""

        faction_id = sov_data.get("ruling_faction_id")
        if not isinstance(faction_id, str):
            return None
        if faction_id not in graph:
            return None
        stance_raw = graph.nodes[faction_id].get("colonial_stance")
        if not isinstance(stance_raw, str):
            return None
        try:
            return ColonialStance(stance_raw)
        except ValueError:
            return None
