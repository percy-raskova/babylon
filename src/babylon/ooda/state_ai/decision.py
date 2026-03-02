"""State Apparatus AI decision function (Feature 039).

Implements the RuleBasedStateAI decision strategy following the OODA
(Observe-Orient-Decide-Act) cycle. The decision function selects verbs
based on a factional objective function weighted by the current
FactionBalance, constrained by the StateBudget, and informed by the
current Heat level (escalation/de-escalation).

See Also:
    ``specs/039-state-apparatus-ai/contracts/state-ai-decision.md``
    :class:`babylon.ooda.state_ai.protocols.NPCDecisionStrategy`
"""

from __future__ import annotations

import random
from typing import Any

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.state_apparatus_ai import (
    VERB_CHILDREN,
    FactionBalance,
    StateAction,
    StateBudget,
)
from babylon.models.enums import StateActionType, StateFaction
from babylon.ooda.state_ai.escalation import (
    compute_heat_escalation_score,
    get_escalation_rank,
)

# ---------------------------------------------------------------------------
# Verb cost table (budget_cost per sub-verb)
# Lower-escalation verbs are cheaper; higher-escalation verbs cost more.
# ---------------------------------------------------------------------------

_VERB_COSTS: dict[StateActionType, float] = {
    # CO_OPT sub-verbs (low cost)
    StateActionType.PROPAGANDIZE: 0.0,
    StateActionType.BRIBE: 5.0,
    StateActionType.INCORPORATE: 3.0,
    StateActionType.DIVIDE: 2.0,
    # ADMINISTER sub-verbs (moderate cost)
    StateActionType.FUND: 8.0,
    StateActionType.STAFF: 5.0,
    StateActionType.LEGISLATE: 3.0,
    StateActionType.AUDIT: 2.0,
    StateActionType.REVOKE: 1.0,
    # DEVELOP sub-verbs (moderate cost)
    StateActionType.INVEST: 10.0,
    StateActionType.REZONE: 4.0,
    StateActionType.DISPLACE: 8.0,
    StateActionType.NEGLECT: 0.0,
    # RESEARCH sub-verbs (moderate cost)
    StateActionType.PURSUE_TECH: 6.0,
    StateActionType.DEPLOY_TECH: 8.0,
    # REPRESS sub-verbs (high cost)
    StateActionType.SURVEIL: 3.0,
    StateActionType.INFILTRATE: 5.0,
    StateActionType.RAID: 10.0,
    StateActionType.PROSECUTE: 7.0,
    StateActionType.LIQUIDATE: 15.0,
    # WITHDRAW sub-verbs (variable cost)
    StateActionType.STRATEGIC_WITHDRAWAL: 1.0,
    StateActionType.TACTICAL_RETREAT: 2.0,
    StateActionType.SCORCHED_EARTH: 12.0,
}

# ---------------------------------------------------------------------------
# Legitimacy cost per sub-verb (how much the action erodes legitimacy)
# Negative = costs legitimacy; positive = gains legitimacy
# ---------------------------------------------------------------------------

_LEGITIMACY_COSTS: dict[StateActionType, float] = {
    StateActionType.PROPAGANDIZE: 0.01,
    StateActionType.BRIBE: -0.01,
    StateActionType.INCORPORATE: 0.005,
    StateActionType.DIVIDE: -0.02,
    StateActionType.FUND: 0.01,
    StateActionType.STAFF: 0.005,
    StateActionType.LEGISLATE: 0.0,
    StateActionType.AUDIT: 0.005,
    StateActionType.REVOKE: -0.01,
    StateActionType.INVEST: 0.02,
    StateActionType.REZONE: -0.01,
    StateActionType.DISPLACE: -0.04,
    StateActionType.NEGLECT: -0.01,
    StateActionType.PURSUE_TECH: 0.01,
    StateActionType.DEPLOY_TECH: 0.0,
    StateActionType.SURVEIL: -0.005,
    StateActionType.INFILTRATE: -0.01,
    StateActionType.RAID: -0.05,
    StateActionType.PROSECUTE: -0.03,
    StateActionType.LIQUIDATE: -0.08,
    StateActionType.STRATEGIC_WITHDRAWAL: -0.02,
    StateActionType.TACTICAL_RETREAT: -0.01,
    StateActionType.SCORCHED_EARTH: -0.10,
}


