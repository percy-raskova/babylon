"""Unit tests for Energy data loader.

Tests the EnergyLoader class for:
- Year filtering via LoaderConfig.energy_years list
- Backwards compatibility with start_year/end_year
- CLI parameter changes
"""

from __future__ import annotations

import inspect

from babylon.data.energy.loader_3nf import EnergyLoader
from babylon.data.loader_base import DataLoader, LoaderConfig


class TestEnergyLoaderConfig:
    """Test LoaderConfig integration with Energy loader."""

    def test_loader_accepts_years_list_from_config(self) -> None:
        """Loader should read years from LoaderConfig.energy_years."""
        config = LoaderConfig(energy_years=[2020, 2021, 2022])
        loader = EnergyLoader(config)
        assert loader.config.energy_years == [2020, 2021, 2022]

    def test_default_years_is_none_means_all(self) -> None:
        """Default config should have None for energy_years (load all)."""
        config = LoaderConfig()
        assert config.energy_years is None

    def test_backwards_compat_start_end_preserved(self) -> None:
        """Start/end year fields should still exist for backwards compatibility."""
        config = LoaderConfig(energy_start_year=2000, energy_end_year=2020)
        assert config.energy_start_year == 2000
        assert config.energy_end_year == 2020

    def test_loader_inherits_from_data_loader(self) -> None:
        """EnergyLoader should inherit from DataLoader base class."""
        loader = EnergyLoader()
        assert isinstance(loader, DataLoader)

    def test_loader_has_correct_dimension_tables(self) -> None:
        """EnergyLoader should declare its dimension tables."""
        loader = EnergyLoader()
        dim_tables = loader.get_dimension_tables()
        assert len(dim_tables) > 0
        table_names = [t.__name__ for t in dim_tables]
        assert "DimEnergyTable" in table_names
        assert "DimEnergySeries" in table_names

    def test_loader_has_correct_fact_tables(self) -> None:
        """EnergyLoader should declare its fact tables."""
        loader = EnergyLoader()
        fact_tables = loader.get_fact_tables()
        assert len(fact_tables) > 0
        table_names = [t.__name__ for t in fact_tables]
        assert "FactEnergyAnnual" in table_names


class TestYearFiltering:
    """Test year filtering functionality for Energy loader."""

    def test_get_year_range_from_years_list(self) -> None:
        """Should derive year range from energy_years list."""
        config = LoaderConfig(energy_years=[2020, 2021, 2022])
        loader = EnergyLoader(config)
        start, end = loader._get_year_range()
        assert start == 2020
        assert end == 2022

    def test_get_year_range_fallback_to_start_end(self) -> None:
        """Should fall back to start_year/end_year when energy_years is None."""
        config = LoaderConfig(
            energy_years=None,
            energy_start_year=1990,
            energy_end_year=2024,
        )
        loader = EnergyLoader(config)
        start, end = loader._get_year_range()
        assert start == 1990
        assert end == 2024

    def test_years_list_precedence_over_start_end(self) -> None:
        """energy_years list should take precedence over start/end year."""
        config = LoaderConfig(
            energy_years=[2020, 2021],
            energy_start_year=1990,  # Should be ignored
            energy_end_year=2024,  # Should be ignored
        )
        loader = EnergyLoader(config)
        start, end = loader._get_year_range()
        assert start == 2020
        assert end == 2021

    def test_non_contiguous_years_uses_min_max(self) -> None:
        """Non-contiguous year list should use min/max for API range."""
        config = LoaderConfig(energy_years=[2015, 2020, 2023])
        loader = EnergyLoader(config)
        start, end = loader._get_year_range()
        assert start == 2015
        assert end == 2023


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing interfaces."""

    def test_cli_accepts_start_end_year_params(self) -> None:
        """CLI should still accept --start-year and --end-year for backwards compat."""
        from babylon.data.cli import energy

        sig = inspect.signature(energy)
        param_names = list(sig.parameters.keys())
        assert "start_year" in param_names
        assert "end_year" in param_names

    def test_cli_accepts_years_param(self) -> None:
        """CLI should accept --years param (new, preferred)."""
        from babylon.data.cli import energy

        sig = inspect.signature(energy)
        param_names = list(sig.parameters.keys())
        assert "years" in param_names

    def test_cli_reset_defaults_to_false(self) -> None:
        """CLI reset should default to False (changed from True)."""
        from babylon.data.cli import energy

        sig = inspect.signature(energy)
        reset_param = sig.parameters["reset"]
        assert reset_param.default is False
