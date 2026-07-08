# Tasks: Simulation Tick Dynamics (Feature 017)

**Input**: Design documents from `/specs/017-simulation-tick-dynamics/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Included per project TDD mandate (CLAUDE.md: Red-Green-Refactor cycle mandatory)

**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Package Structure)

**Purpose**: Create the `tick/` subpackage within `src/babylon/economics/` and the parallel test structure

- [x] T001 Create tick package directory and `__init__.py` with public API stubs in `src/babylon/economics/tick/__init__.py` (verified 2026-07-08: src/babylon/economics/tick/__init__.py)
- [x] T002 Create unit test package directory and `__init__.py` in `tests/unit/economics/tick/__init__.py` (verified 2026-07-08: tests/unit/economics/tick/__init__.py)

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, test infrastructure, and engine integration points that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Pydantic Type Models

- [x] T003 [P] Implement `SimulationTickState`, `NationalTickParameters`, `CountyEconomicState`, `SmoothedCoefficients`, `TickSummary`, `DerivedRates` frozen Pydantic models with all field constraints from data-model.md in `src/babylon/economics/tick/types.py` (verified 2026-07-08: src/babylon/economics/tick/types.py (all 6 models))
- [x] T004 [P] Write tests for all Pydantic model validation (field constraints, frozen immutability, FIPS format, year bounds, sum-to-one invariant on ClassDistribution, division-by-zero Optional[float] fields in DerivedRates) in `tests/unit/economics/tick/test_types.py` (verified 2026-07-08: tests/unit/economics/tick/test_types.py (43 tests))

### Engine Integration Points

- [~] T005 Extend `ServiceContainer` with 7 optional economics calculator fields (`melt_calculator`, `basket_calculator`, `gamma_calculator`, `capital_calculator`, `throughput_calculator`, `transition_engine`, `imperial_rent_calculator`) and update `create()` factory method in `src/babylon/engine/services.py` (partial 2026-07-08: 6 of 7 fields on ServiceContainer (src/babylon/engine/services.py:87-92); imperial_rent_calculator deliberately removed in Leontief refactor commit a5f73139)
- [~] T006 Write tests verifying ServiceContainer backward compatibility (existing tests still pass with None defaults) and that calculator fields are accessible when provided, in existing `tests/unit/engine/test_services.py` or new test file as appropriate (partial 2026-07-08: no dedicated ServiceContainer field assertions in test_services.py; behavior covered at system level (tests/unit/economics/tick/test_system.py:232,:383))

### Graph Bridge

- [x] T007 [P] Implement `write_tick_state_to_graph()` and `read_tick_state_from_graph()` functions that map between SimulationTickState and NetworkX graph (Territory node attributes with `tick_` prefix, graph metadata at `graph.graph["tick_dynamics"]`) per data-model.md Graph Integration section, in `src/babylon/economics/tick/graph_bridge.py` (verified 2026-07-08: src/babylon/economics/tick/graph_bridge.py:41,:186)
- [x] T008 [P] Write tests for graph bridge round-trip: write state to graph then read back, verifying Territory node attributes and graph metadata are correct, in `tests/unit/economics/tick/test_graph_bridge.py` (verified 2026-07-08: tests/unit/economics/tick/test_graph_bridge.py:112-152)

### Test Infrastructure

- [x] T009 Create shared test fixtures in `tests/unit/economics/tick/conftest.py`: mock calculators (MELTCalculator, BasketVisibilityCalculator, GammaIIICalculator, CapitalStockCalculator, ThroughputCalculator, ClassTransitionEngine, ImperialRentCalculator returning known values), stable-economy fixture, crisis-economy fixture, sample SimulationTickState at year 2015, sample NationalTickParameters, sample CountyEconomicState for Wayne County MI (FIPS 26163), graph builder helper (verified 2026-07-08: tests/unit/economics/tick/conftest.py:37-206)

**Checkpoint**: Foundation ready — all types defined, ServiceContainer extended, graph bridge functional, test fixtures available. User story implementation can now begin.

______________________________________________________________________

## Phase 3: User Story 1 — Compute National Economic Parameters Per Tick (Priority: P1) MVP

**Goal**: Compute national-level MELT (tau), basket visibility (gamma_basket), and reproductive visibility (gamma_III) for a given simulation year using existing Feature 013/015 calculators

**Independent Test**: Provide economic data for year 2015, validate that computed tau, gamma_basket, gamma_III match Feature 013/015 calculator outputs

### Tests for User Story 1

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T010 [P] [US1] Write tests for national parameter computation: tau matches MELTCalculator output, gamma_basket matches BasketVisibilityCalculator output, gamma_III matches GammaIIICalculator output, tau_effective = tau x gamma_basket, unavailability indicator when BEA GDP missing, in `tests/unit/economics/tick/test_system.py` (national params section) (verified 2026-07-08: tests/unit/economics/tick/test_system.py:229-299)

### Implementation for User Story 1

- [x] T011 [US1] Implement Step 2 (compute national parameters) in `TickDynamicsSystem` — call `services.melt_calculator.get_melt(year)`, `services.basket_calculator.get_gamma_basket(year)`, `services.gamma_calculator.compute(year)`, assemble `NationalTickParameters`, in `src/babylon/economics/tick/system.py` (verified 2026-07-08: src/babylon/economics/tick/system/__init__.py:354-418)

**Checkpoint**: National parameter computation works independently. Given known year data, produces correct tau, gamma_basket, gamma_III.

______________________________________________________________________

## Phase 4: User Story 2 — Compute County-Level Economic State Per Tick (Priority: P1)

**Goal**: Compute per-county capital stock (K), throughput position (pi), supply chain depth (D) using existing Feature 012/014 calculators, with national MELT from US1 as input

**Independent Test**: Compute county state for known FIPS/year, validate K matches Feature 012, pi matches Feature 014

### Tests for User Story 2

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T012 [P] [US2] Write tests for county-level state computation: K matches CapitalStockCalculator output, pi matches ThroughputCalculator output, uses current tick's national MELT (not stale), temporal accumulation K[t+1] = K[t] x (1-delta) + investment[t], partial data returns unavailability indicators, in `tests/unit/economics/tick/test_system.py` (county state section) (verified 2026-07-08: tests/unit/economics/tick/test_system.py:301-331)

### Implementation for User Story 2

- [x] T013 [US2] Implement Step 3a (compute county-level state) in `TickDynamicsSystem` — iterate over county FIPS set, call `services.capital_calculator.get_K(fips, year)`, `services.throughput_calculator.compute_metrics(fips, year)`, assemble per-county `CountyEconomicState`, in `src/babylon/economics/tick/system.py` (verified 2026-07-08: src/babylon/economics/tick/system/__init__.py:420-513)

**Checkpoint**: County state computation works independently. Given known FIPS/year, produces correct K, pi, D per county.

______________________________________________________________________

## Phase 5: User Story 3 — Execute Full Tick State Evolution (Priority: P1)

**Goal**: Orchestrate the complete 8-step pipeline: national params (US1) -> county state (US2) + smoothing -> imperial rent -> crisis detection -> class transitions -> validate distribution -> derived rates -> TickSummary

**Independent Test**: Provide complete SimulationTickState at tick t, validate output state at t+1 has updated class distributions (sum to 1.0), imperial rent flows, derived rates, correct step ordering

**Dependencies**: US1 (Step 2) and US2 (Step 3a) must be implemented first

### Tests for User Story 3

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T014 [P] [US3] Write tests for crisis detection: unemployment > 8% triggers crisis, profit rate decline > 15% triggers crisis, stable economy does not trigger, configurable thresholds, in `tests/unit/economics/tick/test_crisis.py` (verified 2026-07-08: tests/unit/economics/tick/test_crisis.py:20-151)
- [x] T015 [P] [US3] Write tests for precarity derivation: U-6 formula, PTER formula, NILF formula with configurable coefficients, handoff rule (first sim tick overwrites init values), in `tests/unit/economics/tick/test_precarity.py` (verified 2026-07-08: tests/unit/economics/tick/test_precarity.py:21-91)
- [x] T016 [P] [US3] Write tests for full tick pipeline: output year = input year + 1, class distribution sums to 1.0, step ordering verified (3a/3b parallel after Step 2), stable year produces small changes, crisis year amplifies transitions, calculator exception halts with enhanced context (FR-025), in `tests/unit/economics/tick/test_system.py` (full pipeline section) (verified 2026-07-08: tests/unit/economics/tick/test_system.py:333-390)

### Implementation for User Story 3

- [x] T017 [P] [US3] Implement `ThresholdCrisisDetector` with configurable unemployment_threshold (default 0.08) and profit_rate_decline_threshold (default 0.15), `is_crisis(unemployment_rate, current_profit_rate, previous_profit_rate)` method, in `src/babylon/economics/tick/crisis_detector.py` (verified 2026-07-08: src/babylon/economics/tick/crisis_detector.py:23-74)
- [x] T018 [P] [US3] Implement `PrecarityDeriver` with configurable pter_fraction (default 0.4) and nilf_fraction (default 0.6), `derive(class_distribution, precaritization_rate)` method returning u6_rate, pter_rate, nilf_rate, in `src/babylon/economics/tick/precarity.py` (verified 2026-07-08: src/babylon/economics/tick/precarity.py:16-62)
- [x] T019 [US3] Implement Steps 4-8 in `TickDynamicsSystem.step()`: Step 4 (call `services.imperial_rent_calculator.compute_phi_hour()` per county), Step 5 (call ThresholdCrisisDetector), Step 6 (synthesize `EconomicConditions` from tick state — unemployment_rate, median_wage, MELT, phi_hour, dispossession rates [MVP: hardcoded national averages per Assumptions], crisis flag — then call `services.transition_engine.simulate_transitions(dist, conditions)`; extract `precaritization_rate` from the engine's internal `TransitionRates.precaritization` for precarity derivation), Step 7 (validate sum-to-one invariant per FR-009), Step 8 (compute DerivedRates per county; TickSummary is assembled in T031). Wire full 8-step pipeline with error context per FR-025, in `src/babylon/economics/tick/system.py` (verified 2026-07-08: src/babylon/economics/tick/system/__init__.py:180-219 (Step 4 delegates to Leontief imperial_rent.compute))
- [x] T020 [US3] Implement `TickDynamicsSystem` as engine System conforming to `step(graph, services, context) -> None` protocol: read state from graph via graph_bridge, gate execution to year boundaries (FR-024), execute 8-step pipeline, write results back to graph via graph_bridge, handle timescale bridging, in `src/babylon/economics/tick/system.py` (verified 2026-07-08: src/babylon/economics/tick/system/__init__.py:109-235)
- [x] T021 [US3] Register `TickDynamicsSystem` in `_DEFAULT_SYSTEMS` after `ProductionSystem` and before `SolidaritySystem` in `src/babylon/engine/simulation_engine.py` (verified 2026-07-08: src/babylon/engine/simulation_engine.py:330 (position 4))

**Checkpoint**: Full single-tick pipeline works end-to-end. Given complete state at year t, produces valid state at year t+1 with correct step ordering, class distribution invariants, and derived rates.

______________________________________________________________________

## Phase 6: User Story 5 — Coefficient Smoothing vs Quantity Updates (Priority: P2)

**Goal**: Distinguish quantities (update directly) from coefficients (alpha-smooth), ensuring simulation stability while remaining responsive to economic shifts

**Independent Test**: Introduce spike in gamma_basket, verify smoothed value changes gradually while quantity fields update immediately

### Tests for User Story 5

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T022 [P] [US5] Write tests for CoefficientSmoother: alpha=0.3 smoothing formula verified, first tick uses raw values (no smoothing), sequence convergence toward mean, alpha=1 means no smoothing, alpha validation (reject 0, accept (0,1]), in `tests/unit/economics/tick/test_smoothing.py` (verified 2026-07-08: tests/unit/economics/tick/test_smoothing.py:17-86)

### Implementation for User Story 5

- [x] T023 [US5] Implement `CoefficientSmoother` with configurable alpha (default 0.3), `smooth(raw, previous, is_initialized)` method, first-tick handling (raw passthrough when `is_initialized=False`), update SmoothedCoefficients container, in `src/babylon/economics/tick/smoothing.py` (verified 2026-07-08: src/babylon/economics/tick/smoothing.py:17-57)
- [x] T024 [US5] Integrate CoefficientSmoother into TickDynamicsSystem Step 3b: after Step 2, smooth gamma_basket, gamma_III, gamma_import using CoefficientSmoother, update SmoothedCoefficients in state, ensure 3a and 3b are independent (no data dependency between them), in `src/babylon/economics/tick/system.py` (verified 2026-07-08: src/babylon/economics/tick/system/__init__.py:392-406,:541-571)

**Checkpoint**: Coefficient smoothing works. Spike in gamma_basket produces gradual change; quantities (unemployment, K) update immediately.

______________________________________________________________________

## Phase 7: User Story 4 — Multi-Tick Historical Simulation (Priority: P2)

**Goal**: Run sequence of ticks covering 2010-2024, validate historical trajectories of class composition and economic indicators

**Independent Test**: Run 14 ticks from 2010 initial state, verify intermediate states valid, final distribution within expected ranges

**Dependencies**: US3 (single tick) must work first

### Tests for User Story 4

> **Write tests FIRST, ensure they FAIL before implementation**

- [~] T025 [P] [US4] Write tests for initialization: seed from census data with known county set, partial data availability handled per FR-027 (0% halt, 1-89% warn, >=90% normal), county set immutable after init (FR-026), in `tests/unit/economics/tick/test_initializer.py` (partial 2026-07-08: test_initializer.py covers seeding/multi-county/immutability/sum-to-one; missing FR-027 partial-data halt/warn threshold tests)
- [~] T026 [P] [US4] Write integration tests for multi-tick execution: 14-tick run produces valid intermediate states, final class distributions within SC-002 ranges, crisis years (2008-2012) show amplified transitions per SC-003, Phi_aggregate at Hickel scale per SC-004, coefficient smoothing reduces variance by >= 50% per SC-005, profit rate/OCC trends plausible per SC-007, year 2040 boundary halt per FR-028, convergence detection per FR-029, deterministic output per SC-009, in `tests/integration/economics/test_tick_integration.py` (partial 2026-07-08: test_tick_integration.py covers multi-year chaining, SC-009 determinism, distribution validity, smoothing; missing SC-002..SC-007 range validations, FR-028 halt, FR-029 convergence)

### Implementation for User Story 4

- [~] T027 [US4] Implement `DefaultTickInitializer` with `initialize(year, county_fips, calculators)` method: seed national params from calculators, seed county states from CapitalStockCalculator/ThroughputCalculator, seed precarity from FRED/BLS data, set initial SmoothedCoefficients (is_initialized=False), handle partial failures per FR-027, validate county set per FR-026, in `src/babylon/economics/tick/initializer.py` (partial 2026-07-08: src/babylon/economics/tick/initializer.py:60-206 seeds with fallbacks, but no FR-027 partial-failure thresholds or explicit FR-026 county-set validation)
- [~] T028 [US4] Implement multi-tick execution loop in TickDynamicsSystem or standalone runner: iterate single ticks over year range, chain state (FR-004), detect year 2040 boundary halt (FR-028), detect convergence and annotate TickSummary (FR-029), accumulate tick summaries for historical analysis, in `src/babylon/economics/tick/system.py` (partial 2026-07-08: state chaining works (src/babylon/economics/tick/system/__init__.py:141-151) but no dedicated multi-tick runner, FR-028 year-2040 halt, or FR-029 convergence detection)

**Checkpoint**: Multi-tick simulation runs from 2010 initial state through 2024. Intermediate states valid, final distributions plausible, crisis amplification observable.

______________________________________________________________________

## Phase 8: User Story 6 — Derived Economic Indicators Per Tick (Priority: P3)

**Goal**: Compute profit rate, OCC, exploitation rate, and Phi_aggregate from updated state, independently testable for manual calculation verification

**Independent Test**: Compute derived indicators for known county state, validate r = s/(K+v), OCC = c/v, e = s/v, Phi_aggregate = sum(phi_hour x employment x 2080)

### Tests for User Story 6

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T029 [P] [US6] Write tests for DerivedRateCalculator: profit rate r = s/(K+v), OCC = c/v, exploitation rate e = s/v, division-by-zero handling (K=0 and v=0 -> None, v=0 -> None for OCC and e), Phi_aggregate annualization formula (phi_hour x employment x 2080), unavailability indicators when K missing during init, in `tests/unit/economics/tick/test_derived.py` (verified 2026-07-08: tests/unit/economics/tick/test_derived.py:69-161)

### Implementation for User Story 6

- [x] T030 [US6] Implement `DerivedRateCalculator` with `compute_county_rates(county_state)` returning `DerivedRates` with Optional[float] for division-by-zero, and `compute_phi_aggregate(county_states)` using annualization formula `sum(phi_hour x employment x 2080)`, in `src/babylon/economics/tick/derived_rates.py` (verified 2026-07-08: src/babylon/economics/tick/derived_rates.py:26-111)
- [x] T031 [US6] Integrate DerivedRateCalculator into TickDynamicsSystem Step 8 and assemble final TickSummary: after class distribution committed (Step 7), compute per-county DerivedRates and Phi_aggregate, then assemble TickSummary with year, counties_processed, phi_aggregate, national_melt, mean_profit_rate, mean_occ, mean_exploitation_rate, national_class_distribution. Note: T019 wires Steps 4-7 but defers TickSummary assembly to this task; T031 owns the complete TickSummary construction, in `src/babylon/economics/tick/system.py` (verified 2026-07-08: src/babylon/economics/tick/system/__init__.py:1613-1667)

**Checkpoint**: Derived indicators computed correctly. Manual calculation matches formula output. Division-by-zero produces None. TRPF trend observable across multi-tick run.

______________________________________________________________________

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, export updates, and validation

- [x] T032 Update `src/babylon/economics/tick/__init__.py` with complete public API exports: TickDynamicsSystem, SimulationTickState, NationalTickParameters, CountyEconomicState, SmoothedCoefficients, TickSummary, DerivedRates, DefaultTickInitializer, CoefficientSmoother, ThresholdCrisisDetector, DerivedRateCalculator, PrecarityDeriver, write_tick_state_to_graph, read_tick_state_from_graph (verified 2026-07-08: src/babylon/economics/tick/__init__.py:44-66)
- [x] T033 Update `src/babylon/economics/__init__.py` to re-export key tick types: TickDynamicsSystem, SimulationTickState, DefaultTickInitializer (verified 2026-07-08: src/babylon/economics/__init__.py:167-178,:267-275)
- [ ] T034 Run full test suite (`mise run test:all`) and verify no regressions in existing tests from ServiceContainer extension or _DEFAULT_SYSTEMS modification (unverifiable — ephemeral gate, no durable artifact)
- [ ] T035 Run `mise run typecheck` and resolve any mypy errors across all new and modified files (unverifiable — ephemeral gate, no durable artifact)
- [ ] T036 Run quickstart.md validation: verify code examples in quickstart.md are consistent with implemented API (ServiceContainer.create() kwargs, TickInitializer constructor, graph access patterns) (unverifiable — ephemeral gate, no durable artifact)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational phase — can start immediately after Phase 2
- **US2 (Phase 4)**: Depends on Foundational phase — can run in parallel with US1
- **US3 (Phase 5)**: Depends on US1 + US2 being implemented (Steps 2 and 3a)
- **US5 (Phase 6)**: Depends on Foundational phase — can start after Phase 2, integrates with US3
- **US4 (Phase 7)**: Depends on US3 (single tick must work) and US5 (smoothing needed for multi-tick)
- **US6 (Phase 8)**: Depends on Foundational phase — DerivedRateCalculator is independently testable, integration with US3 Step 8
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```text
Phase 2 (Foundation)
    ├── US1 (Phase 3) ──┐
    ├── US2 (Phase 4) ──┼── US3 (Phase 5) ── US4 (Phase 7)
    ├── US5 (Phase 6) ──┘        │
    └── US6 (Phase 8) ───────────┘ (Step 8 integration)
                                 │
                          Phase 9 (Polish)
