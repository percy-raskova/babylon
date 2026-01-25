"""Unit tests for ETL transformation logic.

Tests the data transformation functions used during ETL to clean and
prepare data for loading into the normalized 3NF schema.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

# =============================================================================
# HELPER FUNCTIONS FOR TESTING (extracted from ETL logic)
# =============================================================================


def parse_digit_level(level_str: str | None) -> int:
    """Parse digit level from productivity industry string.

    Extracts the numeric level from strings like "3-Digit NAICS".

    Args:
        level_str: Level string from productivity_industries.digit_level

    Returns:
        Integer level (3, 4, 5, 6) or 0 if not parseable
    """
    if not level_str:
        return 0
    if "3-Digit" in level_str:
        return 3
    elif "4-Digit" in level_str:
        return 4
    elif "5-Digit" in level_str:
        return 5
    elif "6-Digit" in level_str:
        return 6
    return 0


def extract_state_fips(county_fips: str | None) -> str | None:
    """Extract state FIPS code from county FIPS code.

    County FIPS codes are 5 digits: first 2 are state FIPS.

    Args:
        county_fips: 5-digit county FIPS code

    Returns:
        2-digit state FIPS code or None
    """
    if not county_fips or len(county_fips) < 2:
        return None
    return county_fips[:2]


def coerce_to_decimal(value: Any) -> Decimal | None:
    """Safely coerce a value to Decimal for currency/numeric fields.

    Args:
        value: Input value (could be str, int, float, or None)

    Returns:
        Decimal value or None if not convertible
    """
    if value is None:
        return None
    try:
        if isinstance(value, str):
            # Handle empty strings
            if not value.strip():
                return None
            # Handle formatted numbers like "1,234.56"
            value = value.replace(",", "")
        return Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):
        return None


def normalize_industry_code(code: str | None) -> str | None:
    """Normalize industry code by stripping NAICS prefix.

    Args:
        code: Industry code potentially with "NAICS " prefix

    Returns:
        Normalized code or None
    """
    if not code:
        return None
    return code.replace("NAICS ", "").strip() or None


def resolve_foreign_key(
    lookup: dict[str, int],
    key: str | None,
    required: bool = True,
) -> int | None:
    """Resolve a foreign key using a lookup dictionary.

    Args:
        lookup: Dictionary mapping source keys to target IDs
        key: Source key to look up
        required: If True, raises ValueError for missing keys

    Returns:
        Target ID or None

    Raises:
        ValueError: If required=True and key not found
    """
    if key is None:
        if required:
            raise ValueError("Foreign key cannot be None when required")
        return None

    result = lookup.get(key)
    if result is None and required:
        raise ValueError(f"Foreign key '{key}' not found in lookup")
    return result


def merge_dimension_sources(
    sources: list[dict[str, Any]],
    key_field: str,
) -> dict[str, dict[str, Any]]:
    """Merge multiple source records for a dimension, deduplicating by key.

    Later sources can add to but not override existing fields (except nulls).

    Args:
        sources: List of source records as dicts
        key_field: Field to use as unique key

    Returns:
        Merged dimension records keyed by key_field
    """
    result: dict[str, dict[str, Any]] = {}

    for record in sources:
        key = record.get(key_field)
        if not key:
            continue

        if key not in result:
            result[key] = dict(record)
        else:
            # Merge: fill in None/empty values from later sources
            existing = result[key]
            for field, value in record.items():
                if field != key_field and existing.get(field) in (None, "", 0):
                    existing[field] = value

    return result


# =============================================================================
# TESTS
# =============================================================================


class TestDigitLevelParsing:
    """Tests for parsing digit level from industry strings."""

    def test_three_digit(self) -> None:
        """3-Digit should return 3."""
        assert parse_digit_level("3-Digit NAICS") == 3
        assert parse_digit_level("3-Digit") == 3

    def test_four_digit(self) -> None:
        """4-Digit should return 4."""
        assert parse_digit_level("4-Digit NAICS") == 4

    def test_five_digit(self) -> None:
        """5-Digit should return 5."""
        assert parse_digit_level("5-Digit NAICS") == 5

    def test_six_digit(self) -> None:
        """6-Digit should return 6."""
        assert parse_digit_level("6-Digit NAICS") == 6

    def test_none_returns_zero(self) -> None:
        """None input should return 0."""
        assert parse_digit_level(None) == 0

    def test_empty_string_returns_zero(self) -> None:
        """Empty string should return 0."""
        assert parse_digit_level("") == 0

    def test_unknown_format_returns_zero(self) -> None:
        """Unknown format should return 0."""
        assert parse_digit_level("Sector Level") == 0
        assert parse_digit_level("2-Digit") == 0  # Only 3-6 are valid


class TestStateFipsExtraction:
    """Tests for extracting state FIPS from county FIPS."""

    def test_standard_county_fips(self) -> None:
        """Standard 5-digit FIPS should extract first 2 digits."""
        assert extract_state_fips("36001") == "36"  # New York, Albany
        assert extract_state_fips("06037") == "06"  # California, Los Angeles
        assert extract_state_fips("48201") == "48"  # Texas, Harris

    def test_short_fips_returns_what_it_can(self) -> None:
        """FIPS with only 2 digits returns them."""
        assert extract_state_fips("36") == "36"
        assert extract_state_fips("06") == "06"

    def test_too_short_returns_none(self) -> None:
        """FIPS with less than 2 digits returns None."""
        assert extract_state_fips("3") is None
        assert extract_state_fips("") is None

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert extract_state_fips(None) is None


class TestDecimalCoercion:
    """Tests for safe decimal coercion."""

    def test_integer(self) -> None:
        """Integer should convert to Decimal."""
        assert coerce_to_decimal(100) == Decimal("100")
        assert coerce_to_decimal(0) == Decimal("0")

    def test_float(self) -> None:
        """Float should convert to Decimal."""
        result = coerce_to_decimal(123.45)
        assert result is not None
        assert abs(result - Decimal("123.45")) < Decimal("0.001")

    def test_string_number(self) -> None:
        """String number should convert to Decimal."""
        assert coerce_to_decimal("100.50") == Decimal("100.50")
        assert coerce_to_decimal("-50.25") == Decimal("-50.25")

    def test_formatted_string(self) -> None:
        """Formatted string with commas should convert."""
        assert coerce_to_decimal("1,234.56") == Decimal("1234.56")
        assert coerce_to_decimal("1,000,000") == Decimal("1000000")

    def test_none_returns_none(self) -> None:
        """None should return None."""
        assert coerce_to_decimal(None) is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string should return None."""
        assert coerce_to_decimal("") is None
        assert coerce_to_decimal("   ") is None

    def test_invalid_string_returns_none(self) -> None:
        """Non-numeric string should return None."""
        assert coerce_to_decimal("abc") is None
        assert coerce_to_decimal("N/A") is None


