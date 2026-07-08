"""Unit tests for faction dynamics (Feature 039 Phase 5, US3).

Tests faction shift calculations (player actions, material conditions),
renormalization with per-tick clamping, stability metric computation,
fascist convergence detection, asymmetric reversion thresholds, and
fascist-mode behavioral overrides.

RED-phase tests: these import from ``faction_dynamics.py`` which does
not yet exist, and from ``is_fascist_convergence`` / ``check_fascist_reversion``
which are not yet implemented in ``state_ai.py``. Tests WILL fail until
GREEN-phase implementation (T051-T055).

See Also:
    ``specs/039-state-apparatus-ai/contracts/faction-balance.md``: F-01 through F-05.
    ``specs/039-state-apparatus-ai/tasks.md``: T049-T056.
    ``src/babylon/formulas/state_ai.py``: ``calculate_faction_shift`` (existing).
    ``src/babylon/ooda/state_ai/faction_dynamics.py``: Shift logic (to be created).
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, StateApparatusAIDefines
from babylon.formulas.state_ai import (
    calculate_faction_shift,
    check_fascist_reversion,
    is_fascist_convergence,
)
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.enums import StateActionType, StateFaction

# RED-phase imports -- modules do not exist yet (T051-T055)
from babylon.ooda.state_ai.faction_dynamics import (
    apply_fascist_overrides,
    apply_material_condition_shift,
    apply_player_action_shift,
    compute_stability,
    renormalize_faction_balance,
)
from tests.constants import TestConstants
from tests.unit.state_ai.conftest import make_faction_balance, make_state_action

TC = TestConstants


# =============================================================================
# Helpers
# =============================================================================


def _defines() -> StateApparatusAIDefines:
    """Load default state AI defines."""
    return GameDefines().state_ai


def _assert_sums_to_one(balance: FactionBalance, tol: float = 0.01) -> None:
    """Assert faction weights sum to 1.0 within tolerance."""
    total = balance.finance_capital + balance.security_state + balance.settler_populist
    assert 1.0 - tol <= total <= 1.0 + tol, (
        f"Faction weights must sum to 1.0, got {total}: "
        f"FC={balance.finance_capital}, SS={balance.security_state}, SP={balance.settler_populist}"
    )


def _detroit_balance() -> FactionBalance:
    """Return the Detroit 2010 default faction balance."""
    return make_faction_balance(
        finance_capital=TC.StateAI.DETROIT_FC_WEIGHT,
        security_state=TC.StateAI.DETROIT_SS_WEIGHT,
        settler_populist=TC.StateAI.DETROIT_SP_WEIGHT,
        stability=TC.StateAI.DETROIT_STABILITY,
        legitimacy=TC.StateAI.DETROIT_LEGITIMACY,
    )


# =============================================================================
# TestCalculateFactionShift (existing function)
# =============================================================================


class TestCalculateFactionShift:
    """Test existing faction shift function (calculate_faction_shift).

    Validates heat-driven SS gain, low-heat reversion, moderate-heat
    stability, per-tick clamping, and output normalization.
    """

    def test_high_heat_increases_ss(self) -> None:
        """Heat > 0.5 shifts weight toward Security-State (F-02, FR-C04)."""
        defines = _defines()
        balance = _detroit_balance()
        original_ss = balance.security_state

        shifted = calculate_faction_shift(heat=0.8, current_balance=balance, defines=defines)

        assert shifted.security_state > original_ss, (
            f"Heat=0.8 should increase SS from {original_ss}, got {shifted.security_state}"
        )

    def test_low_heat_reverts_toward_equilibrium(self) -> None:
        """Heat < 0.3 causes SS to lose weight, FC and SP to recover.

        With low threat, Finance-Capital regains influence because the
        apparatus cannot justify its budget.
        """
        defines = _defines()
        # Start with elevated SS
        balance = make_faction_balance(
            finance_capital=0.30,
            security_state=0.45,
            settler_populist=0.25,
        )
        original_ss = balance.security_state

        shifted = calculate_faction_shift(heat=0.1, current_balance=balance, defines=defines)

        assert shifted.security_state < original_ss, (
            f"Heat=0.1 should decrease SS from {original_ss}, got {shifted.security_state}"
        )
        # FC should recover faster than SP (60/40 split in implementation)
        fc_gain = shifted.finance_capital - balance.finance_capital
        sp_gain = shifted.settler_populist - balance.settler_populist
        assert fc_gain >= sp_gain, (
            f"FC gain ({fc_gain}) should equal or exceed SP gain ({sp_gain}) on reversion"
        )

    def test_moderate_heat_no_change(self) -> None:
        """Heat in [0.3, 0.5] produces no faction shift.

        This is the dead zone: threat is present but not dominant,
        so the current balance is maintained.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = calculate_faction_shift(heat=0.4, current_balance=balance, defines=defines)

        assert shifted.finance_capital == balance.finance_capital
        assert shifted.security_state == balance.security_state
        assert shifted.settler_populist == balance.settler_populist

    def test_shift_clamped_to_max(self) -> None:
        """Per-tick SS gain never exceeds max_faction_shift_per_tick.

        Even at heat=1.0 (maximum threat), the shift is bounded to
        prevent single-tick factional takeover.
        """
        defines = _defines()
        balance = _detroit_balance()
        max_shift = defines.max_faction_shift_per_tick

        shifted = calculate_faction_shift(heat=1.0, current_balance=balance, defines=defines)

        # The raw SS increase (before normalization) should not exceed max_shift.
        # After normalization the comparison is approximate.
        ss_delta = shifted.security_state - balance.security_state
        assert ss_delta <= max_shift + 0.01, (
            f"SS delta ({ss_delta}) should not exceed max_shift ({max_shift}) + normalization tolerance"
        )

    def test_result_normalized(self) -> None:
        """Output faction weights always sum to 1.0 (F-01 invariant)."""
        defines = _defines()
        balance = _detroit_balance()

        # Test across a range of heat values
        heat_values = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        max_iterations = len(heat_values)
        for idx in range(max_iterations):
            shifted = calculate_faction_shift(
                heat=heat_values[idx],
                current_balance=balance,
                defines=defines,
            )
            _assert_sums_to_one(shifted)

    def test_extreme_balance_high_heat(self) -> None:
        """SS-dominant balance (SS=0.6) with high heat doesn't exceed 1.0.

        Edge case: when SS is already high, the shift must not push
        it above the [0.0, 1.0] bound.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.20,
            security_state=0.60,
            settler_populist=0.20,
        )

        shifted = calculate_faction_shift(heat=0.9, current_balance=balance, defines=defines)

        assert shifted.security_state <= 1.0, (
            f"SS should not exceed 1.0, got {shifted.security_state}"
        )
        _assert_sums_to_one(shifted)


# =============================================================================
# TestPlayerActionShift (RED phase -- T051)
# =============================================================================


class TestPlayerActionShift:
    """Test player action -> faction shift (FR-C04, T051).

    Player actions in the simulation trigger factional balance shifts:
    - Heat generation strengthens Security-State (justifies repression)
    - Surviving repression weakens Security-State (apparatus failure)
    - Extraction disruption panics Finance-Capital (threatens accumulation)
    - Narrative victories strengthen Settler-Populist (cultural backlash)
    """

    def test_heat_generation_increases_ss(self) -> None:
        """Generating heat shifts balance toward Security-State (FR-C04).

        When the player generates heat (e.g., via organizing, strikes),
        the security apparatus gains factional weight because the threat
        justifies its budget and institutional authority.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = apply_player_action_shift(
            action_type="heat_generation",
            outcome="success",
            current_balance=balance,
            defines=defines,
        )

        assert shifted.security_state > balance.security_state, (
            f"Heat generation should increase SS from {balance.security_state}, "
            f"got {shifted.security_state}"
        )
        _assert_sums_to_one(shifted)

    def test_surviving_repression_decreases_ss(self) -> None:
        """Surviving a repression action weakens Security-State (F-03, FR-C04).

        When the target survives a REPRESS action (>50% membership retained),
        the SS loses credibility. The apparatus failed to suppress the threat,
        demonstrating ineffectiveness to the other factions.
        """
        defines = _defines()
        # Start with elevated SS to make the decline measurable
        balance = make_faction_balance(
            finance_capital=0.25,
            security_state=0.50,
            settler_populist=0.25,
        )

        shifted = apply_player_action_shift(
            action_type="surviving_repression",
            outcome="success",
            current_balance=balance,
            defines=defines,
        )

        assert shifted.security_state < balance.security_state, (
            f"Surviving repression should decrease SS from {balance.security_state}, "
            f"got {shifted.security_state}"
        )
        # Minimum effect floor must be met
        ss_delta = balance.security_state - shifted.security_state
        assert ss_delta >= defines.minimum_effect_floor, (
            f"SS decline ({ss_delta}) must meet minimum_effect_floor "
            f"({defines.minimum_effect_floor})"
        )
        _assert_sums_to_one(shifted)

    def test_extraction_disruption_increases_fc(self) -> None:
        """Disrupting extraction triggers Finance-Capital panic (FR-C04).

        When player actions disrupt capital accumulation (e.g., supply
        chain blockade, strike), Finance-Capital reacts by demanding
        stronger state intervention to restore extraction conditions.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = apply_player_action_shift(
            action_type="extraction_disruption",
            outcome="success",
            current_balance=balance,
            defines=defines,
        )

        assert shifted.finance_capital > balance.finance_capital, (
            f"Extraction disruption should increase FC from {balance.finance_capital}, "
            f"got {shifted.finance_capital}"
        )
        _assert_sums_to_one(shifted)

    def test_narrative_victory_increases_sp(self) -> None:
        """Narrative victories trigger Settler-Populist reaction (FR-C04).

        When the player wins a narrative/cultural victory (e.g., successful
        counter-narrative, media exposure), settler-populist reaction
        intensifies as a defensive response to perceived cultural threat.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = apply_player_action_shift(
            action_type="narrative_victory",
            outcome="success",
            current_balance=balance,
            defines=defines,
        )

        assert shifted.settler_populist > balance.settler_populist, (
            f"Narrative victory should increase SP from {balance.settler_populist}, "
            f"got {shifted.settler_populist}"
        )
        _assert_sums_to_one(shifted)

    def test_shift_respects_max_per_tick(self) -> None:
        """No single player action shifts any faction by more than max_shift.

        The max_faction_shift_per_tick constraint applies to all shift
        sources, including player action shifts.
        """
        defines = _defines()
        max_shift = defines.max_faction_shift_per_tick
        balance = _detroit_balance()

        shifted = apply_player_action_shift(
            action_type="heat_generation",
            outcome="success",
            current_balance=balance,
            defines=defines,
        )

        ss_delta = abs(shifted.security_state - balance.security_state)
        fc_delta = abs(shifted.finance_capital - balance.finance_capital)
        sp_delta = abs(shifted.settler_populist - balance.settler_populist)

        assert ss_delta <= max_shift + 0.01, (
            f"SS delta ({ss_delta}) exceeds max_shift ({max_shift})"
        )
        assert fc_delta <= max_shift + 0.01, (
            f"FC delta ({fc_delta}) exceeds max_shift ({max_shift})"
        )
        assert sp_delta <= max_shift + 0.01, (
            f"SP delta ({sp_delta}) exceeds max_shift ({max_shift})"
        )


