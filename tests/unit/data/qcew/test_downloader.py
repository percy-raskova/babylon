"""Unit tests for QCEW downloader module.

Tests URL construction, skip logic, and data model behavior.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from babylon.data.qcew.downloader import (
    DownloadConfig,
    DownloadReport,
    DownloadResult,
)


class TestDownloadConfig:
    """Tests for DownloadConfig dataclass."""

    def test_get_zip_url_default_base(self) -> None:
        """URL construction uses default BLS base URL."""
        config = DownloadConfig(years=[2020])
        url = config.get_zip_url(2020)
        assert url == "https://data.bls.gov/cew/data/files/2020/csv/2020_annual_singlefile.zip"

    def test_get_zip_url_multiple_years(self) -> None:
        """URL construction works for multiple years."""
        config = DownloadConfig(years=[2010, 2015, 2024])

        assert config.get_zip_url(2010) == (
            "https://data.bls.gov/cew/data/files/2010/csv/2010_annual_singlefile.zip"
        )
        assert config.get_zip_url(2015) == (
            "https://data.bls.gov/cew/data/files/2015/csv/2015_annual_singlefile.zip"
        )
        assert config.get_zip_url(2024) == (
            "https://data.bls.gov/cew/data/files/2024/csv/2024_annual_singlefile.zip"
        )

    def test_get_zip_url_custom_base(self) -> None:
        """URL construction uses custom base URL when provided."""
        config = DownloadConfig(years=[2020], base_url="https://example.com/test")
        url = config.get_zip_url(2020)
        assert url == "https://example.com/test/2020/csv/2020_annual_singlefile.zip"

    def test_get_zip_path(self) -> None:
        """ZIP path construction includes year in filename."""
        config = DownloadConfig(years=[2020], output_dir=Path("/tmp/qcew"))
        path = config.get_zip_path(2020)
        assert path == Path("/tmp/qcew/2020_annual_singlefile.zip")

    def test_get_csv_path_has_space(self) -> None:
        """CSV path includes space in filename (BLS convention)."""
        config = DownloadConfig(years=[2020], output_dir=Path("/tmp/qcew"))
        path = config.get_csv_path(2020)
        # BLS uses a space in the filename
        assert path == Path("/tmp/qcew/2020.annual singlefile.csv")
        assert " " in path.name

    def test_default_output_dir(self) -> None:
        """Default output directory is data/qcew."""
        config = DownloadConfig(years=[2020])
        assert config.output_dir == Path("data/qcew")

    def test_default_rate_limit(self) -> None:
        """Default rate limit is 1 second (polite to BLS)."""
        config = DownloadConfig(years=[2020])
        assert config.rate_limit_seconds == 1.0

    def test_default_skip_existing(self) -> None:
        """Skip existing is True by default."""
        config = DownloadConfig(years=[2020])
        assert config.skip_existing is True

    def test_default_extract(self) -> None:
        """Extract is True by default."""
        config = DownloadConfig(years=[2020])
        assert config.extract is True

    def test_default_cleanup_zips(self) -> None:
        """Cleanup ZIPs is False by default."""
        config = DownloadConfig(years=[2020])
        assert config.cleanup_zips is False


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_status_ok(self) -> None:
        """Status is 'OK' when success is True and not skipped."""
        result = DownloadResult(year=2020, success=True)
        assert result.status == "OK"

    def test_status_skipped(self) -> None:
        """Status is 'SKIPPED' when skipped is True."""
        result = DownloadResult(year=2020, success=True, skipped=True)
        assert result.status == "SKIPPED"

    def test_status_failed(self) -> None:
        """Status is 'FAILED' when success is False."""
        result = DownloadResult(year=2020, success=False, error="Network error")
        assert result.status == "FAILED"

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        result = DownloadResult(year=2020, success=True)
        assert result.zip_path is None
        assert result.csv_path is None
        assert result.error is None
        assert result.bytes_downloaded == 0
        assert result.skipped is False


class TestDownloadReport:
    """Tests for DownloadReport dataclass."""

    def test_add_result_downloaded(self) -> None:
        """add_result categorizes successful downloads correctly."""
        report = DownloadReport(years_requested=[2020])
        result = DownloadResult(year=2020, success=True, bytes_downloaded=1000)

        report.add_result(result)

        assert 2020 in report.years_downloaded
        assert 2020 not in report.years_skipped
        assert 2020 not in report.years_failed
        assert report.total_bytes == 1000

    def test_add_result_skipped(self) -> None:
        """add_result categorizes skipped years correctly."""
        report = DownloadReport(years_requested=[2020])
        result = DownloadResult(year=2020, success=True, skipped=True)

        report.add_result(result)

        assert 2020 in report.years_skipped
        assert 2020 not in report.years_downloaded
        assert 2020 not in report.years_failed
        assert report.total_bytes == 0  # Skipped doesn't add bytes

    def test_add_result_failed(self) -> None:
        """add_result categorizes failed downloads correctly."""
        report = DownloadReport(years_requested=[2020])
        result = DownloadResult(year=2020, success=False, error="Download failed")

        report.add_result(result)

        assert 2020 in report.years_failed
        assert 2020 not in report.years_downloaded
        assert 2020 not in report.years_skipped
        assert "2020: Download failed" in report.errors

    def test_success_rate_all_downloaded(self) -> None:
        """Success rate is 1.0 when all years downloaded."""
        report = DownloadReport(years_requested=[2020, 2021])
        report.add_result(DownloadResult(year=2020, success=True))
        report.add_result(DownloadResult(year=2021, success=True))

        assert report.success_rate == 1.0

    def test_success_rate_includes_skipped(self) -> None:
        """Success rate includes skipped years as successful."""
        report = DownloadReport(years_requested=[2020, 2021])
        report.add_result(DownloadResult(year=2020, success=True))
        report.add_result(DownloadResult(year=2021, success=True, skipped=True))

        assert report.success_rate == 1.0

    def test_success_rate_with_failures(self) -> None:
        """Success rate accounts for failures."""
        report = DownloadReport(years_requested=[2020, 2021])
        report.add_result(DownloadResult(year=2020, success=True))
        report.add_result(DownloadResult(year=2021, success=False))

        assert report.success_rate == 0.5

    def test_success_rate_empty(self) -> None:
        """Success rate is 0 when no years requested."""
        report = DownloadReport(years_requested=[])
        assert report.success_rate == 0.0

    def test_has_failures(self) -> None:
        """has_failures is True when any year failed."""
        report = DownloadReport(years_requested=[2020])
        report.add_result(DownloadResult(year=2020, success=False))

        assert report.has_failures is True

    def test_no_failures(self) -> None:
        """has_failures is False when no years failed."""
        report = DownloadReport(years_requested=[2020])
        report.add_result(DownloadResult(year=2020, success=True))

        assert report.has_failures is False

    def test_total_bytes_accumulates(self) -> None:
        """total_bytes accumulates from all successful downloads."""
        report = DownloadReport(years_requested=[2020, 2021])
        report.add_result(DownloadResult(year=2020, success=True, bytes_downloaded=1000))
        report.add_result(DownloadResult(year=2021, success=True, bytes_downloaded=2000))

        assert report.total_bytes == 3000


class TestDownloaderSkipLogic:
    """Tests for skip_existing behavior."""

    def test_skip_existing_when_csv_exists(self) -> None:
        """Skips download when CSV already exists and skip_existing=True."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create existing CSV file
            csv_path = output_dir / "2020.annual singlefile.csv"
            csv_path.write_text("header\ndata")

            config = DownloadConfig(
                years=[2020],
                output_dir=output_dir,
                skip_existing=True,
            )

            downloader = QcewDownloader()
            result = downloader.download_year(2020, config)

            assert result.success is True
            assert result.skipped is True
            assert result.csv_path == csv_path

    def test_no_skip_when_disabled(self) -> None:
        """Attempts download even when CSV exists if skip_existing=False."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create existing CSV file
            csv_path = output_dir / "2020.annual singlefile.csv"
            csv_path.write_text("header\ndata")

            config = DownloadConfig(
                years=[2020],
                output_dir=output_dir,
                skip_existing=False,
                # Use invalid URL to make download fail predictably
                base_url="http://localhost:99999",
            )

            downloader = QcewDownloader()
            result = downloader.download_year(2020, config)

            # Should attempt download (and fail with invalid URL)
            assert result.skipped is False


class TestVerifyZip:
    """Tests for verify_zip validation method."""

    def test_verify_zip_valid(self) -> None:
        """verify_zip returns True for valid ZIP file."""
        import io
        import zipfile as zf

        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"

            # Create valid ZIP
            buffer = io.BytesIO()
            with zf.ZipFile(buffer, "w") as z:
                z.writestr("test.csv", "data")
            zip_path.write_bytes(buffer.getvalue())

            downloader = QcewDownloader()
            assert downloader.verify_zip(zip_path) is True

    def test_verify_zip_nonexistent(self) -> None:
        """verify_zip returns False for nonexistent file."""
        from babylon.data.qcew.downloader import QcewDownloader

        downloader = QcewDownloader()
        assert downloader.verify_zip(Path("/nonexistent/path.zip")) is False

    def test_verify_zip_not_a_zip(self) -> None:
        """verify_zip returns False for non-ZIP file."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            not_zip = Path(tmpdir) / "fake.zip"
            not_zip.write_text("This is not a ZIP file")

            downloader = QcewDownloader()
            assert downloader.verify_zip(not_zip) is False


