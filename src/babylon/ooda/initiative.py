"""Initiative scoring and action ordering (Feature 032).

Computes per-tick initiative scores for organizations and resolves the
action order (descending score, ascending org_id tiebreak).

See Also:
    ``specs/032-ooda-loop-system/contracts/initiative-scoring-contract.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.config.defines import OODADefines
from babylon.models.enums import EdgeType, JurisdictionLevel
from babylon.ooda.types import InitiativeScore

if TYPE_CHECKING:
    import networkx as nx


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
    graph: nx.DiGraph[str],
) -> float:
    """Compute how embedded an organization is in its operating communities.

    Embeddedness = overlap of org member communities with territory communities.

    Args:
        org_id: Organization node ID.
        graph: Graph with MEMBERSHIP edges and territory/community nodes.

    Returns:
        Embeddedness value in [0, 1].
    """
    org_data = graph.nodes.get(org_id, {})
    territory_ids: list[str] = org_data.get("territory_ids", [])

    # Find community types from MEMBERSHIP edge targets
    org_communities: set[str] = set()
    for _, target, data in graph.out_edges(org_id, data=True):
        edge_type = data.get("edge_type", "")
        if edge_type == EdgeType.MEMBERSHIP.value or edge_type == EdgeType.MEMBERSHIP:
            target_data = graph.nodes.get(target, {})
            community = target_data.get("community_type") or target_data.get("community")
            if community:
                org_communities.add(str(community))

    # Find community types present in org's territories
    territory_communities: set[str] = set()
    for tid in territory_ids:
        # Check nodes that are in this territory
        for node_id, node_data in graph.nodes(data=True):
            if node_data.get("territory_id") == tid or node_id == tid:
                community = node_data.get("community_type")
                if community:
                    territory_communities.add(str(community))

    if not territory_communities:
        return 0.0

    overlap = len(org_communities & territory_communities) / len(territory_communities)
    return max(0.0, min(1.0, overlap))


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
