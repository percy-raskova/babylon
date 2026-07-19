"""Initiative scoring and action ordering (Feature 032).

Computes per-tick initiative scores for organizations and resolves the
action order (descending score, ascending org_id tiebreak).

See Also:
    ``specs/032-ooda-loop-system/contracts/initiative-scoring-contract.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.config.defines import OODADefines
from babylon.models.enums import EdgeType, JurisdictionLevel, NodeType
from babylon.ooda.types import InitiativeScore

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph


def compute_initiative_score(
    org_id: str,
    cycle_time: float,
    jurisdiction: JurisdictionLevel | None,
    counter_intel_score: float,
    community_embeddedness: float,
    momentum: float,
    defines: OODADefines,
) -> InitiativeScore:
    """Compute initiative score for one organization.

    Args:
        org_id: Organization node ID.
        cycle_time: OODA cycle time (from compute_cycle_time).
        jurisdiction: JurisdictionLevel for state orgs, None for others.
        counter_intel_score: Counter-intelligence capability [0, 1].
        community_embeddedness: Community embeddedness [0, 1].
        momentum: Current momentum (>= 0).
        defines: OODADefines coefficients.

    Returns:
        InitiativeScore with all component breakdowns.
    """
    speed = defines.initiative_weight_speed * (1.0 / cycle_time)

    if jurisdiction is not None:
        inst_bonus = _institutional_bonus(jurisdiction, defines)
    else:
        inst_bonus = defines.institutional_bonus_nonstate
    institutional = defines.initiative_weight_institutional * inst_bonus

    counterintel = defines.initiative_weight_counterintel * counter_intel_score
    embeddedness = defines.initiative_weight_embeddedness * community_embeddedness
    momentum_val = defines.initiative_weight_momentum * momentum

    score = speed + institutional + counterintel + embeddedness + momentum_val

    return InitiativeScore(
        org_id=org_id,
        score=score,
        speed_component=speed,
        institutional_component=institutional,
        counterintel_component=counterintel,
        embeddedness_component=embeddedness,
        momentum_component=momentum_val,
    )


def resolve_action_order(scores: list[InitiativeScore]) -> list[InitiativeScore]:
    """Sort organizations by initiative score for action resolution.

    Args:
        scores: List of initiative scores to sort.

    Returns:
        Sorted list (descending score, ascending org_id tiebreak).
    """
    return sorted(scores, key=lambda s: (-s.score, s.org_id))


def compute_community_embeddedness(
    org_id: str,
    graph: BabylonGraph,
) -> float:
    """Compute how embedded an organization is in its territories' communities.

    Walks ``org_id`` -> its ``territory_ids`` (a declared field on
    ``Organization``/``Institution``) -> the ``social_class`` nodes TENANCY-
    linked into each of those territories (the real Occupant -> Territory
    edge; reimplements the traversal idiom of ``web/game/engine_bridge.py::
    _tenancy_members_by_territory`` in ``BabylonGraph`` terms, since ``src``
    may not import ``web``) -> each reachable member's
    ``community_memberships`` list (a declared ``SocialClass`` field,
    ``src/babylon/models/entities/social_class.py``).

    Embeddedness is the share of TENANCY-reachable members carrying at least
    one community membership: ``members_with_membership / total_reachable``.
    Bounded to [0, 1] by construction. Iterates sorted territory ids and
    sorted member node ids throughout, so the result never depends on graph
    insertion order (Constitution III.7 — determinism).

    .. note::
       This value is structurally 0.0 in every real game today: no
       production writer ever populates ``SocialClass.community_memberships``
       (``CommunitySystem.step`` no-ops every tick — see the seam registry,
       ``src/babylon/sentinels/seam/registry.py:1969-1991``,
       ``liveness_class=STRUCTURALLY_IMPOSSIBLE``). Seeding that field is a
       separate, owner-gated program (out of this function's scope); this
       function reads the real substrate shape so the score becomes live the
       moment a producer exists, instead of reading a phantom attribute
       (``community_type``) no producer ever writes.

    Args:
        org_id: Organization node ID.
        graph: Graph with TENANCY edges and territory/social_class nodes.

    Returns:
        Embeddedness value in [0, 1]. 0.0 if the org has no ``territory_ids``
        or no TENANCY-linked member is reachable.
    """
    org_data = graph.nodes.get(org_id, {})
    territory_ids = sorted(org_data.get("territory_ids") or [])
    if not territory_ids:
        return 0.0

    territory_set = set(territory_ids)
    member_ids: set[str] = set()
    for source, target in graph.edges:
        if target not in territory_set:
            continue
        edge_data = graph.edges[(source, target)]
        etype = str(edge_data.get("edge_type", edge_data.get("_edge_type", ""))).lower()
        if etype != EdgeType.TENANCY.value:
            continue
        source_data = graph.nodes.get(source, {})
        if source_data.get("_node_type") != NodeType.SOCIAL_CLASS.value:
            continue
        member_ids.add(source)

    if not member_ids:
        return 0.0

    with_membership = sum(
        1
        for member_id in sorted(member_ids)
        if graph.nodes.get(member_id, {}).get("community_memberships")
    )
    embeddedness = with_membership / len(member_ids)
    return max(0.0, min(1.0, embeddedness))


def update_momentum(
    current_momentum: float,
    action_succeeded: bool,
    defines: OODADefines,
) -> float:
    """Update momentum after an action.

    Args:
        current_momentum: Current momentum value.
        action_succeeded: Whether the action succeeded.
        defines: OODADefines with momentum parameters.

    Returns:
        New momentum value.
    """
    new_momentum = current_momentum * defines.momentum_decay
    if action_succeeded:
        new_momentum += defines.momentum_success_bonus
    return new_momentum


def _institutional_bonus(
    jurisdiction: JurisdictionLevel,
    defines: OODADefines,
) -> float:
    """Look up institutional bonus by jurisdiction level.

    Args:
        jurisdiction: State jurisdiction level.
        defines: OODADefines with institutional bonus values.

    Returns:
        Institutional bonus value.
    """
    bonus_map: dict[JurisdictionLevel, float] = {
        JurisdictionLevel.NATIONAL: defines.institutional_bonus_federal,
        JurisdictionLevel.STATE: defines.institutional_bonus_state,
        JurisdictionLevel.COUNTY: defines.institutional_bonus_local,
        JurisdictionLevel.MUNICIPAL: defines.institutional_bonus_local,
    }
    return bonus_map.get(jurisdiction, defines.institutional_bonus_nonstate)


__all__ = [
    "compute_community_embeddedness",
    "compute_initiative_score",
    "resolve_action_order",
    "update_momentum",
]
