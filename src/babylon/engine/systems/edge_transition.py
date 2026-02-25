"""EdgeTransitionSystem — System #16 in materialist causality order.

Dialectical Field Topology (Feature 002): Evaluates compound predicates
against field values, derivatives, and structural properties. Fires edge
mode transitions per the state machine. Handles contradiction character
flags and aspect reversal detection.

Reference: FR-007 (compound predicates), FR-010 (transition topology)
Reference: FR-018 (contradiction character flag), FR-019 (aspect reversal)
Reference: R-002 (EdgeMode vs EdgeType), R-005 (predicate design)
Reference: R-006 (system ordering — position 16)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.event_bus import Event
from babylon.engine.systems.protocol import ContextType
from babylon.models.enums import ContradictionCharacter, EdgeMode, EventType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Pydantic Models for Predicates and Transitions
# ─────────────────────────────────────────────────────────────────────


class PredicateCondition(BaseModel):
    """A single condition in a compound predicate.

    Args:
        field: Contradiction field name (e.g., "exploitation").
        metric: Which metric to evaluate ("value", "df_dt", "d2f_dt2", "laplacian").
        operator: Comparison operator ("gt", "lt", "gte", "lte").
        threshold: Threshold value for comparison.
        scope: Which node to evaluate at ("source", "target").
    """

    model_config = ConfigDict(frozen=True)

    field: str
    metric: str = Field(description="value, df_dt, d2f_dt2, laplacian")
    operator: str = Field(description="gt, lt, gte, lte")
    threshold: float
    scope: str = Field(default="source", description="source or target")


class CompoundPredicate(BaseModel):
    """A named compound predicate — conjunction of conditions.

    All conditions must be true (AND logic) for the predicate to fire.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    conditions: list[PredicateCondition]


class EdgeModeTransition(BaseModel):
    """A permissible edge mode transition.

    Defines a directed arc in the state machine from from_mode to to_mode,
    gated by a compound predicate, with priority for tie-breaking.
    """

    model_config = ConfigDict(frozen=True)

    from_mode: EdgeMode
    to_mode: EdgeMode
    predicate: CompoundPredicate
    priority: int = Field(default=0, description="Higher priority wins")
    description: str = ""


# ─────────────────────────────────────────────────────────────────────
# Transition Definitions (FR-010: 17 permissible transitions)
# ─────────────────────────────────────────────────────────────────────

