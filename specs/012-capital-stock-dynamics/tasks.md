# Tasks: Capital Stock Dynamics

**Input**: Design documents from `/specs/012-capital-stock-dynamics/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md, data-model.md, contracts/, quickstart.md

**Tests**: This feature includes unit tests as part of TDD (per project CLAUDE.md guidelines).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/babylon/economics/`
- **Unit Tests**: `tests/unit/economics/`
- **Integration Tests**: `tests/integration/economics/`

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new modules and establish base structure

- [ ] T001 Create depreciation.py module skeleton in src/babylon/economics/depreciation.py
- [ ] T002 Create capital_stock.py module skeleton in src/babylon/economics/capital_stock.py
- [ ] T003 Create derived_metrics.py module skeleton in src/babylon/economics/derived_metrics.py
- [ ] T004 [P] Create test_depreciation.py skeleton in tests/unit/economics/test_depreciation.py
- [ ] T005 [P] Create test_capital_stock.py skeleton in tests/unit/economics/test_capital_stock.py
- [ ] T006 [P] Create test_derived_metrics.py skeleton in tests/unit/economics/test_derived_metrics.py
- [ ] T007 Update src/babylon/economics/__init__.py with new module exports

______________________________________________________________________

## Phase 2: Foundational (DepreciationConfig - Required by All Stories)

**Purpose**: Implement DepreciationConfig dataclass that all other components depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Phase (TDD)

- [ ] T008 [P] Write test for DepreciationConfig default rate (0.07) in tests/unit/economics/test_depreciation.py
- [ ] T009 [P] Write test for DepreciationConfig validation rejects rate < 0.01 in tests/unit/economics/test_depreciation.py
- [ ] T010 [P] Write test for DepreciationConfig validation rejects rate > 0.20 in tests/unit/economics/test_depreciation.py
- [ ] T011 [P] Write test for DepreciationConfig.slow() factory (δ=0.05) in tests/unit/economics/test_depreciation.py
- [ ] T012 [P] Write test for DepreciationConfig.fast() factory (δ=0.10) in tests/unit/economics/test_depreciation.py
- [ ] T013 [P] Write test for DepreciationConfig.steady_state_K() formula in tests/unit/economics/test_depreciation.py
- [ ] T014 [P] Write test for DepreciationConfig.next_K() perpetual inventory formula in tests/unit/economics/test_depreciation.py

### Implementation for Foundational Phase

- [ ] T015 Implement DepreciationConfig frozen dataclass with rate validation in src/babylon/economics/depreciation.py
- [ ] T016 Add slow(), fast(), default() factory methods in src/babylon/economics/depreciation.py
- [ ] T017 Add steady_state_K() and next_K() helper methods in src/babylon/economics/depreciation.py
- [ ] T018 Run tests to verify all T008-T014 pass

**Checkpoint**: DepreciationConfig complete - user story implementation can begin

______________________________________________________________________

## Phase 3: User Story 1 - Compute County-Level Capital Stock (Priority: P1) 🎯 MVP

**Goal**: Enable researchers to access capital stock K[fips, year] for TRPF analysis

**Independent Test**: Hydrate Wayne County (26163) tensor data for 2010-2024, compute K for each year, validate perpetual inventory formula K[t] = K[t-1] × (1-δ) + total_c[t-1] and K_0 = total_c_0/δ.

### Tests for User Story 1 (TDD)

- [ ] T019 [P] [US1] Write test for get_K returns NoDataSentinel when tensor missing in tests/unit/economics/test_capital_stock.py
- [ ] T020 [P] [US1] Write test for get_K returns NoDataSentinel for year < MIN_YEAR in tests/unit/economics/test_capital_stock.py
- [ ] T021 [P] [US1] Write test for initial K_0 = total_c/δ formula in tests/unit/economics/test_capital_stock.py
- [ ] T022 [P] [US1] Write test for K[t] = K[t-1]×(1-δ) + total_c[t-1] formula in tests/unit/economics/test_capital_stock.py
- [ ] T023 [P] [US1] Write test for K clamped to non-negative (K >= 0) in tests/unit/economics/test_capital_stock.py
- [ ] T024 [P] [US1] Write test for compute_time_series returns dict[year, K] in tests/unit/economics/test_capital_stock.py
- [ ] T025 [P] [US1] Write test for compute_time_series skips missing years with warning in tests/unit/economics/test_capital_stock.py
- [ ] T026 [P] [US1] Write test for cache_info returns statistics in tests/unit/economics/test_capital_stock.py

