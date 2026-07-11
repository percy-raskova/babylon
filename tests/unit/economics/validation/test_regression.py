"""Tests for falsifiability regression validation (Feature 005 - US3).

TDD RED Phase: These tests define the contract for regression validation.

The domestic hours ~ 1/income regression validates the theoretical prediction
that lower-income households spend more time on unpaid reproductive labor.
A positive coefficient (β > 0) confirms the inverse relationship.

See Also:
    specs/005-atus-department-iii/spec.md User Story 3
    specs/005-atus-department-iii/research.md Section 5
"""

from __future__ import annotations

import pytest


class TestRegressionResult:
    """Test RegressionResult Pydantic model (T029)."""

    def test_regression_result_has_required_fields(self) -> None:
        """RegressionResult has slope, intercept, r_value, p_value, std_err."""
        from babylon.domain.economics.validation.regression import RegressionResult

        result = RegressionResult(
            slope=0.5,
            intercept=10.0,
            r_value=0.7,
            p_value=0.01,
            std_err=0.1,
        )
        assert result.slope == 0.5
        assert result.intercept == 10.0
        assert result.r_value == 0.7
        assert result.p_value == 0.01
        assert result.std_err == 0.1

    def test_regression_result_is_immutable(self) -> None:
        """RegressionResult should be frozen."""
        from pydantic import ValidationError

        from babylon.domain.economics.validation.regression import RegressionResult

        result = RegressionResult(
            slope=0.5,
            intercept=10.0,
            r_value=0.7,
            p_value=0.01,
            std_err=0.1,
        )
        with pytest.raises(ValidationError):
            result.slope = 1.0  # type: ignore[misc]


class TestDomesticHoursRegression:
    """Test validate_domestic_hours_regression function (T027-T028)."""

    # T027: Regression produces positive coefficient β > 0
    def test_regression_positive_coefficient(self) -> None:
        """Regression of domestic_hours ~ 1/income has positive slope (SC-005).

        Theoretical expectation: Lower income households spend more time on
        unpaid reproductive labor. This means domestic_hours increases as
        1/income increases, producing a positive coefficient.
        """
        from babylon.domain.economics.validation.regression import (
            validate_domestic_hours_regression,
        )

        result = validate_domestic_hours_regression()

        # SC-005: Coefficient must be positive
        assert result.slope > 0, (
            f"Expected positive slope for domestic_hours ~ 1/income, got {result.slope}"
        )

    # T028: Regression uses scipy.stats.linregress
    def test_regression_returns_valid_statistics(self) -> None:
        """Regression returns valid statistical measures."""
        from babylon.domain.economics.validation.regression import (
            validate_domestic_hours_regression,
        )

        result = validate_domestic_hours_regression()

        # Should have valid statistical measures from scipy.stats.linregress
        assert isinstance(result.slope, float)
        assert isinstance(result.intercept, float)
        assert isinstance(result.r_value, float)
        assert isinstance(result.p_value, float)
        assert isinstance(result.std_err, float)

        # r_value should be in [-1, 1]
        assert -1.0 <= result.r_value <= 1.0

        # p_value should be in [0, 1]
        assert 0.0 <= result.p_value <= 1.0

        # std_err should be non-negative
        assert result.std_err >= 0.0

    def test_regression_uses_seed_data(self) -> None:
        """Regression uses occupation multipliers from ATUS seed data."""
        from babylon.domain.economics.validation.regression import (
            validate_domestic_hours_regression,
        )

        # Should run without errors using default seed data
        result = validate_domestic_hours_regression()

        # Verify we got real statistical output (not zeros or defaults)
        # With real data, we expect some non-trivial result
        assert result.slope != 0.0 or result.intercept != 0.0


class TestRegressionWithCustomData:
    """Test regression with custom input data."""

    def test_regression_with_explicit_positive_relationship(self) -> None:
        """Regression detects known positive relationship."""
        from babylon.domain.economics.validation.regression import run_linear_regression

        # Create data with explicit positive relationship: y = 2x + 1
        x_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_values = [3.0, 5.0, 7.0, 9.0, 11.0]  # y = 2x + 1

        result = run_linear_regression(x_values, y_values)

        assert result.slope == pytest.approx(2.0, abs=0.01)
        assert result.intercept == pytest.approx(1.0, abs=0.01)
        assert result.r_value == pytest.approx(1.0, abs=0.01)  # Perfect correlation

    def test_regression_with_negative_relationship(self) -> None:
        """Regression detects negative relationship."""
        from babylon.domain.economics.validation.regression import run_linear_regression

        # Create data with negative relationship: y = -2x + 10
        x_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_values = [8.0, 6.0, 4.0, 2.0, 0.0]  # y = -2x + 10

        result = run_linear_regression(x_values, y_values)

        assert result.slope == pytest.approx(-2.0, abs=0.01)
        assert result.slope < 0  # Negative slope

    def test_regression_requires_minimum_data_points(self) -> None:
        """Regression requires at least 2 data points."""
        from babylon.domain.economics.validation.regression import run_linear_regression

        with pytest.raises(ValueError, match="at least 2"):
            run_linear_regression([1.0], [2.0])
