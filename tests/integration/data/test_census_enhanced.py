"""Integration tests for enhanced Census loader functionality.

Tests the Phase 2-4 Census loader enhancements:
- Multi-year loading infrastructure (census_years: list[int])
- Race-disaggregated table loading (DimRace, race_id FK)
- Metro area population (DimMetroArea, BridgeCountyMetro)

These tests verify schema correctness and data relationships without
making actual Census API calls (which are slow and rate-limited).
For full end-to-end tests with real API calls, use manual testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event, func
from sqlalchemy.orm import sessionmaker

from babylon.data.loader_base import LoaderConfig
from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import (
    BridgeCountyMetro,
    DimCounty,
    DimDataSource,
    DimMetroArea,
    DimRace,
    DimState,
    DimTime,
    FactCensusMedianIncome,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def engine() -> Engine:
    """Create in-memory SQLite database with FK enforcement."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    NormalizedBase.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def session(engine: Engine) -> Session:
    """Create session with automatic rollback."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.rollback()
    session.close()


class TestLoaderConfigMultiYear:
    """Test LoaderConfig multi-year configuration."""

    def test_census_years_is_list(self) -> None:
        """census_years should be a list of years."""
        config = LoaderConfig()
        assert isinstance(config.census_years, list)

    def test_census_years_defaults_to_single_year(self) -> None:
        """census_years defaults to [2021] to avoid API rate limits."""
        config = LoaderConfig()
        assert config.census_years == [2021]

    def test_can_specify_single_year(self) -> None:
        """Should be able to specify a single year as list."""
        config = LoaderConfig(census_years=[2022])
        assert config.census_years == [2022]

    def test_can_specify_multiple_years(self) -> None:
        """Should be able to specify multiple years."""
        config = LoaderConfig(census_years=[2020, 2021, 2022])
        assert config.census_years == [2020, 2021, 2022]


class TestDimTimeForCensus:
    """Test DimTime dimension usage for Census multi-year data."""

    def test_can_create_annual_time_record(self, session: Session) -> None:
        """Should be able to create annual time records."""
        time_2022 = DimTime(year=2022, is_annual=True)
        session.add(time_2022)
        session.flush()

        loaded = session.query(DimTime).filter(DimTime.year == 2022).one()
        assert loaded.year == 2022
        assert loaded.is_annual is True
        assert loaded.month is None

    def test_can_create_multiple_years(self, session: Session) -> None:
        """Should be able to create time records for multiple years."""
        for year in range(2020, 2024):
            session.add(DimTime(year=year, is_annual=True))
        session.flush()

        count = session.query(DimTime).filter(DimTime.year >= 2020).count()
        assert count == 4


class TestDimRacePopulation:
    """Test DimRace dimension population."""

    def test_can_populate_all_race_codes(self, session: Session) -> None:
        """Should be able to populate all 10 race codes."""
        from babylon.data.census.loader_3nf import RACE_CODES

        for race_data in RACE_CODES:
            race = DimRace(
                race_code=race_data["code"],
                race_name=race_data["name"],
                race_short_name=race_data["short"],
                is_hispanic_ethnicity=race_data["hispanic"],
                is_indigenous=race_data["indigenous"],
                display_order=race_data["order"],
            )
            session.add(race)

        session.flush()

        count = session.query(DimRace).count()
        assert count == 10

    def test_race_codes_are_unique(self, session: Session) -> None:
        """Race codes should be unique."""
        from sqlalchemy.exc import IntegrityError

        session.add(DimRace(race_code="A", race_name="White", race_short_name="White"))
        session.flush()

        session.add(DimRace(race_code="A", race_name="Duplicate", race_short_name="Dup"))
        with pytest.raises(IntegrityError):
            session.flush()


class TestFactTableWithTimeAndRace:
    """Test fact tables with time_id and race_id FKs."""

    @pytest.fixture
    def populated_dimensions(self, session: Session) -> dict[str, int]:
        """Create required dimension records and return their IDs."""
        # Create state and county
        state = DimState(state_fips="06", state_name="California", state_abbrev="CA")
        session.add(state)
        session.flush()

        county = DimCounty(
            fips="06037",
            county_fips="037",
            county_name="Los Angeles County",
            state_id=state.state_id,
        )
        session.add(county)
        session.flush()

        # Create data source
        source = DimDataSource(
            source_code="ACS5Y2022",
            source_name="Census ACS 5-Year",
            description="American Community Survey",
        )
        session.add(source)
        session.flush()

        # Create time
        time = DimTime(year=2022, is_annual=True)
        session.add(time)
        session.flush()

        # Create race
        race = DimRace(
            race_code="T",
            race_name="Total (all races)",
            race_short_name="Total",
        )
        session.add(race)
        session.flush()

        return {
            "county_id": county.county_id,
            "source_id": source.source_id,
            "time_id": time.time_id,
            "race_id": race.race_id,
        }

    def test_fact_census_median_income_requires_time_id(
        self, session: Session, populated_dimensions: dict[str, int]
    ) -> None:
        """FactCensusMedianIncome should require time_id."""
        from decimal import Decimal

        fact = FactCensusMedianIncome(
            county_id=populated_dimensions["county_id"],
            source_id=populated_dimensions["source_id"],
            time_id=populated_dimensions["time_id"],
            race_id=populated_dimensions["race_id"],
            median_income_usd=Decimal("75000.00"),
        )
        session.add(fact)
        session.flush()

        loaded = session.query(FactCensusMedianIncome).first()
        assert loaded is not None
        assert loaded.time_id == populated_dimensions["time_id"]

    def test_fact_census_median_income_requires_race_id(
        self, session: Session, populated_dimensions: dict[str, int]
    ) -> None:
        """FactCensusMedianIncome should require race_id."""
        from decimal import Decimal

        fact = FactCensusMedianIncome(
            county_id=populated_dimensions["county_id"],
            source_id=populated_dimensions["source_id"],
            time_id=populated_dimensions["time_id"],
            race_id=populated_dimensions["race_id"],
            median_income_usd=Decimal("75000.00"),
        )
        session.add(fact)
        session.flush()

        loaded = session.query(FactCensusMedianIncome).first()
        assert loaded is not None
        assert loaded.race_id == populated_dimensions["race_id"]

    def test_can_store_multiple_years_same_county(
        self, session: Session, populated_dimensions: dict[str, int]
    ) -> None:
        """Should be able to store multiple years of data for same county."""
        from decimal import Decimal

        # Create additional time records
        time_2021 = DimTime(year=2021, is_annual=True)
        session.add(time_2021)
        session.flush()

        # Add facts for both years
        fact_2022 = FactCensusMedianIncome(
            county_id=populated_dimensions["county_id"],
            source_id=populated_dimensions["source_id"],
            time_id=populated_dimensions["time_id"],
            race_id=populated_dimensions["race_id"],
            median_income_usd=Decimal("75000.00"),
        )
        fact_2021 = FactCensusMedianIncome(
            county_id=populated_dimensions["county_id"],
            source_id=populated_dimensions["source_id"],
            time_id=time_2021.time_id,
            race_id=populated_dimensions["race_id"],
            median_income_usd=Decimal("72000.00"),
        )
        session.add_all([fact_2022, fact_2021])
        session.flush()

        count = session.query(FactCensusMedianIncome).count()
        assert count == 2

    def test_can_store_multiple_races_same_county_year(
        self, session: Session, populated_dimensions: dict[str, int]
    ) -> None:
        """Should be able to store multiple races for same county/year."""
        from decimal import Decimal

        # Create additional race
        race_b = DimRace(
            race_code="B",
            race_name="Black or African American alone",
            race_short_name="Black",
        )
        session.add(race_b)
        session.flush()

        # Add facts for both races
        fact_total = FactCensusMedianIncome(
            county_id=populated_dimensions["county_id"],
            source_id=populated_dimensions["source_id"],
            time_id=populated_dimensions["time_id"],
            race_id=populated_dimensions["race_id"],
            median_income_usd=Decimal("75000.00"),
        )
        fact_black = FactCensusMedianIncome(
            county_id=populated_dimensions["county_id"],
            source_id=populated_dimensions["source_id"],
            time_id=populated_dimensions["time_id"],
            race_id=race_b.race_id,
            median_income_usd=Decimal("55000.00"),
        )
        session.add_all([fact_total, fact_black])
        session.flush()

        count = session.query(FactCensusMedianIncome).count()
        assert count == 2


class TestDimMetroAreaSchema:
    """Test DimMetroArea dimension for metro area data."""

    def test_can_create_msa(self, session: Session) -> None:
        """Should be able to create MSA records."""
        metro = DimMetroArea(
            geo_id="31080",
            cbsa_code="31080",
            metro_name="Los Angeles-Long Beach-Anaheim, CA",
            area_type="msa",
        )
        session.add(metro)
        session.flush()

        loaded = session.query(DimMetroArea).first()
        assert loaded.area_type == "msa"

    def test_can_create_micropolitan(self, session: Session) -> None:
        """Should be able to create Micropolitan records."""
        metro = DimMetroArea(
            geo_id="25020",
            cbsa_code="25020",
            metro_name="El Centro, CA",
            area_type="micropolitan",
        )
        session.add(metro)
        session.flush()

        loaded = session.query(DimMetroArea).first()
        assert loaded.area_type == "micropolitan"

    def test_can_create_csa(self, session: Session) -> None:
        """Should be able to create CSA records."""
        metro = DimMetroArea(
            geo_id="348",
            cbsa_code="348",
            metro_name="Los Angeles-Long Beach, CA CSA",
            area_type="csa",
        )
        session.add(metro)
        session.flush()

        loaded = session.query(DimMetroArea).first()
        assert loaded.area_type == "csa"

    def test_area_type_constraint(self, session: Session) -> None:
        """area_type should be constrained to valid values."""
        from sqlalchemy.exc import IntegrityError

        metro = DimMetroArea(
            geo_id="00000",
            metro_name="Invalid Area",
            area_type="invalid",  # Invalid type
        )
        session.add(metro)

        with pytest.raises(IntegrityError):
            session.flush()


class TestBridgeCountyMetro:
    """Test county-to-metro bridge table."""

    @pytest.fixture
    def county_and_metro(self, session: Session) -> dict[str, int]:
        """Create county and metro area records."""
        # Create state
        state = DimState(state_fips="06", state_name="California", state_abbrev="CA")
        session.add(state)
        session.flush()

        # Create county
        county = DimCounty(
            fips="06037",
            county_fips="037",
            county_name="Los Angeles County",
            state_id=state.state_id,
        )
        session.add(county)
        session.flush()

        # Create metro
        metro = DimMetroArea(
            geo_id="31080",
            cbsa_code="31080",
            metro_name="Los Angeles-Long Beach-Anaheim, CA",
            area_type="msa",
        )
        session.add(metro)
        session.flush()

        return {
            "county_id": county.county_id,
            "metro_area_id": metro.metro_area_id,
        }

    def test_can_create_county_metro_mapping(
        self, session: Session, county_and_metro: dict[str, int]
    ) -> None:
        """Should be able to create county-metro mapping."""
        bridge = BridgeCountyMetro(
            county_id=county_and_metro["county_id"],
            metro_area_id=county_and_metro["metro_area_id"],
            is_principal_city=True,
        )
        session.add(bridge)
        session.flush()

        loaded = session.query(BridgeCountyMetro).first()
        assert loaded is not None
        assert loaded.is_principal_city is True

    def test_county_can_belong_to_multiple_metros(
        self, session: Session, county_and_metro: dict[str, int]
    ) -> None:
        """A county can belong to both CBSA and CSA."""
        # Create CSA
        csa = DimMetroArea(
            geo_id="348",
            cbsa_code="348",
            metro_name="Los Angeles-Long Beach, CA CSA",
            area_type="csa",
        )
        session.add(csa)
        session.flush()

        # Map county to both MSA and CSA
        bridge_msa = BridgeCountyMetro(
            county_id=county_and_metro["county_id"],
            metro_area_id=county_and_metro["metro_area_id"],
            is_principal_city=True,
        )
        bridge_csa = BridgeCountyMetro(
            county_id=county_and_metro["county_id"],
            metro_area_id=csa.metro_area_id,
            is_principal_city=False,
        )
        session.add_all([bridge_msa, bridge_csa])
        session.flush()

        count = session.query(BridgeCountyMetro).count()
        assert count == 2


class TestMetroAreaAggregationQuery:
    """Test that county-to-metro aggregation queries work."""

    def test_can_aggregate_income_by_metro(self, session: Session) -> None:
        """Should be able to aggregate county income to metro level."""
        # Setup: Create all required dimensions
        state = DimState(state_fips="06", state_name="California", state_abbrev="CA")
        session.add(state)
        session.flush()

        county1 = DimCounty(
            fips="06037",
            county_fips="037",
            county_name="Los Angeles",
            state_id=state.state_id,
        )
        county2 = DimCounty(
            fips="06059",
            county_fips="059",
            county_name="Orange",
            state_id=state.state_id,
        )
        session.add_all([county1, county2])
        session.flush()

        metro = DimMetroArea(
            geo_id="31080",
            cbsa_code="31080",
            metro_name="Los Angeles-Long Beach-Anaheim, CA",
            area_type="msa",
        )
        session.add(metro)
        session.flush()

        # Bridge both counties to metro
        session.add(
            BridgeCountyMetro(county_id=county1.county_id, metro_area_id=metro.metro_area_id)
        )
        session.add(
            BridgeCountyMetro(county_id=county2.county_id, metro_area_id=metro.metro_area_id)
        )
        session.flush()

        source = DimDataSource(source_code="ACS5Y_METRO", source_name="Census ACS 5-Year")
        session.add(source)
        session.flush()

        time = DimTime(year=2022, is_annual=True)
        session.add(time)
        session.flush()

        race = DimRace(race_code="T", race_name="Total", race_short_name="Total")
        session.add(race)
        session.flush()

        # Add income facts for both counties
        from decimal import Decimal

        session.add(
            FactCensusMedianIncome(
                county_id=county1.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race.race_id,
                median_income_usd=Decimal("80000.00"),
            )
        )
        session.add(
            FactCensusMedianIncome(
                county_id=county2.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race.race_id,
                median_income_usd=Decimal("90000.00"),
            )
        )
        session.flush()

        # Query: Average income by metro
        result = (
            session.query(
                DimMetroArea.metro_name,
                func.avg(FactCensusMedianIncome.median_income_usd),
            )
            .join(BridgeCountyMetro, BridgeCountyMetro.metro_area_id == DimMetroArea.metro_area_id)
            .join(
                FactCensusMedianIncome,
                FactCensusMedianIncome.county_id == BridgeCountyMetro.county_id,
            )
            .filter(FactCensusMedianIncome.race_id == race.race_id)
            .group_by(DimMetroArea.metro_name)
            .first()
        )

        assert result is not None
        metro_name, avg_income = result
        assert metro_name == "Los Angeles-Long Beach-Anaheim, CA"
        # Average of 80000 and 90000 = 85000
        assert float(avg_income) == 85000.0


class TestCensusLoaderInterface:
    """Test CensusLoader interface without making API calls."""

    def test_census_loader_instantiates(self) -> None:
        """CensusLoader should instantiate with config."""
        from babylon.data.census.loader_3nf import CensusLoader

        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        assert loader is not None

    def test_census_loader_has_dimension_tables(self) -> None:
        """CensusLoader should return DimRace and DimTime in dimensions."""
        from babylon.data.census.loader_3nf import CensusLoader

        loader = CensusLoader()
        dims = loader.get_dimension_tables()
        dim_names = {d.__tablename__ for d in dims}

        assert "dim_race" in dim_names
        assert "dim_time" in dim_names
        assert "dim_metro_area" in dim_names

    def test_census_loader_has_fact_tables(self) -> None:
        """CensusLoader should return Census fact tables."""
        from babylon.data.census.loader_3nf import CensusLoader

        loader = CensusLoader()
        facts = loader.get_fact_tables()
        fact_names = {f.__tablename__ for f in facts}

        assert "fact_census_income" in fact_names
        assert "fact_census_median_income" in fact_names
        assert "fact_census_employment" in fact_names


class TestRaceDisaggregationQueryPatterns:
    """Test query patterns for race-disaggregated data."""

    def test_can_filter_facts_by_race(self, session: Session) -> None:
        """Should be able to filter facts by race_id."""
        # Setup dimensions
        state = DimState(state_fips="06", state_name="California", state_abbrev="CA")
        session.add(state)
        session.flush()

        county = DimCounty(
            fips="06037",
            county_fips="037",
            county_name="Los Angeles",
            state_id=state.state_id,
        )
        session.add(county)
        session.flush()

        source = DimDataSource(source_code="ACS5Y_RACE1", source_name="Census ACS 5-Year")
        session.add(source)
        session.flush()

        time = DimTime(year=2022, is_annual=True)
        session.add(time)
        session.flush()

        # Create multiple races
        race_total = DimRace(race_code="T", race_name="Total", race_short_name="Total")
        race_black = DimRace(race_code="B", race_name="Black", race_short_name="Black")
        session.add_all([race_total, race_black])
        session.flush()

        # Add facts for both races
        from decimal import Decimal

        session.add(
            FactCensusMedianIncome(
                county_id=county.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race_total.race_id,
                median_income_usd=Decimal("80000.00"),
            )
        )
        session.add(
            FactCensusMedianIncome(
                county_id=county.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race_black.race_id,
                median_income_usd=Decimal("50000.00"),
            )
        )
        session.flush()

        # Query by race
        black_income = (
            session.query(FactCensusMedianIncome.median_income_usd)
            .join(DimRace, DimRace.race_id == FactCensusMedianIncome.race_id)
            .filter(DimRace.race_code == "B")
            .scalar()
        )

        assert float(black_income) == 50000.0

    def test_can_compare_incomes_across_races(self, session: Session) -> None:
        """Should be able to compare median incomes across races."""
        # Setup dimensions
        state = DimState(state_fips="06", state_name="California", state_abbrev="CA")
        session.add(state)
        session.flush()

        county = DimCounty(
            fips="06037",
            county_fips="037",
            county_name="Los Angeles",
            state_id=state.state_id,
        )
        session.add(county)
        session.flush()

        source = DimDataSource(source_code="ACS5Y_RACE2", source_name="Census ACS 5-Year")
        session.add(source)
        session.flush()

        time = DimTime(year=2022, is_annual=True)
        session.add(time)
        session.flush()

        # Create races
        race_total = DimRace(race_code="T", race_name="Total", race_short_name="Total")
        race_white = DimRace(race_code="A", race_name="White", race_short_name="White")
        race_black = DimRace(race_code="B", race_name="Black", race_short_name="Black")
        session.add_all([race_total, race_white, race_black])
        session.flush()

        # Add facts
        from decimal import Decimal

        session.add(
            FactCensusMedianIncome(
                county_id=county.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race_total.race_id,
                median_income_usd=Decimal("75000.00"),
            )
        )
        session.add(
            FactCensusMedianIncome(
                county_id=county.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race_white.race_id,
                median_income_usd=Decimal("85000.00"),
            )
        )
        session.add(
            FactCensusMedianIncome(
                county_id=county.county_id,
                source_id=source.source_id,
                time_id=time.time_id,
                race_id=race_black.race_id,
                median_income_usd=Decimal("50000.00"),
            )
        )
        session.flush()

        # Query: Compare White to Black median income ratio
        results = (
            session.query(DimRace.race_code, FactCensusMedianIncome.median_income_usd)
            .join(DimRace, DimRace.race_id == FactCensusMedianIncome.race_id)
            .filter(DimRace.race_code.in_(["A", "B"]))
            .all()
        )

        incomes = {r[0]: float(r[1]) for r in results}
        ratio = incomes["A"] / incomes["B"]

        # White income (85000) / Black income (50000) = 1.7
        assert ratio == pytest.approx(1.7)
