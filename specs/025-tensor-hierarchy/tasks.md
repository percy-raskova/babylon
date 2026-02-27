# Tasks: Tensor Hierarchy

**Input**: Design documents from `/specs/025-tensor-hierarchy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/protocols.md
**Tests**: TDD approach per CLAUDE.md — test tasks included for each user story.

**Organization**: Tasks grouped by user story (P1-P5) to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package structure, shared test infrastructure, and conftest files for the tensor hierarchy module.

- [X] T001 Create package directory structure for `src/babylon/economics/tensor_hierarchy/` with `__init__.py`
- [X] T002 [P] Create package directory structure for `src/babylon/data/bea/` (add `__init__.py` if missing) and `src/babylon/data/bts/` with `__init__.py`
- [X] T003 [P] Create test directory structure for `tests/unit/economics/tensor_hierarchy/` and `tests/unit/data/bea/` and `tests/unit/data/bts/` with `__init__.py` files
- [X] T004 [P] Create shared test conftest with mock data sources at `tests/unit/economics/tensor_hierarchy/conftest.py`

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, protocols, schema extensions, and validation infrastructure that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Define IOTableType enum and all Level 1 frozen Pydantic tensor models (InterIndustryFlow, VisibilityMetric, GeographicFlow, ReproductionRequirements, ClassTransitionMatrix) in `src/babylon/economics/tensor_hierarchy/types.py`
- [X] T006 [P] Define all Level 2 frozen Pydantic models (LeontiefInverse, ImperialRentField, ShadowSubsidy, StationaryDistribution) in `src/babylon/economics/tensor_hierarchy/types.py`
- [X] T007 Define all data source Protocols (InterIndustryFlowSource, GeographicFlowSource, VisibilitySource, ReproductionSource, ClassTransitionSource) and computation Protocols (LeontiefComputer, ImperialRentComputer, DepartmentAggregator) in `src/babylon/economics/tensor_hierarchy/protocols.py`
- [X] T008 [P] Implement three-tier validation framework (expected/warning/fail ranges) for all tensor types in `src/babylon/economics/tensor_hierarchy/validation.py`
- [X] T009 [P] Add `dim_bea_io_table_type` and `fact_bea_io_coefficient` tables to SQLite 3NF schema in `src/babylon/data/reference/schema.py`
- [X] T010 [P] Create BEA-to-department TOML mapping file at `src/babylon/economics/tensor_hierarchy/mappings/bea_to_department.toml`
- [X] T011 Write unit tests for all tensor type models (frozen, field constraints, identity rules) in `tests/unit/economics/tensor_hierarchy/test_types.py`
- [X] T012 [P] Write unit tests for validation framework (expected/warning/fail ranges for each tensor type) in `tests/unit/economics/tensor_hierarchy/test_validation.py`
- [X] T013 Configure public exports in `src/babylon/economics/tensor_hierarchy/__init__.py` with `__all__` list

**Checkpoint**: All shared types, protocols, schema extensions, and validation infrastructure are in place. User story implementation can begin.

______________________________________________________________________

## Phase 3: User Story 1 - Inter-Industry Flow + Leontief (Priority: P1) MVP

**Goal**: Load BEA I-O coefficient matrix from XLSX into SQLite, construct InterIndustryFlow tensor, aggregate to 4 departments, compute Leontief inverse, validate against BEA benchmarks.

**Independent Test**: Load BEA I-O table for year 2019, aggregate to 4 departments, compute Leontief inverse, verify output multipliers within 5% of BEA-published `IxI_TR_Summary.xlsx`.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [P] [US1] Write unit tests for BEA I-O XLSX parser (read Use table, extract coefficients, handle missing industries) in `tests/unit/data/bea/test_io_loader.py`
- [X] T015 [P] [US1] Write unit tests for InterIndustryFlow loader from SQLite (get_direct_requirements, get_industry_codes, available_years) in `tests/unit/economics/tensor_hierarchy/test_inter_industry.py`
- [X] T016 [P] [US1] Write math tests for Leontief inverse computation (L = (I-A)^{-1}, singularity detection, non-negativity) in `tests/unit/economics/tensor_hierarchy/test_inter_industry.py`
- [X] T017 [P] [US1] Write unit tests for DepartmentAggregator (70->4 weighted aggregation, TOML mapping load) in `tests/unit/economics/tensor_hierarchy/test_inter_industry.py`
- [X] T018 [P] [US1] Write benchmark test comparing computed Leontief inverse against BEA's published `IxI_TR_Summary.xlsx` (SC-001: within 5%) in `tests/unit/economics/tensor_hierarchy/test_inter_industry.py`

### Implementation for User Story 1

- [X] T019 [US1] Implement BEA I-O XLSX ingestion loader (parse Use/Make tables from `data/input-output/make-use/`, populate `fact_bea_io_coefficient` and `dim_bea_io_table_type` in SQLite) in `src/babylon/data/bea/io_loader.py`
- [X] T020 [US1] Implement DefaultInterIndustryFlowSource (read from SQLite `fact_bea_io_coefficient`, construct InterIndustryFlow tensor) in `src/babylon/economics/tensor_hierarchy/inter_industry.py`
- [X] T021 [US1] Implement DefaultLeontiefComputer (compute L = (I-A)^{-1}, singularity detection via np.linalg, total labor coefficients) in `src/babylon/economics/tensor_hierarchy/inter_industry.py`
- [X] T022 [US1] Implement DefaultDepartmentAggregator (load TOML mapping, weighted aggregation from ~70 industries to 4x4 department matrix) in `src/babylon/economics/tensor_hierarchy/inter_industry.py`
- [X] T023 [US1] Add NoDataSentinel returns for missing years/data in InterIndustryFlow loader
- [X] T024 [US1] Write integration test loading real BEA XLSX -> SQLite -> InterIndustryFlow -> Leontief pipeline in `tests/integration/economics/test_tensor_hierarchy.py`

**Checkpoint**: Inter-industry flow tensor fully functional. BEA I-O data ingested, Leontief inverse computed, department aggregation working, benchmark validated.

______________________________________________________________________

## Phase 4: User Story 2 - Visibility Metric Gamma Wrapper (Priority: P2)

**Goal**: Wrap existing Feature 015 gamma module (`src/babylon/economics/gamma/`) into VisibilityMetric tensor with ShadowSubsidy derivation.

**Independent Test**: Provide test QCEW/ATUS data, compute visibility diagonal, verify g_33 < 0.5 and g_11 near 1.0, compute shadow subsidy.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T025 [P] [US2] Write unit tests for VisibilityMetric adapter (wraps gamma_iii -> g_33, constructs diagonal, handles missing years) in `tests/unit/economics/tensor_hierarchy/test_visibility.py`
- [X] T026 [P] [US2] Write unit tests for ShadowSubsidy computation (Dept III value * (1 - g_33), MELT conversion) in `tests/unit/economics/tensor_hierarchy/test_visibility.py`
- [X] T027 [P] [US2] Write validation tests for g_33 expected range [0.20, 0.40], warn [0.10, 0.50], fail outside [0.0, 1.0] in `tests/unit/economics/tensor_hierarchy/test_visibility.py`

### Implementation for User Story 2

- [X] T028 [US2] Implement DefaultVisibilitySource adapter wrapping `DefaultGammaIIICalculator` and constructing VisibilityMetric tensor in `src/babylon/economics/tensor_hierarchy/visibility.py`
- [X] T029 [US2] Implement ShadowSubsidy computation wrapping `DefaultShadowSubsidyCalculator.compute_phi_iii()` in `src/babylon/economics/tensor_hierarchy/visibility.py`
- [X] T030 [US2] Add NoDataSentinel returns for missing ATUS/QCEW data years in visibility adapter
- [X] T031 [US2] Add visibility-specific validation rules (g_33 < g_11, three-tier ranges) to `src/babylon/economics/tensor_hierarchy/validation.py`

**Checkpoint**: Visibility metric tensor wraps existing gamma module. Shadow subsidy computed correctly. No gamma module modifications.

______________________________________________________________________

## Phase 5: User Story 3 - Geographic Flow + Imperial Rent (Priority: P3)

**Goal**: Build BTS FAF ingestion loader, load geographic flows as sparse matrix at CFS Area resolution, compute imperial rent field from antisymmetric decomposition.

**Independent Test**: Load FAF data subset, compute per-area inflow/outflow, verify sum(Phi) near zero (value conservation).

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T032 [P] [US3] Write unit tests for BTS FAF data ingestion (parse FAF CSV, populate dim_cfs_area + fact_commodity_flow in SQLite) in `tests/unit/data/bts/test_faf_loader.py`
- [X] T033 [P] [US3] Write unit tests for GeographicFlow loader from SQLite (sparse matrix construction, CFS area ordering, commodity filtering) in `tests/unit/economics/tensor_hierarchy/test_geographic_flow.py`
- [X] T034 [P] [US3] Write math tests for ImperialRentField computation (antisymmetric decomposition, net flow per area, value conservation SC-003) in `tests/unit/economics/tensor_hierarchy/test_geographic_flow.py`
- [X] T035 [P] [US3] Write unit tests for geographic aggregation (CFS Area -> state, total flow preservation) in `tests/unit/economics/tensor_hierarchy/test_geographic_flow.py`

### Implementation for User Story 3

- [X] T036 [US3] Implement BTS FAF data ingestion loader (download FAF5 CSV, populate `dim_cfs_area`, `dim_sctg_commodity`, `fact_commodity_flow` in SQLite) in `src/babylon/data/bts/faf_loader.py`
- [X] T037 [US3] Implement DefaultGeographicFlowSource (read from SQLite `fact_commodity_flow`, construct sparse CSR flow matrix, CFS-to-county mapping) in `src/babylon/economics/tensor_hierarchy/geographic_flow.py`
- [X] T038 [US3] Implement DefaultImperialRentComputer (symmetric/antisymmetric decomposition, net value extraction Phi per area) in `src/babylon/economics/tensor_hierarchy/geographic_flow.py`
- [X] T039 [US3] Implement geographic aggregation (CFS Area -> state via mapping, preserving total flow magnitudes) in `src/babylon/economics/tensor_hierarchy/geographic_flow.py`
- [X] T040 [US3] Add NoDataSentinel returns for missing FAF data years and empty flow matrices
- [X] T041 [US3] Add geographic flow validation (non-negative values, conservation check |sum(Phi)| < 0.1% total flow) to `src/babylon/economics/tensor_hierarchy/validation.py`

**Checkpoint**: Geographic flow tensor loads from FAF data. Imperial rent field computed. Value conservation validated. Sparse storage efficient.

______________________________________________________________________

## Phase 6: User Story 4 - Reproduction Requirements (Priority: P4, Deferred Loader)

**Goal**: Define ReproductionRequirements tensor type and computation logic. Test with synthetic data. Data loader deferred pending CEX/PSID constitutional amendment.

**Independent Test**: Provide synthetic consumption and labor matrices, compute total reproduction cost via SNLT conversion, verify against hand calculations.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T042 [P] [US4] Write unit tests for ReproductionRequirements tensor with synthetic data (consumption by class/dept, labor by class pair) in `tests/unit/economics/tensor_hierarchy/test_reproduction.py`
- [X] T043 [P] [US4] Write math tests for total reproduction cost computation (consumption * SNLT + labor hours) in `tests/unit/economics/tensor_hierarchy/test_reproduction.py`

### Implementation for User Story 4

- [X] T044 [US4] Implement ReproductionRequirements computation logic (total_reproduction_cost with SNLT conversion) in `src/babylon/economics/tensor_hierarchy/reproduction.py`
- [X] T045 [US4] Implement stub DefaultReproductionSource returning NoDataSentinel with reason "CEX data source pending constitutional amendment" in `src/babylon/economics/tensor_hierarchy/reproduction.py`

**Checkpoint**: Reproduction requirements type and computation logic implemented. Tested with synthetic data. Production loader deferred.

______________________________________________________________________

## Phase 7: User Story 5 - Class Transition Matrix (Priority: P5, Deferred Loader)

**Goal**: Define ClassTransitionMatrix tensor type, stationary distribution computation, and class aggregation. Test with synthetic data. Data loader deferred pending PSID constitutional amendment.

**Independent Test**: Provide synthetic stochastic matrix, compute eigenvector, verify convergence and stochasticity preservation under aggregation.

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T046 [P] [US5] Write unit tests for ClassTransitionMatrix (stochastic validation, absorbing states, identity matrix) in `tests/unit/economics/tensor_hierarchy/test_class_transition.py`
- [X] T047 [P] [US5] Write math tests for stationary distribution (dominant eigenvector, convergence within 100 self-multiplications, SC-004) in `tests/unit/economics/tensor_hierarchy/test_class_transition.py`
- [X] T048 [P] [US5] Write unit tests for class aggregation (block-sum preserving stochasticity, 6->4 class mapping) in `tests/unit/economics/tensor_hierarchy/test_class_transition.py`

### Implementation for User Story 5

- [X] T049 [US5] Implement stationary distribution computation (eigenvector decomposition of P^T, normalization) in `src/babylon/economics/tensor_hierarchy/class_transition.py`
- [X] T050 [US5] Implement class aggregation (block-sum on transition matrix preserving row stochasticity) in `src/babylon/economics/tensor_hierarchy/class_transition.py`
- [X] T051 [US5] Implement stub DefaultClassTransitionSource returning NoDataSentinel with reason "PSID data source pending constitutional amendment" in `src/babylon/economics/tensor_hierarchy/class_transition.py`

**Checkpoint**: Class transition matrix type and computation logic implemented. Stationary distribution converges. Tested with synthetic data. Production loader deferred.

______________________________________________________________________

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, commutativity validation, and final package exports.

- [X] T052 [P] Write commutativity tests for FR-017 (aggregate then transform == transform then aggregate) for InterIndustryFlow, GeographicFlow, ClassTransitionMatrix in `tests/unit/economics/tensor_hierarchy/test_validation.py`
- [X] T053 [P] Write integration test for full tensor pipeline (BEA XLSX -> SQLite -> InterIndustryFlow -> Leontief -> department aggregation) in `tests/integration/economics/test_tensor_hierarchy.py`
- [X] T054 [P] Write integration test for visibility pipeline (gamma module -> VisibilityMetric -> ShadowSubsidy) in `tests/integration/economics/test_tensor_hierarchy.py`
- [X] T055 Update `src/babylon/economics/tensor_hierarchy/__init__.py` with complete `__all__` exports for all public types, protocols, and default implementations
- [X] T056 Run full test suite (`poetry run pytest tests/unit/economics/tensor_hierarchy/ tests/unit/data/bea/ tests/unit/data/bts/ tests/integration/economics/test_tensor_hierarchy.py -v`) and fix any failures
- [X] T057 Run `poetry run mypy src/babylon/economics/tensor_hierarchy/ --strict` and fix any type errors

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — highest priority, MVP target
- **US2 (Phase 4)**: Depends on Phase 2 — independent of US1
- **US3 (Phase 5)**: Depends on Phase 2 — independent of US1 and US2
- **US4 (Phase 6)**: Depends on Phase 2 — independent of other stories (deferred loader)
- **US5 (Phase 7)**: Depends on Phase 2 — independent of other stories (deferred loader)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (InterIndustryFlow)**: Requires BEA I-O XLSX data (present at `data/input-output/`). No cross-story dependencies.
- **US2 (VisibilityMetric)**: Requires gamma module (Feature 015, complete). No cross-story dependencies.
- **US3 (GeographicFlow)**: Requires BTS FAF data (needs download). No cross-story dependencies.
- **US4 (ReproductionRequirements)**: Requires CEX data (not available, loader deferred). Testable with synthetic data.
- **US5 (ClassTransitionMatrix)**: Requires PSID data (not available, loader deferred). Testable with synthetic data.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD Red phase)
- Data ingestion loaders before tensor loaders (data must be in SQLite first)
- Tensor model loading before derived computations (Level 1 before Level 2)
- Core implementation before validation and error handling
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T005/T006 (tensor models) and T007 (protocols) can run in parallel
- T008 (validation), T009 (schema), T010 (TOML mapping) can all run in parallel
- T011 and T012 (tests) can run in parallel

**Within each User Story**:
- All test tasks marked [P] can run in parallel (different test files)
- Data ingestion loader and tensor type tests are independent

**Across User Stories (after Phase 2)**:
- US1, US2, US3, US4, US5 can all proceed in parallel (independent data sources, independent modules, independent test files)
- US2 is the quickest win (thin adapter over existing module)
- US4 and US5 can be done anytime (synthetic data only, no blockers)

______________________________________________________________________

## Parallel Example: User Story 1

```bash
# Launch all US1 tests in parallel (Red phase):
Task: "Write unit tests for BEA I-O XLSX parser in tests/unit/data/bea/test_io_loader.py"
Task: "Write unit tests for InterIndustryFlow loader in tests/unit/economics/tensor_hierarchy/test_inter_industry.py"
Task: "Write math tests for Leontief inverse in tests/unit/economics/tensor_hierarchy/test_inter_industry.py"
Task: "Write unit tests for DepartmentAggregator in tests/unit/economics/tensor_hierarchy/test_inter_industry.py"
Task: "Write benchmark test against BEA IxI_TR_Summary in tests/unit/economics/tensor_hierarchy/test_inter_industry.py"
```

## Parallel Example: All User Stories (after Phase 2)

```bash
# Launch all user stories in parallel:
Task: "Implement US1 - InterIndustryFlow + Leontief (Phase 3)"
Task: "Implement US2 - VisibilityMetric gamma wrapper (Phase 4)"
Task: "Implement US3 - GeographicFlow + ImperialRent (Phase 5)"
Task: "Implement US4 - ReproductionRequirements with synthetic data (Phase 6)"
Task: "Implement US5 - ClassTransitionMatrix with synthetic data (Phase 7)"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (InterIndustryFlow + Leontief)
4. **STOP and VALIDATE**: Run `poetry run pytest tests/unit/economics/tensor_hierarchy/test_inter_industry.py tests/unit/data/bea/test_io_loader.py -v`
5. Verify SC-001: Output multipliers within 5% of BEA benchmarks

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. Add US1 (InterIndustryFlow) -> Test independently -> Verify benchmarks (MVP!)
3. Add US2 (VisibilityMetric) -> Test independently -> Quick win, thin adapter
4. Add US3 (GeographicFlow) -> Test independently -> Requires FAF data download
5. Add US4 (ReproductionRequirements) -> Synthetic data tests -> Deferred loader
6. Add US5 (ClassTransitionMatrix) -> Synthetic data tests -> Deferred loader
7. Polish -> Commutativity tests, integration tests, type checking

### Suggested MVP Scope

**Phase 1 + Phase 2 + Phase 3 (US1)**: This delivers the InterIndustryFlow tensor with Leontief inverse computation and department aggregation. All data is already present locally in `data/input-output/`. Validates against BEA-published benchmarks. Establishes the pattern for all subsequent tensors.

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD: Write tests first, ensure they fail, then implement
- Commit after each task or logical group per CLAUDE.md
- US4/US5 production loaders deferred pending III.4 constitutional amendment for CEX/PSID data sources
- BEA I-O data already downloaded at `data/input-output/` — no API needed
- BTS FAF data needs download from https://www.bts.gov/faf before US3 implementation
- Gamma module (Feature 015, 101 tests) is wrapped, never modified
