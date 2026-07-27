"""Unit tests for babylon.domain.economics.sigma.wage_alignment (RED phase first)."""

from __future__ import annotations

import pytest

from babylon.domain.economics.sigma.wage_alignment import (
    compute_wage_deviation,
    compute_wage_target,
    fit_linear_wage_target,
)


class TestFitLinearWageTarget:
    def test_fits_exact_line_through_noiseless_points(self) -> None:
        # w = 5*sigma + 20, sampled at sigma = -1, 0, 1, 2
        sigma_values = [-1.0, 0.0, 1.0, 2.0]
        wage_values = [15.0, 20.0, 25.0, 30.0]
        model = fit_linear_wage_target(sigma_values, wage_values)
        assert model.slope == pytest.approx(5.0, abs=1e-9)
        assert model.intercept == pytest.approx(20.0, abs=1e-9)
        assert model.n_observations == 4

    def test_raises_on_fewer_than_two_points(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            fit_linear_wage_target([0.0], [20.0])

    def test_raises_on_mismatched_lengths(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            fit_linear_wage_target([0.0, 1.0], [20.0])

    def test_raises_on_degenerate_sigma_values(self) -> None:
        with pytest.raises(ValueError, match="degenerate"):
            fit_linear_wage_target([1.0, 1.0, 1.0], [10.0, 20.0, 30.0])


class TestComputeWageTarget:
    def test_evaluates_linear_model_at_sigma(self) -> None:
        from babylon.domain.economics.sigma.types import WageTargetModel

        model = WageTargetModel(slope=5.0, intercept=20.0, n_observations=4)
        assert compute_wage_target(sigma=1.0, model=model) == pytest.approx(25.0)

    def test_negative_target_raises_loudly(self) -> None:
        # A model whose domain doesn't cover very negative sigma can imply a
        # negative wage — Currency validation must reject it rather than
        # silently clamp to zero (Loud Failure, Constitution III.11).
        from babylon.domain.economics.sigma.types import WageTargetModel

        model = WageTargetModel(slope=5.0, intercept=20.0, n_observations=4)
        with pytest.raises(ValueError):
            compute_wage_target(sigma=-10.0, model=model)


class TestComputeWageDeviation:
    def test_positive_deviation_when_actual_exceeds_target(self) -> None:
        assert compute_wage_deviation(actual_wage=30.0, target_wage=25.0) == pytest.approx(5.0)

    def test_negative_deviation_when_actual_below_target(self) -> None:
        assert compute_wage_deviation(actual_wage=20.0, target_wage=25.0) == pytest.approx(-5.0)

    def test_zero_deviation_when_equal(self) -> None:
        assert compute_wage_deviation(actual_wage=25.0, target_wage=25.0) == pytest.approx(0.0)