# ---------------------------------------------------------------------------
# Faction-specific objective functions
# ---------------------------------------------------------------------------


def finance_capital_objective(action: StateAction, heat: float) -> float:
    """Score an action from the Finance-Capital perspective.

    Finance-Capital prefers actions that stabilize extraction conditions:
    CO_OPT and DEVELOP score well. REPRESS is tolerated only at high heat.
    WITHDRAW scores poorly (abandons investment).

    Args:
        action: Candidate StateAction.
        heat: Current player threat level [0.0, 1.0].

    Returns:
        Score (higher = more preferred by Finance-Capital).
    """
    verb = action.verb
    base: float = 0.0

    if verb == StateActionType.CO_OPT:
        base = 1.5
    elif verb == StateActionType.DEVELOP:
        base = 1.2
    elif verb == StateActionType.ADMINISTER:
        base = 0.8
    elif verb == StateActionType.RESEARCH:
        base = 0.6
    elif verb == StateActionType.REPRESS:
        # FC tolerates repression only when heat justifies it
        base = -0.5 + heat * 1.0
    elif verb == StateActionType.WITHDRAW:
        base = -1.0

    # FC dislikes high legitimacy costs (bad for business climate)
    legitimacy_penalty = action.legitimacy_cost * 2.0

    return base + legitimacy_penalty


def security_state_objective(action: StateAction, heat: float) -> float:
    """Score an action from the Security-State perspective.

    Security-State prefers REPRESS (justifies apparatus growth) and
    RESEARCH (surveillance tech). Higher heat amplifies REPRESS preference.

    Args:
        action: Candidate StateAction.
        heat: Current player threat level [0.0, 1.0].

    Returns:
        Score (higher = more preferred by Security-State).
    """
    verb = action.verb
    base: float = 0.0

    if verb == StateActionType.REPRESS:
        # SS always likes repression; heat amplifies it
        base = 0.5 + heat * 1.5
    elif verb == StateActionType.RESEARCH:
        base = 0.8
    elif verb == StateActionType.ADMINISTER:
        base = 0.4
    elif verb == StateActionType.CO_OPT:
        # SS tolerates co-optation but doesn't prefer it
        base = 0.2
    elif verb == StateActionType.DEVELOP:
        base = 0.1
    elif verb == StateActionType.WITHDRAW:
        base = -0.8

    # SS gets bonus for surveillance-type sub-verbs
    if action.sub_verb in {StateActionType.SURVEIL, StateActionType.INFILTRATE}:
        base += 0.3

    return base


def settler_populist_objective(action: StateAction, heat: float) -> float:
    """Score an action from the Settler-Populist perspective.

    Settler-Populist prefers DEVELOP.DISPLACE (territorial expansion),
    CO_OPT.DIVIDE (prevents cross-line solidarity). Dislikes WITHDRAW
    (abandonment of settler claims).

    Args:
        action: Candidate StateAction.
        heat: Current player threat level [0.0, 1.0].

    Returns:
        Score (higher = more preferred by Settler-Populist).
    """
    verb = action.verb
    sub = action.sub_verb
    base: float = 0.0

    if verb == StateActionType.DEVELOP:
        base = 0.6
        if sub == StateActionType.DISPLACE:
            base = 1.5  # Core SP interest
    elif verb == StateActionType.CO_OPT:
        base = 0.5
        if sub == StateActionType.DIVIDE:
            base = 1.3  # Prevents multiracial solidarity
        elif sub == StateActionType.PROPAGANDIZE:
            base = 0.8  # Cultural narrative control
    elif verb == StateActionType.REPRESS:
        # SP supports repression of "outsiders" but not broadly
        base = 0.3 + heat * 0.5
    elif verb == StateActionType.ADMINISTER:
        base = 0.4
    elif verb == StateActionType.RESEARCH:
        base = 0.2
    elif verb == StateActionType.WITHDRAW:
        base = -1.2  # Worst outcome for SP

    return base


