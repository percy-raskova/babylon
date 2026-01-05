"""Unit tests for DataLoader base infrastructure.

Tests the LoaderConfig, LoadStats, and DataLoader ABC classes that form
the foundation of the unified data loading system.
"""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import DimState

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# =============================================================================
# LOADERCONFIG TESTS
# =============================================================================


class TestLoaderConfigDefaults:
    """Tests for LoaderConfig default values."""

    def test_census_year_default(self) -> None:
        """Census year should default to 2022."""
        config = LoaderConfig()
        assert config.census_year == 2022

    def test_fred_year_range_default(self) -> None:
        """FRED year range should default to 1990-2024."""
        config = LoaderConfig()
        assert config.fred_start_year == 1990
        assert config.fred_end_year == 2024

    def test_energy_year_range_default(self) -> None:
        """Energy year range should default to 1990-2024."""
        config = LoaderConfig()
        assert config.energy_start_year == 1990
        assert config.energy_end_year == 2024

    def test_trade_years_default(self) -> None:
        """Trade years should default to 2010-2024."""
        config = LoaderConfig()
        assert config.trade_years == list(range(2010, 2025))

    def test_qcew_years_default(self) -> None:
        """QCEW years should default to 2015-2023."""
        config = LoaderConfig()
        assert config.qcew_years == list(range(2015, 2024))

    def test_materials_years_default(self) -> None:
        """Materials years should default to 2015-2023."""
        config = LoaderConfig()
        assert config.materials_years == list(range(2015, 2024))

    def test_state_fips_list_default_is_none(self) -> None:
        """State FIPS list should default to None (all states)."""
        config = LoaderConfig()
        assert config.state_fips_list is None

    def test_include_territories_default(self) -> None:
        """Include territories should default to False."""
        config = LoaderConfig()
        assert config.include_territories is False

    def test_batch_size_default(self) -> None:
        """Batch size should default to 10,000."""
        config = LoaderConfig()
        assert config.batch_size == 10_000

    def test_request_delay_default(self) -> None:
        """Request delay should default to 0.5 seconds."""
        config = LoaderConfig()
        assert config.request_delay_seconds == 0.5

    def test_max_retries_default(self) -> None:
        """Max retries should default to 3."""
        config = LoaderConfig()
        assert config.max_retries == 3

    def test_verbose_default(self) -> None:
        """Verbose should default to True."""
        config = LoaderConfig()
        assert config.verbose is True


class TestLoaderConfigOverrides:
    """Tests for LoaderConfig value overrides."""

    def test_override_census_year(self) -> None:
        """Census year should be overridable."""
        config = LoaderConfig(census_year=2021)
        assert config.census_year == 2021

    def test_override_fred_range(self) -> None:
        """FRED year range should be overridable."""
        config = LoaderConfig(fred_start_year=2000, fred_end_year=2020)
        assert config.fred_start_year == 2000
        assert config.fred_end_year == 2020

    def test_override_state_fips_list(self) -> None:
        """State FIPS list should be overridable."""
        config = LoaderConfig(state_fips_list=["06", "36", "48"])
        assert config.state_fips_list == ["06", "36", "48"]

    def test_override_batch_size(self) -> None:
        """Batch size should be overridable."""
        config = LoaderConfig(batch_size=5000)
        assert config.batch_size == 5000

    def test_partial_override_preserves_defaults(self) -> None:
        """Overriding one field should preserve other defaults."""
        config = LoaderConfig(census_year=2020)
        assert config.census_year == 2020
        assert config.fred_start_year == 1990  # Default preserved
        assert config.batch_size == 10_000  # Default preserved


class TestLoaderConfigDataclass:
    """Tests for LoaderConfig dataclass properties."""

    def test_is_dataclass(self) -> None:
        """LoaderConfig should be a dataclass."""
        config = LoaderConfig()
        assert hasattr(config, "__dataclass_fields__")

    def test_has_expected_fields(self) -> None:
        """LoaderConfig should have all expected fields."""
        expected_fields = {
            "census_year",
            "fred_start_year",
            "fred_end_year",
            "energy_start_year",
            "energy_end_year",
            "trade_years",
            "qcew_years",
            "materials_years",
            "state_fips_list",
            "include_territories",
            "batch_size",
            "request_delay_seconds",
            "max_retries",
            "verbose",
        }
        actual_fields = {f.name for f in fields(LoaderConfig)}
        assert expected_fields == actual_fields

    def test_mutable_default_list_independence(self) -> None:
        """Mutable list defaults should be independent across instances."""
        config1 = LoaderConfig()
        config2 = LoaderConfig()

        # Modify one instance's list
        config1.trade_years.append(2025)

        # Other instance should be unaffected
        assert 2025 not in config2.trade_years


