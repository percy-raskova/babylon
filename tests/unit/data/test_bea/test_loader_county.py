"""Unit tests for BEA county GDP loader.

Tests the BEACountyGDPLoader class for:
- GDP value parsing with suppression handling
- County FIPS extraction and validation
- Industry ID mapping via NAICS codes
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

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
        from babylon.data.normalize.schema import FactBEACountyGDP

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
        from babylon.data.normalize.database import get_normalized_session_factory

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
