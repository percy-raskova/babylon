"""Integration tests for QCEW downloader CLI command.

Uses mocked HTTP responses to avoid hitting BLS servers in tests.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from babylon.data.cli import app

if TYPE_CHECKING:
    pass

runner = CliRunner()


def create_mock_qcew_zip() -> bytes:
    """Create a valid QCEW-style ZIP file with CSV content."""
    csv_content = (
        "area_fips,own_code,industry_code,agglvl_code,year,qtr,"
        "disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages\n"
        "26163,5,10,74,2020,A,N,1234,56789,1234567890\n"
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("2020.annual singlefile.csv", csv_content)

    return zip_buffer.getvalue()


class TestQcewDownloadCommand:
    """Integration tests for qcew-download CLI command."""

    def test_help_available(self) -> None:
        """Command help is available."""
        result = runner.invoke(app, ["qcew-download", "--help"])
        assert result.exit_code == 0
        assert "Download QCEW bulk data files from BLS" in result.stdout

    def test_default_years_in_help(self) -> None:
        """Help shows default year range."""
        result = runner.invoke(app, ["qcew-download", "--help"])
        assert "--years" in result.stdout

    @patch("babylon.data.qcew.downloader.QcewDownloader._download_file")
    def test_download_with_mocked_http(self, mock_download: MagicMock) -> None:
        """Download command creates files with mocked HTTP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Mock the download to create a valid ZIP file
            def side_effect(url: str, dest: Path) -> int:
                zip_content = create_mock_qcew_zip()
                dest.write_bytes(zip_content)
                return len(zip_content)

            mock_download.side_effect = side_effect

            result = runner.invoke(
                app,
                [
                    "qcew-download",
                    "--years",
                    "2020",
                    "--output-dir",
                    str(output_dir),
                ],
            )

            # Should succeed
            assert result.exit_code == 0, f"Failed with output: {result.stdout}"

            # Should show summary
            assert "DOWNLOAD SUMMARY" in result.stdout
            assert "Downloaded: 1" in result.stdout or "Skipped" in result.stdout

    @patch("babylon.data.qcew.downloader.QcewDownloader._download_file")
    def test_skip_existing_csv(self, mock_download: MagicMock) -> None:
        """Command skips download when CSV already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create existing CSV file
            csv_path = output_dir / "2020.annual singlefile.csv"
            csv_path.write_text("header\ndata")

            result = runner.invoke(
                app,
                [
                    "qcew-download",
                    "--years",
                    "2020",
                    "--output-dir",
                    str(output_dir),
                    "--skip-existing",
                ],
            )

            # Should succeed without calling download
            assert result.exit_code == 0
            assert "Skipped (existing): 1" in result.stdout
            mock_download.assert_not_called()

    @patch("babylon.data.qcew.downloader.QcewDownloader._download_file")
    def test_year_range_parsing(self, mock_download: MagicMock) -> None:
        """Command parses year range correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create CSVs for all years so we skip actual downloads
            for year in range(2020, 2023):
                csv_path = output_dir / f"{year}.annual singlefile.csv"
                csv_path.write_text("header\ndata")

            result = runner.invoke(
                app,
                [
                    "qcew-download",
                    "--years",
                    "2020-2022",
                    "--output-dir",
                    str(output_dir),
                ],
            )

            assert result.exit_code == 0
            # All 3 years should be skipped
            assert "Skipped (existing): 3" in result.stdout

    def test_quiet_mode(self) -> None:
        """Quiet mode suppresses most output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create existing CSV
            csv_path = output_dir / "2020.annual singlefile.csv"
            csv_path.write_text("header\ndata")

            result = runner.invoke(
                app,
                [
                    "qcew-download",
                    "--years",
                    "2020",
                    "--output-dir",
                    str(output_dir),
                    "--quiet",
                ],
            )

            assert result.exit_code == 0
            # Should have minimal output in quiet mode
            assert "DOWNLOAD SUMMARY" not in result.stdout


@pytest.mark.integration
class TestQcewDownloaderIntegration:
    """Integration tests for QcewDownloader class directly."""

    @patch("babylon.data.qcew.downloader.QcewDownloader._download_file")
    def test_download_all_with_mock(self, mock_download: MagicMock) -> None:
        """download_all processes multiple years."""
        from babylon.data.qcew.downloader import DownloadConfig, QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Mock download to create valid ZIPs
            def side_effect(url: str, dest: Path) -> int:
                zip_content = create_mock_qcew_zip()
                dest.write_bytes(zip_content)
                return len(zip_content)

            mock_download.side_effect = side_effect

            config = DownloadConfig(
                years=[2020, 2021],
                output_dir=output_dir,
                rate_limit_seconds=0,  # No delay in tests
            )

            downloader = QcewDownloader()
            report = downloader.download_all(config)

            assert len(report.years_downloaded) == 2
            assert report.has_failures is False
            assert report.success_rate == 1.0

    def test_verify_zip_with_valid_zip(self) -> None:
        """verify_zip returns True for valid ZIP."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.write_bytes(create_mock_qcew_zip())

            downloader = QcewDownloader()
            assert downloader.verify_zip(zip_path) is True

    def test_verify_zip_with_invalid_file(self) -> None:
        """verify_zip returns False for invalid file."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            not_a_zip = Path(tmpdir) / "not_a_zip.zip"
            not_a_zip.write_text("This is not a ZIP file")

            downloader = QcewDownloader()
            assert downloader.verify_zip(not_a_zip) is False

    def test_verify_csv_with_valid_csv(self) -> None:
        """verify_csv returns True for valid QCEW CSV."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"
            csv_path.write_text(
                "area_fips,own_code,industry_code,agglvl_code,year,qtr,"
                "disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages\n"
                "26163,5,10,74,2020,A,N,1234,56789,1234567890\n"
            )

            downloader = QcewDownloader()
            assert downloader.verify_csv(csv_path) is True

    def test_verify_csv_missing_columns(self) -> None:
        """verify_csv returns False when required columns missing."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"
            # Missing several required columns
            csv_path.write_text("area_fips,year\n26163,2020\n")

            downloader = QcewDownloader()
            assert downloader.verify_csv(csv_path) is False

    def test_extract_zip_creates_csv(self) -> None:
        """extract_zip creates CSV in output directory."""
        from babylon.data.qcew.downloader import QcewDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            zip_path = output_dir / "2020_annual_singlefile.zip"
            zip_path.write_bytes(create_mock_qcew_zip())

            downloader = QcewDownloader()
            csv_path = downloader.extract_zip(zip_path, output_dir)

            assert csv_path.exists()
            assert csv_path.name == "2020.annual singlefile.csv"
            assert "area_fips" in csv_path.read_text()
