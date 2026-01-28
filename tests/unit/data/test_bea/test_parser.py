"""Unit tests for BEA XLSX parser.

Tests the BEAIndustryParser class for correct parsing of:
- Industry hierarchy from indentation
- Year extraction from header rows
- Value extraction from data rows
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from babylon.data.bea.parser import (
    BEAIndustry,
    BEAIndustryParser,
    BEAIndustryValue,
    BEAParseResult,
)


class TestBEAIndustryParsing:
    """Test industry hierarchy parsing from indentation."""

    @pytest.fixture
    def parser(self, tmp_path: Path) -> BEAIndustryParser:
        """Create parser with temporary data directory."""
        return BEAIndustryParser(tmp_path)

    def test_level_1_all_industries(self, parser: BEAIndustryParser) -> None:
        """Line 1 'All industries' should be level 1 regardless of indentation."""
        industry = parser._parse_industry(1, "    All industries")
        assert industry.level == 1
        assert industry.name == "All industries"
        assert industry.code == "BEA001"

    def test_level_1_no_indent(self, parser: BEAIndustryParser) -> None:
        """No leading spaces indicates level 1 (major categories)."""
        industry = parser._parse_industry(2, "Private industries")
        assert industry.level == 1
        assert industry.name == "Private industries"

    def test_level_2_two_space_indent(self, parser: BEAIndustryParser) -> None:
        """Two leading spaces indicates level 2 (sectors)."""
        industry = parser._parse_industry(3, "  Agriculture, forestry, fishing, and hunting")
        assert industry.level == 2
        assert industry.name == "Agriculture, forestry, fishing, and hunting"

    def test_level_3_four_space_indent(self, parser: BEAIndustryParser) -> None:
        """Four leading spaces indicates level 3 (industries)."""
        industry = parser._parse_industry(4, "    Farms")
        assert industry.level == 3
        assert industry.name == "Farms"

    def test_level_4_six_space_indent(self, parser: BEAIndustryParser) -> None:
        """Six or more leading spaces indicates level 4 (detail)."""
        industry = parser._parse_industry(14, "      Wood products")
        assert industry.level == 4
        assert industry.name == "Wood products"

    def test_code_generation(self, parser: BEAIndustryParser) -> None:
        """BEA codes should be generated from line numbers."""
        industry = parser._parse_industry(42, "  Mining")
        assert industry.code == "BEA042"
        assert industry.line_number == 42


class TestYearParsing:
    """Test year extraction from header rows."""

    @pytest.fixture
    def parser(self, tmp_path: Path) -> BEAIndustryParser:
        """Create parser with temporary data directory."""
        return BEAIndustryParser(tmp_path)

    def test_parse_years_from_header(self, parser: BEAIndustryParser) -> None:
        """Should extract years from header row tuple."""
        header = ("Line", None, None, "1997", "1998", "1999", "2000")
        years = parser._parse_years(header)
        assert years == [1997, 1998, 1999, 2000]

    def test_parse_years_ignores_non_years(self, parser: BEAIndustryParser) -> None:
        """Should ignore non-year values."""
        header = ("Line", "Industry", 5, "1997", "text", "2000")
        years = parser._parse_years(header)
        assert years == [1997, 2000]

    def test_parse_years_filters_unreasonable_years(self, parser: BEAIndustryParser) -> None:
        """Should filter years outside reasonable range (1990-2050)."""
        header = (1800, 1997, 2000, 2060)
        years = parser._parse_years(header)
        assert years == [1997, 2000]


class TestValueExtraction:
    """Test value extraction from data rows."""

    @pytest.fixture
    def parser(self, tmp_path: Path) -> BEAIndustryParser:
        """Create parser with temporary data directory."""
        return BEAIndustryParser(tmp_path)

    def test_extract_values_basic(self, parser: BEAIndustryParser) -> None:
        """Should extract numeric values aligned with years."""
        row = ("1", "    All industries", None, 15393618, 16217046, 17273381)
        years = [1997, 1998, 1999]
        values = parser._extract_year_values(row, years)

        assert len(values) == 3
        assert values[1997] == Decimal("15393618")
        assert values[1998] == Decimal("16217046")
        assert values[1999] == Decimal("17273381")

    def test_extract_values_handles_none(self, parser: BEAIndustryParser) -> None:
        """Should handle None values in data."""
        row = ("1", "Industry", None, 100, None, 200)
        years = [2000, 2001, 2002]
        values = parser._extract_year_values(row, years)

        assert values[2000] == Decimal("100")
        assert values[2001] is None
        assert values[2002] == Decimal("200")

    def test_get_industry_name_preserves_spaces(self, parser: BEAIndustryParser) -> None:
        """Should preserve leading spaces in industry names."""
        row = ("1", "    All industries", None, 100)
        name = parser._get_industry_name(row)
        assert name == "    All industries"
        assert name.startswith("    ")


class TestParseResultStructure:
    """Test BEAParseResult data structure."""

    def test_parse_result_defaults(self) -> None:
        """Should have sensible defaults."""
        result = BEAParseResult()
        assert result.industries == []
        assert result.values == []
        assert result.years == []
        assert result.source_file == ""
        assert result.value_type == ""

    def test_bea_industry_structure(self) -> None:
        """BEAIndustry should store all required fields."""
        industry = BEAIndustry(
            line_number=1,
            name="Test Industry",
            raw_name="  Test Industry",
            level=2,
            code="BEA001",
        )
        assert industry.line_number == 1
        assert industry.name == "Test Industry"
        assert industry.raw_name == "  Test Industry"
        assert industry.level == 2
        assert industry.code == "BEA001"

    def test_bea_industry_value_structure(self) -> None:
        """BEAIndustryValue should store line_number, year, and value."""
        value = BEAIndustryValue(
            line_number=1,
            year=2000,
            value_millions=Decimal("15393618"),
        )
        assert value.line_number == 1
        assert value.year == 2000
        assert value.value_millions == Decimal("15393618")


@pytest.mark.integration
class TestActualFilesParsing:
    """Integration tests against actual BEA XLSX files.

    These tests require the actual BEA data files to be present.
    """

    @pytest.fixture
    def parser(self) -> BEAIndustryParser:
        """Create parser with actual data directory."""
        return BEAIndustryParser(Path("data"))

    def test_parse_gross_output_file_exists(self, parser: BEAIndustryParser) -> None:
        """Should successfully parse GrossOutput.xlsx if file exists."""
        result = parser.parse_gross_output()
        assert len(result.industries) > 0
        assert len(result.values) > 0
        assert len(result.years) > 0
        assert result.value_type == "gross_output"

    def test_parse_value_added_file_exists(self, parser: BEAIndustryParser) -> None:
        """Should successfully parse ValueAdded.xlsx if file exists."""
        result = parser.parse_value_added()
        assert len(result.industries) > 0
        assert len(result.values) > 0
        assert result.value_type == "value_added"

    def test_parse_intermediate_inputs_file_exists(self, parser: BEAIndustryParser) -> None:
        """Should successfully parse IntermediateInputs.xlsx if file exists."""
        result = parser.parse_intermediate_inputs()
        assert len(result.industries) > 0
        assert len(result.values) > 0
        assert result.value_type == "intermediate_inputs"

    def test_all_industries_count_reasonable(self, parser: BEAIndustryParser) -> None:
        """Should parse approximately 71-100 BEA industries."""
        result = parser.parse_gross_output()
        # BEA national accounts have ~71-100 industry lines
        assert 50 <= len(result.industries) <= 150

    def test_years_span_expected_range(self, parser: BEAIndustryParser) -> None:
        """Years should span from late 1990s to recent years."""
        result = parser.parse_gross_output()
        assert min(result.years) <= 2000
        assert max(result.years) >= 2020

    def test_hierarchy_levels_present(self, parser: BEAIndustryParser) -> None:
        """Should have industries at all 4 hierarchy levels."""
        result = parser.parse_gross_output()
        levels = {ind.level for ind in result.industries}
        assert 1 in levels  # Sector/total
        assert 2 in levels  # Major industry
        assert 3 in levels  # Industry
        assert 4 in levels  # Detail
