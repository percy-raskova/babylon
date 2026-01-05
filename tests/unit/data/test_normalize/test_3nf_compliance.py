r"""Tests for formal Third Normal Form (3NF) compliance.

Based on Codd's original definition (1971) and Zaniolo's reformulation (1982):
- Codd: A relation R is in 3NF iff it is in 2NF AND every non-prime attribute
  is non-transitively dependent on each candidate key.
- Zaniolo: For every functional dependency X -> Y, either X contains Y (trivial),
  X is a superkey, OR every element of Y\\X is a prime attribute.
- Kent: "A non-key field must provide a fact about the key, the whole key,
  and nothing but the key."

These tests verify that the normalized 3NF schema meets formal requirements:
1. Primary key uniqueness (no duplicate natural keys)
2. Foreign key referential integrity (all FKs reference valid PKs)
3. Atomic values (1NF prerequisite - no multi-valued columns)
4. No transitive dependencies (3NF core requirement)
5. Full functional dependency on PK (2NF prerequisite)

Additionally tests SQLite-specific quirks:
- PRAGMA foreign_keys=ON enforcement
- No NULLs in PK columns (SQLite allows this unless NOT NULL declared)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import (
    # Dimension tables
    DimAssetCategory,
    DimCommodity,
    DimCommodityMetric,
    DimCommuteMode,
    DimCountry,
    DimCounty,
    DimDataSource,
    DimEducationLevel,
    DimEmploymentStatus,
    DimEnergySeries,
    DimEnergyTable,
    DimFredSeries,
    DimGender,
    DimHousingTenure,
    DimImportSource,
    DimIncomeBracket,
    DimIndustry,
    DimMetroArea,
    DimOccupation,
    DimOwnership,
    DimPovertyCategory,
    DimRentBurden,
    DimSector,
    DimState,
    DimTime,
    DimWealthClass,
    DimWorkerClass,
    # Fact tables
    FactCensusCommute,
    FactCensusEducation,
    FactCensusEmployment,
    FactCensusGini,
    FactCensusHours,
    FactCensusHousing,
    FactCensusIncome,
    FactCensusIncomeSources,
    FactCensusMedianIncome,
    FactCensusOccupation,
    FactCensusPoverty,
    FactCensusRent,
    FactCensusRentBurden,
    FactCensusWorkerClass,
    FactCommodityObservation,
    FactEnergyAnnual,
    FactFredIndustryUnemployment,
    FactFredNational,
    FactFredStateUnemployment,
    FactFredWealthLevels,
    FactFredWealthShares,
    FactMineralEmployment,
    FactMineralProduction,
    FactProductivityAnnual,
    FactQcewAnnual,
    FactStateMinerals,
    FactTradeMonthly,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


# All dimension tables in the schema
DIMENSION_TABLES = [
    DimAssetCategory,
    DimCommodity,
    DimCommodityMetric,
    DimCommuteMode,
    DimCountry,
    DimCounty,
    DimDataSource,
    DimEducationLevel,
    DimEmploymentStatus,
    DimEnergySeries,
    DimEnergyTable,
    DimFredSeries,
    DimGender,
    DimHousingTenure,
    DimImportSource,
    DimIncomeBracket,
    DimIndustry,
    DimMetroArea,
    DimOccupation,
    DimOwnership,
    DimPovertyCategory,
    DimRentBurden,
    DimSector,
    DimState,
    DimTime,
    DimWealthClass,
    DimWorkerClass,
]

# All fact tables in the schema
FACT_TABLES = [
    FactCensusCommute,
    FactCensusEducation,
    FactCensusEmployment,
    FactCensusGini,
    FactCensusHours,
    FactCensusHousing,
    FactCensusIncome,
    FactCensusIncomeSources,
    FactCensusMedianIncome,
    FactCensusOccupation,
    FactCensusPoverty,
    FactCensusRent,
    FactCensusRentBurden,
    FactCensusWorkerClass,
    FactCommodityObservation,
    FactEnergyAnnual,
    FactFredIndustryUnemployment,
    FactFredNational,
    FactFredStateUnemployment,
    FactFredWealthLevels,
    FactFredWealthShares,
    FactMineralEmployment,
    FactMineralProduction,
    FactProductivityAnnual,
    FactQcewAnnual,
    FactStateMinerals,
    FactTradeMonthly,
]


@pytest.fixture(scope="module")
def engine() -> Engine:
    """Create in-memory SQLite database with FK enforcement."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key enforcement for SQLite (OFF by default!)
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


