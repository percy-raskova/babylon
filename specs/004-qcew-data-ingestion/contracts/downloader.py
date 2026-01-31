"""Protocol definitions for QCEW Data Downloader.

Feature: 004-qcew-data-ingestion
Date: 2026-01-30

This module defines the interface contracts for QCEW bulk file downloads.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.data.qcew.downloader import (
        DownloadConfig,
        DownloadReport,
        DownloadResult,
    )


class QcewDownloaderProtocol(Protocol):
    """Protocol for QCEW bulk file downloads.

    Implementations download annual QCEW data from BLS bulk files
    and extract them for use by QcewLoader.
    """

    def download_year(self, year: int, config: DownloadConfig) -> DownloadResult:
        """Download and optionally extract a single year's data.

        Args:
            year: The year to download (e.g., 2015).
            config: Download configuration.

        Returns:
            DownloadResult with success status, paths, and any errors.

        Raises:
            ValueError: If year is out of valid range.
        """
        ...

    def download_all(self, config: DownloadConfig) -> DownloadReport:
        """Download all years specified in config.

        Args:
            config: Download configuration including year list.

        Returns:
            DownloadReport summarizing all download operations.

        Note:
            Implements rate limiting between requests (config.rate_limit_seconds).
            Skips existing files if config.skip_existing is True.
        """
        ...

    def verify_zip(self, path: Path) -> bool:
        """Verify a ZIP file is valid and not corrupted.

        Args:
            path: Path to the ZIP file.

        Returns:
            True if ZIP is valid, False otherwise.
        """
        ...

    def verify_csv(self, path: Path) -> bool:
        """Verify an extracted CSV file has valid QCEW structure.

        Args:
            path: Path to the CSV file.

        Returns:
            True if CSV has expected columns, False otherwise.
        """
        ...

    def extract_zip(self, zip_path: Path, output_dir: Path) -> Path:
        """Extract a QCEW ZIP file to the output directory.

        Args:
            zip_path: Path to the ZIP file.
            output_dir: Directory for extracted CSV.

        Returns:
            Path to the extracted CSV file.

        Raises:
            zipfile.BadZipFile: If ZIP is corrupted.
            FileNotFoundError: If ZIP doesn't exist.
        """
        ...


class DownloadProgressCallback(Protocol):
    """Protocol for download progress callbacks."""

    def on_year_start(self, year: int, total_years: int) -> None:
        """Called when starting download for a year."""
        ...

    def on_year_complete(self, result: DownloadResult) -> None:
        """Called when a year's download completes."""
        ...

    def on_download_progress(self, bytes_downloaded: int, total_bytes: int | None) -> None:
        """Called during download with progress info."""
        ...
