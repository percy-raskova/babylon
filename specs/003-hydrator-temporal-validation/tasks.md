# Tasks: Hydrator Temporal Validation & Deindustrialization Signals

**Input**: Design documents from `/specs/003-hydrator-temporal-validation/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included per project TDD requirements (CLAUDE.md: "We use Test Driven Development").

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Per plan.md source structure:

- Source: `src/babylon/economics/temporal/`
- Calibration: `src/babylon/economics/calibration/`
- Unit tests: `tests/unit/economics/temporal/`
- Integration tests: `tests/integration/economics/`

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure and shared Pydantic models

- [x] T001 Create temporal module directory structure at `src/babylon/economics/temporal/` (verified 2026-07-08: src/babylon/economics/temporal/ package (10 modules))
- [x] T002 Create calibration module directory structure at `src/babylon/economics/calibration/` (verified 2026-07-08: src/babylon/economics/calibration/ (__init__.py, thresholds.py))
- [x] T003 [P] Create test directory structure at `tests/unit/economics/temporal/` (verified 2026-07-08: tests/unit/economics/temporal/ dir + __init__.py)
- [x] T004 [P] Add temporal module exports to `src/babylon/economics/__init__.py` (verified 2026-07-08: src/babylon/economics/__init__.py:135-143)

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and enums that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Models (from data-model.md)

- [x] T005 Implement `DetectionMethod` enum in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:42 DetectionMethod)
- [x] T006 [P] Implement `AnomalyFlag` model in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:61 AnomalyFlag)
- [x] T007 [P] Implement `AnomalyThresholdConfig` model with `fallback_threshold` property in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:184; fallback_threshold :231)
- [x] T008 Implement `TemporalTransition` model with `is_anomalous` property in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:101; is_anomalous :178)
- [x] T009 [P] Implement `SmoothedCoefficientSeries` model with `variance_reduction` property in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:240; variance_reduction :309)
- [x] T010 [P] Implement `DeindustrializationSignal` model with `core_declining`/`core_stagnating` properties in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:326; core_declining :393, core_stagnating :398)
- [x] T011 [P] Implement `TransitionAnnotation` model in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:404)
- [x] T012 Implement `TemporalValidationReport` model with computed properties (`anomalous_transitions`, `flags_by_year`, `systemic_shock_years`) in `src/babylon/economics/temporal/models.py` (verified 2026-07-08: src/babylon/economics/temporal/models.py:448; computed properties :515,:520,:530)

### Model Unit Tests

- [x] T013 [P] Unit tests for `DetectionMethod` enum in `tests/unit/economics/temporal/test_models.py` (verified 2026-07-08: tests/unit/economics/temporal/test_models.py:33)
- [x] T014 [P] Unit tests for `AnomalyThresholdConfig.fallback_threshold` logic in `tests/unit/economics/temporal/test_models.py` (verified 2026-07-08: tests/unit/economics/temporal/test_models.py:170-178)
- [x] T015 [P] Unit tests for `TemporalTransition` validation (year_to = year_from + 1) in `tests/unit/economics/temporal/test_models.py` (verified 2026-07-08: tests/unit/economics/temporal/test_models.py:120)
- [x] T016 [P] Unit tests for `SmoothedCoefficientSeries` validation (alpha ∈ [0,1], equal list lengths) in `tests/unit/economics/temporal/test_models.py` (verified 2026-07-08: tests/unit/economics/temporal/test_models.py:214,:250)
- [x] T017 [P] Unit tests for `DeindustrializationSignal` validation (year_range[0] < year_range[1]) in `tests/unit/economics/temporal/test_models.py` (verified 2026-07-08: tests/unit/economics/temporal/test_models.py:346)

### Protocol Definitions

- [x] T018 Copy protocol definitions from `specs/003-hydrator-temporal-validation/contracts/temporal_validation.py` to `src/babylon/economics/temporal/protocols.py` (verified 2026-07-08: src/babylon/economics/temporal/protocols.py (all 8 protocols incl. AnnotationManager))

**Checkpoint**: Foundation ready - all models validated, protocols defined

______________________________________________________________________

## Phase 3: User Story 1 - Detect Deindustrialization Signal (Priority: P1) 🎯 MVP

**Goal**: Compare Dept I trajectories between Wayne (Detroit core) and Oakland (affluent suburb) to validate deindustrialization pattern

**Independent Test**: Hydrate tensors for Wayne (26163) and Oakland (26125) across available years, compute Dept I trajectory slopes, verify divergence

**Reference**:

- spec.md: US1 acceptance scenarios
- data-model.md: `DeindustrializationSignal` entity
- contracts/temporal_validation.py: `DeindustrializationDetector` protocol
- research.md: Linear trend estimation methodology

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T019 [P] [US1] Unit test for linear trend computation in `tests/unit/economics/temporal/test_signals.py` (verified 2026-07-08: tests/unit/economics/temporal/test_signals.py:18)
- [x] T020 [P] [US1] Unit test for signal detection criteria (core ≤ 0, core < suburb) in `tests/unit/economics/temporal/test_signals.py` (verified 2026-07-08: tests/unit/economics/temporal/test_signals.py:85)
- [ ] T021 [US1] Integration test for Wayne vs Oakland comparison in `tests/integration/economics/test_temporal_validation.py` (left unchecked 2026-07-08: tests/integration/economics/test_temporal_validation.py does not exist)

### Implementation for User Story 1

- [x] T022 [US1] Implement `compute_trend()` helper (linear regression slope) in `src/babylon/economics/temporal/signals.py` (verified 2026-07-08: src/babylon/economics/temporal/signals.py:25 compute_trend)
  - Reference: research.md "Linear Trend Estimation" section
- [x] T023 [US1] Implement `DeindustrializationDetectorImpl.detect_deindustrialization()` in `src/babylon/economics/temporal/signals.py` (verified 2026-07-08: src/babylon/economics/temporal/signals.py:74,:94)
  - Must satisfy `DeindustrializationDetector` protocol from T018
  - Takes core_fips, suburb_fips, years sequence
  - Hydrates tensors using MarxianHydrator
  - Computes Dept I share trend slopes via `compute_trend()`
  - Returns `DeindustrializationSignal` with signal_detected and signal_strength
- [x] T024 [US1] Add Detroit metro constants (WAYNE_FIPS, OAKLAND_FIPS, MACOMB_FIPS) to `tests/constants.py` if not present (verified 2026-07-08: tests/constants.py:117-141 DetroitMetro)
- [ ] T025 [US1] Validate SC-001: Wayne Dept I share decline/stagnation relative to Oakland in ≥80% of year-pairs (left unchecked 2026-07-08: no SC-001 (>=80% year-pair) validation test/artifact exists)

**Checkpoint**: US1 complete - deindustrialization signal detection works independently

______________________________________________________________________

## Phase 4: User Story 2 - Flag Anomalous Year-over-Year Jumps (Priority: P1)

**Goal**: Detect statistically anomalous YoY changes using tiered threshold system (Z-score → empirical → bootstrap)

**Independent Test**: Create multi-year tensor series with known anomaly, verify flag raised with correct detection method

**Reference**:

- spec.md: US2 acceptance scenarios, FR-001, FR-002
- data-model.md: `TemporalTransition`, `AnomalyFlag`, `AnomalyThresholdConfig`
- contracts/temporal_validation.py: `TransitionComputer`, `AnomalyDetector` protocols
- research.md: Z-score computation, rolling statistics

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T026 [P] [US2] Unit test for YoY delta percentage computation in `tests/unit/economics/temporal/test_transitions.py` (verified 2026-07-08: tests/unit/economics/temporal/test_transitions.py:42)
- [x] T027 [P] [US2] Unit test for Z-score computation with rolling window in `tests/unit/economics/temporal/test_anomaly.py` (verified 2026-07-08: tests/unit/economics/temporal/test_anomaly.py:22)
- [x] T028 [P] [US2] Unit test for tiered detection method selection (Z_SCORE vs EMPIRICAL vs BOOTSTRAP) in `tests/unit/economics/temporal/test_anomaly.py` (verified 2026-07-08: tests/unit/economics/temporal/test_anomaly.py:85)
- [ ] T029 [US2] Integration test for anomaly detection across multi-year series in `tests/integration/economics/test_temporal_validation.py` (left unchecked 2026-07-08: tests/integration/economics/test_temporal_validation.py does not exist)

### Implementation for User Story 2

- [x] T030 [US2] Implement `TransitionComputerImpl.compute_transition()` in `src/babylon/economics/temporal/transitions.py` (verified 2026-07-08: src/babylon/economics/temporal/transitions.py:52,:69)
  - Must satisfy `TransitionComputer` protocol from T018
  - Takes fips, year_from, year_to
  - Hydrates both years' tensors
  - Computes delta_total_v, delta_dept_shares, delta_profit_rate as percentages
  - Returns `TemporalTransition` (z_scores and flags_raised populated by detector)
- [x] T031 [US2] Implement `rolling_zscore()` helper in `src/babylon/economics/temporal/anomaly.py` (verified 2026-07-08: src/babylon/economics/temporal/anomaly.py:36)
  - Reference: research.md "Z-Score Computation" section with NumPy implementation
  - Returns None for insufficient history (< window size)
- [x] T032 [US2] Implement `AnomalyDetectorImpl.compute_z_scores()` in `src/babylon/economics/temporal/anomaly.py` (verified 2026-07-08: src/babylon/economics/temporal/anomaly.py:302)
  - Must satisfy `AnomalyDetector` protocol from T018
  - Uses `rolling_zscore()` for each component
- [x] T033 [US2] Implement `AnomalyDetectorImpl.detect_anomalies()` in `src/babylon/economics/temporal/anomaly.py` (verified 2026-07-08: src/babylon/economics/temporal/anomaly.py:177; check_threshold_violation :103; select_detection_method :76)
  - Implements tiered threshold logic from FR-002:
    - Primary: Z-score with k=2.5, 5-year rolling (if ≥5 years history)
    - Fallback: Empirical 95th percentile (if \<5 years, threshold computed)
    - Bootstrap: 15% threshold (if national threshold not calibrated)
  - Sets `detection_method` on each `TemporalTransition`
  - Creates `AnomalyFlag` for each threshold violation
- [ ] T034 [US2] Validate SC-002: ≤5% false positive rate on historical QCEW data (excluding known shocks) (left unchecked 2026-07-08: no SC-002 false-positive-rate validation on QCEW data)

**Checkpoint**: US2 complete - anomaly detection works independently

______________________________________________________________________

## Phase 5: User Story 3 - Apply α-Smoothed Coefficients (Priority: P2)

**Goal**: Provide EWMA-smoothed coefficients for simulation stability per Constitution II.4

**Independent Test**: Apply smoothing with α=0.3 to known series, verify variance reduction ≥40%

**Reference**:

- spec.md: US3 acceptance scenarios, FR-004
- data-model.md: `SmoothedCoefficientSeries`
- contracts/temporal_validation.py: `CoefficientSmoother` protocol
- research.md: α-Smoothing (EWMA) formula and variance reduction

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T035 [P] [US3] Unit test for EWMA formula correctness in `tests/unit/economics/temporal/test_smoothing.py` (verified 2026-07-08: tests/unit/economics/temporal/test_smoothing.py:21)
- [x] T036 [P] [US3] Unit test for α=0 boundary (full smoothing, output = first value) in `tests/unit/economics/temporal/test_smoothing.py` (verified 2026-07-08: tests/unit/economics/temporal/test_smoothing.py:68)
- [x] T037 [P] [US3] Unit test for α=1 boundary (no smoothing, output = raw values) in `tests/unit/economics/temporal/test_smoothing.py` (verified 2026-07-08: tests/unit/economics/temporal/test_smoothing.py:85)
- [x] T038 [P] [US3] Unit test for single year edge case (returns raw with warning) in `tests/unit/economics/temporal/test_smoothing.py` (verified 2026-07-08: tests/unit/economics/temporal/test_smoothing.py:102)
- [ ] T039 [US3] Unit test for gap handling (missing years flagged in metadata) in `tests/unit/economics/temporal/test_smoothing.py` (left unchecked 2026-07-08: no gap/missing-year test in test_smoothing.py)

### Implementation for User Story 3

- [x] T040 [US3] Implement `ewma()` helper function in `src/babylon/economics/temporal/smoothing.py` (verified 2026-07-08: src/babylon/economics/temporal/smoothing.py:30 ewma)
  - Formula: S_t = α * X_t + (1 - α) * S\_{t-1}
  - S_0 = X_0 (first value)
- [x] T041 [US3] Implement `CoefficientSmootherImpl.smooth_coefficients()` in `src/babylon/economics/temporal/smoothing.py` (verified 2026-07-08: src/babylon/economics/temporal/smoothing.py:64,:82)
  - Must satisfy `CoefficientSmoother` protocol from T018
  - Takes fips, years, coefficient name, alpha
  - Hydrates tensors and extracts coefficient values
  - Applies `ewma()` to compute smoothed series
  - Handles gaps (missing years) with metadata flag
  - Logs warning for single-year series
  - Returns `SmoothedCoefficientSeries`
- [~] T042 [US3] Validate SC-003: Variance reduction ≥40% with α=0.3 across Detroit metro 2015-2022 (partial 2026-07-08: test_smoothing.py:146 asserts synthetic variance ratio <0.6, but no >=40% validation across real Detroit-metro 2015-2022 data)
- [ ] T043 [US3] Validate SC-006: α-smoothing adds \<10% overhead to tensor retrieval for 10-year series (left unchecked 2026-07-08: no SC-006 (<10% alpha-smoothing overhead) performance test)

**Checkpoint**: US3 complete - coefficient smoothing works independently

______________________________________________________________________

## Phase 6: Report Generation & Calibration

**Goal**: Combine all components into aggregate report (FR-007) and calibration artifact (FR-008)

**Reference**:

- spec.md: FR-006 (annotations), FR-007 (report), FR-008 (calibration)
- data-model.md: `TemporalValidationReport`, `TransitionAnnotation`
- contracts/temporal_validation.py: `ReportGenerator`, `ThresholdCalibrator` protocols

### Tests

- [x] T044 [P] Unit test for `TemporalValidationReport` computed properties in `tests/unit/economics/temporal/test_reports.py` (verified 2026-07-08: tests/unit/economics/temporal/test_reports.py:28)
- [x] T045 [P] Unit test for threshold calibration persistence in `tests/unit/economics/calibration/test_thresholds.py` (verified 2026-07-08: tests/unit/economics/calibration/test_thresholds.py:38)
- [ ] T046 Integration test for full report generation in `tests/integration/economics/test_temporal_validation.py` (left unchecked 2026-07-08: tests/integration/economics/test_temporal_validation.py does not exist)
- [x] T060 [P] Unit test for `AnnotationManager` CRUD operations in `tests/unit/economics/temporal/test_annotations.py` (verified 2026-07-08: tests/unit/economics/temporal/test_annotations.py:17)

### Implementation

- [x] T047 Implement `ReportGeneratorImpl.generate_report()` in `src/babylon/economics/temporal/reports.py` (verified 2026-07-08: src/babylon/economics/temporal/reports.py:46,:66)
  - Must satisfy `ReportGenerator` protocol from T018
  - Orchestrates: transitions, anomaly detection, smoothing, signals
  - Returns `TemporalValidationReport` with all outputs
- [~] T048 Implement `ThresholdCalibratorImpl` in `src/babylon/economics/calibration/thresholds.py` (partial 2026-07-08: persist_threshold/load_threshold implemented in src/babylon/economics/calibration/thresholds.py, but calibrate_national_threshold is a placeholder returning 0.15 (:106-107 TODO Phase 7))
  - `calibrate_national_threshold()`: Compute 95th percentile of YoY changes across all counties
  - `persist_threshold()`: Save to calibration artifact (JSON file)
  - `load_threshold()`: Load from artifact
- [ ] T049 Validate SC-007: National 95th percentile threshold computed and documented in calibration artifact (left unchecked 2026-07-08: SC-007 national p95 not computed (calibrate stub) and no threshold_calibration.json artifact exists)
- [~] T059 Implement `AnnotationManagerImpl` in `src/babylon/economics/temporal/annotations.py` (partial 2026-07-08: src/babylon/economics/temporal/annotations.py:29 AnnotationManagerImpl annotate/get/delete, but in-memory dict only (:41) — no JSON persistence to calibration dir as required)
  - Must satisfy `AnnotationManager` protocol from contracts/temporal_validation.py
  - `annotate_transition()`: Create TransitionAnnotation with generated key and timestamp
  - `get_annotations()`: Retrieve annotations with optional fips/year filters
  - `delete_annotation()`: Remove annotation by transition_key
  - Persist annotations to JSON file in calibration directory

**Checkpoint**: Report and calibration complete

______________________________________________________________________

## Phase 7: Integration & TemporalValidator Facade

**Goal**: Combine all implementations into unified `TemporalValidator` class satisfying combined protocol

### Implementation

- [x] T050 Implement `TemporalValidator` facade class in `src/babylon/economics/temporal/validator.py` (verified 2026-07-08: src/babylon/economics/temporal/validator.py:40 TemporalValidatorFacade (name drift from spec's TemporalValidator; same composition))
  - Composes: `TransitionComputerImpl`, `AnomalyDetectorImpl`, `CoefficientSmootherImpl`, `DeindustrializationDetectorImpl`, `ReportGeneratorImpl`
  - Satisfies `TemporalValidator` combined protocol from T018
  - Injects `MarxianHydrator` dependency via constructor
- [x] T051 Update `src/babylon/economics/temporal/__init__.py` with public API exports (verified 2026-07-08: src/babylon/economics/temporal/__init__.py:67-104 __all__)
- [ ] T052 Integration test for `TemporalValidator` end-to-end in `tests/integration/economics/test_temporal_validation.py` (left unchecked 2026-07-08: tests/integration/economics/test_temporal_validation.py does not exist)

**Checkpoint**: Unified interface complete

______________________________________________________________________

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T053 Validate SC-004: Analysts can resolve 90% of flags within 5 minutes using metadata (unverifiable — manual UX gate (SC-004 analyst resolution time), no durable artifact)
- [ ] T054 Validate SC-005: Deindustrialization signal tests pass across all available QCEW years for Wayne/Oakland (left unchecked 2026-07-08: no QCEW integration test validating Wayne/Oakland signal across all years)
- [ ] T055 Run quickstart.md examples as integration tests (left unchecked 2026-07-08: no quickstart-derived integration tests; quickstart.md API mismatches actual TemporalValidatorFacade)
- [x] T056 [P] Add docstrings to all public classes and functions (Sphinx-compatible RST format) (verified 2026-07-08: RST docstrings across temporal modules (e.g. src/babylon/economics/temporal/models.py, signals.py, anomaly.py))
- [x] T057 [P] Update `src/babylon/economics/__init__.py` to export temporal validation public API (verified 2026-07-08: src/babylon/economics/__init__.py:135-143 imports, :208-214 __all__)
- [ ] T058 Run full test suite and verify all markers pass (`@pytest.mark.math`, `@pytest.mark.integration`) (unverifiable — ephemeral gate, no durable artifact)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

```mermaid
graph TD
    P1[Phase 1: Setup] --> P2[Phase 2: Foundational]
    P2 --> P3[Phase 3: US1 Deindustrialization]
    P2 --> P4[Phase 4: US2 Anomaly Detection]
    P2 --> P5[Phase 5: US3 α-Smoothing]
    P3 --> P6[Phase 6: Report & Calibration]
    P4 --> P6
    P5 --> P6
    P6 --> P7[Phase 7: Integration]
    P7 --> P8[Phase 8: Polish]