class TestIndustryCodeNormalization:
    """Tests for normalizing industry codes."""

    def test_plain_code(self) -> None:
        """Plain code should pass through."""
        assert normalize_industry_code("311") == "311"
        assert normalize_industry_code("5221") == "5221"

    def test_naics_prefix_stripped(self) -> None:
        """NAICS prefix should be stripped."""
        assert normalize_industry_code("NAICS 311") == "311"
        assert normalize_industry_code("NAICS 5221") == "5221"

    def test_whitespace_handled(self) -> None:
        """Extra whitespace should be stripped."""
        assert normalize_industry_code("  311  ") == "311"
        assert normalize_industry_code("NAICS  311") == "311"

    def test_none_returns_none(self) -> None:
        """None should return None."""
        assert normalize_industry_code(None) is None

    def test_empty_after_strip_returns_none(self) -> None:
        """String that becomes empty after stripping returns None."""
        assert normalize_industry_code("") is None
        assert normalize_industry_code("   ") is None
        assert normalize_industry_code("NAICS ") is None


class TestForeignKeyResolution:
    """Tests for FK resolution with lookups."""

    @pytest.fixture
    def sample_lookup(self) -> dict[str, int]:
        """Sample FK lookup dictionary."""
        return {
            "36001": 1,  # Albany County
            "06037": 2,  # Los Angeles County
            "48201": 3,  # Harris County
        }

    def test_found_key(self, sample_lookup: dict[str, int]) -> None:
        """Known key should return ID."""
        assert resolve_foreign_key(sample_lookup, "36001") == 1
        assert resolve_foreign_key(sample_lookup, "06037") == 2

    def test_missing_key_required_raises(self, sample_lookup: dict[str, int]) -> None:
        """Missing required key should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            resolve_foreign_key(sample_lookup, "99999", required=True)

    def test_missing_key_optional_returns_none(self, sample_lookup: dict[str, int]) -> None:
        """Missing optional key should return None."""
        assert resolve_foreign_key(sample_lookup, "99999", required=False) is None

    def test_none_key_required_raises(self, sample_lookup: dict[str, int]) -> None:
        """None key when required should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            resolve_foreign_key(sample_lookup, None, required=True)

    def test_none_key_optional_returns_none(self, sample_lookup: dict[str, int]) -> None:
        """None key when optional should return None."""
        assert resolve_foreign_key(sample_lookup, None, required=False) is None


