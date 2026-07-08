# Tasks: ATUS Department III - Visibility Decomposition

**Input**: Design documents from `/specs/005-atus-department-iii/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: TDD approach per project CLAUDE.md - tests written FIRST to fail, then implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths are relative to repository root (`src/babylon/`, `tests/`)

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal setup - most infrastructure already exists

- [x] T001 Add visibility_weights section to src/babylon/data/atus/seed_data.yaml (verified 2026-07-08: visibility_weights in src/babylon/data/atus/seed_data.yaml:213-237)
- [x] T002 [P] Create validation module structure at src/babylon/economics/validation/__init__.py (verified 2026-07-08: src/babylon/economics/validation/__init__.py)
- [x] T003 [P] Create test directory structure at tests/unit/economics/validation/ (verified 2026-07-08: tests/unit/economics/validation/ dir + __init__.py)

**Checkpoint**: Seed data and module structure ready

______________________________________________________________________

## Phase 2: User Story 2 - Four-Category Visibility Decomposition (Priority: P2) 🎯 MVP Foundation

**Goal**: Create the VisibilityDecomposition Pydantic model with four-category breakdown

**Why P2 First**: The model is foundational - US1 (g₃₃ computation) depends on this model existing

**Independent Test**: Verify fractions sum to 1.0 ± 0.001, weighted g₃₃ computes correctly

### Tests for User Story 2 (TDD RED Phase)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [~] T004 [P] [US2] Create test_visibility.py with model validation tests at tests/unit/data/atus/test_visibility.py (partial 2026-07-08: implemented in 8a87ad65 (tests/unit/data/atus/test_visibility.py), deleted in spec-037 4ce7c96a)
- [~] T005 [P] [US2] Write test: fractions must sum to 1.0 ± 0.001 (should FAIL - model doesn't exist) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:41-69), deleted in spec-037 4ce7c96a)
- [~] T006 [P] [US2] Write test: total_g33 computed as weighted average (should FAIL - property doesn't exist) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:73), deleted in spec-037 4ce7c96a)
- [~] T007 [P] [US2] Write test: model rejects invalid fractions (negative, >1) (should FAIL) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:107-125), deleted in spec-037 4ce7c96a)
- [~] T007a [P] [US2] Write test: fractions normalize with warning if drift > 0.01 (edge case per spec.md L84) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:132), deleted in spec-037 4ce7c96a)
- [~] T007b [P] [US2] Write test: g₃₃ clamped to [0,1] with warning for out-of-bounds input (edge case per spec.md L82) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:171), deleted in spec-037 4ce7c96a)

### Implementation for User Story 2 (TDD GREEN Phase)

- [~] T008 [US2] Add VisibilityDecomposition model to src/babylon/data/atus/models.py (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at /media/user/data/babylon-data/atus/models.py:159)
- [~] T009 [US2] Implement four fraction fields with Field(ge=0.0, le=1.0) constraints (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/models.py:217-236)
- [~] T010 [US2] Implement model_validator to ensure fractions sum to 1.0 ± 0.001 (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/models.py:238-278)
- [~] T011 [US2] Add visibility coefficient constants (g_domestic=0.0, g_migrant=0.3, g_peripheral=0.0, g_state=1.0) (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/models.py:207-210)
- [~] T012 [US2] Implement computed_field total_g33 as weighted average (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/models.py:280-304)
- [~] T012a [US2] Implement fraction normalization with warning if drift > 0.01 (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/models.py:258-271)
- [~] T012b [US2] Implement g₃₃ clamping to [0,1] with warning for out-of-bounds values (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/models.py:296-302)
- [ ] T013 [US2] Run tests - all T004-T007b should now PASS (unverifiable — ephemeral gate, no durable artifact (US2 tests deleted in spec-037))

**Checkpoint**: VisibilityDecomposition model complete and independently testable

______________________________________________________________________

## Phase 3: User Story 1 - Compute g₃₃ from Data Sources (Priority: P1)

**Goal**: Create VisibilityComputer service that computes g₃₃ from seed data weights

**Independent Test**: Provide input weights, verify g₃₃ falls within [0.2, 0.5] range (SC-003)

### Tests for User Story 1 (TDD RED Phase)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [~] T014 [P] [US1] Write test: VisibilityComputer.get_national_g33() returns value in [0.2, 0.5] (should FAIL) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:245), deleted in spec-037 4ce7c96a)
- [~] T015 [P] [US1] Write test: compute_visibility() returns VisibilityDecomposition (should FAIL) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:260), deleted in spec-037 4ce7c96a)
- [~] T016 [P] [US1] Write test: service raises DataSourceUnavailableError if weights missing (should FAIL) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:274), deleted in spec-037 4ce7c96a)
- [~] T017 [P] [US1] Write test: computed g₃₃ is deterministic given same inputs (should FAIL) (partial 2026-07-08: implemented in 8a87ad65 (test_visibility.py:286), deleted in spec-037 4ce7c96a)

### Implementation for User Story 1 (TDD GREEN Phase)

- [~] T018 [US1] Create src/babylon/data/atus/visibility.py with VisibilityComputer class (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/visibility.py:53)
- [~] T019 [US1] Implement __init__ to load visibility weights from seed_data.yaml (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/visibility.py:80-111)
- [~] T020 [US1] Implement get_national_g33() method per contracts/visibility_protocol.py (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/visibility.py:132-146)
- [~] T021 [US1] Implement compute_visibility() method returning VisibilityDecomposition (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/visibility.py:113-130)
- [~] T022 [US1] Add DataSourceUnavailableError handling for missing weights (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/visibility.py:44-50,91-105)
- [~] T023 [US1] Add VisibilityComputerProtocol to src/babylon/data/atus/protocol.py (partial 2026-07-08: implemented in 8a87ad65; atus/protocol.py deleted in 537d1257; protocol now src/babylon/economics/shadow_labor.py:121-147)
- [~] T024 [US1] Export VisibilityComputer from src/babylon/data/atus/__init__.py (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at babylon-data/atus/__init__.py:19-22)
- [ ] T025 [US1] Run tests - all T014-T017 should now PASS (unverifiable — ephemeral gate, no durable artifact (US1 tests deleted in spec-037))

**Checkpoint**: g₃₃ computation works independently, falls within theoretical range

______________________________________________________________________

## Phase 4: User Story 3 - Validate Falsifiability Criteria (Priority: P3)

**Goal**: Implement regression validation (domestic_hours ~ 1/income with β > 0)

**Independent Test**: Run regression on ATUS occupation multipliers, verify positive coefficient

### Tests for User Story 3 (TDD RED Phase)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T026 [P] [US3] Create test_regression.py at tests/unit/economics/validation/test_regression.py (verified 2026-07-08: tests/unit/economics/validation/test_regression.py)
- [x] T027 [P] [US3] Write test: regression produces positive coefficient β > 0 (should FAIL) (verified 2026-07-08: tests/unit/economics/validation/test_regression.py:60-76)
- [x] T028 [P] [US3] Write test: regression uses scipy.stats.linregress (should FAIL) (verified 2026-07-08: src/babylon/economics/validation/regression.py:31,:98 scipy.stats.linregress; test_regression.py:79-101)
- [x] T029 [P] [US3] Write test: regression returns RegressionResult with slope, p_value (should FAIL) (verified 2026-07-08: tests/unit/economics/validation/test_regression.py:19-53)

### Implementation for User Story 3 (TDD GREEN Phase)

- [x] T030 [US3] Create src/babylon/economics/validation/regression.py (verified 2026-07-08: src/babylon/economics/validation/regression.py)
- [x] T031 [US3] Implement RegressionResult Pydantic model (slope, intercept, r_value, p_value, std_err) (verified 2026-07-08: src/babylon/economics/validation/regression.py:36-66 RegressionResult)
- [x] T032 [US3] Implement validate_domestic_hours_regression() function using scipy.stats.linregress (verified 2026-07-08: src/babylon/economics/validation/regression.py:109-173)
- [x] T033 [US3] Load occupation multipliers from existing ATUS seed data as proxy for income (verified 2026-07-08: src/babylon/economics/validation/regression.py:139)
- [x] T034 [US3] Export from src/babylon/economics/validation/__init__.py (verified 2026-07-08: src/babylon/economics/validation/__init__.py:26-36)
- [ ] T035 [US3] Run tests - all T026-T029 should now PASS (unverifiable — ephemeral gate, no durable artifact)

**Checkpoint**: Falsifiability validation independently testable, confirms theoretical expectation

______________________________________________________________________

## Phase 5: Integration & Shadow Subsidy Update

**Goal**: Wire VisibilityComputer into existing ShadowLaborService via dependency injection

**FR-004 Coverage**: This phase satisfies FR-004 ("override default g₃₃=1.0") by injecting VisibilityComputer into ShadowLaborService. The computed g₃₃ flows through to shadow_subsidy calculation, effectively overriding the default.

**Independent Test**: End-to-end test verifying shadow_subsidy uses computed g₃₃

### Tests for Integration (TDD RED Phase)

- [x] T036 [P] Create test_visibility_integration.py at tests/integration/economics/test_visibility_integration.py (verified 2026-07-08: tests/integration/economics/test_visibility_integration.py)
- [~] T037 [P] Write test: ShadowLaborService accepts VisibilityComputer via DI (should FAIL) (partial 2026-07-08: written real in 8a87ad65; now a pytest.skip stub since spec-037 (VisibilityComputer no longer importable in-tree))
- [~] T038 [P] Write test: shadow_subsidy = v × (1 - computed_g33), not default 1.0 (should FAIL) (partial 2026-07-08: written real in 8a87ad65; now pytest.skip stub at tests/integration/economics/test_visibility_integration.py:32-34)
- [~] T039 [P] Write test: shadow_subsidy accounts for 50-80% of reproductive labor value (SC-004) (should FAIL) (partial 2026-07-08: written real in 8a87ad65; now pytest.skip stub at tests/integration/economics/test_visibility_integration.py:50-52)

### Implementation for Integration (TDD GREEN Phase)

- [x] T040 Update src/babylon/economics/shadow_labor.py to accept VisibilityComputer (verified 2026-07-08: src/babylon/economics/shadow_labor.py:367-382)
- [x] T041 Implement optional visibility_computer parameter with fallback to default g33=1.0 (verified 2026-07-08: src/babylon/economics/shadow_labor.py:371,:430-436)
- [x] T042 Update shadow_subsidy calculation to use computed g₃₃ when VisibilityComputer provided (verified 2026-07-08: src/babylon/economics/shadow_labor.py:430-436 (override > computer > config))
- [ ] T043 Run tests - all T036-T039 should now PASS (unverifiable — ephemeral gate, no durable artifact (integration tests now skipped))
- [ ] T044 Run full test suite: mise run test:all (unverifiable — ephemeral gate, no durable artifact)

**Checkpoint**: Full integration complete, shadow_subsidy reflects actual invisibility

______________________________________________________________________

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T045 [P] Add docstrings to all new public classes/functions (Sphinx-compatible) (verified 2026-07-08: RST docstrings on new public API (src/babylon/economics/shadow_labor.py:1-53,196-236; validation/regression.py:1-21,36-66))
- [ ] T046 [P] Run mypy on new files: mypy src/babylon/data/atus/visibility.py src/babylon/economics/validation/ (unverifiable — ephemeral gate, no durable artifact)
- [ ] T047 [P] Run ruff on new files: ruff check src/babylon/data/atus/visibility.py src/babylon/economics/validation/ (unverifiable — ephemeral gate, no durable artifact)
- [ ] T048 Verify all success criteria (SC-001 through SC-006) pass (unverifiable — ephemeral gate, no durable artifact)
- [~] T049 Update src/babylon/data/atus/__init__.py exports if needed (partial 2026-07-08: implemented in 8a87ad65, deleted from src in spec-037; rebuilt at /media/user/data/babylon-data/atus/__init__.py:24-30)
- [ ] T050 Final validation: run mise run check (unverifiable — ephemeral gate, no durable artifact)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

```mermaid
flowchart LR
    P1[Phase 1: Setup] --> P2[Phase 2: US2 Model]
    P2 --> P3[Phase 3: US1 Service]
    P3 --> P4[Phase 4: US3 Validation]
    P3 --> P5[Phase 5: Integration]
    P4 --> P5
    P5 --> P6[Phase 6: Polish]
