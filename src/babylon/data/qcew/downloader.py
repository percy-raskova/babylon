"""QCEW bulk file downloader for BLS annual data.

This module downloads QCEW annual singlefile ZIPs from BLS bulk data files
and extracts them for use by QcewLoader.

Usage:
    from babylon.data.qcew.downloader import QcewDownloader, DownloadConfig

    config = DownloadConfig(years=list(range(2010, 2025)))
    downloader = QcewDownloader()
    report = downloader.download_all(config)

    print(f"Downloaded: {report.years_downloaded}")
    print(f"Skipped: {report.years_skipped}")
    print(f"Failed: {report.years_failed}")
"""

from __future__ import annotations

import csv
import logging
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import httpx
from tqdm import tqdm

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# BLS QCEW bulk file constants
DEFAULT_BASE_URL = "https://data.bls.gov/cew/data/files"
DEFAULT_OUTPUT_DIR = Path("data/qcew")
DEFAULT_RATE_LIMIT = 1.0  # Seconds between requests (polite to BLS)

# Expected QCEW CSV columns for validation
REQUIRED_COLUMNS = frozenset(
    {
        "area_fips",
        "own_code",
        "industry_code",
        "agglvl_code",
        "year",
        "qtr",
        "disclosure_code",
        "annual_avg_estabs",
        "annual_avg_emplvl",
        "total_annual_wages",
    }
)


@dataclass
class DownloadConfig:
    """Configuration for QCEW bulk downloads.

    Attributes:
        years: List of years to download (e.g., [2010, 2011, ..., 2024]).
        output_dir: Directory for downloaded/extracted files.
        rate_limit_seconds: Minimum delay between HTTP requests.
        skip_existing: If True, skip years with existing CSV files.
        extract: If True, extract ZIPs after download.
        cleanup_zips: If True, delete ZIPs after successful extraction.
        base_url: BLS data files base URL (for testing/override).
    """

    years: list[int]
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    rate_limit_seconds: float = DEFAULT_RATE_LIMIT
    skip_existing: bool = True
    extract: bool = True
    cleanup_zips: bool = False
    base_url: str = DEFAULT_BASE_URL

    def get_zip_url(self, year: int) -> str:
        """Construct URL for a year's ZIP file."""
        return f"{self.base_url}/{year}/csv/{year}_annual_singlefile.zip"

    def get_zip_path(self, year: int) -> Path:
        """Get local path for a year's ZIP file."""
        return self.output_dir / f"{year}_annual_singlefile.zip"

    def get_csv_path(self, year: int) -> Path:
        """Get local path for extracted CSV file.

        Note: BLS uses a space in the filename.
        """
        return self.output_dir / f"{year}.annual singlefile.csv"


@dataclass
class DownloadResult:
    """Result of a single year download operation.

    Attributes:
        year: The year that was downloaded.
        success: True if download and extraction succeeded.
        zip_path: Path to the ZIP file (if kept).
        csv_path: Path to the extracted CSV file.
        error: Error message if failed.
        bytes_downloaded: Size of downloaded ZIP in bytes.
        skipped: True if year was skipped (file already exists).
    """

    year: int
    success: bool
    zip_path: Path | None = None
    csv_path: Path | None = None
    error: str | None = None
    bytes_downloaded: int = 0
    skipped: bool = False

    @property
    def status(self) -> str:
        """Human-readable status string."""
        if self.skipped:
            return "SKIPPED"
        elif self.success:
            return "OK"
        else:
            return "FAILED"