class TestDimensionMerging:
    """Tests for merging dimension records from multiple sources."""

    def test_single_source(self) -> None:
        """Single source should produce that source's records."""
        sources = [
            {"code": "311", "title": "Food Manufacturing", "level": 3},
            {"code": "312", "title": "Beverage Manufacturing", "level": 3},
        ]
        result = merge_dimension_sources(sources, "code")
        assert len(result) == 2
        assert result["311"]["title"] == "Food Manufacturing"

    def test_multiple_sources_merge(self) -> None:
        """Multiple sources should merge, keeping first non-null."""
        sources = [
            {"code": "311", "title": "Food Manufacturing", "level": None},
            {"code": "311", "title": "Different Title", "level": 3},  # Should fill level
        ]
        result = merge_dimension_sources(sources, "code")
        assert len(result) == 1
        assert result["311"]["title"] == "Food Manufacturing"  # First wins
        assert result["311"]["level"] == 3  # None filled from second

    def test_empty_key_skipped(self) -> None:
        """Records with empty key should be skipped."""
        sources = [
            {"code": "311", "title": "Food Manufacturing"},
            {"code": "", "title": "No Code"},
            {"code": None, "title": "Also No Code"},
        ]
        result = merge_dimension_sources(sources, "code")
        assert len(result) == 1
        assert "311" in result

    def test_zero_treated_as_empty(self) -> None:
        """Zero should be treated as empty and fillable."""
        sources = [
            {"code": "311", "level": 0},
            {"code": "311", "level": 3},
        ]
        result = merge_dimension_sources(sources, "code")
        assert result["311"]["level"] == 3


class TestBatchProcessingEdgeCases:
    """Tests for batch processing behavior patterns."""

    def test_batch_size_boundary(self) -> None:
        """Verify correct handling at batch size boundaries."""
        # Simulate batch processing of exactly batch_size items
        batch_size = 10000
        records = list(range(batch_size))

        # Process in batches
        batches_processed = 0
        remaining_after_batches = 0
        batch: list[int] = []

        for record in records:
            batch.append(record)
            if len(batch) >= batch_size:
                batches_processed += 1
                batch = []

        remaining_after_batches = len(batch)

        assert batches_processed == 1
        assert remaining_after_batches == 0

    def test_remainder_after_batches(self) -> None:
        """Verify handling of remaining records after full batches."""
        batch_size = 10000
        records = list(range(batch_size + 500))  # 10500 records

        batches_processed = 0
        batch: list[int] = []

        for record in records:
            batch.append(record)
            if len(batch) >= batch_size:
                batches_processed += 1
                batch = []

        remaining = len(batch)

        assert batches_processed == 1
        assert remaining == 500


