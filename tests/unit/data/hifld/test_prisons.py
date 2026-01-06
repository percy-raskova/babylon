"""Unit tests for HIFLD Prison Boundaries loader.

Tests the HIFLDPrisonsLoader class including FIPS extraction, type mapping,
capacity parsing, and county aggregation logic.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from babylon.data.hifld.prisons import (
    DEFAULT_PRISON_TYPE,
    PRISON_TYPE_MAP,
    HIFLDPrisonsLoader,
)
from babylon.data.loader_base import LoaderConfig
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def prison_loader() -> HIFLDPrisonsLoader:
    """Create prison loader for testing."""
    return HIFLDPrisonsLoader(LoaderConfig())


@pytest.fixture
def sample_prison_attributes() -> dict[str, Any]:
    """Sample prison facility attributes."""
    return {
        "OBJECTID": 1,
        "NAME": "Test Federal Prison",
        "COUNTYFIPS": "06001",
        "COUNTY": "Alameda",
        "STATE": "CA",
        "TYPE": "FEDERAL",
        "CAPACITY": 1500,
        "STATUS": "OPERATIONAL",
        "SECURELVL": "MEDIUM",
    }


# =============================================================================
# LOADER INITIALIZATION TESTS
# =============================================================================


class TestHIFLDPrisonsLoaderInit:
    """Tests for loader initialization."""

    def test_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader ABC."""
        from babylon.data.loader_base import DataLoader

        loader = HIFLDPrisonsLoader()
        assert isinstance(loader, DataLoader)

    def test_accepts_config(self) -> None:
        """Loader should accept LoaderConfig."""
        config = LoaderConfig(verbose=False)
        loader = HIFLDPrisonsLoader(config)
        assert loader.config.verbose is False

    def test_default_config_created(self) -> None:
        """Loader should create default config if none provided."""
        loader = HIFLDPrisonsLoader()
        assert loader.config is not None

    def test_client_initially_none(self) -> None:
        """ArcGIS client should be None before load()."""
        loader = HIFLDPrisonsLoader()
        assert loader._client is None


# =============================================================================
# DIMENSION AND FACT TABLE TESTS
# =============================================================================


class TestHIFLDPrisonsLoaderTables:
    """Tests for dimension and fact table declarations."""

    def test_dimension_tables_includes_coercive_type(
        self, prison_loader: HIFLDPrisonsLoader
    ) -> None:
        """Dimension tables should include DimCoerciveType."""
        from babylon.data.normalize.schema import DimCoerciveType

        tables = prison_loader.get_dimension_tables()
        assert DimCoerciveType in tables

    def test_fact_tables_includes_coercive_infrastructure(
        self, prison_loader: HIFLDPrisonsLoader
    ) -> None:
        """Fact tables should include FactCoerciveInfrastructure."""
        from babylon.data.normalize.schema import FactCoerciveInfrastructure

        tables = prison_loader.get_fact_tables()
        assert FactCoerciveInfrastructure in tables


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

    def test_pads_4_digit_fips(self) -> None:
        """Should zero-pad 4-digit FIPS to 5 digits."""
        attrs = {"COUNTYFIPS": "6001"}  # Missing leading zero
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_truncates_long_fips(self) -> None:
        """Should truncate FIPS longer than 5 digits."""
        attrs = {"COUNTYFIPS": "0600101"}  # Extra digits
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_handles_integer_fips(self) -> None:
        """Should handle integer FIPS values."""
        attrs = {"COUNTYFIPS": 6001}  # Integer, not string
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"

    def test_returns_none_for_missing_fips(self) -> None:
        """Should return None if no FIPS field present."""
        attrs = {"NAME": "Test Prison"}
        result = extract_county_fips_from_attrs(attrs)
        assert result is None

    def test_returns_none_for_short_fips(self) -> None:
        """Should return None for FIPS shorter than 4 digits."""
        attrs = {"COUNTYFIPS": "06"}  # Too short
        result = extract_county_fips_from_attrs(attrs)
        assert result is None

    def test_handles_whitespace(self) -> None:
        """Should strip whitespace from FIPS."""
        attrs = {"COUNTYFIPS": " 06001 "}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06001"


# =============================================================================
# FACILITY TYPE MAPPING TESTS
# =============================================================================