_TRANSITIONS: list[EdgeModeTransition] = [
    # EXTRACTIVE transitions
    EdgeModeTransition(
        from_mode=EdgeMode.EXTRACTIVE,
        to_mode=EdgeMode.ANTAGONISTIC,
        predicate=CompoundPredicate(
            name="extraction_contested",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=5.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="df_dt",
                    operator="gt",
                    threshold=0.0,
                    scope="source",
                ),
            ],
        ),
        priority=10,
        description="Extraction contested: exploitation high and rising",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.EXTRACTIVE,
        to_mode=EdgeMode.TRANSACTIONAL,
        predicate=CompoundPredicate(
            name="extraction_broken",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="lt",
                    threshold=2.0,
                    scope="source",
                ),
            ],
        ),
        priority=5,
        description="Extraction broken: exploitation reduced below threshold",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.EXTRACTIVE,
        to_mode=EdgeMode.CO_OPTIVE,
        predicate=CompoundPredicate(
            name="concessions_offered",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=3.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="imperial_rent",
                    metric="value",
                    operator="gt",
                    threshold=2.0,
                    scope="target",
                ),
            ],
        ),
        priority=8,
        description="Concessions offered to prevent resistance",
    ),
    # TRANSACTIONAL transitions
    EdgeModeTransition(
        from_mode=EdgeMode.TRANSACTIONAL,
        to_mode=EdgeMode.SOLIDARISTIC,
        predicate=CompoundPredicate(
            name="mutual_aid_established",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="lt",
                    threshold=2.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="lt",
                    threshold=2.0,
                    scope="target",
                ),
            ],
        ),
        priority=5,
        description="Mutual aid: low exploitation on both sides",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.TRANSACTIONAL,
        to_mode=EdgeMode.ANTAGONISTIC,
        predicate=CompoundPredicate(
            name="market_failure",
            conditions=[
                PredicateCondition(
                    field="immiseration",
                    metric="df_dt",
                    operator="gt",
                    threshold=1.0,
                    scope="source",
                ),
            ],
        ),
        priority=10,
        description="Market failure: immiseration rapidly increasing",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.TRANSACTIONAL,
        to_mode=EdgeMode.EXTRACTIVE,
        predicate=CompoundPredicate(
            name="power_asymmetry_emerges",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=5.0,
                    scope="source",
                ),
            ],
        ),
        priority=7,
        description="Power asymmetry: exploitation re-emerges",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.TRANSACTIONAL,
        to_mode=EdgeMode.CO_OPTIVE,
        predicate=CompoundPredicate(
            name="co_optive_power",
            conditions=[
                PredicateCondition(
                    field="imperial_rent",
                    metric="value",
                    operator="gt",
                    threshold=3.0,
                    scope="target",
                ),
            ],
        ),
        priority=6,
        description="One party offers above-market benefits for loyalty",
    ),
    # SOLIDARISTIC transitions
    EdgeModeTransition(
        from_mode=EdgeMode.SOLIDARISTIC,
        to_mode=EdgeMode.TRANSACTIONAL,
        predicate=CompoundPredicate(
            name="solidarity_degrades",
            conditions=[
                PredicateCondition(
                    field="immiseration",
                    metric="value",
                    operator="gt",
                    threshold=6.0,
                    scope="source",
                ),
            ],
        ),
        priority=5,
        description="Solidarity degrades under crisis pressure",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.SOLIDARISTIC,
        to_mode=EdgeMode.ANTAGONISTIC,
        predicate=CompoundPredicate(
            name="betrayal",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="df_dt",
                    operator="gt",
                    threshold=3.0,
                    scope="source",
                ),
            ],
        ),
        priority=10,
        description="Betrayal: exploitation spikes within solidarity",
    ),
    # ANTAGONISTIC transitions
    EdgeModeTransition(
        from_mode=EdgeMode.ANTAGONISTIC,
        to_mode=EdgeMode.TRANSACTIONAL,
        predicate=CompoundPredicate(
            name="conflict_resolved",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="df_dt",
                    operator="lte",
                    threshold=0.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="lt",
                    threshold=3.0,
                    scope="source",
                ),
            ],
        ),
        priority=5,
        description="Conflict resolved: exploitation falling and low",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.ANTAGONISTIC,
        to_mode=EdgeMode.SOLIDARISTIC,
        predicate=CompoundPredicate(
            name="shared_enemy_alliance",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=7.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=7.0,
                    scope="target",
                ),
            ],
        ),
        priority=8,
        description="Shared enemy produces alliance (I.15 united front)",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.ANTAGONISTIC,
        to_mode=EdgeMode.CO_OPTIVE,
        predicate=CompoundPredicate(
            name="reform_concession",
            conditions=[
                PredicateCondition(
                    field="imperial_rent",
                    metric="value",
                    operator="gt",
                    threshold=3.0,
                    scope="target",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="df_dt",
                    operator="lt",
                    threshold=0.0,
                    scope="source",
                ),
            ],
        ),
        priority=6,
        description="Conflict resolved through concession (reform)",
    ),
    # CO-OPTIVE transitions
    EdgeModeTransition(
        from_mode=EdgeMode.CO_OPTIVE,
        to_mode=EdgeMode.TRANSACTIONAL,
        predicate=CompoundPredicate(
            name="co_optation_normalizes",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="lt",
                    threshold=2.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="df_dt",
                    operator="lte",
                    threshold=0.0,
                    scope="source",
                ),
            ],
        ),
        priority=5,
        description="Co-optation normalizes into market relations",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.CO_OPTIVE,
        to_mode=EdgeMode.ANTAGONISTIC,
        predicate=CompoundPredicate(
            name="co_optive_breakdown",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="df_dt",
                    operator="gt",
                    threshold=1.0,
                    scope="source",
                ),
            ],
        ),
        priority=10,
        description="CO-OPTIVE breakdown: material basis erodes (George Jackson)",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.CO_OPTIVE,
        to_mode=EdgeMode.SOLIDARISTIC,
        predicate=CompoundPredicate(
            name="co_optation_recognized",
            conditions=[
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=5.0,
                    scope="source",
                ),
                PredicateCondition(
                    field="exploitation",
                    metric="value",
                    operator="gt",
                    threshold=5.0,
                    scope="target",
                ),
            ],
        ),
        priority=3,
        description="Co-opted party recognizes co-optation, chooses solidarity",
    ),
    EdgeModeTransition(
        from_mode=EdgeMode.CO_OPTIVE,
        to_mode=EdgeMode.EXTRACTIVE,
        predicate=CompoundPredicate(
            name="concessions_withdrawn",
            conditions=[
                PredicateCondition(
                    field="imperial_rent",
                    metric="value",
                    operator="lt",
                    threshold=1.0,
                    scope="target",
                ),
            ],
        ),
        priority=7,
        description="Concessions withdrawn, reverts to extraction",
    ),
]

