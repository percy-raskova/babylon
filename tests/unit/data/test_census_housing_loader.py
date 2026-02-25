"""Tests for CensusHousingLoader (Feature 021, US5)."""

from __future__ import annotations

from babylon.data.census_housing.loader import CensusHousingLoader
from babylon.data.loader_base import DataLoader, LoaderConfig
from babylon.data.reference.schema import FactCensusInstitutionalOwnership


class TestCensusHousingLoader:
    """Tests for Census housing data loader."""

    def test_is_data_loader(self) -> None:
        """Loader extends DataLoader ABC."""
        loader = CensusHousingLoader()
        assert isinstance(loader, DataLoader)

    def test_source_code(self) -> None:
        """Loader has correct source code."""
        assert CensusHousingLoader.SOURCE_CODE == "CENSUS_ACS_HOUSING"

    def test_fact_tables(self) -> None:
        """Loader declares correct fact tables."""
        loader = CensusHousingLoader()
        tables = loader.get_fact_tables()
        assert FactCensusInstitutionalOwnership in tables

    def test_dimension_tables_empty(self) -> None:
        """Loader has no specific dimension tables."""
        loader = CensusHousingLoader()
        assert loader.get_dimension_tables() == []

    def test_accepts_loader_config(self) -> None:
        """Loader accepts LoaderConfig."""
        config = LoaderConfig(census_housing_years=[2015, 2016])
        loader = CensusHousingLoader(config)
        assert loader.config.census_housing_years == [2015, 2016]

    def test_check_source_files_warns_on_missing(self) -> None:
        """Preflight warns when data directory is missing."""
        from pathlib import Path

        loader = CensusHousingLoader()
        checks = loader.check_source_files(Path("/nonexistent"))
        assert len(checks) == 1
        assert checks[0].status == "warn"
