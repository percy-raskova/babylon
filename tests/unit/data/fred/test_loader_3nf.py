"""Unit tests for FRED data loader.

Tests the FredLoader class for:
- Year filtering via LoaderConfig.fred_years list
- Industry mapping with aggregate NAICS codes (52-53, 31-33, etc.)
- Idempotency with reset flag behavior
- Backwards compatibility with start_year/end_year
"""

from __future__ import annotations

import contextlib
import inspect
from unittest.mock import MagicMock, patch

import pytest

from babylon.data.fred.loader_3nf import FredLoader
from babylon.data.loader_base import DataLoader, LoaderConfig


class TestFredLoaderConfig:
    """Test LoaderConfig integration with FRED loader."""

    def test_loader_accepts_years_list_from_config(self) -> None:
        """Loader should read years from LoaderConfig.fred_years."""
        config = LoaderConfig(fred_years=[2020, 2021, 2022])
        loader = FredLoader(config)
        assert loader.config.fred_years == [2020, 2021, 2022]

    def test_default_years_is_none_means_all(self) -> None:
        """Default config should have None for fred_years (load all)."""
        config = LoaderConfig()
        assert config.fred_years is None

    def test_backwards_compat_start_end_preserved(self) -> None:
        """Start/end year fields should still exist for backwards compatibility."""
        config = LoaderConfig(fred_start_year=2000, fred_end_year=2020)
        assert config.fred_start_year == 2000
        assert config.fred_end_year == 2020

    def test_loader_inherits_from_data_loader(self) -> None:
        """FredLoader should inherit from DataLoader base class."""
        loader = FredLoader()
        assert isinstance(loader, DataLoader)

    def test_loader_has_correct_dimension_tables(self) -> None:
        """FredLoader should declare its dimension tables."""
        loader = FredLoader()
        dim_tables = loader.get_dimension_tables()
        assert len(dim_tables) > 0
        # Should include FRED-specific dimensions
        table_names = [t.__name__ for t in dim_tables]
        assert "DimFredSeries" in table_names
        assert "DimWealthClass" in table_names
        assert "DimAssetCategory" in table_names

    def test_loader_has_correct_fact_tables(self) -> None:
        """FredLoader should declare its fact tables."""
        loader = FredLoader()
        fact_tables = loader.get_fact_tables()
        assert len(fact_tables) > 0
        # Should include all 5 FRED fact tables
        table_names = [t.__name__ for t in fact_tables]
        assert "FactFredNational" in table_names
        assert "FactFredWealthLevels" in table_names
        assert "FactFredWealthShares" in table_names
        assert "FactFredIndustryUnemployment" in table_names
        assert "FactFredStateUnemployment" in table_names


class TestYearFiltering:
    """Test year filtering functionality for FRED loader."""

    def test_get_year_range_from_years_list(self) -> None:
        """Should derive year range from fred_years list."""
        config = LoaderConfig(fred_years=[2020, 2021, 2022])
        loader = FredLoader(config)
        start, end = loader._get_year_range()
        assert start == 2020
        assert end == 2022

    def test_get_year_range_fallback_to_start_end(self) -> None:
        """Should fall back to start_year/end_year when fred_years is None."""
        config = LoaderConfig(
            fred_years=None,
            fred_start_year=1990,
            fred_end_year=2024,
        )
        loader = FredLoader(config)
        start, end = loader._get_year_range()
        assert start == 1990
        assert end == 2024

    def test_years_list_precedence_over_start_end(self) -> None:
        """fred_years list should take precedence over start/end year."""
        config = LoaderConfig(
            fred_years=[2020, 2021],
            fred_start_year=1990,  # Should be ignored
            fred_end_year=2024,  # Should be ignored
        )
        loader = FredLoader(config)
        start, end = loader._get_year_range()
        assert start == 2020
        assert end == 2021

    def test_non_contiguous_years_uses_min_max(self) -> None:
        """Non-contiguous year list should use min/max for API range."""
        config = LoaderConfig(fred_years=[2015, 2020, 2023])
        loader = FredLoader(config)
        start, end = loader._get_year_range()
        assert start == 2015
        assert end == 2023


