"""Unit tests for DimensionLoader generic class.

Tests the 3-tier caching pattern (in-memory -> database -> create)
used for idempotent dimension loading across all data loaders.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.loaders.dimension_loader import DimensionLoader
from babylon.data.normalize import schema as _schema  # noqa: F401  # Import for side effects
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import DimGender, DimOwnership


def _make_session() -> Session:
    """Create an in-memory DuckDB session for testing."""
    engine = create_engine("duckdb:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


class TestDimensionLoaderBasics:
    """Tests for basic DimensionLoader functionality."""

    def test_get_or_create_creates_new_record(self) -> None:
        """get_or_create creates a new record when key doesn't exist."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")

            gender_id = loader.get_or_create(gender_code="male", gender_label="Male")

            assert gender_id is not None
            assert gender_id > 0
            # Verify record exists in database
            record = session.query(DimGender).filter(DimGender.gender_code == "male").first()
            assert record is not None
            assert record.gender_label == "Male"
        finally:
            session.close()

    def test_get_or_create_returns_same_id_for_same_key(self) -> None:
        """get_or_create returns the same ID when called with the same key."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")

            id1 = loader.get_or_create(gender_code="female", gender_label="Female")
            id2 = loader.get_or_create(gender_code="female", gender_label="Female")

            assert id1 == id2
        finally:
            session.close()

    def test_get_or_create_returns_different_ids_for_different_keys(self) -> None:
        """get_or_create returns different IDs for different keys."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")

            id1 = loader.get_or_create(gender_code="male", gender_label="Male")
            id2 = loader.get_or_create(gender_code="female", gender_label="Female")

            assert id1 != id2
        finally:
            session.close()


class TestDimensionLoaderCache:
    """Tests for DimensionLoader caching behavior."""

    def test_cache_property_returns_lookup_dict(self) -> None:
        """cache property returns the key->id mapping dictionary."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")
            loader.get_or_create(gender_code="male", gender_label="Male")
            loader.get_or_create(gender_code="female", gender_label="Female")

            cache = loader.cache

            assert isinstance(cache, dict)
            assert "male" in cache
            assert "female" in cache
            assert len(cache) == 2
        finally:
            session.close()

    def test_len_returns_cache_size(self) -> None:
        """__len__ returns the number of cached records."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")
            assert len(loader) == 0

            loader.get_or_create(gender_code="male", gender_label="Male")
            assert len(loader) == 1

            loader.get_or_create(gender_code="female", gender_label="Female")
            assert len(loader) == 2
        finally:
            session.close()

    def test_contains_checks_cache(self) -> None:
        """__contains__ checks if key is in cache."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")
            loader.get_or_create(gender_code="male", gender_label="Male")

            assert "male" in loader
            assert "female" not in loader
        finally:
            session.close()

    def test_caches_database_lookups(self) -> None:
        """Database queries are cached to avoid repeated lookups."""
        session = _make_session()
        try:
            # Create a record directly
            gender = DimGender(gender_code="total", gender_label="Total")
            session.add(gender)
            session.flush()
            expected_id = gender.gender_id

            # Create loader and look up the record
            loader = DimensionLoader(session, DimGender, "gender_code")
            id1 = loader.get_or_create(gender_code="total", gender_label="Total")

            # Verify it's cached
            assert "total" in loader
            assert loader.cache["total"] == expected_id
            assert id1 == expected_id
        finally:
            session.close()


class TestDimensionLoaderInitializeFromDb:
    """Tests for initialize_from_db functionality."""

    def test_initialize_from_db_populates_cache(self) -> None:
        """initialize_from_db loads existing records into cache."""
        session = _make_session()
        try:
            # Create records directly in database
            session.add(DimGender(gender_code="male", gender_label="Male"))
            session.add(DimGender(gender_code="female", gender_label="Female"))
            session.flush()

            # Create fresh loader and initialize
            loader = DimensionLoader(session, DimGender, "gender_code")
            count = loader.initialize_from_db()

            assert count == 2
            assert "male" in loader
            assert "female" in loader
        finally:
            session.close()

    def test_initialize_from_db_returns_count(self) -> None:
        """initialize_from_db returns the number of records loaded."""
        session = _make_session()
        try:
            # Empty table
            loader = DimensionLoader(session, DimGender, "gender_code")
            count = loader.initialize_from_db()
            assert count == 0

            # Add records
            session.add(DimGender(gender_code="male", gender_label="Male"))
            session.flush()

            loader2 = DimensionLoader(session, DimGender, "gender_code")
            count2 = loader2.initialize_from_db()
            assert count2 == 1
        finally:
            session.close()

    def test_initialize_from_db_enables_idempotent_loading(self) -> None:
        """Calling initialize_from_db prevents duplicate creation."""
        session = _make_session()
        try:
            # First loader creates record
            loader1 = DimensionLoader(session, DimGender, "gender_code")
            loader1.get_or_create(gender_code="male", gender_label="Male")
            session.commit()

            # Second loader initializes from DB, should find existing
            loader2 = DimensionLoader(session, DimGender, "gender_code")
            count = loader2.initialize_from_db()
            assert count == 1

            id2 = loader2.get_or_create(gender_code="male", gender_label="Male")

            # Should not create a duplicate
            total = session.query(DimGender).count()
            assert total == 1
            assert id2 == loader1.cache["male"]
        finally:
            session.close()


class TestDimensionLoaderGet:
    """Tests for the get() lookup method."""

    def test_get_returns_none_for_missing_key(self) -> None:
        """get() returns None when key doesn't exist."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")

            result = loader.get("nonexistent")

            assert result is None
        finally:
            session.close()

    def test_get_returns_id_for_existing_key_in_cache(self) -> None:
        """get() returns ID when key exists in cache."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")
            expected_id = loader.get_or_create(gender_code="male", gender_label="Male")

            result = loader.get("male")

            assert result == expected_id
        finally:
            session.close()

    def test_get_returns_id_for_existing_key_in_database(self) -> None:
        """get() returns ID when key exists in database but not cache."""
        session = _make_session()
        try:
            # Create directly in database
            gender = DimGender(gender_code="total", gender_label="Total")
            session.add(gender)
            session.flush()
            expected_id = gender.gender_id

            # Fresh loader (empty cache)
            loader = DimensionLoader(session, DimGender, "gender_code")
            result = loader.get("total")

            assert result == expected_id
            # Should now be cached
            assert "total" in loader
        finally:
            session.close()


class TestDimensionLoaderErrors:
    """Tests for error handling."""

    def test_raises_key_error_when_key_column_missing(self) -> None:
        """get_or_create raises KeyError if key_column not in kwargs."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimGender, "gender_code")

            with pytest.raises(KeyError):
                loader.get_or_create(gender_label="Male")  # Missing gender_code
        finally:
            session.close()


