# Tasks: Technical Debt Cleanup & Infrastructure Hardening

**Input**: Design documents from `/specs/010-cleanup-tech-debt/`
**Prerequisites**: plan.md (required), spec.md (required), research.md

**Tests**: This is a refactoring/cleanup spec. Tests are validation-oriented (verification commands) rather than new test creation, except for US3 which adds one integration test.

**Organization**: Tasks are grouped by user story to enable independent implementation and verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/babylon/`, `tests/` at repository root
- Python 3.12+, pytest testing framework
- Sphinx documentation in `docs/`

______________________________________________________________________

## Phase 1: Setup (Pre-flight Validation)

**Purpose**: Verify preconditions before making destructive changes

- [x] T001 Verify clean git status on feature branch `010-cleanup-tech-debt`
- [x] T002 Run `mise run test:all` to establish baseline (all tests must pass)
- [x] T003 Run `mise run docs:strict` to verify docs build cleanly before changes
- [x] T004 [P] Verify PyQt6 dashboard launches: `python -m babylon.ui.dashboard --demo`

**Checkpoint**: Baseline established - safe to proceed with cleanup

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks for this cleanup spec

This is a refactoring spec with no new infrastructure. Each user story is independent and can proceed after Phase 1 validation.

**Checkpoint**: Foundation ready - user story implementation can begin

______________________________________________________________________

## Phase 3: User Story 1 - Legacy DPG Code Removal (Priority: P1) :dart: MVP

**Goal**: Remove all DearPyGui dashboard code to eliminate confusion with PyQt6 architecture

**Independent Test**: Verify deleted files no longer exist, imports updated, tests pass, dashboard launches

### Implementation for User Story 1

- [x] T005 [US1] Delete legacy DPG dashboard file `src/babylon/ui/dpg_runner.py`
- [x] T006 [US1] Delete legacy DPG test file `tests/unit/ui/test_dpg_runner.py`
- [x] T007 [US1] Remove `DPGColors` class from `src/babylon/ui/design_system.py` (keep `BunkerPalette` only)
- [x] T008 [US1] Update exports in `src/babylon/ui/__init__.py` to remove `dpg_runner` and `DPGColors`
- [x] T009 [US1] Update `docs/how-to/gui-development.rst` to replace DPGColors references with BunkerPalette
- [x] T010 [US1] Update `ai-docs/epochs/epoch1/dpg-patterns.yaml` to note DPG deprecation
- [x] T011 [P] [US1] Update `ai-docs/epochs/epoch1/ui-wireframes.yaml` to note DPG removal
- [x] T012 [P] [US1] Update `ai-docs/archive/epochs-overview.md` to note DPG removal

### Validation for User Story 1

- [x] T013 [US1] Validate SC-001: `! test -f src/babylon/ui/dpg_runner.py` (file deleted)
- [x] T014 [US1] Validate SC-002: `! test -f tests/unit/ui/test_dpg_runner.py` (file deleted)
- [x] T015 [US1] Validate SC-003: `grep -r "class DPGColors" src/` returns empty
- [x] T016 [US1] Validate SC-008: `python -m babylon.ui.dashboard --demo` exits 0
- [x] T017 [US1] Run `mise run test:all` to verify no regressions
- [x] T018 [US1] Commit: `refactor(ui): remove legacy DPG dashboard code`

**Checkpoint**: User Story 1 complete - legacy DPG code removed, dashboard functional

______________________________________________________________________

## Phase 4: User Story 2 - Systems Architecture Rename (Priority: P2)

**Goal**: Rename `babylon.systems` to `babylon.formulas` for architectural clarity

**Independent Test**: Verify old package renamed, all imports updated, tests pass, docs build

### Implementation for User Story 2

- [ ] T019 [US2] Execute `git mv src/babylon/systems src/babylon/formulas` to rename package
- [ ] T020 [US2] Update internal imports in `src/babylon/formulas/__init__.py` (babylon.systems.formulas → babylon.formulas)
- [ ] T021 [US2] Update internal imports in `src/babylon/formulas/formulas/__init__.py` (11 occurrences)
- [ ] T022 [P] [US2] Update import in `src/babylon/formulas/formulas/fundamental_theorem.py`
- [ ] T023 [P] [US2] Update import in `src/babylon/formulas/formulas/survival_calculus.py`
- [ ] T024 [P] [US2] Update import in `src/babylon/formulas/formulas/ideological_routing.py`
- [ ] T025 [US2] Update imports in `src/babylon/engine/formula_registry.py` (2 occurrences)
- [ ] T026 [P] [US2] Update import in `src/babylon/engine/systems/economic.py`
- [ ] T027 [P] [US2] Update import in `src/babylon/engine/systems/vitality.py`
- [ ] T028 [P] [US2] Update import in `src/babylon/engine/systems/ideology.py`
- [ ] T029 [P] [US2] Update import in `src/babylon/engine/systems/metabolism.py`

### Test Import Updates for User Story 2

- [ ] T030 [US2] Update imports in `tests/unit/formulas/test_bourgeoisie_decision.py` (15 occurrences)
- [ ] T031 [P] [US2] Update imports in `tests/unit/formulas/test_survival_calculus_properties.py` (2 occurrences)
- [ ] T032 [P] [US2] Update import in `tests/unit/formulas/test_fundamental_theorem.py`
- [ ] T033 [P] [US2] Update import in `tests/unit/formulas/test_fundamental_theorem_properties.py`
- [ ] T034 [P] [US2] Update import in `tests/unit/formulas/test_survival_calculus.py`
- [ ] T035 [P] [US2] Update import in `tests/unit/formulas/test_ideological_routing.py`
- [ ] T036 [P] [US2] Update import in `tests/unit/formulas/test_solidarity.py`
- [ ] T037 [P] [US2] Update import in `tests/unit/formulas/test_unequal_exchange.py`
- [ ] T038 [P] [US2] Update import in `tests/unit/formulas/test_metabolic_rift.py`
- [ ] T039 [P] [US2] Update import in `tests/unit/formulas/test_trpf.py`
- [ ] T040 [P] [US2] Update import in `tests/unit/formulas/test_vitality.py`
- [ ] T041 [P] [US2] Update import in `tests/unit/formulas/test_class_dynamics.py`
- [ ] T042 [P] [US2] Update import in `tests/unit/engine/test_formula_registry.py`
- [ ] T043 [P] [US2] Update import in `tests/unit/config/test_constants_sync.py`
- [ ] T044 [P] [US2] Update import in `tests/integration/system/test_phase1_blueprint.py`

### Documentation Updates for User Story 2

- [ ] T045 [US2] Update module paths in `docs/reference/formulas.rst` (22 occurrences)
- [ ] T046 [P] [US2] Update cross-references in `docs/reference/class-dynamics.rst` (4 occurrences)
- [ ] T047 [P] [US2] Update cross-reference in `docs/reference/topology.rst`
- [ ] T048 [P] [US2] Update cross-references in `docs/concepts/survival-calculus.rst` (4 occurrences)
- [ ] T049 [P] [US2] Update cross-reference in `docs/concepts/imperial-rent.rst`
- [ ] T050 [P] [US2] Update cross-reference in `docs/concepts/percolation-theory.rst`
- [ ] T051 [US2] Rename `docs/api/systems.rst` to `docs/api/formulas.rst`
- [ ] T052 [US2] Update toctree in `docs/api/index.rst` to reference formulas.rst
- [ ] T053 [US2] Update ai-docs YAML files referencing babylon.systems

### Validation for User Story 2

- [ ] T054 [US2] Validate SC-004: `test -d src/babylon/formulas && ! test -d src/babylon/systems`
- [ ] T055 [US2] Validate SC-005: `grep -r "from babylon.systems\|import babylon.systems" src/` returns empty
- [ ] T056 [US2] Validate SC-006: `grep -r "from babylon.systems" tests/` returns empty
- [ ] T057 [US2] Run `mise run test:all` to verify all tests pass (SC-007)
- [ ] T058 [US2] Run `mise run docs:strict` to verify docs build (SC-009)
- [ ] T059 [US2] Commit: `refactor(formulas): rename babylon.systems to babylon.formulas`

**Checkpoint**: User Story 2 complete - package renamed, architecture clarified

______________________________________________________________________

## Phase 5: User Story 3 - Logging Context Integration (Priority: P3)

**Goal**: Validate Spec 008 logging infrastructure and add integration test

**Independent Test**: Verify `log_context_scope` exists, SessionRecorder uses DI, integration test passes

### Implementation for User Story 3

- [ ] T060 [US3] Verify `log_context_scope` exists in `src/babylon/utils/log.py` (FR-007)
- [ ] T061 [US3] Verify `SessionRecorder.__init__` accepts `metrics_collector` parameter in `src/babylon/utils/recorder.py` (FR-008)
- [ ] T062 [US3] Create integration test for tick context logging in `tests/integration/test_log_context.py`

### Validation for User Story 3

- [ ] T063 [US3] Validate SC-011: `pytest tests/integration -k log_context` exits 0
- [ ] T064 [US3] Validate SC-012: `grep "def __init__.*metrics_collector" src/babylon/utils/recorder.py` returns match
- [ ] T065 [US3] Commit: `test(logging): add integration test for tick context`

**Checkpoint**: User Story 3 complete - logging integration validated

______________________________________________________________________

## Phase 6: User Story 4 - TRPF Data Requirements Documentation (Priority: P4)

**Goal**: Document Epoch 2 data requirements with QCEW field mappings in TRPF docstrings

**Independent Test**: Verify TRPF docstrings contain "Epoch 2 Data Requirements" with QCEW mappings

### Implementation for User Story 4

- [ ] T066 [US4] Add "Epoch 2 Data Requirements" section to `calculate_rate_of_profit` docstring in `src/babylon/formulas/formulas/trpf.py` (FR-011)
- [ ] T067 [US4] Document QCEW field mappings for constant_capital, variable_capital, surplus_value in `src/babylon/formulas/formulas/trpf.py`
- [ ] T068 [US4] Add OCC-to-occupation relationship to `calculate_organic_composition` docstring in `src/babylon/formulas/formulas/trpf.py` (FR-012)
- [ ] T069 [US4] Add reference to `ai-docs/epoch2-trpf.yaml` specification in docstrings

### Validation for User Story 4

- [ ] T070 [US4] Validate SC-010: `grep -A5 "Epoch 2 Data Requirements" src/babylon/formulas/formulas/trpf.py` returns QCEW
- [ ] T071 [US4] Run `mise run docs:strict` to verify docstrings are valid RST
- [ ] T072 [US4] Commit: `docs(trpf): document Epoch 2 data requirements with QCEW mappings`

**Checkpoint**: User Story 4 complete - TRPF documentation enhanced

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across all user stories

- [ ] T073 Run full test suite: `mise run test:all` (final SC-007 validation)
- [ ] T074 Run documentation build: `mise run docs:strict` (final SC-009 validation)
- [ ] T075 Verify dashboard launches: `python -m babylon.ui.dashboard --demo` (final SC-008)
- [ ] T076 [P] Update CLAUDE.md agent context if needed
- [ ] T077 [P] Review and update ai-docs/state.yaml with completion status
- [ ] T078 Create final commit if any polish changes needed

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - establishes baseline
- **Foundational (Phase 2)**: N/A for this cleanup spec
- **User Stories (Phase 3-6)**: All depend on Phase 1 baseline validation
  - User stories can proceed sequentially in priority order (P1 → P2 → P3 → P4)
  - US2 depends on US1 being complete (file deletion before rename)
  - US3 and US4 are independent of each other
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 1 - No dependencies on other stories
- **User Story 2 (P2)**: Should complete after US1 (avoids conflicts in file operations)
- **User Story 3 (P3)**: Independent - can run after Phase 1 if staffed in parallel
- **User Story 4 (P4)**: Depends on US2 (trpf.py is renamed in US2)

### Within Each User Story

- Implementation tasks before validation tasks
- File deletions before import updates
- Source code updates before test updates
- Test updates before documentation updates
- All validation commands must pass before commit

### Parallel Opportunities

- All Phase 1 tasks can run in parallel
- Within US1: T010, T011, T012 can run in parallel (different ai-docs files)
- Within US2: All test file updates (T031-T044) can run in parallel
- Within US2: All doc file updates (T046-T050) can run in parallel (except T045, T051, T052)
- US3 and US4 can run in parallel if team capacity allows (after US2)

______________________________________________________________________

## Parallel Example: User Story 2 Test Updates

```bash
# Launch all test import updates together (all different files):
Task: "Update imports in tests/unit/formulas/test_survival_calculus_properties.py"
Task: "Update import in tests/unit/formulas/test_fundamental_theorem.py"
Task: "Update import in tests/unit/formulas/test_fundamental_theorem_properties.py"
Task: "Update import in tests/unit/formulas/test_survival_calculus.py"
Task: "Update import in tests/unit/formulas/test_ideological_routing.py"
Task: "Update import in tests/unit/formulas/test_solidarity.py"
Task: "Update import in tests/unit/formulas/test_unequal_exchange.py"
Task: "Update import in tests/unit/formulas/test_metabolic_rift.py"
Task: "Update import in tests/unit/formulas/test_trpf.py"
Task: "Update import in tests/unit/formulas/test_vitality.py"
Task: "Update import in tests/unit/formulas/test_class_dynamics.py"
Task: "Update import in tests/unit/engine/test_formula_registry.py"
Task: "Update import in tests/unit/config/test_constants_sync.py"
Task: "Update import in tests/integration/system/test_phase1_blueprint.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup validation
2. Complete Phase 3: User Story 1 (DPG removal)
3. **STOP and VALIDATE**: All tests pass, dashboard launches
4. Deploy if only DPG removal needed

### Incremental Delivery

1. Complete Setup → Baseline established
2. Add User Story 1 → DPG removed, dashboard verified (MVP!)
3. Add User Story 2 → Package renamed, architecture clarified
4. Add User Story 3 → Logging validation complete
5. Add User Story 4 → TRPF documentation complete
6. Each story adds value without breaking previous stories

### Recommended Execution Order

Since this is a cleanup spec with mechanical changes:

1. **Single Developer Path**: P1 → P2 → P3 → P4 (sequential)
2. **Two Developer Path**:
   - Dev A: P1 → P2 (file operations)
   - Dev B: P3 → P4 (after P2 completes for trpf.py path)

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and verifiable
- Commit after each user story phase
- Stop at any checkpoint to validate story independently
- Use `git mv` for package rename to preserve history
- All validation commands must exit 0 before proceeding
