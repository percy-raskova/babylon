"""Unit tests for Gamma Visibility Tensor validation functions.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

Tests for three-tier validation: validate_gamma_iii, validate_gamma_import,
validate_gamma_basket.
"""

from __future__ import annotations

from babylon.economics.gamma.validation import (
    validate_gamma_basket,
    validate_gamma_iii,
    validate_gamma_import,
)


class TestValidateGammaIII:
    """Tests for gamma_III validation ranges."""

    def test_expected_range_passes(self) -> None:
        """Test values in [0.20, 0.40] return valid=True, message=None."""
        for value in [0.20, 0.25, 0.30, 0.333, 0.40]:
            valid, message = validate_gamma_iii(value)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test values in [0.10, 0.20) return valid=True with warning."""
        valid, message = validate_gamma_iii(0.15)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_expected(self) -> None:
        """Test values in (0.40, 0.50] return valid=True with warning."""
        valid, message = validate_gamma_iii(0.45)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_below_zero(self) -> None:
        """Test values < 0 return valid=False."""
        valid, message = validate_gamma_iii(-0.1)
        assert valid is False
        assert message is not None

    def test_fail_above_one(self) -> None:
        """Test values > 1.0 return valid=False."""
        valid, message = validate_gamma_iii(1.1)
        assert valid is False
        assert message is not None

    def test_boundary_zero(self) -> None:
        """Test gamma_III = 0.0 is in warning range (below expected)."""
        valid, message = validate_gamma_iii(0.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_one(self) -> None:
        """Test gamma_III = 1.0 is in warning range (above expected)."""
        valid, message = validate_gamma_iii(1.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message


class TestValidateGammaImport:
    """Tests for gamma_import validation ranges."""

    def test_expected_range_passes(self) -> None:
        """Test values in [0.40, 0.70] return valid=True, message=None."""
        for value in [0.40, 0.50, 0.60, 0.65, 0.70]:
            valid, message = validate_gamma_import(value)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test values in (0.0, 0.40) return valid=True with warning."""
        valid, message = validate_gamma_import(0.35)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_expected(self) -> None:
        """Test values in (0.70, 0.80] return valid=True with warning."""
        valid, message = validate_gamma_import(0.75)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_zero(self) -> None:
        """Test gamma_import = 0.0 is invalid (must be > 0)."""
        valid, message = validate_gamma_import(0.0)
        assert valid is False
        assert message is not None

    def test_fail_negative(self) -> None:
        """Test negative values return valid=False."""
        valid, message = validate_gamma_import(-0.1)
        assert valid is False
        assert message is not None

    def test_fail_above_one(self) -> None:
        """Test values > 1.0 return valid=False."""
        valid, message = validate_gamma_import(1.1)
        assert valid is False
        assert message is not None


class TestValidateGammaBasket:
    """Tests for gamma_basket validation ranges."""

    def test_expected_range_passes(self) -> None:
        """Test values in [0.60, 0.85] return valid=True, message=None."""
        for value in [0.60, 0.68, 0.74, 0.80, 0.85]:
            valid, message = validate_gamma_basket(value)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test values in (0.0, 0.60) return valid=True with warning."""
        valid, message = validate_gamma_basket(0.50)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_expected(self) -> None:
        """Test values in (0.85, 0.95] return valid=True with warning."""
        valid, message = validate_gamma_basket(0.90)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_zero(self) -> None:
        """Test gamma_basket = 0.0 is invalid (must be > 0)."""
        valid, message = validate_gamma_basket(0.0)
        assert valid is False
        assert message is not None

    def test_fail_negative(self) -> None:
        """Test negative values return valid=False."""
        valid, message = validate_gamma_basket(-0.1)
        assert valid is False
        assert message is not None

    def test_fail_above_one(self) -> None:
        """Test values > 1.0 return valid=False."""
        valid, message = validate_gamma_basket(1.1)
        assert valid is False
        assert message is not None