# Build lookup: from_mode -> list of transitions
_TRANSITION_MAP: dict[EdgeMode, list[EdgeModeTransition]] = {}
for _t in _TRANSITIONS:
    _TRANSITION_MAP.setdefault(_t.from_mode, []).append(_t)

# Valid from->to pairs (for state machine enforcement)
_VALID_TRANSITIONS: set[tuple[EdgeMode, EdgeMode]] = {
    (t.from_mode, t.to_mode) for t in _TRANSITIONS
}
# ANTAGONISTIC -> ANTAGONISTIC is also valid (persistence)
_VALID_TRANSITIONS.add((EdgeMode.ANTAGONISTIC, EdgeMode.ANTAGONISTIC))


# ─────────────────────────────────────────────────────────────────────
# Predicate Evaluation
# ─────────────────────────────────────────────────────────────────────


def _evaluate_condition(
    condition: PredicateCondition,
    source_attrs: dict[str, Any],
    target_attrs: dict[str, Any],
) -> bool:
    """Evaluate a single predicate condition.

    Args:
        condition: The condition to evaluate.
        source_attrs: Source node attributes.
        target_attrs: Target node attributes.

    Returns:
        True if the condition is satisfied.
    """
    node_attrs = source_attrs if condition.scope == "source" else target_attrs

    # Get the value to compare
    if condition.metric == "value":
        fields: dict[str, float] = node_attrs.get("contradiction_fields", {})
        value = fields.get(condition.field, 0.0)
    elif condition.metric in ("df_dt", "d2f_dt2", "laplacian"):
        derivs: dict[str, dict[str, float | None]] = node_attrs.get("field_derivatives", {})
        field_deriv = derivs.get(condition.field, {})
        raw = field_deriv.get(condition.metric)
        if raw is None:
            return False  # EC-001: undefined derivative cannot satisfy predicate
        value = float(raw)
    else:
        return False

    # Compare
    if condition.operator == "gt":
        return value > condition.threshold
    if condition.operator == "lt":
        return value < condition.threshold
    if condition.operator == "gte":
        return value >= condition.threshold
    if condition.operator == "lte":
        return value <= condition.threshold
    return False


def _evaluate_predicate(
    predicate: CompoundPredicate,
    source_attrs: dict[str, Any],
    target_attrs: dict[str, Any],
) -> bool:
    """Evaluate a compound predicate (conjunction of conditions).

    Args:
        predicate: The compound predicate.
        source_attrs: Source node attributes.
        target_attrs: Target node attributes.

    Returns:
        True if ALL conditions are satisfied.
    """
    return all(_evaluate_condition(c, source_attrs, target_attrs) for c in predicate.conditions)


# ─────────────────────────────────────────────────────────────────────
# System Implementation
# ─────────────────────────────────────────────────────────────────────