# =============================================================================
# TestMaterialConditionShift (RED phase -- T052)
# =============================================================================


class TestMaterialConditionShift:
    """Test material condition -> faction shift triggers (FR-C05, T052).

    Material conditions in the simulation autonomously shift factional
    balance independent of player actions:
    - Profit rate decline empowers Finance-Capital (demands intervention)
    - Imperial rent contraction panics Settler-Populist (threatens base)
    - Legitimacy crisis empowers Security-State (crisis justifies apparatus)
    """

    def test_profit_decline_increases_fc(self) -> None:
        """Profit rate decline increases Finance-Capital influence (FR-C05).

        When the profit rate falls, Finance-Capital demands stronger state
        intervention to restore accumulation conditions. This increases
        FC's factional weight at the expense of SS and SP.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = apply_material_condition_shift(
            condition_type="profit_rate_decline",
            magnitude=0.1,
            current_balance=balance,
            defines=defines,
        )

        assert shifted.finance_capital > balance.finance_capital, (
            f"Profit decline should increase FC from {balance.finance_capital}, "
            f"got {shifted.finance_capital}"
        )
        _assert_sums_to_one(shifted)

    def test_legitimacy_crisis_increases_ss(self) -> None:
        """Legitimacy crisis increases Security-State weight (FR-C05).

        When the state faces a legitimacy crisis (e.g., exposure of
        corruption, police brutality scandal going viral), the Security-
        State gains weight because crisis justifies expanded repressive
        capacity under the guise of 'restoring order'.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = apply_material_condition_shift(
            condition_type="legitimacy_crisis",
            magnitude=0.15,
            current_balance=balance,
            defines=defines,
        )

        assert shifted.security_state > balance.security_state, (
            f"Legitimacy crisis should increase SS from {balance.security_state}, "
            f"got {shifted.security_state}"
        )
        _assert_sums_to_one(shifted)

    def test_imperial_rent_contraction_increases_sp(self) -> None:
        """Imperial rent contraction panics Settler-Populist faction (FR-C05).

        When imperial rent contracts (less surplus flowing from periphery
        to core), the material base of the settler nation is threatened.
        Settler-Populist panic intensifies as the bribes that maintain
        settler loyalty begin to dry up.
        """
        defines = _defines()
        balance = _detroit_balance()

        shifted = apply_material_condition_shift(
            condition_type="imperial_rent_contraction",
            magnitude=0.1,
            current_balance=balance,
            defines=defines,
        )

        assert shifted.settler_populist > balance.settler_populist, (
            f"Imperial rent contraction should increase SP from {balance.settler_populist}, "
            f"got {shifted.settler_populist}"
        )
        _assert_sums_to_one(shifted)

    def test_magnitude_scales_effect(self) -> None:
        """Larger magnitude produces a larger faction shift.

        A severe profit rate decline (magnitude=0.3) should produce a
        larger FC shift than a mild decline (magnitude=0.05).
        """
        defines = _defines()
        balance = _detroit_balance()

        mild_shift = apply_material_condition_shift(
            condition_type="profit_rate_decline",
            magnitude=0.05,
            current_balance=balance,
            defines=defines,
        )
        severe_shift = apply_material_condition_shift(
            condition_type="profit_rate_decline",
            magnitude=0.3,
            current_balance=balance,
            defines=defines,
        )

        mild_fc_delta = mild_shift.finance_capital - balance.finance_capital
        severe_fc_delta = severe_shift.finance_capital - balance.finance_capital

        assert severe_fc_delta > mild_fc_delta, (
            f"Severe magnitude FC delta ({severe_fc_delta}) should exceed "
            f"mild magnitude FC delta ({mild_fc_delta})"
        )

    def test_shift_respects_max_per_tick(self) -> None:
        """Material condition shifts are clamped to max_faction_shift_per_tick."""
        defines = _defines()
        max_shift = defines.max_faction_shift_per_tick
        balance = _detroit_balance()

        shifted = apply_material_condition_shift(
            condition_type="profit_rate_decline",
            magnitude=1.0,  # Extreme magnitude
            current_balance=balance,
            defines=defines,
        )

        fc_delta = abs(shifted.finance_capital - balance.finance_capital)
        assert fc_delta <= max_shift + 0.01, (
            f"FC delta ({fc_delta}) exceeds max_shift ({max_shift})"
        )


