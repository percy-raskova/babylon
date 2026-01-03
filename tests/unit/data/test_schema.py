"""Tests for the external data SQLite schema.

These tests verify:
1. SQLAlchemy model definitions are correct
2. Tables can be created with proper constraints
3. Foreign key relationships work correctly
4. Data insertion and retrieval works as expected
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.database import Base
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


@pytest.mark.ledger
class TestSchemaTableCreation:
    """Test that all schema tables are created correctly."""

    def test_all_tables_created(self, test_engine) -> None:
        """All schema tables should be created."""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "states",
            "metro_areas",
            "census_population",
            "census_metro",
            "fred_indicators",
            "union_membership",
            "strategic_resources",
        ]

        for table in expected_tables:
            assert table in tables, f"Table '{table}' not found in database"

    def test_states_table_columns(self, test_engine) -> None:
        """States table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("states")}

        assert "fips" in columns
        assert "name" in columns
        assert "abbreviation" in columns

    def test_metro_areas_table_columns(self, test_engine) -> None:
        """Metro areas table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("metro_areas")}

        assert "cbsa_code" in columns
        assert "name" in columns

    def test_census_population_table_columns(self, test_engine) -> None:
        """Census population table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("census_population")}

        expected_columns = [
            "id",
            "state_fips",
            "year",
            "total_pop",
            "employed",
            "unemployed",
            "self_employed",
            "median_income",
            "poverty_pop",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in census_population table"

    def test_census_metro_table_columns(self, test_engine) -> None:
        """Census metro table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("census_metro")}

        expected_columns = [
            "id",
            "cbsa_code",
            "year",
            "total_pop",
            "median_income",
            "gini_index",
            "median_rent",
            "median_home_value",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in census_metro table"

    def test_fred_indicators_table_columns(self, test_engine) -> None:
        """FRED indicators table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("fred_indicators")}

        expected_columns = [
            "id",
            "year",
            "quarter",
            "gdp_billions",
            "unemployment_pct",
            "cpi",
            "fed_funds_rate",
            "federal_debt_millions",
            "m2_money_supply",
            "median_income",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in fred_indicators table"

    def test_union_membership_table_columns(self, test_engine) -> None:
        """Union membership table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("union_membership")}

        expected_columns = [
            "id",
            "state_fips",
            "year",
            "total_employed",
            "union_members",
            "union_pct",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in union_membership table"

    def test_strategic_resources_table_columns(self, test_engine) -> None:
        """Strategic resources table should have correct columns."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("strategic_resources")}

        expected_columns = [
            "id",
            "resource_id",
            "resource_name",
            "year",
            "annual_production",
            "production_unit",
            "strategic_reserve",
            "reserve_unit",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in strategic_resources table"


@pytest.mark.ledger
class TestStateModel:
    """Tests for the State model."""

    def test_create_state(self, session: Session) -> None:
        """Can create a state record."""
        state = State(fips="01", name="Alabama", abbreviation="AL")
        session.add(state)
        session.commit()

        result = session.query(State).filter_by(fips="01").first()
        assert result is not None
        assert result.name == "Alabama"
        assert result.abbreviation == "AL"

    def test_state_fips_is_primary_key(self, session: Session) -> None:
        """FIPS code is the primary key - duplicates should fail."""
        state1 = State(fips="01", name="Alabama", abbreviation="AL")
        state2 = State(fips="01", name="Duplicate", abbreviation="DU")

        session.add(state1)
        session.commit()

        session.add(state2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_multiple_states(self, session: Session) -> None:
        """Can create multiple state records."""
        states = [
            State(fips="01", name="Alabama", abbreviation="AL"),
            State(fips="02", name="Alaska", abbreviation="AK"),
            State(fips="04", name="Arizona", abbreviation="AZ"),
        ]
        session.add_all(states)
        session.commit()

        result = session.query(State).all()
        assert len(result) == 3


@pytest.mark.ledger
class TestMetroAreaModel:
    """Tests for the MetroArea model."""

    def test_create_metro_area(self, session: Session) -> None:
        """Can create a metro area record."""
        metro = MetroArea(cbsa_code="31080", name="Los Angeles-Long Beach-Anaheim")
        session.add(metro)
        session.commit()

        result = session.query(MetroArea).filter_by(cbsa_code="31080").first()
        assert result is not None
        assert result.name == "Los Angeles-Long Beach-Anaheim"

    def test_cbsa_code_is_primary_key(self, session: Session) -> None:
        """CBSA code is the primary key - duplicates should fail."""
        metro1 = MetroArea(cbsa_code="31080", name="Los Angeles")
        metro2 = MetroArea(cbsa_code="31080", name="Duplicate")

        session.add(metro1)
        session.commit()

        session.add(metro2)
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.ledger
class TestCensusPopulationModel:
    """Tests for the CensusPopulation model."""

    def test_create_census_population(self, session: Session) -> None:
        """Can create a census population record."""
        # First create a state for the foreign key
        state = State(fips="06", name="California", abbreviation="CA")
        session.add(state)
        session.commit()

        census = CensusPopulation(
            state_fips="06",
            year=2022,
            total_pop=39538223,
            employed=18000000,
            unemployed=1200000,
            self_employed=2500000,
            median_income=78672.0,
            poverty_pop=4500000,
        )
        session.add(census)
        session.commit()

        result = session.query(CensusPopulation).filter_by(state_fips="06").first()
        assert result is not None
        assert result.total_pop == 39538223
        assert result.year == 2022

    def test_census_population_nullable_fields(self, session: Session) -> None:
        """Optional fields can be NULL."""
        state = State(fips="06", name="California", abbreviation="CA")
        session.add(state)
        session.commit()

        # Create with only required fields
        census = CensusPopulation(
            state_fips="06",
            year=2022,
        )
        session.add(census)
        session.commit()

        result = session.query(CensusPopulation).filter_by(state_fips="06").first()
        assert result is not None
        assert result.total_pop is None
        assert result.employed is None

    def test_census_population_without_state(self, session: Session) -> None:
        """Can create census record with NULL state_fips (for national totals)."""
        census = CensusPopulation(
            state_fips=None,
            year=2022,
            total_pop=331000000,
        )
        session.add(census)
        session.commit()

        result = session.query(CensusPopulation).filter_by(total_pop=331000000).first()
        assert result is not None
        assert result.state_fips is None


@pytest.mark.ledger
class TestCensusMetroModel:
    """Tests for the CensusMetro model."""

    def test_create_census_metro(self, session: Session) -> None:
        """Can create a census metro record."""
        # First create a metro area for the foreign key
        metro = MetroArea(cbsa_code="31080", name="Los Angeles-Long Beach-Anaheim")
        session.add(metro)
        session.commit()

        census = CensusMetro(
            cbsa_code="31080",
            year=2022,
            total_pop=13200998,
            median_income=80440.0,
            gini_index=0.49,
            median_rent=1750.0,
            median_home_value=750000.0,
        )
        session.add(census)
        session.commit()

        result = session.query(CensusMetro).filter_by(cbsa_code="31080").first()
        assert result is not None
        assert result.total_pop == 13200998
        assert result.gini_index == 0.49


@pytest.mark.ledger
class TestFredIndicatorModel:
    """Tests for the FredIndicator model."""

    def test_create_fred_indicator(self, session: Session) -> None:
        """Can create a FRED indicator record."""
        indicator = FredIndicator(
            year=2023,
            quarter=4,
            gdp_billions=27610.3,
            unemployment_pct=3.7,
            cpi=306.746,
            fed_funds_rate=5.33,
            federal_debt_millions=34001493.0,
            m2_money_supply=20866.0,
            median_income=74580.0,
        )
        session.add(indicator)
        session.commit()

        result = session.query(FredIndicator).filter_by(year=2023).first()
        assert result is not None
        assert result.gdp_billions == 27610.3
        assert result.quarter == 4

    def test_fred_indicator_annual_data(self, session: Session) -> None:
        """Can create annual FRED data with NULL quarter."""
        indicator = FredIndicator(
            year=2023,
            quarter=None,  # Annual data
            gdp_billions=25460.0,
        )
        session.add(indicator)
        session.commit()

        result = session.query(FredIndicator).filter_by(year=2023).first()
        assert result is not None
        assert result.quarter is None


@pytest.mark.ledger
class TestUnionMembershipModel:
    """Tests for the UnionMembership model."""

    def test_create_union_membership(self, session: Session) -> None:
        """Can create a union membership record."""
        state = State(fips="36", name="New York", abbreviation="NY")
        session.add(state)
        session.commit()

        membership = UnionMembership(
            state_fips="36",
            year=2023,
            total_employed=9200000,
            union_members=2000000,
            union_pct=21.7,
        )
        session.add(membership)
        session.commit()

        result = session.query(UnionMembership).filter_by(state_fips="36").first()
        assert result is not None
        assert result.union_pct == 21.7


@pytest.mark.ledger
class TestStrategicResourceModel:
    """Tests for the StrategicResource model."""

    def test_create_strategic_resource(self, session: Session) -> None:
        """Can create a strategic resource record."""
        resource = StrategicResource(
            resource_id="R002",
            resource_name="Crude Oil",
            year=2023,
            annual_production=4300000000.0,
            production_unit="barrels",
            strategic_reserve=350000000.0,
            reserve_unit="barrels",
        )
        session.add(resource)
        session.commit()

        result = session.query(StrategicResource).filter_by(resource_id="R002").first()
        assert result is not None
        assert result.resource_name == "Crude Oil"
        assert result.annual_production == 4300000000.0

    def test_strategic_resource_multiple_years(self, session: Session) -> None:
        """Can track resource data across multiple years."""
        resources = [
            StrategicResource(
                resource_id="R002",
                resource_name="Crude Oil",
                year=2021,
                annual_production=4000000000.0,
                production_unit="barrels",
            ),
            StrategicResource(
                resource_id="R002",
                resource_name="Crude Oil",
                year=2022,
                annual_production=4150000000.0,
                production_unit="barrels",
            ),
            StrategicResource(
                resource_id="R002",
                resource_name="Crude Oil",
                year=2023,
                annual_production=4300000000.0,
                production_unit="barrels",
            ),
        ]
        session.add_all(resources)
        session.commit()

        result = session.query(StrategicResource).filter_by(resource_id="R002").all()
        assert len(result) == 3


@pytest.mark.ledger
class TestForeignKeyRelationships:
    """Tests for foreign key relationships between tables."""

    def test_census_population_requires_valid_state(self, session: Session) -> None:
        """CensusPopulation state_fips must reference existing state (if not NULL)."""
        # SQLite doesn't enforce FK by default, but we should test the constraint exists
        # This test verifies the FK is defined in the schema
        inspector = inspect(session.bind)
        fks = inspector.get_foreign_keys("census_population")

        state_fk = [fk for fk in fks if fk["referred_table"] == "states"]
        assert len(state_fk) == 1
        assert state_fk[0]["constrained_columns"] == ["state_fips"]

    def test_census_metro_requires_valid_cbsa(self, session: Session) -> None:
        """CensusMetro cbsa_code must reference existing metro area (if not NULL)."""
        inspector = inspect(session.bind)
        fks = inspector.get_foreign_keys("census_metro")

        metro_fk = [fk for fk in fks if fk["referred_table"] == "metro_areas"]
        assert len(metro_fk) == 1
        assert metro_fk[0]["constrained_columns"] == ["cbsa_code"]

    def test_union_membership_requires_valid_state(self, session: Session) -> None:
        """UnionMembership state_fips must reference existing state (if not NULL)."""
        inspector = inspect(session.bind)
        fks = inspector.get_foreign_keys("union_membership")

        state_fk = [fk for fk in fks if fk["referred_table"] == "states"]
        assert len(state_fk) == 1
        assert state_fk[0]["constrained_columns"] == ["state_fips"]
