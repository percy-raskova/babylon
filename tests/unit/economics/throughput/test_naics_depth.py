"""Unit tests for NAICS depth mapping.

Feature: 014-throughput-position
TDD Phase: Red/Green
"""

from __future__ import annotations

from babylon.economics.throughput.naics_depth import (
    NAICS_DEPTH_MAPPING,
    get_depth,
    validate_depth,
)


class TestNAICSDepthMapping:
    """Tests for the NAICS_DEPTH_MAPPING constant."""

    def test_extraction_sectors_have_depth_zero(self) -> None:
        """Extraction sectors (mining, agriculture) should have depth 0."""
        assert NAICS_DEPTH_MAPPING["11"] == 0.0  # Agriculture
        assert NAICS_DEPTH_MAPPING["21"] == 0.0  # Mining

    def test_manufacturing_sectors_have_depth_one_point_five(self) -> None:
        """Manufacturing spans primary and secondary, averaging to 1.5."""
        assert NAICS_DEPTH_MAPPING["31"] == 1.5
        assert NAICS_DEPTH_MAPPING["32"] == 1.5
        assert NAICS_DEPTH_MAPPING["33"] == 1.5

    def test_logistics_sectors_have_depth_three(self) -> None:
        """Logistics/wholesale coordination at depth 3."""
        assert NAICS_DEPTH_MAPPING["42"] == 3.0  # Wholesale Trade
        assert NAICS_DEPTH_MAPPING["48"] == 3.0  # Transportation
        assert NAICS_DEPTH_MAPPING["49"] == 3.0  # Warehousing
        assert NAICS_DEPTH_MAPPING["56"] == 3.0  # Admin/Support

    def test_service_sectors_have_depth_four(self) -> None:
        """Service/retail realization at depth 4."""
        assert NAICS_DEPTH_MAPPING["44"] == 4.0  # Retail
        assert NAICS_DEPTH_MAPPING["45"] == 4.0  # Retail
        assert NAICS_DEPTH_MAPPING["51"] == 4.0  # Information
        assert NAICS_DEPTH_MAPPING["54"] == 4.0  # Professional Services
        assert NAICS_DEPTH_MAPPING["61"] == 4.0  # Education
        assert NAICS_DEPTH_MAPPING["62"] == 4.0  # Healthcare
        assert NAICS_DEPTH_MAPPING["72"] == 4.0  # Accommodation/Food

    def test_finance_sectors_have_depth_five(self) -> None:
        """Financial coordination at depth 5 (highest)."""
        assert NAICS_DEPTH_MAPPING["52"] == 5.0  # Finance
        assert NAICS_DEPTH_MAPPING["53"] == 5.0  # Real Estate
        assert NAICS_DEPTH_MAPPING["55"] == 5.0  # Management

    def test_utilities_and_construction_have_depth_two(self) -> None:
        """Infrastructure sectors at depth 2."""
        assert NAICS_DEPTH_MAPPING["22"] == 2.0  # Utilities
        assert NAICS_DEPTH_MAPPING["23"] == 2.0  # Construction

    def test_all_values_in_valid_range(self) -> None:
        """All depth values must be in [0.0, 5.0]."""
        for naics, depth in NAICS_DEPTH_MAPPING.items():
            assert 0.0 <= depth <= 5.0, f"NAICS {naics} has invalid depth {depth}"

    def test_mapping_has_expected_sector_count(self) -> None:
        """Mapping should cover all major NAICS sectors (20+)."""
        assert len(NAICS_DEPTH_MAPPING) >= 20


class TestGetDepth:
    """Tests for the get_depth() function."""

    def test_known_sector_returns_depth(self) -> None:
        """Known sectors return their depth value."""
        assert get_depth("21") == 0.0  # Mining
        assert get_depth("52") == 5.0  # Finance
        assert get_depth("31") == 1.5  # Manufacturing

    def test_unknown_sector_returns_none(self) -> None:
        """Unknown sectors return None."""
        assert get_depth("99") is None
        assert get_depth("00") is None
        assert get_depth("XX") is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert get_depth("") is None

    def test_three_digit_naics_returns_none(self) -> None:
        """Three-digit NAICS codes are not in mapping (2-digit only)."""
        # 311 is Food Manufacturing, but we only have 2-digit codes
        assert get_depth("311") is None


class TestValidateDepth:
    """Tests for the validate_depth() function."""

    def test_valid_range_minimum(self) -> None:
        """Depth 0.0 is valid (extraction)."""
        assert validate_depth(0.0) is True

    def test_valid_range_maximum(self) -> None:
        """Depth 5.0 is valid (finance)."""
        assert validate_depth(5.0) is True

    def test_valid_intermediate_values(self) -> None:
        """Intermediate depths are valid."""
        assert validate_depth(1.5) is True
        assert validate_depth(2.5) is True
        assert validate_depth(3.5) is True
        assert validate_depth(4.5) is True

    def test_below_range_invalid(self) -> None:
        """Negative depths are invalid."""
        assert validate_depth(-0.1) is False
        assert validate_depth(-1.0) is False

    def test_above_range_invalid(self) -> None:
        """Depths above 5.0 are invalid."""
        assert validate_depth(5.1) is False
        assert validate_depth(6.0) is False
        assert validate_depth(10.0) is False


class TestTheoreticalConsistency:
    """Tests validating theoretical expectations about depth values."""

    def test_finance_deeper_than_manufacturing(self) -> None:
        """Finance (coordination) should be deeper than manufacturing."""
        finance_depth = get_depth("52")
        manufacturing_depth = get_depth("31")
        assert finance_depth is not None
        assert manufacturing_depth is not None
        assert finance_depth > manufacturing_depth

    def test_manufacturing_deeper_than_extraction(self) -> None:
        """Manufacturing should be deeper than extraction."""
        manufacturing_depth = get_depth("31")
        mining_depth = get_depth("21")
        assert manufacturing_depth is not None
        assert mining_depth is not None
        assert manufacturing_depth > mining_depth

    def test_retail_deeper_than_wholesale(self) -> None:
        """Retail (final realization) should be deeper than wholesale."""
        retail_depth = get_depth("44")
        wholesale_depth = get_depth("42")
        assert retail_depth is not None
        assert wholesale_depth is not None
        assert retail_depth > wholesale_depth

    def test_finance_is_maximum_depth(self) -> None:
        """Finance should be at maximum depth (5.0)."""
        finance_depth = get_depth("52")
        assert finance_depth == 5.0
        # No sector should be deeper than finance
        for naics, depth in NAICS_DEPTH_MAPPING.items():
            assert depth <= 5.0, f"NAICS {naics} exceeds finance depth"