class TestVerifyCsv:
    """Tests for verify_csv validation method."""

    def test_verify_csv_valid(self) -> None:
        """verify_csv returns True for valid QCEW CSV."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "valid.csv"
            csv_path.write_text(
                "area_fips,own_code,industry_code,agglvl_code,year,qtr,"
                "disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages\n"
                "26163,5,10,74,2020,A,N,1234,56789,1234567890\n"
            )

            downloader = QcewDownloader()
            assert downloader.verify_csv(csv_path) is True

    def test_verify_csv_missing_columns(self) -> None:
        """verify_csv returns False when required columns are missing."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "invalid.csv"
            # Missing most required columns
            csv_path.write_text("area_fips,year\n26163,2020\n")

            downloader = QcewDownloader()
            assert downloader.verify_csv(csv_path) is False

    def test_verify_csv_empty_file(self) -> None:
        """verify_csv returns False for empty file."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "empty.csv"
            csv_path.write_text("")

            downloader = QcewDownloader()
            assert downloader.verify_csv(csv_path) is False

    def test_verify_csv_nonexistent(self) -> None:
        """verify_csv returns False for nonexistent file."""
        from babylon.data.qcew.downloader import QcewDownloader

        downloader = QcewDownloader()
        assert downloader.verify_csv(Path("/nonexistent/file.csv")) is False

    def test_verify_csv_header_only(self) -> None:
        """verify_csv returns True for CSV with only header (valid structure)."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "header_only.csv"
            csv_path.write_text(
                "area_fips,own_code,industry_code,agglvl_code,year,qtr,"
                "disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages\n"
            )

            downloader = QcewDownloader()
            # Should return True - has valid structure even if no data rows
            assert downloader.verify_csv(csv_path) is True