class EdgeTransitionSystem:
    """Evaluate compound predicates and fire edge mode transitions.

    Execution Order: 16 (after FieldDerivativeSystem)

    For each edge with an edge_mode, evaluates eligible transitions
    from the current mode. If a predicate fires, transitions to the
    new mode. Priority ordering resolves multiple eligible transitions.
    """

    name = "edge_transition"

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Evaluate predicates and fire edge mode transitions.

        Args:
            graph: Mutable graph (NetworkX or GraphProtocol).
            services: ServiceContainer with field_registry.
            context: TickContext or dict with tick and persistent_data.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        registry = services.field_registry
        if registry is None:
            return

        tick: int = 0
        if hasattr(context, "tick"):
            tick = context.tick
        elif isinstance(context, dict):
            tick_val = context.get("tick", 0)
            tick = int(tick_val) if tick_val is not None else 0

        # Process all edges with edge_mode
        for edge in graph.query_edges():
            edge_attrs = dict(edge.attributes)
            current_mode_str = edge_attrs.get("edge_mode")
            if current_mode_str is None:
                continue

            # Parse current mode
            try:
                current_mode = EdgeMode(current_mode_str)
            except ValueError:
                continue

            # Ensure contradiction_character is set (FR-018)
            if "contradiction_character" not in edge_attrs:
                graph.update_edge(
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type,
                    contradiction_character=ContradictionCharacter.NON_ANTAGONISTIC,
                )

            # Get source and target node attributes
            src_node = graph.get_node(edge.source_id)
            tgt_node = graph.get_node(edge.target_id)
            if src_node is None or tgt_node is None:
                continue

            source_attrs = dict(src_node.attributes)
            target_attrs = dict(tgt_node.attributes)

            # Evaluate eligible transitions
            eligible = _TRANSITION_MAP.get(current_mode, [])
            fired: list[EdgeModeTransition] = []
            for transition in eligible:
                if _evaluate_predicate(transition.predicate, source_attrs, target_attrs):
                    fired.append(transition)

            # Select highest-priority transition (EC-003)
            if fired:
                best = max(fired, key=lambda t: t.priority)
                new_mode = best.to_mode

                if new_mode != current_mode:
                    graph.update_edge(
                        edge.source_id,
                        edge.target_id,
                        edge.edge_type,
                        edge_mode=new_mode,
                    )

                    services.event_bus.publish(
                        Event(
                            type=EventType.EDGE_MODE_TRANSITION,
                            tick=tick,
                            payload={
                                "source_id": edge.source_id,
                                "target_id": edge.target_id,
                                "from_mode": current_mode,
                                "to_mode": new_mode,
                                "predicate": best.predicate.name,
                                "description": best.description,
                            },
                        )
                    )

            # Aspect reversal detection (FR-019)
            _check_aspect_reversal(graph, edge, source_attrs, target_attrs, services, tick)


def _check_aspect_reversal(
    graph: GraphProtocol,
    edge: Any,
    source_attrs: dict[str, Any],
    target_attrs: dict[str, Any],
    services: ServiceContainer,
    tick: int,
) -> None:
    """Detect and emit aspect reversal events (FR-019).

    Aspect reversal occurs when the dominant party on a directed edge
    switches. Dominant party = higher wealth (material power).

    Args:
        graph: Graph protocol instance.
        edge: The edge being processed.
        source_attrs: Source node attributes.
        target_attrs: Target node attributes.
        services: For event bus access.
        tick: Current tick number.
    """
    edge_attrs = dict(edge.attributes)
    previous_dominant = edge_attrs.get("_dominant_party")

    # Determine current dominant by material power (wealth)
    source_wealth = float(source_attrs.get("wealth", 0.0))
    target_wealth = float(target_attrs.get("wealth", 0.0))

    if source_wealth > target_wealth:
        current_dominant = edge.source_id
    elif target_wealth > source_wealth:
        current_dominant = edge.target_id
    else:
        current_dominant = previous_dominant  # No change if equal

    # Update dominant party on edge
    if current_dominant is not None:
        graph.update_edge(
            edge.source_id,
            edge.target_id,
            edge.edge_type,
            _dominant_party=current_dominant,
        )

    # Emit reversal event if dominant changed
    if (
        previous_dominant is not None
        and current_dominant is not None
        and previous_dominant != current_dominant
    ):
        services.event_bus.publish(
            Event(
                type=EventType.ASPECT_REVERSAL,
                tick=tick,
                payload={
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "previous_dominant": previous_dominant,
                    "new_dominant": current_dominant,
                },
            )
        )
