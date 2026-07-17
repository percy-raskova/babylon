"""Market-scissors formula laws (Program 23, ADR077).

Behavioral contracts (Constitution III.12): the law of value as restoring
force, boundedness, and determinism are pinned as input→output laws, not
implementation choreography.
"""

from __future__ import annotations

import pytest

from babylon.formulas.market import (
    calculate_ema,
    calculate_growth_drive,
    calculate_scissors_balance,
    calculate_scissors_step,
)

pytestmark = pytest.mark.math


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
