# Tasks: Fundamental Tensor Primitive

**Input**: Design documents from `/specs/011-fundamental-tensor-primitive/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tensor_api.py
**Generated**: 2026-02-01

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md: Single project structure under `src/babylon/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, type definitions, and spec gap resolution

### Spec Gap Resolution (CHK gaps from release-readiness checklist)

- [x] T001 [P] Define "standard hardware" in spec.md SC-005 as: 4-core CPU, 16GB RAM, SSD (addresses CHK028)
- [x] T002 [P] Clarify 0.01% tolerance in spec.md SC-003/SC-004 as relative tolerance (addresses CHK021, CHK041)
- [x] T003 [P] Specify SC-005 latency as p95 target in spec.md (addresses CHK042)
- [x] T004 [P] Specify SC-006 as peak RSS memory in spec.md (addresses CHK043)
- [x] T005 [P] Define floating-point tolerance (1e-9) for SC-008 "identical results" in spec.md (addresses CHK044)
- [x] T006 [P] Add year boundary behavior to spec.md edge cases: years outside 2010-2025 return NoDataSentinel (addresses CHK051, CHK052)
- [x] T007 [P] Add state aggregate edge case to spec.md: state with no loaded counties returns NoDataSentinel (addresses CHK055)
- [x] T008 [P] Enumerate magic constants in spec.md FR-021: SNLT factors, BEA ratio defaults, max_delta for interpolation (addresses CHK018)

### Type Definitions

- [x] T009 [P] Add LaborHours constrained type to src/babylon/models/types.py
- [x] T010 [P] Add SignedLaborHours type for derived values to src/babylon/models/types.py
- [x] T011 [P] Add test constants for tensor operations to tests/constants.py

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Consumer Isolation Documentation (CHK gaps)

- [x] T012 Define "direct database access" precisely in spec.md: any import from babylon.data.* or SQLAlchemy session usage (addresses CHK011)
- [x] T013 [P] List prohibited import paths in spec.md FR-004: babylon.data.*, sqlalchemy.orm.*, sqlite3 (addresses CHK012, CHK016)
- [x] T014 [P] Add static import analysis as SC-002 verification method in spec.md (addresses CHK015)

### Core Sentinel Pattern

- [x] T015 Create NoDataSentinel class in src/babylon/economics/tensor.py per contracts/tensor_api.py
- [x] T016 Add NoDataSentinel unit tests in tests/unit/economics/test_tensor.py

### SNLT Configuration

- [x] T017 Create SNLTConfig Pydantic model in src/babylon/economics/snlt.py per contracts/tensor_api.py
- [x] T018 Add SNLTConfig unit tests in tests/unit/economics/test_snlt.py
- [x] T019 Add SNLT factor validation (must be > 0.0) to prevent division by zero (addresses CHK048)

### Tensor Registry Core

- [x] T020 Create TensorRegistry skeleton in src/babylon/economics/tensor_registry.py with __init__, _county_cache, _aggregate_cache
- [x] T021 Implement TensorRegistry.get() method returning ValueTensor4x3 | NoDataSentinel
- [x] T022 Implement TensorRegistry.available_years() method returning frozenset[int]
- [x] T023 Add thread-safety locks to TensorRegistry cache operations (per data-model.md line 243)
- [x] T024 Add LRU eviction policy to aggregate cache with configurable maxsize (addresses CHK008)

### Non-Functional Requirements (CHK gaps)

- [x] T025 Add performance requirement to spec.md: get() method < 1ms p95 latency (addresses CHK056)
- [x] T026 Add performance requirement to spec.md: get_aggregate() cold cache < 100ms, warm cache < 1ms (addresses CHK057)
- [x] T027 Add spec.md requirement: LRU eviction triggers at 500MB, logs eviction events (addresses CHK058)
- [x] T028 Add logging requirements to spec.md: INFO for hydration, DEBUG for cache hits/misses (addresses CHK059)
- [x] T029 Add NoDataSentinel.reason format requirement: "{context}: {specific_reason}" (addresses CHK060)

**Checkpoint**: Foundation ready - user story implementation can now begin

______________________________________________________________________

## Phase 3: User Story 1 - Simulation Engine Consumes Tensor Data (Priority: P1) 🎯 MVP

**Goal**: Simulation engine accesses economic data exclusively through tensor primitive, receiving labor-hour values for all 12 cells without database queries.

**Independent Test**: Load tensor for single FIPS/year, verify simulation can read c/v/s values in labor-hours for all four departments without any database connection.

### Implementation for User Story 1