def score_action(
    action: StateAction,
    balance: FactionBalance,
    heat: float,
) -> float:
    """Compute the weighted faction objective score for an action.

    score = fc_weight * fc_objective + ss_weight * ss_objective + sp_weight * sp_objective

    Args:
        action: Candidate StateAction.
        balance: Current FactionBalance weights.
        heat: Current player threat level [0.0, 1.0].

    Returns:
        Weighted score (higher = more preferred given current faction balance).
    """
    fc = finance_capital_objective(action, heat)
    ss = security_state_objective(action, heat)
    sp = settler_populist_objective(action, heat)

    return (
        balance.finance_capital * fc + balance.security_state * ss + balance.settler_populist * sp
    )


# ---------------------------------------------------------------------------
# Candidate action generation
# ---------------------------------------------------------------------------


def _generate_candidates(
    budget_available: float,
    defines: StateApparatusAIDefines,
) -> list[StateAction]:
    """Enumerate feasible candidate actions given budget constraints.

    Generates one candidate per sub-verb whose budget cost does not exceed
    the available budget.

    Args:
        budget_available: Remaining budget.
        defines: State AI configuration.

    Returns:
        List of candidate StateAction objects.
    """
    candidates: list[StateAction] = []
    max_verbs = len(VERB_CHILDREN)
    effect_floor = defines.minimum_effect_floor

    for parent_idx, (parent, children) in enumerate(VERB_CHILDREN.items()):
        if parent_idx >= max_verbs:
            break

        # Determine faction alignment for this verb category
        faction = _verb_faction_alignment(parent)

        max_children = len(children)
        for child_idx, child in enumerate(children):
            if child_idx >= max_children:
                break

            cost = _VERB_COSTS.get(child, 5.0)
            if cost > budget_available:
                continue

            legitimacy_cost = _LEGITIMACY_COSTS.get(child, 0.0)

            # Floor very small legitimacy costs to the defines minimum
            if 0 < abs(legitimacy_cost) < effect_floor:
                legitimacy_cost = -effect_floor if legitimacy_cost < 0 else effect_floor

            candidate = StateAction(
                verb=parent,
                sub_verb=child,
                target_id="",
                budget_cost=cost,
                thread_cost=0,
                legitimacy_cost=legitimacy_cost,
                faction_alignment=faction,
            )
            candidates.append(candidate)

    return candidates


def _verb_faction_alignment(verb: StateActionType) -> StateFaction:
    """Determine which faction a top-level verb most aligns with.

    Args:
        verb: A top-level StateActionType.

    Returns:
        The most natural faction alignment for this verb category.
    """
    if verb == StateActionType.REPRESS:
        return StateFaction.SECURITY_STATE
    if verb == StateActionType.DEVELOP:
        return StateFaction.SETTLER_POPULIST
    if verb in {StateActionType.CO_OPT, StateActionType.ADMINISTER}:
        return StateFaction.FINANCE_CAPITAL
    if verb == StateActionType.RESEARCH:
        return StateFaction.SECURITY_STATE
    # WITHDRAW is a last resort, no natural faction
    return StateFaction.FINANCE_CAPITAL


# ---------------------------------------------------------------------------
# RuleBasedStateAI — the main decision class
# ---------------------------------------------------------------------------


