# Tasks: QCEW Data Ingestion Pipeline

**Input**: Design documents from `/specs/004-qcew-data-ingestion/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/downloader.py ✓
**Created**: 2026-01-30

**Key Finding**: The existing `QcewLoader` (983 lines) already handles file-based ingestion. This feature only adds the download component (~200 lines total).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [x] T001 [P] Create `data/qcew/` directory for downloaded files (if not exists)
- [x] T002 [P] Verify httpx, tqdm dependencies available in pyproject.toml

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create `DownloadConfig` dataclass in `src/babylon/data/qcew/downloader.py`

  - Fields: years, output_dir, rate_limit_seconds, skip_existing, extract, cleanup_zips, base_url
  - Methods: get_zip_url(), get_zip_path(), get_csv_path()

- [x] T004 Create `DownloadResult` dataclass in `src/babylon/data/qcew/downloader.py`

  - Fields: year, success, zip_path, csv_path, error, bytes_downloaded, skipped
  - Property: status (OK/SKIPPED/FAILED)

- [x] T005 Create `DownloadReport` dataclass in `src/babylon/data/qcew/downloader.py`

  - Fields: years_requested, years_downloaded, years_skipped, years_failed, results, errors, total_bytes
  - Properties: success_rate, has_failures
  - Method: add_result()

- [x] T006 Update `src/babylon/data/qcew/__init__.py` to export new classes

**Checkpoint**: Foundation ready - user story implementation can now begin

______________________________________________________________________

## Phase 3: User Story 1 - Ingest Detroit Metro Historical Data (Priority: P1) 🎯 MVP

**Goal**: Download and extract QCEW data for Wayne/Oakland/Macomb counties 2010-2024

**Independent Test**: Run download for Detroit metro, verify CSVs exist in data/qcew/

### Implementation for User Story 1

- [x] T007 [US1] Implement `QcewDownloader.__init__()` with httpx client setup

  - File: `src/babylon/data/qcew/downloader.py`
  - Accept optional httpx.Client for testing

- [x] T008 [US1] Implement `QcewDownloader.download_year()` method

  - File: `src/babylon/data/qcew/downloader.py`
  - Download ZIP from BLS URL pattern
  - Stream download with progress callback
  - Return DownloadResult with success/error status

- [x] T009 [US1] Implement `QcewDownloader.verify_zip()` method

  - File: `src/babylon/data/qcew/downloader.py`
  - Check ZIP file integrity using zipfile.is_zipfile()
  - Test that ZIP can be opened without BadZipFile error

- [x] T010 [US1] Implement `QcewDownloader.extract_zip()` method

  - File: `src/babylon/data/qcew/downloader.py`
  - Extract to output directory
  - Handle space in filename: `{year}.annual singlefile.csv`
  - Return path to extracted CSV

- [x] T011 [US1] Implement `QcewDownloader.download_all()` method

  - File: `src/babylon/data/qcew/downloader.py`
  - Iterate through config.years
  - Implement rate limiting (time.sleep between requests)
  - Skip existing files if config.skip_existing
  - Build and return DownloadReport

- [x] T012 [US1] Add unit tests for URL construction and skip logic

  - File: `tests/unit/data/qcew/test_downloader.py`
  - Test DownloadConfig.get_zip_url() for multiple years
  - Test skip_existing behavior with mocked filesystem

**Checkpoint**: US1 complete - Detroit metro download functional

______________________________________________________________________

## Phase 4: User Story 2 - Reproducible Ingestion (Priority: P1)

**Goal**: Single mise command to download and load QCEW data

**Independent Test**: Run `mise run data:qcew-download` on clean environment

### Implementation for User Story 2

- [x] T013 [US2] Add `download` subcommand to QCEW CLI group

  - File: `src/babylon/data/cli.py`
  - Options: --years (default 2010-2024), --output-dir, --skip-existing, --no-extract
  - Call QcewDownloader.download_all()
  - Print progress per year

- [x] T014 [US2] Add `data:qcew-download` task to mise configuration

  - File: `.mise.toml`
  - Command: `poetry run python -m babylon.data.cli qcew-download`
  - Document in mise tasks list

- [x] T015 [US2] Create shell script wrapper `scripts/download_qcew.sh`

  - Accept start_year and end_year arguments
  - Call mise task with year range
  - Print summary on completion

- [x] T016 [US2] Add integration test for CLI download command

  - File: `tests/integration/data/qcew/test_downloader.py`
  - Mock HTTP responses to avoid hitting BLS in tests
  - Verify correct files created

**Checkpoint**: US2 complete - one-command reproducible download

______________________________________________________________________

## Phase 5: User Story 3 - Nationwide Ingestion (Priority: P2)

**Goal**: Support full nationwide QCEW data download

**Independent Test**: Run download without FIPS filter, verify larger file sizes

### Implementation for User Story 3

- [x] T017 [US3] Add --counties option to CLI for filtering

  - File: `src/babylon/data/cli.py`
  - Default: None (all counties)
  - Accept comma-separated FIPS codes for filtering
  - Note: Filtering happens at load time, not download time (files contain all data)
  - **IMPLEMENTATION NOTE**: This option would be no-op for download (files contain all data).
    Filtering is handled by existing QcewLoader during the load phase.

- [x] T018 [US3] Document disk space requirements in quickstart.md

  - File: `specs/004-qcew-data-ingestion/quickstart.md`
  - ~750 MB compressed, ~4.5 GB uncompressed for 2010-2024
  - Note that nationwide load uses existing QcewLoader
  - **Already documented** in quickstart.md lines 198-205

- [x] T019 [US3] Add --cleanup-zips option to free disk space

  - File: `src/babylon/data/cli.py`
  - Delete ZIP files after successful extraction
  - Update DownloadConfig to support this option
  - **Implemented** in qcew-download command

**Checkpoint**: US3 complete - nationwide download supported

______________________________________________________________________

## Phase 6: User Story 4 - Data Validation (Priority: P2)

**Goal**: Validate downloaded data integrity before loading

**Independent Test**: Download sample file, verify validation catches issues

### Implementation for User Story 4

- [x] T020 [US4] Implement `QcewDownloader.verify_csv()` method

  - File: `src/babylon/data/qcew/downloader.py`
  - Check file exists and is not empty
  - Verify expected columns present (area_fips, year, industry_code, etc.)
  - Return True/False
  - **Implemented** with REQUIRED_COLUMNS constant and header validation

- [x] T021 [US4] Add validation step to download_year() flow

  - File: `src/babylon/data/qcew/downloader.py`
  - Call verify_zip() after download
  - Call verify_csv() after extraction
  - Set error in DownloadResult if validation fails
  - **Implemented** in download_year() lines 293-325

- [x] T022 [US4] Add unit tests for validation methods

  - File: `tests/unit/data/qcew/test_downloader.py`
  - Test verify_zip() with valid/invalid ZIP fixtures
  - Test verify_csv() with valid/corrupted CSV fixtures
  - **Implemented** TestVerifyZip and TestVerifyCsv classes

**Checkpoint**: US4 complete - data validation integrated

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T023 [P] Update module docstrings in downloader.py
  - **Complete** - Module has comprehensive docstrings with usage example
- [x] T024 [P] Add type hints and ensure mypy passes
  - **Complete** - `mypy --strict` passes on downloader.py and cli.py
- [ ] T025 Run full integration test: download → load → query (unverifiable — ephemeral gate, no durable artifact)
  - Verify SC-007: `SELECT DISTINCT year FROM fact_qcew_annual WHERE fips_code = '26163'`
  - **Deferred** - Requires actual BLS data download (network I/O)
- [ ] T026 Update project README with QCEW download instructions (left unchecked 2026-07-08: README.md has no QCEW download instructions (single passing mention at README.md:13))
  - **Deferred** - Awaiting feature validation
- [ ] T027 Validate quickstart.md commands work end-to-end (unverifiable — ephemeral gate, no durable artifact)
  - **Deferred** - Requires actual BLS data download (network I/O)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) and US2 (P1) can proceed in parallel after foundation
  - US3 (P2) and US4 (P2) can proceed after US1/US2 or in parallel
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Detroit Metro)**: After Foundational - core download functionality
- **US2 (Reproducible)**: After US1 - needs QcewDownloader to exist
- **US3 (Nationwide)**: After US1 - extends with options
- **US4 (Validation)**: After US1 - adds validation to existing methods

### Within Each User Story

- Models before implementation
- Core methods before CLI integration
- Implementation before tests (existing loader handles loading)

### Parallel Opportunities

- T001, T002 can run in parallel (Setup)
- T012, T016, T022 (tests) can be written in parallel after their implementation tasks
- T023, T024 (polish) can run in parallel

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
1. Complete Phase 2: Foundational (dataclasses)
1. Complete Phase 3: User Story 1 (core downloader)
1. Complete Phase 4: User Story 2 (CLI + mise task)
1. **STOP and VALIDATE**: Download Detroit metro data end-to-end
1. Verify: `ls data/qcew/*.csv` shows 15 files (2010-2024)

### Full Feature

7. Complete Phase 5: User Story 3 (nationwide options)
1. Complete Phase 6: User Story 4 (validation)
1. Complete Phase 7: Polish
1. Final validation: Run SC-007 query

______________________________________________________________________

## Notes

- The existing `QcewLoader` handles all database loading - this feature only adds download
- BLS filename has space: `{year}.annual singlefile.csv` - handle carefully
- Rate limit: 1 second minimum between requests to be polite to BLS
- Estimated implementation: ~200 lines of new code (downloader.py + CLI additions)
