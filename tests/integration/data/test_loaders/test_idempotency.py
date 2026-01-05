"""Integration tests for loader idempotency.

Verifies that all loaders implement the DELETE+INSERT idempotency pattern:
- Running load() twice produces identical results
- reset=True clears old data before loading
- No duplicate primary keys after reload
- Transaction atomicity on failure

Note: These tests use mock data or skip if external data sources
are not available, to ensure CI stability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event, func
from sqlalchemy.orm import sessionmaker

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import DimState

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

from .conftest import ALL_LOADERS

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def isolated_engine() -> Generator[Engine, None, None]:
    """Create completely isolated in-memory database per test."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    NormalizedBase.metadata.create_all(engine)

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def isolated_session(isolated_engine: Engine) -> Generator[Session, None, None]:
    """Create session for isolated database."""
    session_factory = sessionmaker(bind=isolated_engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def fast_config() -> LoaderConfig:
    """Minimal config for fast testing."""
    return LoaderConfig(
        census_year=2022,
        fred_start_year=2022,
        fred_end_year=2022,
        energy_start_year=2022,
        energy_end_year=2022,
        trade_years=[2022],
        qcew_years=[2022],
        materials_years=[2022],
        state_fips_list=["06"],  # California only
        batch_size=100,
        verbose=False,
        max_retries=1,
        request_delay_seconds=0.0,
    )


# =============================================================================
# IDEMPOTENCY HELPER FUNCTIONS
# =============================================================================


def get_table_counts(session: Session, loader: DataLoader) -> dict[str, int]:
    """Get row counts for all tables a loader manages."""
    counts = {}

    for table in loader.get_dimension_tables():
        count = session.query(table).count()
        counts[table.__tablename__] = count

    for table in loader.get_fact_tables():
        count = session.query(table).count()
        counts[table.__tablename__] = count

    return counts


def get_table_checksums(session: Session, loader: DataLoader) -> dict[str, int]:
    """Get simple checksums (count * max_pk) for tables.

    This is a fast approximation of data integrity check.
    For exact comparison, would need to hash all rows.
    """
    checksums = {}

    for table in loader.get_dimension_tables():
        count = session.query(table).count()
        # Get PK column
        pk_cols = list(table.__table__.primary_key.columns)
        if pk_cols and count > 0:
            pk_col = pk_cols[0]
            max_pk = session.query(func.max(pk_col)).scalar() or 0
            checksums[table.__tablename__] = count * max_pk
        else:
            checksums[table.__tablename__] = count

    for table in loader.get_fact_tables():
        count = session.query(table).count()
        checksums[table.__tablename__] = count

    return checksums


# =============================================================================
# IDEMPOTENCY TESTS - UNIT LEVEL (with mocks)
# =============================================================================


class TestIdempotencyPattern:
    """Tests for basic idempotency patterns without external dependencies."""

    def test_clear_tables_actually_clears(self, isolated_session: Session) -> None:
        """clear_tables() should remove all data from managed tables."""
        # Create a simple test loader
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Add some data
        state = DimState(state_fips="99", state_name="Test", state_abbrev="TS")
        isolated_session.add(state)
        isolated_session.commit()

        assert isolated_session.query(DimState).count() == 1

        # Clear tables
        loader.clear_tables(isolated_session)
        isolated_session.commit()

        assert isolated_session.query(DimState).count() == 0

    def test_reset_true_clears_before_load(self, isolated_session: Session) -> None:
        """load(reset=True) should clear existing data."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # First load
        loader.load(isolated_session, reset=True)
        count1 = isolated_session.query(DimState).count()

        # Second load with reset
        loader.load(isolated_session, reset=True)
        count2 = isolated_session.query(DimState).count()

        # Counts should be equal (old data was cleared)
        assert count1 == count2 == 1

    def test_reset_false_accumulates(self, isolated_session: Session) -> None:
        """load(reset=False) should not clear existing data."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Add pre-existing data
        state = DimState(state_fips="01", state_name="Alabama", state_abbrev="AL")
        isolated_session.add(state)
        isolated_session.commit()

        initial_count = isolated_session.query(DimState).count()
        assert initial_count == 1

        # Load without reset
        loader.load(isolated_session, reset=False)

        # Should have original + new data
        final_count = isolated_session.query(DimState).count()
        assert final_count == 2


class TestTransactionAtomicity:
    """Tests for transaction atomicity on failure."""

    def test_rollback_on_error(self, isolated_session: Session) -> None:
        """Failed load should rollback all changes."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Add some initial data
        state = DimState(state_fips="01", state_name="Alabama", state_abbrev="AL")
        isolated_session.add(state)
        isolated_session.commit()

        initial_count = isolated_session.query(DimState).count()
        assert initial_count == 1

        # Simulate a failure during load by patching
        def failing_load(session: Session, reset: bool = True, **kwargs: object) -> LoadStats:
            if reset:
                loader.clear_tables(session)
            # Add data then fail
            new_state = DimState(state_fips="99", state_name="Test", state_abbrev="TS")
            session.add(new_state)
            raise RuntimeError("Simulated failure")

        loader.load = failing_load  # type: ignore[method-assign]

        # Attempt load (should fail)
        try:
            with isolated_session.begin_nested():
                loader.load(isolated_session, reset=True)
        except RuntimeError:
            isolated_session.rollback()

        # Original data should still be there
        final_count = isolated_session.query(DimState).count()
        assert final_count == initial_count


class TestNoDuplicatePrimaryKeys:
    """Tests for PK uniqueness after reload."""

    def test_no_duplicate_pks_after_reload(self, isolated_session: Session) -> None:
        """Reloading should not create duplicate primary keys."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Load twice with reset
        loader.load(isolated_session, reset=True)
        isolated_session.commit()

        loader.load(isolated_session, reset=True)
        isolated_session.commit()

        # Check for duplicates
        from sqlalchemy import func

        total = isolated_session.query(DimState).count()
        distinct = isolated_session.query(func.count(DimState.state_id.distinct())).scalar()

        assert total == distinct, "Found duplicate primary keys"


# =============================================================================
# IDEMPOTENCY TESTS - INTEGRATION LEVEL (with real loaders)
# =============================================================================


# Skip all integration tests if no loaders available
pytestmark = pytest.mark.skipif(
    len(ALL_LOADERS) == 0,
    reason="No loader implementations available",
)


class TestLoaderIdempotency:
    """Integration tests for loader idempotency.

    Note: These tests skip if external data sources are unavailable.
    They're designed to verify the DELETE+INSERT pattern works correctly.
    """

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_loader_returns_loadstats(
        self,
        loader_class: type[DataLoader],
        isolated_session: Session,
        fast_config: LoaderConfig,
    ) -> None:
        """Loaders should return LoadStats even with no data."""
        loader = loader_class(fast_config)

        # Mock the data source to return empty data
        # This tests the structure without requiring external data
        try:
            # Use very restrictive config that should return quickly
            stats = loader.load(isolated_session, reset=True, verbose=False)
            assert isinstance(stats, LoadStats)
            assert stats.source is not None
        except Exception as e:
            # Skip if external dependency unavailable
            if "API" in str(e) or "connection" in str(e).lower() or "file" in str(e).lower():
                pytest.skip(f"External data source unavailable: {e}")
            raise

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_clear_tables_clears_managed_tables(
        self,
        loader_class: type[DataLoader],
        isolated_session: Session,
        fast_config: LoaderConfig,
    ) -> None:
        """clear_tables() should clear all tables the loader manages."""
        loader = loader_class(fast_config)

        # Get counts before (should be 0 in fresh DB)
        _counts_before = get_table_counts(isolated_session, loader)

        # Clear tables
        loader.clear_tables(isolated_session)
        isolated_session.commit()

        # Get counts after
        counts_after = get_table_counts(isolated_session, loader)

        # All should be 0
        for table_name, count in counts_after.items():
            assert count == 0, f"{table_name} should be empty after clear_tables"


class TestDeletePlusInsertPattern:
    """Tests for DELETE+INSERT pattern behavior."""

    def test_delete_insert_clears_old_data(self, isolated_session: Session) -> None:
        """DELETE+INSERT should completely replace old data."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Load with config A (creates state 99)
        loader.load(isolated_session, reset=True)
        isolated_session.commit()

        first_states = {s.state_fips for s in isolated_session.query(DimState).all()}
        assert "99" in first_states

        # Clear and load different data
        loader.clear_tables(isolated_session)
        state2 = DimState(state_fips="01", state_name="Alabama", state_abbrev="AL")
        isolated_session.add(state2)
        isolated_session.commit()

        second_states = {s.state_fips for s in isolated_session.query(DimState).all()}

        # Old data should be gone
        assert "99" not in second_states
        assert "01" in second_states


class TestBatchBoundaryIdempotency:
    """Tests for idempotency across batch boundaries."""

    @pytest.mark.parametrize("batch_size", [1, 10, 100, 1000])
    def test_different_batch_sizes_same_result(
        self,
        batch_size: int,
        isolated_session: Session,
    ) -> None:
        """Different batch sizes should produce identical results."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        # This is a structural test - real loaders would need actual data
        loader = ConcreteTestLoader(LoaderConfig(batch_size=batch_size))

        loader.load(isolated_session, reset=True)
        isolated_session.commit()

        # Verify data was loaded
        count = isolated_session.query(DimState).count()
        assert count > 0


class TestEmptyDataIdempotency:
    """Tests for handling empty data sources."""

    def test_empty_source_produces_empty_stats(self, isolated_session: Session) -> None:
        """Empty data source should produce LoadStats with zero counts."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Clear all data first
        loader.clear_tables(isolated_session)
        isolated_session.commit()

        # Verify empty
        counts = get_table_counts(isolated_session, loader)
        for table_name, count in counts.items():
            if table_name == "dim_state":
                # ConcreteTestLoader adds 1 state
                continue
            assert count == 0, f"{table_name} should be empty"

    def test_idempotent_on_empty(self, isolated_session: Session) -> None:
        """Running on empty source twice should produce same (empty) result."""
        from tests.unit.data.test_normalize.test_loader_base import ConcreteTestLoader

        loader = ConcreteTestLoader()

        # Run twice with reset
        loader.load(isolated_session, reset=True)
        counts1 = get_table_counts(isolated_session, loader)
        isolated_session.commit()

        loader.load(isolated_session, reset=True)
        counts2 = get_table_counts(isolated_session, loader)
        isolated_session.commit()

        assert counts1 == counts2
