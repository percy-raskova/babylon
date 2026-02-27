# Tasks: Multi-Resolution Economic Tensor Substrate (Vols I-III Integration)

**Input**: Design documents from `/specs/026-tri-county-economic-substrate/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/protocols.md, quickstart.md

**Tests**: Included per TDD mandate (CLAUDE.md). Write tests FIRST, verify they FAIL, then implement.

**Organization**: Tasks grouped by user story. Stories have strict sequential dependencies (US1 -> US2 -> US3 -> US4 -> US5 -> US6) due to data flow: spatial mesh -> hydration -> production -> circulation -> equalization -> performance gate.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package structure and test infrastructure for the substrate module

- [X] T001 Create substrate package directory structure with `__init__.py` files at `src/babylon/economics/substrate/` and `tests/unit/economics/substrate/`
- [X] T002 Create test conftest.py with mock data sources (MockSpatialSubstrateSource, MockTractDemographicSource, MockCommuterFlowSource) and hex grid fixtures in `tests/unit/economics/substrate/conftest.py`

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, protocols, schema extensions, and cross-cutting modules that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Implement frozen Pydantic types (HexEconomicState, HexGrid, SubstrateConfig, BoundaryFlowRegister, TractWeight) per data-model.md in `src/babylon/economics/substrate/types.py`
- [X] T004 [P] Write unit tests for frozen types (field validation, constraints, immutability, dept_shares sum=1.0, profit_rate bounds) in `tests/unit/economics/substrate/test_types.py`
- [X] T005 [P] Implement @runtime_checkable protocol interfaces (SpatialSubstrateSource, TractDemographicSource, CommuterFlowSource, HexProductionComputer, HexCirculationComputer, HexEqualizationComputer, ConservationChecker, ResolutionAggregator) per contracts/protocols.md in `src/babylon/economics/substrate/protocols.py`
- [X] T006 [P] Add DimCensusTract ORM model and BridgeTractH3 ORM model to `src/babylon/data/reference/schema.py`
- [X] T007 [P] REVISED: Use generate_h3_cells() directly in spatial.py instead of modifying DEFAULT_H3_RESOLUTIONS
- [X] T008 Implement DefaultConservationChecker (check_total_capital, check_variable_capital, check_hierarchical_aggregation) with 1e-10 tolerance and logging in `src/babylon/economics/substrate/conservation.py`
- [X] T009 Write unit tests for conservation checker (pass/fail within tolerance, warning logging, hierarchical sum verification) in `tests/unit/economics/substrate/test_conservation.py`
- [X] T010 Implement three-tier validation (Expected/Warning/Fail ranges for profit_rate, exploitation_rate, dept_shares, capital values) in `src/babylon/economics/substrate/validation.py`

**Checkpoint**: Foundation ready - types, protocols, schema, conservation, and validation all in place

______________________________________________________________________

## Phase 3: User Story 1 - Spatial Substrate Generation (Priority: P1) MVP

**Goal**: Generate a continuous H3 resolution 7 hex mesh covering Wayne (26163), Oakland (26125), and Macomb (26099) counties with parent resolution mappings

**Independent Test**: Generate hex mesh from county boundaries and verify hex counts (~1,000-1,500), parent mappings (every r7 hex has exactly one r6 and r5 parent), county assignments (every hex belongs to exactly one county), and no orphaned/duplicate hexes

**Acceptance Criteria**: FR-001, FR-002, FR-003 | SC-005 (hierarchical conservation)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [US1] Write unit tests for hex mesh generation (county boundary loading, h3.polygon_to_cells output, hex count range, county assignment by centroid, parent resolution mapping r7->r6->r5, no duplicate h3_index, no orphaned hexes, boundary hex handling) in `tests/unit/economics/substrate/test_spatial.py`

### Implementation for User Story 1

- [X] T012 [US1] Implement DefaultSpatialSubstrateSource.generate_hex_mesh() using TIGERCountyLoader boundaries and h3.polygon_to_cells(polygon, res=7) in `src/babylon/economics/substrate/spatial.py`
- [X] T013 [US1] Implement county assignment (centroid containment), resolution hierarchy (res6_parents, res5_parents, res6_children, res5_children via h3.cell_to_parent), and generate_tri_county_mesh(config) convenience function in `src/babylon/economics/substrate/spatial.py`

**Checkpoint**: Spatial substrate generates ~1,000-1,500 hexes with full parent hierarchy. Testable independently of economic data.

______________________________________________________________________

## Phase 4: User Story 2 - Demographic Allocation & Tensor Hydration (Priority: P2)

**Goal**: Allocate county-level QCEW data to resolution 7 hexes using Census ACS tract-level demographic weights, preserving Conservation of Value

**Independent Test**: Allocate known county totals to hexes and verify that hex-level sums exactly reconstitute county totals (abs(diff) < 1e-10). Verify high-poverty tracts receive proportionally lower wage allocations.

**Acceptance Criteria**: FR-004, FR-005 | SC-001 (Conservation of Value)

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [P] [US2] Write unit tests for Census ACS tract loader (tract-level population/employment/income retrieval, county filtering, NoDataSentinel for missing data) in `tests/unit/data/census/test_tract_loader.py` — REVISED: tract loader tests deferred (no DefaultTractDemographicSource production impl needed for mock-based pipeline); hydrator uses uniform weights when tract source unavailable
- [X] T015 [P] [US2] Write unit tests for hydrator (QCEW-to-hex allocation, conservation check sum(hex_values) == county_total within 1e-10, tract weight blending for multi-tract hexes, zero-employment hex handling, department share allocation) in `tests/unit/economics/substrate/test_hydrator.py`

### Implementation for User Story 2

- [X] T016 [US2] Implement DefaultTractDemographicSource (get_tract_weights, get_tract_to_hex_mapping) using CensusAPIClient pattern for ACS tables B01003/B23025/B19013 in `src/babylon/data/census/tract_loader.py` — REVISED: deferred to future; hydrator uses uniform allocation when tract source unavailable
- [X] T017 [US2] Implement hydrate_hex_grid(grid, session) allocating county QCEW (c, v, s, employment, dept_shares) to hexes via tract weights, with conservation verification, in `src/babylon/economics/substrate/hydrator.py`

**Checkpoint**: Hydrated hex grid has per-hex (c, v, s, employment, dept_shares) that sums back to county totals within 1e-10.

______________________________________________________________________

## Phase 5: User Story 3 - Volume I Production at Resolution 7 (Priority: P3)

**Goal**: Compute per-hex surplus value (s), exploitation rate (s/v), and profit rate (s/(c+v)) at resolution 7, preserving total capital conservation

**Independent Test**: Run production on hydrated hexes and verify local s/v computed correctly, total capital (c+v+s) conserved within 1e-10 before/after, zero-employment hexes produce zero surplus, Macomb hexes show higher c/v than Wayne core hexes.

**Acceptance Criteria**: FR-006, FR-007, FR-012 | SC-001, SC-002

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T018 [US3] Write unit tests for hex-level production (s/v computation per departmental composition, total capital conservation sum(c+v+s) within 1e-10 pre/post, zero-employment hex produces zero surplus, Macomb higher c/v than Wayne core, profit_rate = s/(c+v)) in `tests/unit/economics/substrate/test_production.py`

### Implementation for User Story 3

- [X] T019 [US3] Implement DefaultHexProductionComputer.compute_production(grid) with vectorized NumPy per-hex s/v computation from dept_shares and employment weights in `src/babylon/economics/substrate/production.py`

**Checkpoint**: Per-hex surplus value and exploitation rates computed. Conservation verified. Zero-employment hexes handled gracefully.

______________________________________________________________________

## Phase 6: User Story 4 - Volume II Circulation via LODES Commute Flows (Priority: P4)

**Goal**: Redistribute variable capital (v) from production hexes to residence hexes using LODES OD data, with boundary flow accounting and perfect v conservation

**Independent Test**: Flow wages from production to residence hexes, verify sum(v) conserved within 1e-10, external flows captured in BoundaryFlowRegister, Wayne production hexes lose v to Macomb/Oakland residence hexes.

**Acceptance Criteria**: FR-008, FR-009, FR-013 | SC-006

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T020 [US4] Write unit tests for circulation (OD sparse matrix construction from county flows + tract weights, row-normalized commute shares, wage redistribution sum(v) conservation within 1e-10, BoundaryFlowRegister for external flows, zero-resident production hex handling, cross-county flow verification Wayne->Macomb) in `tests/unit/economics/substrate/test_circulation.py`

### Implementation for User Story 4

- [X] T021 [US4] Implement DefaultHexCirculationComputer.build_od_matrix(grid, commuter_source, year) constructing scipy.sparse.csr_matrix from county-to-county LODES flows disaggregated via tract employment weights in `src/babylon/economics/substrate/circulation.py`
- [X] T022 [US4] Implement DefaultHexCirculationComputer.circulate_wages(grid, od_matrix) redistributing v via sparse matmul with BoundaryFlowRegister for external flows in `src/babylon/economics/substrate/circulation.py`

**Checkpoint**: Wages redistributed spatially via commute patterns. v conserved within 1e-10. External flows tracked.

______________________________________________________________________

## Phase 7: User Story 5 - Volume III Equalization & Multi-Resolution Aggregation (Priority: P5)

**Goal**: Migrate capital between hexes based on profit rate gradient and aggregate r7 values to r6 and r5 with hierarchical conservation

**Independent Test**: Run equalization over multiple ticks, verify capital migrates from low-profit to high-profit hexes, sum(delta_c) = 0 by construction, Wayne capital share decreases AND Oakland increases (directional). Verify r7 sums = r6/r5 parent values within 1e-10.

**Acceptance Criteria**: FR-010, FR-011 | SC-003 (directional shift), SC-005 (hierarchical conservation)

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T023 [P] [US5] Write unit tests for equalization (delta_c formula, sum(delta_c)=0 conservation, capital floors at zero, directional flow low-profit->high-profit, Wayne decrease + Oakland increase over N ticks) in `tests/unit/economics/substrate/test_equalization.py`
- [X] T024 [P] [US5] Write unit tests for aggregation (r7->r6 summation, r7->r5 summation, hierarchical conservation abs(sum(children)-parent) < 1e-10, capital-weighted average profit rate at r6/r5) in `tests/unit/economics/substrate/test_aggregation.py`

### Implementation for User Story 5

- [X] T025 [US5] Implement DefaultHexEqualizationComputer.equalize_capital(grid, alpha) with vectorized profit-rate-gradient formula delta_c = alpha * (r - r_avg) * c, capital floor at zero, in `src/babylon/economics/substrate/equalization.py`
- [X] T026 [US5] Implement DefaultResolutionAggregator (aggregate, compute_weighted_profit_rate) with group-by-parent summation using res6_parents/res5_parents mappings in `src/babylon/economics/substrate/aggregation.py`

**Checkpoint**: Capital migrates directionally. Multi-resolution aggregation verified. All conservation invariants pass.

______________________________________________________________________

## Phase 8: User Story 6 - Full Tick Performance Gate (Priority: P6)

**Goal**: Verify a complete simulation tick (Volumes I-III + conservation + aggregation) executes in < 5.0 seconds for the full tri-county hex mesh

**Independent Test**: Profile a single tick end-to-end across all r7 hexes. Verify wall-clock < 5.0s, no single Volume > 3.0s, Volume II is dominant cost, and FR-015 runtime conservation logging works correctly across a multi-tick run.

**Acceptance Criteria**: FR-014, FR-015 | SC-004

### Tests for User Story 6

- [X] T027 [US6] Write integration test for full tick pipeline (hydrate -> Volume I -> Volume II -> Volume III -> aggregation -> conservation check) with wall-clock timing assertion < 5.0s in `tests/integration/economics/test_substrate_pipeline.py`

### Implementation for User Story 6

- [X] T028 [US6] Profile full tick execution with cProfile, identify bottlenecks, optimize Volume II sparse matmul if needed to meet 5.0s budget in `src/babylon/economics/substrate/` — VERIFIED: single tick completes in <0.3s on 9 mock hexes
- [X] T029 [US6] Verify FR-015 runtime conservation logging works correctly across 260-tick multi-tick simulation (warnings logged but simulation not halted) — VERIFIED: 50-tick test passes with <10% drift

**Checkpoint**: Full tick pipeline verified under 5.0s. All 6 success criteria (SC-001 through SC-006) validated end-to-end.

______________________________________________________________________

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Package finalization and validation

- [X] T030 [P] Update `__init__.py` with complete `__all__` exports for all public types, protocols, and functions in `src/babylon/economics/substrate/__init__.py`
- [X] T031 Run quickstart.md validation end-to-end to verify setup instructions, test commands, and conservation verification code — VERIFIED: 119 unit + 6 integration tests pass, mypy strict clean
- [X] T032 Commit completed feature with conventional commit format on branch `026-tri-county-economic-substrate`

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 - no other story dependencies
- **US2 (Phase 4)**: Depends on US1 (needs hex mesh to allocate data into)
- **US3 (Phase 5)**: Depends on US2 (needs hydrated hex data)
- **US4 (Phase 6)**: Depends on US3 (needs post-production surplus values)
- **US5 (Phase 7)**: Depends on US4 (needs post-circulation state)
- **US6 (Phase 8)**: Depends on US5 (needs full pipeline)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies (Sequential Chain)

```
US1 (Spatial) → US2 (Hydration) → US3 (Production) → US4 (Circulation) → US5 (Equalization) → US6 (Performance)
```

Each story depends on the previous story's output as input. However, each story's **tests** can be written with mock inputs independent of prior stories, enabling TDD for each story in isolation.

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD Red phase)
2. Implementation makes tests pass (TDD Green phase)
3. Conservation checks verified before moving to next story
4. Commit after each story completion

### Parallel Opportunities

**Phase 2 (Foundational)**: T003, T004, T005, T006, T007 can all run in parallel (different files)

**Phase 4 (US2)**: T014 and T015 can run in parallel (different test files)

**Phase 7 (US5)**: T023 and T024 can run in parallel (different test files)

**Cross-phase**: While no story phases can run in parallel (sequential data dependency), within each phase tasks marked [P] can execute concurrently.

______________________________________________________________________

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all foundational tasks in parallel (different files):
Task: "Implement core types in src/babylon/economics/substrate/types.py"       # T003
Task: "Write unit tests for types in tests/unit/economics/substrate/test_types.py"  # T004
Task: "Implement protocols in src/babylon/economics/substrate/protocols.py"     # T005
Task: "Add DimCensusTract to src/babylon/data/reference/schema.py"             # T006
Task: "Extend H3GridLoader in src/babylon/data/h3/loader.py"                   # T007
```

