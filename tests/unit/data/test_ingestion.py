"""Tests for data ingestion scripts.

These tests verify:
1. CSV parsing and validation
2. Data transformation into SQLAlchemy models
3. Error handling for invalid data
4. Full ingestion pipeline
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.database import Base
from babylon.data.external.base import IngestResult, parse_float, parse_int, validate_year
from babylon.data.external.bls import (
    StrategicResourceIngester,
    UnionMembershipIngester,
)
from babylon.data.external.census import (
    CensusMetroIngester,
    CensusPopulationIngester,
    MetroAreaIngester,
    StateIngester,
)
from babylon.data.external.fred import FredIndicatorIngester
from babylon.data.schema import (
    CensusPopulation,
    FredIndicator,
    MetroArea,
    State,
    StrategicResource,
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


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================


@pytest.mark.ledger
class TestParseUtilities:
    """Tests for parsing utility functions."""

    def test_parse_int_valid(self) -> None:
        """Parse valid integer strings."""
        assert parse_int("123") == 123
        assert parse_int("0") == 0
        assert parse_int("-456") == -456

    def test_parse_int_with_commas(self) -> None:
        """Parse integers with comma separators."""
        assert parse_int("1,234,567") == 1234567
        assert parse_int("1,000") == 1000

    def test_parse_int_empty(self) -> None:
        """Return None for empty strings."""
        assert parse_int("") is None
        assert parse_int("  ") is None
        assert parse_int(None) is None

    def test_parse_int_invalid(self) -> None:
        """Return default for invalid strings."""
        assert parse_int("abc") is None
        assert parse_int("12.34") is None  # Float string is invalid for int
        assert parse_int("abc", default=0) == 0

    def test_parse_float_valid(self) -> None:
        """Parse valid float strings."""
        assert parse_float("123.45") == 123.45
        assert parse_float("0.0") == 0.0
        assert parse_float("-456.78") == -456.78

    def test_parse_float_with_commas(self) -> None:
        """Parse floats with comma separators."""
        assert parse_float("1,234,567.89") == 1234567.89
        assert parse_float("1,000.50") == 1000.50

    def test_parse_float_empty(self) -> None:
        """Return None for empty strings."""
        assert parse_float("") is None
        assert parse_float("  ") is None
        assert parse_float(None) is None

    def test_parse_float_invalid(self) -> None:
        """Return default for invalid strings."""
        assert parse_float("abc") is None
        assert parse_float("abc", default=0.0) == 0.0

    def test_validate_year_valid(self) -> None:
        """Validate valid year values."""
        assert validate_year("2023") == []
        assert validate_year("1900") == []
        assert validate_year("2100") == []

    def test_validate_year_missing(self) -> None:
        """Validation fails for missing year."""
        errors = validate_year(None)
        assert len(errors) == 1
        assert "Missing required field: year" in errors[0]

        errors = validate_year("")
        assert len(errors) == 1

    def test_validate_year_out_of_range(self) -> None:
        """Validation fails for out-of-range years."""
        errors = validate_year("1800")  # Before default min 1900
        assert len(errors) == 1
        assert "out of range" in errors[0].lower()

        errors = validate_year("2200")  # After default max 2100
        assert len(errors) == 1
        assert "out of range" in errors[0].lower()

    def test_validate_year_invalid(self) -> None:
        """Validation fails for non-numeric years."""
        errors = validate_year("abc")
        assert len(errors) == 1
        assert "invalid" in errors[0].lower()

    def test_validate_year_custom_range(self) -> None:
        """Validation uses custom min/max years."""
        # Census data can go back to 1790
        errors = validate_year("1800", min_year=1790)
        assert len(errors) == 0  # 1800 is valid with 1790 min

        errors = validate_year("1750", min_year=1790)
        assert len(errors) == 1  # 1750 is out of range


# =============================================================================
# STATE INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestStateIngester:
    """Tests for StateIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid state row."""
        ingester = StateIngester()
        row = {"fips": "01", "name": "Alabama", "abbreviation": "AL"}

        state = ingester.parse_row(row)

        assert state is not None
        assert state.fips == "01"
        assert state.name == "Alabama"
        assert state.abbreviation == "AL"

    def test_validate_missing_fips(self) -> None:
        """Validation fails for missing FIPS."""
        ingester = StateIngester()
        row = {"fips": "", "name": "Alabama", "abbreviation": "AL"}

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("fips" in e.lower() for e in errors)

    def test_validate_invalid_fips_length(self) -> None:
        """Validation fails for wrong FIPS length."""
        ingester = StateIngester()
        row = {"fips": "001", "name": "Alabama", "abbreviation": "AL"}

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("2 characters" in e for e in errors)

    def test_validate_missing_name(self) -> None:
        """Validation fails for missing name."""
        ingester = StateIngester()
        row = {"fips": "01", "name": "", "abbreviation": "AL"}

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("name" in e.lower() for e in errors)

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple state rows."""
        ingester = StateIngester()
        rows = [
            {"fips": "01", "name": "Alabama", "abbreviation": "AL"},
            {"fips": "02", "name": "Alaska", "abbreviation": "AK"},
            {"fips": "04", "name": "Arizona", "abbreviation": "AZ"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 3
        assert result.rows_read == 3
        assert session.query(State).count() == 3


# =============================================================================
# METRO AREA INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestMetroAreaIngester:
    """Tests for MetroAreaIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid metro area row."""
        ingester = MetroAreaIngester()
        row = {"cbsa_code": "31080", "name": "Los Angeles-Long Beach-Anaheim"}

        metro = ingester.parse_row(row)

        assert metro is not None
        assert metro.cbsa_code == "31080"
        assert metro.name == "Los Angeles-Long Beach-Anaheim"

    def test_validate_invalid_cbsa_length(self) -> None:
        """Validation fails for wrong CBSA code length."""
        ingester = MetroAreaIngester()
        row = {"cbsa_code": "3108", "name": "Los Angeles"}  # 4 chars, should be 5

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("5 characters" in e for e in errors)

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple metro area rows."""
        ingester = MetroAreaIngester()
        rows = [
            {"cbsa_code": "31080", "name": "Los Angeles-Long Beach-Anaheim"},
            {"cbsa_code": "16980", "name": "Chicago-Naperville-Elgin"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 2
        assert session.query(MetroArea).count() == 2


# =============================================================================
# CENSUS POPULATION INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestCensusPopulationIngester:
    """Tests for CensusPopulationIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid census population row."""
        ingester = CensusPopulationIngester()
        row = {
            "state_fips": "06",
            "year": "2022",
            "total_pop": "39538223",
            "employed": "18000000",
            "unemployed": "1200000",
            "self_employed": "2500000",
            "median_income": "78672.50",
            "poverty_pop": "4500000",
        }

        census = ingester.parse_row(row)

        assert census is not None
        assert census.state_fips == "06"
        assert census.year == 2022
        assert census.total_pop == 39538223
        assert census.median_income == 78672.50

    def test_parse_row_with_null_state(self) -> None:
        """Parse a row with null state_fips (national data)."""
        ingester = CensusPopulationIngester()
        row = {
            "state_fips": "",
            "year": "2022",
            "total_pop": "331000000",
        }

        census = ingester.parse_row(row)

        assert census is not None
        assert census.state_fips is None
        assert census.total_pop == 331000000

    def test_validate_missing_year(self) -> None:
        """Validation fails for missing year."""
        ingester = CensusPopulationIngester()
        row = {"state_fips": "06", "year": ""}

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("year" in e.lower() for e in errors)

    def test_validate_invalid_year(self) -> None:
        """Validation fails for invalid year."""
        ingester = CensusPopulationIngester()
        row = {"state_fips": "06", "year": "abc"}

        errors = ingester.validate_row(row)

        assert len(errors) > 0

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple census population rows."""
        # First create reference states
        session.add(State(fips="06", name="California", abbreviation="CA"))
        session.add(State(fips="48", name="Texas", abbreviation="TX"))
        session.commit()

        ingester = CensusPopulationIngester()
        rows = [
            {"state_fips": "06", "year": "2022", "total_pop": "39538223"},
            {"state_fips": "48", "year": "2022", "total_pop": "29145505"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 2
        assert session.query(CensusPopulation).count() == 2


# =============================================================================
# CENSUS METRO INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestCensusMetroIngester:
    """Tests for CensusMetroIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid census metro row."""
        ingester = CensusMetroIngester()
        row = {
            "cbsa_code": "31080",
            "year": "2022",
            "total_pop": "13200998",
            "median_income": "80440.00",
            "gini_index": "0.49",
            "median_rent": "1750.00",
            "median_home_value": "750000.00",
        }

        census = ingester.parse_row(row)

        assert census is not None
        assert census.cbsa_code == "31080"
        assert census.gini_index == 0.49

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple census metro rows."""
        # First create reference metro areas
        session.add(MetroArea(cbsa_code="31080", name="Los Angeles"))
        session.add(MetroArea(cbsa_code="16980", name="Chicago"))
        session.commit()

        ingester = CensusMetroIngester()
        rows = [
            {"cbsa_code": "31080", "year": "2022", "total_pop": "13200998"},
            {"cbsa_code": "16980", "year": "2022", "total_pop": "9500000"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 2


# =============================================================================
# FRED INDICATOR INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestFredIndicatorIngester:
    """Tests for FredIndicatorIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid FRED indicator row."""
        ingester = FredIndicatorIngester()
        row = {
            "year": "2023",
            "quarter": "4",
            "gdp_billions": "27610.3",
            "unemployment_pct": "3.7",
            "cpi": "306.746",
            "fed_funds_rate": "5.33",
            "federal_debt_millions": "34001493",
            "m2_money_supply": "20866",
            "median_income": "74580",
        }

        indicator = ingester.parse_row(row)

        assert indicator is not None
        assert indicator.year == 2023
        assert indicator.quarter == 4
        assert indicator.gdp_billions == 27610.3

    def test_parse_row_without_quarter(self) -> None:
        """Parse annual data without quarter."""
        ingester = FredIndicatorIngester()
        row = {
            "year": "2023",
            "quarter": "",
            "gdp_billions": "25460.0",
        }

        indicator = ingester.parse_row(row)

        assert indicator is not None
        assert indicator.quarter is None

    def test_validate_invalid_quarter(self) -> None:
        """Validation fails for invalid quarter."""
        ingester = FredIndicatorIngester()
        row = {"year": "2023", "quarter": "5"}  # Invalid: must be 1-4

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("quarter" in e.lower() for e in errors)

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple FRED indicator rows."""
        ingester = FredIndicatorIngester()
        rows = [
            {"year": "2022", "quarter": "1", "gdp_billions": "24000"},
            {"year": "2022", "quarter": "2", "gdp_billions": "24500"},
            {"year": "2022", "quarter": "3", "gdp_billions": "25000"},
            {"year": "2022", "quarter": "4", "gdp_billions": "25500"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 4
        assert session.query(FredIndicator).count() == 4


# =============================================================================
# UNION MEMBERSHIP INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestUnionMembershipIngester:
    """Tests for UnionMembershipIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid union membership row."""
        ingester = UnionMembershipIngester()
        row = {
            "state_fips": "36",
            "year": "2023",
            "total_employed": "9200000",
            "union_members": "2000000",
            "union_pct": "21.7",
        }

        membership = ingester.parse_row(row)

        assert membership is not None
        assert membership.state_fips == "36"
        assert membership.union_pct == 21.7

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple union membership rows."""
        # First create reference states
        session.add(State(fips="36", name="New York", abbreviation="NY"))
        session.add(State(fips="06", name="California", abbreviation="CA"))
        session.commit()

        ingester = UnionMembershipIngester()
        rows = [
            {"state_fips": "36", "year": "2023", "union_pct": "21.7"},
            {"state_fips": "06", "year": "2023", "union_pct": "15.9"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 2


# =============================================================================
# STRATEGIC RESOURCE INGESTER TESTS
# =============================================================================


@pytest.mark.ledger
class TestStrategicResourceIngester:
    """Tests for StrategicResourceIngester."""

    def test_parse_valid_row(self) -> None:
        """Parse a valid strategic resource row."""
        ingester = StrategicResourceIngester()
        row = {
            "resource_id": "R002",
            "resource_name": "Crude Oil",
            "year": "2023",
            "annual_production": "4300000000",
            "production_unit": "barrels",
            "strategic_reserve": "350000000",
            "reserve_unit": "barrels",
        }

        resource = ingester.parse_row(row)

        assert resource is not None
        assert resource.resource_id == "R002"
        assert resource.resource_name == "Crude Oil"
        assert resource.annual_production == 4300000000.0

    def test_validate_missing_resource_id(self) -> None:
        """Validation fails for missing resource_id."""
        ingester = StrategicResourceIngester()
        row = {"resource_id": "", "resource_name": "Oil", "year": "2023"}

        errors = ingester.validate_row(row)

        assert len(errors) > 0
        assert any("resource_id" in e.lower() for e in errors)

    def test_ingest_rows(self, session: Session) -> None:
        """Ingest multiple strategic resource rows."""
        ingester = StrategicResourceIngester()
        rows = [
            {"resource_id": "R001", "resource_name": "Iron Ore", "year": "2023"},
            {"resource_id": "R002", "resource_name": "Crude Oil", "year": "2023"},
            {"resource_id": "R003", "resource_name": "Steel", "year": "2023"},
        ]

        result = ingester.ingest_rows(session, rows)

        assert result.success
        assert result.rows_inserted == 3
        assert session.query(StrategicResource).count() == 3


# =============================================================================
# INGEST RESULT TESTS
# =============================================================================


@pytest.mark.ledger
class TestIngestResult:
    """Tests for IngestResult dataclass."""

    def test_success_when_inserted(self) -> None:
        """Result is successful when rows are inserted with no errors."""
        result = IngestResult(
            source_file="test.csv",
            rows_read=10,
            rows_inserted=10,
        )

        assert result.success

    def test_not_success_with_errors(self) -> None:
        """Result is not successful when errors exist."""
        result = IngestResult(
            source_file="test.csv",
            rows_read=10,
            rows_inserted=5,
            errors=["Row 3: Invalid data"],
        )

        assert not result.success

    def test_not_success_when_no_rows_inserted(self) -> None:
        """Result is not successful when no rows were inserted."""
        result = IngestResult(
            source_file="test.csv",
            rows_read=10,
            rows_inserted=0,
            rows_skipped=10,
        )

        assert not result.success
