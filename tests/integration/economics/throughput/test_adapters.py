"""Integration tests for SQLite data source adapters.

These tests verify the adapters correctly query the 3NF database
and return properly formatted data for throughput position calculations.

Tests use real data from marxist-data-3NF.sqlite loaded via:
    mise run data:bea-county
    mise run data:qcew

Feature: 014-throughput-position

Note: These tests are marked as integration tests since they require
      the actual database to be populated with data.
"""

from __future__ import annotations

import pytest

from babylon.economics.throughput.adapters import (
    NAICS_2DIGIT_SECTORS,
    SQLiteBEACountyGDPSource,
    SQLiteQCEWCountyNAICSSource,
    _sector_codes_for,
)
from babylon.reference.database import get_normalized_session_factory
from babylon.reference.schema import DimIndustry

# Mark all tests in this module as integration tests (require actual database)
pytestmark = pytest.mark.integration

# Test constants - validated values from data exploration
WAYNE_FIPS = "26163"  # Wayne County, MI (Detroit)
OAKLAND_FIPS = "26125"  # Oakland County, MI (Detroit suburbs)
MANHATTAN_FIPS = "36061"  # New York County, NY (Manhattan)
TEST_YEAR = 2022

# Known legitimately-zero (fips, sector, year) combo: a real imputed leaf
# (is_imputed=1) with SUM(employment)=0 for Bullock County, AL / NAICS 21
# (Mining) / 2024 — used to guard the 0-vs-None distinction (spec-098 fix).
ZERO_EMP_FIPS = "01011"
ZERO_EMP_SECTOR = "21"
ZERO_EMP_YEAR = 2024

# Expected values (approximate, with tolerance)
WAYNE_GDP_2022 = 113_826_760_000  # ~$113.8B
OAKLAND_GDP_2022 = 127_676_400_000  # ~$127.7B
WAYNE_EMP_2022 = 714_597
OAKLAND_EMP_2022 = 717_269

# Tolerance for GDP comparisons (1% due to data updates)
GDP_TOLERANCE = 0.01
EMP_TOLERANCE = 0.01


@pytest.fixture(scope="module")
def session_factory():
    """Get the normalized database session factory."""
    return get_normalized_session_factory()


@pytest.fixture(scope="module")
def bea_source(session_factory):
    """Create BEA county GDP source adapter."""
    return SQLiteBEACountyGDPSource(session_factory)


@pytest.fixture(scope="module")
def qcew_source(session_factory):
    """Create QCEW county NAICS source adapter."""
    return SQLiteQCEWCountyNAICSSource(session_factory)