# =============================================================================
# TestRenormalization (RED phase -- T053)
# =============================================================================


class TestRenormalization:
    """Test per-tick clamping and re-normalization (T053).

    Faction balance shifts must be clamped to max_faction_shift_per_tick
    before re-normalization. The direction of each faction's shift must
    be preserved during normalization.
    """

    def test_clamp_large_shift(self) -> None:
        """A large raw shift is clamped to max_faction_shift_per_tick.

        If the raw shift would move SS by +0.15, it gets clamped to
        max_faction_shift_per_tick (0.05 default).
        """
        max_shift = TC.StateAI.MAX_FACTION_SHIFT_PER_TICK
        previous = _detroit_balance()
        # Propose a balance with an excessive SS increase
        proposed = make_faction_balance(
            finance_capital=0.25,
            security_state=0.55,
            settler_populist=0.20,
        )

        clamped = renormalize_faction_balance(
            balance=proposed,
            max_shift=max_shift,
            previous_balance=previous,
        )

        # SS delta should be at most max_shift from previous
        ss_delta = abs(clamped.security_state - previous.security_state)
        assert ss_delta <= max_shift + 0.01, (
            f"Clamped SS delta ({ss_delta}) exceeds max_shift ({max_shift})"
        )
        _assert_sums_to_one(clamped)

    def test_preserves_direction(self) -> None:
        """If proposed balance increases SS, clamped result also increases SS.

        Direction preservation is critical: clamping must reduce the
        magnitude of a shift without reversing it.
        """
        max_shift = TC.StateAI.MAX_FACTION_SHIFT_PER_TICK
        previous = _detroit_balance()
        # Propose a balance with SS increase
        proposed = make_faction_balance(
            finance_capital=0.30,
            security_state=0.50,
            settler_populist=0.20,
        )

        clamped = renormalize_faction_balance(
            balance=proposed,
            max_shift=max_shift,
            previous_balance=previous,
        )

        assert clamped.security_state >= previous.security_state, (
            f"SS should not decrease: previous={previous.security_state}, "
            f"clamped={clamped.security_state}"
        )

    def test_output_sums_to_one(self) -> None:
        """Renormalized output always sums to 1.0 (F-01 invariant)."""
        max_shift = TC.StateAI.MAX_FACTION_SHIFT_PER_TICK
        previous = _detroit_balance()
        proposed = make_faction_balance(
            finance_capital=0.35,
            security_state=0.40,
            settler_populist=0.25,
        )

        clamped = renormalize_faction_balance(
            balance=proposed,
            max_shift=max_shift,
            previous_balance=previous,
        )

        _assert_sums_to_one(clamped)

    def test_small_shift_passes_through(self) -> None:
        """A shift within max_shift passes through unclamped.

        If the proposed shift is already within bounds, renormalization
        should not alter the balance (except for normalization).
        """
        max_shift = TC.StateAI.MAX_FACTION_SHIFT_PER_TICK
        previous = _detroit_balance()
        # Propose a balance with a small SS increase (within max_shift)
        proposed = make_faction_balance(
            finance_capital=0.43,
            security_state=0.33,
            settler_populist=0.24,
        )

        clamped = renormalize_faction_balance(
            balance=proposed,
            max_shift=max_shift,
            previous_balance=previous,
        )

        # The shift should be approximately preserved
        assert clamped.security_state == pytest.approx(proposed.security_state, abs=0.02), (
            f"Small shift should be approximately preserved: "
            f"proposed={proposed.security_state}, clamped={clamped.security_state}"
        )

    def test_all_factions_clamped_independently(self) -> None:
        """Each faction's delta is independently clamped to max_shift.

        No single faction can shift by more than max_shift per tick,
        even if other factions shift by less.
        """
        max_shift = TC.StateAI.MAX_FACTION_SHIFT_PER_TICK
        previous = _detroit_balance()
        # Extreme proposed balance: all factions shift substantially
        proposed = make_faction_balance(
            finance_capital=0.15,
            security_state=0.60,
            settler_populist=0.25,
        )

        clamped = renormalize_faction_balance(
            balance=proposed,
            max_shift=max_shift,
            previous_balance=previous,
        )

        fc_delta = abs(clamped.finance_capital - previous.finance_capital)
        ss_delta = abs(clamped.security_state - previous.security_state)
        sp_delta = abs(clamped.settler_populist - previous.settler_populist)

        assert fc_delta <= max_shift + 0.01, f"FC delta ({fc_delta}) exceeds max_shift"
        assert ss_delta <= max_shift + 0.01, f"SS delta ({ss_delta}) exceeds max_shift"
        assert sp_delta <= max_shift + 0.01, f"SP delta ({sp_delta}) exceeds max_shift"


