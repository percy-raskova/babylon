# Research: QCEW Data Ingestion Pipeline

**Feature**: 004-qcew-data-ingestion
**Date**: 2026-01-30
**Phase**: 0 (Pre-Design Research)

## Executive Summary

This feature adds a download component to complement the existing QCEW loader infrastructure. The `QcewLoader` already handles file-based ingestion—this feature provides reproducible data acquisition from BLS bulk files.

**Key Discovery**: Most of the required functionality already exists. The scope is narrower than originally anticipated.

## Existing Code Analysis

### QcewLoader (`src/babylon/data/qcew/loader_3nf.py`)

**Current State**: 983 lines, production-ready

**Key Methods**:

```python
def load(self, session, reset=True, verbose=True, **kwargs) -> LoadStats:
    """Hybrid loading: API for 2021+, files for historical."""

def _load_from_files(self, session, years, verbose, data_path) -> LoadStats:
    """Load from local CSV files in data/qcew/ directory."""
```

**What It Already Does**:

- ✅ File-based loading from `data/qcew/*.csv`
- ✅ Resume/checkpoint support via `_is_completed()` / `_mark_completed()`
- ✅ Batch processing with `BATCH_FLUSH_SIZE = 10000`
- ✅ FIPS filtering (county-level only)
- ✅ Progress reporting via tqdm
- ✅ Error handling and logging

**What It Expects**:

- CSV files in `DEFAULT_QCEW_PATH = Path("data/qcew")`
- File naming pattern: `*.csv` (uses glob)
- CSV format: BLS QCEW annual layout

### QcewAPIClient (`src/babylon/data/qcew/api_client.py`)

**Rate Limiting**: 0.5 second delay between requests (polite)
**Retries**: 3 retries with exponential backoff

### CLI (`src/babylon/data/cli.py`)

**Existing Command**: `mise run data:qcew`

```python
@app.command()
def qcew(
    years: str | None = None,          # e.g., "2020-2024" or "2020,2021,2022"
    force_api: bool = False,           # Force API for all years
    force_files: bool = False,         # Force files for all years
    quiet: bool = False
) -> None:
    """Load BLS QCEW employment data into 3NF database."""
```

**Default Years**: 2013-2025 (hybrid loading)

## BLS Bulk File Analysis

### URL Pattern

```
https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip
```

**Examples**:

- 2010: `https://data.bls.gov/cew/data/files/2010/csv/2010_annual_singlefile.zip`
- 2024: `https://data.bls.gov/cew/data/files/2024/csv/2024_annual_singlefile.zip`

### File Structure

**ZIP Contents**: Single CSV file with naming pattern `{year}.annual singlefile.csv`

**Important**: Filename contains a space, which may require careful handling.

### File Sizes (Approximate)

| Year | ZIP Size | CSV Size |
| ---- | -------- | -------- |
| 2010 | ~45 MB   | ~280 MB  |
| 2015 | ~50 MB   | ~300 MB  |
| 2020 | ~55 MB   | ~320 MB  |
| 2024 | ~60 MB   | ~350 MB  |

**Total for 2010-2024**: ~750 MB compressed, ~4.5 GB uncompressed

### CSV Column Layout

Matches `QcewRecord` in `parser.py`:

- `area_fips`: 5-digit county FIPS
- `own_code`: Ownership (1-5)
- `industry_code`: NAICS code
- `agglvl_code`: Aggregation level (70-78 for county)
- `year`: Data year
- `annual_avg_emplvl`: Employment count
- `total_annual_wages`: Total wages ($)
- `avg_annual_pay`: Average pay ($)
- `disclosure_code`: Data suppression flag

## Gap Analysis

| Requirement           | Status     | Location                        |
| --------------------- | ---------- | ------------------------------- |
| Download ZIP from URL | ❌ MISSING | Need `downloader.py`            |
| Extract ZIP to CSV    | ❌ MISSING | Need `downloader.py`            |
| Load CSV into SQLite  | ✅ EXISTS  | `loader_3nf.py`                 |
| Filter by FIPS        | ✅ EXISTS  | `loader_3nf.py`                 |
| Progress reporting    | ✅ EXISTS  | `loader_3nf.py`                 |
| Resume support        | ✅ EXISTS  | `loader_3nf.py`                 |
| CLI command           | ⚠️ PARTIAL | Need `qcew-download` subcommand |
| mise task             | ⚠️ PARTIAL | Need `data:qcew-download`       |

## Implementation Recommendation

### Minimal Scope

Given the existing infrastructure, the implementation scope is:

1. **New Module**: `src/babylon/data/qcew/downloader.py` (~150 lines)

   - `QcewDownloader` class
   - `download_year()` method
   - `download_all()` method
   - ZIP extraction logic

1. **CLI Addition**: Add `qcew-download` command to existing CLI

   - ~50 lines in `cli.py`

1. **mise Task**: Add `data:qcew-download` to `.mise.toml`

   - 2 lines

### Architecture Decision

**Option A**: Standalone download script (shell)

- Pros: Simple, language-agnostic
- Cons: Separate from Python ecosystem, harder to test

**Option B**: Python module with CLI (RECOMMENDED)

- Pros: Testable, integrates with existing infrastructure, reusable
- Cons: Slightly more complex

**Decision**: Option B - aligns with existing project patterns.

## Dependencies

### Already Available

- **httpx**: HTTP client (used by `api_client.py`)
- **tqdm**: Progress bars (used by `loader_3nf.py`)
- **zipfile**: ZIP extraction (Python stdlib)

### No New Dependencies Required

## Risks and Mitigations

| Risk                  | Probability | Impact | Mitigation                     |
| --------------------- | ----------- | ------ | ------------------------------ |
| BLS URL changes       | Low         | High   | Log errors, allow URL override |
| Large downloads fail  | Medium      | Medium | Resume support, retry logic    |
| Disk space exhaustion | Low         | High   | Check space before download    |
| Network throttling    | Low         | Low    | Rate limiting (1s delay)       |

## References

- BLS QCEW Downloads: https://www.bls.gov/cew/downloadable-data-files.htm
- Existing Loader: `src/babylon/data/qcew/loader_3nf.py`
- Existing CLI: `src/babylon/data/cli.py`