@dataclass
class DownloadReport:
    """Summary of a batch download run.

    Attributes:
        years_requested: All years that were requested.
        years_downloaded: Years successfully downloaded.
        years_skipped: Years skipped (already existed).
        years_failed: Years that failed to download.
        results: Individual results for each year.
        errors: All error messages collected.
        total_bytes: Total bytes downloaded.
    """

    years_requested: list[int] = field(default_factory=list)
    years_downloaded: list[int] = field(default_factory=list)
    years_skipped: list[int] = field(default_factory=list)
    years_failed: list[int] = field(default_factory=list)
    results: list[DownloadResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_bytes: int = 0

    @property
    def success_rate(self) -> float:
        """Percentage of requested years successfully handled."""
        if not self.years_requested:
            return 0.0
        handled = len(self.years_downloaded) + len(self.years_skipped)
        return handled / len(self.years_requested)

    @property
    def has_failures(self) -> bool:
        """True if any years failed."""
        return len(self.years_failed) > 0

    def add_result(self, result: DownloadResult) -> None:
        """Add a result and update summary lists."""
        self.results.append(result)
        if result.skipped:
            self.years_skipped.append(result.year)
        elif result.success:
            self.years_downloaded.append(result.year)
            self.total_bytes += result.bytes_downloaded
        else:
            self.years_failed.append(result.year)
            if result.error:
                self.errors.append(f"{result.year}: {result.error}")


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


class QcewDownloader:
    """Downloads QCEW bulk files from BLS.

    Implements the QcewDownloaderProtocol defined in the contracts.
    """

    def __init__(
        self,
        client: httpx.Client | None = None,
        progress_callback: DownloadProgressCallback | None = None,
    ) -> None:
        """Initialize downloader.

        Args:
            client: Optional httpx.Client for testing/customization.
            progress_callback: Optional callback for progress reporting.
        """
        self._client = client
        self._owns_client = client is None
        self._progress_callback = progress_callback

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> QcewDownloader:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

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
        if year < 1990 or year > 2030:
            raise ValueError(f"Year {year} out of valid range [1990, 2030]")

        csv_path = config.get_csv_path(year)
        zip_path = config.get_zip_path(year)

        # Check if already exists and skip_existing is True
        if config.skip_existing and csv_path.exists():
            logger.info("Year %d already exists, skipping: %s", year, csv_path)
            return DownloadResult(
                year=year,
                success=True,
                csv_path=csv_path,
                skipped=True,
            )

        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)

        # Check available disk space (rough estimate: 400MB per year uncompressed)
        try:
            free_space = shutil.disk_usage(config.output_dir).free
            if free_space < 500_000_000:  # 500MB minimum
                return DownloadResult(
                    year=year,
                    success=False,
                    error=f"Insufficient disk space: {free_space / 1e9:.1f} GB available",
                )
        except OSError as e:
            logger.warning("Could not check disk space: %s", e)

        # Download ZIP
        url = config.get_zip_url(year)
        logger.info("Downloading %d from %s", year, url)

        try:
            bytes_downloaded = self._download_file(url, zip_path)
        except Exception as e:
            return DownloadResult(
                year=year,
                success=False,
                error=f"Download failed: {e}",
            )

        # Verify ZIP integrity
        if not self.verify_zip(zip_path):
            zip_path.unlink(missing_ok=True)
            return DownloadResult(
                year=year,
                success=False,
                error="Downloaded ZIP file is corrupted",
                bytes_downloaded=bytes_downloaded,
            )

        # Extract if requested
        extracted_csv: Path | None = None
        if config.extract:
            try:
                extracted_csv = self.extract_zip(zip_path, config.output_dir)
            except Exception as e:
                return DownloadResult(
                    year=year,
                    success=False,
                    zip_path=zip_path,
                    error=f"Extraction failed: {e}",
                    bytes_downloaded=bytes_downloaded,
                )

            # Verify CSV after extraction
            if extracted_csv and not self.verify_csv(extracted_csv):
                return DownloadResult(
                    year=year,
                    success=False,
                    zip_path=zip_path,
                    csv_path=extracted_csv,
                    error="Extracted CSV failed validation (missing required columns)",
                    bytes_downloaded=bytes_downloaded,
                )

            # Cleanup ZIP if requested
            if config.cleanup_zips:
                zip_path.unlink(missing_ok=True)
                zip_path = None  # type: ignore[assignment]

        return DownloadResult(
            year=year,
            success=True,
            zip_path=zip_path if not config.cleanup_zips else None,
            csv_path=extracted_csv,
            bytes_downloaded=bytes_downloaded,
        )

    def _download_file(self, url: str, dest: Path) -> int:
        """Download a file with streaming and progress.

        Returns:
            Number of bytes downloaded.
        """
        client = self._get_client()
        bytes_downloaded = 0

        with client.stream("GET", url) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0)) or None

            with (
                open(dest, "wb") as f,
                tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc=dest.name,
                    disable=self._progress_callback is None
                    and not logger.isEnabledFor(logging.INFO),
                ) as pbar,
            ):
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    pbar.update(len(chunk))
                    if self._progress_callback:
                        self._progress_callback.on_download_progress(bytes_downloaded, total)

        return bytes_downloaded

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
        report = DownloadReport(years_requested=list(config.years))
        total_years = len(config.years)

        for i, year in enumerate(config.years):
            if self._progress_callback:
                self._progress_callback.on_year_start(year, total_years)

            logger.info("Processing year %d (%d/%d)", year, i + 1, total_years)

            result = self.download_year(year, config)
            report.add_result(result)

            if self._progress_callback:
                self._progress_callback.on_year_complete(result)

            logger.info(
                "Year %d: %s%s",
                year,
                result.status,
                f" - {result.error}" if result.error else "",
            )

            # Rate limiting (skip for last item and skipped items)
            if i < total_years - 1 and not result.skipped:
                time.sleep(config.rate_limit_seconds)

        return report

    def verify_zip(self, path: Path) -> bool:
        """Verify a ZIP file is valid and not corrupted.

        Args:
            path: Path to the ZIP file.

        Returns:
            True if ZIP is valid, False otherwise.
        """
        if not path.exists():
            return False

        if not zipfile.is_zipfile(path):
            return False

        try:
            with zipfile.ZipFile(path, "r") as zf:
                # Test ZIP integrity
                bad_file = zf.testzip()
                return bad_file is None
        except zipfile.BadZipFile:
            return False
        except Exception as e:
            logger.warning("ZIP verification failed for %s: %s", path, e)
            return False

    def verify_csv(self, path: Path) -> bool:
        """Verify an extracted CSV file has valid QCEW structure.

        Args:
            path: Path to the CSV file.

        Returns:
            True if CSV has expected columns, False otherwise.
        """
        if not path.exists():
            return False

        if path.stat().st_size == 0:
            return False

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None:
                    return False

                # Check that required columns are present
                header_set = {col.strip().lower() for col in header}
                missing = REQUIRED_COLUMNS - header_set
                if missing:
                    logger.warning("CSV %s missing columns: %s", path, missing)
                    return False

                return True
        except Exception as e:
            logger.warning("CSV verification failed for %s: %s", path, e)
            return False

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
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            # QCEW ZIPs contain a single CSV file
            names = zf.namelist()
            if not names:
                raise ValueError(f"ZIP file is empty: {zip_path}")

            # Find the CSV file (should be the only file)
            csv_name = None
            for name in names:
                if name.endswith(".csv"):
                    csv_name = name
                    break

            if csv_name is None:
                raise ValueError(f"No CSV file found in ZIP: {zip_path}")

            # Extract to output directory
            zf.extract(csv_name, output_dir)
            extracted_path = output_dir / csv_name

            logger.info("Extracted %s to %s", csv_name, extracted_path)
            return extracted_path