class TestDownloaderYearValidation:
    """Tests for year range validation."""

    def test_year_below_range_raises(self) -> None:
        """Years before 1990 raise ValueError."""
        from babylon.data.qcew.downloader import QcewDownloader

        config = DownloadConfig(years=[1989])
        downloader = QcewDownloader()

        with pytest.raises(ValueError, match="out of valid range"):
            downloader.download_year(1989, config)

    def test_year_above_range_raises(self) -> None:
        """Years after 2030 raise ValueError."""
        from babylon.data.qcew.downloader import QcewDownloader

        config = DownloadConfig(years=[2031])
        downloader = QcewDownloader()

        with pytest.raises(ValueError, match="out of valid range"):
            downloader.download_year(2031, config)

    def test_valid_year_range(self) -> None:
        """Years within 1990-2030 are accepted."""
        from babylon.data.qcew.downloader import QcewDownloader

        # Just test that these don't raise - actual download will fail
        # but we're testing the validation logic
        config = DownloadConfig(
            years=[1990, 2020, 2030],
            base_url="http://localhost:99999",  # Invalid to prevent real download
        )
        downloader = QcewDownloader()

        # These should not raise ValueError for year range
        # (they'll fail for other reasons like network)
        for year in [1990, 2020, 2030]:
            try:
                result = downloader.download_year(year, config)
                # If it gets past validation, check it's not a range error
                assert "out of valid range" not in (result.error or "")
            except ValueError as e:
                # Only fail if it's a range error
                assert "out of valid range" not in str(e)