### Implementation for User Story 1

- [ ] T027 [US1] Implement CapitalStockCalculator.__init__ with registry and depreciation params in src/babylon/economics/capital_stock.py
- [ ] T028 [US1] Add depreciation_rate property in src/babylon/economics/capital_stock.py
- [ ] T029 [US1] Implement _cache dict and thread lock in src/babylon/economics/capital_stock.py
- [ ] T030 [US1] Implement compute_time_series() with perpetual inventory method in src/babylon/economics/capital_stock.py
- [ ] T031 [US1] Implement get_K() using cache lookup or compute_time_series in src/babylon/economics/capital_stock.py
- [ ] T032 [US1] Implement clear_cache() and cache_info() methods in src/babylon/economics/capital_stock.py
- [ ] T033 [US1] Add logging for missing year warnings in src/babylon/economics/capital_stock.py
- [ ] T034 [US1] Run tests to verify T019-T026 pass

**Checkpoint**: User Story 1 complete - capital stock K[fips, year] is accessible and testable

______________________________________________________________________

## Phase 4: User Story 2 - Calculate Profit Rate Time Series (Priority: P1)

**Goal**: Enable economists to compute stock-based profit rate r = s/(K+v) for TRPF validation

**Independent Test**: Compute r for Wayne County time series, verify formula r = total_s/(K + total_v), observe expected secular decline.

### Tests for User Story 2 (TDD)

- [ ] T035 [P] [US2] Write test for DerivedTensorMetrics creation with all fields in tests/unit/economics/test_derived_metrics.py
- [ ] T036 [P] [US2] Write test for profit_rate_stock = s/(K+v) formula in tests/unit/economics/test_derived_metrics.py
- [ ] T037 [P] [US2] Write test for profit_rate_stock returns inf when K+v=0 in tests/unit/economics/test_derived_metrics.py
- [ ] T038 [P] [US2] Write test for profit_rate_flow property delegates to tensor in tests/unit/economics/test_derived_metrics.py
- [ ] T039 [P] [US2] Write test for to_dict() returns expected keys in tests/unit/economics/test_derived_metrics.py
- [ ] T040 [P] [US2] Write test for get_metrics returns DerivedTensorMetrics in tests/unit/economics/test_capital_stock.py
- [ ] T041 [P] [US2] Write test for get_metrics returns NoDataSentinel when K unavailable in tests/unit/economics/test_capital_stock.py

### Implementation for User Story 2

- [ ] T042 [US2] Implement DerivedTensorMetrics frozen dataclass in src/babylon/economics/derived_metrics.py
- [ ] T043 [US2] Add profit_rate_flow property delegating to tensor.profit_rate in src/babylon/economics/derived_metrics.py
- [ ] T044 [US2] Add to_dict() method for analysis export in src/babylon/economics/derived_metrics.py
- [ ] T045 [US2] Implement get_metrics() in CapitalStockCalculator in src/babylon/economics/capital_stock.py
- [ ] T046 [US2] Handle division by zero (K+v=0) returning float('inf') in src/babylon/economics/capital_stock.py
- [ ] T047 [US2] Run tests to verify T035-T041 pass

**Checkpoint**: User Stories 1 & 2 complete - K and profit rate r are accessible

______________________________________________________________________

## Phase 5: User Story 3 - Access Derived Ratios (OCC and Exploitation Rate) (Priority: P2)

**Goal**: Enable analysts to access OCC and exploitation rate from DerivedTensorMetrics

**Independent Test**: Compute OCC = c/v and e = s/v from tensor, verify division-by-zero handling returns inf.

### Tests for User Story 3 (TDD)

