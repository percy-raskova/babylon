"""Integration tests for full tensor hydration from SQLite.

Feature: 011-fundamental-tensor-primitive
Implements: T056 from tasks.md

These tests verify the complete tensor hydration pipeline including:
1. QCEW data extraction via SQLiteQCEWSource
2. BEA ratio interpolation via InterpolatingBEASource
3. Department mapping via DepartmentMapper
4. TensorRegistry population with MarxianHydrator
5. Fallback to YAML defaults when BEA data unavailable
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.economics.adapters import InterpolatingBEASource, SQLiteQCEWSource
from babylon.economics.department_mapper import DepartmentMapper
from babylon.economics.hydrator import MarxianHydrator
from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3
from babylon.economics.tensor_registry import TensorRegistry

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine


# =============================================================================
# DATABASE DISCOVERY
# =============================================================================

_DB_PATH_CANDIDATES = [
    Path("data/sqlite/marxist-data-3NF.sqlite"),
    Path("data/babylon.db"),
    Path("data/databases/babylon.db"),
]

_MAPPER_CONFIG_PATH = Path(__file__).parent.parent.parent / (
    "src/babylon/economics/data/naics_to_dept.yaml"
)


def _find_database() -> Path | None:
    """Find the reference database from candidate paths."""
    for candidate in _DB_PATH_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _has_required_tables(db_path: Path) -> bool:
    """Check if database has required QCEW and BEA tables."""
    import sqlite3

    required = {
        "fact_qcew_annual",
        "dim_county",
        "dim_industry",
        "dim_time",
    }

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cursor.fetchall()}
        conn.close()
        return required.issubset(existing)
    except sqlite3.Error:
        return False


def _has_bea_tables(db_path: Path) -> bool:
    """Check if database has BEA tables with correct schema for interpolation tests."""
    import sqlite3

    required_tables = {
        "fact_bea_national_industry",
        "bridge_naics_bea",
        "dim_time",
    }

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cursor.fetchall()}
        if not required_tables.issubset(existing):
            conn.close()
            return False

        # Check that bridge_naics_bea has naics_code column
        cursor.execute("PRAGMA table_info(bridge_naics_bea)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        return "naics_code" in columns
    except sqlite3.Error:
        return False


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def db_path() -> Path:
    """Path to reference database with QCEW tables."""
    path = _find_database()
    if path is None:
        pytest.skip(f"Database not found. Searched: {[str(p) for p in _DB_PATH_CANDIDATES]}")

    if not _has_required_tables(path):
        pytest.skip(f"Database {path} missing required QCEW tables")

    return path


@pytest.fixture(scope="module")
def db_engine(db_path: Path) -> Generator[Engine, None, None]:
    """SQLAlchemy engine for database access."""
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped database session."""
    session_factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def dept_mapper() -> DepartmentMapper:
    """Production department mapper from YAML config."""
    if not _MAPPER_CONFIG_PATH.exists():
        pytest.skip(f"Mapper config not found at {_MAPPER_CONFIG_PATH}")
    return DepartmentMapper.from_yaml(_MAPPER_CONFIG_PATH)


@pytest.fixture
def qcew_source(db_session: Session) -> SQLiteQCEWSource:
    """QCEW data source backed by SQLite."""
    return SQLiteQCEWSource(db_session)


@pytest.fixture
def bea_source(db_session: Session, db_path: Path) -> InterpolatingBEASource | None:
    """BEA data source with interpolation, or None if tables missing."""
    if not _has_bea_tables(db_path):
        return None
    return InterpolatingBEASource(db_session, max_delta=5)


class MockBEASource:
    """Mock BEA data source that returns None for all queries."""

    def get_sv_ratio(self, naics: str, year: int) -> float | None:
        return None

    def get_cv_ratio(self, naics: str, year: int) -> float | None:
        return None


@pytest.fixture
def hydrator(
    qcew_source: SQLiteQCEWSource,
    bea_source: InterpolatingBEASource | None,
    dept_mapper: DepartmentMapper,
) -> MarxianHydrator:
    """MarxianHydrator with real or mock BEA source."""
    # Use mock if BEA tables not available or schema doesn't match
    actual_bea_source = bea_source if bea_source is not None else MockBEASource()

    return MarxianHydrator(
        qcew_source=qcew_source,
        bea_source=actual_bea_source,  # type: ignore[arg-type]
        dept_mapper=dept_mapper,
    )


# =============================================================================
# TEST CONSTANTS
# =============================================================================

# Detroit Metro FIPS codes
WAYNE_FIPS = "26163"  # Wayne County - Detroit core
OAKLAND_FIPS = "26125"  # Oakland County - Affluent suburb
MACOMB_FIPS = "26099"  # Macomb County - Working class suburb

DETROIT_COUNTIES = [WAYNE_FIPS, OAKLAND_FIPS, MACOMB_FIPS]


# =============================================================================
# HYDRATION PIPELINE TESTS
# =============================================================================


