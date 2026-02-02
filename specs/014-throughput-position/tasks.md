# Tasks: Throughput Position and Domestic Value Geography

**Input**: Design documents from `/specs/014-throughput-position/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included per project TDD standards (Red-Green-Refactor cycle).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

## Path Conventions

- **Single project**: `src/babylon/`, `tests/` at repository root
- Source: `src/babylon/economics/throughput/`
- Tests: `tests/unit/economics/throughput/`, `tests/integration/economics/`

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure and shared types

- [ ] T001 Create `src/babylon/economics/throughput/` package directory with `__init__.py`
- [ ] T002 [P] Create `src/babylon/economics/throughput/types.py` with ThroughputMetrics and WageShareEstimate Pydantic models
- [ ] T003 [P] Create `tests/unit/economics/throughput/__init__.py` test package structure
- [ ] T004 [P] Create `tests/integration/economics/__init__.py` if not exists

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: US1 and US2 depend on these data sources

### Data Source Protocols

- [ ] T005 [P] Create `BEACountyGDPSource` protocol in `src/babylon/economics/throughput/data_sources.py`
- [ ] T006 [P] Create `QCEWCountyNAICSSource` protocol in `src/babylon/economics/throughput/data_sources.py`

### BEA County GDP Loader (D-002)

- [ ] T007 Create `src/babylon/data/loaders/bea_cagdp1.py` BEA CAGDP1 county GDP loader
  - Must use "chained 2017 dollars" (LineCode 1, real GDP)
  - Handle BEA API authentication
  - Return NoDataSentinel for missing counties
- [ ] T008 Write unit tests for BEA loader in `tests/unit/data/loaders/test_bea_cagdp1.py`

### NAICS Depth Mapping (FR-003)

- [ ] T009 Create `src/babylon/economics/throughput/naics_depth.py` with NAICS_DEPTH_MAPPING constant
  - Copy from `specs/014-throughput-position/contracts/naics_depth_mapping.py`
  - Implement `get_depth()` and `validate_depth()` functions
- [ ] T010 Write unit tests for NAICS mapping in `tests/unit/economics/throughput/test_naics_depth.py`
  - Test all 20+ NAICS sector mappings
  - Test unknown NAICS code returns None
  - Test depth validation bounds [0.0, 5.0]

**Checkpoint**: Foundation ready - BEA loader works, NAICS mapping complete, data source protocols defined

______________________________________________________________________

## Phase 3: User Story 1 - Compute County Throughput Position (Priority: P1) 🎯 MVP

**Goal**: Compute throughput intensity (τ_through) and position (π) for any US county

**Independent Test**: Compute τ_through and π for Oakland County (26125) and Wayne County (26163), validate Oakland π > Wayne π

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Unit test for τ_through computation in `tests/unit/economics/throughput/test_calculator.py`
  - Test formula: τ_through = GDP / (employment × 2080)
  - Test with mock GDP and employment values
  - Test NoDataSentinel propagation when GDP unavailable
  - Test NoDataSentinel propagation when employment unavailable
- [ ] T012 [P] [US1] Unit test for π computation in `tests/unit/economics/throughput/test_calculator.py`
  - Test formula: π = τ_through / τ_national
  - Test π returns NoDataSentinel when MELT unavailable (FR-006)
  - Test τ_through still computed when MELT unavailable
- [ ] T013 [US1] Integration test for Detroit validation in `tests/integration/economics/test_throughput_validation.py`
  - Test Oakland (26125) π > Wayne (26163) π for year 2022

### Implementation for User Story 1

- [ ] T014 [US1] Create `ThroughputCalculator` protocol in `src/babylon/economics/throughput/calculator.py`
  - Copy interface from `specs/014-throughput-position/contracts/throughput_calculator.py`
- [ ] T015 [US1] Implement `DefaultThroughputCalculator` in `src/babylon/economics/throughput/calculator.py`
  - Inject BEACountyGDPSource and QCEWCountyNAICSSource
  - Inject optional MELTCalculator from Feature 013
  - Implement `compute_throughput_intensity()` method (FR-001)
  - Implement `compute_throughput_position()` method (FR-002)
  - Implement `compute_metrics()` method returning ThroughputMetrics
- [ ] T016 [US1] Add sanity range validation per FR-008
  - τ_through: warn if outside $10-500/hour
  - π: warn if outside 0.2-3.0
- [ ] T017 [US1] Handle NoDataSentinel propagation per FR-007
  - Return ThroughputMetrics | NoDataSentinel union type
  - Include descriptive reason in NoDataSentinel
- [ ] T018 [US1] Export US1 components in `src/babylon/economics/throughput/__init__.py`

**Checkpoint**: τ_through and π computable for any county. Detroit validation passes.

______________________________________________________________________

## Phase 4: User Story 2 - Calculate Supply Chain Depth (Priority: P1)

**Goal**: Compute employment-weighted average supply chain depth (D) for any county

**Independent Test**: Compute D for New York County (36061), verify D > 4.0 (finance-heavy)

### Tests for User Story 2

- [ ] T019 [P] [US2] Unit test for D computation in `tests/unit/economics/throughput/test_supply_chain.py`
  - Test formula: D = Σ(employment × depth) / Σ employment
  - Test with mock NAICS employment distribution
  - Test D in range [0.0, 5.0]
  - Test NoDataSentinel when no NAICS data
- [ ] T020 [P] [US2] Unit test for sector employment retrieval in `tests/unit/economics/throughput/test_supply_chain.py`
  - Test get_sector_employment() returns dict[str, int]
  - Test suppressed sectors excluded

### Implementation for User Story 2

- [ ] T021 [US2] Create `SupplyChainAnalyzer` protocol in `src/babylon/economics/throughput/supply_chain.py`
  - Copy interface from `specs/014-throughput-position/contracts/supply_chain_analyzer.py`
- [ ] T022 [US2] Implement `DefaultSupplyChainAnalyzer` in `src/babylon/economics/throughput/supply_chain.py`
  - Inject QCEWCountyNAICSSource
  - Implement `compute_depth()` method (FR-004)
  - Implement `get_naics_depth()` method using NAICS_DEPTH_MAPPING
  - Implement `get_sector_employment()` method
- [ ] T023 [US2] Add depth validation per FR-008
  - ValueError if computed D outside [0.0, 5.0]
- [ ] T024 [US2] Add partial data handling
  - Flag as partial estimate if some NAICS sectors suppressed
  - Include data quality indicator in ThroughputMetrics
- [ ] T025 [US2] Export US2 components in `src/babylon/economics/throughput/__init__.py`

**Checkpoint**: D computable for any county. Finance centers show D > 4.0.

______________________________________________________________________

## Phase 5: User Story 3 - Estimate Wage Share by Industry (Priority: P2)

**Goal**: Compute wage share proxy (λ_proxy) for industry-county combinations

**Independent Test**: Compute λ for retail (NAICS 44) in Wayne County, verify λ < 0.15 (Walmart effect)

### Tests for User Story 3

- [ ] T026 [P] [US3] Unit test for λ_proxy computation in `tests/unit/economics/throughput/test_supply_chain.py`
  - Test formula: λ_proxy = avg_wage / τ_through
  - Test λ_proxy in range [0.0, 1.0]
  - Test λ_proxy > 1.0 flags data quality issue
- [ ] T027 [P] [US3] Unit test for WageShareEstimate type in `tests/unit/economics/throughput/test_types.py`
  - Test confidence level assignment (high/medium/low)

### Implementation for User Story 3

- [ ] T028 [US3] Extend `SupplyChainAnalyzer` with `compute_wage_share_proxy()` method (FR-005)
  - Calculate λ_proxy = avg_wage / τ_through
  - Return WageShareEstimate with confidence level
  - Flag if λ_proxy > 1.0 (data quality issue per FR-008)
- [ ] T029 [US3] Add confidence level logic
  - High: complete NAICS data, no suppression
  - Medium: partial NAICS data
  - Low: significant suppression or small county

**Checkpoint**: λ_proxy computable. Retail λ < 0.15 validated.

______________________________________________________________________

## Phase 6: User Story 4 - Analyze Throughput-Class Correlation (Priority: P2)

**Goal**: Validate that (π × λ) correlates with LA share from Feature 013

**Independent Test**: Correlation coefficient r > 0.4 across available counties

### Tests for User Story 4

- [ ] T030 [US4] Integration test for π × λ correlation in `tests/integration/economics/test_throughput_validation.py`
  - Load LA share from Feature 013 ClassPositionClassifier
  - Compute π and λ for sample counties
  - Test Pearson correlation > 0.4

### Implementation for User Story 4

- [ ] T031 [US4] Create correlation analysis utility in `src/babylon/economics/throughput/analysis.py`
  - `correlate_throughput_with_class()` function
  - Accepts list of county FIPS codes
  - Returns correlation coefficient and p-value
- [ ] T032 [US4] Integrate with Feature 013 ClassPositionClassifier
  - Import from `babylon.economics.melt`
  - Handle case where Feature 013 unavailable
- [ ] T033 [US4] Add SC-005 validation test in `tests/integration/economics/test_throughput_validation.py`

**Checkpoint**: Throughput-class correlation validated (r > 0.4).

______________________________________________________________________

## Phase 7: User Story 5 - Track Commuter Flows (Priority: P3 - Future Enhancement)

**Goal**: Integrate LODES commuter flow data for residence-work mismatch analysis

**Status**: DEFERRED - Marked as FE-002 in spec.md

### Placeholder Tasks (Future)

- [ ] T034 [US5] [FUTURE] Define LODESDataSource protocol
- [ ] T035 [US5] [FUTURE] Implement LODES data loader
- [ ] T036 [US5] [FUTURE] Add commuter-adjusted throughput calculation

**Note**: US5 is out of scope for MVP. These tasks are placeholders for FE-002.

______________________________________________________________________

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

### Batch Processing (SC-001)

- [ ] T037 Implement batch county computation in `ThroughputCalculator`
  - `compute_all_counties(year: int)` method
  - Target: 3,000+ counties
  - Performance target: <30s total

### Documentation

- [ ] T038 [P] Update `src/babylon/economics/__init__.py` to export throughput module
- [ ] T039 [P] Validate quickstart.md examples work end-to-end
- [ ] T040 [P] Add module docstrings with Sphinx-compatible RST

### Validation Tests (SC-001 through SC-007)

- [ ] T041 [P] Add SC-001 test: 3,000+ counties computed without error
- [ ] T042 [P] Add SC-003 test: D ranking (finance > manufacturing > extraction)
- [ ] T043 [P] Add SC-004 test: high-π counties → higher average wages
- [ ] T044 [P] Add SC-006 test: 100% edge case handling without crashes
- [ ] T045 [P] Add SC-007 test: national retail λ < 0.15

### Code Quality

- [ ] T046 Run `mise run check` (lint + format + typecheck + test:unit)
- [ ] T047 Run `mise run test:int` for integration tests

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────┐
                                     ▼
Phase 2: Foundational ───────────────┼──► BLOCKS ALL USER STORIES
                                     │
              ┌──────────────────────┴──────────────────────┐
              ▼                      ▼                      ▼
Phase 3: US1 (P1)          Phase 4: US2 (P1)      Phase 5: US3 (P2)
  │                          │                      │
  ▼                          ▼                      ▼
  [τ_through, π]             [D]                    [λ_proxy]
                                     │
                                     ▼
                           Phase 6: US4 (P2)
                             [Correlation]
                                     │
                                     ▼
                           Phase 8: Polish
```

