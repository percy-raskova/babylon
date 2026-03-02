# Tasks: Unified Class System

**Input**: Design documents from `/specs/038-unified-class-system/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: TDD (Red-Green-Refactor) per CLAUDE.md — tests included in each phase.

**Organization**: Tasks grouped by user story. Each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- All paths relative to repository root

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add shared types, constants, and configuration that all user stories depend on.

- [ ] T001 Add ClassSystem test constant group (wealth percentiles, precarity values, community memberships, rent values) to tests/constants.py
- [ ] T002 [P] Add CALIBRATION_DISAGREEMENT value to EventType enum in src/babylon/models/enums.py

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ClassSystemDefines sub-model in GameDefines — every user story reads these coefficients.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Create ClassSystemDefines frozen model with trust_land_discount, documentation_exclusion_factor, equity_factor, and base_class_solidarity matrix (15-value upper-triangle dict) in src/babylon/config/defines.py
- [ ] T004 Implement get_base_solidarity(class_a, class_b) symmetric accessor method on ClassSystemDefines with model_validator for matrix entry bounds in src/babylon/config/defines.py
- [ ] T005 Wire ClassSystemDefines into GameDefines as class_system field and add to _from_yaml_dict loader in src/babylon/config/defines.py

**Checkpoint**: `GameDefines().class_system.get_base_solidarity("PROLETARIAT", "PROLETARIAT")` returns `0.80`. All existing tests still pass.

______________________________________________________________________

## Phase 3: User Story 1 — Classify Household Class Position (Priority: P1) MVP

**Goal**: Classify households into one of five ClassPosition values using wealth percentile + precarity, with dual-criteria validation logging (FR-001, FR-002, FR-012).

**Independent Test**: Provide known wealth percentile + precarity -> verify ClassPosition. Verify backward compatibility (no filtration = same as DefaultClassPositionClassifier).

### Tests (Red Phase)

- [ ] T006 [P] [US1] Write red-phase tests for DualCriteriaResult model validation (agrees/magnitude consistency, frozen immutability) in tests/unit/economics/melt/test_unified_classifier.py
- [ ] T007 [P] [US1] Write red-phase tests for classify_with_filtration no-filtration path: all 6 acceptance scenarios from spec (75th->LA, 25th+STABLE->PROL, 10th+EXCLUDED->LUMPEN, 95th->PB, 99.5th->BOURG, 55th+EXCLUDED->LA) in tests/unit/economics/melt/test_unified_classifier.py
- [ ] T008 [P] [US1] Write red-phase tests for classify_dual_criteria: agreement case, disagreement case, magnitude computation, CALIBRATION_DISAGREEMENT event emission in tests/unit/economics/melt/test_unified_classifier.py

### Implementation (Green Phase)

- [ ] T009 [US1] Create DualCriteriaResult frozen Pydantic model with wealth_class, accounting_class, agrees, magnitude fields and model_validator in src/babylon/economics/melt/unified_classifier.py
- [ ] T010 [US1] Implement UnifiedClassifier protocol (classify_with_filtration, apply_filtration, classify_dual_criteria) and DefaultUnifiedClassifier wrapping DefaultClassPositionClassifier in src/babylon/economics/melt/unified_classifier.py
- [ ] T011 [US1] Implement accounting criterion classification (V_produced vs V_reproduction mapping to ClassPosition) in DefaultUnifiedClassifier.classify_dual_criteria in src/babylon/economics/melt/unified_classifier.py
- [ ] T012 [US1] Export UnifiedClassifier, DefaultUnifiedClassifier, DualCriteriaResult from src/babylon/economics/melt/__init__.py
- [ ] T013 [US1] Run green-phase: all US1 tests pass, existing melt tests unbroken

**Checkpoint**: `DefaultUnifiedClassifier().classify_with_filtration(75.0, PrecarityStatus.STABLE)` returns `ClassPosition.LABOR_ARISTOCRACY`. Result identical to `DefaultClassPositionClassifier.classify_by_wealth_and_precarity(75.0, PrecarityStatus.STABLE)`.

______________________________________________________________________

## Phase 4: User Story 2 — Apply Community Filtration (Priority: P1)

**Goal**: Community memberships (FIRST_NATIONS, INCARCERATED, UNDOCUMENTED, DISABLED) modify classification inputs via filtration predicates (FR-003, FR-004). Home ownership LA proxy reads equity_factor from GameDefines and applies trust_land_discount to reservation counties (FR-005).

**Independent Test**: Provide households with known community memberships + wealth. Verify filtration shifts classification in expected direction relative to unfiltered baseline. Verify LA proxy reads from ClassSystemDefines.

### Tests (Red Phase)

- [ ] T014 [P] [US2] Write red-phase tests for FiltrationResult model validation (effective <= original wealth, precarity severity ordering, frozen immutability) in tests/unit/economics/melt/test_filtration.py
- [ ] T015 [P] [US2] Write red-phase tests for each filtration predicate: FIRST_NATIONS trust_land_discount, INCARCERATED precarity override to EXCLUDED, UNDOCUMENTED documentation_exclusion_factor + precarity floor, DISABLED reproduction_cost_modifier in tests/unit/economics/melt/test_filtration.py
- [ ] T016 [P] [US2] Write red-phase tests for multi-membership composition: most-restrictive-wins (FR-004), FIRST_NATIONS overrides SETTLER, order-independence, SETTLER-only = no change in tests/unit/economics/melt/test_filtration.py
- [ ] T017 [P] [US2] Write red-phase tests for classify_with_filtration with filtration: 60th+FIRST_NATIONS->PROL, 45th+INCARCERATED->LUMPEN, 55th+UNDOCUMENTED->shifted, 65th+DISABLED->shifted, multi-membership in tests/unit/economics/melt/test_unified_classifier.py
- [ ] T018 [P] [US2] Write red-phase tests for WealthProxyCalculator reading equity_factor from ClassSystemDefines and trust_land_discount applied to reservation-county home ownership rates (FR-005) in tests/unit/economics/melt/test_wealth_proxy.py

### Implementation (Green Phase)

- [ ] T019 [US2] Implement precarity_severity() comparison helper (STABLE<PRECARIOUS<MARGINALLY_ATTACHED<EXCLUDED) in src/babylon/economics/melt/filtration.py
- [ ] T020 [US2] Create FiltrationResult frozen Pydantic model with model_validator enforcing effective<=original in src/babylon/economics/melt/filtration.py
- [ ] T021 [US2] Implement four filtration predicate functions (one per community type: FIRST_NATIONS, INCARCERATED, UNDOCUMENTED, DISABLED) in src/babylon/economics/melt/filtration.py
- [ ] T022 [US2] Implement apply_filtration() orchestrator: iterate memberships, apply each predicate independently against original inputs, select most-restrictive composite result in src/babylon/economics/melt/filtration.py
- [ ] T023 [US2] Wire apply_filtration into DefaultUnifiedClassifier.classify_with_filtration (filtration path when memberships provided) in src/babylon/economics/melt/unified_classifier.py
- [ ] T024 [US2] Export FiltrationResult, apply_filtration from src/babylon/economics/melt/__init__.py
- [ ] T025 [US2] Update DefaultWealthProxyCalculator to read equity_factor from ClassSystemDefines instead of hardcoded EQUITY_FACTOR constant (FR-005, FR-011) in src/babylon/economics/melt/wealth_proxy.py
- [ ] T026 [US2] Apply trust_land_discount to reservation-county home ownership rates in WealthProxyCalculator LA share computation, using FIPS-based reservation identification (FR-005) in src/babylon/economics/melt/wealth_proxy.py
- [ ] T027 [US2] Run green-phase: all US2 tests pass, US1 tests still pass

**Checkpoint**: `classify_with_filtration(60.0, STABLE, [FIRST_NATIONS_membership], states)` returns `PROLETARIAT` (60 * 0.5 = 30th percentile after trust_land_discount). Without memberships, same call returns `LABOR_ARISTOCRACY`. `DefaultWealthProxyCalculator` reads `equity_factor` from `ClassSystemDefines`.

______________________________________________________________________

## Phase 5: User Story 3 — Compute Solidarity Potential (Priority: P2)

**Goal**: Solidarity potential between agent-pairs uses class-pair matrix for base_solidarity instead of flat constant (FR-006).

**Independent Test**: Provide pairs with known class positions, community overlap, rent values. Verify solidarity potential uses matrix lookup and exhibits monotonicity properties.

### Tests (Red Phase)

- [ ] T028 [P] [US3] Write red-phase tests for get_base_solidarity: symmetry (BC-010), known pair values, unknown pair returns 0.0 in tests/unit/config/test_class_system_defines.py
- [ ] T029 [P] [US3] Write red-phase tests for solidarity potential with matrix: negative output permitted (BC-011), monotonic community overlap (BC-012), monotonic rent differential (BC-013), zero-overlap baseline (BC-014) in tests/unit/formulas/test_community.py

### Implementation (Green Phase)

- [ ] T030 [US3] Extend CommunitySystem to read ClassSystemDefines.get_base_solidarity for agent-pair solidarity potential computation (replace flat base_solidarity with matrix lookup by agent class positions) in src/babylon/engine/systems/community.py
- [ ] T031 [US3] Run green-phase: all US3 tests pass, existing community system tests pass

**Checkpoint**: Two PROLETARIAT agents get `base_solidarity=0.80`. One BOURGEOISIE + one PROLETARIAT get `base_solidarity=0.00`. Parameter sweep confirms SC-007 monotonicity.

______________________________________________________________________

## Phase 6: User Story 4 — Compute National Rent Differential (Priority: P2)

**Goal**: Compute nation-specific Phi_hour differentials from ACS earnings data by race x NAICS at county level (FR-007).

**Independent Test**: Provide mock ACS earnings data. Verify positive differential for settler > colonized, NoDataSentinel for suppressed codes, employment-weighted aggregation.

### Tests (Red Phase)

- [ ] T032 [P] [US4] Write red-phase tests for RentDifferentialResult model validation (fips pattern, year bounds, naics_count + suppressed_count > 0) in tests/unit/economics/melt/test_rent_differential.py
- [ ] T033 [P] [US4] Write red-phase tests for compute_differential: positive sign (BC-016), suppressed data returns NoDataSentinel (BC-015), SETTLER self-differential = 0 (BC-019) in tests/unit/economics/melt/test_rent_differential.py
- [ ] T034 [P] [US4] Write red-phase tests for compute_county_aggregate: employment-weighted (BC-017), all-suppressed returns NoDataSentinel (BC-018), Wayne >= Oakland differential (BC-020) in tests/unit/economics/melt/test_rent_differential.py

### Implementation (Green Phase)

- [ ] T035 [US4] Create RentDifferentialResult frozen Pydantic model with fips, nation, year, differential, naics_count, suppressed_count in src/babylon/economics/melt/rent_differential.py
- [ ] T036 [US4] Implement RentDifferentialCalculator protocol and DefaultRentDifferentialCalculator with mock ACS earnings data (same pattern as DefaultWealthProxyCalculator) in src/babylon/economics/melt/rent_differential.py
- [ ] T037 [US4] Implement compute_differential (single NAICS) with NoDataSentinel propagation and compute_county_aggregate (employment-weighted) in src/babylon/economics/melt/rent_differential.py
- [ ] T038 [US4] Export RentDifferentialCalculator, DefaultRentDifferentialCalculator, RentDifferentialResult from src/babylon/economics/melt/__init__.py
- [ ] T039 [US4] Run green-phase: all US4 tests pass

**Checkpoint**: `compute_county_aggregate("26163", CommunityType.NEW_AFRIKAN, 2022)` returns positive float. `compute_differential("26163", CommunityType.SETTLER, "31-33", 2022)` returns 0.0.

______________________________________________________________________

## Phase 7: User Story 5 — DPD' Lifecycle Class Reproduction (Priority: P3)

**Goal**: Inheritance flows at D'->D transitions differentiated by class position. Foreclosure severs inheritance (FR-008, FR-010).

**Independent Test**: Provide LA household at D'->D transition with/without foreclosure. Verify inheritance preserves or disrupts class position.

**Note**: Per assumption A-007, if Feature 030 InheritanceCalculator is not yet integrated, inheritance defaults to zero and DPD'-dependent scenarios are deferred. Tasks below extend the existing lifecycle infrastructure.

### Tests (Red Phase)

- [ ] T040 [P] [US5] Write red-phase tests for class-differentiated inheritance: LA household transfers equity, PROLETARIAT transfers near-zero, foreclosed LA transfers zero in tests/unit/economics/lifecycle/test_class_inheritance.py
- [ ] T041 [P] [US5] Write red-phase tests for crisis dispossession: LA->PROLETARIAT transition via wealth destruction, community-modifiable dispossession rate in tests/unit/economics/lifecycle/test_class_inheritance.py

### Implementation (Green Phase)

- [ ] T042 [US5] Extend DefaultInheritanceCalculator to differentiate inheritance amounts by ClassPosition (add class-aware inheritance scaling to existing compute_inheritance method) in src/babylon/economics/lifecycle/inheritance.py
- [ ] T043 [US5] Implement crisis dispossession logic: foreclosure event severs inheritance, dispossession rate modifiable by community membership in src/babylon/economics/lifecycle/dispossession.py
- [ ] T044 [US5] Run green-phase: all US5 tests pass, existing lifecycle tests pass

**Checkpoint**: LA household D'->D produces `net_inheritance > 0`. Same household with foreclosure flag produces `net_inheritance == 0`.

______________________________________________________________________

## Phase 8: User Story 6 — Validate Fractal Consistency (Priority: P3)

**Goal**: Same ClassPosition enum and classification logic works at both metro and sub-county zoom levels (FR-009).

**Independent Test**: Apply UnifiedClassifier at metro Detroit scale. Zoom into Core Non-Bourgeoisie. Verify internal structure replicates four-node pattern.

### Tests (Red Phase)

- [ ] T045 [P] [US6] Write red-phase tests for fractal consistency: same ClassPosition enum at sub-scale, Wayne has higher PROLETARIAT+LUMPEN share than Oakland, valid classifications at both resolutions in tests/unit/economics/melt/test_fractal_consistency.py

### Implementation (Green Phase)

- [ ] T046 [US6] Implement fractal zoom validation helper that applies UnifiedClassifier at sub-county resolution and verifies four-node pattern replication in src/babylon/economics/melt/unified_classifier.py
- [ ] T047 [US6] Add Detroit tri-county validation data (Wayne 26163 vs Oakland 26125 class distributions) to DefaultWealthProxyCalculator or test fixtures in tests/unit/economics/melt/test_fractal_consistency.py
- [ ] T048 [US6] Run green-phase: all US6 tests pass

**Checkpoint**: Classification at metro scale and sub-county scale produce valid ClassPosition values using the same code path. Wayne County PROLETARIAT+LUMPEN share > Oakland County.

______________________________________________________________________

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance, backward compatibility verification, integration stubs, and documentation.

- [ ] T049 [P] Run mypy strict on all new and modified files: src/babylon/economics/melt/filtration.py, unified_classifier.py, rent_differential.py, wealth_proxy.py, src/babylon/config/defines.py
- [ ] T050 [P] Run ruff lint + format on all new and modified files
- [ ] T051 Verify backward compatibility: run full existing melt test suite (poetry run pytest tests/unit/economics/melt/ -v) — zero regressions
- [ ] T052 Run full unit test suite (mise run test:unit) — all tests pass
- [ ] T053 Verify quickstart.md code examples execute correctly

### Deferred Success Criteria (Integration-Level Validation)

The following success criteria require simulation-level validation with historical data, not unit tests. They are validated during integration testing or simulation runs, not during this task sequence:

- **SC-001** (>=90% accounting-wealth agreement on Detroit data): Requires hydrated county data + simulation tick. Validated during Feature 026 tri-county substrate integration.
- **SC-002** (Pareto emergence 1%/9%/40%/50%): Requires multi-tick simulation run. Validated during integration testing with full engine.
- **SC-004** (crisis dispossession r > 0.6 with foreclosure): Requires 2008-2012 historical data. Validated during Feature 026 + Feature 030 integration.

- [ ] T054 [P] Create integration test stubs for SC-001, SC-002, SC-004 with @pytest.mark.integration and skip decorator pending Feature 026 data hydration in tests/integration/economics/test_class_system_integration.py
- [ ] T055 Verify all unit tests and integration stubs pass (mise run test:unit && poetry run pytest tests/integration/economics/ -v --co)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP target
- **US2 (Phase 4)**: Depends on US1 (extends UnifiedClassifier with filtration path)
- **US3 (Phase 5)**: Depends on Foundational only (uses ClassSystemDefines.get_base_solidarity)
- **US4 (Phase 6)**: Depends on Foundational only (independent new module)
- **US5 (Phase 7)**: Depends on US1 (uses ClassPosition from unified classifier)
- **US6 (Phase 8)**: Depends on US1 + US2 (validates full classification pipeline)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1 (Setup) --> Phase 2 (Foundational)
                         |
                    +----+----------+
                    v    v          v
               Phase 3  Phase 5   Phase 6
               (US1)    (US3)     (US4)
                 |
                 v
               Phase 4 ----------> Phase 8
               (US2)               (US6)
                 |
                 v
               Phase 7
               (US5)
                                    |
                    All ----------> Phase 9 (Polish)
```