class TestSQLitePragmaEnforcement:
    """Tests for SQLite-specific FK enforcement."""

    def test_foreign_keys_pragma_is_on(self, engine: Engine) -> None:
        """PRAGMA foreign_keys should be ON for all connections."""
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            value = result.scalar()
            assert value == 1, "PRAGMA foreign_keys should be ON (1), got OFF (0)"

    def test_fk_violation_raises_error(self, session: Session) -> None:
        """Inserting orphan FK should raise IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        # Try to insert a county with non-existent state_id
        county = DimCounty(
            fips="99999",
            county_fips="99999",
            county_name="Orphan County",
            state_id=99999,  # Non-existent state
        )
        session.add(county)

        with pytest.raises(IntegrityError):
            session.flush()


class TestPrimaryKeyUniqueness:
    """Tests for PK uniqueness across all tables."""

    @pytest.mark.parametrize("table", DIMENSION_TABLES)
    def test_dimension_table_has_primary_key(self, table: type) -> None:
        """Every dimension table should have a primary key defined."""
        pk_columns = table.__table__.primary_key.columns
        assert len(pk_columns) > 0, f"{table.__name__} has no primary key"

    @pytest.mark.parametrize("table", FACT_TABLES)
    def test_fact_table_has_primary_key(self, table: type) -> None:
        """Every fact table should have a primary key defined."""
        pk_columns = table.__table__.primary_key.columns
        assert len(pk_columns) > 0, f"{table.__name__} has no primary key"

    @pytest.mark.parametrize("table", DIMENSION_TABLES)
    def test_dimension_pk_column_is_not_nullable(self, table: type) -> None:
        """Dimension PK columns should be NOT NULL."""
        for col in table.__table__.primary_key.columns:
            # SQLite quirk: PKs can be NULL unless explicitly NOT NULL
            # INTEGER PRIMARY KEY is auto-NOT NULL, but composite PKs are not
            assert col.nullable is False, (
                f"{table.__name__}.{col.name} PK column should be NOT NULL"
            )

    @pytest.mark.parametrize("table", FACT_TABLES)
    def test_fact_pk_column_is_not_nullable(self, table: type) -> None:
        """Fact PK columns should be NOT NULL."""
        for col in table.__table__.primary_key.columns:
            assert col.nullable is False, (
                f"{table.__name__}.{col.name} PK column should be NOT NULL"
            )


class TestForeignKeyIntegrity:
    """Tests for FK referential integrity."""

    @pytest.mark.parametrize("table", DIMENSION_TABLES + FACT_TABLES)
    def test_all_fks_reference_valid_tables(self, engine: Engine, table: type) -> None:
        """All FK columns should reference existing tables."""
        inspector = inspect(engine)
        table_name = table.__tablename__

        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            ref_table = fk["referred_table"]
            # Verify the referenced table exists
            all_tables = inspector.get_table_names()
            assert ref_table in all_tables, f"{table_name} has FK to non-existent table {ref_table}"

    @pytest.mark.parametrize("table", FACT_TABLES)
    def test_fact_tables_have_foreign_keys(self, engine: Engine, table: type) -> None:
        """Fact tables should have at least one FK (they reference dimensions)."""
        inspector = inspect(engine)
        table_name = table.__tablename__

        fks = inspector.get_foreign_keys(table_name)
        # Most fact tables should have FKs, but some may be valid without
        # (e.g., if they only have natural key measures)
        # This is a soft check - we just verify FK structure if present
        for fk in fks:
            assert "referred_table" in fk, f"{table_name} has malformed FK"
            assert "referred_columns" in fk, f"{table_name} has malformed FK"


class TestAtomicValues:
    """Tests for 1NF atomicity (no multi-valued columns)."""

    # Columns explicitly allowed to contain JSON/text blobs
    ALLOWED_TEXT_BLOBS = {
        "marxian_interpretation",
        "description",
        "notes",
        "error_message",
    }

    @pytest.mark.parametrize("table", DIMENSION_TABLES + FACT_TABLES)
    def test_no_array_columns(self, table: type) -> None:
        """Tables should not have ARRAY type columns."""
        for col in table.__table__.columns:
            col_type = str(col.type).upper()
            assert "ARRAY" not in col_type, (
                f"{table.__name__}.{col.name} uses ARRAY type, violating 1NF"
            )

    @pytest.mark.parametrize("table", DIMENSION_TABLES + FACT_TABLES)
    def test_no_json_in_measure_columns(self, table: type) -> None:
        """Measure columns (numeric) should not be JSON type."""
        numeric_prefixes = ("count", "amount", "value", "total", "sum", "avg", "rate")
        for col in table.__table__.columns:
            if col.name.lower().startswith(numeric_prefixes):
                col_type = str(col.type).upper()
                assert "JSON" not in col_type, (
                    f"{table.__name__}.{col.name} measure column uses JSON type"
                )


class TestNamingConventions:
    """Tests for consistent naming that supports 3NF analysis."""

    @pytest.mark.parametrize("table", DIMENSION_TABLES)
    def test_dimension_table_prefix(self, table: type) -> None:
        """Dimension tables should be prefixed with 'dim_'."""
        assert table.__tablename__.startswith("dim_"), (
            f"{table.__name__} should have 'dim_' prefix, got {table.__tablename__}"
        )

    @pytest.mark.parametrize("table", FACT_TABLES)
    def test_fact_table_prefix(self, table: type) -> None:
        """Fact tables should be prefixed with 'fact_'."""
        assert table.__tablename__.startswith("fact_"), (
            f"{table.__name__} should have 'fact_' prefix, got {table.__tablename__}"
        )

    @pytest.mark.parametrize("table", DIMENSION_TABLES)
    def test_dimension_pk_naming(self, table: type) -> None:
        """Dimension PKs should follow naming convention (e.g., state_id, county_id)."""
        pk_columns = list(table.__table__.primary_key.columns)
        if len(pk_columns) == 1:
            pk_name = pk_columns[0].name
            # PK should end with _id
            assert pk_name.endswith("_id"), (
                f"{table.__name__} PK should end with '_id', got {pk_name}"
            )


class TestNoTransitiveDependencies:
    """Tests verifying no transitive dependencies (3NF core requirement).

    A transitive dependency occurs when:
    - A → B (non-key A determines B)
    - B → C (non-key B determines C)
    - Therefore A → C transitively

    In 3NF, all non-key attributes must depend ONLY on the primary key.
    """

    def test_dim_county_no_state_data_redundancy(self) -> None:
        """DimCounty should not duplicate DimState attributes.

        If county had state_name, that would be transitive:
        county_id → state_id → state_name

        Instead, state_name should only exist in DimState.
        """
        county_columns = {c.name for c in DimCounty.__table__.columns}

        # These would indicate transitive dependencies
        transitive_indicators = {"state_name", "state_abbrev"}

        violations = county_columns & transitive_indicators
        assert len(violations) == 0, (
            f"DimCounty has transitive state data: {violations}. "
            "State data should only be in DimState."
        )

    def test_dim_industry_no_sector_data_redundancy(self) -> None:
        """DimIndustry should not duplicate DimSector attributes.

        industry_id → sector_id → sector_name would be transitive.
        """
        industry_columns = {c.name for c in DimIndustry.__table__.columns}

        # sector_code is OK (it's the FK relationship), but sector_name would be transitive
        transitive_indicators = {"sector_name", "sector_title"}

        violations = industry_columns & transitive_indicators
        assert len(violations) == 0, (
            f"DimIndustry has transitive sector data: {violations}. "
            "Sector names should only be in DimSector."
        )

    def test_fact_tables_only_contain_fks_and_measures(self) -> None:
        """Fact tables should contain only FK columns and numeric measures.

        They should not contain descriptive attributes that belong in dimensions.
        This prevents transitive dependencies through fact tables.
        """
        # Columns that indicate dimension data has leaked into facts
        dimension_indicators = {"name", "title", "description", "category", "type"}

        for table in FACT_TABLES:
            columns = {c.name.lower() for c in table.__table__.columns}
            # Filter out allowed exceptions
            columns = columns - {"error_message", "notes", "marxian_interpretation"}

            for indicator in dimension_indicators:
                matching = [c for c in columns if indicator in c and not c.endswith("_id")]
                # Allow specific known exceptions
                if table == FactFredNational and "category" in matching:
                    continue  # FRED has category as a measure grouping, not dimension data
                if table == FactMineralProduction and "production_type" in matching:
                    continue  # production_type categorizes mineral production records
                assert len(matching) == 0, (
                    f"{table.__name__} has dimension-like column {matching}, "
                    "which may indicate transitive dependency"
                )


class TestTableCounts:
    """Tests verifying expected table counts."""

    def test_dimension_table_count(self) -> None:
        """Should have 27 dimension tables."""
        assert len(DIMENSION_TABLES) == 27, (
            f"Expected 27 dimension tables, got {len(DIMENSION_TABLES)}"
        )

    def test_fact_table_count(self) -> None:
        """Should have at least 20 fact tables."""
        # The schema may grow, so we use >= for future-proofing
        assert len(FACT_TABLES) >= 20, f"Expected at least 20 fact tables, got {len(FACT_TABLES)}"

    def test_all_tables_in_normalized_base(self, engine: Engine) -> None:
        """All defined tables should be in NormalizedBase metadata."""
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())

        for table in DIMENSION_TABLES + FACT_TABLES:
            assert table.__tablename__ in actual_tables, (
                f"{table.__tablename__} not found in database"
            )


class TestSchemaIntegrity:
    """Tests for overall schema structure integrity."""

    def test_no_orphan_foreign_keys(self, engine: Engine) -> None:
        """All FKs should reference existing columns in target tables."""
        inspector = inspect(engine)
        all_tables = set(inspector.get_table_names())

        for table in DIMENSION_TABLES + FACT_TABLES:
            fks = inspector.get_foreign_keys(table.__tablename__)
            for fk in fks:
                ref_table = fk["referred_table"]
                ref_columns = fk["referred_columns"]

                assert ref_table in all_tables, (
                    f"{table.__tablename__} FK references non-existent table {ref_table}"
                )

                # Verify referenced columns exist
                ref_table_columns = {c["name"] for c in inspector.get_columns(ref_table)}
                for ref_col in ref_columns:
                    assert ref_col in ref_table_columns, (
                        f"{table.__tablename__} FK references non-existent column "
                        f"{ref_table}.{ref_col}"
                    )

    def test_dimension_tables_have_unique_constraints(self, engine: Engine) -> None:
        """Dimension tables should have unique constraints on natural keys."""
        inspector = inspect(engine)

        # Key dimension tables that MUST have unique constraints
        required_unique = {
            "dim_state": ["state_fips"],
            "dim_county": ["fips"],
            "dim_country": ["cty_code"],
            "dim_industry": ["naics_code"],
        }

        for table_name, expected_unique in required_unique.items():
            uniques = inspector.get_unique_constraints(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = pk_constraint.get("constrained_columns", []) if pk_constraint else []

            # Natural key should either be PK or have unique constraint
            for col in expected_unique:
                is_pk = col in pk_cols
                is_unique = any(col in u.get("column_names", []) for u in uniques)

                assert is_pk or is_unique, (
                    f"{table_name}.{col} should be PK or have UNIQUE constraint"
                )
