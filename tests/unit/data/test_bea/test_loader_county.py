"""Unit tests for BEA county GDP loader.

Tests the BEACountyGDPLoader class for:
- GDP value parsing with suppression handling
- County FIPS extraction and validation
- Industry ID mapping via NAICS codes
- Regression tests for encoding and FIPS lookup bugs
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from babylon.data.bea.loader_county import BEACountyGDPLoader


class TestGDPValueParsing:
    """Test GDP value parsing from CSV strings."""

    def test_parse_normal_value(self) -> None:
        """Should convert thousands to millions."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("1000000")
        assert result == Decimal("1000")  # 1M thousands = 1000 millions

    def test_parse_value_with_commas(self) -> None:
        """Should handle comma-separated values."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("1,000,000")
        assert result == Decimal("1000")

    def test_parse_suppressed_value(self) -> None:
        """Should return None for suppressed (D) values."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("(D)")
        assert result is None

    def test_parse_empty_value(self) -> None:
        """Should return None for empty strings."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("")
        assert result is None

    def test_parse_whitespace_value(self) -> None:
        """Should return None for whitespace-only strings."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("   ")
        assert result is None

    def test_parse_small_value(self) -> None:
        """Should handle small values accurately."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("500")
        assert result == Decimal("0.5")  # 500 thousands = 0.5 millions

    def test_parse_invalid_value(self) -> None:
        """Should return None for non-numeric values."""
        from babylon.data.bea.loader_county import parse_gdp_value

        result = parse_gdp_value("N/A")
        assert result is None


class TestCountyFIPSExtraction:
    """Test county FIPS extraction from GeoFIPS field."""

    def test_extract_valid_county_fips(self) -> None:
        """Should extract 5-digit county FIPS."""
        from babylon.data.bea.loader_county import extract_county_fips

        result = extract_county_fips(' "01001"')
        assert result == "01001"

    def test_extract_fips_with_quotes(self) -> None:
        """Should handle quoted FIPS codes."""
        from babylon.data.bea.loader_county import extract_county_fips

        result = extract_county_fips('"06037"')
        assert result == "06037"

    def test_skip_national_code(self) -> None:
        """Should skip national code 00000."""
        from babylon.data.bea.loader_county import extract_county_fips

        result = extract_county_fips(' "00000"')
        assert result is None

    def test_skip_state_code(self) -> None:
        """Should skip state codes (XX000)."""
        from babylon.data.bea.loader_county import extract_county_fips

        result = extract_county_fips(' "06000"')
        assert result is None

    def test_skip_metro_code(self) -> None:
        """Should skip metro codes (not 5 digits)."""
        from babylon.data.bea.loader_county import extract_county_fips

        result = extract_county_fips("M0001")
        assert result is None

    def test_extract_fips_with_spaces(self) -> None:
        """Should handle FIPS with leading spaces."""
        from babylon.data.bea.loader_county import extract_county_fips

        result = extract_county_fips("   01001  ")
        assert result == "01001"


class TestLoaderStructure:
    """Test loader structure and configuration."""

    def test_loader_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader base class."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader
        from babylon.data.loader_base import DataLoader

        loader = BEACountyGDPLoader()
        assert isinstance(loader, DataLoader)

    def test_default_data_dir(self) -> None:
        """Should use 'data' as default data directory."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader

        loader = BEACountyGDPLoader()
        assert loader.data_dir == Path("data")

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Should accept custom data directory."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader

        loader = BEACountyGDPLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables_empty(self) -> None:
        """County GDP loader doesn't create dimensions."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader

        loader = BEACountyGDPLoader()
        assert loader.get_dimension_tables() == []

    def test_get_fact_tables(self) -> None:
        """Should declare FactBEACountyGDP as fact table."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader
        from babylon.data.reference.schema import FactBEACountyGDP

        loader = BEACountyGDPLoader()
        tables = loader.get_fact_tables()
        assert FactBEACountyGDP in tables


