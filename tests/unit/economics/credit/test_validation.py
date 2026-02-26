"""Unit tests for credit and financialization validation functions.

Feature: 024-capital-volume-iii (Phase 12)

Tests for three-tier validation: validate_financialization_index,
validate_interest_burden_ratio.
"""

from __future__ import annotations

from babylon.economics.credit.validation import (
    validate_financialization_index,
    validate_interest_burden_ratio,
)


class TestValidateFinancializationIndex:
    """Tests for financialization index validation ranges."""

    def test_expected_range_passes(self) -> None:
        """Test values in [1.5, 3.0] return valid=True, message=None."""
        for value in [1.5, 2.0, 2.5, 2.75, 3.0]:
            valid, message = validate_financialization_index(value)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test values in [0.5, 1.5) return valid=True with warning."""
        valid, message = validate_financialization_index(1.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_expected(self) -> None:
        """Test values in (3.0, 5.0] return valid=True with warning."""
        valid, message = validate_financialization_index(4.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_warning_below_fail(self) -> None:
        """Test values in (5.0, 20.0] return valid=True with warning."""
        valid, message = validate_financialization_index(10.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_below_zero(self) -> None:
        """Test values < 0 return valid=False."""
        valid, message = validate_financialization_index(-0.1)
        assert valid is False
        assert message is not None

    def test_fail_above_max(self) -> None:
        """Test values > 20.0 return valid=False."""
        valid, message = validate_financialization_index(20.1)
        assert valid is False
        assert message is not None

    def test_boundary_zero(self) -> None:
        """Test financialization_index = 0.0 is in warning range (below expected)."""
        valid, message = validate_financialization_index(0.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_fail_max(self) -> None:
        """Test financialization_index = 20.0 is in warning range (above expected)."""
        valid, message = validate_financialization_index(20.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_expected_min(self) -> None:
        """Test financialization_index = 1.5 is within expected range."""
        valid, message = validate_financialization_index(1.5)
        assert valid is True
        assert message is None

    def test_boundary_expected_max(self) -> None:
        """Test financialization_index = 3.0 is within expected range."""
        valid, message = validate_financialization_index(3.0)
        assert valid is True
        assert message is None


class TestValidateInterestBurdenRatio:
    """Tests for interest burden ratio validation ranges."""

    def test_expected_range_passes(self) -> None:
        """Test values in [0.05, 0.35] return valid=True, message=None."""
        for value in [0.05, 0.10, 0.20, 0.30, 0.35]:
            valid, message = validate_interest_burden_ratio(value)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test values in [0.0, 0.05) return valid=True with warning."""
        valid, message = validate_interest_burden_ratio(0.02)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_expected(self) -> None:
        """Test values in (0.35, 0.60] return valid=True with warning."""
        valid, message = validate_interest_burden_ratio(0.50)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_warning_below_fail(self) -> None:
        """Test values in (0.60, 1.0] return valid=True with warning."""
        valid, message = validate_interest_burden_ratio(0.80)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_below_zero(self) -> None:
        """Test values < 0 return valid=False."""
        valid, message = validate_interest_burden_ratio(-0.01)
        assert valid is False
        assert message is not None

    def test_fail_above_one(self) -> None:
        """Test values > 1.0 return valid=False."""
        valid, message = validate_interest_burden_ratio(1.1)
        assert valid is False
        assert message is not None

    def test_boundary_zero(self) -> None:
        """Test interest_burden_ratio = 0.0 is in warning range (below expected)."""
        valid, message = validate_interest_burden_ratio(0.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_one(self) -> None:
        """Test interest_burden_ratio = 1.0 is in warning range (above expected)."""
        valid, message = validate_interest_burden_ratio(1.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_expected_min(self) -> None:
        """Test interest_burden_ratio = 0.05 is within expected range."""
        valid, message = validate_interest_burden_ratio(0.05)
        assert valid is True
        assert message is None

    def test_boundary_expected_max(self) -> None:
        """Test interest_burden_ratio = 0.35 is within expected range."""
        valid, message = validate_interest_burden_ratio(0.35)
        assert valid is True
        assert message is None