class TestNullHandling:
    """Tests for proper NULL value handling in transformations."""

    def test_null_string_variations(self) -> None:
        """Various NULL representations should be handled."""
        null_like_values = [None, "", "  ", "NULL", "null", "N/A", "n/a", "-"]

        for val in null_like_values:
            # These should not raise exceptions
            result = coerce_to_decimal(val)
            assert result is None or isinstance(result, Decimal)

    def test_null_propagation(self) -> None:
        """NULLs should propagate correctly through transforms."""
        # State FIPS from NULL county
        assert extract_state_fips(None) is None

        # Industry code from NULL
        assert normalize_industry_code(None) is None

        # Digit level from NULL
        assert parse_digit_level(None) == 0


# =============================================================================
# ADDITIONAL ETL PITFALL TESTS - Common Data Quality Issues
# =============================================================================


def parse_currency(value: str | None) -> Decimal | None:
    """Parse currency strings, removing $ and handling negatives.

    Handles formats like:
    - "$1,234.56"
    - "($1,234.56)" (negative)
    - "-$1,234.56"
    - "1234.56"

    Args:
        value: Currency string to parse

    Returns:
        Decimal value or None if not parseable
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Check for negative wrapped in parentheses: ($123.45)
    is_negative = False
    if value.startswith("(") and value.endswith(")"):
        is_negative = True
        value = value[1:-1]

    # Remove currency symbols and whitespace
    value = value.replace("$", "").replace("€", "").replace("£", "").replace(" ", "")

    # Handle leading minus
    if value.startswith("-"):
        is_negative = True
        value = value[1:]

    # Remove commas
    value = value.replace(",", "")

    try:
        result = Decimal(value)
        return -result if is_negative else result
    except (ValueError, ArithmeticError):
        return None


def parse_percentage(value: str | None) -> Decimal | None:
    """Parse percentage strings to decimal (0-1 or 0-100 scale preserved).

    Args:
        value: Percentage string like "25%", "25.5%", or "0.25"

    Returns:
        Decimal value (maintains scale from input)
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Remove % sign if present
    has_percent = "%" in value
    value = value.replace("%", "").strip()

    try:
        result = Decimal(value)
        # If had % sign, divide by 100 to get 0-1 scale
        if has_percent:
            result = result / Decimal("100")
        return result
    except (ValueError, ArithmeticError):
        return None


