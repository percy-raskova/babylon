# Feature Specification: Data Preflight & Loader Unification

**Feature Branch**: `009-data-preflight`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Spec 009: Data Preflight & Loader Unification - Refactor loaders with VerificationProtocol, expand preflight.py for Detroit scenario data validation, and integrate preflight checks into CLI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clear Error Reporting Before Simulation Starts (Priority: P1)

A user attempts to run the Detroit scenario simulation but is missing required data files. Instead of the simulation crashing mid-execution with a cryptic stack trace, the user receives a clear, structured report identifying which data sources are missing before any simulation code runs.

**Why this priority**: This is the core value proposition - preventing frustrating mid-simulation failures and providing actionable guidance on missing data. Without this, users waste time debugging stack traces instead of understanding data requirements.

**Independent Test**: Can be fully tested by running the simulation with missing LODES data and verifying a human-readable "Missing Data" report appears with download/acquisition guidance.

**Acceptance Scenarios**:

1. **Given** a user with missing LODES crosswalk files, **When** they start the Detroit scenario, **Then** they receive a report listing "LODES: Missing us_xwalk.csv in data/lodes" with a hint on where to download the file.

2. **Given** a user with missing TIGER shapefiles, **When** they run any geography-dependent simulation, **Then** they receive a report listing the missing shapefile path and Census Bureau download URL.

3. **Given** a user with all required Detroit data present, **When** they start the Detroit scenario, **Then** preflight passes silently (no stdout output) and simulation starts normally.

4. **Given** a user with missing QCEW files, **When** they start the Detroit scenario, **Then** they receive a report listing "QCEW: No CSV files found in data/qcew" with a BLS download hint.

5. **Given** a user without CENSUS_API_KEY set, **When** they start the Detroit scenario, **Then** they receive a warning (not failure) noting the key is optional but recommended.

______________________________________________________________________

### User Story 2 - Unified Loader Verification Interface (Priority: P2)

A developer adding a new data loader can implement a standard verification interface that integrates automatically with the preflight system. This ensures all loaders consistently report their data requirements.

**Why this priority**: Enables maintainability and extensibility. New loaders automatically participate in preflight checks without modifying preflight.py directly.

**Independent Test**: Can be fully tested by creating a mock loader implementing `VerificationProtocol`, registering it, and verifying preflight invokes the loader's verification method.

**Acceptance Scenarios**:

1. **Given** a loader implementing the verification protocol, **When** that loader is registered with the preflight system, **Then** preflight automatically invokes its source file checks.

2. **Given** a loader's verification returns failures, **When** preflight runs, **Then** the failures appear in the result with loader-specific context.

3. **Given** a loader that requires network resources, **When** preflight runs in offline mode, **Then** the loader reports a warning instead of a failure for network-dependent checks.

______________________________________________________________________

### User Story 3 - Detroit Scenario Complete Validation (Priority: P3)

A user preparing to run the Detroit scenario (2010-2025) receives comprehensive validation that all required datasets exist: QCEW (employment), LODES (commute/freight flows), ACS (demographics), and TIGER (county boundaries).

**Why this priority**: Detroit is the reference scenario for the simulation. Validating its complete data requirements ensures the flagship use case works reliably.

**Independent Test**: Can be fully tested by running preflight with Detroit scenario configuration and verifying all four data sources are checked with appropriate year coverage.

**Acceptance Scenarios**:

1. **Given** the Detroit scenario configuration, **When** preflight runs for Detroit, **Then** it validates QCEW, LODES, ACS, and TIGER data sources for Wayne, Oakland, and Macomb counties.

2. **Given** a Detroit configuration for years 2010-2025, **When** preflight runs, **Then** it verifies each data source covers the specified year range (or reports gaps).

3. **Given** partial Detroit data (e.g., QCEW present but LODES missing), **When** preflight runs, **Then** the report shows a success summary for QCEW and failure details for LODES.

______________________________________________________________________

### Edge Cases

