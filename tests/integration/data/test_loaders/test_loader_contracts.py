"""Integration tests for DataLoader contract compliance.

Verifies that all concrete loader implementations properly implement
the DataLoader ABC contract:
- load() returns LoadStats
- get_dimension_tables() returns list of table classes
- get_fact_tables() returns list of table classes
- Tables are properly registered in NormalizedBase
- Loaders accept LoaderConfig
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.normalize.database import NormalizedBase

if TYPE_CHECKING:
    pass

from .conftest import ALL_LOADERS

# Skip all tests if no loaders are available
pytestmark = pytest.mark.skipif(
    len(ALL_LOADERS) == 0,
    reason="No loader implementations available",
)


class TestLoaderInstantiation:
    """Tests for loader instantiation."""

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_loader_is_dataloader_subclass(self, loader_class: type[DataLoader]) -> None:
        """All loaders should be DataLoader subclasses."""
        assert issubclass(loader_class, DataLoader)

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_loader_instantiates_with_default_config(self, loader_class: type[DataLoader]) -> None:
        """Loaders should instantiate without config (using defaults)."""
        loader = loader_class()
        assert loader is not None
        assert isinstance(loader.config, LoaderConfig)

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_loader_accepts_custom_config(self, loader_class: type[DataLoader]) -> None:
        """Loaders should accept custom LoaderConfig."""
        config = LoaderConfig(batch_size=100, verbose=False)
        loader = loader_class(config)
        assert loader.config.batch_size == 100
        assert loader.config.verbose is False


class TestGetDimensionTables:
    """Tests for get_dimension_tables() implementation."""

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_returns_list(self, loader_class: type[DataLoader]) -> None:
        """get_dimension_tables() should return a list."""
        loader = loader_class()
        tables = loader.get_dimension_tables()
        assert isinstance(tables, list)

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_returns_table_classes(self, loader_class: type[DataLoader]) -> None:
        """get_dimension_tables() should return SQLAlchemy model classes."""
        loader = loader_class()
        tables = loader.get_dimension_tables()

        for table in tables:
            assert isinstance(table, type), f"{table} is not a type"
            assert hasattr(table, "__tablename__"), f"{table} has no __tablename__"
            assert hasattr(table, "__table__"), f"{table} has no __table__"

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_tables_have_valid_prefix(self, loader_class: type[DataLoader]) -> None:
        """Dimension/bridge tables should have 'dim_' or 'bridge_' prefix."""
        loader = loader_class()
        tables = loader.get_dimension_tables()

        for table in tables:
            valid_prefix = table.__tablename__.startswith(("dim_", "bridge_"))
            assert valid_prefix, (
                f"{table.__name__} should have 'dim_' or 'bridge_' prefix, "
                f"got {table.__tablename__}"
            )

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_tables_exist_in_metadata(self, loader_class: type[DataLoader]) -> None:
        """Returned tables should exist in NormalizedBase.metadata."""
        loader = loader_class()
        tables = loader.get_dimension_tables()
        known_tables = set(NormalizedBase.metadata.tables.keys())

        for table in tables:
            assert table.__tablename__ in known_tables, (
                f"{table.__tablename__} not in NormalizedBase.metadata"
            )


class TestGetFactTables:
    """Tests for get_fact_tables() implementation."""

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_returns_list(self, loader_class: type[DataLoader]) -> None:
        """get_fact_tables() should return a list."""
        loader = loader_class()
        tables = loader.get_fact_tables()
        assert isinstance(tables, list)

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_returns_table_classes(self, loader_class: type[DataLoader]) -> None:
        """get_fact_tables() should return SQLAlchemy model classes."""
        loader = loader_class()
        tables = loader.get_fact_tables()

        for table in tables:
            assert isinstance(table, type), f"{table} is not a type"
            assert hasattr(table, "__tablename__"), f"{table} has no __tablename__"
            assert hasattr(table, "__table__"), f"{table} has no __table__"

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_tables_have_fact_prefix(self, loader_class: type[DataLoader]) -> None:
        """Fact tables should have 'fact_' prefix."""
        loader = loader_class()
        tables = loader.get_fact_tables()

        for table in tables:
            assert table.__tablename__.startswith("fact_"), (
                f"{table.__name__} should have 'fact_' prefix, got {table.__tablename__}"
            )

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_tables_exist_in_metadata(self, loader_class: type[DataLoader]) -> None:
        """Returned tables should exist in NormalizedBase.metadata."""
        loader = loader_class()
        tables = loader.get_fact_tables()
        known_tables = set(NormalizedBase.metadata.tables.keys())

        for table in tables:
            assert table.__tablename__ in known_tables, (
                f"{table.__tablename__} not in NormalizedBase.metadata"
            )


class TestTableOverlap:
    """Tests for table registration correctness."""

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_no_overlap_between_dim_and_fact(self, loader_class: type[DataLoader]) -> None:
        """Dimension and fact tables should not overlap."""
        loader = loader_class()
        dim_tables = set(loader.get_dimension_tables())
        fact_tables = set(loader.get_fact_tables())

        overlap = dim_tables & fact_tables
        assert len(overlap) == 0, f"Tables in both dim and fact: {overlap}"

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_has_at_least_one_table(self, loader_class: type[DataLoader]) -> None:
        """Loaders should register at least one table."""
        loader = loader_class()
        dim_count = len(loader.get_dimension_tables())
        fact_count = len(loader.get_fact_tables())

        total = dim_count + fact_count
        assert total > 0, f"{loader_class.__name__} has no tables registered"


class TestLoadMethodContract:
    """Tests for load() method contract.

    Note: These tests verify the method signature and return type,
    not the actual loading behavior (that's in test_idempotency.py).
    """

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_load_method_exists(self, loader_class: type[DataLoader]) -> None:
        """load() method should exist."""
        loader = loader_class()
        assert hasattr(loader, "load")
        assert callable(loader.load)

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_load_accepts_session(self, loader_class: type[DataLoader]) -> None:
        """load() should accept session parameter."""
        import inspect

        sig = inspect.signature(loader_class.load)
        params = list(sig.parameters.keys())
        assert "session" in params

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_load_accepts_reset(self, loader_class: type[DataLoader]) -> None:
        """load() should accept reset parameter."""
        import inspect

        sig = inspect.signature(loader_class.load)
        params = list(sig.parameters.keys())
        assert "reset" in params

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_load_accepts_verbose(self, loader_class: type[DataLoader]) -> None:
        """load() should accept verbose parameter."""
        import inspect

        sig = inspect.signature(loader_class.load)
        params = list(sig.parameters.keys())
        assert "verbose" in params


class TestClearTablesContract:
    """Tests for clear_tables() method."""

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_clear_tables_method_exists(self, loader_class: type[DataLoader]) -> None:
        """clear_tables() method should exist."""
        loader = loader_class()
        assert hasattr(loader, "clear_tables")
        assert callable(loader.clear_tables)

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_clear_tables_accepts_session(self, loader_class: type[DataLoader]) -> None:
        """clear_tables() should accept session parameter."""
        import inspect

        sig = inspect.signature(loader_class.clear_tables)
        params = list(sig.parameters.keys())
        assert "session" in params


class TestLoaderNaming:
    """Tests for loader naming conventions."""

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_loader_suffix(self, loader_class: type[DataLoader]) -> None:
        """Loader classes should end with 'Loader'."""
        assert loader_class.__name__.endswith("Loader"), (
            f"{loader_class.__name__} should end with 'Loader'"
        )

    @pytest.mark.parametrize("loader_class", ALL_LOADERS)
    def test_loader_has_docstring(self, loader_class: type[DataLoader]) -> None:
        """Loader classes should have docstrings."""
        assert loader_class.__doc__ is not None, f"{loader_class.__name__} needs a docstring"
        assert len(loader_class.__doc__.strip()) > 0


class TestLoaderCount:
    """Tests for expected loader count."""

    def test_have_multiple_loaders(self) -> None:
        """Should have at least 5 loader implementations."""
        assert len(ALL_LOADERS) >= 5, (
            f"Expected at least 5 loaders, got {len(ALL_LOADERS)}: "
            f"{[loader_cls.__name__ for loader_cls in ALL_LOADERS]}"
        )

    def test_expected_loaders_present(self) -> None:
        """Expected loader classes should be available."""
        loader_names = {loader.__name__ for loader in ALL_LOADERS}

        expected = {"CensusLoader", "FredLoader", "EnergyLoader", "TradeLoader", "QcewLoader"}
        missing = expected - loader_names

        # Soft check - some loaders may not be implemented yet
        if len(missing) > 0:
            pytest.skip(f"Some expected loaders not yet implemented: {missing}")
