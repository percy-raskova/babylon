# Tasks: MELT and Basket Visibility Computation (013)

**Input**: Design documents from `/specs/013-melt-basket-visibility/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: This feature follows TDD - tests are written first for each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Checklist Gap Mapping

The following tasks address remaining gaps from `checklists/tvt-domain-review.md`:

| Gap | Task | Description |
|-----|------|-------------|
| CHK030 | T012 | Distinct error messages for GDP vs employment data |
| CHK038 | T050 | Literature validation test with ±10% tolerance |
| CHK039 | T008 | Feature 012 integration points documentation |
| CHK040 | T007 | TensorRegistry integration pattern reference |
| CHK042 | T009 | Cache invalidation conditions specification |
| CHK044 | T010 | CPI data source for V_reproduction |
| CHK046 | T051 | SC-002 measurability test against QCEW data |
| CHK048 | T052 | SC-004 average wage definition (median QCEW) |
| CHK050 | T053 | Integration regression tests for existing consumers |

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Project initialization and module structure

- [x] T001 Create module structure at `src/babylon/economics/melt/` with `__init__.py`
- [x] T002 [P] Create `src/babylon/economics/melt/types.py` with ClassPosition enum per contracts/class_position.py
- [x] T003 [P] Create `src/babylon/economics/melt/parameters.py` with NationalParameters model per contracts/national_parameters.py
- [x] T004 [P] Create stub files for calculators:
  - `src/babylon/economics/melt/melt_calculator.py`
  - `src/babylon/economics/melt/basket_visibility.py`
  - `src/babylon/economics/melt/class_position.py`
  - `src/babylon/economics/melt/imperial_rent.py`
- [x] T005 Update `src/babylon/economics/__init__.py` to export new module symbols

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Document data source protocols in `src/babylon/economics/melt/data_sources.py`:
  - `BEADataSource` protocol (GDP by year)
  - `QCEWDataSource` protocol (employment by year)
  - `CPIDataSource` protocol (inflation adjustment) [CHK044]
- [x] T007 Document TensorRegistry integration pattern in module docstring referencing `src/babylon/economics/tensor.py` patterns for NoDataSentinel [CHK040]
- [x] T008 Add Feature 012 integration points to module docstring:
  - Reference `CapitalStockCalculator` service pattern
  - Reference `TensorRegistry.get_tensor()` cache pattern
  - Document how NationalParameters will integrate with ValueTensor [CHK039]
- [x] T009 Specify cache invalidation strategy in `parameters.py` docstring:
  - Annual parameters cached by (year) key
  - Cache invalidated on: data source refresh, year boundary crossing
  - Thread-safe access via immutable NationalParameters [CHK042]
- [x] T010 Define CPI data source for V_reproduction in `data_sources.py`:
  - BLS CPI-U (All Urban Consumers) series CUUR0000SA0
  - Base year: 2024 for $12/hour subsistence floor
  - Formula: V_reproduction(year) = $12 × (CPI_2024 / CPI_year) [CHK044]
- [x] T011 Create `tests/unit/economics/melt/` directory structure with `conftest.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

______________________________________________________________________

## Phase 3: User Story 1 - Compute National MELT (Priority: P1) MVP

**Goal**: Compute τ = GDP / L for any year in [2010, 2024] range

**Independent Test**: `pytest tests/unit/economics/melt/test_melt_calculator.py -v`

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T012 [P] [US1] Create `tests/unit/economics/melt/test_melt_calculator.py`:
  - Test τ computation with mock GDP and employment data
  - Test NoDataSentinel return with descriptive reason for missing GDP [CHK030]
  - Test NoDataSentinel return with DISTINCT reason for missing employment [CHK030]
  - Test year range validation [2010, 2024]
  - Test sanity validation: expected ($55-75), warning ($40-100), fail (<$20 or >$200)
  - Test edge case: year exactly at boundaries (2010, 2024)

### Implementation for User Story 1

- [x] T013 [US1] Implement `DefaultMELTCalculator` in `src/babylon/economics/melt/melt_calculator.py`:
  - `get_melt(year: int) -> float | NoDataSentinel`
  - Formula: τ = GDP / (employment × 2080)
  - Return NoDataSentinel with reason "GDP data unavailable for year {year}" [CHK030]
  - Return NoDataSentinel with reason "Employment data unavailable for year {year}" [CHK030]
- [x] T014 [US1] Implement `validate_melt(tau: float) -> tuple[bool, str | None]`:
  - Expected range: $55-75/hour (valid=True, message=None)
  - Warning range: $40-100/hour (valid=True, message=warning)
  - Fail range: <$20 or >$200/hour (valid=False, message=error)
  - Empirical basis: BEA NIPA + QCEW 2010-2024 regression
