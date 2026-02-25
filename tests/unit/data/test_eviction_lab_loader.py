"""Tests for EvictionLabLoader (Feature 021, US5)."""

from __future__ import annotations

from babylon.data.eviction_lab.loader import EvictionLabLoader
from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.reference.schema import FactEvictionLabFiling


class TestEvictionLabLoader:
    """Tests for Eviction Lab data loader."""

    def test_is_data_loader(self) -> None:
        """Loader extends DataLoader ABC."""
        loader = EvictionLabLoader()
        assert isinstance(loader, DataLoader)

    def test_source_code(self) -> None:
        """Loader has correct source code."""
        assert EvictionLabLoader.SOURCE_CODE == "EVICTION_LAB"

    def test_fact_tables(self) -> None:
        """Loader declares correct fact tables."""
        loader = EvictionLabLoader()
        tables = loader.get_fact_tables()
        assert FactEvictionLabFiling in tables

    def test_dimension_tables_empty(self) -> None:
        """Loader has no specific dimension tables."""
        loader = EvictionLabLoader()
        assert loader.get_dimension_tables() == []

    def test_accepts_loader_config(self) -> None:
        """Loader accepts LoaderConfig."""
        config = LoaderConfig(eviction_lab_years=[2010, 2011])
        loader = EvictionLabLoader(config)
        assert loader.config.eviction_lab_years == [2010, 2011]

    def test_check_source_files_warns_on_missing(self) -> None:
        """Preflight warns when data directory is missing."""
        from pathlib import Path

        loader = EvictionLabLoader()
        checks = loader.check_source_files(Path("/nonexistent"))
        assert len(checks) == 1
        assert checks[0].status == "warn"
