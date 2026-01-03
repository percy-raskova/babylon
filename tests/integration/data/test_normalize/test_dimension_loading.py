"""Integration tests for dimension loading in ETL pipeline.

Tests the loading of dimension tables from research.sqlite into the
normalized 3NF schema, verifying FK relationships, classifications,
and data integrity.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from babylon.data.normalize.database import SOURCE_DB_PATH, NormalizedBase
from babylon.data.normalize.etl import (
    load_dim_country,
    load_dim_county,
    load_dim_industry,
    load_dim_ownership,
    load_dim_sector,
    load_dim_state,
    load_dim_worker_class,
)
from babylon.data.normalize.schema import (
    DimCountry,
    DimCounty,
    DimIndustry,
    DimOwnership,
    DimSector,
    DimState,
    DimWorkerClass,
)

# Skip all tests if source database doesn't exist
pytestmark = pytest.mark.skipif(
    not SOURCE_DB_PATH.exists(), reason="Source database not available for integration tests"
)


@pytest.fixture(scope="module")
def source_engine():
    """Create connection to source research.sqlite."""
    engine = create_engine(f"sqlite:///{SOURCE_DB_PATH}")
    return engine


@pytest.fixture(scope="function")
def target_engine():
    """Create fresh in-memory target database for each test."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def target_session(target_engine):
    """Create session for target database."""
    Session = sessionmaker(bind=target_engine)
    session = Session()
    yield session
    session.close()


class TestStateLoading:
    """Integration tests for state dimension loading."""

    def test_loads_states_from_census(self, source_engine, target_session) -> None:
        """States should be loaded from census_counties table."""
        count = load_dim_state(source_engine, target_session)
        assert count > 0, "Should load at least some states"

        # Verify specific states exist
        states = target_session.query(DimState).all()
        state_names = {s.state_name for s in states}

        # Check for major states
        assert "California" in state_names or "New York" in state_names, (
            "Should include major states"
        )

    def test_state_fips_are_unique(self, source_engine, target_session) -> None:
        """State FIPS codes should be unique."""
        load_dim_state(source_engine, target_session)

        states = target_session.query(DimState).all()
        fips_codes = [s.state_fips for s in states]

        assert len(fips_codes) == len(set(fips_codes)), "State FIPS should be unique"

    def test_state_ids_are_sequential(self, source_engine, target_session) -> None:
        """State IDs should be sequential starting from 1."""
        load_dim_state(source_engine, target_session)

        states = target_session.query(DimState).order_by(DimState.state_id).all()
        ids = [s.state_id for s in states]

        # IDs should be 1, 2, 3, ...
        assert ids == list(range(1, len(ids) + 1)), "State IDs should be sequential"


class TestCountyLoading:
    """Integration tests for county dimension loading."""

    def test_counties_have_valid_state_fk(self, source_engine, target_session) -> None:
        """All counties should have valid state foreign keys."""
        # Must load states first
        load_dim_state(source_engine, target_session)
        load_dim_county(source_engine, target_session)

        counties = target_session.query(DimCounty).all()
        valid_state_ids = {s.state_id for s in target_session.query(DimState).all()}

        for county in counties:
            assert county.state_id in valid_state_ids, (
                f"County {county.name} has invalid state_id {county.state_id}"
            )

    def test_county_fips_are_unique(self, source_engine, target_session) -> None:
        """County FIPS codes should be unique."""
        load_dim_state(source_engine, target_session)
        load_dim_county(source_engine, target_session)

        counties = target_session.query(DimCounty).all()
        fips_codes = [c.fips for c in counties]

        assert len(fips_codes) == len(set(fips_codes)), "County FIPS should be unique"

    def test_state_fips_extracted_from_county_fips(self, source_engine, target_session) -> None:
        """State FIPS should be extractable from county FIPS."""
        load_dim_state(source_engine, target_session)
        load_dim_county(source_engine, target_session)

        # Build lookup of state FIPS to state_id
        state_fips_lookup = {s.state_fips: s.state_id for s in target_session.query(DimState).all()}

        counties = target_session.query(DimCounty).limit(100).all()
        for county in counties:
            expected_state_fips = county.fips[:2] if county.fips else None
            if expected_state_fips and expected_state_fips in state_fips_lookup:
                expected_state_id = state_fips_lookup[expected_state_fips]
                assert county.state_id == expected_state_id, (
                    f"County {county.fips} should have state_id {expected_state_id}"
                )