- [x] T015 [US1] Implement `data_range` property returning (2010, 2024)
- [x] T016 [US1] Create mock data source implementations for testing:
  - `MockBEADataSource` with configurable GDP values
  - `MockQCEWDataSource` with configurable employment values

**Checkpoint**: US1 complete - can compute and validate national MELT independently

______________________________________________________________________

## Phase 4: User Story 2 - Determine Class Position Thresholds (Priority: P1)

**Goal**: Classify wages into LABOR_ARISTOCRACY, PROLETARIAT, SUBPROLETARIAT

**Independent Test**: `pytest tests/unit/economics/melt/test_class_position.py -v`

### Tests for User Story 2

- [x] T017 [P] [US2] Create `tests/unit/economics/melt/test_class_position.py`:
  - Test ClassPosition enum has exactly 3 values
  - Test classification: wage > τ_effective → LABOR_ARISTOCRACY
  - Test classification: τ_effective >= wage > V_reproduction → PROLETARIAT
  - Test classification: wage <= V_reproduction → SUBPROLETARIAT
  - Test boundary case: wage == τ_effective (should be PROLETARIAT)
  - Test boundary case: wage == V_reproduction (should be SUBPROLETARIAT)
  - Test classify_distribution returns correct shares

### Implementation for User Story 2

- [x] T018 [US2] Finalize ClassPosition enum in `types.py`:
  - LABOR_ARISTOCRACY = auto()
  - PROLETARIAT = auto()
  - SUBPROLETARIAT = auto()
  - Add docstring explaining wage-based classification limitation
  - Document: Cannot identify bourgeoisie (non-wage) or lumpen (excluded from production)
- [x] T019 [US2] Implement `DefaultClassPositionClassifier` in `class_position.py`:
  - `classify(wage: float, params: NationalParameters) -> ClassPosition`
  - `classify_distribution(wages: Sequence[float], params: NationalParameters) -> dict[ClassPosition, float]`
- [x] T020 [US2] Add validation for NationalParameters consistency:
  - τ_effective == τ × γ_basket (within 0.01 tolerance)
  - V_reproduction < τ_effective (required for valid classification)

**Checkpoint**: US2 complete - can classify wages into class positions independently

______________________________________________________________________

## Phase 5: User Story 3 - Calculate Basket Visibility (Priority: P2)

**Goal**: Compute γ_basket from import share and peripheral visibility

**Independent Test**: `pytest tests/unit/economics/melt/test_basket_visibility.py -v`

### Tests for User Story 3

- [x] T021 [P] [US3] Create `tests/unit/economics/melt/test_basket_visibility.py`:
  - Test γ_basket formula: γ_basket = 1 / (α/γ_import + (1-α))
  - Test MVP mode returns (0.68, True) when no data
  - Test edge case α=0: returns γ_basket=1.0 (no imports, no subsidy)
  - Test edge case α=1: returns γ_basket=γ_import (100% imports)
  - Test sanity validation ranges: expected (0.60-0.80), warning (0.40-0.95), fail (<0.1 or >1.0)
  - Test mvp_alpha property returns 0.25
  - Test mvp_gamma_import property returns 0.35
  - Test mvp_gamma_basket property returns 0.68

### Implementation for User Story 3

- [x] T022 [US3] Implement `DefaultBasketVisibilityCalculator` in `basket_visibility.py`:
  - `get_gamma_basket(year: int, alpha: float | None, gamma_import: float | None) -> tuple[float, bool]`
  - When alpha/gamma_import not provided, return MVP values with estimated=True
  - Formula: γ_basket = 1 / (α/γ_import + (1-α))
- [x] T023 [US3] Implement `validate_gamma_basket(gamma: float) -> tuple[bool, str | None]`:
  - Expected range: 0.60-0.80 (valid=True, message=None)
  - Warning range: 0.40-0.95 (valid=True, message=warning)
  - Fail range: <0.1 or >1.0 (valid=False, message=error)
- [x] T024 [US3] Implement MVP constant properties:
  - `mvp_gamma_basket` = 0.68
  - `mvp_alpha` = 0.25 (Hickel et al. methodology)
  - `mvp_gamma_import` = 0.35 (weighted average ERDI)
- [x] T025 [US3] Add docstring documenting MVP derivation:
  - α ≈ 0.25: Import share per Hickel et al. (2022) methodology
  - γ_import ≈ 0.35: Trade-weighted average ERDI of US partners
  - γ_basket = 1 / (0.25/0.35 + 0.75) ≈ 0.68