```

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD Red phase)
2. Implementation makes tests pass (TDD Green phase)
3. Refactor if needed (TDD Refactor phase)
4. Commit after each story completes

### Parallel Opportunities

**Phase 2 parallel set**: T003 + T004 (types), T007 + T008 (graph bridge) can run in parallel — different files, no dependencies

**After Phase 2**:
- US1 (T010-T011) and US2 (T012-T013) can run in parallel — different pipeline steps, no overlap
- US5 (T022-T024) and US6 (T029-T031) can start independently after Phase 2 — different modules

**Within US3**: T014 + T015 + T016 (tests) can run in parallel — different test files. T017 + T018 (crisis + precarity) can run in parallel — different source files

______________________________________________________________________

## Parallel Example: Phase 2 Foundational

```bash
# Launch in parallel (different files, no dependencies):
Task T003: "Implement Pydantic models in src/babylon/economics/tick/types.py"
Task T007: "Implement graph bridge in src/babylon/economics/tick/graph_bridge.py"

# Then in parallel (test files for above):
Task T004: "Write type model tests in tests/unit/economics/tick/test_types.py"
Task T008: "Write graph bridge tests in tests/unit/economics/tick/test_graph_bridge.py"
```

## Parallel Example: US1 + US2 (after Phase 2)

```bash
# Launch in parallel (independent pipeline steps):
Task T010: "Write US1 tests in tests/unit/economics/tick/test_system.py (national params)"
Task T012: "Write US2 tests in tests/unit/economics/tick/test_system.py (county state)"

