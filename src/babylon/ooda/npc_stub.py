"""NPC action selection stub (Feature 032, extended by Feature 039).

Deterministic priority-based action selection for non-player organizations.
Each org type has a fixed priority queue of actions it prefers. The stub
selects actions greedily until action points are exhausted.

For STATE_APPARATUS organizations with factional data (Feature 039),
delegates to ``RuleBasedStateAI.select_action()`` instead of the
static priority queue.
"""

from __future__ import annotations

import logging
from typing import Any

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, OrgType
from babylon.ooda.action_eligibility import check_eligibility
from babylon.ooda.types import Action

_log = logging.getLogger(__name__)

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

    # Feature 039: Delegate STATE_APPARATUS with faction data to RuleBasedStateAI
    if org_type == OrgType.STATE_APPARATUS.value:
        state_actions = _try_state_ai_dispatch(org_id, org_attrs)
        if state_actions is not None:
            return state_actions

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


def _try_state_ai_dispatch(
    org_id: str,
    org_attrs: dict[str, Any],
) -> list[Action] | None:
    """Attempt to dispatch to RuleBasedStateAI for state apparatus orgs.

    Returns None if the org lacks the required faction data, falling
    through to legacy priority-queue selection.

    Args:
        org_id: Organization node ID.
        org_attrs: Organization node attributes dict.

    Returns:
        List of legacy Action objects wrapping StateAction selections,
        or None to fall through to legacy dispatch.
    """
    # Require faction_balance data to activate state AI
    faction_data = org_attrs.get("faction_balance")
    if faction_data is None:
        return None

    # Lazy imports to avoid circular dependencies
    from babylon.config.defines import GameDefines
    from babylon.models.entities.state_apparatus_ai import FactionBalance, StateBudget
    from babylon.models.enums import StateActionType
    from babylon.ooda.state_ai.decision import RuleBasedStateAI

    # Reconstruct FactionBalance from graph attributes
    if isinstance(faction_data, FactionBalance):
        balance = faction_data
    elif isinstance(faction_data, dict):
        balance = FactionBalance(**faction_data)
    else:
        _log.warning("Invalid faction_balance data for %s, falling through", org_id)
        return None

    # Reconstruct or create default StateBudget
    budget_data = org_attrs.get("state_budget")
    if isinstance(budget_data, StateBudget):
        budget = budget_data
    elif isinstance(budget_data, dict):
        budget = StateBudget(**budget_data)
    else:
        budget = StateBudget(
            revenue=100.0,
            available=100.0,
            allocated={
                StateActionType.ADMINISTER: 15.0,
                StateActionType.DEVELOP: 15.0,
                StateActionType.RESEARCH: 10.0,
                StateActionType.CO_OPT: 20.0,
                StateActionType.REPRESS: 30.0,
                StateActionType.WITHDRAW: 10.0,
            },
            imperial_rent_pool=50.0,
        )

    heat = float(org_attrs.get("heat", 0.3))
    rng_seed = org_attrs.get("rng_seed")
    defines = GameDefines().state_ai

    ai = RuleBasedStateAI()
    state_actions = ai.select_action(
        org_id=org_id,
        faction_balance=balance,
        budget=budget,
        heat=heat,
        defines=defines,
        rng_seed=rng_seed,
    )

    # Convert StateAction to legacy Action format for OODA system compatibility
    legacy_actions: list[Action] = []
    max_convert = 20
    for idx, sa in enumerate(state_actions):
        if idx >= max_convert:
            break
        legacy_actions.append(
            Action(
                org_id=org_id,
                action_type=ActionType.REPRESS,  # Best-match legacy type
                target_id=sa.target_id or org_id,
                action_point_cost=1,
                budget_cost=sa.budget_cost,
            )
        )

    return legacy_actions


__all__ = ["select_npc_actions"]