**Checkpoint**: US3 complete - can compute basket visibility independently

______________________________________________________________________

## Phase 6: User Story 4 - County Workforce Classification (Priority: P2)

**Goal**: Aggregate individual classifications to county-level class distribution

**Independent Test**: `pytest tests/unit/economics/melt/test_county_classification.py -v`

### Tests for User Story 4

- [x] T026 [P] [US4] Create `tests/unit/economics/melt/test_county_classification.py`:
  - Test classify_distribution returns dict with all 3 ClassPosition keys
  - Test shares sum to 1.0 (within floating point tolerance)
  - Test empty wage list returns equal shares (0.333...)
  - Test single wage returns 100% in appropriate class

### Implementation for User Story 4

- [x] T027 [US4] Extend `classify_distribution` in `class_position.py`:
  - Accept `weights: Sequence[float] | None` for employment-weighted aggregation
  - Return `dict[ClassPosition, float]` with shares summing to 1.0
- [x] T028 [US4] Add FIPS code documentation for Detroit validation case:
  - Wayne County (Detroit proper): FIPS 26163
  - Oakland County (suburbs): FIPS 26125
  - Expected: Oakland LA share > Wayne LA share

**Checkpoint**: US4 complete - can classify county workforces independently

______________________________________________________________________

## Phase 7: User Story 5 - Calculate Imperial Rent per Hour (Priority: P3)

**Goal**: Compute Φ_hour and L_commanded per TVT Axioms E3-E4

**Independent Test**: `pytest tests/unit/economics/melt/test_imperial_rent.py -v`

### Tests for User Story 5

- [x] T029 [P] [US5] Create `tests/unit/economics/melt/test_imperial_rent.py`:
  - Test Φ_hour formula: Φ_hour = (W/τ) × (1/γ_basket) - 1
  - Test L_commanded formula: L_commanded = (W/τ) × (1/γ_basket)
  - Test relationship: Φ_hour = L_commanded - 1
  - Test break-even case: W = τ_effective → Φ_hour = 0
  - Test Labor Aristocracy: W > τ_effective → Φ_hour > 0
  - Test Proletariat: W < τ_effective → Φ_hour < 0
  - Test theoretical bounds: phi_at_zero approaches -1
  - Test is_labor_aristocracy predicate

### Implementation for User Story 5

- [x] T030 [US5] Implement `DefaultImperialRentCalculator` in `imperial_rent.py`:
  - `compute_phi_hour(wage: float, params: NationalParameters) -> float`
  - `compute_labor_commanded(wage: float, params: NationalParameters) -> float`
  - `is_labor_aristocracy(wage: float, params: NationalParameters) -> bool`
- [x] T031 [US5] Implement `get_theoretical_bounds(params: NationalParameters) -> dict[str, float]`:
  - `phi_at_zero`: Limit as W → 0 (approaches -1)
  - `phi_at_threshold`: Φ_hour when W = τ_effective (equals 0)
  - `phi_at_tau`: Φ_hour when W = τ (depends on γ_basket)
  - `l_cmd_at_threshold`: L_commanded when W = τ_effective (equals 1)
- [x] T032 [US5] Add algebraic proof in docstring:
  ```
  Break-Even Proof:
  At W = τ_effective = τ × γ_basket:
  Φ_hour = (W/τ) × (1/γ_basket) - 1
         = (τ × γ_basket / τ) × (1/γ_basket) - 1
         = γ_basket × (1/γ_basket) - 1
         = 1 - 1 = 0 ✓
  ```

**Checkpoint**: US5 complete - can compute imperial rent metrics independently

______________________________________________________________________

## Phase 8: Integration & Validation

**Purpose**: End-to-end integration and validation against success criteria

### Integration Tests

- [ ] T033 [P] Create `tests/integration/economics/test_melt_integration.py`:
  - Test full pipeline: MELT → γ_basket → NationalParameters → ClassPosition → Φ_hour
  - Test NationalParameters construction from calculator outputs
  - Test quickstart.md examples execute without error
- [ ] T034 Verify Detroit Metro validation case:
  - Create test with mock Wayne/Oakland wage distributions
  - Assert Oakland LA share > Wayne LA share

### Data Source Integration

- [ ] T035 [P] Create `src/babylon/economics/melt/bea_source.py`:
  - Implement BEADataSource protocol with real BEA NIPA API
  - Cache GDP values by year
- [ ] T036 [P] Create `src/babylon/economics/melt/qcew_source.py`:
  - Implement QCEWDataSource protocol with BLS QCEW data
  - Cache employment values by year
