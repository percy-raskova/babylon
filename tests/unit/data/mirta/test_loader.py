"""Unit tests for MIRTA Military Installations loader.

Tests the MIRTAMilitaryLoader class including FIPS extraction, service
branch mapping, and county aggregation logic.
"""

from __future__ import annotations

import pytest

from babylon.data.loader_base import LoaderConfig
from babylon.data.mirta.loader import (
    DEFAULT_MILITARY_TYPE,
    MILITARY_TYPE_MAP,
    MIRTAMilitaryLoader,
)
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def military_loader() -> MIRTAMilitaryLoader:
    """Create military loader for testing."""
    return MIRTAMilitaryLoader(LoaderConfig())


# =============================================================================
# LOADER INITIALIZATION TESTS
# =============================================================================


class TestMIRTAMilitaryLoaderInit:
    """Tests for loader initialization."""

    def test_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader ABC."""
        from babylon.data.loader_base import DataLoader

        loader = MIRTAMilitaryLoader()
        assert isinstance(loader, DataLoader)

    def test_accepts_config(self) -> None:
        """Loader should accept LoaderConfig."""
        config = LoaderConfig(verbose=False)
        loader = MIRTAMilitaryLoader(config)
        assert loader.config.verbose is False

    def test_client_initially_none(self) -> None:
        """ArcGIS client should be None before load()."""
        loader = MIRTAMilitaryLoader()
        assert loader._client is None


# =============================================================================
# DIMENSION AND FACT TABLE TESTS
# =============================================================================


class TestMIRTAMilitaryLoaderTables:
    """Tests for dimension and fact table declarations."""

    def test_dimension_tables_includes_coercive_type(
        self, military_loader: MIRTAMilitaryLoader
    ) -> None:
        """Dimension tables should include DimCoerciveType."""
        from babylon.data.normalize.schema import DimCoerciveType

        tables = military_loader.get_dimension_tables()
        assert DimCoerciveType in tables

    def test_fact_tables_includes_coercive_infrastructure(
        self, military_loader: MIRTAMilitaryLoader
    ) -> None:
        """Fact tables should include FactCoerciveInfrastructure."""
        from babylon.data.normalize.schema import FactCoerciveInfrastructure

        tables = military_loader.get_fact_tables()
        assert FactCoerciveInfrastructure in tables


# =============================================================================
# COUNTY FIPS EXTRACTION TESTS
# =============================================================================


class TestExtractCountyFIPS:
    """Tests for extract_county_fips_from_attrs utility."""

    def test_extracts_from_countyfips_field(self) -> None:
        """Should extract FIPS from COUNTYFIPS field."""
        attrs = {"COUNTYFIPS": "06073"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06073"

    def test_extracts_from_cnty_fips_field(self) -> None:
        """Should extract FIPS from CNTY_FIPS field."""
        attrs = {"CNTY_FIPS": "51059"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "51059"

    def test_extracts_from_fips_field(self) -> None:
        """Should extract FIPS from FIPS field."""
        attrs = {"FIPS": "48029"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "48029"

    def test_constructs_from_state_and_county(self) -> None:
        """Should construct FIPS from STATE_FIPS and CNTY_FIPS_3."""
        attrs = {"STATE_FIPS": "06", "CNTY_FIPS_3": "073"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06073"

    def test_constructs_from_statefp_and_countyfp(self) -> None:
        """Should construct FIPS from STATEFP and COUNTYFP."""
        attrs = {"STATEFP": "48", "COUNTYFP": "029"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "48029"

    def test_pads_4_digit_fips(self) -> None:
        """Should zero-pad 4-digit FIPS to 5 digits."""
        attrs = {"COUNTYFIPS": "6073"}
        result = extract_county_fips_from_attrs(attrs)
        assert result == "06073"

    def test_returns_none_for_missing_fips(self) -> None:
        """Should return None if no FIPS field present."""
        attrs = {"SITE_NAME": "Test Base"}
        result = extract_county_fips_from_attrs(attrs)
        assert result is None


# =============================================================================
# SERVICE BRANCH MAPPING TESTS
# =============================================================================


class TestMapServiceBranch:
    """Tests for _map_service_branch method."""

    def test_maps_army(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map ARMY to military_army."""
        attrs = {"SERVICE": "ARMY"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_army"

    def test_maps_navy(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map NAVY to military_navy."""
        attrs = {"SERVICE": "NAVY"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_navy"

    def test_maps_air_force(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map AIR FORCE to military_air_force."""
        attrs = {"SERVICE": "AIR FORCE"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_air_force"

    def test_maps_marine_corps(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map MARINE CORPS to military_marines."""
        attrs = {"SERVICE": "MARINE CORPS"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_marines"

    def test_maps_coast_guard(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map COAST GUARD to military_coast_guard."""
        attrs = {"SERVICE": "COAST GUARD"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_coast_guard"

    def test_maps_space_force(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map SPACE FORCE to military_space_force."""
        attrs = {"SERVICE": "SPACE FORCE"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_space_force"

    def test_maps_national_guard(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map NATIONAL GUARD to military_guard."""
        attrs = {"SERVICE": "NATIONAL GUARD"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_guard"

    def test_maps_joint(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should map JOINT to military_joint."""
        attrs = {"SERVICE": "JOINT"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_joint"

    def test_reads_from_branch_field(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should read from BRANCH field if SERVICE missing."""
        attrs = {"BRANCH": "NAVY"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_navy"

    def test_reads_from_component_field(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should read from COMPONENT field if others missing."""
        attrs = {"COMPONENT": "AIR FORCE"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_air_force"

    def test_case_insensitive(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should handle lowercase service values."""
        attrs = {"SERVICE": "army"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_army"

    def test_air_force_from_site_name_afb(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should detect Air Force from AFB in site name."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "Edwards AFB"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_air_force"

    def test_navy_from_site_name_naval(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should detect Navy from NAVAL in site name."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "Naval Air Station Pensacola"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_navy"

    def test_navy_from_site_name_nas(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should detect Navy from NAS in site name."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "NAS Jacksonville"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_navy"

    def test_army_from_site_name_fort(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should detect Army from FORT in site name."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "Fort Bragg"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_army"

    def test_marines_from_site_name(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should detect Marines from MARINE in site name."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "Marine Corps Base Camp Pendleton"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_marines"

    def test_guard_from_site_name_armory(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should detect National Guard from ARMORY in site name."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "Springfield Armory"}
        result = military_loader._map_service_branch(attrs)
        assert result == "military_guard"

    def test_unknown_service_returns_default(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should return default type for unknown values."""
        attrs = {"SERVICE": "UNKNOWN", "SITE_NAME": "Test Site"}
        result = military_loader._map_service_branch(attrs)
        assert result == DEFAULT_MILITARY_TYPE[0]

    def test_missing_service_returns_default(self, military_loader: MIRTAMilitaryLoader) -> None:
        """Should return default type if SERVICE field missing."""
        attrs = {"SITE_NAME": "Test Base"}
        result = military_loader._map_service_branch(attrs)
        assert result == DEFAULT_MILITARY_TYPE[0]


# =============================================================================
# MILITARY TYPE MAPPING CONFIGURATION TESTS
# =============================================================================


class TestMilitaryTypeMapConfiguration:
    """Tests for MILITARY_TYPE_MAP configuration."""

    def test_army_type_structure(self) -> None:
        """Army type should have correct structure."""
        code, name, category, command = MILITARY_TYPE_MAP["ARMY"]
        assert code == "military_army"
        assert name == "Army Installation"
        assert category == "military"
        assert command == "federal"

    def test_navy_type_structure(self) -> None:
        """Navy type should have correct structure."""
        code, name, category, command = MILITARY_TYPE_MAP["NAVY"]
        assert code == "military_navy"
        assert category == "military"
        assert command == "federal"

    def test_air_force_type_structure(self) -> None:
        """Air Force type should have correct structure."""
        code, name, category, command = MILITARY_TYPE_MAP["AIR FORCE"]
        assert code == "military_air_force"
        assert category == "military"
        assert command == "federal"

    def test_default_type_structure(self) -> None:
        """Default type should have correct structure."""
        code, name, category, command = DEFAULT_MILITARY_TYPE
        assert code == "military_other"
        assert category == "military"
        assert command == "federal"

    def test_all_types_have_military_category(self) -> None:
        """All military types should be military category."""
        for type_info in MILITARY_TYPE_MAP.values():
            code, name, category, command = type_info
            assert category == "military"

    def test_all_types_have_federal_command(self) -> None:
        """All military types should have federal command chain."""
        for type_info in MILITARY_TYPE_MAP.values():
            code, name, category, command = type_info
            assert command == "federal"


# =============================================================================
# LOAD STATS TESTS
# =============================================================================


class TestMIRTAMilitaryLoaderStats:
    """Tests for load statistics tracking."""

    def test_stats_source_is_mirta_military(self) -> None:
        """Load stats source should be 'mirta_military'."""
        from babylon.data.loader_base import LoadStats

        stats = LoadStats(source="mirta_military")
        assert stats.source == "mirta_military"