class TestSQLiteBEACountyGDPSource:
    """Tests for SQLiteBEACountyGDPSource adapter."""

    def test_get_county_gdp_wayne_county(self, bea_source: SQLiteBEACountyGDPSource):
        """Test retrieving Wayne County (Detroit) GDP for 2022."""
        gdp = bea_source.get_county_gdp(WAYNE_FIPS, TEST_YEAR)

        assert gdp is not None, "Wayne County GDP should be available for 2022"
        assert isinstance(gdp, float), "GDP should be a float"
        assert gdp > 0, "GDP should be positive"

        # Check within tolerance of expected value
        relative_error = abs(gdp - WAYNE_GDP_2022) / WAYNE_GDP_2022
        assert relative_error < GDP_TOLERANCE, (
            f"Wayne GDP {gdp:,.0f} differs from expected {WAYNE_GDP_2022:,.0f} "
            f"by {relative_error:.2%}"
        )

    def test_get_county_gdp_oakland_county(self, bea_source: SQLiteBEACountyGDPSource):
        """Test retrieving Oakland County GDP for 2022."""
        gdp = bea_source.get_county_gdp(OAKLAND_FIPS, TEST_YEAR)

        assert gdp is not None, "Oakland County GDP should be available for 2022"

        # Check within tolerance of expected value
        relative_error = abs(gdp - OAKLAND_GDP_2022) / OAKLAND_GDP_2022
        assert relative_error < GDP_TOLERANCE, (
            f"Oakland GDP {gdp:,.0f} differs from expected {OAKLAND_GDP_2022:,.0f} "
            f"by {relative_error:.2%}"
        )

    def test_oakland_gdp_greater_than_wayne(self, bea_source: SQLiteBEACountyGDPSource):
        """Verify Oakland County has higher GDP than Wayne County (2022)."""
        wayne_gdp = bea_source.get_county_gdp(WAYNE_FIPS, TEST_YEAR)
        oakland_gdp = bea_source.get_county_gdp(OAKLAND_FIPS, TEST_YEAR)

        assert wayne_gdp is not None and oakland_gdp is not None
        assert oakland_gdp > wayne_gdp, (
            f"Oakland GDP ({oakland_gdp:,.0f}) should exceed Wayne GDP ({wayne_gdp:,.0f})"
        )

    def test_get_county_gdp_unknown_fips_returns_none(self, bea_source: SQLiteBEACountyGDPSource):
        """Test that unknown FIPS code returns None."""
        gdp = bea_source.get_county_gdp("99999", TEST_YEAR)
        assert gdp is None, "Unknown FIPS should return None"

    def test_get_county_gdp_invalid_year_returns_none(self, bea_source: SQLiteBEACountyGDPSource):
        """Test that invalid year returns None."""
        gdp = bea_source.get_county_gdp(WAYNE_FIPS, 1900)
        assert gdp is None, "Year before data range should return None"

    def test_get_all_counties_returns_dict(self, bea_source: SQLiteBEACountyGDPSource):
        """Test get_all_counties returns a dictionary of FIPS to GDP."""
        counties = bea_source.get_all_counties(TEST_YEAR)

        assert isinstance(counties, dict), "Should return a dict"
        assert len(counties) > 3000, f"Expected 3000+ counties, got {len(counties)}"

        # Verify known counties are present
        assert WAYNE_FIPS in counties, "Wayne County should be in results"
        assert OAKLAND_FIPS in counties, "Oakland County should be in results"

        # Values should be positive
        for fips, gdp in counties.items():
            assert gdp > 0, f"GDP for {fips} should be positive"

    def test_gdp_values_in_dollars_not_millions(self, bea_source: SQLiteBEACountyGDPSource):
        """Verify GDP values are converted from millions to dollars."""
        gdp = bea_source.get_county_gdp(WAYNE_FIPS, TEST_YEAR)

        # Wayne County GDP is ~$113B, so should be > 100 billion
        assert gdp is not None
        assert gdp > 100_000_000_000, (
            f"GDP {gdp:,.0f} seems too small - should be in dollars, not millions"
        )