### Within Each User Story

- Red-phase tests written FIRST (all [P] within a phase can be parallel)
- Models before service logic
- Service logic before wiring/integration
- Green-phase verification at end of each phase
- Commit after each phase completion

### Parallel Opportunities

**Within Phase 1**: T001 and T002 are [P] — different files
**Within Phase 3 Red**: T006, T007, T008 are [P] — same file but independent test classes
**Within Phase 4 Red**: T014, T015, T016, T017, T018 are [P] — different test files/classes
**Between Phases**: US3 (Phase 5) and US4 (Phase 6) can run in parallel after Foundational
**Within Phase 5 Red**: T028, T029 are [P] — different test files
**Within Phase 6 Red**: T032, T033, T034 are [P] — independent test classes
**Within Phase 9**: T049 and T050 are [P] — different tools

______________________________________________________________________

## Parallel Example: User Story 2

```bash
# Red phase — all tests in parallel:
Task T014: "FiltrationResult validation tests in test_filtration.py"
Task T015: "Per-predicate filtration tests in test_filtration.py"
Task T016: "Multi-membership composition tests in test_filtration.py"
Task T017: "Filtration-path classification tests in test_unified_classifier.py"
Task T018: "WealthProxyCalculator + ClassSystemDefines tests in test_wealth_proxy.py"

# Green phase — sequential:
Task T019: Precarity severity helper
Task T020: FiltrationResult model
Task T021: Four predicate functions
Task T022: apply_filtration() orchestrator
Task T023: Wire into UnifiedClassifier
Task T024: Package exports
Task T025: Update WealthProxyCalculator equity_factor source
Task T026: Trust_land_discount on reservation counties
Task T027: Verify all tests green
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005)
3. Complete Phase 3: User Story 1 (T006-T013)
4. **STOP and VALIDATE**: classify_with_filtration works without filtration, dual-criteria logs disagreements
5. Backward compatibility confirmed

### Incremental Delivery

1. Setup + Foundational -> ClassSystemDefines in GameDefines
2. US1 -> Basic classification with dual-criteria -> **MVP**
3. US2 -> Community filtration + FR-005 LA proxy update -> Core feature complete
4. US3 + US4 (parallel) -> Solidarity matrix + rent differential -> Bifurcation inputs ready
5. US5 -> Lifecycle inheritance -> Class reproduction dynamics
6. US6 -> Fractal validation -> Constitutional compliance confirmed
7. Polish -> Full test suite green, mypy/ruff clean, integration stubs placed

### Suggested MVP Scope

**US1 alone** (Phase 1-3, tasks T001-T013) delivers:
- UnifiedClassifier with backward-compatible classification
- Dual-criteria validation with event bus logging
- All coefficients in GameDefines
- 13 tasks, ~300 lines production code, ~400 lines test code

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to user story for traceability
- Each user story is independently testable at its checkpoint
- TDD: write tests first (red), implement (green), refactor
- Commit after each phase completion per CLAUDE.md
- FIRST_NATIONS in code = "INDIGENOUS" in spec (research.md R-003)
- Feature 026 (tri-county substrate) is spec-only — use mock data for testing
- Feature 030 (DPD') defaults to zero inheritance if not yet integrated (A-007)
- SC-001, SC-002, SC-004 deferred to integration testing (requires simulation-level data)
