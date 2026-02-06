# Tasks: Class Dynamics Engine

**Input**: Design documents from `/specs/016-class-dynamics-engine/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Included per TDD workflow (Red-Green-Refactor). Tests MUST be written and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Create package structure and initialize module

- [ ] T001 Create package directory `src/babylon/economics/dynamics/` and `__init__.py` with grouped `__all__` exports (initially empty, updated as modules are added)
- [ ] T002 Create test directory `tests/unit/economics/dynamics/` and empty `__init__.py`

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, protocols, data sources, and test infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] [Foundation] Write tests for ClassDistribution, EconomicConditions, TransitionRates, AccumulationResult, DispossessionRisk, SavingsRateSchedule frozen models in `tests/unit/economics/dynamics/test_types.py` — cover sum-to-one validation, field constraints, `dynamic_shares()`, `with_updated_dynamics()`, immutability
- [ ] T004 [P] [Foundation] Write tests for hardcoded national dispossession data (2007-2020 foreclosure, bankruptcy, eviction rates) in `tests/unit/economics/dynamics/test_hardcoded_data.py` — cover year range, rate bounds, crisis-year elevation
- [ ] T005 [P] [Foundation] Write tests for DefaultSavingsRateSchedule in `tests/unit/economics/dynamics/test_savings_schedule.py` — cover 5 ClassPosition rates, phi_adjustment capping, edge cases (zero wage, zero phi)
- [ ] T006 [P] [Foundation] Write tests for three-tier validation (Expected/Warning/Fail) in `tests/unit/economics/dynamics/test_validation.py` — cover transition rate ranges and class share ranges from research.md Section 7
- [ ] T007 [Foundation] Implement all frozen Pydantic types in `src/babylon/economics/dynamics/types.py` — ClassDistribution, EconomicConditions, TransitionRates, AccumulationResult, DispossessionRisk, SavingsRateSchedule per data-model.md entities
- [ ] T008 [Foundation] Implement all protocols in `src/babylon/economics/dynamics/data_sources.py` — DispossessionDataSource, SavingsRateSource (runtime-checkable Protocol classes per data-model.md), and define AccumulationCalculator, DispossessionCalculator, ClassTransitionEngine, CrisisAmplifier protocol stubs in their respective files (`accumulation.py`, `dispossession.py`, `transition_engine.py`, `crisis.py`) — protocols only, no implementations yet
- [ ] T009 [Foundation] Implement HardcodedNationalDispossessionSource in `src/babylon/economics/dynamics/hardcoded_data.py` — national averages by year (2007-2020) from research.md Section 3 tables, returns None for out-of-range years
- [ ] T010 [Foundation] Implement DefaultSavingsRateSchedule in `src/babylon/economics/dynamics/savings_schedule.py` — class-based step function (B=0.38, PB=0.20, LA=0.12, P=0.03, L=0.00) with phi_adjustment = min(phi_hour * 2080 / wage, 0.05) per research.md Section 4
- [ ] T011 [Foundation] Implement three-tier validation functions in `src/babylon/economics/dynamics/validation.py` — `validate_transition_rates()` and `validate_class_shares()` per research.md Section 7 ranges, following gamma/validation.py pattern
- [ ] T012 [Foundation] Create test fixtures and mock data sources in `tests/unit/economics/dynamics/conftest.py` — mock DispossessionDataSource, mock SavingsRateSource, fixture ClassDistribution/EconomicConditions instances for stable/crisis scenarios, following gamma/conftest.py pattern
- [ ] T013 [Foundation] Update `src/babylon/economics/dynamics/__init__.py` with exports for all foundational types and implementations

**Checkpoint**: All foundational types pass tests. Data sources and validation operational. Test infrastructure ready for user stories.

______________________________________________________________________

## Phase 3: User Story 1 - Compute Wealth Accumulation Rate (Priority: P1)

**Goal**: Compute annual wealth accumulation rate from wage, consumption, savings rate, and imperial rent subsidy. Determine how fast workers accumulate or lose wealth.

**Independent Test**: Compute accumulation rate for known wage/consumption/imperial-rent combinations. Validate: positive accumulation when wages > consumption, zero at near-subsistence, negative during wealth destruction.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [US1] Write tests for AccumulationCalculator protocol compliance and DefaultAccumulationCalculator in `tests/unit/economics/dynamics/test_accumulation.py` — cover:
  - Scenario 1: $60k wage, $50k consumption, 15% savings -> ~$1,500 annual gain (FR-001, SC-006)
  - Scenario 2: $40k wage, $39.5k near-subsistence -> near-zero gain
  - Scenario 3: Imperial rent subsidy comparison (with vs without phi_hour)
  - Scenario 4: Negative wealth shock (medical debt scenario)
  - Edge cases: zero wage, zero phi_hour, maximum phi_adjustment cap at 0.05

### Implementation for User Story 1

- [ ] T015 [US1] Implement AccumulationCalculator protocol and DefaultAccumulationCalculator in `src/babylon/economics/dynamics/accumulation.py` — constructor takes SavingsRateSchedule; `compute(wage, melt, phi_hour) -> AccumulationResult` per spec FR-001, FR-008
- [ ] T016 [US1] Update `__init__.py` exports with AccumulationCalculator and DefaultAccumulationCalculator

**Checkpoint**: Accumulation rate computation works independently. All 4 acceptance scenarios from spec US1 pass.

______________________________________________________________________

## Phase 4: User Story 2 - Assess Dispossession Risk (Priority: P1)

**Goal**: Compute composite dispossession risk from foreclosure, bankruptcy, and eviction rates. Distinguish which mechanisms affect which transition pathways.

**Independent Test**: Compute dispossession risk for known county-year data. Validate crisis years show elevated risk vs stable years. Validate NoDataSentinel returned for missing data.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [US2] Write tests for DispossessionCalculator protocol compliance and DefaultDispossessionCalculator in `tests/unit/economics/dynamics/test_dispossession.py` — cover:
  - Scenario 1: Stable year (2015) -> low composite risk
  - Scenario 2: Crisis year (2010) -> risk at least 2x stable baseline (SC-002)
  - Scenario 3: High eviction + low foreclosure -> eviction affects P->L, foreclosure affects LA->P (FR-006)
  - Scenario 4: Missing data source -> NoDataSentinel with specific missing source identified (FR-010)
  - Edge cases: all rates zero, all rates at maximum

### Implementation for User Story 2

- [ ] T018 [US2] Implement DispossessionCalculator protocol and DefaultDispossessionCalculator in `src/babylon/economics/dynamics/dispossession.py` — constructor takes DispossessionDataSource; `compute(fips, year, conditions) -> DispossessionRisk | NoDataSentinel` per spec FR-003, FR-006, FR-010
- [ ] T019 [US2] Update `__init__.py` exports with DispossessionCalculator and DefaultDispossessionCalculator

**Checkpoint**: Dispossession risk computation works independently. All 4 acceptance scenarios from spec US2 pass.

______________________________________________________________________

## Phase 5: User Story 3 - Simulate Class Distribution Transitions (Priority: P1)

**Goal**: Combine accumulation and dispossession into actual class share changes for one simulation period. Enforce sum-to-one invariant.

**Independent Test**: Start with known distribution, apply known conditions for one period. Validate output sums to 1.0, transitions match expected directions, shares non-negative.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020a [P] [US3] Write tests for precaritization rate computation (FR-015) and stabilization rate computation (FR-016) in `tests/unit/economics/dynamics/test_transition_engine.py` — cover:
  - Precaritization: higher unemployment + higher eviction -> higher precaritization rate
  - Precaritization: zero unemployment + zero eviction -> zero precaritization
  - Stabilization: low unemployment -> high stabilization rate (near base_stabilization)
  - Stabilization: high unemployment -> near-zero stabilization rate
  - Both: output rates within validation Expected/Warning bounds (research.md §7)
- [ ] T020b [US3] Write tests for ClassTransitionEngine protocol compliance and DefaultClassTransitionEngine in `tests/unit/economics/dynamics/test_transition_engine.py` — cover:
  - Scenario 1: Stable conditions -> small perturbations, sum = 1.0 (SC-001, SC-005)
  - Scenario 2: Crisis conditions -> LA decreases, lumpen increases
  - Scenario 3: Recovery conditions -> lumpen decreases, upward mobility (SC-004)
  - Scenario 4: Sum-to-one invariant check on all outputs (FR-004)
  - Scenario 5: Continuous flows, not discrete jumps (FR-013)
  - Edge cases: degenerate distribution (one class = 1.0), empty classes produce no flow, NoDataSentinel propagation from missing data

### Implementation for User Story 3

- [ ] T021 [US3] Implement ClassTransitionEngine protocol and DefaultClassTransitionEngine in `src/babylon/economics/dynamics/transition_engine.py` — constructor takes AccumulationCalculator, DispossessionCalculator, CrisisAmplifier; `simulate_transitions(dist, conditions) -> ClassDistribution | NoDataSentinel` per spec FR-002, FR-004, FR-005, FR-012, FR-013, FR-014. Apply flows per data-model.md state transition equations, normalize to sum=1.0
- [ ] T022 [US3] Update `__init__.py` exports with ClassTransitionEngine and DefaultClassTransitionEngine

**Checkpoint**: Full one-period transition simulation works. Sum-to-one invariant always holds. All 4 acceptance scenarios from spec US3 pass.

______________________________________________________________________

## Phase 6: User Story 4 - Model Crisis Amplification (Priority: P2)

**Goal**: Amplify transition rates during crisis periods via multiplicative amplifier (2.5x downward, 0.3x upward per FR-009).

**Independent Test**: Compare transition magnitudes under normal vs crisis conditions. Validate crisis produces multiplicative amplification of downward transitions.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T023 [US4] Write tests for CrisisAmplifier protocol compliance and DefaultCrisisAmplifier in `tests/unit/economics/dynamics/test_crisis.py` — cover:
  - Scenario 1: Crisis flag -> downward rates amplified by 2.5x, upward rates dampened to 0.3x (research.md Section 5)
  - Scenario 2: No crisis flag -> rates unchanged (passthrough)
  - Scenario 3: Multi-period crisis -> accelerating cumulative downward mobility (SC-002)
  - Edge cases: rates at boundary after amplification (clamped to [0, 1])

### Implementation for User Story 4

- [ ] T024 [US4] Implement CrisisAmplifier protocol and DefaultCrisisAmplifier in `src/babylon/economics/dynamics/crisis.py` — `amplify(rates, crisis) -> TransitionRates` per spec FR-009, research.md Section 5 (crisis_amplifier=2.5, recovery_dampener=0.3)
- [ ] T025 [US4] Update `__init__.py` exports with CrisisAmplifier and DefaultCrisisAmplifier

**Checkpoint**: Crisis amplification works independently and integrates with transition engine. SC-002 (2x transition magnitude during crisis) validated.

______________________________________________________________________

## Phase 7: User Story 5 - Validate Against Historical Class Composition (Priority: P3)

**Goal**: Run multi-year simulation from known starting distribution through historical conditions and validate output matches plausible class composition ranges.

**Independent Test**: Run dynamics engine from 2010 starting distribution through 2010-2019 economic conditions. Compare final distribution to expected ranges.

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [US5] Write multi-period simulation validation tests in `tests/unit/economics/dynamics/test_transition_engine.py` (append to existing) — cover:
  - Scenario 1: 2010-2019 simulation -> final distribution within SC-008 ranges (B 0.5-2%, PB 5-15%, LA 30-50%, P 25-45%, L 10-25%)
  - Scenario 2: 2008-2012 crisis -> LA declines, lumpen increases (directional match to Great Recession)
  - Scenario 3: Recovery years -> gradual upward mobility (SC-004)

### Implementation for User Story 5

- [ ] T027 [US5] Create multi-period simulation helper or test fixtures in `tests/unit/economics/dynamics/conftest.py` — generate EconomicConditions sequence for 2007-2020 using hardcoded data, enabling multi-year validation runs
- [ ] T028 [US5] Tune transition parameters if needed to achieve SC-008 plausible ranges — adjust only within validation Warning bounds from research.md Section 7

**Checkpoint**: Historical validation passes. Multi-period simulation produces plausible class distributions.

______________________________________________________________________

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, validation, and cleanup

- [ ] T029 [P] Run `poetry run mypy src/babylon/economics/dynamics/ --strict` and fix all type errors
- [ ] T030 [P] Run `poetry run ruff check src/babylon/economics/dynamics/` and fix all lint issues
- [ ] T031 [P] Verify all `__init__.py` exports match quickstart.md usage examples
- [ ] T032 Run full test suite: `poetry run pytest tests/unit/economics/dynamics/ -v` — all tests pass
- [ ] T033 Run quickstart.md code example as integration smoke test
- [ ] T034 Validate FR-011 (transition rate validation logging for anomalous values)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories
- **US1 Accumulation (Phase 3)**: Depends on Phase 2 (types, savings_schedule, conftest)
- **US2 Dispossession (Phase 4)**: Depends on Phase 2 (types, hardcoded_data, data_sources, conftest)
- **US3 Transitions (Phase 5)**: Depends on Phase 3 AND Phase 4 (needs both calculators)
- **US4 Crisis (Phase 6)**: Depends on Phase 2 (types only); integrates with Phase 5
- **US5 Validation (Phase 7)**: Depends on Phase 5 AND Phase 6 (needs full engine with crisis)
- **Polish (Phase 8)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)** and **US2 (P1)**: Can start in parallel after Phase 2
- **US3 (P1)**: Requires US1 + US2 complete (consumes both calculators)
- **US4 (P2)**: Can start after Phase 2, but integration requires US3
- **US5 (P3)**: Requires US3 + US4 complete (full engine needed)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD Red phase)
- Protocol before implementation (interface before concrete)
- Implementation before __init__.py export updates
- Story complete and green before moving to next priority

### Parallel Opportunities

- T003, T004, T005, T006 can all run in parallel (different test files)
- T007, T008, T009, T010, T011 implementation can partially parallelize (different source files)
- US1 (Phase 3) and US2 (Phase 4) can run in parallel after Phase 2
- US4 (Phase 6) implementation can start in parallel with US3 tests
- T029, T030, T031 Polish tasks can run in parallel

______________________________________________________________________

## Implementation Strategy

### Recommended: Incremental Delivery

1. Complete Phase 1: Setup -> Package exists
2. Complete Phase 2: Foundational -> All types, data, validation green
3. Complete Phase 3: US1 Accumulation -> **Validate independently**
4. Complete Phase 4: US2 Dispossession -> **Validate independently**
5. Complete Phase 5: US3 Transitions -> **Full engine MVP working**
6. Complete Phase 6: US4 Crisis -> **Crisis dynamics operational**
7. Complete Phase 7: US5 Validation -> **Historical plausibility confirmed**
8. Complete Phase 8: Polish -> **Production-ready**

### Task Count Summary

| Phase | Tasks | Parallel |
|-------|-------|----------|
| Setup | 2 | - |
| Foundational | 11 | T003-T006 [P] |
| US1 Accumulation | 3 | - |
| US2 Dispossession | 3 | - |
| US3 Transitions | 4 | T020a [P] |
| US4 Crisis | 3 | - |
| US5 Validation | 3 | - |
| Polish | 6 | T029-T031 [P] |
| **Total** | **35** | |