```

### User Story Dependencies

- **User Story 2 (P2)**: No dependencies - model is foundational (implement FIRST despite P2 priority)
- **User Story 1 (P1)**: Depends on US2 model existing
- **User Story 3 (P3)**: Can start after US1 service exists (uses same seed data)

### Within Each Phase

1. RED: Write tests that FAIL (T004-T007, T014-T017, etc.)
1. GREEN: Implement until tests PASS (T008-T013, T018-T025, etc.)
1. Commit after each phase completion

### Parallel Opportunities

**Phase 1** (all parallel):

```bash
Task T001: seed_data.yaml
Task T002: validation/__init__.py
Task T003: test directory
```

**Phase 2 Tests** (all parallel):

```bash
Task T004-T007: All test files can be written simultaneously
```

**Phase 3 Tests** (all parallel):

```bash
Task T014-T017: Service tests can be written simultaneously
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 2 + User Story 1)

1. Complete Phase 1: Setup (seed data, module structure)
1. Complete Phase 2: US2 Model (VisibilityDecomposition)
1. Complete Phase 3: US1 Service (VisibilityComputer)
1. **STOP and VALIDATE**: Test g₃₃ computation independently
1. Deploy/demo if ready - shadow_subsidy now uses real data

### Incremental Delivery

1. Setup → Model → Service → **MVP: g₃₃ computation works**
1. Add US3 Validation → **Falsifiability confirmed**
1. Add Integration → **Full shadow_subsidy integration**
1. Polish → **Production ready**

### TDD Cycle Per Phase

```
RED:   Write tests (T004-T007) → All FAIL
GREEN: Implement (T008-T013) → All PASS
COMMIT: git commit -m "feat(atus): add VisibilityDecomposition model"
```

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- [Story] labels map tasks to user stories for traceability
- TDD: Tests MUST fail before implementation
- Commit after each phase or logical group
- Stop at any checkpoint to validate independently
- Existing infrastructure (dept_III, shadow_subsidy, ATUS loader) is NOT modified except for integration points
