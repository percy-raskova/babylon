# Tasks: Gamma (Visibility) Tensor

**Feature**: 015-gamma-visibility-tensor
**Input**: Design documents from `/specs/015-gamma-visibility-tensor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Unit tests are included following TDD approach (existing project pattern with `@pytest.mark.unit`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- Source: `src/babylon/economics/gamma/`
- Tests: `tests/unit/economics/gamma/`, `tests/integration/economics/`

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create gamma package structure and foundational types

- [X] T001 Create gamma package directory structure at `src/babylon/economics/gamma/`
- [X] T002 [P] Create package `__init__.py` with exports at `src/babylon/economics/gamma/__init__.py`
- [X] T003 [P] Create test package structure at `tests/unit/economics/gamma/__init__.py`

______________________________________________________________________

## Phase 2: Foundational (Types & Data Sources)

**Purpose**: Core types and protocols that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Define GammaIII Pydantic model in `src/babylon/economics/gamma/types.py`
- [X] T005 [P] Define GammaImport Pydantic model in `src/babylon/economics/gamma/types.py`
- [X] T006 [P] Define GammaBasket Pydantic model in `src/babylon/economics/gamma/types.py`
- [X] T007 [P] Define ShadowSubsidy Pydantic model in `src/babylon/economics/gamma/types.py`
- [X] T008 [P] Define ERDIData Pydantic model with MVP_ERDI_VALUES constants in `src/babylon/economics/gamma/types.py`
- [X] T009 Define data source protocols (UnpaidCareHoursSource, PaidCareHoursSource, ERDISource) in `src/babylon/economics/gamma/data_sources.py`
- [X] T010 Define validation functions (validate_gamma_iii, validate_gamma_import, validate_gamma_basket) in `src/babylon/economics/gamma/validation.py`
- [X] T011 [P] Write unit tests for all Pydantic types in `tests/unit/economics/gamma/test_types.py`
- [X] T012 [P] Write unit tests for validation functions in `tests/unit/economics/gamma/test_validation.py`
- [X] T012a Define weighted_average_gamma() utility function in `src/babylon/economics/gamma/types.py` that computes Σ(weight × γ) / Σ(weight) per FR-011
- [X] T012b [P] Write unit test for weighted_average_gamma() verifying intensive aggregation (sum of weights, not sum of values) in `tests/unit/economics/gamma/test_types.py`

**Checkpoint**: Foundation ready - types validated, protocols defined, intensive aggregation utility available

______________________________________________________________________

## Phase 3: User Story 1 - Compute Reproductive Labor Visibility (γ_III) (Priority: P1) 🎯 MVP

**Goal**: Compute γ_III = L_paid_care / (L_paid_care + L_unpaid_care) from ATUS/QCEW data

**Independent Test**: Compute γ_III for national aggregate, validate result in [0.20, 0.40] range

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T013 [P] [US1] Unit test for GammaIIICalculator.compute() in `tests/unit/economics/gamma/test_gamma_iii.py`
- [X] T014 [P] [US1] Unit test for GammaIIICalculator.get_paid_care_hours() in `tests/unit/economics/gamma/test_gamma_iii.py`
- [X] T015 [P] [US1] Unit test for GammaIIICalculator.get_unpaid_care_hours() in `tests/unit/economics/gamma/test_gamma_iii.py`
- [X] T016 [P] [US1] Unit test for NoDataSentinel return when ATUS unavailable in `tests/unit/economics/gamma/test_gamma_iii.py`
- [X] T017 [P] [US1] Unit test for Fortunati exploitation rate calculation in `tests/unit/economics/gamma/test_gamma_iii.py`

### Implementation for User Story 1

- [X] T018 [US1] Create QCEW care sector adapter with NAICS codes 61, 62, 624, 814 in `src/babylon/economics/gamma/adapters.py`
- [X] T019 [US1] Implement care fraction coefficients (education=0.60, healthcare=0.30, social=0.80, household=1.00) in `src/babylon/economics/gamma/adapters.py`
- [X] T020 [US1] Implement GammaIIICalculator protocol in `src/babylon/economics/gamma/gamma_iii.py`
- [X] T021 [US1] Implement DefaultGammaIIICalculator with ATUS/QCEW integration in `src/babylon/economics/gamma/gamma_iii.py`
- [X] T022 [US1] Add logging for out-of-range warnings (γ_III outside [0.20, 0.40]) in `src/babylon/economics/gamma/gamma_iii.py`
- [X] T023 [US1] Update package exports for GammaIIICalculator in `src/babylon/economics/gamma/__init__.py`

**Checkpoint**: γ_III computes correctly from ATUS/QCEW data, tests pass

______________________________________________________________________

## Phase 4: User Story 2 - Calculate Reproductive Shadow Subsidy (Priority: P1) 🎯 MVP

**Goal**: Compute Φ_III = (1 - γ_III) × L_unpaid × τ, with fallback to labor-hours when MELT unavailable

**Independent Test**: Given γ_III=0.30, unpaid_hours=50B, MELT=$65/hour, result ≈ $2.3 trillion

### Tests for User Story 2

- [X] T024 [P] [US2] Unit test for compute_phi_iii() with MELT available in `tests/unit/economics/gamma/test_shadow_subsidy.py`
- [X] T025 [P] [US2] Unit test for compute_phi_iii() with MELT unavailable (labor-hours fallback) in `tests/unit/economics/gamma/test_shadow_subsidy.py`
- [X] T026 [P] [US2] Unit test for magnitude validation ($1.5-3.5T range) in `tests/unit/economics/gamma/test_shadow_subsidy.py`

### Implementation for User Story 2

- [X] T027 [US2] Implement ShadowSubsidyCalculator protocol in `src/babylon/economics/gamma/shadow_subsidy.py`
- [X] T028 [US2] Implement DefaultShadowSubsidyCalculator.compute_phi_iii() in `src/babylon/economics/gamma/shadow_subsidy.py`
- [X] T029 [US2] Integrate with MELT calculator from Feature 013 in `src/babylon/economics/gamma/shadow_subsidy.py`
- [X] T030 [US2] Add labor-hours fallback when MELT unavailable in `src/babylon/economics/gamma/shadow_subsidy.py`
- [X] T031 [US2] Update package exports for ShadowSubsidyCalculator in `src/babylon/economics/gamma/__init__.py`

**Checkpoint**: Φ_III computes to ~$2.3T, both dollar and labor-hour outputs work

______________________________________________________________________

## Phase 5: User Story 3 - Compute International Import Visibility (Priority: P2)

**Goal**: Compute γ_import = Σ(import_share[origin] × 1/ERDI[origin]) using MVP hardcoded ERDI values

**Independent Test**: Compute γ_import for known shares/ERDI, validate result in [0.40, 0.70] range

### Tests for User Story 3

- [X] T032 [P] [US3] Unit test for GammaImportCalculator.compute() in `tests/unit/economics/gamma/test_gamma_import.py`
- [X] T033 [P] [US3] Unit test for GammaImportCalculator.get_erdi() with MVP values in `tests/unit/economics/gamma/test_gamma_import.py`
- [X] T034 [P] [US3] Unit test for import share validation (sum=1.0) in `tests/unit/economics/gamma/test_gamma_import.py`
- [X] T035 [P] [US3] Unit test for fallback ERDI values (Core=1.0, Periphery=2.0) in `tests/unit/economics/gamma/test_gamma_import.py`

### Implementation for User Story 3

- [X] T036 [US3] Implement GammaImportCalculator protocol in `src/babylon/economics/gamma/gamma_import.py`
- [X] T037 [US3] Implement DefaultGammaImportCalculator with MVP ERDI values in `src/babylon/economics/gamma/gamma_import.py`
- [X] T038 [US3] Add import share validation (sum must equal 1.0 ± 0.01) in `src/babylon/economics/gamma/gamma_import.py`
- [X] T039 [US3] Add logging for out-of-range warnings (γ_import outside [0.40, 0.70]) in `src/babylon/economics/gamma/gamma_import.py`
- [X] T040 [US3] Update package exports for GammaImportCalculator in `src/babylon/economics/gamma/__init__.py`

**Checkpoint**: γ_import computes to ~0.65 from MVP ERDI values, tests pass

______________________________________________________________________

## Phase 6: User Story 4 - Compute Consumption Basket Visibility (Priority: P2)

**Goal**: Compute γ_basket = 1 / (α/γ_import + (1-α)) using harmonic mean formula

**Independent Test**: Given α=0.35, γ_import=0.65, result ≈ 0.74; edge cases α=0→1.0, α=1→γ_import

### Tests for User Story 4

- [X] T041 [P] [US4] Unit test for GammaBasketCalculator.compute() in `tests/unit/economics/gamma/test_gamma_basket.py`
- [X] T042 [P] [US4] Unit test for edge case α=0 (γ_basket=1.0) in `tests/unit/economics/gamma/test_gamma_basket.py`
- [X] T043 [P] [US4] Unit test for edge case α=1 (γ_basket=γ_import) in `tests/unit/economics/gamma/test_gamma_basket.py`
- [X] T044 [P] [US4] Unit test for constraint γ_basket ≥ γ_import in `tests/unit/economics/gamma/test_gamma_basket.py`

### Implementation for User Story 4

- [X] T045 [US4] Implement GammaBasketCalculator protocol in `src/babylon/economics/gamma/gamma_basket.py`
- [X] T046 [US4] Implement DefaultGammaBasketCalculator with harmonic mean formula in `src/babylon/economics/gamma/gamma_basket.py`
- [X] T047 [US4] Add validation for γ_basket ≥ γ_import constraint in `src/babylon/economics/gamma/gamma_basket.py`
- [X] T048 [US4] Add logging for out-of-range warnings (γ_basket outside [0.60, 0.85]) in `src/babylon/economics/gamma/gamma_basket.py`
- [X] T049 [US4] Update package exports for GammaBasketCalculator in `src/babylon/economics/gamma/__init__.py`

**Checkpoint**: γ_basket computes to ~0.74 for typical US basket, edge cases handled

______________________________________________________________________

## Phase 7: User Story 5 - Compute Imperial Shadow Subsidy (Priority: P3)

**Goal**: Compute Φ_imperial = (1 - γ_basket) × Consumption

**Independent Test**: Given γ_basket=0.74, consumption=$15T, result ≈ $3.9 trillion

### Tests for User Story 5

- [X] T050 [P] [US5] Unit test for compute_phi_imperial() in `tests/unit/economics/gamma/test_shadow_subsidy.py`
- [X] T051 [P] [US5] Unit test for magnitude validation ($1.0-4.0T range) in `tests/unit/economics/gamma/test_shadow_subsidy.py`
- [X] T052 [P] [US5] Unit test for total shadow subsidy (Φ_III + Φ_imperial) in `tests/unit/economics/gamma/test_shadow_subsidy.py`

### Implementation for User Story 5

- [X] T053 [US5] Implement DefaultShadowSubsidyCalculator.compute_phi_imperial() in `src/babylon/economics/gamma/shadow_subsidy.py`
- [X] T054 [US5] Implement compute_total_shadow() combining both subsidies in `src/babylon/economics/gamma/shadow_subsidy.py`
- [X] T055 [US5] Add magnitude validation logging for imperial subsidy in `src/babylon/economics/gamma/shadow_subsidy.py`

**Checkpoint**: Imperial shadow subsidy computes to ~$3.9T, total shadow computes correctly

______________________________________________________________________

## Phase 8: Integration & Polish

**Purpose**: End-to-end validation and cross-cutting concerns

- [X] T056 Write integration test for full gamma tensor computation in `tests/integration/economics/test_gamma_validation.py`
- [X] T057 [P] Add Detroit Metro validation scenario (γ_III, γ_import, γ_basket, both Φ values) in `tests/integration/economics/test_gamma_validation.py`
- [X] T057a [P] Write integration test for SC-002: verify γ_III increases when paid_care_hours increases relative to unpaid_care_hours (synthetic directional test) in `tests/integration/economics/test_gamma_validation.py`
- [X] T058 [P] Validate quickstart.md examples work as documented
- [X] T059 Run full test suite and verify all tests pass (`mise run test:unit`)
- [X] T060 Run code quality checks (`mise run check`)
- [X] T061 Update specs/015-gamma-visibility-tensor/tasks.md status to complete

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel (both P1)
  - US3 and US4 can proceed in parallel (both P2)
  - US5 depends on US4 (needs γ_basket)
- **Integration (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Uses GammaIII from US1 but can be implemented in parallel with mock data
- **User Story 3 (P2)**: Can start after Foundational - No dependencies on other stories
- **User Story 4 (P2)**: Uses γ_import from US3 - Can start after US3 or use mock data
- **User Story 5 (P3)**: Uses γ_basket from US4 - Must wait for US4 completion

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Types before services
- Services before integration
- Core implementation before validation/logging

### Parallel Opportunities

- All Foundational type definitions (T004-T008) can run in parallel
- All test tasks within each user story marked [P] can run in parallel
- US1+US2 can be worked on in parallel by different developers
- US3+US4 can be worked on in parallel (with mock data for US4)

______________________________________________________________________

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for GammaIIICalculator.compute() in tests/unit/economics/gamma/test_gamma_iii.py"
Task: "Unit test for GammaIIICalculator.get_paid_care_hours() in tests/unit/economics/gamma/test_gamma_iii.py"
Task: "Unit test for GammaIIICalculator.get_unpaid_care_hours() in tests/unit/economics/gamma/test_gamma_iii.py"
```