- [ ] T048 [P] [US3] Write test for organic_composition = c/v formula in tests/unit/economics/test_derived_metrics.py
- [ ] T049 [P] [US3] Write test for exploitation_rate = s/v formula in tests/unit/economics/test_derived_metrics.py
- [ ] T050 [P] [US3] Write test for OCC returns inf when v=0 in tests/unit/economics/test_derived_metrics.py
- [ ] T051 [P] [US3] Write test for exploitation_rate returns inf when v=0 in tests/unit/economics/test_derived_metrics.py

### Implementation for User Story 3

- [ ] T052 [US3] Verify OCC and exploitation_rate are computed in DerivedTensorMetrics in src/babylon/economics/derived_metrics.py
- [ ] T053 [US3] Ensure division-by-zero produces float('inf') consistently in src/babylon/economics/derived_metrics.py
- [ ] T054 [US3] Run tests to verify T048-T051 pass

**Checkpoint**: User Stories 1, 2, & 3 complete - K, r, OCC, e all accessible

______________________________________________________________________

## Phase 6: User Story 4 - Perform Depreciation Sensitivity Analysis (Priority: P2)

**Goal**: Enable researchers to test TRPF robustness with varying δ values

**Independent Test**: Compute K with δ = 0.05, 0.07, 0.10 and verify K_slow > K_default > K_fast, all showing declining r trend.

### Tests for User Story 4 (TDD)

- [ ] T055 [P] [US4] Write test for K with δ=0.05 > K with δ=0.07 in tests/unit/economics/test_capital_stock.py
- [ ] T056 [P] [US4] Write test for K with δ=0.10 < K with δ=0.07 in tests/unit/economics/test_capital_stock.py
- [ ] T057 [P] [US4] Write test for multiple calculators with different configs are independent in tests/unit/economics/test_capital_stock.py

### Implementation for User Story 4

- [ ] T058 [US4] Verify CapitalStockCalculator correctly uses injected DepreciationConfig in src/babylon/economics/capital_stock.py
- [ ] T059 [US4] Add example in docstring showing sensitivity analysis pattern in src/babylon/economics/capital_stock.py
- [ ] T060 [US4] Run tests to verify T055-T057 pass

**Checkpoint**: User Stories 1-4 complete - sensitivity analysis enabled

______________________________________________________________________

## Phase 7: User Story 5 - Access Aggregated Capital Stock (Priority: P3)

**Goal**: Enable policy analysts to access state/national capital stock totals

**Independent Test**: Compute K for all Michigan counties (state 26), sum to state total, verify K_aggregate matches sum(county K).

### Tests for User Story 5 (TDD)

- [ ] T061 [P] [US5] Write test for get_K_aggregate STATE returns sum of county K values in tests/unit/economics/test_capital_stock.py
- [ ] T062 [P] [US5] Write test for get_K_aggregate NATION returns sum of all county K values in tests/unit/economics/test_capital_stock.py
- [ ] T063 [P] [US5] Write test for get_K_aggregate returns NoDataSentinel when no county data in tests/unit/economics/test_capital_stock.py

### Implementation for User Story 5

- [ ] T064 [US5] Implement get_K_aggregate() for STATE level in src/babylon/economics/capital_stock.py
- [ ] T065 [US5] Implement get_K_aggregate() for NATION level in src/babylon/economics/capital_stock.py
- [ ] T066 [US5] Add aggregation cache with invalidation in src/babylon/economics/capital_stock.py
- [ ] T067 [US5] Run tests to verify T061-T063 pass

**Checkpoint**: All user stories complete - full capital stock dynamics functionality

______________________________________________________________________

## Phase 8: Integration & TRPF Validation

**Purpose**: Integration tests and statistical validation of TRPF predictions

### Integration Tests

- [ ] T068 [P] Write integration test for full pipeline: registry → calculator → metrics in tests/integration/economics/test_trpf_validation.py
- [ ] T069 [P] Write integration test for Detroit validation case (Wayne vs Oakland OCC) in tests/integration/economics/test_trpf_validation.py
- [ ] T070 Write test for SC-002: profit rate linear regression shows negative slope in tests/integration/economics/test_trpf_validation.py
- [ ] T071 Write test for SC-003: OCC-CoreIndex correlation > 0.3 in tests/integration/economics/test_trpf_validation.py
- [ ] T072 Write test for SC-004: TRPF robust across δ ∈ {0.05, 0.07, 0.10} in tests/integration/economics/test_trpf_validation.py
- [ ] T073 Write test for SC-005: state aggregate = sum(county K) within 0.01% in tests/integration/economics/test_trpf_validation.py

