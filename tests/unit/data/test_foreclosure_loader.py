"""Tests for ForeclosureRateLoader (Feature 021, US5)."""

from __future__ import annotations

from babylon.data.foreclosure.loader import ForeclosureRateLoader
from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.reference.schema import FactForeclosureRate


class TestForeclosureRateLoader:
    """Tests for foreclosure rate data loader."""

    def test_is_data_loader(self) -> None:
        """Loader extends DataLoader ABC."""
        loader = ForeclosureRateLoader()
        assert isinstance(loader, DataLoader)

    def test_source_code(self) -> None:
        """Loader has correct source code."""
        assert ForeclosureRateLoader.SOURCE_CODE == "HUD_FORECLOSURE"

    def test_fact_tables(self) -> None:
        """Loader declares correct fact tables."""
        loader = ForeclosureRateLoader()
        tables = loader.get_fact_tables()
        assert FactForeclosureRate in tables

    def test_dimension_tables_empty(self) -> None:
        """Loader has no specific dimension tables."""
        loader = ForeclosureRateLoader()
        assert loader.get_dimension_tables() == []

    def test_accepts_loader_config(self) -> None:
        """Loader accepts LoaderConfig."""
        config = LoaderConfig(foreclosure_years=[2008, 2009, 2010])
        loader = ForeclosureRateLoader(config)
        assert loader.config.foreclosure_years == [2008, 2009, 2010]

    def test_check_source_files_warns_on_missing(self) -> None:
        """Preflight warns when data directory is missing."""
        from pathlib import Path

        loader = ForeclosureRateLoader()
        checks = loader.check_source_files(Path("/nonexistent"))
        assert len(checks) == 1
        assert checks[0].status == "warn"