class TestSQLiteQCEWCountyNAICSSource:
    """Tests for SQLiteQCEWCountyNAICSSource adapter."""

    def test_get_county_total_employment_wayne(self, qcew_source: SQLiteQCEWCountyNAICSSource):
        """Test retrieving Wayne County total employment for 2022."""
        emp = qcew_source.get_county_total_employment(WAYNE_FIPS, TEST_YEAR)

        assert emp is not None, "Wayne County employment should be available"
        assert isinstance(emp, int), "Employment should be an integer"
        assert emp > 0, "Employment should be positive"

        # Check within tolerance of expected value
        relative_error = abs(emp - WAYNE_EMP_2022) / WAYNE_EMP_2022
        assert relative_error < EMP_TOLERANCE, (
            f"Wayne employment {emp:,} differs from expected {WAYNE_EMP_2022:,} "
            f"by {relative_error:.2%}"
        )

    def test_get_county_total_employment_oakland(self, qcew_source: SQLiteQCEWCountyNAICSSource):
        """Test retrieving Oakland County total employment for 2022."""
        emp = qcew_source.get_county_total_employment(OAKLAND_FIPS, TEST_YEAR)

        assert emp is not None, "Oakland County employment should be available"

        relative_error = abs(emp - OAKLAND_EMP_2022) / OAKLAND_EMP_2022
        assert relative_error < EMP_TOLERANCE, (
            f"Oakland employment {emp:,} differs from expected {OAKLAND_EMP_2022:,} "
            f"by {relative_error:.2%}"
        )

    def test_get_county_total_employment_unknown_fips_returns_none(
        self, qcew_source: SQLiteQCEWCountyNAICSSource
    ):
        """Test that unknown FIPS code returns None."""
        emp = qcew_source.get_county_total_employment("99999", TEST_YEAR)
        assert emp is None, "Unknown FIPS should return None"

    def test_get_county_naics_employment_finance(self, qcew_source: SQLiteQCEWCountyNAICSSource):
        """Test retrieving finance sector (NAICS 52) employment."""
        emp = qcew_source.get_county_naics_employment(WAYNE_FIPS, "52", TEST_YEAR)

        # Finance employment may be suppressed in some counties, but Wayne should have it
        assert emp is not None, "Wayne County finance employment should be available"
        assert emp > 0, "Finance employment should be positive"
        assert emp < 200_000, "Finance employment should be reasonable (not total)"

    def test_get_county_naics_employment_unknown_naics_returns_none(
        self, qcew_source: SQLiteQCEWCountyNAICSSource
    ):
        """Test that unknown NAICS code returns None."""
        emp = qcew_source.get_county_naics_employment(WAYNE_FIPS, "XX", TEST_YEAR)
        assert emp is None, "Unknown NAICS should return None"

    def test_get_county_naics_employment_real_zero_is_not_none(
        self, qcew_source: SQLiteQCEWCountyNAICSSource
    ):
        """A confirmed SUM(employment)=0 leaf must return 0, not None.

        Regression guard (spec-098 fix): a truthy check (``if total else
        None``) silently conflated a real zero with "no data". Bullock
        County, AL (01011) NAICS 21 (Mining) in 2024 has a real imputed
        leaf with employment=0 — that is DATA, not unavailability, per the
        ``QCEWCountyNAICSSource`` protocol contract.
        """
        emp = qcew_source.get_county_naics_employment(ZERO_EMP_FIPS, ZERO_EMP_SECTOR, ZERO_EMP_YEAR)
        assert emp == 0, (
            f"Expected a confirmed zero (0), got {emp!r} — 0-vs-None conflation regression"
        )

    def test_get_county_employment_by_naics_returns_sectors(
        self, qcew_source: SQLiteQCEWCountyNAICSSource
    ):
        """Test getting employment breakdown by NAICS sector."""
        sectors = qcew_source.get_county_employment_by_naics(WAYNE_FIPS, TEST_YEAR)

        assert isinstance(sectors, dict), "Should return a dict"
        assert len(sectors) > 0, "Should have at least some sectors"

        # Check some expected sectors are present
        # (some may be suppressed, so we check a subset)
        found_sectors = set(sectors.keys())
        expected_sectors = {"52", "62", "44-45"}  # Finance, Healthcare, Retail

        # At least one of these common sectors should be present
        assert found_sectors & expected_sectors, (
            f"Expected at least one of {expected_sectors} in {found_sectors}"
        )

        # All values should be positive integers
        for naics, emp in sectors.items():
            assert isinstance(emp, int), f"Employment for {naics} should be int"
            assert emp > 0, f"Employment for {naics} should be positive"

    def test_get_county_employment_by_naics_includes_confirmed_zero_sector(
        self, qcew_source: SQLiteQCEWCountyNAICSSource
    ):
        """A confirmed-zero sector must appear in the dict with value 0.

        Regression guard (spec-098 fix): a truthy check (``if emp:``)
        silently dropped confirmed-zero sectors from the result, which
        undercounts ``get_sector_coverage()``'s ``sectors_with_data`` /
        ``employment_covered`` metrics downstream.
        """
        sectors = qcew_source.get_county_employment_by_naics(ZERO_EMP_FIPS, ZERO_EMP_YEAR)

        assert ZERO_EMP_SECTOR in sectors, (
            f"Confirmed-zero sector {ZERO_EMP_SECTOR!r} was dropped from {sectors!r}"
        )
        assert sectors[ZERO_EMP_SECTOR] == 0

    def test_get_county_naics_wages_returns_weekly(self, qcew_source: SQLiteQCEWCountyNAICSSource):
        """Test retrieving average weekly wages for a sector."""
        wages = qcew_source.get_county_naics_wages(WAYNE_FIPS, "52", TEST_YEAR)

        # Finance wages should be available
        assert wages is not None, "Wayne County finance wages should be available"
        assert isinstance(wages, float), "Wages should be a float"

        # Weekly wages should be in reasonable range (not annual)
        assert 500 < wages < 10_000, (
            f"Weekly wage {wages:.0f} seems wrong - expected 500-10000 $/week"
        )


