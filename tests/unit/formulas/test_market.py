"""Market-scissors formula laws (Program 23, ADR077).

Behavioral contracts (Constitution III.12): the law of value as restoring
force, boundedness, and determinism are pinned as input→output laws, not
implementation choreography.
"""

from __future__ import annotations

import pytest

from babylon.formulas.market import (
    calculate_anchor_pull,
    calculate_correction_severity,
    calculate_correction_snap,
    calculate_ema,
    calculate_growth_drive,
    calculate_overhang,
    calculate_scissors_balance,
    calculate_scissors_step,
    calculate_serviceable_divergence,
)

pytestmark = pytest.mark.math


class TestServiceableDivergence:
    """ADR078: what the rate of profit can service (Vol. III part 3 × part 5)."""

    def test_zero_profit_serves_only_the_base(self) -> None:
        assert calculate_serviceable_divergence(0.0, base=0.55, slope=4.0) == 0.55

    def test_healthy_profit_extends_serviceability(self) -> None:
        assert calculate_serviceable_divergence(0.1, base=0.55, slope=4.0) == pytest.approx(0.95)

    def test_negative_profit_clamps_to_base(self) -> None:
        """A loss-making economy services no more than the base — never less
        (the floor is the credit system's intrinsic tolerance, not a debt)."""
        assert calculate_serviceable_divergence(-0.2, base=0.55, slope=4.0) == 0.55

    def test_absent_profit_rate_is_the_base(self) -> None:
        """No profit observable → honest fallback to the base (III.11)."""
        assert calculate_serviceable_divergence(None, base=0.55, slope=4.0) == 0.55


class TestServiceableDivergenceInterestBurden:
    """U6: a financialised county tightens its own correction threshold
    independent of profit rate (Vol. III part 3 meeting part 5)."""

    def test_interest_burden_tightens_the_threshold(self) -> None:
        healthy = calculate_serviceable_divergence(0.1, base=0.55, slope=4.0)
        tightened = calculate_serviceable_divergence(
            0.1, base=0.55, slope=4.0, interest_burden=0.3, interest_slope=1.0
        )
        assert tightened < healthy
        assert tightened == pytest.approx(0.65)

    def test_absent_interest_burden_is_bit_identical_to_pre_u6(self) -> None:
        assert calculate_serviceable_divergence(
            0.1, base=0.55, slope=4.0, interest_burden=None, interest_slope=1.0
        ) == pytest.approx(0.95)

    def test_zero_interest_slope_is_inert(self) -> None:
        assert calculate_serviceable_divergence(
            0.1, base=0.55, slope=4.0, interest_burden=5.0, interest_slope=0.0
        ) == pytest.approx(0.95)

    def test_floor_at_zero(self) -> None:
        assert (
            calculate_serviceable_divergence(
                0.0, base=0.1, slope=0.0, interest_burden=1.0, interest_slope=1.0
            )
            == 0.0
        )


class TestOverhang:
    def test_within_serviceability_is_zero(self) -> None:
        assert calculate_overhang(0.4, 0.55) == 0.0

    def test_excess_is_the_difference(self) -> None:
        assert calculate_overhang(0.9, 0.55) == pytest.approx(0.35)

    def test_negative_fictitious_never_overhangs(self) -> None:
        """Undervalued claims (fictitious below real) are no crisis trigger."""
        assert calculate_overhang(-1.0, 0.55) == 0.0


class TestCorrectionSnap:
    def test_snap_closes_severity_fraction(self) -> None:
        log, _vel = calculate_correction_snap(1.0, 0.2, severity=0.6)
        assert log == pytest.approx(0.4)

    def test_snap_kills_upward_momentum(self) -> None:
        _log, vel = calculate_correction_snap(1.0, 0.2, severity=0.6)
        assert vel == 0.0

    def test_snap_preserves_downward_momentum(self) -> None:
        """Panic overshoot is real: an already-falling series keeps falling."""
        _log, vel = calculate_correction_snap(1.0, -0.1, severity=0.6)
        assert vel == pytest.approx(-0.1)

    def test_snap_is_antisymmetric(self) -> None:
        """A negative log ratio snaps toward zero from below, same law."""
        log, _vel = calculate_correction_snap(-1.0, 0.0, severity=0.6)
        assert log == pytest.approx(-0.4)

    def test_full_severity_reaches_par(self) -> None:
        log, _vel = calculate_correction_snap(1.7, 0.5, severity=1.0)
        assert log == 0.0


