"""Faction dynamics shift calculations (Feature 039 Phase 5, US3).

Implements player-action and material-condition driven faction balance
shifts, per-tick clamping with renormalization, stability computation,
and fascist-mode behavioral overrides.

See Also:
    ``specs/039-state-apparatus-ai/contracts/faction-balance.md``: F-01 through F-05.
    :func:`babylon.formulas.state_ai.calculate_faction_shift`: Heat-driven shifts.
    :class:`babylon.config.defines.StateApparatusAIDefines`: Shift limits.
"""

from __future__ import annotations

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.state_apparatus_ai import FactionBalance, StateAction
from babylon.models.enums import StateActionType, StateFaction

# ---------------------------------------------------------------------------
# Player action → faction shift (T051)
# ---------------------------------------------------------------------------

# Shift direction per player action type: (faction_to_increase, base_magnitude)
_PLAYER_ACTION_SHIFTS: dict[str, tuple[str, float]] = {
    "heat_generation": ("security_state", 0.04),
    "surviving_repression": ("security_state", -0.04),  # Negative = decrease SS
    "extraction_disruption": ("finance_capital", 0.04),
    "narrative_victory": ("settler_populist", 0.04),
    "legitimacy_building": ("finance_capital", 0.03),
}


def apply_player_action_shift(
    action_type: str,
    outcome: str,
    current_balance: FactionBalance,
    defines: StateApparatusAIDefines,
) -> FactionBalance:
    """Apply a faction shift triggered by a player action.

    Args:
        action_type: Type of player action (e.g., "heat_generation").
        outcome: Action outcome (e.g., "success", "failure").
        current_balance: Current FactionBalance.
        defines: State AI configuration.

    Returns:
        New FactionBalance with shifted weights.
    """
    shift_spec = _PLAYER_ACTION_SHIFTS.get(action_type)
    if shift_spec is None:
        return current_balance

    target_faction, base_magnitude = shift_spec

    # Scale magnitude by outcome — success applies full shift
    scale = 1.0 if outcome == "success" else 0.5
    raw_magnitude = base_magnitude * scale

    # Apply minimum effect floor
    if 0 < abs(raw_magnitude) < defines.minimum_effect_floor:
        raw_magnitude = (
            defines.minimum_effect_floor if raw_magnitude > 0 else -defines.minimum_effect_floor
        )

    return _apply_single_faction_shift(
        current_balance=current_balance,
        target_faction=target_faction,
        magnitude=raw_magnitude,
        max_shift=defines.max_faction_shift_per_tick,
    )


# ---------------------------------------------------------------------------
# Repression failure shift (F-03)
# ---------------------------------------------------------------------------


def apply_repression_failure_shift(
    current_balance: FactionBalance,
    membership_retained_ratio: float,
    defines: StateApparatusAIDefines,
) -> FactionBalance:
    """Apply faction shift when a REPRESS action fails.

    When the target retains >50% membership, Security-State credibility
    decreases, shifting weight away from SS.

    Args:
        current_balance: Current FactionBalance.
        membership_retained_ratio: Fraction of membership retained (0.0-1.0).
        defines: State AI configuration.

    Returns:
        New FactionBalance with SS decreased.
    """
    if membership_retained_ratio <= 0.5:
        # Repression succeeded — no credibility loss
        return current_balance

    # Magnitude scales with how badly the repression failed
    # 0.5 retained = barely failed, 1.0 retained = complete failure
    failure_severity = (membership_retained_ratio - 0.5) * 2.0  # [0, 1]
    raw_magnitude = max(
        defines.minimum_effect_floor,
        failure_severity * 0.05,
    )

    return _apply_single_faction_shift(
        current_balance=current_balance,
        target_faction="security_state",
        magnitude=-raw_magnitude,  # Negative = decrease SS
        max_shift=defines.max_faction_shift_per_tick,
    )


# ---------------------------------------------------------------------------
# Material condition → faction shift (T052)
# ---------------------------------------------------------------------------