# Then in parallel:
Task T011: "Implement Step 2 national params in src/babylon/economics/tick/system.py"
Task T013: "Implement Step 3a county state in src/babylon/economics/tick/system.py"
```

**Note**: T010/T012 and T011/T013 target the same file (system.py / test_system.py) but different sections. If using parallel agents, these should be serialized to avoid conflicts. Alternatively, split into separate files (e.g., `national_params.py`, `county_state.py`) and compose in `system.py`.

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T009)
3. Complete Phase 3: US1 — national parameters (T010-T011)
4. Complete Phase 4: US2 — county state (T012-T013)
5. Complete Phase 5: US3 — full tick pipeline (T014-T021)
6. **STOP and VALIDATE**: Single tick works end-to-end for year 2015
7. Commit MVP milestone

### Incremental Delivery

1. Setup + Foundational -> Types and infrastructure ready
2. US1 + US2 -> Individual pipeline steps testable
3. US3 -> Full single-tick pipeline (MVP!)
4. US5 -> Smoothing adds stability for multi-tick
5. US4 -> Multi-tick validation against history
6. US6 -> Derived indicators for analysis
7. Polish -> Exports, regression check, typecheck

### Commit Strategy

Per CLAUDE.md: commit after each unit of work. Suggested commit points:
- After Phase 1: `feat(tick-dynamics): create tick package structure`
- After Phase 2: `feat(tick-dynamics): add foundational types, graph bridge, ServiceContainer extension`
- After US1: `feat(tick-dynamics): implement national parameter computation (US1)`
- After US2: `feat(tick-dynamics): implement county-level state computation (US2)`
- After US3: `feat(tick-dynamics): implement full tick pipeline orchestration (US3)`
- After US5: `feat(tick-dynamics): add coefficient smoothing (US5)`
- After US4: `feat(tick-dynamics): add multi-tick historical simulation (US4)`
- After US6: `feat(tick-dynamics): add derived economic indicators (US6)`
- After Polish: `feat(tick-dynamics): finalize exports and cross-cutting validation`

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD: write tests FIRST (Red), implement to pass (Green), refactor
- Commit after each story or logical group
- Stop at any checkpoint to validate story independently
- All source files go in `src/babylon/economics/tick/`
- All unit tests go in `tests/unit/economics/tick/`
- Integration tests go in `tests/integration/economics/`
- ServiceContainer extension is the only modification outside the tick package (plus _DEFAULT_SYSTEMS registration)
