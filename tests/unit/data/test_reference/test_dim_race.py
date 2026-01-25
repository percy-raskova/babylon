"""Unit tests for DimRace dimension table and Census race/ethnicity handling.

These tests verify the DimRace schema structure and the FactTableSpec
dataclass configuration used in the data-driven Census loader architecture.

Tests follow the patterns established in test_3nf_compliance.py for schema
validation and test structure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import DimRace

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


# Census race codes following the A-I suffix scheme plus T for Total
VALID_RACE_CODES = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "T"}


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


class TestDimRaceSchema:
    """Test DimRace table structure and constraints."""

    def test_tablename_follows_dimension_convention(self) -> None:
        """DimRace should have 'dim_' prefix."""
        assert DimRace.__tablename__ == "dim_race"

    def test_has_primary_key(self) -> None:
        """DimRace should have a primary key defined."""
        pk_columns = list(DimRace.__table__.primary_key.columns)
        assert len(pk_columns) == 1
        assert pk_columns[0].name == "race_id"

    def test_race_code_is_unique(self) -> None:
        """race_code should have a unique constraint."""
        race_code_col = DimRace.__table__.columns["race_code"]
        assert race_code_col.unique is True

    def test_race_code_is_not_nullable(self) -> None:
        """race_code should be NOT NULL."""
        race_code_col = DimRace.__table__.columns["race_code"]
        assert race_code_col.nullable is False

    def test_race_name_is_not_nullable(self) -> None:
        """race_name should be NOT NULL."""
        race_name_col = DimRace.__table__.columns["race_name"]
        assert race_name_col.nullable is False

    def test_race_short_name_is_not_nullable(self) -> None:
        """race_short_name should be NOT NULL."""
        race_short_name_col = DimRace.__table__.columns["race_short_name"]
        assert race_short_name_col.nullable is False

    def test_has_check_constraint_for_race_code(self, engine: Engine) -> None:
        """race_code should be constrained to valid Census codes."""
        # The schema should have a check constraint for race_code validity
        from sqlalchemy import inspect

        inspector = inspect(engine)
        check_constraints = inspector.get_check_constraints("dim_race")

        # Find the race_code check constraint
        race_code_constraint = None
        for cc in check_constraints:
            if "race_code" in cc.get("sqltext", ""):
                race_code_constraint = cc
                break

        assert race_code_constraint is not None, "Missing CHECK constraint for race_code"

        # Verify it includes all valid codes
        constraint_text = race_code_constraint.get("sqltext", "")
        for code in VALID_RACE_CODES:
            assert f"'{code}'" in constraint_text, (
                f"race_code CHECK constraint should include '{code}'"
            )

    def test_has_boolean_flags(self) -> None:
        """DimRace should have is_hispanic_ethnicity and is_indigenous flags."""
        columns = {c.name for c in DimRace.__table__.columns}
        assert "is_hispanic_ethnicity" in columns
        assert "is_indigenous" in columns

    def test_has_display_order(self) -> None:
        """DimRace should have display_order for UI ordering."""
        columns = {c.name for c in DimRace.__table__.columns}
        assert "display_order" in columns


class TestDimRaceDataIntegrity:
    """Test DimRace data insertion and constraints at runtime."""

    def test_can_insert_valid_race_codes(self, session: Session) -> None:
        """Should be able to insert all valid Census race codes."""
        for i, code in enumerate(sorted(VALID_RACE_CODES)):
            race = DimRace(
                race_code=code,
                race_name=f"Test Race {code}",
                race_short_name=code,
                display_order=i,
            )
            session.add(race)

        session.flush()

        # Verify all were inserted
        count = session.query(DimRace).count()
        assert count == len(VALID_RACE_CODES)

    def test_reject_duplicate_race_code(self, session: Session) -> None:
        """Should reject duplicate race_code values."""
        from sqlalchemy.exc import IntegrityError

        race1 = DimRace(race_code="A", race_name="White alone", race_short_name="White")
        race2 = DimRace(race_code="A", race_name="Duplicate White", race_short_name="Dup")

        session.add(race1)
        session.flush()

        session.add(race2)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_reject_invalid_race_code(self, session: Session) -> None:
        """Should reject race codes not in the valid set."""
        from sqlalchemy.exc import IntegrityError

        invalid_race = DimRace(
            race_code="X",  # Invalid - not in A-I or T
            race_name="Invalid Race",
            race_short_name="Invalid",
        )
        session.add(invalid_race)

        with pytest.raises(IntegrityError):
            session.flush()

    def test_aian_flags_correct_values(self, session: Session) -> None:
        """AIAN (code C) should have is_indigenous=True."""
        aian = DimRace(
            race_code="C",
            race_name="American Indian and Alaska Native alone",
            race_short_name="AIAN",
            is_indigenous=True,
            is_hispanic_ethnicity=False,
        )
        session.add(aian)
        session.flush()

        loaded = session.query(DimRace).filter(DimRace.race_code == "C").one()
        assert loaded.is_indigenous is True
        assert loaded.is_hispanic_ethnicity is False

    def test_hispanic_flag_correct_for_code_i(self, session: Session) -> None:
        """Hispanic (code I) should have is_hispanic_ethnicity=True."""
        hispanic = DimRace(
            race_code="I",
            race_name="Hispanic or Latino",
            race_short_name="Hispanic",
            is_indigenous=False,
            is_hispanic_ethnicity=True,
        )
        session.add(hispanic)
        session.flush()

        loaded = session.query(DimRace).filter(DimRace.race_code == "I").one()
        assert loaded.is_hispanic_ethnicity is True
        assert loaded.is_indigenous is False


class TestFactTableSpec:
    """Test FactTableSpec dataclass from the Census loader.

    Validates the data-driven loader architecture introduced in Phase 2.
    """

    def test_fact_table_spec_is_frozen(self) -> None:
        """FactTableSpec should be immutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        spec = FACT_TABLE_SPECS[0]

        with pytest.raises(FrozenInstanceError):
            spec.table_id = "modified"  # type: ignore[misc]

    def test_all_specs_have_required_fields(self) -> None:
        """All specs must have table_id, fact_class, label, value_field."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        for spec in FACT_TABLE_SPECS:
            assert spec.table_id, f"{spec} missing table_id"
            assert spec.fact_class, f"{spec} missing fact_class"
            assert spec.label, f"{spec} missing label"
            assert spec.value_field, f"{spec} missing value_field"

    def test_race_suffixes_is_tuple(self) -> None:
        """race_suffixes should be a tuple for immutability."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        for spec in FACT_TABLE_SPECS:
            assert isinstance(spec.race_suffixes, tuple), (
                f"{spec.table_id} race_suffixes should be tuple, got {type(spec.race_suffixes)}"
            )

    def test_all_race_suffixes_are_valid_codes(self) -> None:
        """All race_suffixes should be in the valid Census A-I set."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        valid_suffixes = {"A", "B", "C", "D", "E", "F", "G", "H", "I"}

        for spec in FACT_TABLE_SPECS:
            for suffix in spec.race_suffixes:
                assert suffix in valid_suffixes, (
                    f"{spec.table_id} has invalid race suffix '{suffix}'"
                )

    def test_at_least_some_specs_have_race_suffixes(self) -> None:
        """At least some table specs should have race iterations enabled."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        specs_with_race = [s for s in FACT_TABLE_SPECS if s.race_suffixes]
        assert len(specs_with_race) > 0, "No table specs have race_suffixes defined"

    def test_at_least_some_specs_without_race_suffixes(self) -> None:
        """Some table specs should NOT have race iterations (e.g., Gini)."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        specs_without_race = [s for s in FACT_TABLE_SPECS if not s.race_suffixes]
        # This is expected for tables like B19083 (Gini index) which don't have race iterations
        assert len(specs_without_race) > 0, (
            "Expected some specs without race iterations (e.g., Gini)"
        )

    def test_fact_classes_are_valid_orm_models(self) -> None:
        """fact_class should reference valid SQLAlchemy models."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS
        from babylon.data.reference.database import NormalizedBase

        for spec in FACT_TABLE_SPECS:
            # Should be a class with __tablename__
            assert hasattr(spec.fact_class, "__tablename__"), (
                f"{spec.table_id} fact_class missing __tablename__"
            )
            # Should be a subclass of NormalizedBase
            assert issubclass(spec.fact_class, NormalizedBase), (
                f"{spec.table_id} fact_class not a NormalizedBase subclass"
            )


