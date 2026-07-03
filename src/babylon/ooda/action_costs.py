"""Community-modified action costs (Feature 032).

Computes effective AP cost for actions based on org-community
membership overlap, contradiction axes, and outsider status.

See Also:
    ``specs/032-ooda-loop-system/contracts/action-resolution-contract.md``
"""

from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, CommunityType, EdgeType
from babylon.ooda._helpers import _compute_membership_overlap
from babylon.ooda.types import ActionCostModifier

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph


# Contradiction axes: (hegemonic, marginalized) pairs
_CONTRADICTION_PAIRS: list[tuple[CommunityType, CommunityType]] = [
    (CommunityType.SETTLER, CommunityType.NEW_AFRIKAN),
    (CommunityType.SETTLER, CommunityType.FIRST_NATIONS),
    (CommunityType.SETTLER, CommunityType.CHICANO),
    (CommunityType.PATRIARCHAL, CommunityType.WOMEN),
    (CommunityType.PATRIARCHAL, CommunityType.TRANS),
]


def compute_action_cost(
    action_type: ActionType,
    org_id: str,
    target_id: str,
    graph: BabylonGraph,
    defines: OODADefines,
) -> ActionCostModifier:
    """Compute effective cost of an action with community modifiers.

    Args:
        action_type: The action being costed.
        org_id: Acting organization node ID.
        target_id: Target community node ID.
        graph: World graph.
        defines: OODADefines with cost coefficients.

    Returns:
        ActionCostModifier with base cost, modifier, effective cost, and reason.
    """
    base_cost = defines.get_base_cost(action_type.value)

    # Step 2: Membership overlap
    overlap = _compute_membership_overlap(org_id, target_id, graph)

    # Step 3: Check contradiction axis
    org_community_types = _get_org_community_types(org_id, graph)
    target_community_type = _get_target_community_type(target_id, graph)

    # Step 4: Compute modifier
    if overlap > 0.0:
        raw_modifier = 1.0 - overlap * defines.embeddedness_discount
        modifier = max(defines.min_cost_modifier, raw_modifier)
        reason = f"Embedded (overlap={overlap:.2f})"
    elif _is_contradiction_pair(org_community_types, target_community_type):
        modifier = defines.contradiction_cost_multiplier
        reason = "Across contradiction axis"
    else:
        modifier = defines.outsider_cost_multiplier
        reason = "No membership in target community"

    # Step 5: Effective cost
    effective_cost = max(1, math.ceil(base_cost * modifier))

    return ActionCostModifier(
        base_cost=base_cost,
        modifier=modifier,
        effective_cost=effective_cost,
        reason=reason,
    )


def _get_org_community_types(
    org_id: str,
    graph: BabylonGraph,
) -> set[CommunityType]:
    """Get community types of an org's members.

    Args:
        org_id: Organization node ID.
        graph: World graph.

    Returns:
        Set of CommunityType values found among org members.
    """
    community_types: set[CommunityType] = set()
    max_edges = 1000
    edge_count = 0
    for _, target, data in graph.out_edges(org_id, data=True):
        edge_type = data.get("edge_type", "")
        if edge_type == EdgeType.MEMBERSHIP.value or edge_type == EdgeType.MEMBERSHIP:
            member_data = graph.nodes.get(target, {})
            ct_str = member_data.get("community_type", "")
            if ct_str:
                with contextlib.suppress(ValueError):
                    community_types.add(CommunityType(ct_str))
        edge_count += 1  # noqa: SIM113 — enumerate breaks mypy with EdgeView unpacking
        if edge_count >= max_edges:
            break

    return community_types


def _get_target_community_type(
    target_id: str,
    graph: BabylonGraph,
) -> CommunityType | None:
    """Get the community type of a target community node.

    Args:
        target_id: Community node ID.
        graph: World graph.

    Returns:
        CommunityType or None if not found.
    """
    target_data = graph.nodes.get(target_id, {})
    ct_str = target_data.get("community_type", "")
    if ct_str:
        try:
            return CommunityType(ct_str)
        except ValueError:
            return None
    return None


def _is_contradiction_pair(
    org_community_types: set[CommunityType],
    target_community_type: CommunityType | None,
) -> bool:
    """Check if org communities and target community form a contradiction pair.

    A contradiction exists when org members are from the hegemonic side
    and the target is marginalized, or vice versa.

    Args:
        org_community_types: Community types of org members.
        target_community_type: Community type of the target.

    Returns:
        True if a contradiction axis is crossed.
    """
    if target_community_type is None:
        return False

    for hegemonic, marginalized in _CONTRADICTION_PAIRS:
        # Org is hegemonic, target is marginalized
        if hegemonic in org_community_types and target_community_type == marginalized:
            return True
        # Org is marginalized, target is hegemonic
        if marginalized in org_community_types and target_community_type == hegemonic:
            return True

    return False


__all__ = [
    "compute_action_cost",
]
