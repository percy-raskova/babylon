# Feature Specification: QCEW Data Ingestion Pipeline

**Feature Branch**: `004-qcew-data-ingestion`
**Created**: 2026-01-30
**Status**: Draft
**Input**: User description: "Bulk ingest QCEW annual employment and wage data from BLS for years 2010-2024, enabling temporal validation and empirical calibration of Marxian value tensors."

## Clarifications

*None required - requirements are clear from BLS data structure and existing database schema.*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest Detroit Metro Historical Data (Priority: P1)

As a simulation developer, I need to populate the `fact_qcew_annual` table with employment and wage data for Wayne, Oakland, and Macomb counties from 2010-2024, so that the MarxianHydrator can compute temporal trends and the deindustrialization signal can be validated.

**Why this priority**: This directly unblocks PRE-001 for the hydrator temporal validation feature. Without historical data, Z-score anomaly detection and deindustrialization signal detection cannot function.

**Independent Test**: Can be fully tested by running the ingestion for Detroit metro counties and verifying row counts and data integrity in SQLite.

**Acceptance Scenarios**:

1. **Given** an empty or partially populated `fact_qcew_annual` table, **When** I run the ingestion pipeline for years 2010-2024 with Detroit metro filter, **Then** the table contains data for all three counties (26163, 26125, 26099) across all 15 years with no gaps.

1. **Given** the ingestion has completed, **When** I query for Wayne County (26163) year 2015, **Then** I receive employment and wage data broken down by NAICS industry codes.

1. **Given** the ingestion has already run for a year, **When** I run it again for the same year, **Then** existing records are updated (upsert) rather than duplicated.

1. **Given** network interruption during download, **When** the pipeline resumes, **Then** it continues from where it left off without re-downloading completed years.

______________________________________________________________________

### User Story 2 - Reproducible Ingestion for Other Developers (Priority: P1)

As a developer setting up the project on a new machine, I need a single command that downloads and loads QCEW data, so that I can reproduce the empirical data foundation without manual file management.

**Why this priority**: Tied with US1 - reproducibility is essential for open-source collaboration and CI/CD validation.

**Independent Test**: Can be fully tested by running the command on a clean environment and verifying data loads correctly.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository, **When** I run `mise run data:qcew-ingest` (or equivalent), **Then** the pipeline downloads, extracts, and loads QCEW data for the configured year range.

1. **Given** BLS servers are accessible, **When** I run the ingestion command, **Then** downloads use polite rate limiting (minimum 1 second between requests) to respect BLS server resources.

1. **Given** the ingestion command, **When** I check the output, **Then** progress is reported per-year (downloading, extracting, loading) with row counts.

______________________________________________________________________

### User Story 3 - Nationwide Ingestion for Calibration (Priority: P2)

As a data scientist, I need to ingest QCEW data for all U.S. counties, so that I can compute the national 95th percentile threshold for anomaly detection calibration.

**Why this priority**: Required for FR-008 in the temporal validation feature, but Detroit metro (US1) can proceed independently.

**Independent Test**: Can be fully tested by running nationwide ingestion and verifying coverage across all ~3,200 counties.

**Acceptance Scenarios**:

1. **Given** the ingestion configured for nationwide data, **When** I run the pipeline, **Then** data is loaded for all counties present in the BLS annual files.

1. **Given** nationwide ingestion has completed, **When** I query distinct county counts per year, **Then** each year has approximately 3,200 counties (matching BLS published counts).

1. **Given** the large data volume (~4-5 million rows per year), **When** ingestion runs, **Then** it completes within a reasonable time using batch inserts.

______________________________________________________________________

### User Story 4 - Data Validation and Integrity (Priority: P2)

As a data quality analyst, I need the ingestion pipeline to validate data integrity, so that downstream systems receive clean, consistent data.

**Why this priority**: Prevents garbage-in-garbage-out scenarios that would corrupt tensor calculations.

**Independent Test**: Can be fully tested by ingesting sample data and verifying constraint enforcement.

**Acceptance Scenarios**:

1. **Given** raw QCEW CSV data, **When** ingested, **Then** only county-level records are loaded (5-digit FIPS codes), excluding state totals, MSA aggregates, and national totals.

