"""NPC action selection stub (Feature 032).

Deterministic priority-based action selection for non-player organizations.
Each org type has a fixed priority queue of actions it prefers. The stub
selects actions greedily until action points are exhausted.

AI-driven action selection is deferred to a future feature.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, OrgType
from babylon.ooda.action_eligibility import check_eligibility
from babylon.ooda.types import Action

# Priority queues by org type (highest priority first)
_NPC_PRIORITIES: dict[str, list[ActionType]] = {
    OrgType.STATE_APPARATUS.value: [
        ActionType.SURVEIL,
        ActionType.REPRESS,
        ActionType.INFILTRATE,
        ActionType.MAP_NETWORK,
        ActionType.COUNTER_INTEL,
    ],
    OrgType.POLITICAL_FACTION.value: [
        ActionType.EDUCATE,
        ActionType.ORGANIZE,
        ActionType.AGITATE,
        ActionType.RECRUIT,
        ActionType.FUNDRAISE,
    ],
    OrgType.CIVIL_SOCIETY.value: [
        ActionType.PROVIDE_SERVICE,
        ActionType.EDUCATE,
        ActionType.ORGANIZE,
        ActionType.FUNDRAISE,
        ActionType.BUILD_INFRASTRUCTURE,
    ],
    OrgType.BUSINESS.value: [
        ActionType.EMPLOY,
        ActionType.FUNDRAISE,
        ActionType.DENOUNCE,
    ],
}


def select_npc_actions(
    org_id: str,
    org_attrs: dict[str, Any],
    target_id: str,
    defines: OODADefines,
) -> list[Action]:
    """Select actions for an NPC organization using priority queue.

    Greedily selects highest-priority eligible actions until action
    points are exhausted.

    Args:
        org_id: Organization node ID.
        org_attrs: Organization node attributes dict.
        target_id: Default target for actions.
        defines: OODADefines for action point costs.

    Returns:
        List of Action objects within AP budget.
    """
    org_type = org_attrs.get("org_type", "")
    ooda_profile = org_attrs.get("ooda_profile", {})
    action_points = ooda_profile.get("action_points", 3)
    remaining_ap = action_points

    priorities = _NPC_PRIORITIES.get(org_type, [])
    actions: list[Action] = []

    max_actions = 20  # Upper bound for loop safety
    for action_type in priorities:
        if len(actions) >= max_actions:
            break
        if not check_eligibility(org_type, action_type, org_attrs):
            continue

        cost = defines.get_base_cost(action_type.value)
        if cost > remaining_ap:
            continue

        action = Action(
            org_id=org_id,
            action_type=action_type,
            target_id=target_id,
            action_point_cost=cost,
        )
        actions.append(action)
        remaining_ap -= cost

    return actions


__all__ = ["select_npc_actions"]