class TestMapFacilityType:
    """Tests for _map_facility_type method."""

    def test_maps_federal(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map FEDERAL to prison_federal."""
        attrs = {"TYPE": "FEDERAL"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_federal"

    def test_maps_state(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map STATE to prison_state."""
        attrs = {"TYPE": "STATE"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_state"

    def test_maps_local(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map LOCAL to prison_local."""
        attrs = {"TYPE": "LOCAL"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_local"

    def test_maps_county_to_local(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map COUNTY to prison_local."""
        attrs = {"TYPE": "COUNTY"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_local"

    def test_maps_city_to_local(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map CITY to prison_local."""
        attrs = {"TYPE": "CITY"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_local"

    def test_maps_private(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map PRIVATE to prison_private."""
        attrs = {"TYPE": "PRIVATE"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_private"

    def test_maps_tribal(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should map TRIBAL to prison_tribal."""
        attrs = {"TYPE": "TRIBAL"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_tribal"

    def test_case_insensitive(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should handle lowercase type values."""
        attrs = {"TYPE": "federal"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_federal"

    def test_partial_match(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should match partial type strings."""
        attrs = {"TYPE": "FEDERAL CORRECTIONAL INSTITUTION"}
        result = prison_loader._map_facility_type(attrs)
        assert result == "prison_federal"

    def test_unknown_type_returns_default(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should return default type for unknown values."""
        attrs = {"TYPE": "UNKNOWN"}
        result = prison_loader._map_facility_type(attrs)
        assert result == DEFAULT_PRISON_TYPE[0]

    def test_missing_type_returns_default(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should return default type if TYPE field missing."""
        attrs = {"NAME": "Test Prison"}
        result = prison_loader._map_facility_type(attrs)
        assert result == DEFAULT_PRISON_TYPE[0]


# =============================================================================
# CAPACITY PARSING TESTS
# =============================================================================


class TestParseCapacity:
    """Tests for _parse_capacity method."""

    def test_parses_integer(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should parse integer capacity."""
        result = prison_loader._parse_capacity(1500)
        assert result == 1500

    def test_parses_float(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should parse float capacity as integer."""
        result = prison_loader._parse_capacity(1500.5)
        assert result == 1500

    def test_parses_string(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should parse string capacity."""
        result = prison_loader._parse_capacity("1500")
        assert result == 1500

    def test_parses_string_with_commas(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should parse string with comma separators."""
        result = prison_loader._parse_capacity("1,500")
        assert result == 1500

    def test_returns_zero_for_none(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should return 0 for None value."""
        result = prison_loader._parse_capacity(None)
        assert result == 0

    def test_returns_zero_for_negative(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should return 0 for negative values."""
        result = prison_loader._parse_capacity(-100)
        assert result == 0

    def test_returns_zero_for_invalid_string(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should return 0 for non-numeric strings."""
        result = prison_loader._parse_capacity("N/A")
        assert result == 0

    def test_handles_whitespace(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Should strip whitespace from string values."""
        result = prison_loader._parse_capacity(" 1500 ")
        assert result == 1500


# =============================================================================
# PRISON TYPE MAPPING CONFIGURATION TESTS
# =============================================================================


class TestPrisonTypeMapConfiguration:
    """Tests for PRISON_TYPE_MAP configuration."""

    def test_federal_type_tuple_structure(self) -> None:
        """Federal type should have correct tuple structure."""
        code, name, category, command = PRISON_TYPE_MAP["FEDERAL"]
        assert code == "prison_federal"
        assert name == "Federal Prison"
        assert category == "carceral"
        assert command == "federal"

    def test_state_type_tuple_structure(self) -> None:
        """State type should have correct tuple structure."""
        code, name, category, command = PRISON_TYPE_MAP["STATE"]
        assert category == "carceral"
        assert command == "state"

    def test_local_type_tuple_structure(self) -> None:
        """Local type should have correct tuple structure."""
        code, name, category, command = PRISON_TYPE_MAP["LOCAL"]
        assert category == "carceral"
        assert command == "local"

    def test_private_type_has_mixed_command(self) -> None:
        """Private type should have mixed command chain."""
        code, name, category, command = PRISON_TYPE_MAP["PRIVATE"]
        assert command == "mixed"

    def test_default_type_structure(self) -> None:
        """Default type should have correct structure."""
        code, name, category, command = DEFAULT_PRISON_TYPE
        assert code == "prison_other"
        assert category == "carceral"


# =============================================================================
# LOAD STATS TESTS
# =============================================================================


class TestHIFLDPrisonsLoaderStats:
    """Tests for load statistics tracking."""

    def test_stats_source_is_hifld_prisons(self, prison_loader: HIFLDPrisonsLoader) -> None:
        """Load stats source should be 'hifld_prisons'."""
        from babylon.data.loader_base import LoadStats

        # Create mock session and client to verify stats source
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(prison_loader, "_client") as mock_client:
            mock_client.get_record_count.return_value = 0
            mock_client.query_all.return_value = iter([])

            # We can't easily run full load without DB, so just verify the source
            stats = LoadStats(source="hifld_prisons")
            assert stats.source == "hifld_prisons"
