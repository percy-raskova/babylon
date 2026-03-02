"""Contract tests for faction balance dynamics (Feature 039 Phase 5).

Behavioral contracts F-01 through F-05 from
``specs/039-state-apparatus-ai/contracts/faction-balance.md``.

These tests validate faction weight normalization, heat-driven Security-State
shifts, repression failure consequences, fascist convergence detection, and
near-absorbing state resistance. Tests for F-03, F-04, F-05 import functions
that do not yet exist (TDD RED phase).

See Also:
    :mod:`babylon.formulas.state_ai`: ``calculate_faction_shift`` (exists).
    :mod:`babylon.ooda.state_ai.faction_dynamics`: ``apply_repression_failure_shift`` (RED).
    :mod:`babylon.formulas.state_ai`: ``is_fascist_convergence``, ``check_fascist_reversion`` (RED).
    ``specs/039-state-apparatus-ai/contracts/faction-balance.md``: Contract definitions.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.formulas.state_ai import calculate_faction_shift
from tests.constants import TestConstants
from tests.contract.state_ai.conftest import make_faction_balance

TC = TestConstants

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NORMALIZATION_LO: float = 0.99
_NORMALIZATION_HI: float = 1.01
_SUSTAINED_HEAT_TICKS: int = 8
_SUSTAINED_HEAT_LEVEL: float = 0.7


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    """Build StateApparatusAIDefines with optional overrides."""
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _weight_sum(balance: object) -> float:
    """Sum the three faction weights of a FactionBalance."""
    # Use getattr to stay decoupled from type import at call sites.
    fc: float = balance.finance_capital
    ss: float = balance.security_state
    sp: float = balance.settler_populist
    return fc + ss + sp


# ===========================================================================
# F-01: Weight Normalization
# ===========================================================================


class TestWeightNormalization:
    """F-01: Weights always sum to 1.0 within tolerance [0.99, 1.01].

    Reference: FR-C02, R-003.
    Spec: faction-balance.md F-01.
    """

    def test_fresh_balance_normalized(self) -> None:
        """Default factory FactionBalance satisfies normalization invariant."""
        balance = make_faction_balance()
        total = _weight_sum(balance)
        assert _NORMALIZATION_LO <= total <= _NORMALIZATION_HI, (
            f"Fresh FactionBalance weights sum to {total}, "
            f"expected within [{_NORMALIZATION_LO}, {_NORMALIZATION_HI}]"
        )

    def test_shift_preserves_normalization(self) -> None:
        """Faction shift at moderate heat preserves normalization."""
        defines = _make_defines()
        balance = make_faction_balance()

        shifted = calculate_faction_shift(
            heat=0.6,
            current_balance=balance,
            defines=defines,
        )

        total = _weight_sum(shifted)
        assert _NORMALIZATION_LO <= total <= _NORMALIZATION_HI, (
            f"Post-shift weights sum to {total}, "
            f"expected within [{_NORMALIZATION_LO}, {_NORMALIZATION_HI}]"
        )

    def test_extreme_heat_shift_still_normalized(self) -> None:
        """Even at maximum heat (1.0), iterated shifts stay normalized."""
        defines = _make_defines()
        balance = make_faction_balance()
        max_ticks: int = 20

        for _tick in range(max_ticks):
            balance = calculate_faction_shift(
                heat=1.0,
                current_balance=balance,
                defines=defines,
            )
            total = _weight_sum(balance)
            assert _NORMALIZATION_LO <= total <= _NORMALIZATION_HI, (
                f"Tick {_tick}: weights sum to {total} at heat=1.0, "
                f"expected within [{_NORMALIZATION_LO}, {_NORMALIZATION_HI}]"
            )

    def test_low_heat_reversion_preserves_normalization(self) -> None:
        """Low-heat reversion (heat < 0.3) also preserves normalization."""
        defines = _make_defines()
        # Start with SS-dominant balance to trigger reversion path
        balance = make_faction_balance(
            finance_capital=0.20,
            security_state=0.55,
            settler_populist=0.25,
        )
        max_ticks: int = 10

        for _tick in range(max_ticks):
            balance = calculate_faction_shift(
                heat=0.1,
                current_balance=balance,
                defines=defines,
            )
            total = _weight_sum(balance)
            assert _NORMALIZATION_LO <= total <= _NORMALIZATION_HI, (
                f"Tick {_tick}: reversion weights sum to {total}, "
                f"expected within [{_NORMALIZATION_LO}, {_NORMALIZATION_HI}]"
            )

    def test_multiple_shift_cycles_normalized(self) -> None:
        """Alternating high/low heat cycles maintain normalization."""
        defines = _make_defines()
        balance = make_faction_balance()
        max_ticks: int = 20

        for tick in range(max_ticks):
            # Alternate: 5 ticks high heat, 5 ticks low heat
            heat: float = 0.8 if (tick % 10) < 5 else 0.1
            balance = calculate_faction_shift(
                heat=heat,
                current_balance=balance,
                defines=defines,
            )
            total = _weight_sum(balance)
            assert _NORMALIZATION_LO <= total <= _NORMALIZATION_HI, (
                f"Tick {tick} (heat={heat}): weights sum to {total}, "
                f"expected within [{_NORMALIZATION_LO}, {_NORMALIZATION_HI}]"
            )


# ===========================================================================
# F-02: Heat Triggers Security-State Shift
# ===========================================================================


class TestHeatSecurityStateShift:
    """F-02: Sustained heat > 0.5 increases Security-State weight.

    Reference: FR-C04, SC-010.
    Spec: faction-balance.md F-02.
    """

    def test_eight_tick_sustained_heat_increases_ss(self) -> None:
        """8 ticks at heat=0.7 raises SS by at least minimum_effect_floor.

        Contract: ``sustained Heat > 0.5 for 8 consecutive ticks`` produces
        SS increase >= minimum_effect_floor (0.02).
        """
        defines = _make_defines()
        balance = make_faction_balance()
        initial_ss: float = balance.security_state

        max_ticks: int = _SUSTAINED_HEAT_TICKS
        for _tick in range(max_ticks):
            balance = calculate_faction_shift(
                heat=_SUSTAINED_HEAT_LEVEL,
                current_balance=balance,
                defines=defines,
            )

        ss_delta = balance.security_state - initial_ss
        assert ss_delta >= defines.minimum_effect_floor, (
            f"After {max_ticks} ticks at heat={_SUSTAINED_HEAT_LEVEL}, "
            f"SS increased by {ss_delta:.4f}, expected >= {defines.minimum_effect_floor}"
        )

    def test_shift_sourced_from_fc_and_sp(self) -> None:
        """SS increase comes at expense of FC and SP (total is conserved).

        The sum FC + SP must decrease by at least as much as SS increased,
        within floating-point tolerance.
        """
        defines = _make_defines()
        balance = make_faction_balance()
        initial_fc: float = balance.finance_capital
        initial_sp: float = balance.settler_populist
        initial_ss: float = balance.security_state

        max_ticks: int = _SUSTAINED_HEAT_TICKS
        for _tick in range(max_ticks):
            balance = calculate_faction_shift(
                heat=_SUSTAINED_HEAT_LEVEL,
                current_balance=balance,
                defines=defines,
            )

        ss_gain = balance.security_state - initial_ss
        fc_sp_loss = (initial_fc + initial_sp) - (
            balance.finance_capital + balance.settler_populist
        )

        # Both FC and SP may not decline individually (normalization may shift
        # ratios), but their combined loss must approximately equal SS gain.
        assert ss_gain > 0, "SS should increase under sustained heat"
        assert fc_sp_loss > 0, "Combined FC+SP should decrease"
        assert abs(ss_gain - fc_sp_loss) < 0.01, (
            f"SS gain ({ss_gain:.4f}) should match FC+SP loss ({fc_sp_loss:.4f}) within tolerance"
        )

    def test_low_heat_does_not_increase_ss(self) -> None:
        """Heat=0.3 (within no-shift band) does not increase SS."""
        defines = _make_defines()
        balance = make_faction_balance()
        initial_ss: float = balance.security_state

        max_ticks: int = _SUSTAINED_HEAT_TICKS
        for _tick in range(max_ticks):
            balance = calculate_faction_shift(
                heat=0.3,
                current_balance=balance,
                defines=defines,
            )

        # Heat=0.3 is in the no-shift dead zone (0.3 <= heat <= 0.5)
        assert balance.security_state <= initial_ss, (
            f"Heat=0.3 should not increase SS: initial={initial_ss}, final={balance.security_state}"
        )

    def test_monotonic_ss_growth_under_sustained_heat(self) -> None:
        """SS weight is non-decreasing across ticks at sustained high heat."""
        defines = _make_defines()
        balance = make_faction_balance()
        prev_ss: float = balance.security_state

        max_ticks: int = _SUSTAINED_HEAT_TICKS
        for tick in range(max_ticks):
            balance = calculate_faction_shift(
                heat=_SUSTAINED_HEAT_LEVEL,
                current_balance=balance,
                defines=defines,
            )
            assert balance.security_state >= prev_ss, (
                f"Tick {tick}: SS decreased from {prev_ss} to "
                f"{balance.security_state} under sustained heat"
            )
            prev_ss = balance.security_state


# ===========================================================================
# F-03: Successful Repression Failure Triggers SS Decline
# ===========================================================================


class TestRepressionFailureShift:
    """F-03: Failed repression decreases Security-State weight.

    Reference: FR-C04.
    Spec: faction-balance.md F-03.

    TDD RED phase: ``apply_repression_failure_shift`` does not exist yet.
    These tests import from ``babylon.ooda.state_ai.faction_dynamics``.
    """

    @pytest.mark.red_phase
    def test_repression_failure_decreases_ss(self) -> None:
        """When REPRESS fails (target retains >50% membership), SS decreases.

        Contract: ``security_state weight decreases`` after repression failure.
        """
        # Import inside test — module does not exist yet (TDD RED).
        from babylon.ooda.state_ai.faction_dynamics import (  # type: ignore[import-not-found]
            apply_repression_failure_shift,
        )

        defines = _make_defines()
        # Start with SS-dominant balance to have room for decline
        balance = make_faction_balance(
            finance_capital=0.25,
            security_state=0.50,
            settler_populist=0.25,
        )
        initial_ss: float = balance.security_state

        shifted = apply_repression_failure_shift(
            current_balance=balance,
            membership_retained_ratio=0.6,  # 60% survived — repression failed
            defines=defines,
        )

        assert shifted.security_state < initial_ss, (
            f"SS should decrease after repression failure: "
            f"initial={initial_ss}, final={shifted.security_state}"
        )

    @pytest.mark.red_phase
    def test_repression_failure_minimum_effect(self) -> None:
        """SS decrease from failed repression meets minimum_effect_floor.

        Contract: ``decrease magnitude is at least minimum_effect_floor (0.02)``.
        """
        from babylon.ooda.state_ai.faction_dynamics import (  # type: ignore[import-not-found]
            apply_repression_failure_shift,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.25,
            security_state=0.50,
            settler_populist=0.25,
        )
        initial_ss: float = balance.security_state

        shifted = apply_repression_failure_shift(
            current_balance=balance,
            membership_retained_ratio=0.7,  # 70% survived
            defines=defines,
        )

        ss_drop = initial_ss - shifted.security_state
        assert ss_drop >= defines.minimum_effect_floor, (
            f"SS drop ({ss_drop:.4f}) must be >= minimum_effect_floor "
            f"({defines.minimum_effect_floor})"
        )

    @pytest.mark.red_phase
    def test_repression_failure_preserves_normalization(self) -> None:
        """Post-failure FactionBalance weights still sum to 1.0."""
        from babylon.ooda.state_ai.faction_dynamics import (  # type: ignore[import-not-found]
            apply_repression_failure_shift,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.25,
            security_state=0.50,
            settler_populist=0.25,
        )

        shifted = apply_repression_failure_shift(
            current_balance=balance,
            membership_retained_ratio=0.65,
            defines=defines,
        )

        total = _weight_sum(shifted)
        assert _NORMALIZATION_LO <= total <= _NORMALIZATION_HI, (
            f"Post-failure weights sum to {total}, "
            f"expected within [{_NORMALIZATION_LO}, {_NORMALIZATION_HI}]"
        )


# ===========================================================================
# F-04: Fascist Convergence Detection
# ===========================================================================


class TestFascistConvergence:
    """F-04: Three-pillar fascist convergence detection.

    Reference: FR-C06, R-008.
    Spec: faction-balance.md F-04.

    TDD RED phase: ``is_fascist_convergence`` does not exist yet.
    """

    @pytest.mark.red_phase
    def test_all_three_pillars_triggers_convergence(self) -> None:
        """All three conditions met for confirmation_ticks -> convergence True.

        Three pillars:
        1. SS > fascist_security_threshold (0.4)
        2. settler_ci > fascist_settler_ci_threshold (0.6)
        3. FC < fascist_finance_ceiling (0.25)
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            is_fascist_convergence,
        )

        defines = _make_defines()
        # All three conditions met
        balance = make_faction_balance(
            finance_capital=0.15,  # FC < 0.25 (acquiescence)
            security_state=0.55,  # SS > 0.4 (dominance)
            settler_populist=0.30,  # remainder
        )
        settler_ci: float = 0.7  # > 0.6 (mass base)

        # Provide consecutive_ticks >= convergence_confirmation_ticks (default 2)
        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=defines.convergence_confirmation_ticks,
            defines=defines,
        )

        assert result is True, (
            "All three fascist convergence pillars met for confirmation window — should return True"
        )

    @pytest.mark.red_phase
    def test_missing_ss_pillar_no_convergence(self) -> None:
        """SS below threshold -> no convergence (police state without apparatus).

        Spec: ``SS > 0.4 but settler CI < 0.6: police state, not fascism.``
        Here we test the inverse: settler CI is fine but SS is too low.
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            is_fascist_convergence,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.20,
            security_state=0.30,  # SS < 0.4 — pillar missing
            settler_populist=0.50,
        )
        settler_ci: float = 0.7

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=defines.convergence_confirmation_ticks,
            defines=defines,
        )

        assert result is False, (
            "SS below threshold (0.30 < 0.4): populist reaction without "
            "repressive apparatus backing — not fascism"
        )

    @pytest.mark.red_phase
    def test_missing_settler_ci_no_convergence(self) -> None:
        """Settler CI below threshold -> no convergence (no mass base).

        Spec: ``SS > 0.4 but settler CI < 0.6: police state, not fascism.``
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            is_fascist_convergence,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,  # SS > 0.4 — OK
            settler_populist=0.30,
        )
        settler_ci: float = 0.4  # < 0.6 — pillar missing

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=defines.convergence_confirmation_ticks,
            defines=defines,
        )

        assert result is False, (
            "Settler CI below threshold (0.4 < 0.6): police state without mass base — not fascism"
        )

    @pytest.mark.red_phase
    def test_missing_fc_acquiescence_no_convergence(self) -> None:
        """FC above ceiling -> no convergence (Finance-Capital still resisting).

        Spec: ``SS > 0.4 and settler CI > 0.6 but FC > 0.25: contested state.``
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            is_fascist_convergence,
        )

        defines = _make_defines()
        # FC > 0.25 means Finance-Capital still has power — contested state
        balance = make_faction_balance(
            finance_capital=0.30,
            security_state=0.45,  # SS > 0.4 — OK
            settler_populist=0.25,
        )
        settler_ci: float = 0.7  # > 0.6 — OK

        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=defines.convergence_confirmation_ticks,
            defines=defines,
        )

        assert result is False, (
            "FC above ceiling (0.30 > 0.25): Finance-Capital still resisting — "
            "contested state, not fascism"
        )

    @pytest.mark.red_phase
    def test_confirmation_window_required(self) -> None:
        """Single tick meeting conditions is insufficient for convergence.

        Spec: ``conditions must hold for convergence_confirmation_ticks
        consecutive ticks to prevent single-tick spikes``.
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            is_fascist_convergence,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.15,
            security_state=0.55,
            settler_populist=0.30,
        )
        settler_ci: float = 0.7

        # Only 1 consecutive tick — below confirmation window (default 2)
        result = is_fascist_convergence(
            balance=balance,
            settler_ci=settler_ci,
            consecutive_ticks=1,
            defines=defines,
        )

        assert result is False, (
            f"Only 1 consecutive tick — below confirmation window "
            f"({defines.convergence_confirmation_ticks} required)"
        )


