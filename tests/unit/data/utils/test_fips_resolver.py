"""Unit tests for FIPS code resolution utilities.

Tests the normalize_fips, extract_state_fips, and extract_county_fips_from_attrs
functions used by multiple data loaders.
"""

from __future__ import annotations

from babylon.data.utils.fips_resolver import (
    COUNTY_ONLY_FIELD_NAMES,
    FIPS_FIELD_NAMES,
    STATE_FIPS_FIELD_NAMES,
    extract_county_fips_from_attrs,
    extract_state_fips,
    normalize_fips,
)

# =============================================================================
# NORMALIZE FIPS TESTS
# =============================================================================


class TestNormalizeFips:
    """Tests for normalize_fips function."""

    def test_pads_4_digit_county_fips(self) -> None:
        """Should zero-pad 4-digit FIPS to 5 digits."""
        result = normalize_fips("6001", 5)
        assert result == "06001"

    def test_pads_3_digit_county_fips(self) -> None:
        """Should zero-pad 3-digit FIPS to 5 digits."""
        result = normalize_fips("001", 5)
        assert result == "00001"

    def test_handles_integer_input(self) -> None:
        """Should handle integer FIPS values."""
        result = normalize_fips(6001, 5)
        assert result == "06001"

    def test_single_digit_state_fips(self) -> None:
        """Should zero-pad single-digit state FIPS."""
        result = normalize_fips(6, 2)
        assert result == "06"

    def test_returns_none_for_none(self) -> None:
        """Should return None for None input."""
        result = normalize_fips(None, 5)
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Should return None for empty string."""
        result = normalize_fips("", 5)
        assert result is None

    def test_returns_none_for_nan_string(self) -> None:
        """Should return None for 'nan' string."""
        result = normalize_fips("nan", 5)
        assert result is None

    def test_returns_none_for_none_string(self) -> None:
        """Should return None for 'none' string."""
        result = normalize_fips("None", 5)
        assert result is None

    def test_returns_none_for_null_string(self) -> None:
        """Should return None for 'null' string."""
        result = normalize_fips("null", 5)
        assert result is None

    def test_truncates_long_fips(self) -> None:
        """Should truncate FIPS longer than expected length."""
        result = normalize_fips("060010123", 5)
        assert result == "06001"

    def test_handles_whitespace(self) -> None:
        """Should strip leading/trailing whitespace."""
        result = normalize_fips(" 6001 ", 5)
        assert result == "06001"

    def test_min_length_rejects_short_input(self) -> None:
        """Should return None when input is below min_length."""
        result = normalize_fips("06", 5, min_length=4)
        assert result is None

    def test_min_length_accepts_valid_input(self) -> None:
        """Should accept input at or above min_length."""
        result = normalize_fips("6001", 5, min_length=4)
        assert result == "06001"

    def test_min_length_accepts_at_boundary(self) -> None:
        """Should accept input exactly at min_length."""
        result = normalize_fips("6001", 5, min_length=4)
        assert result == "06001"

    def test_exact_length_no_padding(self) -> None:
        """Should not pad when input is already expected length."""
        result = normalize_fips("06001", 5)
        assert result == "06001"


# =============================================================================
# EXTRACT STATE FIPS TESTS
# =============================================================================


class TestExtractStateFips:
    """Tests for extract_state_fips function."""

    def test_extracts_from_5_digit_fips(self) -> None:
        """Should extract 2-digit state from 5-digit county FIPS."""
        result = extract_state_fips("06001")
        assert result == "06"

    def test_extracts_from_4_digit_fips(self) -> None:
        """Should handle 4-digit county FIPS (missing leading zero)."""
        result = extract_state_fips("6001")
        assert result == "06"

    def test_returns_none_for_empty_string(self) -> None:
        """Should return None for empty string."""
        result = extract_state_fips("")
        assert result is None

    def test_returns_none_for_short_fips(self) -> None:
        """Should return None for FIPS shorter than 4 digits."""
        result = extract_state_fips("06")
        assert result is None

    def test_handles_longer_fips(self) -> None:
        """Should handle FIPS longer than 5 digits."""
        result = extract_state_fips("0600101")
        assert result == "06"


# =============================================================================
# EXTRACT COUNTY FIPS FROM ATTRS TESTS
# =============================================================================


class TestExtractCountyFipsFromAttrs:
    """Tests for extract_county_fips_from_attrs function."""

    def test_extracts_from_countyfips(self) -> None:
        """Should extract FIPS from COUNTYFIPS field."""
        attrs = {"COUNTYFIPS": "06001"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_extracts_from_cnty_fips(self) -> None:
        """Should extract FIPS from CNTY_FIPS field."""
        attrs = {"CNTY_FIPS": "36061"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "36061"

    def test_extracts_from_fips(self) -> None:
        """Should extract FIPS from FIPS field."""
        attrs = {"FIPS": "48201"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "48201"

    def test_extracts_from_county_fips(self) -> None:
        """Should extract FIPS from COUNTY_FIPS field."""
        attrs = {"COUNTY_FIPS": "12086"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "12086"

    def test_extracts_from_county_fip(self) -> None:
        """Should extract FIPS from COUNTY_FIP field."""
        attrs = {"COUNTY_FIP": "17031"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "17031"

    def test_pads_4_digit_fips(self) -> None:
        """Should zero-pad 4-digit FIPS to 5 digits."""
        attrs = {"COUNTYFIPS": "6001"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_pads_integer_fips(self) -> None:
        """Should handle integer FIPS values."""
        attrs = {"COUNTYFIPS": 6001}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_truncates_long_fips(self) -> None:
        """Should truncate FIPS longer than 5 digits."""
        attrs = {"COUNTYFIPS": "0600101"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_returns_none_for_missing_fields(self) -> None:
        """Should return None when no FIPS field present."""
        attrs = {"NAME": "Test Location"}
        result = extract_county_fips_from_attrs(attrs)
        assert result is None

    def test_returns_none_for_short_fips(self) -> None:
        """Should return None for FIPS shorter than 4 digits."""
        attrs = {"COUNTYFIPS": "06"}
        result = extract_county_fips_from_attrs(attrs)
        assert result is None

    def test_constructs_from_state_and_county(self) -> None:
        """Should construct FIPS from STATE_FIPS and CNTY_FIPS_3."""
        attrs = {"STATE_FIPS": "06", "CNTY_FIPS_3": "001"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_constructs_from_statefp_and_countyfp(self) -> None:
        """Should construct FIPS from STATEFP and COUNTYFP."""
        attrs = {"STATEFP": "48", "COUNTYFP": "029"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "48029"

    def test_constructs_with_padding(self) -> None:
        """Should pad state and county when constructing."""
        attrs = {"STATE_FIPS": "6", "CNTY_FIPS_3": "1"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_custom_field_names(self) -> None:
        """Should use custom field names when provided."""
        attrs = {"CUSTOM_FIPS": "12345"}
        result = extract_county_fips_from_attrs(attrs, field_names=("CUSTOM_FIPS",))
        assert result == "12345"

    def test_disables_construction(self) -> None:
        """Should not construct when try_construct=False."""
        attrs = {"STATE_FIPS": "06", "CNTY_FIPS_3": "001"}
        result = extract_county_fips_from_attrs(attrs, try_construct=False)
        assert result is None

    def test_prefers_direct_field_over_construction(self) -> None:
        """Should prefer direct FIPS field over construction."""
        attrs = {
            "COUNTYFIPS": "36061",
            "STATE_FIPS": "06",
            "CNTY_FIPS_3": "001",
        }
        result = extract_county_fips_from_attrs(attrs)
        assert result == "36061"  # Direct field, not 06001

    def test_handles_whitespace(self) -> None:
        """Should strip whitespace from FIPS values."""
        attrs = {"COUNTYFIPS": " 06001 "}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"


# =============================================================================
# FIELD NAME CONFIGURATION TESTS
# =============================================================================


class TestFieldNameConfiguration:
    """Tests for field name constants."""

    def test_fips_field_names_contains_common_fields(self) -> None:
        """FIPS_FIELD_NAMES should contain common field names."""
        assert "COUNTYFIPS" in FIPS_FIELD_NAMES
        assert "CNTY_FIPS" in FIPS_FIELD_NAMES
        assert "FIPS" in FIPS_FIELD_NAMES

    def test_state_fips_field_names_contains_common_fields(self) -> None:
        """STATE_FIPS_FIELD_NAMES should contain common field names."""
        assert "STATE_FIPS" in STATE_FIPS_FIELD_NAMES
        assert "STATEFP" in STATE_FIPS_FIELD_NAMES

    def test_county_only_field_names_contains_common_fields(self) -> None:
        """COUNTY_ONLY_FIELD_NAMES should contain common field names."""
        assert "CNTY_FIPS_3" in COUNTY_ONLY_FIELD_NAMES
        assert "COUNTYFP" in COUNTY_ONLY_FIELD_NAMES
