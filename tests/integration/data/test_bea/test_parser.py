"""Integration tests for BEA XLSX parser.

Tests against actual BEA XLSX files.
Requires the actual BEA data files to be present.

Extracted from tests/unit/data/test_bea/test_parser.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.data.bea.parser import BEAIndustryParser


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
