"""Shared fixtures for data loader integration tests.

Provides:
- In-memory SQLite database with FK enforcement
- Session factory with automatic rollback
- Sample dimension data for testing
- All loader classes for parameterized tests
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.normalize.database import NormalizedBase

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def in_memory_engine() -> Generator[Engine, None, None]:
    """Create in-memory SQLite database with FK enforcement.

    Uses module scope to avoid recreation overhead while still
    providing isolation through function-scoped sessions.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key enforcement for SQLite (OFF by default!)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    NormalizedBase.metadata.create_all(engine)

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session(in_memory_engine: Engine) -> Generator[Session, None, None]:
    """Create session with automatic rollback for test isolation.

    Each test gets a fresh transaction that is rolled back after,
    ensuring tests don't affect each other.
    """
    session_factory = sessionmaker(bind=in_memory_engine)
    session = session_factory()

    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def fresh_db_session() -> Generator[Session, None, None]:
    """Create completely fresh in-memory database for each test.

    Use this when you need complete isolation (e.g., testing
    schema creation or destructive operations).
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    NormalizedBase.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    yield session

    session.close()
    engine.dispose()


# =============================================================================
# LOADER FIXTURES
# =============================================================================


def get_all_loader_classes() -> list[type[DataLoader]]:
    """Get all implemented DataLoader subclasses.

    Returns only loaders that are fully implemented and can be tested.
    Loaders are imported dynamically to avoid import errors if
    dependencies are missing.
    """
    loaders: list[type[DataLoader]] = []

    # Try to import each loader, skip if not available
    try:
        from babylon.data.census.loader_3nf import CensusLoader

        loaders.append(CensusLoader)
    except ImportError:
        pass

    try:
        from babylon.data.fred.loader_3nf import FredLoader

        loaders.append(FredLoader)
    except ImportError:
        pass

    try:
        from babylon.data.energy.loader_3nf import EnergyLoader

        loaders.append(EnergyLoader)
    except ImportError:
        pass

    try:
        from babylon.data.trade.loader_3nf import TradeLoader

        loaders.append(TradeLoader)
    except ImportError:
        pass

    try:
        from babylon.data.qcew.loader_3nf import QcewLoader

        loaders.append(QcewLoader)
    except ImportError:
        pass

    try:
        from babylon.data.materials.loader_3nf import MaterialsLoader

        loaders.append(MaterialsLoader)
    except ImportError:
        pass

    return loaders


# Get all loaders at module load time
ALL_LOADERS = get_all_loader_classes()


@pytest.fixture(scope="module")
def all_loader_classes() -> list[type[DataLoader]]:
    """Provide list of all loader classes for parametrized tests."""
    return ALL_LOADERS


@pytest.fixture
def minimal_config() -> LoaderConfig:
    """Minimal config for fast testing.

    Reduces year ranges and batch sizes to speed up integration tests.
    """
    return LoaderConfig(
        census_year=2022,
        fred_start_year=2020,
        fred_end_year=2022,
        energy_start_year=2020,
        energy_end_year=2022,
        trade_years=[2020, 2021, 2022],
        qcew_years=[2020, 2021, 2022],
        materials_years=[2020, 2021, 2022],
        state_fips_list=["06"],  # California only for speed
        batch_size=1000,  # Smaller batches for testing
        verbose=False,
    )


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_state_data() -> list[dict[str, str]]:
    """Sample DimState records for testing."""
    return [
        {"state_fips": "01", "state_name": "Alabama", "state_abbrev": "AL"},
        {"state_fips": "06", "state_name": "California", "state_abbrev": "CA"},
        {"state_fips": "36", "state_name": "New York", "state_abbrev": "NY"},
        {"state_fips": "48", "state_name": "Texas", "state_abbrev": "TX"},
    ]


@pytest.fixture
def sample_county_data() -> list[dict[str, str | int]]:
    """Sample DimCounty records for testing (requires state_id FK)."""
    return [
        {"fips": "06037", "name": "Los Angeles County", "state_id": 2},
        {"fips": "06073", "name": "San Diego County", "state_id": 2},
        {"fips": "36061", "name": "New York County", "state_id": 3},
    ]


@pytest.fixture
def sample_industry_data() -> list[dict[str, str | int | None]]:
    """Sample DimIndustry records for testing."""
    return [
        {
            "naics_code": "31",
            "title": "Manufacturing",
            "naics_level": 2,
            "sector_code": "31",
            "class_composition": "goods_producing",
        },
        {
            "naics_code": "52",
            "title": "Finance and Insurance",
            "naics_level": 2,
            "sector_code": "52",
            "class_composition": "circulation",
        },
        {
            "naics_code": "62",
            "title": "Health Care",
            "naics_level": 2,
            "sector_code": "62",
            "class_composition": "service_producing",
        },
    ]


# =============================================================================
# HELPER FIXTURES
# =============================================================================


@pytest.fixture
def fk_check_enabled(in_memory_engine: Engine) -> bool:
    """Verify FK checking is enabled."""
    with in_memory_engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        return result.scalar() == 1