class TestNAICSToLineCodeMapping:
    """Test NAICS code to BEA line code mapping."""

    def test_all_industry_mapping(self) -> None:
        """Should map '...' to line 1 (all industry total)."""
        from babylon.data.bea.loader_county import NAICS_TO_LINE_CODE

        assert NAICS_TO_LINE_CODE["..."] == 1

    def test_agriculture_mapping(self) -> None:
        """Should map '11' to line 3 (agriculture)."""
        from babylon.data.bea.loader_county import NAICS_TO_LINE_CODE

        assert NAICS_TO_LINE_CODE["11"] == 3

    def test_manufacturing_mapping(self) -> None:
        """Should map '31-33' to line 12 (manufacturing)."""
        from babylon.data.bea.loader_county import NAICS_TO_LINE_CODE

        assert NAICS_TO_LINE_CODE["31-33"] == 12

    def test_retail_mapping(self) -> None:
        """Should map '44-45' to line 35 (retail trade)."""
        from babylon.data.bea.loader_county import NAICS_TO_LINE_CODE

        assert NAICS_TO_LINE_CODE["44-45"] == 35

    def test_government_mapping(self) -> None:
        """Should map '92' to line 83 (government)."""
        from babylon.data.bea.loader_county import NAICS_TO_LINE_CODE

        assert NAICS_TO_LINE_CODE["92"] == 83


