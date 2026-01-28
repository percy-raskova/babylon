"""Unit tests for FCC Broadband Coverage loader.

Tests the FCCBroadbandLoader class with mocked database and file system.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from babylon.data.fcc.loader import DEFAULT_DOWNLOAD_DIR, FCCBroadbandLoader

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestFCCBroadbandLoaderInit:
    """Tests for loader initialization."""

    def test_init_with_defaults(self) -> None:
        """Initializes with default download directory."""
        loader = FCCBroadbandLoader()
        assert loader._download_dir == DEFAULT_DOWNLOAD_DIR

    def test_init_with_custom_download_dir(self) -> None:
        """Accepts custom download directory."""
        custom_dir = Path("/custom/path")
        loader = FCCBroadbandLoader(download_dir=custom_dir)
        assert loader._download_dir == custom_dir


@pytest.mark.unit
class TestFCCBroadbandLoaderTables:
    """Tests for table metadata methods."""

    def test_get_dimension_tables(self) -> None:
        """Returns dimension tables for FCC loader."""
        loader = FCCBroadbandLoader()
        tables = loader.get_dimension_tables()
        table_names = [t.__name__ for t in tables]
        assert "DimDataSource" in table_names

    def test_get_fact_tables(self) -> None:
        """Returns fact tables for FCC loader."""
        loader = FCCBroadbandLoader()
        tables = loader.get_fact_tables()
        table_names = [t.__name__ for t in tables]
        assert "FactBroadbandCoverage" in table_names


@pytest.mark.unit
class TestFCCBroadbandLoaderFindLatestDateDir:
    """Tests for date directory discovery."""

    def test_finds_latest_date_dir(self) -> None:
        """Finds most recent date directory."""
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir)

            # Create date directories
            (download_dir / "2025-03-31").mkdir()
            (download_dir / "2025-06-30").mkdir()
            (download_dir / "2025-01-15").mkdir()

            loader = FCCBroadbandLoader(download_dir=download_dir)
            latest = loader._find_latest_date_dir()

        assert latest is not None
        assert latest.name == "2025-06-30"

    def test_returns_none_for_empty_dir(self) -> None:
        """Returns None when no date directories exist."""
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir)
            loader = FCCBroadbandLoader(download_dir=download_dir)
            latest = loader._find_latest_date_dir()

        assert latest is None

    def test_returns_none_for_missing_dir(self) -> None:
        """Returns None when download directory doesn't exist."""
        loader = FCCBroadbandLoader(download_dir=Path("/nonexistent"))
        latest = loader._find_latest_date_dir()
        assert latest is None

    def test_ignores_non_date_directories(self) -> None:
        """Ignores directories that don't start with digits."""
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir)

            # Non-date directory
            (download_dir / "national").mkdir()
            (download_dir / "metadata").mkdir()

            # Date directory
            (download_dir / "2025-06-30").mkdir()

            loader = FCCBroadbandLoader(download_dir=download_dir)
            latest = loader._find_latest_date_dir()

        assert latest is not None
        assert latest.name == "2025-06-30"


@pytest.mark.unit
class TestFCCBroadbandLoaderToPercentage:
    """Tests for decimal to percentage conversion."""

    def test_converts_decimal_to_percentage(self) -> None:
        """Converts 0.0-1.0 decimal to 0.00-100.00 percentage."""
        result = FCCBroadbandLoader._to_percentage(Decimal("0.95"))
        assert result == Decimal("95.00")

    def test_rounds_to_two_decimal_places(self) -> None:
        """Rounds percentage to two decimal places."""
        result = FCCBroadbandLoader._to_percentage(Decimal("0.12345"))
        # Uses default Decimal.quantize rounding (ROUND_HALF_EVEN)
        assert result == Decimal("12.34")

    def test_handles_zero(self) -> None:
        """Handles zero value."""
        result = FCCBroadbandLoader._to_percentage(Decimal("0"))
        assert result == Decimal("0.00")

    def test_handles_one(self) -> None:
        """Handles 1.0 (100%)."""
        result = FCCBroadbandLoader._to_percentage(Decimal("1"))
        assert result == Decimal("100.00")


