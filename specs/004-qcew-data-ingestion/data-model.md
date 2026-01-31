# Data Model: QCEW Data Ingestion Pipeline

**Feature**: 004-qcew-data-ingestion
**Date**: 2026-01-30

## Overview

This feature adds minimal new models for download operations. The existing loader infrastructure handles all database models (`FactQcewAnnual`, `DimCounty`, etc.).

## Existing Models (No Changes)

The following models from `src/babylon/data/reference/schema.py` are used unchanged:

- **FactQcewAnnual**: County-level employment/wage facts
- **FactQcewStateAnnual**: State-level aggregates
- **FactQcewMetroAnnual**: Metro area aggregates
- **DimCounty**: County dimension
- **DimIndustry**: NAICS industry dimension
- **DimOwnership**: Ownership type dimension
- **DimTime**: Time dimension

## New Models (Download Operations)

### DownloadConfig

```python
from dataclasses import dataclass, field
from pathlib import Path


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
    output_dir: Path = field(default_factory=lambda: Path("data/qcew"))
    rate_limit_seconds: float = 1.0
    skip_existing: bool = True
    extract: bool = True
    cleanup_zips: bool = False
    base_url: str = "https://data.bls.gov/cew/data/files"

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
```

### DownloadResult

```python
from dataclasses import dataclass
from pathlib import Path


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
```

### DownloadReport

```python
from dataclasses import dataclass, field


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
```

## Validation Rules

1. **DownloadConfig.years**: Must be non-empty list of integers in range [1990, 2030]
1. **DownloadConfig.rate_limit_seconds**: Must be ≥ 0.5 (polite to BLS servers)
1. **DownloadConfig.output_dir**: Must be writable path
1. **DownloadResult.bytes_downloaded**: Non-negative integer

## Relationships

```
DownloadConfig
      │
      │ (configures)
      ▼
QcewDownloader ─────► DownloadResult (1 per year)
      │                      │
      │                      │ (aggregated into)
      │                      ▼
      └──────────────► DownloadReport
```

## Integration with Existing Models

The download models are **pure data acquisition** entities. They have no direct relationship to database models like `FactQcewAnnual`. The flow is:

1. **Download Phase**: `DownloadConfig` → `QcewDownloader` → CSV files on disk
1. **Load Phase**: CSV files → `QcewLoader` → `FactQcewAnnual` (existing)

This separation follows the Constitution's principle II.6: "State is Data, Engine is Transformation."