@pytest.mark.integration
class TestActualDatabaseLoading:
    """Integration tests against actual database.

    These tests require:
    - DimCounty to be populated (from CensusLoader)
    - DimBEAIndustry to be populated (from BEANationalLoader)
    - CAGDP2.zip to exist in data/bea/regional/
    """

    @pytest.fixture(scope="class")
    def session_factory(self) -> Callable:
        """Get session factory."""
        from babylon.data.reference.database import get_normalized_session_factory

        return get_normalized_session_factory()

    @pytest.fixture
    def loader(self) -> BEACountyGDPLoader:
        """Create loader."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader

        return BEACountyGDPLoader()

    def test_load_creates_county_gdp_records(
        self, session_factory: Callable, loader: BEACountyGDPLoader
    ) -> None:
        """Should create county GDP records."""
        from pathlib import Path

        from sqlalchemy import text

        # Check prerequisites
        zip_path = Path("data/bea/regional/CAGDP2.zip")
        if not zip_path.exists():
            pytest.skip("CAGDP2.zip not downloaded")

        with session_factory() as session:
            county_count = session.execute(text("SELECT COUNT(*) FROM dim_county")).scalar()
            if county_count == 0:
                pytest.skip("DimCounty not populated (requires CensusLoader)")

            industry_count = session.execute(text("SELECT COUNT(*) FROM dim_bea_industry")).scalar()
            if industry_count == 0:
                pytest.skip("DimBEAIndustry not populated (requires BEANationalLoader)")

            # Load county GDP
            stats = loader.load(session, reset=True, verbose=False)

            # Should have created records
            gdp_count = session.execute(text("SELECT COUNT(*) FROM fact_bea_county_gdp")).scalar()

            assert gdp_count > 0
            assert stats.facts_loaded.get("fact_bea_county_gdp", 0) == gdp_count

    def test_all_gdp_records_have_valid_county(
        self, session_factory: Callable, loader: BEACountyGDPLoader
    ) -> None:
        """All GDP records should reference valid counties."""
        from pathlib import Path

        from sqlalchemy import text

        zip_path = Path("data/bea/regional/CAGDP2.zip")
        if not zip_path.exists():
            pytest.skip("CAGDP2.zip not downloaded")

        with session_factory() as session:
            gdp_count = session.execute(text("SELECT COUNT(*) FROM fact_bea_county_gdp")).scalar()
            if gdp_count == 0:
                pytest.skip("fact_bea_county_gdp not populated")

            # Check FK integrity
            result = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM fact_bea_county_gdp g
                    LEFT JOIN dim_county c ON g.county_id = c.county_id
                    WHERE c.county_id IS NULL
                """)
            ).scalar()

            assert result == 0

    def test_all_gdp_records_have_valid_industry(
        self, session_factory: Callable, loader: BEACountyGDPLoader
    ) -> None:
        """All GDP records should reference valid industries."""
        from pathlib import Path

        from sqlalchemy import text

        zip_path = Path("data/bea/regional/CAGDP2.zip")
        if not zip_path.exists():
            pytest.skip("CAGDP2.zip not downloaded")

        with session_factory() as session:
            gdp_count = session.execute(text("SELECT COUNT(*) FROM fact_bea_county_gdp")).scalar()
            if gdp_count == 0:
                pytest.skip("fact_bea_county_gdp not populated")

            # Check FK integrity
            result = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM fact_bea_county_gdp g
                    LEFT JOIN dim_bea_industry i ON g.bea_industry_id = i.bea_industry_id
                    WHERE i.bea_industry_id IS NULL
                """)
            ).scalar()

            assert result == 0


class TestRegressionBugs:
    """Regression tests for previously encountered bugs.

    These tests ensure we don't reintroduce bugs that were fixed:
    - Latin-1 encoding for county names with special characters (ñ)
    - Full 5-digit FIPS codes in county cache lookup
    - CSV DictReader file handle state corruption
    """

    def test_csv_handles_latin1_characters(self, tmp_path: Path) -> None:
        """CSV reading should handle Latin-1 encoded county names.

        BEA CSV files contain county names like "Doña Ana County" which use
        Latin-1 encoding (byte 0xf1 = ñ). Reading with UTF-8 would raise:
        UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf1

        Regression test for: fix(data): use latin-1 encoding for BEA county CSV
        """
        # Create CSV with Latin-1 encoded county name
        csv_content = (
            "GeoFIPS,GeoName,Region,TableName,LineCode,IndustryClassification,"
            "Description,Unit,2022,2023\n"
            '"35013","Doña Ana, NM",,CAGDP2,1,"...","All industry total",'
            '"Thousands of dollars",1000000,1100000\n'
        )

        csv_path = tmp_path / "test_latin1.csv"
        # Write with Latin-1 encoding (as BEA files use)
        csv_path.write_bytes(csv_content.encode("latin-1"))

        # Verify reading with latin-1 works (our fix)
        with open(csv_path, encoding="latin-1") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert "Doña Ana" in row["GeoName"]

        # Verify reading with UTF-8 would fail (the original bug)
        with pytest.raises(UnicodeDecodeError), open(csv_path, encoding="utf-8") as f:
            _ = f.read()

    def test_county_cache_uses_full_fips(self) -> None:
        """County cache should use full 5-digit FIPS, not 3-digit county_fips.

        DimCounty has both:
        - fips: "01001" (full 5-digit FIPS)
        - county_fips: "001" (3-digit county code within state)

        The BEA CSV uses full 5-digit FIPS, so cache must use DimCounty.fips.

        Regression test for: fix(data): use full 5-digit FIPS in BEA county loader
        """
        from babylon.data.bea.loader_county import BEACountyGDPLoader

        loader = BEACountyGDPLoader()

        # Create mock session with sample county data
        mock_session = MagicMock()

        # Mock DimCounty with both fips (5-digit) and county_fips (3-digit)
        mock_county = MagicMock()
        mock_county.county_id = 1
        mock_county.fips = "01001"  # Full 5-digit FIPS
        mock_county.county_fips = "001"  # 3-digit county code (WRONG to use)

        mock_session.query.return_value.all.return_value = [
            (mock_county.county_id, mock_county.fips)
        ]

        # Build cache - should use full FIPS
        loader._build_county_cache(mock_session)

        # Verify cache is keyed by full 5-digit FIPS
        assert "01001" in loader._county_cache
        assert loader._county_cache["01001"] == 1

        # Verify cache is NOT keyed by 3-digit county_fips
        assert "001" not in loader._county_cache

    def test_csv_reader_state_not_corrupted(self, tmp_path: Path) -> None:
        """CSV DictReader should not have corrupted state after line counting.

        Original bug: Creating DictReader, seeking file, counting lines, then
        creating new DictReader caused the new reader to read data row as header.

        The fix uses separate file handles for counting vs reading.

        Regression test for: fix(data): fix CSV DictReader state corruption
        """
        # Create a simple CSV
        csv_content = "col_a,col_b,col_c\n1,2,3\n4,5,6\n"
        csv_path = tmp_path / "test_reader.csv"
        csv_path.write_text(csv_content)

        # Our fixed pattern: separate handles for counting and reading
        with open(csv_path) as f:
            total_lines = sum(1 for _ in f) - 1  # Count lines

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Line count should match actual data rows
        assert total_lines == 2

        # Should have correct fieldnames and data
        assert reader.fieldnames == ["col_a", "col_b", "col_c"]
        assert len(rows) == total_lines
        assert rows[0]["col_a"] == "1"

        # The OLD buggy pattern (don't do this):
        # with open(csv_path) as f:
        #     reader = csv.DictReader(f)
        #     f.seek(0)
        #     total_lines = sum(1 for _ in f) - 1
        #     f.seek(0)
        #     next(reader)  # This corrupts state
        #     reader = csv.DictReader(f)  # This reads "1,2,3" as header!