### User Story Dependencies

- **US1 (P1)**: Requires Foundational (T005-T010). Independent of US2.
- **US2 (P1)**: Requires Foundational (T009-T010 for NAICS mapping). Independent of US1.
- **US3 (P2)**: Requires US1 (τ_through) and US2 (sector analysis)
- **US4 (P2)**: Requires US3 (λ_proxy) and Feature 013 integration
- **US5 (P3)**: DEFERRED - Future enhancement

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD Red phase)
2. Protocols/interfaces before implementations
3. Core computation before validation logic
4. Unit tests before integration tests

### Parallel Opportunities

**Phase 1** (all parallel):
- T002, T003, T004 can run simultaneously

**Phase 2** (mostly parallel):
- T005, T006 (protocols) can run in parallel
- T007, T008 (BEA loader) sequential
- T009, T010 (NAICS mapping) sequential

**After Foundational**:
- US1 and US2 can proceed in parallel (different files, no shared state)
- US3 depends on both US1 and US2

**Phase 8** (all parallel):
- T038-T045 can run in parallel

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (τ_through, π)
4. Complete Phase 4: US2 (D)
5. **STOP and VALIDATE**: Detroit validation passes (Oakland > Wayne)
6. Deploy MVP - basic throughput metrics available

### Full Implementation

1. MVP (US1 + US2)
2. Add US3 (λ_proxy) - enables wage share analysis
3. Add US4 (correlation) - validates theoretical framework
4. Polish phase - batch processing, documentation
5. Future: US5 when LODES integration needed

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story independently testable after completion
- Commit after each task or logical group
- All tests use `@pytest.mark.unit` or `@pytest.mark.integration` markers
- NoDataSentinel propagation is critical - no silent failures