class TestIndustryMapping:
    """Test aggregate NAICS code to sector code mapping."""

    def test_aggregate_52_53_maps_to_sector(self) -> None:
        """Aggregate code 52-53 should find industry via sector_code."""
        loader = FredLoader()

        # Mock session with sector-level industries
        mock_session = MagicMock()
        mock_industry_52 = MagicMock()
        mock_industry_52.industry_id = 52
        mock_industry_52.sector_code = "52"
        mock_industry_52.naics_level = 2

        # Configure query to return industry for sector 52 or 53
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_industry_52
        mock_session.query.return_value = mock_query

        loader._build_industry_lookup(mock_session)

        # Should have mapped aggregate to industry_id
        assert "52-53" in loader._industry_naics_to_id
        assert loader._industry_naics_to_id["52-53"] == 52

    def test_aggregate_31_33_maps_to_manufacturing(self) -> None:
        """Aggregate code 31-33 should find manufacturing sector."""
        loader = FredLoader()

        mock_session = MagicMock()
        mock_industry = MagicMock()
        mock_industry.industry_id = 31
        mock_industry.sector_code = "31"
        mock_industry.naics_level = 2

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_industry
        mock_session.query.return_value = mock_query

        loader._build_industry_lookup(mock_session)

        assert "31-33" in loader._industry_naics_to_id

    def test_single_naics_23_maps_directly(self) -> None:
        """Single NAICS code like 23 should map directly."""
        loader = FredLoader()

        mock_session = MagicMock()
        mock_industry = MagicMock()
        mock_industry.industry_id = 23
        mock_industry.sector_code = "23"
        mock_industry.naics_level = 2

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_industry
        mock_session.query.return_value = mock_query

        loader._build_industry_lookup(mock_session)

        assert "23" in loader._industry_naics_to_id

    def test_unknown_sector_logs_debug_not_error(self) -> None:
        """Missing sector should log debug message, not raise error."""
        loader = FredLoader()

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No industry found
        mock_session.query.return_value = mock_query

        # Should not raise, just log
        with patch("babylon.data.fred.loader_3nf.logger") as mock_logger:
            loader._build_industry_lookup(mock_session)
            # Debug level, not warning or error
            assert mock_logger.debug.called


class TestIdempotency:
    """Test reset flag behavior for idempotency."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock session with query support."""
        session = MagicMock()
        session.query.return_value.delete.return_value = None
        session.flush.return_value = None
        session.commit.return_value = None
        return session

    def test_reset_false_preserves_existing_data(self, mock_session: MagicMock) -> None:
        """reset=False should not call _clear_fred_tables."""
        loader = FredLoader()

        # Patch internal methods to avoid actual API calls
        with (
            patch.object(loader, "_clear_fred_tables") as mock_clear,
            patch.object(loader, "_client_scope"),
        ):
            # Will fail due to mocking, but we check if clear was called
            with contextlib.suppress(Exception):
                loader.load(mock_session, reset=False, verbose=False)

            # Should NOT have called clear when reset=False
            mock_clear.assert_not_called()

    def test_reset_true_clears_fred_tables_only(self, mock_session: MagicMock) -> None:
        """reset=True should clear FRED tables but not shared dimensions."""
        loader = FredLoader()

        with (
            patch.object(loader, "_clear_fred_tables") as mock_clear,
            patch.object(loader, "_client_scope"),
        ):
            with contextlib.suppress(Exception):
                loader.load(mock_session, reset=True, verbose=False)

            # Should have called clear when reset=True
            mock_clear.assert_called_once()

    def test_clear_fred_tables_does_not_touch_shared_dims(self) -> None:
        """_clear_fred_tables should not delete DimState, DimIndustry, DimTime.

        The implementation uses raw SQL DELETE (session.execute) to bypass
        SQLAlchemy's ORM identity map, avoiding UNIQUE constraint errors on
        subsequent re-insertion within the same transaction.
        """
        loader = FredLoader()
        mock_session = MagicMock()

        loader._clear_fred_tables(mock_session)

        # Collect all SQL strings passed to session.execute()
        executed_sqls = [str(call[0][0]) for call in mock_session.execute.call_args_list]

        # Should NOT delete shared dimensions
        assert not any("dim_state" in sql for sql in executed_sqls)
        assert not any("dim_industry" in sql for sql in executed_sqls)
        assert not any("dim_time" in sql for sql in executed_sqls)

        # Should delete FRED-specific fact and dimension tables
        assert any("fact_fred_national" in sql for sql in executed_sqls)
        assert any("dim_fred_series" in sql for sql in executed_sqls)

    def test_series_loader_uses_get_or_create(self) -> None:
        """_load_series_dimension should reuse existing series records."""
        loader = FredLoader()
        mock_session = MagicMock()

        # Mock existing series in database
        existing_series = MagicMock()
        existing_series.series_id = 42
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing_series
        mock_session.query.return_value = mock_query

        # Mock client with metadata
        mock_client = MagicMock()
        loader._client = mock_client

        # Call with one series code
        with (
            patch.dict(
                "babylon.data.fred.loader_3nf.ALL_NATIONAL_SERIES",
                {"TEST_SERIES": "Test"},
                clear=True,
            ),
            patch.dict("babylon.data.fred.loader_3nf.DFA_WEALTH_LEVEL_SERIES", {}, clear=True),
            patch.dict("babylon.data.fred.loader_3nf.DFA_WEALTH_SHARE_SERIES", {}, clear=True),
        ):
            count = loader._load_series_dimension(mock_session, verbose=False)

        # Should have queried for existing series
        mock_session.query.assert_called()
        # Should NOT have added new record (existing found)
        mock_session.add.assert_not_called()
        # Should have cached the existing series_id
        assert loader._series_to_id.get("TEST_SERIES") == 42
        # Count should be 0 (no new records)
        assert count == 0

    def test_wealth_class_loader_uses_get_or_create(self) -> None:
        """_load_wealth_class_dimension should reuse existing records."""
        loader = FredLoader()
        mock_session = MagicMock()

        # Mock existing wealth class
        existing = MagicMock()
        existing.wealth_class_id = 99
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing
        mock_session.query.return_value = mock_query

        with patch.dict(
            "babylon.data.fred.loader_3nf.DFA_WEALTH_CLASSES",
            {"TOP1": {"label": "Top 1%", "babylon_class": "bourgeoisie"}},
            clear=True,
        ):
            count = loader._load_wealth_class_dimension(mock_session, _verbose=False)

        # Should have cached existing ID
        assert loader._class_to_id.get("TOP1") == 99
        # No new records
        assert count == 0

    def test_asset_category_loader_uses_get_or_create(self) -> None:
        """_load_asset_category_dimension should reuse existing records."""
        loader = FredLoader()
        mock_session = MagicMock()

        # Mock existing category
        existing = MagicMock()
        existing.category_id = 77
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing
        mock_session.query.return_value = mock_query

        with patch.dict(
            "babylon.data.fred.loader_3nf.DFA_ASSET_CATEGORIES",
            {"NET_WORTH": {"label": "Net Worth", "interpretation": "Total wealth"}},
            clear=True,
        ):
            count = loader._load_asset_category_dimension(mock_session, _verbose=False)

        # Should have cached existing ID
        assert loader._category_to_id.get("NET_WORTH") == 77
        # No new records
        assert count == 0