class TestDimensionLoaderWithDerivedFields:
    """Tests for loaders that need derived field computation."""

    def test_works_with_derived_boolean_fields(self) -> None:
        """DimensionLoader works with models that have derived boolean fields."""
        session = _make_session()
        try:
            loader = DimensionLoader(session, DimOwnership, "own_code")

            # Ownership "5" is private sector
            id1 = loader.get_or_create(
                own_code="5",
                own_title="Private",
                is_government=False,
                is_private=True,
            )

            # Ownership "1" is government
            id2 = loader.get_or_create(
                own_code="1",
                own_title="Federal Government",
                is_government=True,
                is_private=False,
            )

            assert id1 != id2

            # Verify derived fields were stored correctly
            private = session.query(DimOwnership).filter(DimOwnership.own_code == "5").first()
            assert private is not None
            assert private.is_private is True
            assert private.is_government is False

            govt = session.query(DimOwnership).filter(DimOwnership.own_code == "1").first()
            assert govt is not None
            assert govt.is_government is True
            assert govt.is_private is False
        finally:
            session.close()

    def test_multiple_loaders_same_session(self) -> None:
        """Multiple DimensionLoaders can coexist on the same session."""
        session = _make_session()
        try:
            gender_loader = DimensionLoader(session, DimGender, "gender_code")
            ownership_loader = DimensionLoader(session, DimOwnership, "own_code")

            gender_id = gender_loader.get_or_create(gender_code="male", gender_label="Male")
            ownership_id = ownership_loader.get_or_create(
                own_code="5", own_title="Private", is_government=False, is_private=True
            )

            # Both should work independently
            assert gender_id > 0
            assert ownership_id > 0
            assert len(gender_loader) == 1
            assert len(ownership_loader) == 1
        finally:
            session.close()
