"""Unit tests for Census CSV parser.

Tests parsing logic for ACS Census data files.
"""

from __future__ import annotations

import pandas as pd
import pytest

from babylon.data.census.parser import (
    AIAN_VARIANT,
    CENSUS_NULL_VALUES,
    MAIN_VARIANT,
    SUPPORTED_VARIANTS,
    extract_cbsa_code,
    parse_column_label,
    safe_float,
    safe_int,
)


@pytest.mark.unit
class TestExtractCBSACode:
    """Tests for CBSA code extraction from GEO_ID."""

    def test_extracts_valid_cbsa(self) -> None:
        """Extracts 5-digit CBSA from standard GEO_ID."""
        geo_id = "310M600US10180"
        cbsa = extract_cbsa_code(geo_id)
        assert cbsa == "10180"

    def test_extracts_cbsa_from_different_pattern(self) -> None:
        """Handles variations in GEO_ID format."""
        geo_id = "310M200US35620"
        cbsa = extract_cbsa_code(geo_id)
        assert cbsa == "35620"

    def test_returns_none_for_invalid_geo_id(self) -> None:
        """Returns None if pattern doesn't match."""
        geo_id = "0400000US06"  # State-level, not CBSA
        cbsa = extract_cbsa_code(geo_id)
        assert cbsa is None

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None for empty string."""
        cbsa = extract_cbsa_code("")
        assert cbsa is None


@pytest.mark.unit
class TestParseColumnLabel:
    """Tests for Census column label parsing."""

    def test_parse_simple_total(self) -> None:
        """Parses simple Total label."""
        label, category = parse_column_label("Estimate!!Total:")
        assert label == "Total"
        assert category is None  # Total is not a category

    def test_parse_nested_label(self) -> None:
        """Parses nested label with category."""
        label, category = parse_column_label("Estimate!!Total:!!Less than $10,000")
        assert label == "Less than $10,000"
        assert category == "Less than $10,000"

    def test_parse_gender_breakdown(self) -> None:
        """Parses gender breakdown labels."""
        label, category = parse_column_label("Estimate!!Male:!!Management, business, science")
        assert "Management" in label
        assert category == "Male"

    def test_handles_empty_string(self) -> None:
        """Handles empty string input."""
        label, category = parse_column_label("")
        assert label == ""
        assert category is None

    def test_handles_none_input(self) -> None:
        """Handles None input."""
        label, category = parse_column_label(None)  # type: ignore[arg-type]
        assert label == ""
        assert category is None

    def test_strips_trailing_colons(self) -> None:
        """Strips trailing colons from labels."""
        label, category = parse_column_label("Estimate!!Total:!!Some Category:")
        assert not label.endswith(":")


@pytest.mark.unit
class TestSafeInt:
    """Tests for safe integer conversion."""

    def test_converts_valid_integer(self) -> None:
        """Converts valid integer values."""
        assert safe_int("12345") == 12345
        assert safe_int(12345) == 12345

    def test_converts_float_to_int(self) -> None:
        """Converts float strings to integers."""
        assert safe_int("12345.67") == 12345

    def test_returns_none_for_null_values(self) -> None:
        """Returns None for Census NULL indicators."""
        for null_val in ["N", "-", "(X)", "**", "***", "null", ""]:
            assert safe_int(null_val) is None

    def test_returns_none_for_nan(self) -> None:
        """Returns None for pandas NaN."""
        assert safe_int(pd.NA) is None
        assert safe_int(float("nan")) is None

    def test_returns_none_for_invalid_string(self) -> None:
        """Returns None for non-numeric strings."""
        assert safe_int("invalid") is None


@pytest.mark.unit
class TestSafeFloat:
    """Tests for safe float conversion."""

    def test_converts_valid_float(self) -> None:
        """Converts valid float values."""
        assert safe_float("123.45") == 123.45
        assert safe_float(123.45) == 123.45

    def test_converts_integer_to_float(self) -> None:
        """Converts integers to floats."""
        result = safe_float("12345")
        assert result == 12345.0
        assert isinstance(result, float)

    def test_returns_none_for_null_values(self) -> None:
        """Returns None for Census NULL indicators."""
        for null_val in ["N", "-", "(X)", "**", "***", "null", ""]:
            assert safe_float(null_val) is None

    def test_returns_none_for_nan(self) -> None:
        """Returns None for pandas NaN."""
        assert safe_float(pd.NA) is None
        assert safe_float(float("nan")) is None

    def test_returns_none_for_invalid_string(self) -> None:
        """Returns None for non-numeric strings."""
        assert safe_float("invalid") is None


@pytest.mark.unit
class TestConstants:
    """Tests for module constants."""

    def test_census_null_values_set(self) -> None:
        """CENSUS_NULL_VALUES is a set with expected entries."""
        assert isinstance(CENSUS_NULL_VALUES, set)
        assert "N" in CENSUS_NULL_VALUES
        assert "-" in CENSUS_NULL_VALUES
        assert "(X)" in CENSUS_NULL_VALUES

    def test_supported_variants(self) -> None:
        """SUPPORTED_VARIANTS includes expected variants."""
        assert MAIN_VARIANT in SUPPORTED_VARIANTS
        assert AIAN_VARIANT in SUPPORTED_VARIANTS
        assert "ACSDT5Y2021" in SUPPORTED_VARIANTS