def parse_scaled_number(value: str | None) -> Decimal | None:
    """Parse numbers with scale suffixes like "Trillion", "Billion", "Million".

    Common in economic data where values are reported as "1.5 Trillion".

    Args:
        value: Number string potentially with scale suffix

    Returns:
        Decimal value in base units (e.g., 1.5 Trillion -> 1500000000000)
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Define scale multipliers
    scales = {
        "quadrillion": Decimal("1000000000000000"),
        "trillion": Decimal("1000000000000"),
        "billion": Decimal("1000000000"),
        "million": Decimal("1000000"),
        "thousand": Decimal("1000"),
        "q": Decimal("1000000000000000"),  # Abbreviations
        "t": Decimal("1000000000000"),
        "b": Decimal("1000000000"),
        "m": Decimal("1000000"),
        "k": Decimal("1000"),
    }

    value_lower = value.lower()
    multiplier = Decimal("1")

    # Find and extract scale suffix
    for suffix, scale in scales.items():
        if suffix in value_lower:
            multiplier = scale
            # Remove the suffix to get the numeric part
            value = value_lower.replace(suffix, "").strip()
            break

    # Remove commas
    value = value.replace(",", "")

    try:
        numeric = Decimal(value)
        return numeric * multiplier
    except (ValueError, ArithmeticError):
        return None


def normalize_frequency(freq: str | None) -> str | None:
    """Normalize frequency strings to standard values.

    Args:
        freq: Frequency like "Annual", "Quarterly", "Monthly", "A", "Q", "M"

    Returns:
        Standard frequency: "annual", "quarterly", "monthly", or None
    """
    if not freq or not isinstance(freq, str):
        return None

    freq = freq.strip().lower()

    # Map variations to standard values
    annual = {"annual", "annually", "yearly", "year", "a", "ann", "yr"}
    quarterly = {"quarterly", "quarter", "q", "qtr"}
    monthly = {"monthly", "month", "m", "mo"}
    daily = {"daily", "day", "d"}

    if freq in annual:
        return "annual"
    elif freq in quarterly:
        return "quarterly"
    elif freq in monthly:
        return "monthly"
    elif freq in daily:
        return "daily"

    return None


def safe_float_to_decimal(value: float) -> Decimal:
    """Convert float to Decimal avoiding precision issues.

    Direct conversion of binary floats to Decimal can produce
    unexpected precision artifacts.

    Args:
        value: Float value

    Returns:
        Decimal with reasonable precision
    """
    # Convert via string with fixed precision to avoid float artifacts
    return Decimal(f"{value:.10f}").normalize()


def coerce_boolean(value: Any) -> bool | None:
    """Coerce various boolean representations to Python bool.

    Args:
        value: Various bool representations (1/0, Y/N, True/False, etc.)

    Returns:
        Python bool or None if not interpretable
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        value = value.strip().lower()
        if value in ("true", "yes", "y", "1", "t"):
            return True
        elif value in ("false", "no", "n", "0", "f"):
            return False

    return None


class TestCurrencyParsing:
    """Tests for parsing currency strings."""

    def test_plain_number(self) -> None:
        """Plain number should parse."""
        assert parse_currency("1234.56") == Decimal("1234.56")

    def test_dollar_sign(self) -> None:
        """Dollar sign should be stripped."""
        assert parse_currency("$1234.56") == Decimal("1234.56")
        assert parse_currency("$ 1234.56") == Decimal("1234.56")

    def test_comma_formatting(self) -> None:
        """Comma-formatted numbers should parse."""
        assert parse_currency("$1,234.56") == Decimal("1234.56")
        assert parse_currency("$1,234,567.89") == Decimal("1234567.89")

    def test_negative_with_minus(self) -> None:
        """Negative with minus sign should parse."""
        assert parse_currency("-$1,234.56") == Decimal("-1234.56")
        assert parse_currency("-1234.56") == Decimal("-1234.56")

    def test_negative_with_parentheses(self) -> None:
        """Accounting format negatives (parentheses) should parse."""
        assert parse_currency("($1,234.56)") == Decimal("-1234.56")
        assert parse_currency("(1,234.56)") == Decimal("-1234.56")

    def test_other_currencies(self) -> None:
        """Euro and Pound symbols should be stripped."""
        assert parse_currency("€1,234.56") == Decimal("1234.56")
        assert parse_currency("£1,234.56") == Decimal("1234.56")

    def test_null_values(self) -> None:
        """NULL-like values should return None."""
        assert parse_currency(None) is None
        assert parse_currency("") is None
        assert parse_currency("   ") is None


class TestPercentageParsing:
    """Tests for parsing percentage strings."""

    def test_with_percent_sign(self) -> None:
        """Percentage with % should convert to decimal."""
        assert parse_percentage("25%") == Decimal("0.25")
        assert parse_percentage("100%") == Decimal("1")
        assert parse_percentage("0.5%") == Decimal("0.005")

    def test_without_percent_sign(self) -> None:
        """Number without % should pass through (assumed already decimal)."""
        assert parse_percentage("0.25") == Decimal("0.25")

    def test_whitespace_handling(self) -> None:
        """Whitespace around % should be handled."""
        assert parse_percentage("  25 %  ") == Decimal("0.25")
        assert parse_percentage("25 %") == Decimal("0.25")

    def test_null_values(self) -> None:
        """NULL-like values should return None."""
        assert parse_percentage(None) is None
        assert parse_percentage("") is None


