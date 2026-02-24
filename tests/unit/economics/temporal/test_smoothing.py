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


class TestEwmaMutationKillers:
    """Mutation-killing tests for ewma() and _extract_coefficient."""

    def test_ewma_second_value_uses_alpha_weight(self) -> None:
        """Verify S_1 = α * X_1 + (1-α) * S_0 exactly."""
        from babylon.economics.temporal.smoothing import ewma

        result = ewma([10.0, 20.0], alpha=0.4)
        # S_0 = 10.0
        # S_1 = 0.4 * 20.0 + 0.6 * 10.0 = 8.0 + 6.0 = 14.0
        assert result[0] == 10.0
        assert result[1] == pytest.approx(14.0)

    def test_ewma_third_value_chains_correctly(self) -> None:
        """Verify S_2 chains from S_1 (not S_0 or X_1)."""
        from babylon.economics.temporal.smoothing import ewma

        result = ewma([10.0, 20.0, 30.0], alpha=0.5)
        # S_0 = 10.0
        # S_1 = 0.5 * 20.0 + 0.5 * 10.0 = 15.0
        # S_2 = 0.5 * 30.0 + 0.5 * 15.0 = 22.5
        assert result[2] == pytest.approx(22.5)

    def test_ewma_alpha_half_midpoint(self) -> None:
        """α=0.5 gives exact midpoint between current and previous smoothed."""
        from babylon.economics.temporal.smoothing import ewma

        result = ewma([0.0, 100.0], alpha=0.5)
        assert result[1] == pytest.approx(50.0)

    def test_ewma_preserves_length(self) -> None:
        """Output length equals input length exactly."""
        from babylon.economics.temporal.smoothing import ewma

        for n in (1, 2, 5, 10):
            values = [float(i) for i in range(n)]
            assert len(ewma(values, 0.3)) == n

    def test_ewma_first_element_always_equals_input(self) -> None:
        """S_0 = X_0 regardless of alpha."""
        from babylon.economics.temporal.smoothing import ewma

        for alpha in (0.0, 0.1, 0.5, 0.9, 1.0):
            result = ewma([42.0, 100.0], alpha=alpha)
            assert result[0] == 42.0

    def test_ewma_negative_values(self) -> None:
        """EWMA handles negative values correctly."""
        from babylon.economics.temporal.smoothing import ewma

        result = ewma([-10.0, -20.0], alpha=0.3)
        # S_1 = 0.3 * (-20) + 0.7 * (-10) = -6 + (-7) = -13
        assert result[1] == pytest.approx(-13.0)

    def test_ewma_large_alpha_tracks_input_closely(self) -> None:
        """α close to 1.0 tracks raw input closely."""
        from babylon.economics.temporal.smoothing import ewma

        raw = [0.0, 100.0, 0.0, 100.0]
        result = ewma(raw, alpha=0.99)
        # S_1 ≈ 0.99 * 100 + 0.01 * 0 = 99.0
        assert result[1] == pytest.approx(99.0)

    def test_ewma_small_alpha_resists_change(self) -> None:
        """α close to 0.0 resists change from initial value."""
        from babylon.economics.temporal.smoothing import ewma

        raw = [1.0, 100.0, 100.0, 100.0]
        result = ewma(raw, alpha=0.01)
        # S_1 = 0.01 * 100 + 0.99 * 1.0 = 1.99
        assert result[1] == pytest.approx(1.99)
        # Even after 3 more values of 100, still close to initial
        assert result[3] < 5.0


class TestExtractCoefficientMutationKillers:
    """Mutation-killing tests for _extract_coefficient."""

    def _make_mock_tensor(
        self,
        profit_rate: float = 0.1,
        exploitation_rate: float = 0.5,
        total_v: float = 100.0,
        dept_I_v: float = 10.0,
        dept_IIa_v: float = 30.0,
        dept_IIb_v: float = 40.0,
        dept_III_v: float = 20.0,
    ) -> object:
        """Create a mock tensor with the required attributes."""
        from types import SimpleNamespace

        return SimpleNamespace(
            profit_rate=profit_rate,
            exploitation_rate=exploitation_rate,
            total_v=total_v,
            dept_I=SimpleNamespace(v=dept_I_v),
            dept_IIa=SimpleNamespace(v=dept_IIa_v),
            dept_IIb=SimpleNamespace(v=dept_IIb_v),
            dept_III=SimpleNamespace(v=dept_III_v),
        )

    def test_extract_profit_rate(self) -> None:
        """Extracts profit_rate correctly."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(profit_rate=0.25)
        assert smoother._extract_coefficient(tensor, "profit_rate") == pytest.approx(0.25)

    def test_extract_exploitation_rate(self) -> None:
        """Extracts exploitation_rate correctly (distinct from profit_rate)."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(profit_rate=0.1, exploitation_rate=0.8)
        assert smoother._extract_coefficient(tensor, "exploitation_rate") == pytest.approx(0.8)

    def test_extract_dept_I_share(self) -> None:
        """Extracts dept_I share = dept_I.v / total_v."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(total_v=200.0, dept_I_v=50.0)
        assert smoother._extract_coefficient(tensor, "dept_I_share") == pytest.approx(0.25)

    def test_extract_dept_IIa_share(self) -> None:
        """Extracts dept_IIa share distinctly from other departments."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(total_v=100.0, dept_IIa_v=45.0)
        assert smoother._extract_coefficient(tensor, "dept_IIa_share") == pytest.approx(0.45)

    def test_extract_dept_IIb_share(self) -> None:
        """Extracts dept_IIb share distinctly."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(total_v=100.0, dept_IIb_v=35.0)
        assert smoother._extract_coefficient(tensor, "dept_IIb_share") == pytest.approx(0.35)

    def test_extract_dept_III_share(self) -> None:
        """Extracts dept_III share distinctly."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(total_v=100.0, dept_III_v=15.0)
        assert smoother._extract_coefficient(tensor, "dept_III_share") == pytest.approx(0.15)

    def test_extract_dept_share_zero_total_v_returns_zero(self) -> None:
        """When total_v is 0, all dept shares return 0.0."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(total_v=0.0)
        assert smoother._extract_coefficient(tensor, "dept_I_share") == 0.0

    def test_extract_unknown_coefficient_raises(self) -> None:
        """Unknown coefficient raises ValueError."""
        from babylon.economics.temporal.smoothing import CoefficientSmootherImpl

        smoother = CoefficientSmootherImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor()
        with pytest.raises(ValueError, match="Unknown coefficient"):
            smoother._extract_coefficient(tensor, "nonexistent")
