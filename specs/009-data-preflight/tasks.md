# Tasks: Data Preflight & Loader Unification

**Branch**: `009-data-preflight` | **Date**: 2026-02-01
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 0: Setup & Verification

- [x] **T001** - Run baseline test count for regression tracking
  - File: `tests/unit/data/test_preflight.py`
  - Command: `pytest tests/unit/data/test_preflight.py -v --collect-only`
  - Record: Current test count for SC-006 baseline

## Phase 1: Core Infrastructure

- [x] **T002** - Define VerificationProtocol in loader_base.py
  - File: `src/babylon/data/loader_base.py`
  - Insert: After line 697 (before `__all__`)
  - Contract: [contracts/verification_protocol.py](./contracts/verification_protocol.py)
  - Verification: `mypy src/babylon/data/loader_base.py` passes

- [x] **T003** - Export VerificationProtocol in preflight __all__
  - File: `src/babylon/data/preflight.py`
  - Update: `__all__` to include new exports
  - Verification: `from babylon.data.preflight import PreflightCheck` works

## Phase 2: Loader Protocol Implementation [P]

Tasks in this phase can be executed in parallel.

- [x] **T004** [P] - Implement VerificationProtocol in LodesCrosswalkLoader
  - File: `src/babylon/data/lodes/loader_3nf.py`
  - Insert: After `get_fact_tables()` method (after line 103)
  - Checks: File exists, not empty, not LFS pointer
  - Hint: Download URL from LEHD

- [x] **T005** [P] - Implement VerificationProtocol in TIGERCountyLoader
  - File: `src/babylon/data/tiger/loader.py`
  - Insert: After `get_fact_tables()` method (after line 146)
  - Checks: Shapefile exists, not empty
  - Hint: Census Bureau TIGER/Line download URL

- [x] **T006** [P] - Implement VerificationProtocol in CensusLoader
  - File: `src/babylon/data/census/loader_3nf.py`
  - Checks: CBSA file exists, not LFS pointer, API key (warn if missing)
  - Reuse: `_is_lfs_pointer()` from cbsa_parser.py

## Phase 3: Scenario Configuration

- [x] **T007** - Add ScenarioDataConfig dataclass to preflight.py
  - File: `src/babylon/data/preflight.py`
  - Insert: After line 71 (after `AddCheckFn` type alias)
  - Model: [data-model.md](./data-model.md) - ScenarioDataConfig definition
  - Validation: required_loaders not empty, year_range valid

- [x] **T008** - Add Detroit scenario configuration
  - File: `src/babylon/data/preflight.py`
  - Config: QCEW, LODES, Census, TIGER for Wayne/Oakland/Macomb counties
  - Years: 2010-2025
  - FIPS: 26163, 26125, 26099

- [x] **T009** - Add run_scenario_preflight() function
  - File: `src/babylon/data/preflight.py`
  - Insert: After `run_preflight()` function (after line 477)
  - Logic: Call both VerificationProtocol loaders AND existing _check_* functions
  - QCEW: Uses existing _check_qcew() (not VerificationProtocol per clarification)

## Phase 4: Entry Point Integration

- [x] **T010** - Add preflight report printer to __main__.py
  - File: `src/babylon/__main__.py`
  - Function: `_print_preflight_report(result: PreflightResult)`
  - Output: Human-readable failure report with hints

- [x] **T011** - Integrate preflight into main() entry point
  - File: `src/babylon/__main__.py`
  - Insert: At start of `main()` function (after line 32)
  - Logic: Run preflight("detroit"), exit(1) on failure
  - Silent: No stdout when ok=True

## Phase 5: Tests [P]

Tasks in this phase can be executed in parallel.

- [x] **T012** [P] - Add unit tests for VerificationProtocol implementations
  - File: `tests/unit/data/test_preflight.py`
  - Tests:
    - test_lodes_loader_missing_file
    - test_tiger_loader_empty_file
    - test_census_loader_lfs_pointer
    - test_census_loader_missing_api_key

- [x] **T013** [P] - Add unit tests for ScenarioDataConfig
  - File: `tests/unit/data/test_preflight.py`
  - Tests:
    - test_scenario_config_empty_loaders_raises
    - test_scenario_config_invalid_year_range_raises
    - test_detroit_config_has_four_sources

- [x] **T014** [P] - Create integration test file for Detroit scenario
  - File: `tests/integration/data/test_preflight_detroit.py` (NEW)
  - Tests:
    - test_detroit_preflight_validates_all_four_sources
    - test_detroit_partial_data_reports_mixed_results

## Phase 6: Validation

- [x] **T015** - Run full test suite for regressions
  - Command: `pytest tests/unit/data/test_preflight.py -v`
  - Verify: All existing tests pass (SC-006)
  - Verify: New tests pass

- [x] **T016** - Run mypy type checks
  - Command: `mypy src/babylon/data/preflight.py src/babylon/data/loader_base.py`
  - Verify: No type errors

- [x] **T017** - Verify entry point integration
  - Command: `python -m babylon` (with missing data)
  - Expected: Preflight failure report, exit code 1
  - Command: `python -m babylon` (with all data)
  - Expected: Simulation starts normally

## Dependencies

```
T001 (baseline) → T002-T003 (infra) → T004-T006 (loaders, parallel)
                                    ↓
                              T007-T009 (scenario)
                                    ↓
                              T010-T011 (entry point)
                                    ↓
                              T012-T014 (tests, parallel)
                                    ↓
                              T015-T017 (validation)
```

## Exit Criteria

From [plan.md](./plan.md):

- [x] VerificationProtocol defined and documented
- [x] 3 loaders implement protocol (Census, LODES, TIGER)
- [x] Detroit scenario preflight validates all 4 data sources
- [x] Entry point integration blocks simulation on preflight failure
- [x] All existing tests pass (SC-006) - 24 tests total (up from 7 baseline)
- [x] New integration tests for Detroit scenario (3 passed, 1 skipped)
- [x] All checklist gaps addressed in spec clarifications