- [x] T030 [P] [US1] Extend DepartmentRow in src/babylon/economics/tensor.py to use LaborHours type
- [x] T031 [P] [US1] Extend ValueTensor4x3 in src/babylon/economics/tensor.py to use LaborHours for all 12 cells
- [x] T032 [US1] Add computed fields to ValueTensor4x3: profit_rate, exploitation_rate, organic_composition per data-model.md formulas
- [x] T033 [US1] Add imperial_rent computed field (SignedLaborHours) to ValueTensor4x3 per data-model.md
- [x] T034 [US1] Implement TensorRegistry.hydrate_counties() in src/babylon/economics/tensor_registry.py
- [x] T035 [US1] Modify MarxianHydrator in src/babylon/economics/hydrator.py to return ValueTensor4x3 with LaborHours
- [x] T036 [US1] Apply SNLT conversion in hydrator: wages × factor → LaborHours
- [x] T037 [US1] Modify Simulation.from_sqlite() in src/babylon/engine/simulation.py to initialize TensorRegistry
- [x] T038 [US1] Add tensor_registry reference to SimulationSnapshot in src/babylon/models/snapshots.py
- [x] T039 [US1] Unit test: verify simulation accesses tensor without database query in tests/unit/economics/test_tensor_registry.py
- [x] T040 [US1] Integration test: SQLite → TensorRegistry → Simulation flow in tests/integration/test_tensor_data_flow.py

**Checkpoint**: Simulation engine can consume tensor data - core functionality complete

______________________________________________________________________

## Phase 4: User Story 2 - Hexagon Visualization Receives Tensor Data (Priority: P2)

**Goal**: Hexagon visualization receives data exclusively from tensor primitive or derived tensors, never touching database directly.

**Independent Test**: Populate tensor with known values, verify hexagons display correct labor-hour data without any database imports.

### Implementation for User Story 2

- [x] T041 [P] [US2] Add tensor_year field to TerritoryState in src/babylon/models/snapshots.py
- [x] T042 [US2] Implement TensorConsumer protocol in visualization layer (per contracts/tensor_api.py)
- [x] T043 [US2] Add set_tensor_source() method to HexagonRenderer pattern in quickstart.md
- [x] T044 [US2] Create static import analysis script in tools/verify_hexagon_isolation.py (addresses SC-002)
- [x] T045 [US2] Add import analysis to CI workflow to enforce hexagon isolation
- [x] T046 [US2] Unit test: verify hexagon receives tensor data without DB imports in tests/unit/test_hexagon_isolation.py

**Checkpoint**: Hexagon visualization isolated from database - consumer isolation complete

______________________________________________________________________

## Phase 5: User Story 3 - Tensor Loads from SQLite Database (Priority: P3)

**Goal**: Tensor primitive hydrates from SQLite containing QCEW wage data and BEA ratios, converting monetary wages to labor-hours.

**Independent Test**: Initialize tensor from test SQLite, verify correct data mapping with SNLT conversion applied.

### Implementation for User Story 3

- [x] T047 [P] [US3] Implement BEA ratio temporal interpolation in src/babylon/economics/adapters.py per research.md R3
- [x] T048 [US3] Add max_delta parameter (default 5 years) to BEA interpolation (addresses CHK054)
- [x] T049 [US3] Implement fallback to YAML defaults when no BEA ratio found within max_delta
- [x] T050 [US3] Implement TensorRegistry.hydrate_state() in src/babylon/economics/tensor_registry.py
- [x] T051 [US3] Add lazy loading trigger: first access to unloaded FIPS returns NoDataSentinel with reason (addresses CHK033)
- [x] T052 [US3] Implement year boundary validation: years outside 2010-2025 return NoDataSentinel
- [x] T053 [US3] Handle partial hydration: log warning for failed years, continue with successful ones (addresses CHK050)
- [x] T054 [US3] Handle initialization failure: raise TensorInitializationError when SQLite unavailable (addresses CHK047)
- [x] T055 [US3] Unit test: BEA interpolation algorithm in tests/unit/economics/test_bea_interpolation.py
- [x] T056 [US3] Integration test: full hydration from SQLite in tests/integration/test_tensor_hydration.py

**Checkpoint**: Tensor loading from database complete - data layer functional

______________________________________________________________________

## Phase 6: User Story 4 - Derived Tensors Compute from Primitive (Priority: P3)

**Goal**: Higher-level tensors (Imperial Rent Field, etc.) derive values from primitive ValueTensor4x3, not from raw database queries.

**Independent Test**: Compute derived tensor from known primitive, verify derivation formula matches manual calculation.

### Implementation for User Story 4