@pytest.mark.unit
class TestFCCBroadbandLoaderLoad:
    """Tests for load method with mocked dependencies."""

    def test_load_returns_error_for_missing_data(self) -> None:
        """Returns error stats when no data found."""
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir)

            mock_session = MagicMock()
            loader = FCCBroadbandLoader(download_dir=download_dir)

            stats = loader.load(mock_session, verbose=False)

        assert len(stats.errors) > 0
        assert "No download data" in stats.errors[0]

    def test_load_returns_error_for_missing_csv(self) -> None:
        """Returns error stats when CSV file not found."""
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir)

            # Create date dir but no national CSV
            date_dir = download_dir / "2025-06-30"
            date_dir.mkdir()
            (date_dir / "national").mkdir()

            mock_session = MagicMock()
            loader = FCCBroadbandLoader(download_dir=download_dir)

            stats = loader.load(mock_session, as_of_date="2025-06-30", verbose=False)

        assert len(stats.errors) > 0
        assert "No national CSV" in stats.errors[0]

    def test_load_with_specific_date(self) -> None:
        """Uses specified as_of_date for data path."""
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir)

            # Create both date directories
            (download_dir / "2025-03-31" / "national").mkdir(parents=True)
            (download_dir / "2025-06-30" / "national").mkdir(parents=True)

            # Create CSV in specific date directory
            csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
"""
            csv_path = (
                download_dir
                / "2025-03-31"
                / "national"
                / "fixed_broadband_summary_by_geography.csv"
            )
            csv_path.write_text(csv_content)

            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.all.return_value = []
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_session.query.return_value.all.return_value = []

            loader = FCCBroadbandLoader(download_dir=download_dir)

            with (
                patch.object(loader, "_clear_fcc_data"),
                patch.object(loader, "_load_county_lookup"),
                patch.object(loader, "_load_data_source"),
            ):
                loader._fips_to_county = {}
                loader._source_id = 1  # Set source_id directly
                stats = loader.load(mock_session, as_of_date="2025-03-31", verbose=False)

        # Should have processed the file from 2025-03-31
        assert stats.files_processed == 1


@pytest.mark.unit
class TestFCCBroadbandLoaderCountyLookup:
    """Tests for county FIPS lookup building."""

    def test_builds_fips_to_county_map(self) -> None:
        """Builds FIPS -> county_id mapping from database."""
        mock_session = MagicMock()

        # Mock county query results
        mock_county1 = MagicMock()
        mock_county1.fips = "06001"
        mock_county1.county_id = 1

        mock_county2 = MagicMock()
        mock_county2.fips = "06037"
        mock_county2.county_id = 2

        mock_session.query.return_value.all.return_value = [mock_county1, mock_county2]

        loader = FCCBroadbandLoader()
        loader._load_county_lookup(mock_session)

        assert loader._fips_to_county["06001"] == 1
        assert loader._fips_to_county["06037"] == 2


@pytest.mark.unit
class TestFCCBroadbandLoaderDataSource:
    """Tests for data source dimension loading."""

    def test_creates_new_data_source(self) -> None:
        """Creates new data source if not exists."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        loader = FCCBroadbandLoader()
        loader._load_data_source(mock_session, as_of_date="2025-06-30")

        # Should have added a new source
        mock_session.add.assert_called_once()
        added_source = mock_session.add.call_args[0][0]
        assert added_source.source_code == "FCC_BDC_20250630"
        assert added_source.source_year == 2025

    def test_reuses_existing_data_source(self) -> None:
        """Reuses existing data source if found."""
        mock_session = MagicMock()

        # Mock existing source
        mock_source = MagicMock()
        mock_source.source_id = 42
        mock_session.query.return_value.filter.return_value.first.return_value = mock_source

        loader = FCCBroadbandLoader()
        loader._load_data_source(mock_session, as_of_date="2025-06-30")

        # Should not have added anything
        mock_session.add.assert_not_called()
        assert loader._source_id == 42