- **Empty files (0 bytes)**: Treated as failures; report "File exists but is empty" with re-download hint.
- **Git LFS pointer files**: Treated as failures; report with `git lfs pull` instructions (FR-009).
- **Unset API keys for optional loaders**: Treated as warnings; simulation may proceed with reduced functionality.
- **Incompatible version/format**: Deferred to loader. Preflight only checks existence, non-empty size, and LFS status. Format validation occurs during load().
- **Year range exceeds data coverage**: Report partial coverage as warning; fail only if zero years available.
- **Read permission errors**: Treated as failures; report with hint "Check file permissions: chmod +r <path>".
- **Corrupted files (non-empty but invalid content)**: Deferred to loader. Preflight validates file presence/size/LFS only; content validation is loader responsibility.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a verification protocol that loaders can implement to declare their source file requirements.
- **FR-002**: System MUST update CensusLoader, LodesCrosswalkLoader, and TIGERCountyLoader to implement the verification protocol.
- **FR-003**: System MUST update preflight to discover and invoke all registered verification protocol implementers.
- **FR-004**: System MUST validate that Detroit scenario data (QCEW, LODES, ACS, TIGER) exists for years 2010-2025 before simulation starts.
- **FR-005**: System MUST integrate preflight checks into the simulation entry point so preflight runs automatically before simulation initialization.
- **FR-006**: System MUST generate a structured "Missing Data" report with file paths, hints, and download URLs when validation fails.
- **FR-007**: System MUST distinguish between hard failures (cannot proceed) and warnings (optional data missing).
- **FR-008**: System MUST support offline mode (skip network endpoint checks) and online mode (validate API reachability).
- **FR-009**: System MUST detect Git LFS pointer files that haven't been pulled and report them as failures with retrieval instructions.
- **FR-010**: System MUST exit with non-zero status code when preflight fails, preventing simulation from starting.

### Key Entities

- **VerificationProtocol**: Interface that loaders implement to declare their file/resource requirements. Returns a list of preflight check objects.
- **PreflightCheck**: Existing entity representing a single check result (status, message, hint, details).
- **PreflightResult**: Existing aggregate of all checks with convenience properties for failures/warnings.
- **ScenarioDataConfig**: Configuration mapping scenario names (e.g., "detroit") to required data sources and coverage years.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users attempting to run Detroit scenario without required data receive a complete missing data report in under 5 seconds.
  - *Test methodology*: Cold start (no Python cache), standard SSD, Detroit scenario with 4 data sources, measured via `time python -m babylon`.
- **SC-002**: Preflight correctly identifies 100% of required files for the Detroit scenario (QCEW, LODES, ACS, TIGER for 3 counties, 2010-2025).
- **SC-003**: New loaders can integrate with preflight by implementing a single-method protocol.
- **SC-004**: Zero simulation crashes due to missing data files after preflight passes.
  - *Test methodology*: Integration test runs Detroit simulation with all data present; verifies simulation completes first tick without FileNotFoundError.
- **SC-005**: Preflight report includes actionable hints with download URLs for each missing data source.
- **SC-006**: All existing preflight tests continue to pass (zero regressions).
  - *Baseline*: Run `pytest tests/unit/data/test_preflight.py -v --collect-only` before implementation to establish test count.

## Clarifications

### Session 2026-01-31

- Q: How should loaders be discovered by the preflight system? → A: Explicit registration (whitelist of loader classes in preflight.py)
- Q: How should empty or corrupt data files be handled? → A: Treat as failures (same as missing - block simulation start)

### Session 2026-02-01 (Checklist Review)

- Q: Should QCEW implement VerificationProtocol? → A: No. Existing `_check_qcew()` function is sufficient. `run_scenario_preflight()` calls both protocol-based loaders AND existing `_check_*` functions.
- Q: What does "silently" mean in Story 1 Scenario 3? → A: No stdout output when preflight passes (ok=True). Logging at DEBUG level is acceptable.
- Q: Should preflight support JSON output? → A: Excluded from MVP. Console output only. PreflightResult.to_dict() exists for programmatic access.
- Q: How to handle corrupted (non-empty but invalid) files? → A: Preflight checks existence/size/LFS only. Content validation deferred to loader's load() method.
- Q: How to handle read permission errors? → A: Treat as failure with hint "Check file permissions".

### MVP Scope Exclusions

The following are explicitly **excluded from MVP scope**:

- **Interrupt handling (Ctrl+C)**: Default Python behavior (raise KeyboardInterrupt)
- **Retry logic for transient network errors**: Single attempt; fail on error
- **Download URL validation**: Hints are static strings, not validated
- **Logging/observability configuration**: Use existing logger; no new requirements
- **Error message localization (i18n)**: English only
- **Thread safety/concurrent execution**: Preflight runs sequentially, single-threaded

## Assumptions

- Detroit scenario requires Wayne (26163), Oakland (26125), and Macomb (26099) counties.
- LODES data is stored in `data/lodes/` with `us_xwalk.csv` or `us_xwalk.csv.gz` naming.
- TIGER shapefiles are stored in `data/tiger/county/` with Census Bureau naming conventions.
- ACS data is fetched via Census API (checked by existing CensusLoader preflight).
- Loaders are registered via explicit whitelist in preflight.py (not dynamic discovery).
- The simulation entry point is `python -m babylon` which will be enhanced to run preflight before simulation.
