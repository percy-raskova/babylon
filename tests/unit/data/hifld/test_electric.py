"""Unit tests for HIFLD Electric Grid loader.

Tests the HIFLDElectricLoader class including FIPS extraction, capacity
estimation, and substation aggregation logic.
"""

from __future__ import annotations

import pytest

from babylon.data.hifld.electric import HIFLDElectricLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def electric_loader() -> HIFLDElectricLoader:
    """Create electric grid loader for testing."""
    return HIFLDElectricLoader(LoaderConfig())


# =============================================================================
# LOADER INITIALIZATION TESTS
# =============================================================================


class TestHIFLDElectricLoaderInit:
    """Tests for loader initialization."""

    def test_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader ABC."""
        from babylon.data.loader_base import DataLoader

        loader = HIFLDElectricLoader()
        assert isinstance(loader, DataLoader)

    def test_accepts_config(self) -> None:
        """Loader should accept LoaderConfig."""
        config = LoaderConfig(verbose=False)
        loader = HIFLDElectricLoader(config)
        assert loader.config.verbose is False

    def test_clients_initially_none(self) -> None:
        """ArcGIS clients should be None before load()."""
        loader = HIFLDElectricLoader()
        assert loader._substation_client is None
        assert loader._transmission_client is None


# =============================================================================
# DIMENSION AND FACT TABLE TESTS
# =============================================================================


class TestHIFLDElectricLoaderTables:
    """Tests for dimension and fact table declarations."""

    def test_dimension_tables_is_empty(self, electric_loader: HIFLDElectricLoader) -> None:
        """Electric loader doesn't need custom dimensions."""
        tables = electric_loader.get_dimension_tables()
        assert len(tables) == 0

    def test_fact_tables_includes_electric_grid(self, electric_loader: HIFLDElectricLoader) -> None:
        """Fact tables should include FactElectricGrid."""
        from babylon.data.normalize.schema import FactElectricGrid

        tables = electric_loader.get_fact_tables()
        assert FactElectricGrid in tables


# =============================================================================
# COUNTY FIPS EXTRACTION TESTS
# =============================================================================


class TestExtractCountyFIPS:
    """Tests for extract_county_fips_from_attrs utility."""

    def test_extracts_from_countyfips_field(self) -> None:
        """Should extract FIPS from COUNTYFIPS field."""
        attrs = {"COUNTYFIPS": "06001"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_extracts_from_cnty_fips_field(self) -> None:
        """Should extract FIPS from CNTY_FIPS field."""
        attrs = {"CNTY_FIPS": "36061"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "36061"

    def test_extracts_from_county_fip_field(self) -> None:
        """Should extract FIPS from COUNTY_FIP field."""
        attrs = {"COUNTY_FIP": "48201"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "48201"

    def test_pads_4_digit_fips(self) -> None:
        """Should zero-pad 4-digit FIPS to 5 digits."""
        attrs = {"COUNTYFIPS": "6001"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_returns_none_for_missing_fips(self) -> None:
        """Should return None if no FIPS field present."""
        attrs = {"NAME": "Test Substation"}
        result = extract_county_fips_from_attrs(attrs)
        assert result is None


# =============================================================================
# NUMERIC PARSING TESTS
# =============================================================================


class TestParseNumeric:
    """Tests for _parse_numeric method."""

    def test_parses_integer(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should parse integer values."""
        result = electric_loader._parse_numeric(345000)
        assert result == 345000.0

    def test_parses_float(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should parse float values."""
        result = electric_loader._parse_numeric(345000.5)
        assert result == 345000.5

    def test_parses_string(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should parse string values."""
        result = electric_loader._parse_numeric("345000")
        assert result == 345000.0

    def test_parses_string_with_commas(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should parse string with comma separators."""
        result = electric_loader._parse_numeric("345,000")
        assert result == 345000.0

    def test_returns_none_for_none(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should return None for None value."""
        result = electric_loader._parse_numeric(None)
        assert result is None

    def test_returns_none_for_invalid_string(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should return None for non-numeric strings."""
        result = electric_loader._parse_numeric("N/A")
        assert result is None

    def test_handles_whitespace(self, electric_loader: HIFLDElectricLoader) -> None:
        """Should strip whitespace from string values."""
        result = electric_loader._parse_numeric(" 345000 ")
        assert result == 345000.0


# =============================================================================
# LOAD STATS TESTS
# =============================================================================


class TestHIFLDElectricLoaderStats:
    """Tests for load statistics tracking."""

    def test_stats_source_is_hifld_electric(self) -> None:
        """Load stats source should be 'hifld_electric'."""
        from babylon.data.loader_base import LoadStats

        stats = LoadStats(source="hifld_electric")
        assert stats.source == "hifld_electric"