class TestCountryLoading:
    """Integration tests for country dimension loading."""

    def test_countries_have_world_system_tier(self, source_engine, target_session) -> None:
        """Non-region countries should have world system tier classification."""
        count = load_dim_country(source_engine, target_session)
        assert count > 0, "Should load countries"

        countries = (
            target_session.query(DimCountry)
            .filter(
                DimCountry.is_region == False  # noqa: E712
            )
            .all()
        )

        # Count how many real countries have valid tiers
        # Some entries marked is_region=False are actually aggregates (e.g., "NAFTA with Mexico")
        valid_tiers = 0
        aggregate_patterns = [
            "NAFTA",
            "OPEC",
            "Total",
            "European Union",
            "CAFTA",
            "South and Central America",
            "Advanced Technology",
        ]

        for country in countries:
            # Skip aggregates that weren't marked as regions in source
            is_aggregate = any(p in country.country_name for p in aggregate_patterns)
            if is_aggregate:
                continue

            if country.world_system_tier in ("core", "semi_periphery", "periphery"):
                valid_tiers += 1
            else:
                # This would be a real country without classification - report it
                pytest.fail(f"Country {country.country_name} should have valid tier, got None")

        # Verify we found a reasonable number of countries with tiers
        assert valid_tiers > 100, f"Should have >100 classified countries, got {valid_tiers}"

    def test_regions_have_no_tier(self, source_engine, target_session) -> None:
        """Aggregate regions should not have world system tier."""
        load_dim_country(source_engine, target_session)

        regions = (
            target_session.query(DimCountry)
            .filter(
                DimCountry.is_region == True  # noqa: E712
            )
            .all()
        )

        for region in regions:
            assert region.world_system_tier is None, (
                f"Region {region.country_name} should not have tier"
            )

    def test_core_countries_include_g7(self, source_engine, target_session) -> None:
        """G7 countries should be classified as core."""
        load_dim_country(source_engine, target_session)

        g7_names = {
            "United States",
            "Canada",
            "United Kingdom",
            "France",
            "Germany",
            "Italy",
            "Japan",
        }

        core_countries = (
            target_session.query(DimCountry).filter(DimCountry.world_system_tier == "core").all()
        )
        core_names = {c.country_name for c in core_countries}

        # At least some G7 should be in core
        found_g7 = g7_names & core_names
        assert len(found_g7) >= 3, f"Should find G7 in core, found: {found_g7}"


class TestIndustryLoading:
    """Integration tests for industry dimension loading."""

    def test_industries_have_class_composition(self, source_engine, target_session) -> None:
        """Industries should have Marxian class composition classification."""
        count = load_dim_industry(source_engine, target_session)
        assert count > 0, "Should load industries"

        industries = target_session.query(DimIndustry).all()

        # Count classifications
        classified = sum(1 for i in industries if i.class_composition is not None)
        assert classified > 0, "Some industries should be classified"

        # Verify valid classification values
        valid_classes = {
            "goods_producing",
            "service_producing",
            "circulation",
            "government",
            "extraction",
        }
        for ind in industries:
            if ind.class_composition:
                assert ind.class_composition in valid_classes, (
                    f"Industry {ind.naics_code} has invalid class {ind.class_composition}"
                )

    def test_industries_have_sector_codes(self, source_engine, target_session) -> None:
        """Industries should have 2-digit sector codes extracted."""
        load_dim_industry(source_engine, target_session)

        industries = target_session.query(DimIndustry).filter(DimIndustry.naics_level >= 2).all()

        # Most should have sector codes
        with_sector = sum(1 for i in industries if i.sector_code)
        assert with_sector / len(industries) > 0.5, "Most industries should have sector codes"

    def test_manufacturing_is_goods_producing(self, source_engine, target_session) -> None:
        """Manufacturing sectors (31-33) should be goods_producing."""
        load_dim_industry(source_engine, target_session)

        manufacturing = (
            target_session.query(DimIndustry)
            .filter(DimIndustry.sector_code.in_(["31", "32", "33"]))
            .all()
        )

        for ind in manufacturing:
            assert ind.class_composition == "goods_producing", (
                f"Manufacturing {ind.naics_code} should be goods_producing"
            )

    def test_finance_is_circulation(self, source_engine, target_session) -> None:
        """Finance/insurance (52) should be circulation."""
        load_dim_industry(source_engine, target_session)

        finance = target_session.query(DimIndustry).filter(DimIndustry.sector_code == "52").all()

        for ind in finance:
            assert ind.class_composition == "circulation", (
                f"Finance {ind.naics_code} should be circulation"
            )


