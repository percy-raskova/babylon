# Tasks: MVP Simulation Engine

**Input**: Design documents from `/specs/001-mvp-sim-engine/` **Prerequisites**: plan.md, spec.md, research.md,
data-model.md, contracts/

**Tests**: Integration tests included per plan.md test structure (pytest markers: `@pytest.mark.unit`,
`@pytest.mark.integration`)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All file paths are relative to repository root

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new packages and module structure per plan.md

- [x] T001 Create protocols package directory at `src/babylon/protocols/`
- [x] T002 Create `src/babylon/protocols/__init__.py` with package exports
- [x] T003 Create `src/babylon/models/snapshots.py` stub file
- [x] T004 Create test directories `tests/unit/protocols/` and `tests/integration/mvp/`

**Checkpoint**: Directory structure ready for implementation

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and protocols that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Snapshot Models (Required by all protocols)

- [x] T005 Implement `HexState` Pydantic model in `src/babylon/models/snapshots.py` per
  [data-model.md#HexState](data-model.md#hexstate)
- [x] T006 Implement `EdgeState` Pydantic model in `src/babylon/models/snapshots.py` per
  [data-model.md#EdgeState](data-model.md#edgestate)
- [x] T007 Implement `TerritoryState` Pydantic model in `src/babylon/models/snapshots.py` per
  [data-model.md#TerritoryState](data-model.md#territorystate) including `equilibrium_r` field
- [x] T008 Implement `SimulationSnapshot` Pydantic model in `src/babylon/models/snapshots.py` per
  [data-model.md#SimulationSnapshot](data-model.md#simulationsnapshot)
- [x] T009 Add validation rules for all snapshot models (FIPS pattern, profit_rate clamping, H3 index pattern)
- [x] T010 Export snapshot types from `src/babylon/models/__init__.py`

### Protocol Definitions (Required before Simulation mods)

- [x] T011 [P] Implement `SimulationState` protocol in `src/babylon/protocols/simulation_state.py` per
  [contracts/simulation_state.py](contracts/simulation_state.py)
- [x] T012 [P] Implement `SimulationControl` protocol in `src/babylon/protocols/simulation_control.py` per
  [contracts/simulation_control.py](contracts/simulation_control.py)
- [x] T013 Update `src/babylon/protocols/__init__.py` to export both protocols

**Checkpoint**: Foundation ready - protocols and types defined, user story implementation can begin

______________________________________________________________________

## Phase 3: User Story 1+2 - Run Tick & Query State (Priority: P1) 🎯 MVP

**Goal**: GUI developer can call `step()` and `get_territory_state()` to see state changes

**Independent Test**: Initialize simulation, call `step()`, verify profit_rate changed; query territory by ID and verify
fields present

**Note**: US1 and US2 are both P1 priority and tightly coupled—implementing together as MVP core

### Implementation for User Story 1+2

- [x] T014 [US1+2] Add `get_current_tick()` method to `Simulation` class in `src/babylon/engine/simulation.py`
- [x] T015 [US1+2] Add `get_snapshot()` method to `Simulation` class returning `SimulationSnapshot` per
  [plan.md#Architecture](plan.md#architecture)
- [x] T016 [US1+2] Add `get_territory_state(territory_id)` method to `Simulation` class returning
  `TerritoryState | None`
- [x] T017 [US1+2] Add `get_hexes_for_territory(territory_id)` method to `Simulation` class returning `set[str]`
- [x] T018 [US1+2] Modify existing `step()` method to update profit_rate per
  [plan.md#Per-Tick Update Rule](plan.md#per-tick-update-rule) with territory-specific `equilibrium_r`
- [x] T019 [US1+2] Add `reset()` method to `Simulation` class per Assumption #6 (restore cached initial state)
- [x] T020 [US1+2] Cache initial state at construction for `reset()` functionality
- [x] T021 [US1+2] Add profit_rate clamping to [0.0, 1.0] range with warning log per Edge Cases
- [x] T022 [US1+2] Ensure `Simulation` class satisfies `SimulationState` and `SimulationControl` protocols (add type
  hints)

### Tests for User Story 1+2

- [x] T023 [US1+2] Integration test: `test_gui_readiness.py` - SC-001 acceptance test in `tests/integration/mvp/` per
  [quickstart.md#GUI Readiness Test](quickstart.md#gui-readiness-test). Include NaN/negative edge case validation with
  clamping verification.
- [x] T024 [US1+2] Integration test: `test_determinism.py` - SC-002 reproducibility in `tests/integration/mvp/` per
  [quickstart.md#Determinism Verification](quickstart.md#determinism-verification)

**Checkpoint**: Core MVP complete - GUI can step simulation and query state. US1 and US2 acceptance scenarios pass.

______________________________________________________________________

## Phase 4: User Story 3 - Hydrate from SQLite (Priority: P2)

**Goal**: Simulation initializes from real QCEW/BEA data instead of hardcoded values

**Independent Test**: Initialize via `from_sqlite()`, verify Wayne County profit_rate differs from Oakland (SC-006)

### Implementation for User Story 3

- [x] T025 [US3] Create `src/babylon/data/reference/hydrator.py` module for SQLite hydration
- [x] T026 [US3] Implement `query_counties(fips_codes)` function to fetch from `dim_county` per
  [research.md#3. SQLite Schema](research.md#3-sqlite-reference-database-schema)
- [x] T027 [US3] Implement `query_hex_claims(county_ids)` function to fetch from `bridge_county_h3`
- [x] T028 [US3] Implement `compute_initial_profit_rate(fips, year)` function using `MarxianHydrator` per
  [research.md#4. Economics Hydrator](research.md#4-economics-hydrator)
- [x] T029 [US3] Implement `Simulation.from_sqlite(fips_codes, year)` class method per
  [plan.md#Hydration Flow](plan.md#hydration-flow)
- [x] T030 [US3] Add fail-fast error handling for missing county data per Edge Cases
- [x] T031 [US3] Add warning log for empty hex_claims per Edge Cases
- [x] T032 [US3] Set `equilibrium_r = initial_r` for each territory at hydration time

### Tests for User Story 3

- [x] T033 [P] [US3] Integration test: `test_hydration.py` - SQLite → Territory in `tests/integration/mvp/`
- [x] T034 [US3] Integration test: Verify SC-006 (Wayne ≠ Oakland profit_rate) in
  `tests/integration/mvp/test_hydration.py`
- [x] T035 [US3] Integration test: Verify SC-003 (\<2s initialization) in `tests/integration/mvp/test_hydration.py`
  using `@pytest.mark.timeout(2)`

**Checkpoint**: User Story 3 complete - data-driven initialization works with Detroit test case

______________________________________________________________________

## Phase 5: User Story 4 - Protocol-Based Interface (Priority: P2)

**Goal**: GUI code can type-check against protocols without importing Simulation implementation

**Independent Test**: Run mypy on mock GUI code that imports only protocols - no errors

### Implementation for User Story 4

- [x] T036 [US4] Add `@runtime_checkable` decorator to both protocols in `src/babylon/protocols/`
- [x] T037 [US4] Verify protocol imports work standalone:
  `from babylon.protocols import SimulationState, SimulationControl`
- [x] T038 [US4] Add type hints to `Simulation` class showing protocol implementation

### Tests for User Story 4

- [x] T039 [P] [US4] Unit test: `isinstance(sim, SimulationState)` returns True in
  `tests/unit/protocols/test_simulation_state.py`
- [x] T040 [P] [US4] Unit test: `isinstance(sim, SimulationControl)` returns True in
  `tests/unit/protocols/test_simulation_control.py`
- [x] T041 [US4] Verification: Run `mypy` on a test file that imports only protocols (SC-005)

**Checkpoint**: User Story 4 complete - clean protocol boundary established

______________________________________________________________________

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, and final checks

- [x] T042 Add STUB comments to placeholder constants per Constitution III.1: `# STUB: Replace with TRPF`
- [x] T043 Run full test suite: `pytest tests/unit/protocols/ tests/integration/mvp/ -v`
- [x] T044 Verify all success criteria SC-001 through SC-006 pass
- [x] T045 Run quickstart.md examples as smoke test per [quickstart.md](quickstart.md)
- [x] T046 Update `src/babylon/models/__init__.py` exports if needed
- [x] T047 Update `src/babylon/protocols/__init__.py` with `__all__` exports

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1: Setup
    │
    ▼
Phase 2: Foundational (T005-T013)
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
Phase 3: US1+2    Phase 4: US3     Phase 5: US4
(P1 - MVP Core)   (P2 - Data)      (P2 - Protocols)
    │                 │                 │
    └─────────────────┴─────────────────┘
                      │
                      ▼
              Phase 6: Polish
```

### User Story Dependencies

| Story | Depends On | Can Parallel With | | ---------- | ---------------- | ------------------------ | | US1+2 (P1) |
Phase 2 complete | US3, US4 (after Phase 2) | | US3 (P2) | Phase 2 complete | US1+2, US4 | | US4 (P2) | Phase 2 complete
| US1+2, US3 |

### Within-Phase Task Order

**Phase 2 (Foundational)**:

- T005-T008: Sequential (TerritoryState depends on HexState for validation)
- T009-T010: After T008
- T011-T012: Parallel [P] (after T008)
- T013: After T011, T012

**Phase 3 (US1+2)**:

- T014-T022: Sequential (each method builds on prior)
- T023-T024: After T022 (integration tests)

**Phase 4 (US3)**:

- T025-T032: Sequential (hydration pipeline)
- T033-T035: After T032 (tests)

**Phase 5 (US4)**:

- T036-T038: Sequential (protocol implementation)
- T039-T040: Parallel [P] (unit tests)
- T041: After T039, T040 (mypy verification)

### Parallel Opportunities

```bash
# After Phase 2 completes, launch all user stories in parallel:
# Team member A: Phase 3 (US1+2)
# Team member B: Phase 4 (US3)
# Team member C: Phase 5 (US4)

# Within Phase 2, protocols can be parallel:
# T011 [P] SimulationState protocol
# T012 [P] SimulationControl protocol

# Within Phase 5, unit tests can be parallel:
# T039 [P] test_simulation_state.py
# T040 [P] test_simulation_control.py
```

______________________________________________________________________

## Parallel Example: Phase 2 Foundational

```bash
# Sequential: Snapshot models (T005 → T006 → T007 → T008 → T009 → T010)
# Then parallel: Protocols
Task: "Implement SimulationState protocol in src/babylon/protocols/simulation_state.py"
Task: "Implement SimulationControl protocol in src/babylon/protocols/simulation_control.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1+2 Only)

1. Complete Phase 1: Setup
1. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
1. Complete Phase 3: User Story 1+2 (Run Tick + Query State)
1. **STOP and VALIDATE**: Run T023, T024 - GUI readiness and determinism tests
1. Deploy/demo if ready - this is the MVP!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
1. Add US1+2 → Test independently → **MVP Complete** (GUI can render)
1. Add US3 → Test independently → Real data flowing
1. Add US4 → Test independently → Clean protocol boundary
1. Polish → Full feature complete

### Success Criteria Mapping

| Success Criterion | Verified By Task | | ----------------------------------- | ---------------- | | SC-001: GUI
readiness test | T023 | | SC-002: Determinism (100 ticks) | T024 | | SC-003: \<2s initialization | T035 | | SC-004:
Protocol methods callable | T039, T040 | | SC-005: mypy type-check protocols | T041 | | SC-006: Wayne ≠ Oakland
profit_rate | T034 |

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- US1 and US2 combined as US1+2 because they're both P1 and tightly coupled (step + query)
- Protocol compliance tests (T039, T040) consolidated in Phase 5 to avoid duplication
- All STUB constants must be commented per Constitution III.1
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Reference documents in task descriptions link to specific sections for implementation details
