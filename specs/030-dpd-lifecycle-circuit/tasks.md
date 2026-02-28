# Tasks: D-P-D' Lifecycle Circuit

**Input**: Design documents from `/specs/030-dpd-lifecycle-circuit/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/lifecycle-system-contract.md, quickstart.md

**Tests**: Included per project TDD requirement (CLAUDE.md mandates Red-Green-Refactor).

**Organization**: Tasks grouped by user story. User stories ordered by spec priority (P1 → P2 → P3 → P4 → P5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US7)
- Exact file paths included in all descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure, shared types, GameDefines category, and EventType values that all user stories depend on.

- [ ] T001 Create lifecycle module directory structure: `src/babylon/economics/lifecycle/` with `__init__.py`, and `tests/unit/economics/lifecycle/` with `__init__.py`
- [ ] T002 Add `LifecycleDefines` frozen Pydantic model (36 fields with defaults and provenance) to `src/babylon/config/defines.py`, wire into `GameDefines` and `_from_yaml_dict`. Include legitimation weight ranking invariant validation and mobility P25<=P75 validation. See data-model.md LifecycleDefines table for all fields, including covariate defaults and ideology_regression_coefficient.
- [ ] T003 [P] Add 5 lifecycle `EventType` values (`LIFECYCLE_TRANSITION`, `LEGITIMATION_CRISIS`, `LEGITIMATION_RECOVERY`, `INHERITANCE_TRANSFER`, `DUAL_CIRCUIT_INTERFERENCE`) and `LegitimationClassification` enum (`CRISIS`, `UNSTABLE`, `STABLE`) to `src/babylon/models/enums.py`
- [ ] T004 [P] Create lifecycle types (`DPDState`, `LegitimationState`, `InheritanceFlow`, `ClassMobilityParams`) as frozen Pydantic models with constrained types in `src/babylon/economics/lifecycle/types.py`. See data-model.md for fields, constraints, and computed properties. All populations as `float >= 0`, rates as `Coefficient`, legitimation components as `Probability`, wealth as `Currency`, gini as `Gini`. ClassMobilityParams includes 10 fields: mobility rates (P25, P75), racial gap, carceral/mortality modifiers, and 5 D-phase context covariates (baseline_gini, poverty_share, employment_rate, single_parent_fraction, college_rate).

**Checkpoint**: Module structure exists. Types importable. GameDefines has lifecycle category. Enums extended.

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure formulas and package exports that all user stories consume. MUST complete before any user story.

- [ ] T005 Write failing tests for pure lifecycle formulas (population flow, dependency ratio, legitimation index, Pareto Gini, ideology blend, shadow subsidy) in `tests/unit/formulas/test_lifecycle_formulas.py`. Use `@pytest.mark.math`. Cover: conservation arithmetic, zero-population edge case, legitimation weight ordering, Pareto α→Gini conversion, ideology regression toward mean.
- [ ] T006 Implement pure lifecycle formulas in `src/babylon/formulas/lifecycle.py`: `compute_population_flow(pop_D, pop_P, pop_D_prime, rates, birth_rate) -> tuple[float, ...]`, `compute_dependency_ratio(pop_D, pop_P, pop_D_prime) -> float`, `compute_legitimation_index(components, weights) -> float`, `compute_pareto_gini(alpha) -> float`, `compute_ideology_transmission(caregiver, institutional, caregiver_weight) -> float`, `compute_shadow_subsidy(d_g2_cost, wage_premium) -> float`. Register in `FormulaRegistry.default()`.
- [ ] T007 Create package exports in `src/babylon/economics/lifecycle/__init__.py` with `__all__` list exposing types and (as implemented) calculators.

**Checkpoint**: `poetry run pytest tests/unit/formulas/test_lifecycle_formulas.py -v` passes. Formulas importable. Package exports working.

______________________________________________________________________

## Phase 3: User Story 1 — Population Cohort Tracking (Priority: P1) MVP

**Goal**: Each county tracks D/P/D' populations with per-tick transitions, births, deaths, and dependency ratio. FR-001, FR-002, FR-003, FR-011.

**Independent Test**: Create county with known D/P/D' pops, run 1 tick, verify transitions + conservation + dependency ratio. See quickstart.md Scenario 1.

### Tests for US1

- [ ] T008 [US1] Write failing tests for cohort dynamics calculator in `tests/unit/economics/lifecycle/test_cohort_dynamics.py`. Use `@pytest.mark.unit`. Cover: single-tick population flow with known inputs (quickstart Scenario 1 values), population conservation within 0.1% tolerance (SC-001), zero D-phase edge case (US1 acceptance #2), zero P-phase edge case (pop_P=0 → dependency_ratio=inf, per contract error handling), high dependency ratio burden (US1 acceptance #3), negative population clamping, births = birth_rate × pop_P.

### Implementation for US1

- [ ] T009 [US1] Implement `CohortDynamicsCalculator` (Protocol + Default) in `src/babylon/economics/lifecycle/cohort_dynamics.py`. Methods: `compute_transitions(dpd_state, defines) -> DPDState` applying births/transitions/deaths per contract steps 1-6, `verify_conservation(old, new) -> bool` checking 0.1% tolerance, `compute_subsistence_burden(dependency_ratio, base_subsistence) -> float` for FR-011.
- [ ] T010 [US1] Create `LifecycleSystem` skeleton implementing System protocol in `src/babylon/engine/systems/lifecycle.py`. Implement `name` property and `step(graph, services, context)` with only Phase 3 logic: read/initialize DPDState per county, call CohortDynamicsCalculator, write updated DPDState + dependency_ratio to graph node, emit `LIFECYCLE_TRANSITION` event. Follow auto-wrap guard pattern from existing systems.
- [ ] T011 [US1] Insert `LifecycleSystem` at position 7 in `_DEFAULT_SYSTEMS` list in `src/babylon/engine/simulation_engine.py` (between CommunitySystem and SolidaritySystem per research.md R-004). Add import.

**Checkpoint**: `poetry run pytest tests/unit/economics/lifecycle/test_cohort_dynamics.py -v` passes. Population flows correctly per tick. Conservation holds. Dependency ratio computed. System runs in engine turn order.

______________________________________________________________________

## Phase 4: User Story 2 — Legitimation Bargain and Crisis Detection (Priority: P2)

**Goal**: Compute legitimation index from 5 weighted components, classify crisis risk, blend with agitation-inverse for bifurcation feed. FR-004, FR-005, FR-006, FR-012.

**Independent Test**: Construct LegitimationState with known values, verify index = weighted sum with political-judgment weights, verify crisis classification boundaries, verify bifurcation integration. See quickstart.md Scenario 2 + Scenario 4.

### Tests for US2

- [ ] T012 [US2] Write failing tests for legitimation calculator in `tests/unit/economics/lifecycle/test_legitimation.py`. Use `@pytest.mark.unit`. Cover: weighted index computation with political-judgment weights (quickstart Scenario 2: 0.6055 STABLE), degradation to CRISIS (all components 0.2 → index 0.2), boundary values (0.3 → UNSTABLE, 0.5 → STABLE), weighted blend with agitation-inverse (quickstart Scenario 4), PENSION_DEFAULT event degradation (FR-012), weight ranking invariant validation.

### Implementation for US2

- [ ] T013 [US2] Implement `LegitimationCalculator` (Protocol + Default) in `src/babylon/economics/lifecycle/legitimation.py`. Methods: `compute_index(state, weights) -> Probability` applying FR-004 weighted sum with ranking invariant, `classify_crisis(index, thresholds) -> LegitimationClassification` per FR-005, `compute_blended_legitimation(structural, agitation, blend_weight) -> float` per FR-006, `apply_pension_default(state, degradation_factor) -> LegitimationState` per FR-012.
- [ ] T014 [US2] Extend `_compute_legitimation()` in `src/babylon/economics/crisis/bifurcation.py` to accept optional `lifecycle_legitimation: float | None` parameter and compute weighted blend per FR-006. Preserve backward compatibility (when None, use existing agitation-inverse).
- [ ] T015 [US2] Wire legitimation computation into `LifecycleSystem.step()` in `src/babylon/engine/systems/lifecycle.py`: after population transitions, compute LegitimationState, classify crisis, write `legitimation_state` + `legitimation_index` to graph node, emit `LEGITIMATION_CRISIS`/`LEGITIMATION_RECOVERY` events on classification changes.

**Checkpoint**: `poetry run pytest tests/unit/economics/lifecycle/test_legitimation.py -v` passes. Legitimation index = 0.6055 for Scenario 2 values. Bifurcation integration working. PENSION_DEFAULT degrades indicators.

______________________________________________________________________

## Phase 5: User Story 7 — Dual Circuit Interference (Priority: P2)

**Goal**: Model resource competition, shadow subsidy, dispossession short-circuit, legitimation-fertility nexus, and sandwich squeeze between D-P-D' and P-D-P' circuits. FR-019, FR-020, FR-021, FR-022, FR-023.

**Independent Test**: Create county with squeezed P-phase resources, verify tradeoff allocation correlates with legitimation index, verify dispossession hits both circuits, verify shadow subsidy is always positive. See quickstart.md Scenario 7 + Scenario 9.

**Depends on**: US2 (legitimation index required for resource allocation split)

### Tests for US7

- [ ] T016 [US7] Write failing tests for dual circuit calculator in `tests/unit/economics/lifecycle/test_dual_circuit.py`. Use `@pytest.mark.unit`. Cover: resource competition tradeoff (quickstart Scenario 7 values, wage < demands → squeeze active), legitimation-driven allocation split (SC-011: high legit → children, low legit → self), dispossession short-circuit hits both circuits (SC-012), legitimation-fertility nexus (SC-013: crisis → lower fertility + higher consciousness), sandwich squeeze at high dependency ratio (FR-022), shadow subsidy always positive (SC-014).

### Implementation for US7

- [ ] T017 [US7] Implement `DualCircuitCalculator` (Protocol + Default) in `src/babylon/economics/lifecycle/dual_circuit.py`. Methods: `compute_resource_competition(wage, d_prime_cost, d_g2_cost, subsistence, legitimation_index) -> ResourceAllocation` per FR-019, `apply_dispossession_short_circuit(wealth_extracted, dpd_state, legitimation_state) -> tuple[DPDState, LegitimationState]` per FR-020, `compute_legitimation_fertility_nexus(legitimation_index, base_fertility, base_ideology, thresholds) -> tuple[float, float]` per FR-021, `compute_sandwich_squeeze(dependency_ratio, threshold, per_capita_resources) -> float` per FR-022, `compute_shadow_subsidy(d_g2_cost, wage_paid) -> Currency` per FR-023.
- [ ] T018 [US7] Wire dual circuit computations into `LifecycleSystem.step()` in `src/babylon/engine/systems/lifecycle.py`: after legitimation, compute resource competition + sandwich squeeze + shadow subsidy, emit `DUAL_CIRCUIT_INTERFERENCE` events when squeeze active or dispossession detected.

**Checkpoint**: `poetry run pytest tests/unit/economics/lifecycle/test_dual_circuit.py -v` passes. Resource competition produces legitimation-dependent allocation. Shadow subsidy always positive. Dispossession hits both circuits.

______________________________________________________________________

## Phase 6: User Story 3 — Intergenerational Inheritance Flow (Priority: P3)

**Goal**: Model Pareto-distributed wealth transfer at D' terminus, compute inheritance Gini, reduce inheritance on dispossession. FR-007, FR-008, FR-013.

**Independent Test**: Place D' population with known wealth, trigger death transitions, verify Pareto-distributed inheritance, verify Gini(inheritance) > Gini(income). See quickstart.md Scenario 3.

### Tests for US3

- [ ] T019 [P] [US3] Write failing tests for inheritance calculator in `tests/unit/economics/lifecycle/test_inheritance.py`. Use `@pytest.mark.unit`. Cover: Pareto distribution with α=1.5 produces Gini≈0.5, care cost fraction reduces net inheritance (quickstart Scenario 3), net inheritance non-negative (care capped at wealth), SC-003 inheritance_gini > income_gini, dispossession reduces inheritance to zero for affected households (FR-008), bottom-50% families pass net zero (US3 acceptance #2).

### Implementation for US3

- [ ] T020 [US3] Implement `InheritanceCalculator` (Protocol + Default) in `src/babylon/economics/lifecycle/inheritance.py`. Methods: `compute_inheritance_flow(dpd_state, wealth_d_prime, deaths, care_cost_fraction, pareto_alpha) -> InheritanceFlow` applying Pareto at familial unit level per FR-007, `apply_dispossession_reduction(flow, dispossession_amount) -> InheritanceFlow` per FR-008, `compute_inheritance_gini(pareto_alpha) -> Gini` per FR-013.
- [ ] T021 [US3] Wire inheritance computation into `LifecycleSystem.step()` in `src/babylon/engine/systems/lifecycle.py`: when deaths > 0, compute InheritanceFlow, write to graph node, emit `INHERITANCE_TRANSFER` event.

**Checkpoint**: `poetry run pytest tests/unit/economics/lifecycle/test_inheritance.py -v` passes. Pareto α=1.5 → Gini≈0.5. Care costs capped. Dispossession reduces inheritance.

______________________________________________________________________

## Phase 7: User Story 6 — Class Mobility Parameterization (Priority: P3)

**Goal**: Derive tunable class mobility parameters from Chetty Opportunity Atlas, expose as GameDefines, model D-to-P class transition outcomes by race and parental income. FR-014, FR-015, FR-016, FR-017, FR-018.

**Independent Test**: Verify default parameters match Mobility Atlas KFR values, verify racial gap shifts in response to in-game events. See quickstart.md Scenario 5 (differential rates) and spec US6 acceptance scenarios.

### Tests for US6

- [ ] T022 [P] [US6] Write failing tests for mobility calculator in `tests/unit/economics/lifecycle/test_mobility.py`. Use `@pytest.mark.unit`. Cover: baseline mobility KFR_P25=0.445 and KFR_P75=0.580 (SC-010 within 5% at both percentiles), linear interpolation between P25/P75 anchors, racial gap Black-White=0.134, carceral modifier 2.8x, early mortality modifier 1.24x, in-game event widens racial gap (US6 acceptance #2), premature P-phase exit rate matches calibrated default 0.004 (FR-017), D-phase context covariates (baseline_gini, poverty_share, etc.) affect mobility outcome (FR-015), parameter provenance documentation exists for each default.

### Implementation for US6

- [ ] T023 [US6] Implement `ClassMobilityCalculator` (Protocol + Default) in `src/babylon/economics/lifecycle/mobility.py`. Methods: `compute_mobility_outcome(parental_percentile, race, params) -> float` per FR-016 (linear interpolation between P25/P75 anchor rates, racial gap applied additively), `compute_premature_exit_rate(base_rate, race_modifier, carceral_modifier) -> Coefficient` per FR-017, `apply_covariate_adjustment(base_outcome, covariates) -> float` per FR-015 (D-phase context covariates modify mobility outcome), `apply_event_modifier(params, event_type, magnitude) -> ClassMobilityParams` per FR-018 (in-game events shift parameters).
- [ ] T024 [US6] Wire mobility parameters into `LifecycleSystem.step()` in `src/babylon/engine/systems/lifecycle.py`: read ClassMobilityParams per county, apply to D-to-P transitions (class outcome), apply premature exit rates to P-to-D' transitions.

**Checkpoint**: `poetry run pytest tests/unit/economics/lifecycle/test_mobility.py -v` passes. Default KFR within 5% of Atlas values. Racial gap coefficients applied. Events modify parameters.

______________________________________________________________________

## Phase 8: User Story 4 — Ideological Socialization in D Phase (Priority: P4)

**Goal**: Transmit ideology from P-phase caregivers to D-phase dependents during D-to-P transition, with regression toward mean and community influence. FR-009.

**Independent Test**: Create D-phase cohort with known caregiver ideology, advance through D-to-P transition, verify consciousness baseline reflects weighted blend. See quickstart.md Scenario 6.

**Depends on**: US1 (population transitions), Feature 029 (CommunityConsciousness)

### Tests for US4

- [ ] T025 [US4] Write failing tests for ideology transmission in `tests/unit/economics/lifecycle/test_cohort_dynamics.py` (extend existing file). Cover: caregiver_weight=0.7 × ideology=0.3 + institutional_weight=0.3 × hegemony=0.8 = 0.45 (quickstart Scenario 6), regression toward population mean (SC-005: correlation r > 0.3 between caregiver and new-worker consciousness), community ConsciousnessTendency amplification (US4 acceptance #2), strong hegemonic schooling pulls toward dominant ideology (US4 acceptance #3).

### Implementation for US4

- [ ] T026 [US4] Add ideology transmission method to `CohortDynamicsCalculator` in `src/babylon/economics/lifecycle/cohort_dynamics.py`: `compute_ideology_transmission(caregiver_ideology, institutional_ideology, caregiver_weight, community_tendency, population_mean) -> float` per FR-009. Apply regression toward mean. Account for community consciousness tendency amplification.
- [ ] T027 [US4] Wire ideology transmission into `LifecycleSystem.step()` in `src/babylon/engine/systems/lifecycle.py`: during D-to-P transition processing, compute transmitted ideology for entering P-phase cohort, apply to consciousness baseline via graph node update.

**Checkpoint**: Ideology transmission produces Scenario 6 values. Correlation between caregiver and new-worker consciousness > 0.3. Community tendency amplifies transmission.

______________________________________________________________________

## Phase 9: User Story 5 — Eugenics Contradiction / Differential P-Phase Duration (Priority: P5)

**Goal**: Encode differential transition rates by race/incarceration/community to model structural inequality in lifecycle duration. FR-010, FR-011.

**Independent Test**: Create two cohorts with different transition rates, run multiple generations, verify affected population shows shorter P phases and less accumulation. See spec US5 acceptance scenarios.

**Depends on**: US1 (transition rates), US6 (mobility parameters for racial modifiers)

### Tests for US5

- [ ] T028 [US5] Write failing tests for differential rate computation in `tests/unit/economics/lifecycle/test_cohort_dynamics.py` (extend existing file). Cover: Black P→D' rate > White P→D' rate with early_mortality_modifier=1.24 (US5 acceptance #1), incarceration removes P-phase individuals (premature P→D' at carceral_modifier rate, US5 acceptance #2), environmental racism elevates rate_P_to_D_prime for affected groups (US5 acceptance #3), 5-generational wealth gap compounds (SC-004).

### Implementation for US5

- [ ] T029 [US5] Add differential rate computation to `CohortDynamicsCalculator` in `src/babylon/economics/lifecycle/cohort_dynamics.py`: `apply_differential_rates(base_rates, racial_modifiers, carceral_modifiers, community_type) -> dict[str, Coefficient]` per FR-010. Modify `compute_transitions()` to accept and apply per-group modifiers.
- [ ] T030 [US5] Wire differential rates into `LifecycleSystem.step()` in `src/babylon/engine/systems/lifecycle.py`: read racial/carceral modifiers from ClassMobilityParams, apply via CohortDynamicsCalculator, track per-group population dynamics.

**Checkpoint**: Black P→D' rate is 1.24× White rate. Carceral modifier removes P-phase population. 5-generation simulation shows compounding wealth gap.

______________________________________________________________________

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Integration wiring, package validation, reproduction.py shadow subsidy connection, full system integration test.

- [ ] T031 Wire shadow subsidy metric from `DualCircuitCalculator` to `_REPRO_EXTERNALIZATION_FACTOR` in `src/babylon/economics/reproduction.py` per research.md R-006 (FR-023 addresses existing TODO)
- [ ] T032 Validate and finalize package exports in `src/babylon/economics/lifecycle/__init__.py` — ensure all public types and calculators are exported with `__all__`
- [ ] T033 [P] Write integration test in `tests/integration/test_lifecycle_system.py` covering quickstart.md Scenario 8 (multi-tick steady state: 100 ticks, conservation holds, populations non-negative, dependency ratio stabilizes) and Scenario 9 (dispossession short-circuit)
- [ ] T034 Run full quickstart.md scenario validation — verify all 9 scenarios produce expected outputs
- [ ] T035 Run `mise run check` (lint + format + typecheck + test:unit) and fix any issues across all new files

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (types must exist for formulas)
- **US1 (Phase 3)**: Depends on Phase 2 — **BLOCKS** all subsequent user stories
- **US2 (Phase 4)**: Depends on Phase 3 (needs DPDState + population dynamics)
- **US7 (Phase 5)**: Depends on Phase 4 (needs legitimation index for resource allocation)
- **US3 (Phase 6)**: Depends on Phase 3 — can run **parallel** with Phase 4/5
- **US6 (Phase 7)**: Depends on Phase 3 — can run **parallel** with Phase 4/5/6
- **US4 (Phase 8)**: Depends on Phase 3 + Feature 029 consciousness system
- **US5 (Phase 9)**: Depends on Phase 3 + Phase 7 (mobility parameters for racial modifiers)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundation only — no dependencies on other stories. **MVP**.
- **US2 (P2)**: Depends on US1 (needs population data for legitimation context)
- **US7 (P2)**: Depends on US2 (needs legitimation index for allocation split)
- **US3 (P3)**: Depends on US1 only — can parallel with US2/US7
- **US6 (P3)**: Depends on US1 only — can parallel with US2/US7/US3
- **US4 (P4)**: Depends on US1 — can parallel with US2/US3/US6
- **US5 (P5)**: Depends on US1 + US6 (mobility params needed for racial modifiers)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD Red phase)
- Types/models before calculators
- Calculators before LifecycleSystem wiring
- Commit after each completed story

### Parallel Opportunities

**Setup [P] tasks** (T003, T004): Different files, no dependencies — run together.

**US3 + US6 in parallel** (Phases 6-7): Both depend only on US1, touch different files:
```
Agent A: T019 → T020 → T021  (inheritance.py)
Agent B: T022 → T023 → T024  (mobility.py)
```

**US4 parallel with US2/US3/US6**: Touches cohort_dynamics.py (shared with US1/US5), but ideology transmission methods are additive — can overlap if coordinated.

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T007)
3. Complete Phase 3: US1 — Population Cohort Tracking (T008–T011)
4. **STOP and VALIDATE**: `poetry run pytest tests/unit/economics/lifecycle/ tests/unit/formulas/test_lifecycle_formulas.py -v`
5. Counties have D/P/D' populations with per-tick dynamics and conservation invariant

### Incremental Delivery

1. Setup + Foundational → Types and formulas ready
2. US1 → Population dynamics working → **MVP Demo**
3. US2 → Legitimation feeds bifurcation → Crisis detection active
4. US7 → Dual circuit interference → Resource competition emergent
5. US3 + US6 (parallel) → Inheritance + mobility calibrated → Class reproduction
6. US4 → Ideology transmission → Consciousness stickiness across generations
7. US5 → Differential rates → Racial capitalism encoded
8. Polish → Integration test + shadow subsidy wiring → Feature complete

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after its phase completes
- TDD mandatory: write failing tests before implementation (Red → Green → Refactor)
- Commit after each completed phase or logical unit per CLAUDE.md
- All parameters in LifecycleDefines must have provenance citations (FR-018, III.1)
- Legitimation weight ranking is a design invariant (political judgment) — validate in tests
- Population conservation invariant (0.1% tolerance) is a hard constraint — test every phase
