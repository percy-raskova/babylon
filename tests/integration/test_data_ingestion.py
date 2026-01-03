"""Integration tests for data ingestion pipeline.

These tests verify:
1. Full CSV ingestion pipeline works end-to-end
2. Foreign key relationships are maintained
3. Data integrity across multiple tables
4. Error handling for missing/invalid files
"""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.database import Base
from babylon.data.external.bls import StrategicResourceIngester, UnionMembershipIngester
from babylon.data.external.census import (
    CensusMetroIngester,
    CensusPopulationIngester,
    MetroAreaIngester,
    StateIngester,
    ingest_all_census_data,
)
from babylon.data.external.fred import FredIndicatorIngester
from babylon.data.schema import (
    CensusMetro,
    CensusPopulation,
    FredIndicator,
    MetroArea,
    State,
    StrategicResource,
    UnionMembership,
)


@pytest.fixture
def test_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine):
    """Create a test session."""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def sample_data_dir():
    """Create a temporary directory with sample CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # Create states.csv
        states_csv = data_dir / "states.csv"
        states_csv.write_text(
            "fips,name,abbreviation\n"
            "01,Alabama,AL\n"
            "02,Alaska,AK\n"
            "06,California,CA\n"
            "36,New York,NY\n"
            "48,Texas,TX\n"
        )

        # Create metro_areas.csv
        metros_csv = data_dir / "metro_areas.csv"
        metros_csv.write_text(
            "cbsa_code,name\n"
            "31080,Los Angeles-Long Beach-Anaheim\n"
            "16980,Chicago-Naperville-Elgin\n"
            "47900,Washington-Arlington-Alexandria\n"
        )

        # Create census_state_population.csv
        census_pop_csv = data_dir / "census_state_population.csv"
        census_pop_csv.write_text(
            "state_fips,year,total_pop,employed,unemployed,self_employed,median_income,poverty_pop\n"
            "06,2022,39538223,18000000,1200000,2500000,78672.50,4500000\n"
            "48,2022,29145505,14000000,900000,1800000,64034.00,3800000\n"
            "36,2022,20201249,9200000,600000,1100000,74314.00,2700000\n"
        )

        # Create census_metro_demographics.csv
        census_metro_csv = data_dir / "census_metro_demographics.csv"
        census_metro_csv.write_text(
            "cbsa_code,year,total_pop,median_income,gini_index,median_rent,median_home_value\n"
            "31080,2022,13200998,80440.00,0.49,1750.00,750000.00\n"
            "16980,2022,9618502,71535.00,0.47,1250.00,350000.00\n"
        )

        # Create fred_economic_indicators.csv
        fred_csv = data_dir / "fred_economic_indicators.csv"
        fred_csv.write_text(
            "year,quarter,gdp_billions,unemployment_pct,cpi,fed_funds_rate,federal_debt_millions,m2_money_supply,median_income\n"
            "2023,1,26136.0,3.5,302.0,4.65,31300000,20350,73000\n"
            "2023,2,26582.0,3.5,303.5,5.08,32000000,20500,73500\n"
            "2023,3,27063.0,3.7,305.0,5.33,32700000,20700,74000\n"
            "2023,4,27610.3,3.7,306.7,5.33,34000000,20866,74580\n"
        )

        # Create bls_union_membership.csv
        union_csv = data_dir / "bls_union_membership.csv"
        union_csv.write_text(
            "state_fips,year,total_employed,union_members,union_pct\n"
            "36,2023,9200000,2000000,21.7\n"
            "06,2023,18000000,2800000,15.9\n"
            "48,2023,14000000,700000,5.0\n"
        )

        # Create strategic_resources.csv
        resources_csv = data_dir / "strategic_resources.csv"
        resources_csv.write_text(
            "resource_id,resource_name,year,annual_production,production_unit,strategic_reserve,reserve_unit\n"
            "R001,Iron Ore,2023,48000000,metric_tons,0,metric_tons\n"
            "R002,Crude Oil,2023,4300000000,barrels,350000000,barrels\n"
            "R003,Steel,2023,80000000,metric_tons,0,metric_tons\n"
        )

        yield data_dir


@pytest.mark.integration
class TestCsvIngestion:
    """Tests for CSV file ingestion."""

    def test_ingest_states_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest states from CSV file."""
        ingester = StateIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "states.csv")

        assert result.success
        assert result.rows_read == 5
        assert result.rows_inserted == 5
        assert session.query(State).count() == 5

        # Verify specific state
        california = session.query(State).filter_by(fips="06").first()
        assert california is not None
        assert california.name == "California"
        assert california.abbreviation == "CA"

    def test_ingest_metro_areas_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest metro areas from CSV file."""
        ingester = MetroAreaIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "metro_areas.csv")

        assert result.success
        assert result.rows_inserted == 3
        assert session.query(MetroArea).count() == 3

    def test_ingest_census_population_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest census population from CSV file."""
        # First ingest states (foreign key dependency)
        StateIngester().ingest_csv(session, sample_data_dir / "states.csv")

        ingester = CensusPopulationIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "census_state_population.csv")

        assert result.success
        assert result.rows_inserted == 3

        # Verify data
        california = session.query(CensusPopulation).filter_by(state_fips="06").first()
        assert california is not None
        assert california.total_pop == 39538223
        assert california.median_income == 78672.50

    def test_ingest_census_metro_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest census metro data from CSV file."""
        # First ingest metro areas (foreign key dependency)
        MetroAreaIngester().ingest_csv(session, sample_data_dir / "metro_areas.csv")

        ingester = CensusMetroIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "census_metro_demographics.csv")

        assert result.success
        assert result.rows_inserted == 2

        # Verify Gini index
        la = session.query(CensusMetro).filter_by(cbsa_code="31080").first()
        assert la is not None
        assert la.gini_index == 0.49

    def test_ingest_fred_indicators_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest FRED indicators from CSV file."""
        ingester = FredIndicatorIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "fred_economic_indicators.csv")

        assert result.success
        assert result.rows_inserted == 4

        # Verify quarterly data
        q4 = session.query(FredIndicator).filter_by(year=2023, quarter=4).first()
        assert q4 is not None
        assert q4.gdp_billions == 27610.3
        assert q4.unemployment_pct == 3.7

    def test_ingest_union_membership_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest union membership from CSV file."""
        # First ingest states (foreign key dependency)
        StateIngester().ingest_csv(session, sample_data_dir / "states.csv")

        ingester = UnionMembershipIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "bls_union_membership.csv")

        assert result.success
        assert result.rows_inserted == 3

        # Verify New York union rate
        ny = session.query(UnionMembership).filter_by(state_fips="36").first()
        assert ny is not None
        assert ny.union_pct == 21.7

    def test_ingest_strategic_resources_csv(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest strategic resources from CSV file."""
        ingester = StrategicResourceIngester()
        result = ingester.ingest_csv(session, sample_data_dir / "strategic_resources.csv")

        assert result.success
        assert result.rows_inserted == 3

        # Verify oil data
        oil = session.query(StrategicResource).filter_by(resource_id="R002").first()
        assert oil is not None
        assert oil.resource_name == "Crude Oil"
        assert oil.annual_production == 4300000000.0
        assert oil.strategic_reserve == 350000000.0