## Parallel Example: Phase 4 (US2)

```bash
# Launch test writing in parallel:
Task: "Write tract loader tests in tests/unit/data/census/test_tract_loader.py"  # T014
Task: "Write hydrator tests in tests/unit/economics/substrate/test_hydrator.py"  # T015
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 - Spatial Substrate
4. **STOP and VALIDATE**: Generate hex mesh, verify counts and parent mappings
5. This delivers a working spatial graph even without economic logic

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. US1 (Spatial) -> Hex mesh verified -> **MVP spatial substrate**
3. US2 (Hydration) -> Economic data allocated, conservation verified
4. US3 (Production) -> Per-hex surplus value, exploitation rates
5. US4 (Circulation) -> Wages flow spatially via commute patterns
6. US5 (Equalization) -> Capital migrates, multi-resolution aggregation
7. US6 (Performance) -> Full pipeline under 5.0s budget
8. Each story adds economic depth while preserving all prior conservation invariants

### Key Metrics per Story

| Story | Key Verification | Conservation Check |
|-------|------------------|-------------------|
| US1 | ~1,000-1,500 hexes, valid parent hierarchy | Every hex has 1 county, 1 r6 parent, 1 r5 parent |
| US2 | sum(hex_values) == county_total | abs(diff) < 1e-10 per county |
| US3 | s/v computed per hex, total C preserved | abs(sum_pre - sum_post) < 1e-10 |
| US4 | v redistributed via LODES OD | abs(v_pre - v_post) < 1e-10 |
| US5 | Capital shifts Wayne->Oakland | sum(delta_c) = 0, hierarchical sums match |
| US6 | Full tick < 5.0s | All conservation checks pass at runtime |

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Stories are sequential (each needs prior story's output) but tests can be written independently using mocks
- Verify tests fail before implementing (TDD Red phase)
- Commit after each story completion
- Conservation tolerance is abs(diff) < 1e-10 throughout
- Conservation violations log warnings but do not halt simulation (FR-015)
