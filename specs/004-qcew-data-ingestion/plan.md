# Implementation Plan: QCEW Data Ingestion Pipeline

**Branch**: `004-qcew-data-ingestion` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-qcew-data-ingestion/spec.md`

## Summary

Add a download script and CLI command to fetch QCEW bulk data files from BLS, complementing the existing `QcewLoader` infrastructure. The loader already supports file-based ingestion—this feature provides the missing download component for reproducible data acquisition.

**Key Finding**: The existing `QcewLoader` in `src/babylon/data/qcew/loader_3nf.py` already implements:

- Hybrid loading (API for 2021+, files for historical years)
- File-based loading from `data/qcew/*.csv`
- Resume/checkpoint support
- Rate limiting and batch processing

**What's Missing**: A download script to fetch bulk ZIP files from `https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip`.

## Technical Context

**Language/Version**: Python 3.11+ (existing project standard)
**Primary Dependencies**: httpx (already in project), tqdm (already in project), zipfile (stdlib)
**Storage**: SQLite (`data/sqlite/marxist-data-3NF.sqlite` via existing loader)
**Testing**: pytest with `@pytest.mark.integration` marker
**Target Platform**: Linux (development), cross-platform (Poetry)
**Project Type**: Single (extends existing `src/babylon/data/qcew/` module)
**Performance Goals**: \<5 minutes per year (SC-003), \<15 minutes total for Detroit metro (SC-005)
**Constraints**: Polite rate limiting (≥1 second between requests), disk space for ZIP extraction (~300MB per year uncompressed)
**Scale/Scope**: 15 years × ~4M rows/year = ~60M rows nationwide; ~500K rows Detroit metro

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle                                        | Status  | Notes                                                                           |
| ------------------------------------------------ | ------- | ------------------------------------------------------------------------------- |
| **III.4 Data Source Traceability**               | ✅ PASS | BLS QCEW is listed in Constitution data sources table                           |
| **II.6 State is Data, Engine is Transformation** | ✅ PASS | Data ingestion populates `fact_qcew_annual`, separate from transformation logic |
| **III.1 No Magic Constants**                     | ✅ PASS | URL pattern is BLS's published structure, year range is configurable            |
| **V.2 Zoom Where Data Exists**                   | ✅ PASS | Detroit metro filter aligns with Constitution's Metro Detroit test case         |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/004-qcew-data-ingestion/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output - existing infrastructure analysis
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - usage examples
├── contracts/           # Phase 1 output - interface contracts
│   └── downloader.py    # Download protocol
├── checklists/
│   └── requirements.md  # Specification quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/data/qcew/
├── __init__.py          # EXISTING - exports
├── api_client.py        # EXISTING - BLS API client
├── parser.py            # EXISTING - CSV parsing
├── schema.py            # EXISTING - Pydantic models
├── loader_3nf.py        # EXISTING - hybrid loader (already works!)
└── downloader.py        # NEW - bulk ZIP downloader

scripts/
└── download_qcew.sh     # NEW - shell wrapper for CLI

tests/
├── integration/data/qcew/
│   ├── test_loader_3nf.py      # EXISTING
│   └── test_downloader.py      # NEW - download integration tests
└── unit/data/qcew/
    └── test_downloader.py      # NEW - download unit tests
```

**Structure Decision**: Minimal addition to existing `qcew/` module. Only adding `downloader.py` and a shell script wrapper.

## Complexity Tracking

> No Constitution Check violations requiring justification.

| Item                    | Status                                     |
| ----------------------- | ------------------------------------------ |
| Constitution violations | None                                       |
| Complexity additions    | Minimal - single new module + shell script |

______________________________________________________________________

## Phase 0: Research

### Existing Infrastructure Analysis

**QcewLoader** (`src/babylon/data/qcew/loader_3nf.py`):

- 983 lines, production-ready
- `load()` method with hybrid approach: API for 2021+, files for 2013-2020
- `_load_from_files()` expects CSVs in `data/qcew/` directory
- Checkpointing via `_is_completed()` / `_mark_completed()` enables resume
- Uses `parse_qcew_csv()` from `parser.py` for file reading

**QcewAPIClient** (`src/babylon/data/qcew/api_client.py`):

- Uses httpx with rate limiting (0.5s delay)
- `BASE_URL = "https://data.bls.gov/cew/data/api"`
- Already has retry logic with exponential backoff

**CLI** (`src/babylon/data/cli.py`):

- `qcew` command already exists with `--years`, `--force-files`, `--force-api` options
- Default years: 2013-2025
- Prerequisite check: requires Census dimensions first

**Current Gap**: No download functionality. The loader assumes CSVs already exist.

### BLS Bulk File Structure

**URL Pattern**: `https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip`

**ZIP Contents**: Single CSV file `{year}.annual singlefile.csv` (note: space in filename)

**File Size**: ~50-80 MB compressed, ~300 MB uncompressed per year

**Column Layout**: Matches `QcewRecord` in `parser.py` (area_fips, own_code, industry_code, year, etc.)

### Dependencies

- **httpx**: Already used by `api_client.py` - no new dependency
- **tqdm**: Already used by `loader_3nf.py` - no new dependency
- **zipfile**: Python stdlib - no new dependency

### Risks

1. **BLS URL structure changes**: Low risk, pattern stable since 2015. Mitigation: Log errors, allow manual URL override.
1. **Large file sizes**: ~4.5GB total for 2010-2024. Mitigation: Stream downloads, cleanup option.
1. **Network interruptions**: Mitigation: Resume support (skip existing ZIPs).

______________________________________________________________________

## Phase 1: Design

### Data Model

Minimal additions - reuses existing models.

**DownloadConfig** (new):

```python
@dataclass
class DownloadConfig:
    """Configuration for QCEW bulk downloads."""

    years: list[int]
    output_dir: Path = Path("data/qcew")
    rate_limit_seconds: float = 1.0
    skip_existing: bool = True
    extract: bool = True
    cleanup_zips: bool = False
```

**DownloadResult** (new):

```python
@dataclass
class DownloadResult:
    """Result of a download operation."""

    year: int
    success: bool
    zip_path: Path | None = None
    csv_path: Path | None = None
    error: str | None = None
    bytes_downloaded: int = 0
```

**DownloadReport** (new):

```python
@dataclass
class DownloadReport:
    """Summary of download run."""

    years_requested: list[int]
    years_downloaded: list[int]
    years_skipped: list[int]
    years_failed: list[int]
    errors: list[str]
    total_bytes: int
```

### Interface Contracts

See [contracts/downloader.py](./contracts/downloader.py).

```python
class QcewDownloader(Protocol):
    """Protocol for QCEW bulk file downloads."""

    def download_year(self, year: int) -> DownloadResult:
        """Download and extract a single year's data."""
        ...

    def download_all(self, config: DownloadConfig) -> DownloadReport:
        """Download all configured years."""
        ...

    def verify_file(self, path: Path) -> bool:
        """Verify a downloaded/extracted file is valid."""
        ...
```

### Quickstart

See [quickstart.md](./quickstart.md).

______________________________________________________________________

## Implementation Phases

### Phase A: Downloader Module (FR-001, FR-002, FR-006, FR-008)

- Create `src/babylon/data/qcew/downloader.py`
- Implement `QcewDownloader` class with:
  - `download_year()` - download and extract single year
  - `download_all()` - batch download with progress
  - Rate limiting (1 second between requests)
  - Skip-if-exists logic for resume support
- Unit tests for URL construction, skip logic

### Phase B: CLI Integration (FR-005, FR-007, FR-010)

- Add `download` subcommand to QCEW CLI group
- Options: `--years`, `--output-dir`, `--skip-existing`, `--extract`
- Progress reporting per year
- Add `mise run data:qcew-download` task

### Phase C: Shell Script Wrapper (US2)

- Create `scripts/download_qcew.sh` for simple one-liner usage
- Document in README

### Phase D: Validation & Integrity (FR-009, US4)

- Add CSV validation after extraction
- Verify FIPS code format (5-digit county codes only)
- Log disclosure code handling

### Phase E: Integration Testing

- Test download → load → query pipeline
- Detroit metro filter verification
- Re-run idempotency check

______________________________________________________________________

## Relationship to Existing Loader

```
┌─────────────────────────────────────────────────┐
│              NEW: QcewDownloader                │
│  (downloads ZIPs from BLS, extracts CSVs)       │
├─────────────────────────────────────────────────┤
│ download_year(2015) → data/qcew/2015.annual...  │
│ download_all(2010-2024) → all CSVs              │
└────────────────────────┬────────────────────────┘
                         │ CSVs ready
                         ▼
┌─────────────────────────────────────────────────┐
│         EXISTING: QcewLoader.load()             │
│  (already works with files in data/qcew/)       │
├─────────────────────────────────────────────────┤
│ _load_from_files() reads CSVs                   │
│ _process_file_record() creates FactQcewAnnual   │
└─────────────────────────────────────────────────┘
```

The downloader is a **pure data acquisition** component. The loader handles all database operations.

______________________________________________________________________

## Success Criteria Mapping

| SC     | Requirement            | How Verified                                                                                         |
| ------ | ---------------------- | ---------------------------------------------------------------------------------------------------- |
| SC-001 | 15 years × 3 counties  | `SELECT DISTINCT year, fips_code FROM fact_qcew_annual WHERE fips_code IN ('26163','26125','26099')` |
| SC-003 | \<5 min/year           | Timing logs in download script                                                                       |
| SC-004 | \<30s for re-run       | Test with `--skip-existing`                                                                          |
| SC-005 | \<15 min fresh setup   | End-to-end integration test                                                                          |
| SC-006 | Cache reduces time 90% | Compare first run vs second run                                                                      |
| SC-007 | All years queryable    | SQL query in test                                                                                    |