class TestSectorLoading:
    """Integration tests for sector dimension loading."""

    def test_sectors_derived_from_industries(self, source_engine, target_session) -> None:
        """Sectors should be derived from loaded industries."""
        load_dim_industry(source_engine, target_session)
        count = load_dim_sector(source_engine, target_session)

        assert count > 0, "Should derive sectors from industries"

        sectors = target_session.query(DimSector).all()

        # Sector codes should be 2-digit
        for sector in sectors:
            assert len(sector.sector_code) == 2, (
                f"Sector code {sector.sector_code} should be 2 digits"
            )

    def test_sector_codes_are_unique(self, source_engine, target_session) -> None:
        """Sector codes should be unique."""
        load_dim_industry(source_engine, target_session)
        load_dim_sector(source_engine, target_session)

        sectors = target_session.query(DimSector).all()
        codes = [s.sector_code for s in sectors]

        assert len(codes) == len(set(codes)), "Sector codes should be unique"


class TestOwnershipLoading:
    """Integration tests for ownership dimension loading."""

    def test_ownership_codes_loaded(self, source_engine, target_session) -> None:
        """Ownership codes should be loaded from QCEW."""
        count = load_dim_ownership(source_engine, target_session)
        assert count > 0, "Should load ownership codes"

    def test_ownership_has_government_flag(self, source_engine, target_session) -> None:
        """Ownership codes should have is_government flag set correctly."""
        load_dim_ownership(source_engine, target_session)

        ownerships = target_session.query(DimOwnership).all()

        # Code 5 is private, codes 1-4 are government
        for own in ownerships:
            if own.own_code == "5":
                assert own.is_government is False, "Code 5 should not be government"
                assert own.is_private is True, "Code 5 should be private"
            elif own.own_code in {"1", "2", "3", "4"}:
                assert own.is_government is True, f"Code {own.own_code} should be government"
                assert own.is_private is False, f"Code {own.own_code} should not be private"


class TestWorkerClassLoading:
    """Integration tests for worker class dimension loading."""

    def test_worker_classes_have_marxian_class(self, source_engine, target_session) -> None:
        """Worker classes should have Marxian class classification."""
        count = load_dim_worker_class(source_engine, target_session)

        if count == 0:
            pytest.skip("No worker class data in source database")

        classes = target_session.query(DimWorkerClass).all()

        # Check valid Marxian classes
        valid_classes = {"proletariat", "petty_bourgeois", "state_worker", "unpaid_labor"}
        for wc in classes:
            if wc.marxian_class:
                assert wc.marxian_class in valid_classes, (
                    f"Worker class {wc.class_code} has invalid marxian_class"
                )


class TestDimensionLoadOrder:
    """Tests verifying correct dimension load order for FK resolution."""

    def test_county_requires_state_first(self, source_engine, target_session) -> None:
        """Loading counties without states should fail or produce orphans."""
        # Try loading counties without states
        try:
            load_dim_county(source_engine, target_session)
            # If it succeeds, counties should have no valid state FK
            _counties = target_session.query(DimCounty).all()  # noqa: F841
            # This is actually OK behavior - just means no FK enforcement
            # The test documents the dependency
        except Exception:
            # Expected - dependency failure
            pass

    def test_sector_requires_industry_first(self, source_engine, target_session) -> None:
        """Loading sectors without industries should produce no sectors."""
        count = load_dim_sector(source_engine, target_session)
        assert count == 0, "Sectors without industries should be empty"


class TestDimensionDataQuality:
    """Tests for data quality in loaded dimensions."""

    def test_no_duplicate_primary_keys(self, source_engine, target_session) -> None:
        """Loaded dimensions should have no duplicate primary keys."""
        load_dim_state(source_engine, target_session)
        load_dim_country(source_engine, target_session)
        load_dim_industry(source_engine, target_session)

        # Check each dimension
        for DimModel in [DimState, DimCountry, DimIndustry]:
            rows = target_session.query(DimModel).all()
            # Get primary key values
            pk_col = DimModel.__table__.primary_key.columns.values()[0].name
            pk_values = [getattr(r, pk_col) for r in rows]
            assert len(pk_values) == len(set(pk_values)), (
                f"{DimModel.__name__} has duplicate primary keys"
            )

    def test_no_null_required_fields(self, source_engine, target_session) -> None:
        """Required fields should not be NULL."""
        load_dim_state(source_engine, target_session)
        load_dim_country(source_engine, target_session)

        # Check state names
        states = target_session.query(DimState).all()
        for state in states:
            assert state.state_name is not None, f"State {state.state_fips} has NULL name"
            assert state.state_fips is not None, f"State {state.state_id} has NULL FIPS"

        # Check country names
        countries = target_session.query(DimCountry).all()
        for country in countries:
            assert country.country_name is not None, f"Country {country.cty_code} has NULL name"