@pytest.mark.integration
class TestIngestAllCensusData:
    """Tests for the ingest_all_census_data convenience function."""

    def test_ingest_all_census_data(self, session: Session, sample_data_dir: Path) -> None:
        """Ingest all census data from a directory."""
        results = ingest_all_census_data(session, sample_data_dir)

        # All files should be processed
        assert "states.csv" in results
        assert "metro_areas.csv" in results
        assert "census_state_population.csv" in results
        assert "census_metro_demographics.csv" in results

        # All should be successful
        assert results["states.csv"].success
        assert results["metro_areas.csv"].success
        assert results["census_state_population.csv"].success
        assert results["census_metro_demographics.csv"].success

        # Verify total counts
        assert session.query(State).count() == 5
        assert session.query(MetroArea).count() == 3
        assert session.query(CensusPopulation).count() == 3
        assert session.query(CensusMetro).count() == 2


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error handling in ingestion."""

    def test_missing_file_returns_error(self, session: Session) -> None:
        """Ingesting a missing file returns an error result."""
        ingester = StateIngester()
        result = ingester.ingest_csv(session, Path("/nonexistent/file.csv"))

        assert not result.success
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower() or "File not found" in result.errors[0]

    def test_invalid_rows_are_skipped(self, session: Session) -> None:
        """Invalid rows are skipped and reported."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("fips,name,abbreviation\n")
            f.write("01,Alabama,AL\n")  # Valid
            f.write("0,Invalid,XX\n")  # Invalid: FIPS too short
            f.write("02,Alaska,AK\n")  # Valid
            csv_path = Path(f.name)

        try:
            ingester = StateIngester()
            result = ingester.ingest_csv(session, csv_path)

            assert result.rows_read == 3
            assert result.rows_inserted == 2
            assert result.rows_skipped == 1
            assert len(result.errors) == 1
            assert session.query(State).count() == 2
        finally:
            csv_path.unlink()

    def test_empty_csv_file(self, session: Session) -> None:
        """Ingesting an empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("fips,name,abbreviation\n")  # Header only
            csv_path = Path(f.name)

        try:
            ingester = StateIngester()
            result = ingester.ingest_csv(session, csv_path)

            assert result.rows_read == 0
            assert result.rows_inserted == 0
            # Empty but valid file is not an error
            assert len(result.errors) == 0
        finally:
            csv_path.unlink()


@pytest.mark.integration
class TestDataIntegrity:
    """Tests for data integrity across the pipeline."""

    def test_full_pipeline_integrity(self, session: Session, sample_data_dir: Path) -> None:
        """Full pipeline maintains referential integrity."""
        # Ingest all reference data first
        StateIngester().ingest_csv(session, sample_data_dir / "states.csv")
        MetroAreaIngester().ingest_csv(session, sample_data_dir / "metro_areas.csv")

        # Ingest dependent data
        CensusPopulationIngester().ingest_csv(
            session, sample_data_dir / "census_state_population.csv"
        )
        CensusMetroIngester().ingest_csv(session, sample_data_dir / "census_metro_demographics.csv")
        UnionMembershipIngester().ingest_csv(session, sample_data_dir / "bls_union_membership.csv")
        FredIndicatorIngester().ingest_csv(
            session, sample_data_dir / "fred_economic_indicators.csv"
        )
        StrategicResourceIngester().ingest_csv(session, sample_data_dir / "strategic_resources.csv")

        # Verify all data is linked correctly
        # California should have census data, union data
        ca_census = session.query(CensusPopulation).filter_by(state_fips="06").first()
        ca_union = session.query(UnionMembership).filter_by(state_fips="06").first()

        assert ca_census is not None
        assert ca_union is not None
        assert ca_census.total_pop == 39538223
        assert ca_union.union_pct == 15.9

        # LA metro should have census data
        la_metro = session.query(CensusMetro).filter_by(cbsa_code="31080").first()
        assert la_metro is not None
        assert la_metro.total_pop == 13200998

        # FRED should have all quarterly data
        fred_data = session.query(FredIndicator).filter_by(year=2023).all()
        assert len(fred_data) == 4

        # Strategic resources should all be present
        resources = session.query(StrategicResource).all()
        assert len(resources) == 3

    def test_idempotent_ingestion(self, session: Session, sample_data_dir: Path) -> None:
        """Re-ingesting the same data doesn't create duplicates (for reference tables)."""
        ingester = StateIngester()

        # First ingestion
        result1 = ingester.ingest_csv(session, sample_data_dir / "states.csv")
        assert result1.rows_inserted == 5

        # Second ingestion - will fail due to unique constraint on primary key
        # The session will have an error, which is expected behavior
        result2 = ingester.ingest_csv(session, sample_data_dir / "states.csv")

        # We expect errors because states already exist
        # This verifies the primary key constraint is working
        assert result2.rows_skipped > 0 or len(result2.errors) > 0