# Shift direction per material condition: (faction_to_increase, base_per_unit)
_MATERIAL_CONDITION_SHIFTS: dict[str, tuple[str, float]] = {
    "profit_rate_decline": ("finance_capital", 0.3),
    "legitimacy_crisis": ("security_state", 0.25),
    "imperial_rent_contraction": ("settler_populist", 0.3),
    "successful_co_opt": ("finance_capital", 0.2),
}


def apply_material_condition_shift(
    condition_type: str,
    magnitude: float,
    current_balance: FactionBalance,
    defines: StateApparatusAIDefines,
) -> FactionBalance:
    """Apply a faction shift triggered by a material condition change.

    Args:
        condition_type: Type of material condition (e.g., "profit_rate_decline").
        magnitude: Severity of the condition [0.0, 1.0].
        current_balance: Current FactionBalance.
        defines: State AI configuration.

    Returns:
        New FactionBalance with shifted weights.
    """
    shift_spec = _MATERIAL_CONDITION_SHIFTS.get(condition_type)
    if shift_spec is None:
        return current_balance

    target_faction, base_per_unit = shift_spec
    raw_magnitude = magnitude * base_per_unit

    # Apply minimum effect floor
    if 0 < abs(raw_magnitude) < defines.minimum_effect_floor:
        raw_magnitude = defines.minimum_effect_floor

    return _apply_single_faction_shift(
        current_balance=current_balance,
        target_faction=target_faction,
        magnitude=raw_magnitude,
        max_shift=defines.max_faction_shift_per_tick,
    )


# ---------------------------------------------------------------------------
# Renormalization with per-tick clamping (T053)
# ---------------------------------------------------------------------------


def renormalize_faction_balance(
    balance: FactionBalance,
    max_shift: float,
    previous_balance: FactionBalance,
) -> FactionBalance:
    """Clamp per-faction deltas and renormalize to sum to 1.0.

    Each faction's delta from ``previous_balance`` is independently clamped
    to ``[-max_shift, +max_shift]``. The result is then normalized while
    preserving the clamping constraint (iterative normalization).

    Args:
        balance: Proposed new FactionBalance.
        max_shift: Maximum per-faction delta per tick.
        previous_balance: Previous tick's FactionBalance.

    Returns:
        Clamped and normalized FactionBalance.
    """
    # Iterative clamp-normalize: clamp deltas, normalize, re-check.
    # This ensures no individual faction delta exceeds max_shift after
    # normalization (which can amplify deltas).
    fc_cur = previous_balance.finance_capital
    ss_cur = previous_balance.security_state
    sp_cur = previous_balance.settler_populist

    fc_target = balance.finance_capital
    ss_target = balance.security_state
    sp_target = balance.settler_populist

    max_iterations = 5
    for _iteration in range(max_iterations):
        fc_delta = _clamp(fc_target - fc_cur, max_shift)
        ss_delta = _clamp(ss_target - ss_cur, max_shift)
        sp_delta = _clamp(sp_target - sp_cur, max_shift)

        fc_new = max(0.0, fc_cur + fc_delta)
        ss_new = max(0.0, ss_cur + ss_delta)
        sp_new = max(0.0, sp_cur + sp_delta)

        # Normalize to sum to 1.0
        total = fc_new + ss_new + sp_new
        if total > 0:
            fc_new /= total
            ss_new /= total
            sp_new /= total
        else:
            fc_new = 1.0 / 3.0
            ss_new = 1.0 / 3.0
            sp_new = 1.0 / 3.0

        # Check if all deltas from previous are within bounds
        all_ok = (
            abs(fc_new - fc_cur) <= max_shift + 1e-9
            and abs(ss_new - ss_cur) <= max_shift + 1e-9
            and abs(sp_new - sp_cur) <= max_shift + 1e-9
        )
        if all_ok:
            break

        # Use normalized values as new targets for next iteration
        fc_target = fc_new
        ss_target = ss_new
        sp_target = sp_new

    return FactionBalance(
        finance_capital=round(fc_new, 6),
        security_state=round(ss_new, 6),
        settler_populist=round(sp_new, 6),
        stability=balance.stability,
        legitimacy=balance.legitimacy,
    )