# =============================================================================
# TestStabilityComputation (RED phase -- T053)
# =============================================================================


class TestStabilityComputation:
    """Test stability metric from shift history (T053).

    Stability measures how much the faction balance has been shifting
    recently. A stable balance (low variance) yields high stability;
    volatile shifts yield low stability.
    """

    def test_constant_balance_high_stability(self) -> None:
        """Identical balances across the window yield stability near 1.0.

        No variance = maximum stability.
        """
        balance = _detroit_balance()
        history: list[FactionBalance] = [balance] * 5

        stability = compute_stability(shift_history=history, window=5)

        assert stability >= 0.9, f"Constant balance should yield stability >= 0.9, got {stability}"

    def test_volatile_shifts_low_stability(self) -> None:
        """Alternating extreme balances yield stability near 0.0.

        Maximum variance = minimum stability.
        """
        high_ss = make_faction_balance(
            finance_capital=0.20,
            security_state=0.60,
            settler_populist=0.20,
        )
        high_fc = make_faction_balance(
            finance_capital=0.60,
            security_state=0.20,
            settler_populist=0.20,
        )
        # Alternating extremes
        history: list[FactionBalance] = [high_ss, high_fc, high_ss, high_fc, high_ss]

        stability = compute_stability(shift_history=history, window=5)

        assert stability <= 0.3, f"Volatile shifts should yield stability <= 0.3, got {stability}"

    def test_stability_bounded_zero_to_one(self) -> None:
        """Stability metric is always in [0.0, 1.0]."""
        balance = _detroit_balance()
        history: list[FactionBalance] = [balance] * 3

        stability = compute_stability(shift_history=history, window=3)

        assert 0.0 <= stability <= 1.0, f"Stability must be in [0.0, 1.0], got {stability}"

    def test_window_longer_than_history_uses_available(self) -> None:
        """If window > len(history), use the full history.

        Should not raise an error; just compute over available data.
        """
        balance = _detroit_balance()
        history: list[FactionBalance] = [balance, balance]

        # window=10 but only 2 entries
        stability = compute_stability(shift_history=history, window=10)

        assert 0.0 <= stability <= 1.0, (
            f"Stability must be in [0.0, 1.0] even with short history, got {stability}"
        )