class RuleBasedStateAI:
    """Rule-based state AI implementing NPCDecisionStrategy protocol.

    Follows the OODA cycle each tick:
    1. OBSERVE — read heat level and faction balance
    2. ORIENT — assess threat, generate candidates, compute escalation scores
    3. DECIDE — score candidates via factional objective + escalation affinity
    4. ACT — select best action(s) within budget

    See Also:
        :class:`babylon.ooda.state_ai.protocols.NPCDecisionStrategy`
        ``specs/039-state-apparatus-ai/contracts/state-ai-decision.md``
    """

    def select_action(
        self,
        org_id: str,
        faction_balance: FactionBalance,
        budget: StateBudget,
        heat: float,
        defines: StateApparatusAIDefines,
        rng_seed: int | None = None,
    ) -> list[StateAction]:
        """Select actions for one tick.

        Args:
            org_id: Organization node ID.
            faction_balance: Current FactionBalance weights.
            budget: Current StateBudget (available funds).
            heat: Player threat level [0.0, 1.0].
            defines: State AI configuration.
            rng_seed: Optional RNG seed for determinism.

        Returns:
            List of StateAction objects (at most ``defines.actions_per_tick``).
        """
        rng = random.Random(rng_seed)

        max_actions = defines.actions_per_tick
        available = budget.available

        # OBSERVE + ORIENT: Generate feasible candidates
        candidates = _generate_candidates(available, defines)

        if not candidates:
            return []

        # DECIDE: Score each candidate
        max_rank = len(defines.escalation_ladder) - 1
        scored: list[tuple[float, StateAction]] = []

        max_candidates = len(candidates)
        for idx, candidate in enumerate(candidates):
            if idx >= max_candidates:
                break

            # Factional objective score
            faction_score = score_action(candidate, faction_balance, heat)

            # Escalation affinity score
            esc_rank = get_escalation_rank(candidate.sub_verb, defines)
            if esc_rank >= 0:
                esc_score = compute_heat_escalation_score(heat, esc_rank, max_rank)
            else:
                esc_score = 0.5  # Neutral for verbs not on ladder

            # Combined score with small random tiebreaker
            combined = faction_score + esc_score + rng.uniform(0.0, 0.01)
            scored.append((combined, candidate))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # ACT: Select top actions within budget
        selected: list[StateAction] = []
        remaining_budget = available

        max_selections = min(max_actions, len(scored))
        for selection_idx in range(len(scored)):
            if len(selected) >= max_selections:
                break

            _score, candidate = scored[selection_idx]
            if candidate.budget_cost <= remaining_budget:
                # Re-create with target_id
                action = StateAction(
                    verb=candidate.verb,
                    sub_verb=candidate.sub_verb,
                    target_id=org_id,
                    budget_cost=candidate.budget_cost,
                    thread_cost=candidate.thread_cost,
                    legitimacy_cost=candidate.legitimacy_cost,
                    faction_alignment=candidate.faction_alignment,
                )
                selected.append(action)
                remaining_budget -= candidate.budget_cost

        return selected

    def get_debug_state(
        self,
        defines: StateApparatusAIDefines,
        faction_balance: FactionBalance | None = None,
        budget: StateBudget | None = None,
        last_actions: list[StateAction] | None = None,
    ) -> dict[str, Any] | None:
        """Expose all state internals when God Mode is enabled.

        Args:
            defines: State AI configuration with ``god_mode_enabled``.
            faction_balance: Current faction balance (if available).
            budget: Current budget state (if available).
            last_actions: Most recent actions taken (if available).

        Returns:
            Dict of all state internals if god_mode_enabled, else None.
        """
        if not defines.god_mode_enabled:
            return None

        debug: dict[str, Any] = {"god_mode": True}

        if faction_balance is not None:
            debug["faction_balance"] = {
                "finance_capital": faction_balance.finance_capital,
                "security_state": faction_balance.security_state,
                "settler_populist": faction_balance.settler_populist,
                "stability": faction_balance.stability,
                "legitimacy": faction_balance.legitimacy,
                "dominant_faction": str(faction_balance.dominant_faction),
            }

        if budget is not None:
            debug["budget"] = {
                "revenue": budget.revenue,
                "available": budget.available,
                "allocated": dict(budget.allocated),
            }

        if last_actions is not None:
            debug["last_actions"] = [
                {
                    "verb": str(a.verb),
                    "sub_verb": str(a.sub_verb),
                    "target_id": a.target_id,
                    "budget_cost": a.budget_cost,
                    "legitimacy_cost": a.legitimacy_cost,
                }
                for a in last_actions
            ]

        return debug


__all__ = [
    "RuleBasedStateAI",
    "finance_capital_objective",
    "score_action",
    "security_state_objective",
    "settler_populist_objective",
]
