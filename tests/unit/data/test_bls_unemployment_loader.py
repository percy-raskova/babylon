"""Tests for BLSUnemploymentLoader (Feature 021, US5)."""

from __future__ import annotations

from babylon.data.bls_unemployment.loader import BLSUnemploymentLoader
from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.reference.schema import FactBLSUnemploymentDecomposition


class TestBLSUnemploymentLoader:
    """Tests for BLS unemployment decomposition loader."""

    def test_is_data_loader(self) -> None:
        """Loader extends DataLoader ABC."""
        loader = BLSUnemploymentLoader()
        assert isinstance(loader, DataLoader)

    def test_source_code(self) -> None:
        """Loader has correct source code."""
        assert BLSUnemploymentLoader.SOURCE_CODE == "BLS_LAUS"

    def test_fact_tables(self) -> None:
        """Loader declares correct fact tables."""
        loader = BLSUnemploymentLoader()
        tables = loader.get_fact_tables()
        assert FactBLSUnemploymentDecomposition in tables

    def test_dimension_tables_empty(self) -> None:
        """Loader has no specific dimension tables."""
        loader = BLSUnemploymentLoader()
        assert loader.get_dimension_tables() == []

    def test_accepts_loader_config(self) -> None:
        """Loader accepts LoaderConfig."""
        config = LoaderConfig(bls_unemployment_years=[2010, 2011])
        loader = BLSUnemploymentLoader(config)
        assert loader.config.bls_unemployment_years == [2010, 2011]

    def test_check_source_files_warns_on_missing(self) -> None:
        """Preflight warns when data directory is missing."""
        from pathlib import Path

        loader = BLSUnemploymentLoader()
        checks = loader.check_source_files(Path("/nonexistent"))
        assert len(checks) == 1
        assert checks[0].status == "warn"