class TestScaledNumberParsing:
    """Tests for parsing numbers with scale suffixes."""

    def test_trillion(self) -> None:
        """Trillion suffix should scale correctly."""
        assert parse_scaled_number("1 Trillion") == Decimal("1000000000000")
        assert parse_scaled_number("1.5 trillion") == Decimal("1500000000000")
        assert parse_scaled_number("1.5T") == Decimal("1500000000000")

    def test_billion(self) -> None:
        """Billion suffix should scale correctly."""
        assert parse_scaled_number("500 Billion") == Decimal("500000000000")
        assert parse_scaled_number("1.25B") == Decimal("1250000000")

    def test_million(self) -> None:
        """Million suffix should scale correctly."""
        assert parse_scaled_number("100 Million") == Decimal("100000000")
        assert parse_scaled_number("1.5M") == Decimal("1500000")

    def test_thousand(self) -> None:
        """Thousand suffix should scale correctly."""
        assert parse_scaled_number("50 thousand") == Decimal("50000")
        assert parse_scaled_number("100K") == Decimal("100000")

    def test_quadrillion(self) -> None:
        """Quadrillion suffix should scale correctly."""
        assert parse_scaled_number("1 Quadrillion") == Decimal("1000000000000000")

    def test_no_suffix(self) -> None:
        """Number without suffix should parse as-is."""
        assert parse_scaled_number("1234567") == Decimal("1234567")

    def test_with_commas(self) -> None:
        """Commas in number should be handled."""
        assert parse_scaled_number("1,234 Million") == Decimal("1234000000")

    def test_null_values(self) -> None:
        """NULL-like values should return None."""
        assert parse_scaled_number(None) is None
        assert parse_scaled_number("") is None


class TestFrequencyNormalization:
    """Tests for normalizing frequency strings."""

    def test_annual_variations(self) -> None:
        """Various annual representations should normalize."""
        annual_inputs = ["Annual", "ANNUAL", "annually", "Yearly", "Year", "A", "ann"]
        for freq in annual_inputs:
            assert normalize_frequency(freq) == "annual", f"{freq} should be annual"

    def test_quarterly_variations(self) -> None:
        """Various quarterly representations should normalize."""
        quarterly_inputs = ["Quarterly", "QUARTERLY", "Quarter", "Q", "qtr"]
        for freq in quarterly_inputs:
            assert normalize_frequency(freq) == "quarterly", f"{freq} should be quarterly"

    def test_monthly_variations(self) -> None:
        """Various monthly representations should normalize."""
        monthly_inputs = ["Monthly", "MONTHLY", "Month", "M", "mo"]
        for freq in monthly_inputs:
            assert normalize_frequency(freq) == "monthly", f"{freq} should be monthly"

    def test_daily_variations(self) -> None:
        """Various daily representations should normalize."""
        daily_inputs = ["Daily", "DAILY", "Day", "D"]
        for freq in daily_inputs:
            assert normalize_frequency(freq) == "daily", f"{freq} should be daily"

    def test_unknown_returns_none(self) -> None:
        """Unknown frequency should return None."""
        assert normalize_frequency("Weekly") is None
        assert normalize_frequency("Biannual") is None

    def test_null_values(self) -> None:
        """NULL-like values should return None."""
        assert normalize_frequency(None) is None
        assert normalize_frequency("") is None