### Validation Runs

- [ ] T074 Run all unit tests to verify passing
- [ ] T075 Run integration tests with synthetic data to verify TRPF validation
- [ ] T076 Verify SC-006: existing TensorRegistry tests still pass

______________________________________________________________________

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and finalization

- [ ] T077 [P] Add module docstrings per Sphinx RST format in src/babylon/economics/depreciation.py
- [ ] T078 [P] Add module docstrings per Sphinx RST format in src/babylon/economics/capital_stock.py
- [ ] T079 [P] Add module docstrings per Sphinx RST format in src/babylon/economics/derived_metrics.py
- [ ] T080 [P] Add type hints and validate with mypy for all new modules
- [ ] T081 Run quickstart.md examples manually to verify they work
- [ ] T082 Update ai-docs/state.yaml with new components (CapitalStockCalculator, DerivedTensorMetrics)
- [ ] T083 Final commit with all changes

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Phase 2 completion
  - US1 can proceed immediately after Phase 2
  - US2 depends on US1 (needs get_K for profit rate)
  - US3 can start with US2 (shares DerivedTensorMetrics)
  - US4 can start after US1 (only needs K computation)
  - US5 can start after US1 (only needs get_K)
- **Integration (Phase 8)**: Depends on all user stories
- **Polish (Phase 9)**: Depends on Phase 8

### User Story Dependencies

```
Phase 2 (DepreciationConfig)
          │
          ▼
    ┌─────┴─────┐
    │           │
    ▼           ▼
   US1 ────► US2 ────► US3
(get_K)    (metrics) (ratios)
    │
    ├─────► US4 (sensitivity)
    │
    └─────► US5 (aggregation)
```

- **US1**: Can start after Phase 2 - No dependencies on other stories
- **US2**: Depends on US1 (needs get_K for profit_rate_stock calculation)
- **US3**: Can parallelize with US2 end (both use DerivedTensorMetrics)
- **US4**: Can start after US1 (only needs K computation, tests δ variations)
- **US5**: Can start after US1 (only needs get_K, adds aggregation)

### Within Each User Story

- Tests (TDD) MUST be written and FAIL before implementation
- Implementation follows test order
- Story complete when all story tests pass

### Parallel Opportunities

All tasks marked [P] can run in parallel:
- T004-T006 (test skeletons)
- T008-T014 (foundational tests)
- T019-T026 (US1 tests)
- T035-T041 (US2 tests)
- T048-T051 (US3 tests)
- T055-T057 (US4 tests)
- T061-T063 (US5 tests)
- T068-T069 (integration tests)
- T077-T080 (documentation)

______________________________________________________________________

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write test for get_K returns NoDataSentinel when tensor missing in tests/unit/economics/test_capital_stock.py"
Task: "Write test for get_K returns NoDataSentinel for year < MIN_YEAR in tests/unit/economics/test_capital_stock.py"
Task: "Write test for initial K_0 = total_c/δ formula in tests/unit/economics/test_capital_stock.py"
Task: "Write test for K[t] = K[t-1]×(1-δ) + total_c[t-1] formula in tests/unit/economics/test_capital_stock.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (DepreciationConfig)
3. Complete Phase 3: User Story 1 (get_K)
4. Complete Phase 4: User Story 2 (profit rate)
5. **STOP and VALIDATE**: Test K and profit rate independently
6. Deploy/demo if ready - this is minimum viable TRPF capability

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test K computation → Checkpoint
3. Add User Story 2 → Test profit rate → **MVP Complete!**
4. Add User Story 3 → Test OCC/e ratios → Enhanced metrics
5. Add User Story 4 → Test sensitivity → Robustness validation
6. Add User Story 5 → Test aggregation → Macro analysis
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2
   - Developer B: User Story 4 (after US1 core complete)
   - Developer C: User Story 5 (after US1 core complete)
3. Stories complete and integrate independently

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- TDD: Write failing tests before implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All formulas from TVT Sections 3.6-3.8, 5.2