# =============================================================================
# TestFascistConvergence (RED phase -- T054)
# =============================================================================


class TestFascistConvergence:
    """Test fascist convergence detection (F-04, FR-C06, T054).

    Three-pillar model: SS > 0.4, settler CI > 0.6, FC < 0.25.
    Must hold for convergence_confirmation_ticks consecutive ticks.
    """

    def test_all_conditions_met_returns_true(self) -> None:
        """All three pillars met for enough ticks -> convergence detected.

        SS dominant (>0.4), settler CI high (>0.6), FC marginalized (<0.25).
        Held for convergence_confirmation_ticks (default 2) ticks.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        settler_ci = 0.7  # Above fascist_settler_ci_threshold (0.6)
        consecutive_ticks = defines.convergence_confirmation_ticks

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is True, (
            f"All convergence conditions met for {consecutive_ticks} ticks, "
            f"expected True, got {result}"
        )

    def test_ss_below_threshold_returns_false(self) -> None:
        """SS below fascist_security_threshold -> no convergence.

        Even with settler CI high and FC low, weak SS means no
        repressive apparatus backing for fascism.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.20,
            security_state=0.35,  # Below 0.4
            settler_populist=0.45,
        )
        settler_ci = 0.7
        consecutive_ticks = defines.convergence_confirmation_ticks

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is False, (
            f"SS={balance.security_state} below threshold {defines.fascist_security_threshold}, "
            f"expected False"
        )

    def test_settler_ci_below_threshold_returns_false(self) -> None:
        """Settler CI below threshold -> no convergence.

        Police state (high SS) without popular mass base (low settler CI)
        is not fascism -- it's authoritarian but lacks the mass movement.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        settler_ci = 0.4  # Below 0.6
        consecutive_ticks = defines.convergence_confirmation_ticks

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is False, (
            f"Settler CI={settler_ci} below threshold {defines.fascist_settler_ci_threshold}, "
            f"expected False"
        )

    def test_fc_above_ceiling_returns_false(self) -> None:
        """FC above fascist_finance_ceiling -> no convergence.

        Finance-Capital still has enough weight to resist fascist
        convergence via co-optation strategies.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.30,  # Above 0.25
            security_state=0.45,
            settler_populist=0.25,
        )
        settler_ci = 0.7
        consecutive_ticks = defines.convergence_confirmation_ticks

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is False, (
            f"FC={balance.finance_capital} above ceiling {defines.fascist_finance_ceiling}, "
            f"expected False"
        )

    def test_single_tick_insufficient(self) -> None:
        """One tick is not enough to confirm convergence (default requires 2).

        Single-tick spikes can occur due to transient events and should
        not trigger the irreversible fascist mode.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        settler_ci = 0.7
        consecutive_ticks = 1  # Less than convergence_confirmation_ticks (2)

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is False, (
            f"Single tick should be insufficient for convergence "
            f"(need {defines.convergence_confirmation_ticks}), expected False"
        )

    def test_two_consecutive_ticks_sufficient(self) -> None:
        """Exactly convergence_confirmation_ticks (default 2) ticks -> confirmed.

        The minimum confirmation window has been met.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        settler_ci = 0.7
        consecutive_ticks = defines.convergence_confirmation_ticks  # Exactly 2

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is True, (
            f"{consecutive_ticks} consecutive ticks should be sufficient, expected True"
        )

    def test_all_pillars_at_exact_thresholds(self) -> None:
        """All pillars at exact boundary values (SS=0.4, CI=0.6, FC=0.25).

        The thresholds are strict inequalities (>0.4, >0.6, <0.25),
        so values exactly AT the threshold should return False.
        """
        defines = _defines()
        # SS exactly at threshold (not above), FC exactly at ceiling (not below)
        balance = make_faction_balance(
            finance_capital=0.25,
            security_state=0.40,
            settler_populist=0.35,
        )
        settler_ci = 0.6  # Exactly at threshold, not above
        consecutive_ticks = defines.convergence_confirmation_ticks

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=consecutive_ticks,
            defines=defines,
        )

        assert result is False, (
            "Exact threshold values should not trigger convergence "
            "(strict inequalities), expected False"
        )


