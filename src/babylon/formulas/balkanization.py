"""Spec-070 Balkanization formulas (FR-003, FR-004, FR-007, FR-021,
FR-029b, FR-034).

This module exposes pure deterministic functions consumed by the three
new Systems (FactionInfluenceSystem, SovereigntySystem,
CollapseTransitionSystem). All multipliers and thresholds funnel through
:class:`babylon.config.defines.balkanization.BalkanizationDefines` so no
magic numbers appear at the system layer (Constitution III.1).
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.models.enums import ColonialStance, ExtractionPolicy

if TYPE_CHECKING:  # pragma: no cover - import-only
    from babylon.kernel.graph_protocol import GraphProtocol


# StanceToPolicyMapping (data-model.md §3.2). Deterministic.
_STANCE_TO_POLICY: dict[ColonialStance, ExtractionPolicy] = {
    ColonialStance.UPHOLD: ExtractionPolicy.INTENSIFY,
    ColonialStance.IGNORE: ExtractionPolicy.CONTINUE,
    ColonialStance.ABOLISH: ExtractionPolicy.CEASE,
}


def calculate_metabolic_impact(
    policy: ExtractionPolicy,
    defines: BalkanizationDefines | None = None,
) -> float:
    """Return the per-tick habitability change for a given
    :class:`ExtractionPolicy` (spec-070 FR-004).

    The default mapping is:

    - INTENSIFY → ``-0.02``
    - CONTINUE  → ``-0.005``
    - CEASE     → ``+0.01``

    Override any of the three via
    :class:`~babylon.config.defines.balkanization.BalkanizationDefines`
    (no magic numbers at the system layer, Constitution III.1).

    Args:
        policy: The Sovereign's current extraction policy.
        defines: Optional override defines; uses canonical defaults when
            omitted.

    Returns:
        Per-tick habitability change to apply along each CLAIMS edge.

    Raises:
        ValueError: If ``policy`` is not a recognized
            :class:`ExtractionPolicy` member.

    Example:
        >>> from babylon.models.enums import ExtractionPolicy
        >>> calculate_metabolic_impact(ExtractionPolicy.INTENSIFY)
        -0.02
    """

    if defines is None:
        defines = BalkanizationDefines()
    if policy is ExtractionPolicy.INTENSIFY:
        return defines.metabolic_impact_intensify
    if policy is ExtractionPolicy.CONTINUE:
        return defines.metabolic_impact_continue
    if policy is ExtractionPolicy.CEASE:
        return defines.metabolic_impact_cease
    raise ValueError(f"Unknown ExtractionPolicy: {policy!r}")


def derive_extraction_policy_from_stance(stance: ColonialStance) -> ExtractionPolicy:
    """Derive the Sovereign's :class:`ExtractionPolicy` from a Faction's
    :class:`ColonialStance` (spec-070 FR-003).

    Mapping (data-model.md §3.2; deterministic):

    - UPHOLD  → INTENSIFY
    - IGNORE  → CONTINUE
    - ABOLISH → CEASE

    Args:
        stance: The ruling Faction's colonial stance.

    Returns:
        Derived ExtractionPolicy.

    Raises:
        KeyError: If ``stance`` is not a recognized ColonialStance member.

    Example:
        >>> from babylon.models.enums import ColonialStance
        >>> derive_extraction_policy_from_stance(ColonialStance.UPHOLD)
        <ExtractionPolicy.INTENSIFY: 'intensify'>
    """

    return _STANCE_TO_POLICY[stance]


def derive_default_multipliers_from_stance(
    stance: ColonialStance,
    defines: BalkanizationDefines | None = None,
) -> tuple[float, float, float, float]:
    """Return the canonical 4-tuple of Faction mechanical multipliers
    (FR-007 + data-model.md §3.1) for a given :class:`ColonialStance`.

    Tuple order is::

        (extraction_modifier, violence_modifier,
         class_reduction, metabolic_reduction)

    The default mapping (overridable via
    :class:`~babylon.config.defines.balkanization.BalkanizationDefines`):

    +---------+-----------+----------+------------+------------+
    | Stance  | extraction| violence | class_red. | metab_red. |
    +=========+===========+==========+============+============+
    | UPHOLD  |       1.5 |      2.0 |        0.0 |       -0.5 |
    | IGNORE  |       0.8 |      0.5 |        0.7 |        0.0 |
    | ABOLISH |       0.0 |      0.3 |        0.5 |       +0.8 |
    +---------+-----------+----------+------------+------------+

    Args:
        stance: The Faction's colonial stance.
        defines: Optional override defines; uses canonical defaults when
            omitted.

    Returns:
        4-tuple of multipliers in the canonical order above.

    Raises:
        KeyError: If ``stance`` is not a recognized ColonialStance member.

    Example:
        >>> from babylon.models.enums import ColonialStance
        >>> derive_default_multipliers_from_stance(ColonialStance.UPHOLD)
        (1.5, 2.0, 0.0, -0.5)
    """

    if defines is None:
        defines = BalkanizationDefines()
    key = stance.value
    return (
        defines.stance_extraction_modifier[key],
        defines.stance_violence_modifier[key],
        defines.stance_class_reduction[key],
        defines.stance_metabolic_reduction[key],
    )


def winning_faction_for_territory(
    graph: GraphProtocol,
    territory_id: str,
    incumbent_faction_id: str | None,
    rng: random.Random,
) -> str | None:
    """Determine the winning :class:`BalkanizationFaction` for a Territory
    (spec-070 FR-021).

    Computes ``argmax_f Σ INFLUENCES(f → territory).influence_level`` with
    a two-stage tiebreaker:

    1. If the incumbent ruling_faction is among the tied factions, the
       incumbent wins (stability preserved).
    2. Otherwise, draw deterministically from ``rng`` over the sorted-ID
       tied set.

    Args:
        graph: GraphProtocol exposing
            :meth:`query_faction_influence_by_territory`.
        territory_id: Target Territory node ID.
        incumbent_faction_id: ID of the Territory's current ruling
            Faction, if any. May be ``None`` for unclaimed territory.
        rng: Seeded :class:`random.Random` used for deterministic
            tiebreaking when no incumbent participates.

    Returns:
        The winning Faction ID, or ``None`` if the Territory has zero
        incoming INFLUENCES.

    Raises:
        AttributeError: If ``graph`` does not implement
            :meth:`query_faction_influence_by_territory`.
    """

    rows = list(graph.query_faction_influence_by_territory(territory_id))
    if not rows:
        return None
    # rows: list[(faction_id, influence_level, support_type)]
    totals: dict[str, float] = {}
    for row in rows:
        faction_id = row[0]
        influence_level = row[1]
        totals[faction_id] = totals.get(faction_id, 0.0) + float(influence_level)
    if not totals:
        return None
    # Identify the maximum total (with epsilon tolerance to avoid
    # float-noise ties masking true ties).
    max_total = max(totals.values())
    eps = 1e-12
    tied = sorted(faction_id for faction_id, total in totals.items() if (max_total - total) <= eps)
    if len(tied) == 1:
        return tied[0]
    if incumbent_faction_id is not None and incumbent_faction_id in tied:
        return incumbent_faction_id
    # Sorted-ID RNG fallback (deterministic given seeded rng).
    return rng.choice(tied)


def detect_red_settler_trap(
    faction_class_reduction: float,
    faction_colonial_stance: ColonialStance,
    defines: BalkanizationDefines | None = None,
) -> bool:
    """Detect the Red Settler Trap diagnostic condition (spec-070 FR-034).

    Fires when a Faction has both:

    - ``class_reduction >= red_settler_trap_class_reduction_threshold``
      (default 0.6), AND
    - ``colonial_stance ∈ {UPHOLD, IGNORE}``

    The combination represents a Faction successfully reducing class
    contradiction while leaving settler-colonial relations intact — the
    canonical RED_OGV (Occupied Garrison of the Volksgemeinschaft) trap.

    Args:
        faction_class_reduction: Faction's class_reduction multiplier.
        faction_colonial_stance: Faction's colonial_stance.
        defines: Optional override defines.

    Returns:
        ``True`` iff the trap condition is satisfied.

    Example:
        >>> from babylon.models.enums import ColonialStance
        >>> detect_red_settler_trap(0.7, ColonialStance.IGNORE)
        True
        >>> detect_red_settler_trap(0.7, ColonialStance.ABOLISH)
        False
    """

    if defines is None:
        defines = BalkanizationDefines()
    if faction_colonial_stance is ColonialStance.ABOLISH:
        return False
    return faction_class_reduction >= defines.red_settler_trap_class_reduction_threshold


def contiguous_influence_majority_subregion(
    graph: GraphProtocol,
    faction_id: str,
    sovereign_id: str,
    defines: BalkanizationDefines | None = None,
) -> frozenset[str]:
    """Compute the largest contiguous H3-res-7 sub-region of a Sovereign's
    territory where ``faction_id``'s INFLUENCES.influence_level exceeds
    :attr:`BalkanizationDefines.secession_influence_threshold`
    (spec-070 FR-029b).

    The result is a deterministic, lex-sorted frontier BFS over
    ADJACENCY-linked H3 res-7 hexes, restricted to hexes claimed by
    ``sovereign_id`` and satisfying the influence predicate.

    Args:
        graph: GraphProtocol exposing :meth:`query_sovereign_claims`,
            :meth:`query_adjacent_territories`, and
            :meth:`query_faction_influence_by_territory`.
        faction_id: Candidate secessionist Faction ID.
        sovereign_id: Parent Sovereign whose territory is being analyzed.
        defines: Optional override defines.

    Returns:
        Frozen set of Territory IDs comprising the largest contiguous
        sub-region. Returns the empty set if no eligible component is
        ≥ :attr:`BalkanizationDefines.min_contiguous_hex_count`.

    Raises:
        AttributeError: If ``graph`` does not implement the required
            query methods.
    """

    if defines is None:
        defines = BalkanizationDefines()
    eligible = _eligible_territories(graph, faction_id, sovereign_id, defines)
    if not eligible:
        return frozenset()
    best = _largest_contiguous_component(graph, eligible)
    if len(best) < defines.min_contiguous_hex_count:
        return frozenset()
    return best


def _eligible_territories(
    graph: GraphProtocol,
    faction_id: str,
    sovereign_id: str,
    defines: BalkanizationDefines,
) -> set[str]:
    """Return Territories where ``faction_id`` exceeds the secession
    influence threshold among the Sovereign's claims."""

    claimed = {row[0] for row in graph.query_sovereign_claims(sovereign_id)}
    if not claimed:
        return set()
    threshold = defines.secession_influence_threshold
    return {tid for tid in claimed if _faction_influence_in(graph, faction_id, tid) > threshold}