class TestRaceCodesConstant:
    """Test the RACE_CODES constant in the Census loader."""

    def test_race_codes_has_10_entries(self) -> None:
        """RACE_CODES should have 10 entries (T + A-I)."""
        from babylon.data.census.loader_3nf import RACE_CODES

        assert len(RACE_CODES) == 10

    def test_race_codes_includes_total(self) -> None:
        """RACE_CODES should include T for Total."""
        from babylon.data.census.loader_3nf import RACE_CODES

        codes = {r["code"] for r in RACE_CODES}
        assert "T" in codes

    def test_race_codes_have_required_fields(self) -> None:
        """Each RACE_CODES entry should have code, name, short, etc."""
        from babylon.data.census.loader_3nf import RACE_CODES

        for race in RACE_CODES:
            assert "code" in race, f"Missing 'code' in {race}"
            assert "name" in race, f"Missing 'name' in {race}"
            assert "short" in race, f"Missing 'short' in {race}"
            assert "hispanic" in race, f"Missing 'hispanic' in {race}"
            assert "indigenous" in race, f"Missing 'indigenous' in {race}"
            assert "order" in race, f"Missing 'order' in {race}"

    def test_aian_has_indigenous_true(self) -> None:
        """AIAN (code C) should have indigenous=True."""
        from babylon.data.census.loader_3nf import RACE_CODES

        aian = next(r for r in RACE_CODES if r["code"] == "C")
        assert aian["indigenous"] is True
        assert aian["short"] == "AIAN"

    def test_hispanic_has_hispanic_true(self) -> None:
        """Hispanic (code I) should have hispanic=True."""
        from babylon.data.census.loader_3nf import RACE_CODES

        hispanic = next(r for r in RACE_CODES if r["code"] == "I")
        assert hispanic["hispanic"] is True


class TestFullRaceSuffixesConstant:
    """Test the FULL_RACE_SUFFIXES constant."""

    def test_full_race_suffixes_is_9_elements(self) -> None:
        """FULL_RACE_SUFFIXES should have 9 elements (A-I)."""
        from babylon.data.census.loader_3nf import FULL_RACE_SUFFIXES

        assert len(FULL_RACE_SUFFIXES) == 9

    def test_full_race_suffixes_is_tuple(self) -> None:
        """FULL_RACE_SUFFIXES should be a tuple."""
        from babylon.data.census.loader_3nf import FULL_RACE_SUFFIXES

        assert isinstance(FULL_RACE_SUFFIXES, tuple)

    def test_full_race_suffixes_does_not_include_total(self) -> None:
        """FULL_RACE_SUFFIXES should NOT include T (Total is base table)."""
        from babylon.data.census.loader_3nf import FULL_RACE_SUFFIXES

        assert "T" not in FULL_RACE_SUFFIXES
