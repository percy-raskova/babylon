"""Unit tests for surplus distribution validation functions.

Feature: 024-capital-volume-iii (Phase 12)

Tests for three-tier validation: validate_rentier_share.
"""

from __future__ import annotations

from babylon.economics.distribution.validation import (
    validate_rentier_share,
)


class TestValidateRentierShare:
    """Tests for rentier share validation ranges."""

    def test_expected_range_passes(self) -> None:
        """Test values in [0.02, 0.15] return valid=True, message=None."""
        for value in [0.02, 0.05, 0.08, 0.12, 0.15]:
            valid, message = validate_rentier_share(value)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test values in [0.0, 0.02) return valid=True with warning."""
        valid, message = validate_rentier_share(0.01)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_expected(self) -> None:
        """Test values in (0.15, 0.30] return valid=True with warning."""
        valid, message = validate_rentier_share(0.25)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_warning_range_above_warning_below_fail(self) -> None:
        """Test values in (0.30, 1.0] return valid=True with warning."""
        valid, message = validate_rentier_share(0.50)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_below_zero(self) -> None:
        """Test values < 0 return valid=False."""
        valid, message = validate_rentier_share(-0.01)
        assert valid is False
        assert message is not None

    def test_fail_above_one(self) -> None:
        """Test values > 1.0 return valid=False."""
        valid, message = validate_rentier_share(1.1)
        assert valid is False
        assert message is not None

    def test_boundary_zero(self) -> None:
        """Test rentier_share = 0.0 is in warning range (below expected)."""
        valid, message = validate_rentier_share(0.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_one(self) -> None:
        """Test rentier_share = 1.0 is in warning range (above expected)."""
        valid, message = validate_rentier_share(1.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_boundary_expected_min(self) -> None:
        """Test rentier_share = 0.02 is within expected range."""
        valid, message = validate_rentier_share(0.02)
        assert valid is True
        assert message is None

    def test_boundary_expected_max(self) -> None:
        """Test rentier_share = 0.15 is within expected range."""
        valid, message = validate_rentier_share(0.15)
        assert valid is True
        assert message is None