## Parallel Example: Foundational Types

```bash
# Launch all type definitions together:
Task: "Define GammaIII Pydantic model in src/babylon/economics/gamma/types.py"
Task: "Define GammaImport Pydantic model in src/babylon/economics/gamma/types.py"
Task: "Define GammaBasket Pydantic model in src/babylon/economics/gamma/types.py"
Task: "Define ShadowSubsidy Pydantic model in src/babylon/economics/gamma/types.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (γ_III calculation)
4. Complete Phase 4: User Story 2 (Φ_III shadow subsidy)
5. **STOP and VALIDATE**: Test γ_III and Φ_III independently
6. Deploy/demo if ready (~$2.3T reproductive shadow subsidy)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (γ_III) → Test independently → MVP deliverable
3. Add User Story 2 (Φ_III) → Test independently → MVP complete (~$2.3T subsidy)
4. Add User Story 3 (γ_import) → Test independently → International mechanism
5. Add User Story 4 (γ_basket) → Test independently → Composite visibility
6. Add User Story 5 (Φ_imperial) → Test independently → Full "two subsidies" framework (~$6T total)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 + 2 (reproductive mechanism)
   - Developer B: User Story 3 + 4 (international mechanism)
3. Developer B hands off γ_basket to Developer A for User Story 5
4. Integration phase completed together

______________________________________________________________________

## Summary

| Phase | Tasks | Story | Description |
|-------|-------|-------|-------------|
| Phase 1 | T001-T003 | Setup | Package structure |
| Phase 2 | T004-T012b | Foundational | Types, protocols, validation, aggregation |
| Phase 3 | T013-T023 | US1 (P1) | γ_III calculation |
| Phase 4 | T024-T031 | US2 (P1) | Φ_III shadow subsidy |
| Phase 5 | T032-T040 | US3 (P2) | γ_import calculation |
| Phase 6 | T041-T049 | US4 (P2) | γ_basket calculation |
| Phase 7 | T050-T055 | US5 (P3) | Φ_imperial calculation |
| Phase 8 | T056-T061 | Integration | Validation & polish |

**Total Tasks**: 64
**MVP Tasks** (US1+US2): 33 tasks
**P1 Priority**: 19 tasks (T013-T031)
**P2 Priority**: 18 tasks (T032-T049)
**P3 Priority**: 6 tasks (T050-T055)

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Do NOT modify** existing `melt/basket_visibility.py` (per research.md R4)
- Reuse existing data sources (ATUS, QCEW, MELT) per research.md R6