# ---------------------------------------------------------------------------
# Stability computation (T053)
# ---------------------------------------------------------------------------


def compute_stability(
    shift_history: list[FactionBalance],
    window: int,
) -> float:
    """Compute a stability metric from recent faction balance history.

    Stability = 1 - normalized_variance. A constant balance yields ~1.0;
    volatile shifts yield values closer to 0.0.

    Args:
        shift_history: List of recent FactionBalance snapshots.
        window: Number of recent entries to consider.

    Returns:
        Stability score in [0.0, 1.0].
    """
    if len(shift_history) < 2:
        return 1.0

    # Use the most recent `window` entries
    recent = shift_history[-window:] if len(shift_history) >= window else shift_history
    n = len(recent)

    if n < 2:
        return 1.0

    # Compute variance across all three faction weights
    fc_vals = [b.finance_capital for b in recent]
    ss_vals = [b.security_state for b in recent]
    sp_vals = [b.settler_populist for b in recent]

    total_var = _variance(fc_vals) + _variance(ss_vals) + _variance(sp_vals)

    # Normalize: for faction weights summing to 1.0, maximum variance occurs
    # when weights alternate between extremes (e.g., [1,0,0] and [0,1,0]).
    # Each weight has variance up to 0.25 (Bernoulli), and with correlated
    # triplets the practical max is ~0.16 per weight (~0.48 total).
    # Use a calibrated value that makes alternating 0.2↔0.6 swings register
    # as clearly unstable (stability < 0.3).
    max_variance = 0.10
    normalized = min(1.0, total_var / max_variance)

    return max(0.0, min(1.0, 1.0 - normalized))


# ---------------------------------------------------------------------------
# Fascist mode behavioral overrides (T055)
# ---------------------------------------------------------------------------


def apply_fascist_overrides(
    actions: list[StateAction],
    balance: FactionBalance,
    defines: StateApparatusAIDefines,
) -> list[StateAction]:
    """Apply fascist-mode behavioral overrides to selected actions.

    In fascist mode:
    - CO_OPT → REPRESS (redirect co-optation to repression)
    - DEVELOP → DEVELOP.DISPLACE (redirect development to displacement)
    - WITHDRAW → WITHDRAW.SCORCHED_EARTH (no strategic retreat)

    Args:
        actions: Original action list from decision function.
        balance: Current FactionBalance (unused but available for future tuning).
        defines: State AI configuration.

    Returns:
        New list with overridden actions.
    """
    # Use defines to floor legitimacy costs of overridden actions
    effect_floor = defines.minimum_effect_floor

    overridden: list[StateAction] = []
    max_actions = len(actions)

    for idx in range(max_actions):
        action = actions[idx]
        overridden.append(_apply_single_override(action, balance, effect_floor))

    return overridden


def _apply_single_override(
    action: StateAction,
    balance: FactionBalance,
    effect_floor: float,
) -> StateAction:
    """Apply fascist override to a single action.

    Args:
        action: Original StateAction.
        balance: Current FactionBalance (used for faction alignment).
        effect_floor: Minimum legitimacy cost magnitude.

    Returns:
        Overridden StateAction (or original if no override applies).
    """
    verb = action.verb
    # Use dominant faction for alignment of overridden actions
    dominant = balance.dominant_faction

    if verb == StateActionType.CO_OPT:
        # CO_OPT budget → REPRESS redirect
        # Floor the legitimacy cost to at least -effect_floor (repression always costs)
        leg_cost = min(action.legitimacy_cost, -effect_floor)
        return StateAction(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            target_id=action.target_id,
            budget_cost=action.budget_cost,
            thread_cost=action.thread_cost,
            legitimacy_cost=leg_cost,
            faction_alignment=dominant if dominant else StateFaction.SECURITY_STATE,
        )

    if verb == StateActionType.DEVELOP:
        # DEVELOP → displacement-oriented sub-verb
        return StateAction(
            verb=StateActionType.DEVELOP,
            sub_verb=StateActionType.DISPLACE,
            target_id=action.target_id,
            budget_cost=action.budget_cost,
            thread_cost=action.thread_cost,
            legitimacy_cost=action.legitimacy_cost,
            faction_alignment=action.faction_alignment,
        )

    if verb == StateActionType.WITHDRAW:
        # WITHDRAW → SCORCHED_EARTH
        return StateAction(
            verb=StateActionType.WITHDRAW,
            sub_verb=StateActionType.SCORCHED_EARTH,
            target_id=action.target_id,
            budget_cost=action.budget_cost,
            thread_cost=action.thread_cost,
            legitimacy_cost=action.legitimacy_cost,
            faction_alignment=action.faction_alignment,
        )

    # All other verbs pass through unchanged
    return action


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, limit: float) -> float:
    """Clamp a value to [-limit, +limit]."""
    return max(-limit, min(limit, value))