```

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase
  - US1, US2, US3 can proceed in parallel after Phase 2
- **Report/Calibration (Phase 6)**: Depends on US1, US2, US3 completion
- **Integration (Phase 7)**: Depends on Phase 6
- **Polish (Phase 8)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Foundational - uses `MarxianHydrator.hydrate()`, `DeindustrializationSignal` model
- **User Story 2 (P1)**: Independent after Foundational - uses `MarxianHydrator.hydrate()`, `TemporalTransition` model, `AnomalyFlag` model
- **User Story 3 (P2)**: Independent after Foundational - uses `MarxianHydrator.hydrate()`, `SmoothedCoefficientSeries` model

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
1. Helper functions before main implementation
1. Protocol implementation before validation
1. Success criteria validation last

### Parallel Opportunities

**Phase 2 (Foundational) - Models can be parallelized:**

```bash
# Run in parallel (different models, same file but independent):
T006, T007, T009, T010, T011  # Independent model implementations
T013, T014, T015, T016, T017  # Independent unit tests
```

**Phases 3-5 (User Stories) - Entire phases can be parallelized:**

```bash
# After Phase 2 completes, all three can run in parallel:
Phase 3 (US1): T019-T025
Phase 4 (US2): T026-T034
Phase 5 (US3): T035-T043
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
1. Complete Phase 2: Foundational (models only, minimal)
1. Complete Phase 3: User Story 1 (deindustrialization signal)
1. **STOP and VALIDATE**: Test Wayne vs Oakland comparison
1. If signal detected correctly → MVP validated

### Incremental Delivery

1. Setup + Foundational → Foundation ready
1. Add US1 (Deindustrialization) → Test → Core validation passes
1. Add US2 (Anomaly Detection) → Test → Data quality layer added
1. Add US3 (α-Smoothing) → Test → Coefficient stability added
1. Add Report/Calibration → Test → Full feature complete
1. Integration + Polish → Production ready

### Parallel Team Strategy

With 3 developers:

1. Team completes Setup + Foundational together
1. Once Foundational done:
   - Developer A: User Story 1 (T019-T025)
   - Developer B: User Story 2 (T026-T034)
   - Developer C: User Story 3 (T035-T043)
1. Reconvene for Phase 6-8 (sequential)

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after completion
- PRE-001 (QCEW data 2010-2024) is now loading - integration tests may be limited until complete
- Commit after each task or logical group
- Reference sections in data-model.md and research.md for implementation details