class TestNAICS2DigitSectors:
    """Tests for NAICS sector constant."""

    def test_naics_sectors_count(self):
        """Verify we have 20 2-digit NAICS sectors defined."""
        assert len(NAICS_2DIGIT_SECTORS) == 20

    def test_naics_sectors_includes_major_sectors(self):
        """Verify major sectors are included."""
        expected = ["11", "21", "52", "62", "72", "92"]
        for sector in expected:
            assert sector in NAICS_2DIGIT_SECTORS, f"Missing sector {sector}"

    def test_sector_codes_for_map_to_real_dim_industry_rows(self, session_factory):
        """Guard ``_sector_codes_for``'s mapping against DB drift.

        The unit tests in ``test_adapters_sector_expansion.py`` only restate
        the function's own hardcoded ``ranges`` dict. This integration test
        additionally verifies each expanded sector_code actually exists in
        ``dim_industry`` for every adapter label, so a future reference-DB
        rebuild that drops/renames a sector_code would be caught here.
        """
        with session_factory() as session:
            existing_codes = {
                row[0] for row in session.query(DimIndustry.sector_code).distinct().all()
            }

        for label in NAICS_2DIGIT_SECTORS:
            for code in _sector_codes_for(label):
                assert code in existing_codes, (
                    f"{label} -> {code} does not exist in dim_industry.sector_code"
                )


class TestThroughputPositionValidation:
    """Integration tests validating throughput position calculation inputs."""

    def test_detroit_validation_data_available(
        self,
        bea_source: SQLiteBEACountyGDPSource,
        qcew_source: SQLiteQCEWCountyNAICSSource,
    ):
        """Verify data needed for Detroit metro validation is available."""
        # GDP data
        wayne_gdp = bea_source.get_county_gdp(WAYNE_FIPS, TEST_YEAR)
        oakland_gdp = bea_source.get_county_gdp(OAKLAND_FIPS, TEST_YEAR)

        assert wayne_gdp is not None, "Wayne GDP required for validation"
        assert oakland_gdp is not None, "Oakland GDP required for validation"

        # Employment data
        wayne_emp = qcew_source.get_county_total_employment(WAYNE_FIPS, TEST_YEAR)
        oakland_emp = qcew_source.get_county_total_employment(OAKLAND_FIPS, TEST_YEAR)

        assert wayne_emp is not None, "Wayne employment required for validation"
        assert oakland_emp is not None, "Oakland employment required for validation"

    def test_compute_throughput_intensity_manually(
        self,
        bea_source: SQLiteBEACountyGDPSource,
        qcew_source: SQLiteQCEWCountyNAICSSource,
    ):
        """Manually compute τ_through to validate data consistency."""
        hours_per_year = 2080

        # Wayne County
        wayne_gdp = bea_source.get_county_gdp(WAYNE_FIPS, TEST_YEAR)
        wayne_emp = qcew_source.get_county_total_employment(WAYNE_FIPS, TEST_YEAR)

        assert wayne_gdp is not None and wayne_emp is not None
        wayne_tau = wayne_gdp / (wayne_emp * hours_per_year)

        # Oakland County
        oakland_gdp = bea_source.get_county_gdp(OAKLAND_FIPS, TEST_YEAR)
        oakland_emp = qcew_source.get_county_total_employment(OAKLAND_FIPS, TEST_YEAR)

        assert oakland_gdp is not None and oakland_emp is not None
        oakland_tau = oakland_gdp / (oakland_emp * hours_per_year)

        # Sanity checks per FR-008: τ_through should be $10-500/hour
        assert 10 < wayne_tau < 500, f"Wayne τ={wayne_tau:.2f} outside sanity range"
        assert 10 < oakland_tau < 500, f"Oakland τ={oakland_tau:.2f} outside sanity range"

        # Oakland should have higher throughput than Wayne
        assert oakland_tau > wayne_tau, (
            f"Oakland τ ({oakland_tau:.2f}) should exceed Wayne τ ({wayne_tau:.2f})"
        )

        # Log the values for reference
        print(f"\nWayne County τ_through: ${wayne_tau:.2f}/hour")
        print(f"Oakland County τ_through: ${oakland_tau:.2f}/hour")
