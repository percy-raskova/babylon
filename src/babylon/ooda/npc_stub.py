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
from typing import TYPE_CHECKING, Any

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, OrgType
from babylon.ooda.action_eligibility import check_eligibility
from babylon.ooda.types import Action

if TYPE_CHECKING:
    from babylon.config.defines import StateApparatusAIDefines

    # nx-compat payload surface (constitution II.12), not the formal
    # GraphProtocol — GraphProtocol has no .nodes(data=True); mirrors the
    # BabylonGraph typing already used by layer0.py/layer3.py/action_effects.py.
    from babylon.topology.graph import BabylonGraph

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
    graph: BabylonGraph | None = None,
    state_ai_defines: StateApparatusAIDefines | None = None,
) -> list[Action]:
    """Select actions for an NPC organization using priority queue.

    Greedily selects highest-priority eligible actions until action
    points are exhausted.

    Args:
        org_id: Organization node ID.
        org_attrs: Organization node attributes dict.
        target_id: Default target for actions (legacy priority-queue path
            only — the RuleBasedStateAI path below does its own target
            discovery via *graph*).
        defines: OODADefines for action point costs.
        graph: Mutable world graph, used by the RuleBasedStateAI dispatch
            to discover real REPRESS targets (task #73). Optional for
            backward compatibility with callers that exercise this
            function without a graph (e.g. isolated unit tests) — those
            keep the legacy self-targeting fallback documented on
            ``RuleBasedStateAI.select_action``.
        state_ai_defines: ``services.defines.state_ai`` — threaded through
            so the RuleBasedStateAI dispatch honors any ``defines.yaml``
            override (III.5) instead of constructing a fresh
            ``GameDefines()``. Optional for the same backward-compat
            reason as *graph*.

    Returns:
        List of Action objects within AP budget.
    """
    org_type = org_attrs.get("org_type", "")

    # Feature 039: Delegate STATE_APPARATUS with faction data to RuleBasedStateAI
    if org_type == OrgType.STATE_APPARATUS.value:
        state_actions = _try_state_ai_dispatch(
            org_id, org_attrs, graph=graph, state_ai_defines=state_ai_defines
        )
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


def _gather_repress_target_candidates(
    org_id: str,
    graph: BabylonGraph | None,
) -> list[tuple[str, float]] | None:
    """Enumerate REPRESS-target candidates visible to the state (task #73).

    Candidates are non-state ORGANIZATION nodes only. Verified against
    the actual downstream resolver (``babylon.ooda.layer3._propagate_heat``,
    the only layer-3 processor a dispatched state action reaches — every
    ``StateAction`` collapses to a legacy ``ActionType.REPRESS`` at
    :func:`_try_state_ai_dispatch`'s conversion step regardless of the
    underlying verb): it reads/writes a generic ``graph.nodes[target]
    ["heat"]``, which works for any node but is only a *declared* model
    field on ``organization`` (and ``territory``/``community``) nodes.
    ``SocialClass`` has no ``heat`` field and is ``extra="forbid"``
    (frozen) — writing one would raise on the next
    ``WorldState.from_graph()`` round-trip, the same landmine documented
    for ``infrastructure`` vs. ``Territory`` in
    ``models/world_state.py``'s ``TERRITORY_EXCLUDED_FIELDS``. So
    SocialClass nodes are deliberately excluded here (deviation from the
    epoch doctrine's literal "+ social_class nodes" phrasing — flagged in
    the task report, not silently dropped).

    Other STATE_APPARATUS orgs (e.g. a second jurisdiction) are also
    excluded — the state does not repress its own apparatus.

    Args:
        org_id: The acting state organization's own ID (excluded).
        graph: World graph, or ``None`` if the caller has none available.

    Returns:
        ``(entity_id, heat)`` pairs, or ``None`` if *graph* is ``None``
        (the caller couldn't look — distinct from looking and finding
        zero candidates, which returns ``[]``).
    """
    if graph is None:
        return None

    candidates: list[tuple[str, float]] = []
    max_nodes = 1000
    for idx, (node_id, data) in enumerate(graph.nodes(data=True)):
        if idx >= max_nodes:
            break
        if node_id == org_id:
            continue
        if data.get("_node_type") != "organization":
            continue
        if data.get("org_type") == OrgType.STATE_APPARATUS.value:
            continue
        candidates.append((node_id, float(data.get("heat", 0.0))))

    return candidates


def _try_state_ai_dispatch(
    org_id: str,
    org_attrs: dict[str, Any],
    graph: BabylonGraph | None = None,
    state_ai_defines: StateApparatusAIDefines | None = None,
) -> list[Action] | None:
    """Attempt to dispatch to RuleBasedStateAI for state apparatus orgs.

    Returns None if the org lacks the required faction data, falling
    through to legacy priority-queue selection.

    Args:
        org_id: Organization node ID.
        org_attrs: Organization node attributes dict.
        graph: World graph for REPRESS target discovery (task #73). See
            :func:`_gather_repress_target_candidates`.
        state_ai_defines: ``services.defines.state_ai``, honoring any
            ``defines.yaml`` override. Falls back to a fresh
            ``GameDefines()`` when unavailable (documented TODO below).

    Returns:
        List of legacy Action objects wrapping StateAction selections,
        or None to fall through to legacy dispatch.
    """
    # Require faction_balance data to activate state AI
    faction_data = org_attrs.get("faction_balance")
    if faction_data is None:
        return None

    # Lazy imports to avoid circular dependencies
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

    if state_ai_defines is not None:
        defines = state_ai_defines
    else:
        # TODO(task #73 follow-up): every real dispatch path
        # (OODASystem._resolve_for_organization, via select_npc_actions)
        # now threads services.defines.state_ai through, so this branch
        # should be unreachable in production. It remains as an honest
        # fallback for callers that invoke select_npc_actions /
        # _try_state_ai_dispatch without a ServiceContainer (isolated
        # unit tests) rather than a blind refactor forcing services
        # everywhere. If this ever logs from engine code, that's a real
        # bug — wire services.defines.state_ai at that call site instead.
        from babylon.config.defines import GameDefines

        _log.debug(
            "_try_state_ai_dispatch(%s): no state_ai_defines supplied, "
            "using GameDefines() defaults instead of services.defines.state_ai",
            org_id,
        )
        defines = GameDefines().state_ai

    target_candidates = _gather_repress_target_candidates(org_id, graph)

    ai = RuleBasedStateAI()
    state_actions = ai.select_action(
        org_id=org_id,
        faction_balance=balance,
        budget=budget,
        heat=heat,
        defines=defines,
        rng_seed=rng_seed,
        target_candidates=target_candidates,
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