# =============================================================================
# TestFascistReversion (RED phase -- T054)
# =============================================================================


class TestFascistReversion:
    """Test asymmetric exit thresholds for fascist mode (F-05, FR-C07, T054).

    Fascist mode is a near-absorbing state: entry is easy but exit is hard.
    Exit requires BOTH SS < 0.25 AND settler CI < 0.30 (much harder than
    the entry thresholds of SS > 0.4, CI > 0.6).
    """

    def test_both_below_reversion_returns_true(self) -> None:
        """SS below 0.25 AND settler CI below 0.30 -> reversion possible.

        Both conditions must be met simultaneously for the system to
        exit fascist mode.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.55,
            security_state=0.20,  # Below 0.25
            settler_populist=0.25,
        )
        settler_ci = 0.25  # Below 0.30

        result = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert result is True, (
            f"Both SS ({balance.security_state}) < {defines.reversion_ss_threshold} "
            f"and CI ({settler_ci}) < {defines.reversion_ci_threshold}, expected True"
        )

    def test_ss_only_below_returns_false(self) -> None:
        """SS below reversion threshold but settler CI still high -> no reversion.

        The security apparatus has weakened, but the popular mass base
        for fascism remains. Fascism can be maintained by settler
        vigilantism even without strong formal SS.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.55,
            security_state=0.20,  # Below 0.25
            settler_populist=0.25,
        )
        settler_ci = 0.50  # Above 0.30

        result = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert result is False, (
            f"SS below threshold but CI ({settler_ci}) above "
            f"{defines.reversion_ci_threshold}, expected False"
        )

    def test_ci_only_below_returns_false(self) -> None:
        """Settler CI below reversion threshold but SS still high -> no reversion.

        The mass base has eroded, but the repressive apparatus is still
        strong enough to maintain fascist mode through force alone.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.35,
            security_state=0.40,  # Above 0.25
            settler_populist=0.25,
        )
        settler_ci = 0.20  # Below 0.30

        result = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert result is False, (
            f"CI below threshold but SS ({balance.security_state}) above "
            f"{defines.reversion_ss_threshold}, expected False"
        )

    def test_near_absorbing_resists_partial_reversion(self) -> None:
        """SS at 0.38 (above reversion threshold) -> fascism persists.

        Even though SS has dropped from its convergence entry value (>0.4),
        it's still above the reversion threshold (0.25). The near-absorbing
        nature of fascism resists partial reversion.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.32,
            security_state=0.38,  # Dropped from 0.4+ but still above 0.25
            settler_populist=0.30,
        )
        settler_ci = 0.55  # Dropped from 0.6+ but still above 0.30

        result = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert result is False, (
            f"SS={balance.security_state} and CI={settler_ci} still above reversion "
            f"thresholds, fascism should persist"
        )

    def test_exact_reversion_thresholds(self) -> None:
        """Values exactly AT reversion thresholds should NOT revert.

        The reversion conditions use strict inequalities (< threshold),
        so values exactly at the threshold don't qualify.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.50,
            security_state=0.25,  # Exactly at reversion_ss_threshold
            settler_populist=0.25,
        )
        settler_ci = 0.30  # Exactly at reversion_ci_threshold

        result = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert result is False, (
            f"Exact threshold values (SS={balance.security_state}, CI={settler_ci}) "
            f"should not trigger reversion (strict inequalities)"
        )


# =============================================================================
# TestFascistOverrides (RED phase -- T055)
# =============================================================================


class TestFascistOverrides:
    """Test behavioral overrides in fascist mode (FR-C07, T055).

    When fascist convergence is active, the state AI's action selection
    is qualitatively transformed:
    - CO_OPT budget redirects to REPRESS
    - DEVELOP shifts to displacement-oriented sub-verbs
    - WITHDRAW becomes SCORCHED_EARTH
    """

    def test_co_opt_redirected_to_repress(self) -> None:
        """CO_OPT.BRIBE becomes REPRESS sub-verb in fascist mode (FR-C07).

        In fascist mode, co-optation budgets are redirected to repression.
        The apparatus no longer attempts to absorb opposition -- it
        destroys it.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        co_opt_action = make_state_action(
            verb=StateActionType.CO_OPT,
            sub_verb=StateActionType.BRIBE,
            budget_cost=5.0,
            thread_cost=0,
            legitimacy_cost=-0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )

        overridden = apply_fascist_overrides(
            actions=[co_opt_action],
            balance=balance,
            defines=defines,
        )

        assert len(overridden) == 1, f"Expected 1 action, got {len(overridden)}"
        action = overridden[0]
        assert action.verb == StateActionType.REPRESS, (
            f"CO_OPT should be redirected to REPRESS in fascist mode, got {action.verb}"
        )

    def test_develop_shifted_to_displacement(self) -> None:
        """DEVELOP.INVEST becomes DEVELOP.DISPLACE in fascist mode (FR-C07).

        Development investment is redirected from infrastructure improvement
        to population displacement -- settler territorial expansion.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        develop_action = make_state_action(
            verb=StateActionType.DEVELOP,
            sub_verb=StateActionType.INVEST,
            budget_cost=10.0,
            thread_cost=0,
            legitimacy_cost=0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )

        overridden = apply_fascist_overrides(
            actions=[develop_action],
            balance=balance,
            defines=defines,
        )

        assert len(overridden) == 1, f"Expected 1 action, got {len(overridden)}"
        action = overridden[0]
        assert action.verb == StateActionType.DEVELOP, (
            f"Verb should remain DEVELOP, got {action.verb}"
        )
        assert action.sub_verb in {StateActionType.DISPLACE, StateActionType.REZONE}, (
            f"DEVELOP sub-verb should shift to displacement (DISPLACE or REZONE), "
            f"got {action.sub_verb}"
        )

    def test_withdraw_becomes_scorched_earth(self) -> None:
        """WITHDRAW.STRATEGIC_WITHDRAWAL becomes WITHDRAW.SCORCHED_EARTH (FR-C07).

        In fascist mode, the state does not retreat strategically --
        it destroys what it cannot hold.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        withdraw_action = make_state_action(
            verb=StateActionType.WITHDRAW,
            sub_verb=StateActionType.STRATEGIC_WITHDRAWAL,
            budget_cost=1.0,
            thread_cost=0,
            legitimacy_cost=-0.02,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )

        overridden = apply_fascist_overrides(
            actions=[withdraw_action],
            balance=balance,
            defines=defines,
        )

        assert len(overridden) == 1, f"Expected 1 action, got {len(overridden)}"
        action = overridden[0]
        assert action.verb == StateActionType.WITHDRAW, (
            f"Verb should remain WITHDRAW, got {action.verb}"
        )
        assert action.sub_verb == StateActionType.SCORCHED_EARTH, (
            f"WITHDRAW sub-verb should become SCORCHED_EARTH, got {action.sub_verb}"
        )

    def test_repress_action_unchanged(self) -> None:
        """REPRESS actions pass through unchanged in fascist mode.

        Repression is already the preferred verb in fascist mode, so
        no override is needed.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        repress_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )

        overridden = apply_fascist_overrides(
            actions=[repress_action],
            balance=balance,
            defines=defines,
        )

        assert len(overridden) == 1, f"Expected 1 action, got {len(overridden)}"
        action = overridden[0]
        assert action.verb == StateActionType.REPRESS, (
            f"REPRESS should remain REPRESS, got {action.verb}"
        )
        assert action.sub_verb == StateActionType.RAID, (
            f"REPRESS.RAID sub-verb should be unchanged, got {action.sub_verb}"
        )

    def test_multiple_actions_all_overridden(self) -> None:
        """All actions in a list are subjected to fascist overrides.

        The override function must process each action independently.
        """
        defines = _defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        actions = [
            make_state_action(
                verb=StateActionType.CO_OPT,
                sub_verb=StateActionType.BRIBE,
                budget_cost=5.0,
                thread_cost=0,
                legitimacy_cost=-0.01,
                faction_alignment=StateFaction.FINANCE_CAPITAL,
            ),
            make_state_action(
                verb=StateActionType.WITHDRAW,
                sub_verb=StateActionType.TACTICAL_RETREAT,
                budget_cost=2.0,
                thread_cost=0,
                legitimacy_cost=-0.01,
                faction_alignment=StateFaction.FINANCE_CAPITAL,
            ),
        ]

        overridden = apply_fascist_overrides(
            actions=actions,
            balance=balance,
            defines=defines,
        )

        assert len(overridden) == 2, f"Expected 2 actions, got {len(overridden)}"
        # First action: CO_OPT -> REPRESS
        assert overridden[0].verb == StateActionType.REPRESS, (
            f"First action should be REPRESS, got {overridden[0].verb}"
        )
        # Second action: WITHDRAW -> SCORCHED_EARTH
        assert overridden[1].sub_verb == StateActionType.SCORCHED_EARTH, (
            f"Second action sub-verb should be SCORCHED_EARTH, got {overridden[1].sub_verb}"
        )

    def test_empty_action_list_returns_empty(self) -> None:
        """Empty input returns empty output."""
        defines = _defines()
        balance = _detroit_balance()

        overridden = apply_fascist_overrides(
            actions=[],
            balance=balance,
            defines=defines,
        )

        assert overridden == [], f"Expected empty list, got {overridden}"