1. **Given** a record with disclosure suppression (missing wage data), **When** ingested, **Then** the record is either loaded with NULL values or skipped with a logged warning.

1. **Given** ingestion completes, **When** I check foreign key relationships, **Then** all FIPS codes in `fact_qcew_annual` have corresponding entries in `dim_county` (or are flagged for missing dimension data).

______________________________________________________________________

### Edge Cases

- What happens when BLS removes or restructures a historical year's files?

  - Log error, skip that year, continue with others. Report missing years at end.

- What happens when a ZIP file is corrupted during download?

  - Verify ZIP integrity before extraction. Re-download if corrupted.

- What happens when disk space is insufficient for extraction?

  - Check available space before extraction. Fail fast with clear error message.

- What happens when the database schema has changed?

  - Migration scripts handle schema evolution. Ingestion validates against current schema.

- What happens when NAICS codes change between years (e.g., 2017 revision)?

  - Load raw NAICS codes as-is. Classification mapping is handled by DepartmentMapper, not ingestion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST download QCEW annual ZIP files from BLS using the URL pattern `https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip`.

- **FR-002**: System MUST extract CSV files from downloaded ZIPs and parse them according to BLS QCEW annual layout (area_fips, year, industry_code, own_code, annual_avg_emplvl, total_annual_wages, avg_annual_pay, etc.).

- **FR-003**: System MUST load parsed data into `fact_qcew_annual` table using upsert semantics (INSERT OR REPLACE) to support re-runs.

- **FR-004**: System MUST support filtering by FIPS codes to enable Detroit-metro-only ingestion (26163, 26125, 26099).

- **FR-005**: System MUST support year range specification (e.g., 2010-2024) via command-line argument or configuration.

- **FR-006**: System MUST implement polite rate limiting (minimum 1 second delay between HTTP requests) when downloading from BLS.

- **FR-007**: System MUST report progress including: years downloaded, extraction status, rows loaded per year.

- **FR-008**: System MUST skip already-downloaded ZIP files to support resumable ingestion.

- **FR-009**: System MUST validate that loaded FIPS codes are 5-digit county codes, excluding state totals (2-digit), MSA codes, and national totals.

- **FR-010**: System MUST be invocable via mise task (`mise run data:qcew-ingest`) for developer convenience.

### Key Entities

- **QCEWDownloadConfig**: Configuration for the download process. Contains: year_range (tuple), fips_filter (optional set), output_dir (path), rate_limit_seconds (float).

- **QCEWAnnualRecord**: Parsed record from QCEW CSV. Contains: area_fips, year, industry_code, own_code, annual_avg_emplvl, total_annual_wages, avg_annual_pay, disclosure_code.

- **IngestionReport**: Summary of ingestion run. Contains: years_attempted (list), years_succeeded (list), years_failed (list), rows_loaded (dict by year), errors (list).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After Detroit metro ingestion (2010-2024), `fact_qcew_annual` contains data for all 15 years × 3 counties with zero year gaps.

- **SC-002**: Full nationwide ingestion (2010-2024) loads approximately 50-60 million rows total (estimated ~4M rows/year × 15 years).

- **SC-003**: Ingestion for a single year completes within 5 minutes on a standard developer machine (download + extract + load).

- **SC-004**: Re-running ingestion for already-loaded years completes within 30 seconds (skips download, verifies existing data).

- **SC-005**: A developer with a fresh repository clone can populate the database with Detroit metro data in under 15 minutes using a single command.

- **SC-006**: Downloaded ZIP files are cached locally, reducing repeat ingestion time by 90% (only load phase runs).

- **SC-007**: Query `SELECT DISTINCT year FROM fact_qcew_annual WHERE fips_code = '26163' ORDER BY year` returns all years from 2010 to 2024 with no gaps.

## Assumptions

- BLS maintains the current URL pattern for downloadable files (`data.bls.gov/cew/data/files/{year}/csv/...`).
- BLS servers are publicly accessible without authentication.
- The `annual_singlefile.zip` format remains consistent across years (same CSV column layout).
- Network connectivity is available during ingestion (not designed for offline-first).
- The existing `fact_qcew_annual` schema is compatible with BLS data fields.
- SQLite is sufficient for the data volume (~60M rows nationwide, ~500K rows Detroit metro).