def _faction_influence_in(graph: GraphProtocol, faction_id: str, territory_id: str) -> float:
    """Sum of ``faction_id`` INFLUENCES on ``territory_id``."""

    total = 0.0
    for row in graph.query_faction_influence_by_territory(territory_id):
        if row[0] == faction_id:
            total += float(row[1])
    return total


def _largest_contiguous_component(graph: GraphProtocol, eligible: set[str]) -> frozenset[str]:
    """Return the largest contiguous component within ``eligible`` via
    deterministic-frontier BFS over ADJACENCY edges."""

    visited: set[str] = set()
    best: frozenset[str] = frozenset()
    for seed in sorted(eligible):
        if seed in visited:
            continue
        component = _bfs_component(graph, seed, eligible, visited)
        if len(component) > len(best):
            best = frozenset(component)
    return best


def _bfs_component(
    graph: GraphProtocol,
    seed: str,
    eligible: set[str],
    visited: set[str],
) -> set[str]:
    """BFS one component from ``seed``, mutating ``visited`` and
    returning the collected nodes. Deterministic by lex-sort of each
    frontier level."""

    component: set[str] = set()
    frontier: list[str] = [seed]
    while frontier:
        next_frontier: list[str] = []
        for node in sorted(frontier):
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for adj in sorted(graph.query_adjacent_territories(node)):
                if adj in eligible and adj not in visited:
                    next_frontier.append(adj)
        frontier = next_frontier
    return component


def extrapolate_habitability(
    current_habitability: float,
    metabolic_impact: float,
    horizon_ticks: int,
) -> float:
    """Linearly extrapolate a Territory's habitability over a horizon
    (spec-070 FR-051, used by :class:`SovereignProjection`).

    Assumes constant policy (no Faction transitions during the horizon).
    Clamps to [0.0, 1.0].

    Args:
        current_habitability: Current habitability ∈ [0, 1].
        metabolic_impact: Per-tick habitability change.
        horizon_ticks: Number of ticks to project forward.

    Returns:
        Projected habitability, clamped to ``[0.0, 1.0]``.

    Example:
        >>> extrapolate_habitability(0.8, -0.02, 10)
        0.6
        >>> extrapolate_habitability(0.5, 0.01, 100)  # would overshoot
        1.0
    """

    projected = current_habitability + metabolic_impact * horizon_ticks
    return max(0.0, min(1.0, projected))


__all__ = [
    "calculate_metabolic_impact",
    "contiguous_influence_majority_subregion",
    "derive_default_multipliers_from_stance",
    "derive_extraction_policy_from_stance",
    "detect_red_settler_trap",
    "extrapolate_habitability",
    "winning_faction_for_territory",
]