def _variance(values: list[float]) -> float:
    """Compute population variance of a list of floats."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def _apply_single_faction_shift(
    current_balance: FactionBalance,
    target_faction: str,
    magnitude: float,
    max_shift: float,
) -> FactionBalance:
    """Apply a shift to a single faction, redistributing to others.

    Args:
        current_balance: Current FactionBalance.
        target_faction: Name of the faction field to shift.
        magnitude: Signed shift amount (positive = increase target).
        max_shift: Maximum absolute shift per tick.

    Returns:
        New normalized FactionBalance.
    """
    fc = current_balance.finance_capital
    ss = current_balance.security_state
    sp = current_balance.settler_populist

    # Clamp magnitude
    clamped = _clamp(magnitude, max_shift)

    # Apply shift to target faction, redistribute loss/gain to others
    if target_faction == "finance_capital":
        fc_new = max(0.0, fc + clamped)
        loss = fc_new - fc
        other_total = ss + sp
        if other_total > 0:
            ss_new = max(0.0, ss - loss * (ss / other_total))
            sp_new = max(0.0, sp - loss * (sp / other_total))
        else:
            ss_new = ss
            sp_new = sp
    elif target_faction == "security_state":
        ss_new = max(0.0, ss + clamped)
        loss = ss_new - ss
        other_total = fc + sp
        if other_total > 0:
            fc_new = max(0.0, fc - loss * (fc / other_total))
            sp_new = max(0.0, sp - loss * (sp / other_total))
        else:
            fc_new = fc
            sp_new = sp
    elif target_faction == "settler_populist":
        sp_new = max(0.0, sp + clamped)
        loss = sp_new - sp
        other_total = fc + ss
        if other_total > 0:
            fc_new = max(0.0, fc - loss * (fc / other_total))
            ss_new = max(0.0, ss - loss * (ss / other_total))
        else:
            fc_new = fc
            ss_new = ss
    else:
        return current_balance

    return _normalize_and_build(
        fc_new,
        ss_new,
        sp_new,
        stability=current_balance.stability,
        legitimacy=current_balance.legitimacy,
    )


def _normalize_and_build(
    fc: float,
    ss: float,
    sp: float,
    stability: float,
    legitimacy: float,
) -> FactionBalance:
    """Normalize faction weights and construct a FactionBalance.

    Args:
        fc: Finance-Capital raw weight.
        ss: Security-State raw weight.
        sp: Settler-Populist raw weight.
        stability: Stability value to preserve.
        legitimacy: Legitimacy value to preserve.

    Returns:
        Normalized FactionBalance.
    """
    total = fc + ss + sp
    if total > 0:
        fc /= total
        ss /= total
        sp /= total
    else:
        fc = 1.0 / 3.0
        ss = 1.0 / 3.0
        sp = 1.0 / 3.0

    return FactionBalance(
        finance_capital=round(fc, 6),
        security_state=round(ss, 6),
        settler_populist=round(sp, 6),
        stability=stability,
        legitimacy=legitimacy,
    )


__all__ = [
    "apply_fascist_overrides",
    "apply_material_condition_shift",
    "apply_player_action_shift",
    "apply_repression_failure_shift",
    "compute_stability",
    "renormalize_faction_balance",
]
