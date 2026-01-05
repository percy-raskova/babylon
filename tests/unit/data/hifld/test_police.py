"""Unit tests for HIFLD Local Law Enforcement loader.

Tests the HIFLDPoliceLoader class including FIPS extraction, type mapping,
and county aggregation logic.
"""

from __future__ import annotations

import pytest

from babylon.data.hifld.police import (
    DEFAULT_POLICE_TYPE,
    POLICE_TYPE_MAP,
    HIFLDPoliceLoader,
)
from babylon.data.loader_base import LoaderConfig

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def police_loader() -> HIFLDPoliceLoader:
    """Create police loader for testing."""
    return HIFLDPoliceLoader(LoaderConfig())


# =============================================================================
# LOADER INITIALIZATION TESTS
# =============================================================================


class TestHIFLDPoliceLoaderInit:
    """Tests for loader initialization."""

    def test_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader ABC."""
        from babylon.data.loader_base import DataLoader

        loader = HIFLDPoliceLoader()
        assert isinstance(loader, DataLoader)

    def test_accepts_config(self) -> None:
        """Loader should accept LoaderConfig."""
        config = LoaderConfig(verbose=False)
        loader = HIFLDPoliceLoader(config)
        assert loader.config.verbose is False

    def test_client_initially_none(self) -> None:
        """ArcGIS client should be None before load()."""
        loader = HIFLDPoliceLoader()
        assert loader._client is None


# =============================================================================
# DIMENSION AND FACT TABLE TESTS
# =============================================================================


class TestHIFLDPoliceLoaderTables:
    """Tests for dimension and fact table declarations."""

    def test_dimension_tables_includes_coercive_type(
        self, police_loader: HIFLDPoliceLoader
    ) -> None:
        """Dimension tables should include DimCoerciveType."""
        from babylon.data.normalize.schema import DimCoerciveType

        tables = police_loader.get_dimension_tables()
        assert DimCoerciveType in tables

    def test_fact_tables_includes_coercive_infrastructure(
        self, police_loader: HIFLDPoliceLoader
    ) -> None:
        """Fact tables should include FactCoerciveInfrastructure."""
        from babylon.data.normalize.schema import FactCoerciveInfrastructure

        tables = police_loader.get_fact_tables()
        assert FactCoerciveInfrastructure in tables


# =============================================================================
# COUNTY FIPS EXTRACTION TESTS
# =============================================================================


class TestExtractCountyFIPS:
    """Tests for _extract_county_fips method."""

    def test_extracts_from_countyfips_field(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should extract FIPS from COUNTYFIPS field."""
        attrs = {"COUNTYFIPS": "06001"}
        result = police_loader._extract_county_fips(attrs)
        assert result == "06001"

    def test_extracts_from_cnty_fips_field(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should extract FIPS from CNTY_FIPS field."""
        attrs = {"CNTY_FIPS": "36061"}
        result = police_loader._extract_county_fips(attrs)
        assert result == "36061"

    def test_pads_4_digit_fips(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should zero-pad 4-digit FIPS to 5 digits."""
        attrs = {"COUNTYFIPS": "6001"}
        result = police_loader._extract_county_fips(attrs)
        assert result == "06001"

    def test_returns_none_for_missing_fips(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should return None if no FIPS field present."""
        attrs = {"NAME": "Test Police Dept"}
        result = police_loader._extract_county_fips(attrs)
        assert result is None


# =============================================================================
# FACILITY TYPE MAPPING TESTS
# =============================================================================


class TestMapFacilityType:
    """Tests for _map_facility_type method."""

    def test_maps_police_department(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map POLICE DEPARTMENT to police_local."""
        attrs = {"TYPE": "POLICE DEPARTMENT"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_local"

    def test_maps_sheriff(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map SHERIFF to police_sheriff."""
        attrs = {"TYPE": "SHERIFF"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_sheriff"

    def test_maps_campus_police(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map CAMPUS POLICE to police_campus."""
        attrs = {"TYPE": "CAMPUS POLICE"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_campus"

    def test_maps_transit_police(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map TRANSIT POLICE to police_transit."""
        attrs = {"TYPE": "TRANSIT POLICE"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_transit"

    def test_maps_constable(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map CONSTABLE to police_constable."""
        attrs = {"TYPE": "CONSTABLE"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_constable"

    def test_maps_marshal(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map MARSHAL to police_marshal."""
        attrs = {"TYPE": "MARSHAL"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_marshal"

    def test_maps_tribal_police(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should map TRIBAL POLICE to police_tribal."""
        attrs = {"TYPE": "TRIBAL POLICE"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_tribal"

    def test_case_insensitive(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should handle lowercase type values."""
        attrs = {"TYPE": "sheriff"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_sheriff"

    def test_sheriff_from_name_field(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should detect SHERIFF from NAME field if TYPE unknown."""
        attrs = {"TYPE": "OTHER", "NAME": "Los Angeles County Sheriff"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_sheriff"

    def test_campus_from_name_field(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should detect CAMPUS from NAME field if TYPE unknown."""
        attrs = {"TYPE": "OTHER", "NAME": "UCLA Campus Police"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_campus"

    def test_university_from_name_field(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should detect UNIVERSITY from NAME field as campus police."""
        attrs = {"TYPE": "OTHER", "NAME": "University of California Police"}
        result = police_loader._map_facility_type(attrs)
        assert result == "police_campus"

    def test_unknown_type_returns_default(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should return default type for unknown values."""
        attrs = {"TYPE": "UNKNOWN", "NAME": "Test Agency"}
        result = police_loader._map_facility_type(attrs)
        assert result == DEFAULT_POLICE_TYPE[0]

    def test_missing_type_returns_default(self, police_loader: HIFLDPoliceLoader) -> None:
        """Should return default type if TYPE field missing."""
        attrs = {"NAME": "Test Police"}
        result = police_loader._map_facility_type(attrs)
        assert result == DEFAULT_POLICE_TYPE[0]


# =============================================================================
# POLICE TYPE MAPPING CONFIGURATION TESTS
# =============================================================================


class TestPoliceTypeMapConfiguration:
    """Tests for POLICE_TYPE_MAP configuration."""

    def test_police_department_type_structure(self) -> None:
        """Police department type should have correct structure."""
        code, name, category, command = POLICE_TYPE_MAP["POLICE DEPARTMENT"]
        assert code == "police_local"
        assert name == "Local Police Department"
        assert category == "enforcement"
        assert command == "local"

    def test_sheriff_type_structure(self) -> None:
        """Sheriff type should have correct structure."""
        code, name, category, command = POLICE_TYPE_MAP["SHERIFF"]
        assert code == "police_sheriff"
        assert category == "enforcement"
        assert command == "local"

    def test_tribal_police_has_federal_command(self) -> None:
        """Tribal police should have federal command chain."""
        code, name, category, command = POLICE_TYPE_MAP["TRIBAL POLICE"]
        assert command == "federal"

    def test_default_type_structure(self) -> None:
        """Default type should have correct structure."""
        code, name, category, command = DEFAULT_POLICE_TYPE
        assert code == "police_other"
        assert category == "enforcement"
        assert command == "local"

    def test_all_types_have_enforcement_category(self) -> None:
        """All police types should be enforcement category."""
        for type_info in POLICE_TYPE_MAP.values():
            code, name, category, command = type_info
            assert category == "enforcement"


# =============================================================================
# LOAD STATS TESTS
# =============================================================================


class TestHIFLDPoliceLoaderStats:
    """Tests for load statistics tracking."""

    def test_stats_source_is_hifld_police(self) -> None:
        """Load stats source should be 'hifld_police'."""
        from babylon.data.loader_base import LoadStats

        stats = LoadStats(source="hifld_police")
        assert stats.source == "hifld_police"