- [ ] T037 [P] Create `src/babylon/economics/melt/cpi_source.py`:
  - Implement CPIDataSource protocol with BLS CPI-U series
  - Cache CPI values by year

______________________________________________________________________

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and checklist gap resolution

### Documentation

- [ ] T038 [P] Update `src/babylon/economics/__init__.py` with complete exports:
  - ClassPosition, NationalParameters
  - MELTCalculator, BasketVisibilityCalculator
  - ClassPositionClassifier, ImperialRentCalculator
  - Default implementations
- [ ] T039 [P] Add TVT axiom references to all calculator docstrings:
  - MELTCalculator: TVT Axiom B3
  - BasketVisibilityCalculator: TVT Axiom D3
  - ClassPositionClassifier: TVT Axioms C1, E1-E2
  - ImperialRentCalculator: TVT Axioms E3-E4
- [ ] T040 Update CLAUDE.md Active Technologies section with Feature 013

### Checklist Gap Resolution Tasks

- [ ] T050 [P] Create `tests/unit/economics/melt/test_literature_validation.py` [CHK038]:
  - Test τ ≈ $65/hour (2022) within ±10% of BEA/QCEW derived value
  - Test γ_basket ≈ 0.68 within ±10% of Hickel et al. derived value
  - Document literature sources in test docstring
- [ ] T051 [P] Create `tests/unit/economics/melt/test_sc002_measurability.py` [CHK046]:
  - Test LA share 30-50% against 2022 QCEW national wage distribution
  - Document: τ_effective ≈ $44/hour, QCEW median ≈ $28/hour
  - Assert: workers above $44/hour represent 30-50% of workforce
- [ ] T052 [P] Add "average wage" definition to spec documentation [CHK048]:
  - Define: "average US worker wage" = median hourly wage from QCEW
  - 2022 median: ~$28/hour (BLS QCEW)
  - Assert: Φ_hour($28, params_2022) > 0 validates SC-004
- [ ] T053 [P] Create `tests/integration/economics/test_melt_regression.py` [CHK050]:
  - Test existing ValueTensor consumers still work after melt module addition
  - Test TensorRegistry.get_tensor() not affected
  - Test no import errors from existing economics module users

### Final Validation

- [ ] T054 Run `quickstart.md` examples and verify output matches expected
- [ ] T055 Update `checklists/tvt-domain-review.md` to mark resolved gaps
- [ ] T056 Run full test suite: `mise run test:unit && mise run test:int`

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
┌───────────┬───────────┬───────────┬───────────┐
│ Phase 3   │ Phase 4   │ Phase 5   │ Phase 6   │
│ US1 (P1)  │ US2 (P1)  │ US3 (P2)  │ US4 (P2)  │
│ MELT      │ ClassPos  │ γ_basket  │ County    │
└─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘
      │           │           │           │
      └───────────┴───────────┴───────────┘
                      ↓
              Phase 7: US5 (P3)
              Imperial Rent
                      ↓
              Phase 8: Integration
                      ↓
              Phase 9: Polish
```

### User Story Dependencies

- **US1 (MELT)**: Foundation only - no story dependencies
- **US2 (ClassPosition)**: Requires NationalParameters (shared with US1)
- **US3 (γ_basket)**: Foundation only - can run parallel with US1/US2
- **US4 (County)**: Requires ClassPositionClassifier from US2
- **US5 (Imperial Rent)**: Requires NationalParameters, uses all calculators

### Parallel Opportunities

**After Phase 2 completes, these can run in parallel:**
- US1 tests + implementation (T012-T016)
- US2 tests + implementation (T017-T020)
- US3 tests + implementation (T021-T025)

**Within each phase, [P] tasks can run in parallel:**
- T002, T003, T004 (module stubs)
- T012, T017, T021, T026, T029 (all test files)
- T035, T036, T037 (data source implementations)

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (MELT computation)
4. Complete Phase 4: US2 (Class position classification)
5. **STOP and VALIDATE**: Can compute τ and classify wages
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 + US2 → Core classification working (MVP!)
3. US3 → γ_basket computation (enables customization)
4. US4 → County aggregation (enables geographic analysis)
5. US5 → Imperial rent metrics (full theoretical framework)

### Parallel Team Strategy

With multiple developers:
1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (MELT) + US3 (γ_basket)
   - Developer B: US2 (ClassPosition) + US4 (County)
3. Both complete → US5 can begin
4. Integration tests verify all components work together

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD Red-Green-Refactor)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Checklist gaps (CHK###) mapped to specific tasks for traceability