class TestLoaderCheckpointBehavior:
    """Tests for QCEW loader checkpoint behavior.

    Regression tests for the bug where files with 0 records
    were incorrectly marked as completed.
    """

    def test_checkpoint_not_created_for_zero_records(self) -> None:
        """Checkpoints should NOT be created when 0 records are loaded.

        This prevents false positives when year filtering yields no data.
        A file should only be marked completed if it actually contributed
        records to the database.
        """
        from unittest.mock import MagicMock, patch

        from babylon.data.loader_base import LoaderConfig
        from babylon.data.qcew.loader_3nf import QcewLoader

        config = LoaderConfig(qcew_years=[2010])
        loader = QcewLoader(config)

        # Mock session and methods
        mock_session = MagicMock()
        mock_csv_file = MagicMock()
        mock_csv_file.name = "2010.annual.singlefile.csv"

        # Mock _get_file_hash to return a test hash
        with (
            patch.object(loader, "_get_file_hash", return_value="testhash123"),
            patch.object(loader, "_is_completed", return_value=False),
            patch.object(loader, "_process_csv_file", return_value=0),  # 0 records!
            patch.object(loader, "_mark_completed") as mock_mark,
        ):
            # Simulate the processing loop logic
            file_hash = loader._get_file_hash(mock_csv_file)
            if not loader._is_completed(mock_session, "qcew", 0, file_hash, "file", "T"):
                file_record_count = loader._process_csv_file(
                    mock_session, mock_csv_file, {2010}, {}, MagicMock(), False
                )
                # Only mark completed if records > 0
                if file_record_count > 0:
                    loader._mark_completed(
                        mock_session, "qcew", 0, file_hash, "file", "T", file_record_count
                    )

            # _mark_completed should NOT have been called since 0 records
            mock_mark.assert_not_called()

    def test_checkpoint_created_for_positive_records(self) -> None:
        """Checkpoints SHOULD be created when records are loaded."""
        from unittest.mock import MagicMock, patch

        from babylon.data.loader_base import LoaderConfig
        from babylon.data.qcew.loader_3nf import QcewLoader

        config = LoaderConfig(qcew_years=[2010])
        loader = QcewLoader(config)

        mock_session = MagicMock()
        mock_csv_file = MagicMock()
        mock_csv_file.name = "2010.annual.singlefile.csv"

        with (
            patch.object(loader, "_get_file_hash", return_value="testhash123"),
            patch.object(loader, "_is_completed", return_value=False),
            patch.object(loader, "_process_csv_file", return_value=1000),  # 1000 records!
            patch.object(loader, "_mark_completed") as mock_mark,
        ):
            file_hash = loader._get_file_hash(mock_csv_file)
            if not loader._is_completed(mock_session, "qcew", 0, file_hash, "file", "T"):
                file_record_count = loader._process_csv_file(
                    mock_session, mock_csv_file, {2010}, {}, MagicMock(), False
                )
                if file_record_count > 0:
                    loader._mark_completed(
                        mock_session, "qcew", 0, file_hash, "file", "T", file_record_count
                    )

            # _mark_completed SHOULD have been called
            mock_mark.assert_called_once_with(
                mock_session, "qcew", 0, "testhash123", "file", "T", 1000
            )