# =============================================================================
# LOADSTATS TESTS
# =============================================================================


class TestLoadStatsCreation:
    """Tests for LoadStats creation and properties."""

    def test_create_with_source(self) -> None:
        """LoadStats should require source identifier."""
        stats = LoadStats(source="census")
        assert stats.source == "census"

    def test_default_empty_dicts(self) -> None:
        """LoadStats should have empty dicts by default."""
        stats = LoadStats(source="test")
        assert stats.dimensions_loaded == {}
        assert stats.facts_loaded == {}
        assert stats.errors == []

    def test_default_zero_counts(self) -> None:
        """LoadStats should have zero counts by default."""
        stats = LoadStats(source="test")
        assert stats.api_calls == 0
        assert stats.files_processed == 0


class TestLoadStatsProperties:
    """Tests for LoadStats computed properties."""

    def test_total_dimensions(self) -> None:
        """total_dimensions should sum dimension table counts."""
        stats = LoadStats(
            source="test",
            dimensions_loaded={"dim_state": 52, "dim_county": 3143},
        )
        assert stats.total_dimensions == 52 + 3143

    def test_total_facts(self) -> None:
        """total_facts should sum fact table counts."""
        stats = LoadStats(
            source="test",
            facts_loaded={"fact_census_income": 1000, "fact_qcew_annual": 5000},
        )
        assert stats.total_facts == 1000 + 5000

    def test_total_rows(self) -> None:
        """total_rows should sum dimensions and facts."""
        stats = LoadStats(
            source="test",
            dimensions_loaded={"dim_state": 52},
            facts_loaded={"fact_census_income": 1000},
        )
        assert stats.total_rows == 52 + 1000

    def test_has_errors_false(self) -> None:
        """has_errors should be False when no errors."""
        stats = LoadStats(source="test")
        assert stats.has_errors is False

    def test_has_errors_true(self) -> None:
        """has_errors should be True when errors present."""
        stats = LoadStats(source="test", errors=["Error 1", "Error 2"])
        assert stats.has_errors is True


class TestLoadStatsStr:
    """Tests for LoadStats string representation."""

    def test_str_includes_source(self) -> None:
        """String representation should include source."""
        stats = LoadStats(source="census")
        assert "census" in str(stats)

    def test_str_includes_dimension_count(self) -> None:
        """String representation should include dimension count."""
        stats = LoadStats(
            source="test",
            dimensions_loaded={"dim_state": 52},
        )
        output = str(stats)
        assert "52" in output or "Dimensions" in output

    def test_str_includes_api_calls_if_nonzero(self) -> None:
        """String representation should include API calls if > 0."""
        stats = LoadStats(source="test", api_calls=100)
        assert "100" in str(stats) or "API" in str(stats)

    def test_str_includes_error_count_if_present(self) -> None:
        """String representation should include error count if errors."""
        stats = LoadStats(source="test", errors=["Error 1"])
        assert "1" in str(stats) or "Error" in str(stats)


# =============================================================================
# DATALOADER ABC TESTS
# =============================================================================


class ConcreteTestLoader(DataLoader):
    """Concrete implementation of DataLoader for testing."""

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Simple test implementation."""
        stats = LoadStats(source="test")
        if reset:
            self.clear_tables(session)
        # Add a test state
        state = DimState(state_fips="99", state_name="Test State", state_abbrev="TS")
        session.add(state)
        session.flush()
        stats.dimensions_loaded["dim_state"] = 1
        return stats

    def get_dimension_tables(self) -> list[type]:
        """Return test dimension tables."""
        return [DimState]

    def get_fact_tables(self) -> list[type]:
        """Return empty list (no facts in test)."""
        return []


@pytest.fixture
def test_session() -> Session:
    """Create in-memory test session."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