class TestScissorsStep:
    def test_zero_state_zero_drive_stays_at_value(self) -> None:
        assert calculate_scissors_step(
            0.0, 0.0, 0.0, reversion=0.02, damping=0.15, max_abs_log=2.0
        ) == (0.0, 0.0)

    def test_law_of_value_restores_perturbation(self) -> None:
        """An opened scissors with no drive decays toward zero.

        Marx's gravitation of price to value (Capital Vol. III ch. 10) as a
        dynamical law: the reversion term is the ONLY force and it closes
        the gap.
        """
        log_ratio, velocity = 1.0, 0.0
        for _ in range(400):  # fixed bound (Power-of-10 rule 2)
            log_ratio, velocity = calculate_scissors_step(
                log_ratio, velocity, 0.0, reversion=0.02, damping=0.15, max_abs_log=2.0
            )
        assert abs(log_ratio) < 0.05

    def test_positive_drive_opens_scissors_upward(self) -> None:
        log_ratio, velocity = calculate_scissors_step(
            0.0, 0.0, 0.1, reversion=0.02, damping=0.15, max_abs_log=2.0
        )
        assert log_ratio > 0.0
        assert velocity > 0.0

    def test_clamp_kills_momentum_at_upper_rail(self) -> None:
        log_ratio, velocity = calculate_scissors_step(
            1.99, 5.0, 1.0, reversion=0.0, damping=0.0, max_abs_log=2.0
        )
        assert log_ratio == 2.0
        assert velocity == 0.0

    def test_clamp_kills_momentum_at_lower_rail(self) -> None:
        log_ratio, velocity = calculate_scissors_step(
            -1.99, -5.0, -1.0, reversion=0.0, damping=0.0, max_abs_log=2.0
        )
        assert log_ratio == -2.0
        assert velocity == 0.0

    def test_deterministic(self) -> None:
        a = calculate_scissors_step(0.3, -0.1, 0.05, reversion=0.02, damping=0.15, max_abs_log=2.0)
        b = calculate_scissors_step(0.3, -0.1, 0.05, reversion=0.02, damping=0.15, max_abs_log=2.0)
        assert a == b

    def test_stays_bounded_under_sustained_extreme_drive(self) -> None:
        """No parameterization the defines allow can escape the clamp."""
        log_ratio, velocity = 0.0, 0.0
        for _ in range(200):  # fixed bound
            log_ratio, velocity = calculate_scissors_step(
                log_ratio, velocity, 5.0, reversion=0.0, damping=0.0, max_abs_log=2.0
            )
            assert -2.0 <= log_ratio <= 2.0


class TestGrowthDrive:
    def test_zero_previous_is_honest_zero(self) -> None:
        assert calculate_growth_drive(5.0, 0.0, sensitivity=1.0) == 0.0

    def test_relative_growth(self) -> None:
        assert calculate_growth_drive(1.1, 1.0, sensitivity=1.0) == pytest.approx(0.1)

    def test_contraction_is_negative(self) -> None:
        assert calculate_growth_drive(0.9, 1.0, sensitivity=2.0) == pytest.approx(-0.2)


class TestEma:
    def test_alpha_one_tracks_value(self) -> None:
        assert calculate_ema(3.0, 7.0, alpha=1.0) == 7.0

    def test_blend(self) -> None:
        assert calculate_ema(0.0, 1.0, alpha=0.25) == pytest.approx(0.25)


class TestBalance:
    def test_zero_log_is_balanced(self) -> None:
        assert calculate_scissors_balance(0.0, scale=0.5) == 0.0

    def test_positive_log_is_price_pole(self) -> None:
        assert 0.0 < calculate_scissors_balance(0.5, scale=0.5) < 1.0

    def test_bounded(self) -> None:
        assert calculate_scissors_balance(100.0, scale=0.5) == pytest.approx(1.0)
        assert calculate_scissors_balance(-100.0, scale=0.5) == pytest.approx(-1.0)

    def test_antisymmetric(self) -> None:
        assert calculate_scissors_balance(0.7, scale=0.5) == pytest.approx(
            -calculate_scissors_balance(-0.7, scale=0.5)
        )


class TestCorrectionSeverity:
    """U6: a debt spiral makes the re-identification of claims with real
    surplus MORE violent — the accumulated-debt term on correction
    severity."""

    def test_absent_debt_ratio_is_the_base_severity(self) -> None:
        assert calculate_correction_severity(0.6, debt_ratio=None, slope=0.5) == 0.6

    def test_debt_ratio_increases_severity(self) -> None:
        assert calculate_correction_severity(0.6, debt_ratio=0.2, slope=0.5) == pytest.approx(0.7)

    def test_severity_clamps_to_one(self) -> None:
        assert calculate_correction_severity(0.6, debt_ratio=5.0, slope=1.0) == 1.0

    def test_negative_debt_ratio_never_reduces_severity(self) -> None:
        assert calculate_correction_severity(0.6, debt_ratio=-1.0, slope=0.5) == 0.6

    def test_zero_slope_is_inert(self) -> None:
        assert calculate_correction_severity(0.6, debt_ratio=10.0, slope=0.0) == 0.6


class TestAnchorPull:
    """D1/U6: pulls the fictitious oscillator toward the FRED-grounded
    anchor while real financial data covers this tick; absent anchor is
    inert — the oscillator's endogenous dynamics carry the other ~85% of
    a campaign (§3.3 D1)."""

    def test_absent_anchor_is_zero_drive(self) -> None:
        assert calculate_anchor_pull(None, 0.4, gain=0.3) == 0.0

    def test_pulls_toward_a_higher_anchor(self) -> None:
        assert calculate_anchor_pull(1.0, 0.4, gain=0.3) == pytest.approx(0.18)

    def test_pulls_toward_a_lower_anchor(self) -> None:
        assert calculate_anchor_pull(0.0, 0.4, gain=0.3) == pytest.approx(-0.12)

    def test_zero_gain_is_inert_even_when_anchored(self) -> None:
        assert calculate_anchor_pull(1.0, 0.4, gain=0.0) == 0.0

    def test_at_the_anchor_the_pull_is_zero(self) -> None:
        assert calculate_anchor_pull(0.4, 0.4, gain=0.5) == 0.0
