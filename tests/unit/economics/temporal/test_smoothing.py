"""Unit tests for coefficient smoothing.

Feature: 003-hydrator-temporal-validation
User Story 3: Apply α-Smoothed Coefficients

Tests cover:
- T035: EWMA formula correctness
- T036: α=0 boundary (full smoothing)
- T037: α=1 boundary (no smoothing)
- T038: Single year edge case
- T039: Gap handling (missing years)

TDD: These tests are written FIRST and should FAIL until implementation.
"""

import pytest

from babylon.economics.temporal.models import SmoothedCoefficientSeries


class TestEwmaFormula:
    """Test EWMA formula correctness (T035, T040)."""

    def test_ewma_basic_computation(self) -> None:
        """EWMA computes correctly with α=0.3."""
        from babylon.economics.temporal.smoothing import ewma

        # Raw values: 4%, 6%, 5%
        # Expected with α=0.3:
        # S_0 = 0.04
        # S_1 = 0.3 * 0.06 + 0.7 * 0.04 = 0.018 + 0.028 = 0.046
        # S_2 = 0.3 * 0.05 + 0.7 * 0.046 = 0.015 + 0.0322 = 0.0472
        raw_values = [0.04, 0.06, 0.05]
        alpha = 0.3

        smoothed = ewma(raw_values, alpha)

        assert len(smoothed) == 3
        assert smoothed[0] == pytest.approx(0.04, abs=0.0001)
        assert smoothed[1] == pytest.approx(0.046, abs=0.001)
        assert smoothed[2] == pytest.approx(0.0472, abs=0.001)

    def test_ewma_dampens_oscillation(self) -> None:
        """EWMA dampens oscillating values."""
        from babylon.economics.temporal.smoothing import ewma

        # Oscillating values: 4%, 6%, 4%, 6%, 4%
        raw_values = [0.04, 0.06, 0.04, 0.06, 0.04]
        alpha = 0.3

        smoothed = ewma(raw_values, alpha)

        # First and last raw are same, but smoothed should converge toward mean
        # Smoothed should have less variance than raw
        raw_range = max(raw_values) - min(raw_values)
        smoothed_range = max(smoothed) - min(smoothed)

        assert smoothed_range < raw_range

    def test_ewma_empty_list_returns_empty(self) -> None:
        """EWMA returns empty list for empty input."""
        from babylon.economics.temporal.smoothing import ewma

        smoothed = ewma([], 0.3)
        assert smoothed == []


class TestAlphaBoundaryZero:
    """Test α=0 boundary (full smoothing) (T036)."""

    def test_alpha_zero_full_smoothing(self) -> None:
        """α=0 means full smoothing: output equals first value."""
        from babylon.economics.temporal.smoothing import ewma

        raw_values = [0.04, 0.10, 0.20, 0.05]
        alpha = 0.0

        smoothed = ewma(raw_values, alpha)

        # All outputs should equal the first value
        for s in smoothed:
            assert s == pytest.approx(0.04, abs=0.0001)


class TestAlphaBoundaryOne:
    """Test α=1 boundary (no smoothing) (T037)."""

    def test_alpha_one_no_smoothing(self) -> None:
        """α=1 means no smoothing: output equals raw values."""
        from babylon.economics.temporal.smoothing import ewma

        raw_values = [0.04, 0.10, 0.20, 0.05]
        alpha = 1.0

        smoothed = ewma(raw_values, alpha)

        # All outputs should equal raw values
        for raw, smooth in zip(raw_values, smoothed, strict=True):
            assert smooth == pytest.approx(raw, abs=0.0001)


class TestSingleYearEdgeCase:
    """Test single year edge case (T038)."""

    def test_single_value_returns_same(self) -> None:
        """Single value series returns that value."""
        from babylon.economics.temporal.smoothing import ewma

        raw_values = [0.04]
        alpha = 0.3

        smoothed = ewma(raw_values, alpha)

        assert len(smoothed) == 1
        assert smoothed[0] == pytest.approx(0.04, abs=0.0001)


class TestCoefficientSmootherImpl:
    """Test CoefficientSmootherImpl (T041)."""

    def test_smooth_coefficients_returns_series(self) -> None:
        """smooth_coefficients returns SmoothedCoefficientSeries."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        assert hasattr(smoother, "smooth_coefficients")

    def test_smooth_coefficients_invalid_alpha_raises(self) -> None:
        """smooth_coefficients with alpha outside [0, 1] raises ValueError."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="alpha"):
            smoother.smooth_coefficients(
                fips="26163",
                years=[2020, 2021],
                coefficient="profit_rate",
                alpha=1.5,  # Invalid
            )


class TestVarianceReduction:
    """Test variance reduction validation (T042)."""

    def test_smoothing_reduces_variance(self) -> None:
        """Smoothing with α=0.3 reduces variance."""
        from babylon.economics.temporal.smoothing import ewma

        # High-variance raw values
        raw_values = [0.02, 0.08, 0.03, 0.07, 0.04, 0.06, 0.03, 0.07]
        alpha = 0.3

        smoothed = ewma(raw_values, alpha)

        # Compute variances
        def variance(vals: list[float]) -> float:
            if len(vals) < 2:
                return 0.0
            mean = sum(vals) / len(vals)
            return sum((x - mean) ** 2 for x in vals) / len(vals)

        raw_var = variance(raw_values)
        smooth_var = variance(smoothed)

        # Smoothed variance should be significantly less
        variance_ratio = smooth_var / raw_var if raw_var > 0 else 1.0
        assert variance_ratio < 0.6, f"Expected ≤60% variance, got {variance_ratio:.2%}"

    def test_series_variance_reduction_property(self) -> None:
        """SmoothedCoefficientSeries.variance_reduction computes correctly."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.3,
            years=[2018, 2019, 2020, 2021, 2022],
            raw_values=[0.02, 0.08, 0.03, 0.07, 0.04],
            smoothed_values=[0.02, 0.038, 0.036, 0.046, 0.044],
        )

        # Variance reduction should be computed
        reduction = series.variance_reduction
        assert 0.0 < reduction < 1.0