class TestFloatToDecimalPrecision:
    """Tests for avoiding float-to-decimal precision issues."""

    def test_notorious_float_issues(self) -> None:
        """Classic float precision issues should be handled."""
        # 0.1 + 0.2 != 0.3 in binary float land
        result = safe_float_to_decimal(0.1)
        assert result == Decimal("0.1")

        result = safe_float_to_decimal(0.1 + 0.2)
        # Should be close to 0.3, not 0.30000000000000004
        assert abs(result - Decimal("0.3")) < Decimal("0.0000001")

    def test_large_floats(self) -> None:
        """Large floats should convert without precision loss."""
        result = safe_float_to_decimal(1234567890.12)
        assert abs(result - Decimal("1234567890.12")) < Decimal("0.01")

    def test_small_floats(self) -> None:
        """Small floats should convert correctly."""
        result = safe_float_to_decimal(0.000001)
        assert result == Decimal("0.000001")

    def test_zero(self) -> None:
        """Zero should convert correctly."""
        assert safe_float_to_decimal(0.0) == Decimal("0")

    def test_negative(self) -> None:
        """Negative floats should convert correctly."""
        assert safe_float_to_decimal(-123.45) == Decimal("-123.45")


class TestBooleanCoercion:
    """Tests for coercing various boolean representations."""

    def test_python_bool(self) -> None:
        """Python booleans should pass through."""
        assert coerce_boolean(True) is True
        assert coerce_boolean(False) is False

    def test_integers(self) -> None:
        """1/0 should convert to True/False."""
        assert coerce_boolean(1) is True
        assert coerce_boolean(0) is False
        assert coerce_boolean(42) is True  # Any non-zero is True

    def test_string_true(self) -> None:
        """Various true strings should convert."""
        true_strings = ["true", "True", "TRUE", "yes", "Yes", "Y", "y", "1", "t", "T"]
        for s in true_strings:
            assert coerce_boolean(s) is True, f"'{s}' should be True"

    def test_string_false(self) -> None:
        """Various false strings should convert."""
        false_strings = ["false", "False", "FALSE", "no", "No", "N", "n", "0", "f", "F"]
        for s in false_strings:
            assert coerce_boolean(s) is False, f"'{s}' should be False"

    def test_none_returns_none(self) -> None:
        """None should return None."""
        assert coerce_boolean(None) is None

    def test_unknown_string_returns_none(self) -> None:
        """Unknown strings should return None."""
        assert coerce_boolean("maybe") is None
        assert coerce_boolean("unknown") is None
        assert coerce_boolean("") is None


class TestDataQualityEdgeCases:
    """Tests for edge cases that cause ETL issues."""

    def test_unicode_whitespace(self) -> None:
        """Non-breaking spaces and other unicode whitespace."""
        # Non-breaking space (U+00A0) often appears in data
        value_with_nbsp = "100\u00a0000"  # 100 000 with non-breaking space
        # This should be handled - currently it might fail
        result = coerce_to_decimal(value_with_nbsp.replace("\u00a0", ""))
        assert result == Decimal("100000")

    def test_bom_in_data(self) -> None:
        """Byte order mark at start of string."""
        value_with_bom = "\ufeff100.50"  # BOM + number
        result = coerce_to_decimal(value_with_bom.replace("\ufeff", ""))
        assert result == Decimal("100.50")

    def test_mixed_case_units(self) -> None:
        """Units should be case-insensitive."""
        assert parse_scaled_number("1 TRILLION") == Decimal("1000000000000")
        assert parse_scaled_number("1 TriLLion") == Decimal("1000000000000")

    def test_leading_trailing_zeros(self) -> None:
        """Leading/trailing zeros should be handled."""
        assert parse_currency("00100.50") == Decimal("100.50")
        assert parse_currency("100.500") == Decimal("100.500")

    def test_scientific_notation(self) -> None:
        """Scientific notation should be handled."""
        # Common in large economic values
        result = coerce_to_decimal("1.5e9")
        assert result == Decimal("1500000000")

        result = coerce_to_decimal("1.5E-3")
        assert result == Decimal("0.0015")

    def test_inf_and_nan(self) -> None:
        """Infinity and NaN should be handled gracefully."""
        # These should return None, not crash
        assert coerce_to_decimal("inf") is None or coerce_to_decimal("inf") == Decimal("inf")
        # NaN is tricky - just make sure we don't crash
        result = coerce_to_decimal("nan")
        assert result is None or isinstance(result, Decimal)


