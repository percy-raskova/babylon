"""Unit tests for God Mode Dashboard validators.

Tests H3 index and FIPS code validation utilities.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import pytest

from babylon.ui.dashboard.validators import (
    is_valid_fips_code,
    is_valid_h3_index,
    validate_fips_code,
    validate_h3_index,
)


class TestIsValidH3Index:
    """Tests for is_valid_h3_index() function."""

    def test_valid_lowercase_h3_index(self) -> None:
        """Valid lowercase H3 index should return True."""
        assert is_valid_h3_index("852a1072fffffff") is True

    def test_valid_uppercase_h3_index(self) -> None:
        """Valid uppercase H3 index should return True."""
        assert is_valid_h3_index("852A1072FFFFFFF") is True

    def test_valid_mixed_case_h3_index(self) -> None:
        """Valid mixed case H3 index should return True."""
        assert is_valid_h3_index("852a1072FFFFFFF") is True

    def test_too_short_h3_index(self) -> None:
        """H3 index with fewer than 15 chars should return False."""
        assert is_valid_h3_index("852a1072") is False
        assert is_valid_h3_index("") is False

    def test_too_long_h3_index(self) -> None:
        """H3 index with more than 15 chars should return False."""
        assert is_valid_h3_index("852a1072ffffffff") is False

    def test_non_hex_characters(self) -> None:
        """H3 index with non-hex characters should return False."""
        assert is_valid_h3_index("852a1072ggfffff") is False
        assert is_valid_h3_index("invalid-h3-idx!") is False

    def test_non_string_input(self) -> None:
        """Non-string input should return False."""
        assert is_valid_h3_index(None) is False  # type: ignore[arg-type]
        assert is_valid_h3_index(123456789012345) is False  # type: ignore[arg-type]
        assert is_valid_h3_index(["852a1072fffffff"]) is False  # type: ignore[arg-type]


class TestValidateH3Index:
    """Tests for validate_h3_index() function."""

    def test_valid_lowercase_returns_normalized(self) -> None:
        """Valid lowercase H3 index should return unchanged."""
        result = validate_h3_index("852a1072fffffff")
        assert result == "852a1072fffffff"

    def test_valid_uppercase_returns_lowercase(self) -> None:
        """Valid uppercase H3 index should return lowercase."""
        result = validate_h3_index("852A1072FFFFFFF")
        assert result == "852a1072fffffff"

    def test_valid_mixed_case_returns_lowercase(self) -> None:
        """Valid mixed case H3 index should return lowercase."""
        result = validate_h3_index("852a1072FFFFFFF")
        assert result == "852a1072fffffff"

    def test_invalid_h3_raises_value_error(self) -> None:
        """Invalid H3 index should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid H3 index"):
            validate_h3_index("invalid")

    def test_empty_string_raises_value_error(self) -> None:
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid H3 index"):
            validate_h3_index("")

    def test_too_short_raises_value_error(self) -> None:
        """Too short H3 index should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid H3 index"):
            validate_h3_index("852a107")


class TestIsValidFipsCode:
    """Tests for is_valid_fips_code() function."""

    def test_valid_fips_code(self) -> None:
        """Valid 5-digit FIPS code should return True."""
        assert is_valid_fips_code("26163") is True  # Wayne County, MI
        assert is_valid_fips_code("26125") is True  # Oakland County, MI
        assert is_valid_fips_code("00000") is True  # Edge case: all zeros

    def test_too_short_fips_code(self) -> None:
        """FIPS code with fewer than 5 digits should return False."""
        assert is_valid_fips_code("2616") is False
        assert is_valid_fips_code("26") is False
        assert is_valid_fips_code("") is False

    def test_too_long_fips_code(self) -> None:
        """FIPS code with more than 5 digits should return False."""
        assert is_valid_fips_code("261630") is False
        assert is_valid_fips_code("2616300") is False

    def test_non_numeric_fips_code(self) -> None:
        """FIPS code with non-numeric characters should return False."""
        assert is_valid_fips_code("2616A") is False
        assert is_valid_fips_code("abcde") is False
        assert is_valid_fips_code("26-63") is False

    def test_non_string_input(self) -> None:
        """Non-string input should return False."""
        assert is_valid_fips_code(None) is False  # type: ignore[arg-type]
        assert is_valid_fips_code(26163) is False  # type: ignore[arg-type]
        assert is_valid_fips_code(["26163"]) is False  # type: ignore[arg-type]


class TestValidateFipsCode:
    """Tests for validate_fips_code() function."""

    def test_valid_fips_returns_unchanged(self) -> None:
        """Valid FIPS code should return unchanged."""
        result = validate_fips_code("26163")
        assert result == "26163"

    def test_invalid_fips_raises_value_error(self) -> None:
        """Invalid FIPS code should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid FIPS code"):
            validate_fips_code("123")

    def test_empty_string_raises_value_error(self) -> None:
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid FIPS code"):
            validate_fips_code("")

    def test_non_numeric_raises_value_error(self) -> None:
        """Non-numeric FIPS code should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid FIPS code"):
            validate_fips_code("abcde")

    def test_too_long_raises_value_error(self) -> None:
        """Too long FIPS code should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid FIPS code"):
            validate_fips_code("261630")