# ===========================================================================
# F-05: Fascist Near-Absorbing State
# ===========================================================================


class TestNearAbsorbingState:
    """F-05: Fascist mode resists reversion with asymmetric thresholds.

    Reference: FR-C07, R-008.
    Spec: faction-balance.md F-05.

    Entry:  SS > 0.4, settler CI > 0.6, FC < 0.25
    Exit:   SS < 0.25 AND settler CI < 0.30

    TDD RED phase: ``check_fascist_reversion`` does not exist yet.
    """

    @pytest.mark.red_phase
    def test_partial_revert_maintains_fascist_mode(self) -> None:
        """SS drops to 0.38 (above reversion threshold) -> fascism persists.

        Spec: ``e.g., security_state drops to 0.38 ... system resists reversion``.
        SS at 0.38 is below entry threshold (0.4) but above exit threshold (0.25).
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            check_fascist_reversion,
        )

        defines = _make_defines()
        # Fascist mode already active. SS dropped but not below exit threshold.
        balance = make_faction_balance(
            finance_capital=0.22,
            security_state=0.38,  # Below entry (0.4), above exit (0.25)
            settler_populist=0.40,
        )
        settler_ci: float = 0.55  # Below entry (0.6), above exit (0.30)

        should_revert = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert should_revert is False, (
            "Partial reversion (SS=0.38, CI=0.55) should NOT exit fascist mode — "
            "near-absorbing state resists reversion"
        )

    @pytest.mark.red_phase
    def test_full_revert_exits_fascist_mode(self) -> None:
        """Both SS < 0.25 AND settler CI < 0.30 -> fascist mode exits.

        Spec: ``security_state drops below reversion_ss_threshold (0.25)
        AND settler collective_identity drops below reversion_ci_threshold (0.30)``.
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            check_fascist_reversion,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.52,
            security_state=0.24,  # Below reversion_ss_threshold (0.25)
            settler_populist=0.24,
        )
        settler_ci: float = 0.29  # Below reversion_ci_threshold (0.30)

        should_revert = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert should_revert is True, (
            "Full reversion (SS=0.24, CI=0.29) should exit fascist mode — both thresholds breached"
        )

    @pytest.mark.red_phase
    def test_entry_easier_than_exit(self) -> None:
        """Asymmetric thresholds: entry conditions are easier than exit conditions.

        Entry: SS > 0.4 (needs to exceed 0.4)
        Exit: SS < 0.25 (needs to drop below 0.25 — a 0.15+ swing)

        Entry: CI > 0.6 (needs to exceed 0.6)
        Exit: CI < 0.30 (needs to drop below 0.30 — a 0.30+ swing)

        This models the historical reality that fascism is easier to enter
        than to exit.
        """
        defines = _make_defines()

        # Entry threshold gaps (how far you need to go to enter)
        entry_ss = defines.fascist_security_threshold  # 0.4
        entry_ci = defines.fascist_settler_ci_threshold  # 0.6

        # Exit threshold gaps (how far you need to go to exit)
        exit_ss = defines.reversion_ss_threshold  # 0.25
        exit_ci = defines.reversion_ci_threshold  # 0.30

        # The SS gap between entry and exit thresholds
        ss_asymmetry = entry_ss - exit_ss
        assert ss_asymmetry > 0, (
            f"Entry SS threshold ({entry_ss}) must be higher than exit "
            f"SS threshold ({exit_ss}) for asymmetric hysteresis"
        )

        # The CI gap between entry and exit thresholds
        ci_asymmetry = entry_ci - exit_ci
        assert ci_asymmetry > 0, (
            f"Entry CI threshold ({entry_ci}) must be higher than exit "
            f"CI threshold ({exit_ci}) for asymmetric hysteresis"
        )

        # Verify the TestConstants match the defines (cross-check)
        assert entry_ss == TC.StateAI.FASCIST_SS_THRESHOLD
        assert entry_ci == TC.StateAI.FASCIST_SETTLER_CI_THRESHOLD
        assert exit_ss == TC.StateAI.REVERSION_SS_THRESHOLD
        assert exit_ci == TC.StateAI.REVERSION_CI_THRESHOLD

    @pytest.mark.red_phase
    def test_only_ss_below_exit_does_not_revert(self) -> None:
        """SS below exit threshold but CI above exit -> no reversion.

        Both conditions must be met simultaneously for reversion.
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            check_fascist_reversion,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.52,
            security_state=0.24,  # Below reversion_ss_threshold (0.25)
            settler_populist=0.24,
        )
        settler_ci: float = 0.45  # Above reversion_ci_threshold (0.30)

        should_revert = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert should_revert is False, (
            "Only SS below exit threshold (CI=0.45 still above 0.30) — fascism persists"
        )

    @pytest.mark.red_phase
    def test_only_ci_below_exit_does_not_revert(self) -> None:
        """CI below exit threshold but SS above exit -> no reversion.

        Both conditions must be met simultaneously for reversion.
        """
        from babylon.formulas.state_ai import (  # type: ignore[attr-error]
            check_fascist_reversion,
        )

        defines = _make_defines()
        balance = make_faction_balance(
            finance_capital=0.35,
            security_state=0.35,  # Above reversion_ss_threshold (0.25)
            settler_populist=0.30,
        )
        settler_ci: float = 0.25  # Below reversion_ci_threshold (0.30)

        should_revert = check_fascist_reversion(
            balance=balance,
            settler_ci=settler_ci,
            defines=defines,
        )

        assert should_revert is False, (
            "Only CI below exit threshold (SS=0.35 still above 0.25) — fascism persists"
        )
