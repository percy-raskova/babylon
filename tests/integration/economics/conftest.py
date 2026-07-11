"""Shared fixtures for economics integration tests.

This module provides fixtures for testing the Marxian value transformation
pipeline, including:

- Mock data sources (QCEW, BEA)
- DepartmentMapper with test configuration
- MarxianHydrator instances
- Real QCEW database fixtures for end-to-end validation

Spec 057 unquarantine: the original ``babylon.domain.economics.reproduction``
module was removed in commit ``a5f73139``. The ``ImperialRentCalculator`` /
``PeripheryReproductionBasket`` fixtures + ``hydrate_with_rent`` paths that
depended on it have been removed; the orphan test files
(``test_imperial_rent.py``, ``test_melt_integration.py``,
``test_melt_regression.py``) were deleted as part of FR-009. The Spec 057
Leontief pipeline is tested via ``tests/integration/economics/tick/
test_imperial_rent_pipeline.py`` instead.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from babylon.domain.economics.adapters import SQLiteQCEWSource
from babylon.domain.economics.department_mapper import DepartmentMapper
from babylon.domain.economics.hydrator import MarxianHydrator

# =============================================================================
# DATABASE PATH CANDIDATES (mirrors tests/integration/tensors/conftest.py)
# =============================================================================

_DB_PATH_CANDIDATES = [
    Path("data/sqlite/marxist-data-3NF.sqlite"),
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

    Skips the test if the database is not found or doesn't have
    the required QCEW tables.

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
    """SQLAlchemy engine for QCEW database with FK enforcement.

    Args:
        qcew_db_path: Path to the database file.

    Yields:
        SQLAlchemy Engine configured for the QCEW database.
    """
    engine = create_engine(
        f"sqlite:///{qcew_db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine
    engine.dispose()


@pytest.fixture
def qcew_session(qcew_engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped session for QCEW queries with auto-rollback.

    Args:
        qcew_engine: SQLAlchemy engine from qcew_engine fixture.

    Yields:
        SQLAlchemy Session for database queries.
    """
    session_factory = sessionmaker(bind=qcew_engine, autoflush=False, autocommit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def real_qcew_source(qcew_session: Session) -> SQLiteQCEWSource:
    """QCEW data source reading from the 3NF normalized database.

    Args:
        qcew_session: SQLAlchemy session for database queries.

    Returns:
        SQLiteQCEWSource configured with the test session.
    """
    return SQLiteQCEWSource(qcew_session)


# Path to production NAICS-to-department mapping configuration
_PRODUCTION_MAPPER_PATH = Path(__file__).parent.parent.parent.parent / (
    "src/babylon/domain/economics/data/naics_to_dept.yaml"
)


@pytest.fixture(scope="session")
def production_mapper() -> DepartmentMapper:
    """Load production DepartmentMapper from YAML config.

    Returns:
        DepartmentMapper configured from production YAML.
    """
    if not _PRODUCTION_MAPPER_PATH.exists():
        pytest.skip(f"Production mapper config not found at {_PRODUCTION_MAPPER_PATH}")
    return DepartmentMapper.from_yaml(_PRODUCTION_MAPPER_PATH)


class NullBEADataSource:
    """BEA data source returning None for all queries.

    When BEA data is unavailable, the hydrator falls back to department
    default ratios from the YAML config.
    """

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Always returns None to trigger fallback to defaults."""
        return None

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Always returns None to trigger fallback to defaults."""
        return None


@pytest.fixture
def production_hydrator(
    real_qcew_source: SQLiteQCEWSource,
    production_mapper: DepartmentMapper,
) -> MarxianHydrator:
    """Hydrator configured with real QCEW data and production mapper.

    Uses real QCEW wage data with null BEA source (falls back to YAML
    default ratios) and production department mapper configuration.

    Args:
        real_qcew_source: SQLiteQCEWSource for real QCEW data.
        production_mapper: Production DepartmentMapper.

    Returns:
        MarxianHydrator configured for empirical validation.
    """
    return MarxianHydrator(
        qcew_source=real_qcew_source,
        bea_source=NullBEADataSource(),
        dept_mapper=production_mapper,
    )


# =============================================================================
# MOCK DATA SOURCES
# =============================================================================


class MockQCEWDataSource:
    """Mock QCEW data source with predetermined county wage data.

    Implements the QCEWDataSource protocol for testing.
    """

    def __init__(self, data: dict[tuple[str, int], list[tuple[str, float, int]]]) -> None:
        """Initialize with county data.

        Args:
            data: Mapping of (fips_code, year) -> list of (naics_code, wages, employment)
        """
        self._data = data

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year.

        Returns:
            List of (naics_code, wages, employment) tuples.
        """
        return self._data.get((fips_code, year), [])


class MockBEADataSource:
    """Mock BEA data source with predetermined industry ratios.

    Implements the BEADataSource protocol for testing.
    """

    def __init__(
        self,
        sv_ratios: dict[str, float] | None = None,
        cv_ratios: dict[str, float] | None = None,
    ) -> None:
        """Initialize with ratio data.

        Args:
            sv_ratios: NAICS code -> s/v ratio mapping.
            cv_ratios: NAICS code -> c/v ratio mapping.
        """
        self._sv_ratios = sv_ratios or {}
        self._cv_ratios = cv_ratios or {}

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Get s/v ratio for a NAICS code.

        Returns:
            Rate of surplus value, or None if unavailable.
        """
        return self._sv_ratios.get(naics_code)

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Get c/v ratio for a NAICS code.

        Returns:
            Organic composition of capital, or None if unavailable.
        """
        return self._cv_ratios.get(naics_code)


# =============================================================================
# QCEW DATA FIXTURES
# =============================================================================


@pytest.fixture
def wayne_county_qcew() -> list[tuple[str, float, int]]:
    """Wayne County (Detroit area) QCEW data - working class industrial base.

    Wayne County characteristics:
    - Strong manufacturing (auto industry) - Dept IIa
    - Basic retail and services - Dept IIa
    - Limited luxury sector - Dept IIb
    - Government excluded (NAICS 92)
    """
    return [
        # Manufacturing (heavily IIa - necessary consumption)
        ("336111", 500_000_000.0, 50000),  # Auto manufacturing
        ("311", 100_000_000.0, 15000),  # Food manufacturing
        # Retail (mostly IIa)
        ("4451", 80_000_000.0, 20000),  # Grocery stores
        ("4522", 60_000_000.0, 12000),  # Department stores
        # Services (mix)
        ("722513", 40_000_000.0, 25000),  # Fast food (IIa)
        # Healthcare/Education (Dept III - social reproduction)
        ("62", 200_000_000.0, 45000),  # Healthcare
        ("6244", 30_000_000.0, 8000),  # Child day care
        # Government - excluded
        ("921110", 150_000_000.0, 20000),  # Federal government
    ]


@pytest.fixture
def oakland_county_qcew() -> list[tuple[str, float, int]]:
    """Oakland County (affluent suburb) QCEW data - upper middle class consumption.

    Oakland County characteristics:
    - Professional services - Dept I (B2B)
    - Luxury retail and services - Dept IIb
    - Higher proportion of luxury consumption
    - Government excluded (NAICS 92)
    """
    return [
        # Professional services (Dept I - B2B)
        ("54", 300_000_000.0, 40000),  # Professional services
        # Retail (more luxury-oriented)
        ("44831", 50_000_000.0, 3000),  # Jewelry stores (pure IIb)
        ("45111", 40_000_000.0, 5000),  # Sporting goods (IIb-heavy)
        ("4522", 80_000_000.0, 15000),  # Department stores (mix)
        # Services (more luxury)
        ("71391", 30_000_000.0, 2000),  # Golf courses (pure IIb)
        ("722511", 60_000_000.0, 8000),  # Fine dining (IIb-heavy)
        # Healthcare/Education (Dept III)
        ("62", 180_000_000.0, 35000),  # Healthcare
        ("6244", 25_000_000.0, 6000),  # Child day care
        # Government - excluded
        ("921110", 100_000_000.0, 12000),  # Federal government
    ]


# =============================================================================
# DEPARTMENT MAPPER FIXTURE
# =============================================================================


@pytest.fixture
def dept_mapper(tmp_path: Path) -> DepartmentMapper:
    """Create a DepartmentMapper for testing."""
    yaml_content = """
defaults:
  31:
    dept_IIa: 0.70
    dept_IIb: 0.30
  44:
    dept_IIa: 0.75
    dept_IIb: 0.25
  45:
    dept_IIa: 0.65
    dept_IIb: 0.35
  54:
    dept_I: 0.60
    dept_IIa: 0.30
    dept_IIb: 0.10
  62:
    dept_IIa: 0.30
    dept_III: 0.70
  71:
    dept_IIa: 0.30
    dept_IIb: 0.70
  72:
    dept_IIa: 0.60
    dept_IIb: 0.40

overrides:
  336111:
    dept_I: 0.70
    dept_IIa: 0.20
    dept_IIb: 0.10
  311:
    dept_I: 0.30
    dept_IIa: 0.55
    dept_IIb: 0.15
  4451:
    dept_IIa: 0.95
    dept_IIb: 0.05
  4522:
    dept_IIa: 0.60
    dept_IIb: 0.40
  44831:
    dept_IIb: 1.0
  45111:
    dept_IIa: 0.30
    dept_IIb: 0.70
  6244:
    dept_III: 1.0
  71391:
    dept_IIb: 1.0
  722511:
    dept_IIa: 0.20
    dept_IIb: 0.80
  722513:
    dept_IIa: 0.90
    dept_IIb: 0.10

excluded:
  - "92"

default_ratios:
  dept_I:
    cv_ratio: 3.0
    sv_ratio: 2.0
  dept_IIa:
    cv_ratio: 1.5
    sv_ratio: 1.0
  dept_IIb:
    cv_ratio: 2.5
    sv_ratio: 3.0
  dept_III:
    cv_ratio: 0.5
    sv_ratio: 0.7
"""
    config_file = tmp_path / "naics_to_dept.yaml"
    config_file.write_text(yaml_content)
    return DepartmentMapper.from_yaml(config_file)


# =============================================================================
# BEA DATA SOURCE FIXTURE
# =============================================================================


@pytest.fixture
def mock_bea_source() -> MockBEADataSource:
    """Create a mock BEA data source with industry ratios."""
    return MockBEADataSource(
        sv_ratios={
            "336111": 1.2,  # Auto manufacturing
            "311": 0.9,  # Food manufacturing
            "4451": 0.8,  # Grocery stores
        },
        cv_ratios={
            "336111": 2.5,  # Capital-intensive auto
            "311": 1.8,  # Food manufacturing
            "4451": 1.2,  # Retail
        },
    )


# =============================================================================
# IMPERIAL RENT FIXTURES (REMOVED post-Spec 057)
# =============================================================================
# The ``periphery_basket``, ``rent_calculator``, ``hydrator_with_rent``, and
# ``hydrator_session`` fixtures depended on the deleted
# ``babylon.domain.economics.reproduction`` module. The new Leontief pipeline is
# tested separately via ``tests/integration/economics/tick/
# test_imperial_rent_pipeline.py`` which uses synthetic Mock fixtures for
# the Spec 057 Protocol surfaces (PeripheryLaborCoefficientsSource,
# FinalDemandSource, IndustryToCountyAllocator).