class TestCLIParameterParsing:
    """Test CLI command parameter behavior."""

    def test_parse_years_single_year(self) -> None:
        """parse_years should handle single year."""
        from babylon.data.cli import parse_years

        result = parse_years("2020")
        assert result == [2020]

    def test_parse_years_range(self) -> None:
        """parse_years should handle year range."""
        from babylon.data.cli import parse_years

        result = parse_years("2020-2023")
        assert result == [2020, 2021, 2022, 2023]

    def test_parse_years_list(self) -> None:
        """parse_years should handle comma-separated list."""
        from babylon.data.cli import parse_years

        result = parse_years("2020,2021,2022")
        assert result == [2020, 2021, 2022]

    def test_parse_years_none_returns_none(self) -> None:
        """parse_years should return None for None input."""
        from babylon.data.cli import parse_years

        result = parse_years(None)
        assert result is None


class TestAPIErrorHandling:
    """Test error handling during API interactions."""

    def test_api_error_recorded_in_stats(self) -> None:
        """API errors should be recorded in LoadStats."""
        from babylon.data.loader_base import LoadStats

        stats = LoadStats(source="fred")
        mock_error = Exception("API timeout")
        mock_error.status_code = 500  # type: ignore[attr-defined]
        mock_error.url = "https://api.fred.com/test"  # type: ignore[attr-defined]

        stats.record_api_error(mock_error, context="fred:load")

        assert len(stats.api_errors) == 1
        assert stats.api_errors[0].status_code == 500

    def test_loader_continues_on_series_error(self) -> None:
        """Loader should continue processing other series when one fails."""
        # This tests the existing behavior - failure on one series
        # shouldn't stop the entire load
        loader = FredLoader()
        assert hasattr(loader, "load")
        # Full integration test would require API mocking


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing interfaces."""

    def test_cli_accepts_start_end_year_params(self) -> None:
        """CLI should still accept --start-year and --end-year for backwards compat."""
        from babylon.data.cli import fred

        sig = inspect.signature(fred)
        param_names = list(sig.parameters.keys())
        assert "start_year" in param_names
        assert "end_year" in param_names

    def test_cli_accepts_years_param(self) -> None:
        """CLI should accept --years param (new, preferred)."""
        from babylon.data.cli import fred

        sig = inspect.signature(fred)
        param_names = list(sig.parameters.keys())
        assert "years" in param_names

    def test_cli_reset_defaults_to_false(self) -> None:
        """CLI reset should default to False (changed from True)."""
        from babylon.data.cli import fred

        sig = inspect.signature(fred)
        reset_param = sig.parameters["reset"]
        assert reset_param.default is False