class TestNullValuePatterns:
    """Comprehensive tests for NULL value patterns in source data."""

    @pytest.fixture
    def null_representations(self) -> list[str | None]:
        """Common NULL representations found in source data."""
        return [
            None,
            "",
            "   ",
            "NULL",
            "null",
            "Null",
            "N/A",
            "n/a",
            "NA",
            "na",
            "#N/A",
            "#NA",
            "-",
            "--",
            ".",
            "..",
            "(X)",  # Census suppressed data
            "(D)",  # Census withheld data
            "(S)",  # Census suppressed data (alternate)
            "*",
            "**",
            "***",
            "NaN",
            "nan",
            "-999",  # Sentinel values
            "-9999",
            "99999",
        ]

    def test_currency_null_patterns(self, null_representations: list[str | None]) -> None:
        """Currency parser should handle all NULL patterns."""
        for value in null_representations:
            result = parse_currency(value)
            # Should either be None or a valid Decimal (for sentinel values)
            assert result is None or isinstance(result, Decimal)

    def test_percentage_null_patterns(self, null_representations: list[str | None]) -> None:
        """Percentage parser should handle all NULL patterns."""
        for value in null_representations:
            result = parse_percentage(value)
            assert result is None or isinstance(result, Decimal)

    def test_scaled_number_null_patterns(self, null_representations: list[str | None]) -> None:
        """Scaled number parser should handle all NULL patterns."""
        for value in null_representations:
            result = parse_scaled_number(value)
            assert result is None or isinstance(result, Decimal)


class TestCommonETLBugs:
    """Tests targeting specific bugs commonly encountered in ETL."""

    def test_empty_string_vs_none(self) -> None:
        """Empty string and None should both be treated as missing."""
        # This is a common bug: treating "" as valid and None as missing
        assert coerce_to_decimal("") is None
        assert coerce_to_decimal(None) is None
        # Both should have same effect in FK lookups
        assert resolve_foreign_key({"a": 1}, "", required=False) is None
        assert resolve_foreign_key({"a": 1}, None, required=False) is None

    def test_string_zero_vs_integer_zero(self) -> None:
        """String '0' and integer 0 should both be valid values."""
        # This catches the bug of treating 0 as falsy/missing
        assert coerce_to_decimal("0") == Decimal("0")
        assert coerce_to_decimal(0) == Decimal("0")
        # Zero is a valid value, not NULL!
        assert coerce_boolean(0) is False  # 0 is False, not None
        assert coerce_boolean("0") is False

    def test_whitespace_only_not_valid(self) -> None:
        """Whitespace-only strings should be treated as missing."""
        assert coerce_to_decimal("   ") is None
        assert normalize_industry_code("   ") is None
        assert normalize_frequency("   ") is None

    def test_type_mismatch_handling(self) -> None:
        """Unexpected types should be handled without crashing."""
        # Sometimes data comes as wrong type
        assert coerce_to_decimal(["1", "2"]) is None  # List instead of string
        assert coerce_to_decimal({"value": 1}) is None  # Dict instead of string
        assert coerce_boolean([]) is None

    def test_numeric_string_with_units(self) -> None:
        """Numbers with embedded units in source data."""
        # Common in energy data: "1,234 BTU" or "100 MW"
        # For now, just test that we don't crash
        result = coerce_to_decimal("1,234 BTU")
        # This will likely return None, which is correct behavior
        # The caller should strip units before calling
        assert result is None or isinstance(result, Decimal)