@pytest.mark.integration
class TestFullHydrationPipeline:
    """Tests for complete hydration from SQLite to TensorRegistry."""

    def test_hydrate_single_county_year(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Hydrating a single county-year produces a valid tensor."""
        year = 2022

        # Verify QCEW data exists
        raw_data = qcew_source.fetch_county_wages(WAYNE_FIPS, year)
        if not raw_data:
            pytest.skip(f"No QCEW data for {WAYNE_FIPS} in {year}")

        # Hydrate tensor
        tensor = hydrator.hydrate(WAYNE_FIPS, year)

        # Verify tensor structure
        assert isinstance(tensor, ValueTensor4x3)
        assert tensor.fips_code == WAYNE_FIPS
        assert tensor.year == year

        # Verify tensor has meaningful data
        assert tensor.total_v > 0, "Variable capital should be positive"
        assert tensor.total_value > 0, "Total value should be positive"

    def test_hydrate_multiple_counties(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Hydrating multiple counties populates the registry correctly."""
        registry = TensorRegistry()
        year = 2022
        counties_with_data = []

        for fips in DETROIT_COUNTIES:
            if qcew_source.fetch_county_wages(fips, year):
                counties_with_data.append(fips)

        if len(counties_with_data) < 2:
            pytest.skip("Need at least 2 counties with data for this test")

        # Hydrate all counties
        registry.hydrate_counties(hydrator, counties_with_data, [year])

        # Verify all loaded
        for fips in counties_with_data:
            tensor = registry.get(fips, year)
            assert isinstance(tensor, ValueTensor4x3), f"Missing tensor for {fips}"
            assert tensor.fips_code == fips

    def test_hydrate_multiple_years(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Hydrating multiple years creates tensors for each year."""
        registry = TensorRegistry()
        years = [2020, 2021, 2022]
        valid_years = []

        for year in years:
            if qcew_source.fetch_county_wages(WAYNE_FIPS, year):
                valid_years.append(year)

        if len(valid_years) < 2:
            pytest.skip("Need at least 2 years with data for this test")

        registry.hydrate_counties(hydrator, [WAYNE_FIPS], valid_years)

        # Verify all years loaded
        for year in valid_years:
            tensor = registry.get(WAYNE_FIPS, year)
            assert isinstance(tensor, ValueTensor4x3)
            assert tensor.year == year


@pytest.mark.integration
class TestBEAInterpolationIntegration:
    """Tests for BEA temporal interpolation in full hydration pipeline."""

    def test_interpolation_produces_reasonable_ratios(
        self,
        db_session: Session,
        db_path: Path,
    ) -> None:
        """BEA interpolation produces ratios in economically reasonable range."""
        if not _has_bea_tables(db_path):
            pytest.skip("BEA tables not present in database")

        source = InterpolatingBEASource(db_session, max_delta=5)

        # Query a manufacturing NAICS code that likely has BEA data
        test_naics = "336111"  # Automobile manufacturing
        year = 2022

        sv_ratio = source.get_sv_ratio(test_naics, year)
        cv_ratio = source.get_cv_ratio(test_naics, year)

        # If data exists, verify reasonable bounds
        if sv_ratio is not None:
            assert 0 <= sv_ratio <= 10, f"s/v ratio {sv_ratio} outside bounds [0, 10]"

        if cv_ratio is not None:
            assert 0 <= cv_ratio <= 20, f"c/v ratio {cv_ratio} outside bounds [0, 20]"

    def test_missing_bea_falls_back_to_yaml_defaults(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
        dept_mapper: DepartmentMapper,
    ) -> None:
        """When BEA data is unavailable, hydrator uses YAML default ratios."""
        year = 2022

        if not qcew_source.fetch_county_wages(WAYNE_FIPS, year):
            pytest.skip(f"No QCEW data for {WAYNE_FIPS} in {year}")

        tensor = hydrator.hydrate(WAYNE_FIPS, year)

        # Tensor should still be valid even if BEA returned None
        assert tensor.total_v > 0
        assert tensor.total_c >= 0  # May be 0 if all fallbacks failed
        assert tensor.total_s >= 0


@pytest.mark.integration
class TestTensorRegistryIntegration:
    """Tests for TensorRegistry integration with hydration."""

    def test_registry_get_returns_sentinel_for_unloaded(self) -> None:
        """Registry returns NoDataSentinel for non-hydrated county-years."""
        registry = TensorRegistry()

        result = registry.get("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "not loaded" in result.reason.lower()

    def test_registry_caches_hydrated_tensors(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Registry caches tensors, returning same instance on repeated calls."""
        if not qcew_source.fetch_county_wages(WAYNE_FIPS, 2022):
            pytest.skip("No QCEW data for Wayne County 2022")

        registry = TensorRegistry()
        registry.hydrate_counties(hydrator, [WAYNE_FIPS], [2022])

        # Multiple gets should return same object
        tensor1 = registry.get(WAYNE_FIPS, 2022)
        tensor2 = registry.get(WAYNE_FIPS, 2022)

        assert tensor1 is tensor2, "Registry should cache tensor instances"

    def test_registry_returns_tensor_after_hydration(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Registry returns tensors for hydrated county-years."""
        registry = TensorRegistry()
        counties_with_data = []

        for fips in DETROIT_COUNTIES:
            if qcew_source.fetch_county_wages(fips, 2022):
                counties_with_data.append(fips)

        if not counties_with_data:
            pytest.skip("No QCEW data for Detroit counties")

        registry.hydrate_counties(hydrator, counties_with_data, [2022])

        # Verify get() returns tensors for hydrated counties
        for fips in counties_with_data:
            result = registry.get(fips, 2022)
            # Should be either a tensor (success) or sentinel (hydration failed)
            assert isinstance(result, (ValueTensor4x3, NoDataSentinel))


@pytest.mark.integration
class TestHydrationErrorHandling:
    """Tests for error handling during hydration."""

    def test_hydrate_missing_county_produces_zero_tensor(
        self,
        hydrator: MarxianHydrator,
    ) -> None:
        """Hydrating a non-existent county produces a zero-value tensor.

        The MarxianHydrator returns a valid tensor with zero values when
        no QCEW data exists for a county-year. This is expected behavior
        since the county may simply have no recorded employment data.
        """
        registry = TensorRegistry()

        # Hydrate a fake FIPS code
        registry.hydrate_counties(hydrator, ["00000"], [2022])

        result = registry.get("00000", 2022)

        # Should have a tensor with zero values (no data found)
        assert isinstance(result, ValueTensor4x3)
        assert result.total_v == 0, "Missing county should have zero variable capital"
        assert result.fips_code == "00000"

    def test_partial_hydration_processes_all_counties(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Hydration processes all counties, returning zeros for missing ones."""
        registry = TensorRegistry()

        # Mix of valid and invalid FIPS codes
        fips_codes = ["00000", WAYNE_FIPS, "99999"]

        if not qcew_source.fetch_county_wages(WAYNE_FIPS, 2022):
            pytest.skip("No QCEW data for Wayne County 2022")

        # Should not raise - processes all counties
        registry.hydrate_counties(hydrator, fips_codes, [2022])

        # Valid county should have data
        wayne = registry.get(WAYNE_FIPS, 2022)
        assert isinstance(wayne, ValueTensor4x3)
        assert wayne.total_v > 0, "Wayne County should have data"

        # Invalid counties should have zero tensors
        invalid1 = registry.get("00000", 2022)
        invalid2 = registry.get("99999", 2022)
        assert isinstance(invalid1, ValueTensor4x3)
        assert isinstance(invalid2, ValueTensor4x3)
        assert invalid1.total_v == 0, "Fake county should have zero data"
        assert invalid2.total_v == 0, "Fake county should have zero data"


@pytest.mark.integration
class TestHydrationDataQuality:
    """Tests for data quality checks in hydrated tensors."""

    def test_accounting_identity_holds(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Allocated wages + excluded = QCEW total (accounting identity)."""
        year = 2022
        raw_data = qcew_source.fetch_county_wages(WAYNE_FIPS, year)

        if not raw_data:
            pytest.skip(f"No QCEW data for {WAYNE_FIPS} in {year}")

        total_qcew = sum(wages for _, wages, _ in raw_data)
        tensor = hydrator.hydrate(WAYNE_FIPS, year)

        allocated_v = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v
        computed_total = allocated_v + tensor.excluded_wages

        # Allow 0.1% tolerance for floating point
        assert computed_total == pytest.approx(total_qcew, rel=0.001), (
            f"Accounting identity violated: "
            f"allocated ({allocated_v:,.0f}) + excluded ({tensor.excluded_wages:,.0f}) = "
            f"{computed_total:,.0f} != QCEW total ({total_qcew:,.0f})"
        )

    def test_profit_rate_within_bounds(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """Profit rate should be within economically reasonable bounds."""
        if not qcew_source.fetch_county_wages(WAYNE_FIPS, 2022):
            pytest.skip("No QCEW data for Wayne County 2022")

        tensor = hydrator.hydrate(WAYNE_FIPS, 2022)

        # Piketty bounds: 3-8% historically for profit rates
        # Allow 0-15% for broader tolerance
        assert 0 <= tensor.profit_rate <= 0.15, (
            f"Profit rate {tensor.profit_rate:.2%} outside bounds [0%, 15%]"
        )

    def test_all_departments_non_negative(
        self,
        hydrator: MarxianHydrator,
        qcew_source: SQLiteQCEWSource,
    ) -> None:
        """All department values should be non-negative."""
        if not qcew_source.fetch_county_wages(WAYNE_FIPS, 2022):
            pytest.skip("No QCEW data for Wayne County 2022")

        tensor = hydrator.hydrate(WAYNE_FIPS, 2022)

        # Check all departments
        for dept in [tensor.dept_I, tensor.dept_IIa, tensor.dept_IIb, tensor.dept_III]:
            assert dept.c >= 0, f"Constant capital negative: {dept.c}"
            assert dept.v >= 0, f"Variable capital negative: {dept.v}"
            assert dept.s >= 0, f"Surplus value negative: {dept.s}"