class TestDataLoaderABC:
    """Tests for DataLoader abstract base class."""

    def test_cannot_instantiate_abstract(self) -> None:
        """DataLoader cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataLoader()  # type: ignore[abstract]

    def test_concrete_implementation_works(self) -> None:
        """Concrete implementation can be instantiated."""
        loader = ConcreteTestLoader()
        assert loader is not None

    def test_default_config_if_none_provided(self) -> None:
        """DataLoader should use default config if none provided."""
        loader = ConcreteTestLoader()
        assert loader.config is not None
        assert isinstance(loader.config, LoaderConfig)
        assert loader.config.batch_size == 10_000

    def test_accepts_custom_config(self) -> None:
        """DataLoader should accept custom config."""
        config = LoaderConfig(batch_size=5000)
        loader = ConcreteTestLoader(config)
        assert loader.config.batch_size == 5000

    def test_load_returns_loadstats(self, test_session: Session) -> None:
        """load() should return LoadStats."""
        loader = ConcreteTestLoader()
        stats = loader.load(test_session)
        assert isinstance(stats, LoadStats)

    def test_load_populates_stats(self, test_session: Session) -> None:
        """load() should populate LoadStats with counts."""
        loader = ConcreteTestLoader()
        stats = loader.load(test_session)
        assert stats.dimensions_loaded.get("dim_state") == 1

    def test_get_dimension_tables_returns_list(self) -> None:
        """get_dimension_tables() should return list of table classes."""
        loader = ConcreteTestLoader()
        tables = loader.get_dimension_tables()
        assert isinstance(tables, list)
        assert DimState in tables

    def test_get_fact_tables_returns_list(self) -> None:
        """get_fact_tables() should return list of table classes."""
        loader = ConcreteTestLoader()
        tables = loader.get_fact_tables()
        assert isinstance(tables, list)


class TestDataLoaderClearTables:
    """Tests for DataLoader.clear_tables() method."""

    def test_clear_tables_removes_data(self, test_session: Session) -> None:
        """clear_tables() should remove data from loader's tables."""
        loader = ConcreteTestLoader()

        # Load some data
        loader.load(test_session, reset=False)
        assert test_session.query(DimState).count() == 1

        # Clear tables
        loader.clear_tables(test_session)
        test_session.commit()

        assert test_session.query(DimState).count() == 0

    def test_clear_tables_respects_table_list(self, test_session: Session) -> None:
        """clear_tables() should only clear tables from get_*_tables()."""
        loader = ConcreteTestLoader()

        # The loader only handles DimState, so other tables should be unaffected
        # (This is a structural test - we verify the method uses get_*_tables)
        dimension_tables = loader.get_dimension_tables()
        assert DimState in dimension_tables

    def test_reset_true_clears_before_load(self, test_session: Session) -> None:
        """load(reset=True) should clear existing data."""
        loader = ConcreteTestLoader()

        # Load data twice with reset=True
        loader.load(test_session, reset=True)
        loader.load(test_session, reset=True)

        # Should only have 1 row (second load cleared first)
        assert test_session.query(DimState).count() == 1

    def test_reset_false_accumulates(self, test_session: Session) -> None:
        """load(reset=False) should accumulate data."""
        loader = ConcreteTestLoader()

        # Load data twice without reset
        loader.load(test_session, reset=False)

        # Manually add another state
        state2 = DimState(state_fips="98", state_name="Test State 2", state_abbrev="T2")
        test_session.add(state2)
        test_session.flush()

        # Should have 2 rows
        assert test_session.query(DimState).count() == 2


class TestDataLoaderInterface:
    """Tests verifying DataLoader interface contract."""

    def test_load_signature(self) -> None:
        """load() should have expected signature."""
        import inspect

        sig = inspect.signature(DataLoader.load)
        params = list(sig.parameters.keys())

        assert "session" in params
        assert "reset" in params
        assert "verbose" in params
        assert "kwargs" in params

    def test_get_dimension_tables_returns_types(self) -> None:
        """get_dimension_tables() should return type objects."""
        loader = ConcreteTestLoader()
        tables = loader.get_dimension_tables()

        for table in tables:
            assert isinstance(table, type)
            assert hasattr(table, "__tablename__")

    def test_get_fact_tables_returns_types(self) -> None:
        """get_fact_tables() should return type objects."""
        loader = ConcreteTestLoader()
        tables = loader.get_fact_tables()

        for table in tables:
            assert isinstance(table, type)
            assert hasattr(table, "__tablename__")
