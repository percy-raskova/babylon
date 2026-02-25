"""Tests for BLSProductivityLoader (Feature 021, US5)."""

from __future__ import annotations

from babylon.data.bls_productivity.loader import BLSProductivityLoader
from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.reference.schema import FactBLSProductivity


class TestBLSProductivityLoader:
    """Tests for BLS productivity data loader."""

    def test_is_data_loader(self) -> None:
        """Loader extends DataLoader ABC."""
        loader = BLSProductivityLoader()
        assert isinstance(loader, DataLoader)

    def test_source_code(self) -> None:
        """Loader has correct source code."""
        assert BLSProductivityLoader.SOURCE_CODE == "BLS_PRODUCTIVITY"

    def test_fact_tables(self) -> None:
        """Loader declares correct fact tables."""
        loader = BLSProductivityLoader()
        tables = loader.get_fact_tables()
        assert FactBLSProductivity in tables

    def test_dimension_tables_empty(self) -> None:
        """Loader has no specific dimension tables."""
        loader = BLSProductivityLoader()
        assert loader.get_dimension_tables() == []

    def test_accepts_loader_config(self) -> None:
        """Loader accepts LoaderConfig."""
        config = LoaderConfig(bls_productivity_years=[2018, 2019])
        loader = BLSProductivityLoader(config)
        assert loader.config.bls_productivity_years == [2018, 2019]

    def test_check_source_files_warns_on_missing(self) -> None:
        """Preflight warns when data directory is missing."""
        from pathlib import Path

        loader = BLSProductivityLoader()
        checks = loader.check_source_files(Path("/nonexistent"))
        assert len(checks) == 1
        assert checks[0].status == "warn"
