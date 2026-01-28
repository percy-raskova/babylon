"""Fixtures for empirical validation tests with real QCEW data.

This module provides fixtures for accessing the QCEW database and creating
real data sources for tensor validation tests.

Key Fixtures:
    - qcew_db_path: Path to the QCEW SQLite database
    - qcew_engine: SQLAlchemy engine for the QCEW database
    - qcew_session: Session for QCEW queries (function-scoped)
    - production_mapper: DepartmentMapper loaded from production config
    - real_qcew_source: SQLiteQCEWSource implementation
    - production_hydrator: MarxianHydrator with real data sources

All fixtures gracefully skip tests when the database is not present,
enabling the test suite to work in CI environments without database files.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.economics.adapters import SQLiteQCEWSource
from babylon.economics.department_mapper import DepartmentMapper
from babylon.economics.hydrator import MarxianHydrator

# =============================================================================
# DATABASE PATH CANDIDATES
# =============================================================================

# Ordered list of candidate database paths (first found wins)
_DB_PATH_CANDIDATES = [
    Path("data/babylon.db"),
    Path("data/databases/babylon.db"),
    Path("data/qcew.db"),
    Path("data/databases/qcew.db"),
]


def _find_qcew_database() -> Path | None:
    """Find the QCEW database from candidate paths.

    Returns:
        Path to the database, or None if not found.
    """
    for candidate in _DB_PATH_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _verify_qcew_tables_exist(db_path: Path) -> bool:
    """Verify that the required QCEW tables exist in the database.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        True if all required tables exist, False otherwise.
    """
    import sqlite3

    required_tables = {
        "fact_qcew_annual",
        "dim_county",
        "dim_industry",
        "dim_time",
    }

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        return required_tables.issubset(existing_tables)
    except sqlite3.Error:
        return False


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def qcew_db_path() -> Path:
    """Path to QCEW database with required tables.

    Skips the test if the database is not found or doesn't have the required
    QCEW tables. This enables graceful degradation in CI environments where
    the database may not be available or fully populated.

    Returns:
        Path to the QCEW SQLite database file.
    """
    db_path = _find_qcew_database()
    if db_path is None:
        pytest.skip(f"QCEW database not found. Searched: {[str(p) for p in _DB_PATH_CANDIDATES]}")

    if not _verify_qcew_tables_exist(db_path):
        pytest.skip(
            f"Database {db_path} does not have required QCEW tables "
            "(fact_qcew_annual, dim_county, dim_industry, dim_time)"
        )

    return db_path


@pytest.fixture(scope="session")
def qcew_engine(qcew_db_path: Path) -> Generator[Engine, None, None]:
    """SQLAlchemy engine for QCEW database.

    Creates a read-only connection to the QCEW database with FK constraint
    enforcement enabled.

    Args:
        qcew_db_path: Path to the database file.

    Yields:
        SQLAlchemy Engine configured for the QCEW database.
    """
    # Create engine with URI for additional options
    engine = create_engine(
        f"sqlite:///{qcew_db_path}",
        echo=False,
        # Enable FK constraints (important for data integrity checks)
        connect_args={"check_same_thread": False},
    )

    # Enable foreign key constraint enforcement
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine

    engine.dispose()


@pytest.fixture
def qcew_session(qcew_engine: Engine) -> Generator[Session, None, None]:
    """Session for QCEW queries.

    Function-scoped session that auto-rollbacks after each test to prevent
    accidental data modification (though these are read-only tests).

    Args:
        qcew_engine: SQLAlchemy engine from qcew_engine fixture.

    Yields:
        SQLAlchemy Session for database queries.
    """
    SessionLocal = sessionmaker(bind=qcew_engine, autoflush=False, autocommit=False)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# MAPPER AND DATA SOURCE FIXTURES
# =============================================================================

# Path to production NAICS-to-department mapping configuration
_PRODUCTION_MAPPER_PATH = Path(__file__).parent.parent.parent.parent / (
    "src/babylon/economics/data/naics_to_dept.yaml"
)


@pytest.fixture(scope="session")
def production_mapper() -> DepartmentMapper:
    """Load production DepartmentMapper from YAML config.

    Uses the actual production configuration from src/babylon/economics/data/
    to ensure tests validate against real mapping rules.

    Returns:
        DepartmentMapper configured from production YAML.
    """
    if not _PRODUCTION_MAPPER_PATH.exists():
        pytest.skip(f"Production mapper config not found at {_PRODUCTION_MAPPER_PATH}")
    return DepartmentMapper.from_yaml(_PRODUCTION_MAPPER_PATH)


@pytest.fixture
def real_qcew_source(qcew_session: Session) -> SQLiteQCEWSource:
    """QCEW data source reading from the 3NF normalized database.

    Creates an SQLiteQCEWSource that queries the real QCEW database via
    SQLAlchemy, implementing the QCEWDataSource protocol.

    Args:
        qcew_session: SQLAlchemy session for database queries.

    Returns:
        SQLiteQCEWSource configured with the test session.
    """
    return SQLiteQCEWSource(qcew_session)


@pytest.fixture
def mock_bea_source() -> MockBEADataSource:
    """Mock BEA data source returning None for all queries.

    When BEA data is unavailable, the hydrator falls back to department
    default ratios from the YAML config. This fixture enables testing
    the hydrator with real QCEW data but default ratios.

    Returns:
        MockBEADataSource that returns None for all ratio queries.
    """
    return MockBEADataSource()


@pytest.fixture
def production_hydrator(
    real_qcew_source: SQLiteQCEWSource,
    mock_bea_source: MockBEADataSource,
    production_mapper: DepartmentMapper,
) -> MarxianHydrator:
    """Hydrator configured with real QCEW data and production mapper.

    This is the primary fixture for empirical validation tests. It uses:
    - Real QCEW wage data from the database
    - Mock BEA source (falls back to YAML default ratios)
    - Production department mapper configuration

    Args:
        real_qcew_source: SQLiteQCEWSource for real QCEW data.
        mock_bea_source: Mock BEA source returning None.
        production_mapper: Production DepartmentMapper.

    Returns:
        MarxianHydrator configured for empirical validation.
    """
    return MarxianHydrator(
        qcew_source=real_qcew_source,
        bea_source=mock_bea_source,
        dept_mapper=production_mapper,
    )


# =============================================================================
# MOCK DATA SOURCE
# =============================================================================


class MockBEADataSource:
    """Mock BEA data source that returns None for all queries.

    Used when testing with real QCEW data but no BEA ratios available.
    The hydrator will fall back to department default ratios from YAML.
    """

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        """Always returns None to trigger fallback to defaults."""
        return None

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:
        """Always returns None to trigger fallback to defaults."""
        return None


# =============================================================================
# TEST CONSTANTS
# =============================================================================

# Detroit Metro Area FIPS codes
WAYNE_FIPS = "26163"  # Wayne County - Detroit core (deindustrialized)
OAKLAND_FIPS = "26125"  # Oakland County - Affluent suburb
MACOMB_FIPS = "26099"  # Macomb County - Working class suburb

DETROIT_METRO_COUNTIES = [WAYNE_FIPS, OAKLAND_FIPS, MACOMB_FIPS]

# Piketty guardrails for profit rate bounds
PIKETTY_R_MIN = 0.03  # Recessionary floor (3%)
PIKETTY_R_MAX = 0.08  # Boom ceiling (8%)

# Temporal smoothness bound
MAX_YOY_CHANGE = 0.30  # 30% max year-over-year change

# Train/test split for out-of-sample validation
TRAIN_YEARS = range(2010, 2020)  # 2010-2019
TEST_YEARS = range(2020, 2023)  # 2020-2022