- [ ] T057 [P] [US4] Create DerivedTensor protocol implementation in src/babylon/economics/derived_tensors.py
- [ ] T058 [US4] Implement ImperialRentField class computing Φ = total_v - total_value per data-model.md
- [ ] T059 [US4] Implement geographic aggregation: TensorRegistry.get_aggregate() for STATE and NATION levels
- [ ] T060 [US4] Add aggregation formula validation: sum(counties) must match state within 0.01% relative tolerance
- [ ] T061 [US4] Implement cache invalidation strategy: clear aggregate cache when source tensors updated (addresses CHK025)
- [ ] T062 [US4] Unit test: derived tensor matches manual calculation in tests/unit/economics/test_derived_tensors.py
- [ ] T063 [US4] Unit test: geographic aggregation accuracy in tests/unit/economics/test_tensor_aggregation.py

**Checkpoint**: Derived tensors functional - all economic calculations unified

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Performance validation, documentation, and cross-cutting improvements

### Performance Validation

- [ ] T064 Benchmark test: 100 counties × 10 years < 5 seconds in tests/benchmark/test_tensor_performance.py
- [ ] T065 Memory profiler test: full US dataset < 500MB peak RSS in tests/benchmark/test_tensor_memory.py
- [ ] T066 Add get() latency assertion: p95 < 1ms in benchmark tests
- [ ] T067 Add get_aggregate() latency assertions: cold < 100ms, warm < 1ms in benchmark tests

### Traceability (CHK gaps)

- [ ] T068 Verify FR-007 through FR-018 have corresponding success criteria, add where missing (addresses CHK068)
- [ ] T069 Document concurrent access pattern in data-model.md (addresses CHK046)

### Documentation & Cleanup

- [ ] T070 [P] Update quickstart.md with final API examples
- [ ] T071 [P] Add logging throughout tensor operations per spec requirements
- [ ] T072 Run release-readiness.md checklist validation - all items should now pass
- [ ] T073 Update ai-docs/state.yaml with tensor primitive implementation status

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 (P1): Can start immediately after Foundational
  - US2 (P2): Can start after Foundational, integrates with US1 for TerritoryState
  - US3 (P3): Can start after Foundational, provides hydration for US1
  - US4 (P3): Depends on US1 (needs tensor structure), can parallel with US2/US3
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
        │
        ▼
   ┌────┴────┐
   │         │
   ▼         ▼
  US1 ◄──── US3
   │         │
   ▼         │
  US2        │
   │         │
   ▼         ▼
  US4 ◄──────┘
   │
   ▼
 Polish
```

- **US1 (Simulation)**: Core tensor structure - can start first
- **US2 (Hexagon)**: Needs TerritoryState from US1
- **US3 (Loading)**: Can parallel with US1, provides data source
- **US4 (Derived)**: Needs tensor structure from US1, aggregation from US3

### Parallel Opportunities

#### Within Phase 1 (Setup)
```bash
# All spec gap resolution tasks can run in parallel:
T001, T002, T003, T004, T005, T006, T007, T008

# All type definition tasks can run in parallel:
T009, T010, T011
```

#### Within Phase 2 (Foundational)
```bash
# Documentation tasks can run in parallel:
T012, T013, T014

# After T015 (NoDataSentinel), these can parallel:
T017 (SNLTConfig), T020 (TensorRegistry skeleton)
```

#### User Story Parallelization
```bash
# After Foundational complete, US1 and US3 can start in parallel:
US1: T030, T031 (tensor extensions)
US3: T047 (BEA interpolation)

# US2 can start once US1 reaches T038 (snapshots):
US2: T041, T042 (visualization integration)

# US4 can start once US1 reaches T032 (computed fields):
US4: T057, T058 (derived tensors)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (spec gaps + types)
2. Complete Phase 2: Foundational (sentinel, SNLT, registry core)
3. Complete Phase 3: User Story 1 (simulation consumes tensor)
4. **STOP and VALIDATE**: Test simulation accessing tensor without DB queries
5. Deploy/demo if ready - simulation has labor-hour economic data

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Simulation functional → MVP!
3. Add US2 → Hexagon isolation complete
4. Add US3 → Database loading complete
5. Add US4 → Derived tensors complete
6. Polish → Performance validated, all checklist items pass

### Key Gap Resolution Summary

| Gap Category | Tasks Addressing |
|--------------|-----------------|
| Performance metrics undefined | T025, T026, T027, T064-T067 |
| Acceptance criteria ambiguous | T001-T005, T060 |
| Consumer isolation incomplete | T012-T014, T044-T046 |
| Temporal boundaries missing | T006, T007, T052 |

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Gap resolution tasks (T001-T014, T025-T029) address checklist failures from release-readiness.md
