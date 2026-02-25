# Tasks: Capital Volume II Integration

**Input**: Design documents from `/specs/023-capital-volume-ii/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**TDD**: Yes (project standard — Red-Green-Refactor)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package structure and shared test infrastructure

- [x] T001 Create circulation package directory structure at `src/babylon/economics/circulation/` with `__init__.py`
- [x] T002 Create test directory structure at `tests/unit/economics/circulation/` with `__init__.py`
- [x] T003 Create shared test fixtures and factories in `tests/unit/economics/circulation/conftest.py` — include DomainFactory helpers for CircuitState, TurnoverProfile, InventoryState, DepartmentRow with sensible defaults

**Checkpoint**: Package structure exists, conftest importable

______________________________________________________________________

## Phase 2: Foundational (All Type Definitions)

**Purpose**: All frozen Pydantic models with computed fields — MUST be complete before ANY user story implementation

**CRITICAL**: No user story work can begin until this phase is complete. All 19 entities from data-model.md are defined here because they are shared across multiple user stories.

### RED Phase: Type Tests

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 Write tests for CapitalForm, ReplacementCyclePosition, InventoryDiagnosis, CrisisSeverity enums in `tests/unit/economics/circulation/test_types.py` — verify enum values, StrEnum membership, string representation
- [x] T005 Write tests for CircuitState model in `tests/unit/economics/circulation/test_types.py` — verify total_capital computation, liquidity_ratio (including zero-capital edge case returning 0.0), commodity_overhang (including zero-capital), frozen immutability
- [x] T006 Write tests for TurnoverProfile model in `tests/unit/economics/circulation/test_types.py` — verify production_time, circulation_time, turnover_time, turnovers_per_year (including zero turnover_time returning 0.0), production_ratio
- [x] T007 Write tests for AnnualSurplusValue model in `tests/unit/economics/circulation/test_types.py` — verify rate_of_surplus_value, turnovers_per_year, annual_surplus_value, annual_rate_of_surplus_value against Marx's examples (s/v=100%, 2-month turnover → 600%)
- [x] T008 Write tests for DepreciationFundState model in `tests/unit/economics/circulation/test_types.py` — verify fund_adequacy, replacement_cycle_position classification at all four thresholds (>1.5, >1.0, >0.7, <=0.7)
- [x] T009a Write tests for FixedCapitalItem model in `tests/unit/economics/circulation/test_types.py` — verify annual_depreciation (initial_value / service_life_years), remaining_value at age 0 (full value), age = service_life (zero), midpoint ($1M/10yr/5yr = $500K remaining), depreciation_fund_required, frozen immutability
- [x] T009 Write tests for MoralDepreciation model in `tests/unit/economics/circulation/test_types.py` — verify obsolescence_factor computation, zero physical_remaining_life edge case returning 1.0
- [x] T010 Write tests for InventoryState model in `tests/unit/economics/circulation/test_types.py` — verify total_inventory, inventory_problem at thresholds (finished>60 → OVERPRODUCTION, raw<7 → SUPPLY_CRISIS, normal)
- [x] T011 Write tests for ReproductionBalance and ReproductionAnalysis models in `tests/unit/economics/circulation/test_types.py` — verify field constraints and frozen behavior
- [x] T012 Write tests for RealizationCrisis model in `tests/unit/economics/circulation/test_types.py` — verify realization_gap, realization_rate, crisis_severity at all four thresholds (>95%, >85%, >70%, <=70%)
- [x] T013 Write tests for DisproportionalityCrisis model in `tests/unit/economics/circulation/test_types.py` — verify actual_i_share, imbalance, imbalance_direction
- [x] T014 Write tests for PureCirculationCosts model in `tests/unit/economics/circulation/test_types.py` — verify total_pure_circulation sum, circulation_burden method
- [x] T015 Write tests for TransportationValue model in `tests/unit/economics/circulation/test_types.py` — verify value_added, destination_value, transport_value_ratio
- [x] T016 Write tests for CirculationCrisisAssessment and CirculationCrisisState models in `tests/unit/economics/circulation/test_types.py` — verify factory defaults, frozen behavior

### GREEN Phase: Type Implementations

- [x] T017 Implement all enum types (CapitalForm, ReplacementCyclePosition, InventoryDiagnosis, CrisisSeverity) in `src/babylon/economics/circulation/types.py` — StrEnum pattern matching CrisisPhase
- [x] T018 Implement CircuitState, TurnoverProfile, AnnualSurplusValue frozen models with computed fields in `src/babylon/economics/circulation/types.py`
- [x] T019 Implement FixedCapitalItem, DepreciationFundState, MoralDepreciation frozen models with computed fields in `src/babylon/economics/circulation/types.py`
- [x] T020 Implement InventoryState, ReproductionBalance, ReproductionAnalysis frozen models in `src/babylon/economics/circulation/types.py`
- [x] T021 Implement RealizationCrisis, DisproportionalityCrisis frozen models with computed fields in `src/babylon/economics/circulation/types.py`
- [x] T022 Implement PureCirculationCosts (with circulation_burden method), TransportationValue frozen models in `src/babylon/economics/circulation/types.py`
- [x] T023 Implement CirculationCrisisAssessment, CirculationCrisisState (with factory classmethod) frozen models in `src/babylon/economics/circulation/types.py`
- [x] T024 Verify all type tests pass — run `poetry run pytest tests/unit/economics/circulation/test_types.py -v`

**Checkpoint**: All 19 entities defined and tested (including FixedCapitalItem for FR-009). Computed fields work including edge cases. All user stories can now begin.

______________________________________________________________________

## Phase 3: User Story 1 - Capital Circuit State Tracking (Priority: P1) MVP

**Goal**: Capital is distributed across Money, Productive, and Commodity forms. Form transitions follow the M-C-P-C'-M' circuit governed by turnover profiles.

**Independent Test**: Create a county with initial capital across three forms, advance one tick, verify transitions respect turnover timing and total capital invariant is preserved.

**FRs**: FR-001, FR-002, FR-003

### RED Phase

- [x] T025 [US1] Write tests for `advance_circuit()` in `tests/unit/economics/circulation/test_circuit.py` — test M→C transition when purchase time elapses, C→P when capital enters production, P→C' when working period completes (surplus added), C'→M' when sale time elapses
- [x] T026 [US1] Write tests for total capital invariant in `tests/unit/economics/circulation/test_circuit.py` — verify M+P+C = constant except during production phase where surplus is created
- [x] T027 [US1] Write tests for edge cases in `tests/unit/economics/circulation/test_circuit.py` — all capital stuck in one form (100% commodity = liquidity crisis), zero total capital, negative elapsed days rejected

### GREEN Phase

- [x] T028 [US1] Implement `advance_circuit()` function in `src/babylon/economics/circulation/circuit.py` — pure function taking CircuitState + TurnoverProfile + surplus + elapsed_days → new CircuitState
- [x] T029 [US1] Implement `initialize_circuit_state()` function in `src/babylon/economics/circulation/circuit.py` — distribute initial capital across M/P/C forms based on industry-weighted turnover profile
- [x] T030 [US1] Verify all circuit tests pass — run `poetry run pytest tests/unit/economics/circulation/test_circuit.py -v`

**Checkpoint**: Circuit state transitions work. Can create county capital, advance through forms, total invariant holds.

______________________________________________________________________

## Phase 4: User Story 2 - Turnover Time and Annual Surplus Value (Priority: P1)

**Goal**: Turnover time varies by industry. Annual surplus value = per-cycle surplus x turnovers per year. Faster turnover = more surplus from same capital.

**Independent Test**: Compute annual surplus for two entities with identical s/v but different turnover times. Verify faster turner produces proportionally more annual surplus.

**FRs**: FR-004, FR-005, FR-006, FR-007

### RED Phase

- [x] T031 [US2] Write tests for `compute_annual_surplus_value()` in `tests/unit/economics/circulation/test_turnover.py` — test Marx's examples: s/v=100% with 2-month turnover (600%), 6-month turnover (200%), verify proportionality
- [x] T032 [US2] Write tests for `compare_turnover_advantage()` in `tests/unit/economics/circulation/test_turnover.py` — fast vs slow turner ratio, equal turners return 1.0
- [x] T033 [US2] Write tests for default turnover profiles in `tests/unit/economics/circulation/test_turnover.py` — verify profiles load by NAICS sector code, unknown NAICS returns fallback, production_time + circulation_time = turnover_time
- [x] T034 [US2] Write tests for `get_weighted_turnover_profile()` in `tests/unit/economics/circulation/test_turnover.py` — county with mixed industries gets weighted-average turnover profile

### GREEN Phase

- [x] T035 [US2] Implement `compute_annual_surplus_value()` and `compare_turnover_advantage()` in `src/babylon/economics/circulation/turnover.py`
- [x] T036 [US2] Implement default turnover profiles by NAICS sector in `src/babylon/economics/circulation/defaults.py` — hardcoded industry-level defaults derived from BEA Fixed Asset Tables and Census M3 ratios. Also define all threshold constants as `Final` named values with traceability comments per plan.md Threshold Traceability section (OVERPRODUCTION_DAYS_THRESHOLD, SUPPLY_CRISIS_DAYS_THRESHOLD, COMMODITY_OVERHANG_CRISIS, LIQUIDITY_CRISIS_RATIO, REALIZATION_RATE_NORMAL/SLOWDOWN/RECESSION, REPLACEMENT_BOOM/EXPANSION/MAINTENANCE_RATIO)
- [x] T037 [US2] Implement `TurnoverProfileSource` Protocol and `DefaultTurnoverProfileSource` in `src/babylon/economics/circulation/turnover.py` — Protocol for DI, default resolves from `defaults.py`
- [x] T038 [US2] Implement `get_weighted_turnover_profile()` in `src/babylon/economics/circulation/turnover.py` — compute county-level turnover from industry mix weights
- [x] T039 [US2] Verify all turnover tests pass — run `poetry run pytest tests/unit/economics/circulation/test_turnover.py -v`

**Checkpoint**: Turnover time computation works. Annual surplus amplification matches Marx's examples. Industry defaults resolve.

______________________________________________________________________

## Phase 5: User Story 3 - Fixed vs Circulating Capital Decomposition (Priority: P2)

**Goal**: Constant capital (c) decomposed into fixed (machinery, buildings) and circulating (raw materials, fuel). Depreciation fund tracks accumulation vs replacement. Moral depreciation models obsolescence.

**Independent Test**: Create fixed capital item with known service life. Verify depreciation accumulates correctly and replacement cycle position classifies at all thresholds.

**FRs**: FR-008, FR-009, FR-010, FR-011

### RED Phase

- [x] T040 [P] [US3] Write tests for `decompose_constant_capital()` in `tests/unit/economics/circulation/test_fixed_circulating.py` — verify split using ratio, ratio=0 (all circulating), ratio=1 (all fixed), mid-range values
- [x] T041 [P] [US3] Write tests for `update_depreciation_fund()` in `tests/unit/economics/circulation/test_fixed_circulating.py` — verify fund accumulation, all four replacement cycle positions, fund_adequacy computation
- [x] T042 [P] [US3] Write tests for moral depreciation computation in `tests/unit/economics/circulation/test_fixed_circulating.py` — physical > economic (rapid obsolescence), physical = economic (no obsolescence), physical = 0 edge case

### GREEN Phase

- [x] T043 [US3] Implement `decompose_constant_capital()` in `src/babylon/economics/circulation/fixed_circulating.py` — pure function splitting Currency into (fixed, circulating) tuple
- [x] T044 [US3] Implement `update_depreciation_fund()` in `src/babylon/economics/circulation/fixed_circulating.py` — pure function updating DepreciationFundState for one period
- [x] T045 [US3] Implement `compute_moral_depreciation()` in `src/babylon/economics/circulation/fixed_circulating.py` — compute obsolescence factor from BEA industry data
- [x] T046 [US3] Verify all fixed/circulating tests pass — run `poetry run pytest tests/unit/economics/circulation/test_fixed_circulating.py -v`

**Checkpoint**: Constant capital splits correctly. Depreciation fund tracks. Moral depreciation handles edge cases.

______________________________________________________________________

## Phase 6: User Story 4 - Reproduction Schema Balance Conditions (Priority: P2)

**Goal**: Check whether inter-departmental exchange satisfies simple reproduction I(v+s)=IIc and extended reproduction conditions including Department III.

**Independent Test**: Provide balanced and imbalanced department configurations. Verify gap computation and direction interpretation for 5+ scenarios.

**FRs**: FR-012, FR-013, FR-014

### RED Phase

- [x] T047 [P] [US4] Write tests for `check_simple_reproduction()` in `tests/unit/economics/circulation/test_reproduction.py` — test balanced case (gap=0), overproduction Dept I (positive gap), underproduction Dept I (negative gap), at least 5 distinct scenarios per SC-003
- [x] T048 [P] [US4] Write tests for `check_extended_reproduction()` in `tests/unit/economics/circulation/test_reproduction.py` — test sustainable (gap<=0), unsustainable (gap>0), Dept III zero output edge case (gap = total_v)
- [x] T049 [P] [US4] Write tests for `compute_disproportionality()` in `tests/unit/economics/circulation/test_reproduction.py` — test overproduction means of production vs consumption goods, equal shares, extreme imbalance

### GREEN Phase

- [x] T050 [US4] Implement `check_simple_reproduction()` in `src/babylon/economics/circulation/reproduction.py` — combine DepartmentRow IIa + IIb into single Dept II, compute I(v+s) - IIc gap
- [x] T051 [US4] Implement `check_extended_reproduction()` in `src/babylon/economics/circulation/reproduction.py` — compute total_v demand vs Dept III capacity
- [x] T052 [US4] Implement `compute_disproportionality()` in `src/babylon/economics/circulation/reproduction.py` — compute share metrics and direction
- [x] T053 [US4] Implement `combine_departments_ii()` helper in `src/babylon/economics/circulation/reproduction.py` — sum IIa + IIb DepartmentRow c, v, s values into a single DepartmentRow
- [x] T054 [US4] Verify all reproduction tests pass — run `poetry run pytest tests/unit/economics/circulation/test_reproduction.py -v`

**Checkpoint**: Reproduction schema checks work. 5+ scenarios validate simple reproduction. Extended reproduction with Dept III correct.

______________________________________________________________________

## Phase 7: User Story 5 - Inventory Tracking and Realization Crisis Detection (Priority: P3)

**Goal**: Track inventory levels (raw, WIP, finished). Detect realization crisis from rising inventory + flat/falling production. Compute realization gap and severity.

**Independent Test**: Provide time series with rising finished goods and flat production. Verify realization crisis detected. Verify severity classification at all thresholds.

**FRs**: FR-015, FR-016, FR-017

### RED Phase

- [x] T055 [P] [US5] Write tests for `compute_realization_metrics()` in `tests/unit/economics/circulation/test_inventory.py` — test all four severity thresholds (>95% NORMAL, >85% MILD_SLOWDOWN, >70% RECESSION, <=70% CRISIS), zero produced edge case
- [x] T056 [P] [US5] Write tests for `detect_realization_crisis()` in `tests/unit/economics/circulation/test_inventory.py` — rising inventory + falling production = True, rising inventory + rising production = False, flat inventory = False, single-element list edge case

### GREEN Phase

- [x] T057 [US5] Implement `compute_realization_metrics()` in `src/babylon/economics/circulation/inventory.py` — pure function producing RealizationCrisis from produced/realized values
- [x] T058 [US5] Implement `detect_realization_crisis()` in `src/babylon/economics/circulation/inventory.py` — time series trend detection comparing first and last elements
- [x] T059 [US5] Verify all inventory tests pass — run `poetry run pytest tests/unit/economics/circulation/test_inventory.py -v`

**Checkpoint**: Inventory diagnosis works. Realization crisis detection catches rising-inventory patterns. Severity classifies correctly.

______________________________________________________________________

## Phase 8: User Story 6 - Circulation Costs Classification (Priority: P3)

**Goal**: Classify labor as productive (value-creating) or unproductive (pure circulation). Compute circulation burden ratio. Model transportation as productive labor adding value.

**Independent Test**: Provide circulation cost breakdown. Verify total pure circulation cost and burden ratio. Classify transport worker as productive, cashier as unproductive.

**FRs**: FR-018, FR-019, FR-020

### RED Phase

- [x] T060 [P] [US6] Write tests for PureCirculationCosts total and burden in `tests/unit/economics/circulation/test_costs.py` — verify sum of all 6 cost fields, burden = total / revenue, zero revenue edge case
- [x] T061 [P] [US6] Write tests for TransportationValue computations in `tests/unit/economics/circulation/test_costs.py` — verify value_added = c+v+s, destination_value = origin + added, transport_value_ratio
- [x] T062 [P] [US6] Write tests for `classify_labor()` in `tests/unit/economics/circulation/test_costs.py` — production worker = productive, truck driver = productive, cashier = unproductive, advertising = unproductive, warehouse worker = partially productive

### GREEN Phase

- [x] T063 [US6] Implement `classify_labor()` function in `src/babylon/economics/circulation/costs.py` — occupation-based classification with rationale
- [x] T064 [US6] Implement any additional cost computation helpers in `src/babylon/economics/circulation/costs.py` — ensure PureCirculationCosts and TransportationValue computed fields cover all FRs
- [x] T065 [US6] Verify all cost tests pass — run `poetry run pytest tests/unit/economics/circulation/test_costs.py -v`

**Checkpoint**: Labor classification works. Circulation burden computes correctly. Transportation value adds c+v+s.

______________________________________________________________________

## Phase 9: User Story 7 - Integrated Circulation Crisis Detection (Priority: P3)

**Goal**: Detect realization crisis, turnover disruption, and reproduction failure in an integrated assessment. Complement (not replace) existing TRPF crisis mechanics.

**Independent Test**: Provide circuit state, turnover profile, inventory state, and reproduction conditions. Verify each crisis type detected independently and in combination. Normal conditions produce no flags.

**FRs**: FR-021, FR-022

**Depends on**: US1 (circuit), US2 (turnover), US4 (reproduction), US5 (inventory)

### RED Phase

- [x] T066 [US7] Write tests for `assess_circulation_crisis()` in `tests/unit/economics/circulation/test_crisis.py` — test realization crisis flagged when commodity_overhang > 0.3, turnover crisis flagged when liquidity < 0.1 and circulation_time > production_time, reproduction crisis flagged when conditions fail
- [x] T067 [US7] Write tests for combined crisis scenarios in `tests/unit/economics/circulation/test_crisis.py` — all three active simultaneously, none active (normal), exactly one active at a time (3 isolated tests)
- [x] T068 [US7] Write tests for vulnerability reporting in `tests/unit/economics/circulation/test_crisis.py` — verify correct vulnerability strings (LABOR_SHORTAGE, SUPPLY_CHAIN_CRISIS, REALIZATION_CRISIS, MONETARY_CRISIS) appear in vulnerabilities list

### GREEN Phase

- [x] T069 [US7] Implement `assess_circulation_crisis()` in `src/babylon/economics/circulation/crisis.py` — pure function taking CircuitState, TurnoverProfile, InventoryState, ReproductionBalance, ReproductionAnalysis → CirculationCrisisAssessment
- [x] T070 [US7] Verify all crisis assessment tests pass — run `poetry run pytest tests/unit/economics/circulation/test_crisis.py -v`

**Checkpoint**: Integrated crisis detection works. All three crisis types detected independently and combined. No false positives on normal conditions.

______________________________________________________________________

## Phase 10: Tick System Integration

**Purpose**: Wire circulation into the annual pipeline and graph bridge. Integrate with existing CountyEconomicState.

**Depends on**: All user stories (US1-US7) complete

### RED Phase

- [x] T071 Write tests for `circulation_state` field on CountyEconomicState in `tests/unit/economics/circulation/test_integration.py` — verify field exists with factory default, frozen model still valid, existing fields unaffected
- [x] T072 Write tests for graph bridge serialization in `tests/unit/economics/circulation/test_integration.py` — verify `tick_liquidity_ratio`, `tick_commodity_overhang`, `tick_realization_crisis` and other circulation attributes written to territory nodes
- [x] T073 Write tests for graph bridge deserialization in `tests/unit/economics/circulation/test_integration.py` — verify CirculationCrisisState reconstructed from territory node attributes

### GREEN Phase

- [x] T074 Add `circulation_state: CirculationCrisisState` field to `CountyEconomicState` in `src/babylon/economics/tick/types.py` — with `Field(default_factory=CirculationCrisisState.initial)`, preserving all existing fields
- [x] T075 Add circulation step to `TickDynamicsSystem.step()` pipeline in `src/babylon/economics/tick/system.py` — insert after imperial rent computation (step 4), before crisis triggers (step 5); compute circuit state, inventory, reproduction, crisis assessment per county
- [x] T076 Add circulation attributes to `write_tick_state_to_graph()` in `src/babylon/economics/tick/graph_bridge.py` — serialize `tick_liquidity_ratio`, `tick_commodity_overhang`, `tick_turnovers_per_year`, `tick_annual_surplus_rate`, `tick_replacement_cycle`, `tick_inventory_diagnosis`, `tick_realization_crisis`, `tick_turnover_crisis`, `tick_reproduction_crisis`
- [x] T077 Add circulation attributes to `read_tick_state_from_graph()` in `src/babylon/economics/tick/graph_bridge.py` — reconstruct CirculationCrisisState from territory node attributes with fallback defaults
- [x] T078 Update system order tests in `tests/unit/engine/test_system_order.py` — if circulation adds a new system or modifies step count
- [x] T079 Verify integration tests pass — run `poetry run pytest tests/unit/economics/circulation/test_integration.py -v`
- [x] T080 Verify no regressions — run `mise run test:unit`

**Checkpoint**: Circulation state persists across ticks via graph bridge. Annual pipeline includes circulation step. All existing tests still pass.

______________________________________________________________________

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Package exports, type checking, documentation

- [x] T081 [P] Implement package exports in `src/babylon/economics/circulation/__init__.py` — `__all__` list with all public types and functions, grouped imports following `melt/__init__.py` pattern
- [x] T082 [P] Run mypy strict type checking — `poetry run mypy src/babylon/economics/circulation/ --strict` — fix any type errors
- [x] T083 [P] Run ruff lint and format — `poetry run ruff check src/babylon/economics/circulation/ --fix && poetry run ruff format src/babylon/economics/circulation/`
- [x] T084 Add doctest examples to key formulas in `src/babylon/economics/circulation/turnover.py` and `src/babylon/economics/circulation/reproduction.py` — verify with `poetry run pytest --doctest-modules src/babylon/economics/circulation/`
- [x] T085 Run full CI gate — `mise run check` — verify all lint + format + typecheck + unit tests pass
- [x] T086 Verify quickstart.md code examples are accurate — manually test each example from `specs/023-capital-volume-ii/quickstart.md` in a Python REPL

**Checkpoint**: Package is clean, typed, linted, documented, and CI-green.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (types.py) — MVP story
- **US2 (Phase 4)**: Depends on Foundational — can run in parallel with US1
- **US3 (Phase 5)**: Depends on Foundational — can run in parallel with US1, US2
- **US4 (Phase 6)**: Depends on Foundational — can run in parallel with US1-US3
- **US5 (Phase 7)**: Depends on Foundational — can run in parallel with US1-US4
- **US6 (Phase 8)**: Depends on Foundational — can run in parallel with US1-US5
- **US7 (Phase 9)**: Depends on US1 + US2 + US4 + US5 (needs circuit, turnover, reproduction, inventory)
- **Integration (Phase 10)**: Depends on ALL user stories (US1-US7)
- **Polish (Phase 11)**: Depends on Integration

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational
- **US2 (P1)**: Independent after Foundational
- **US3 (P2)**: Independent after Foundational
- **US4 (P2)**: Independent after Foundational
- **US5 (P3)**: Independent after Foundational
- **US6 (P3)**: Independent after Foundational
- **US7 (P3)**: Depends on US1, US2, US4, US5 (uses their output types in the integrated assessment)

### Within Each User Story

- RED tests MUST be written and FAIL before GREEN implementation
- Run verification command at the end of each story
- Commit after each completed story

### Parallel Opportunities

- T004-T016 (all RED type tests) can run in parallel — all write to same file but test different models
- T017-T023 (all GREEN type implementations) can run in parallel — same file but independent sections
- US1-US6 phases can run in parallel after Foundational completes (different source and test files)
- T040-T042 within US3 are parallelizable (different test scenarios, same file)
- T047-T049 within US4 are parallelizable
- T055-T056 within US5 are parallelizable
- T060-T062 within US6 are parallelizable
- T081-T083 in Polish are parallelizable (different tools)

______________________________________________________________________

## Parallel Example: User Stories 1 + 2 (After Foundational)

```bash
# Agent A: User Story 1 (Circuit State)
Task: "Write circuit transition tests in tests/unit/economics/circulation/test_circuit.py"
Task: "Implement advance_circuit() in src/babylon/economics/circulation/circuit.py"

# Agent B: User Story 2 (Turnover & Annual Surplus) — runs simultaneously
Task: "Write turnover computation tests in tests/unit/economics/circulation/test_turnover.py"
Task: "Implement compute_annual_surplus_value() in src/babylon/economics/circulation/turnover.py"
Task: "Implement default profiles in src/babylon/economics/circulation/defaults.py"
```

## Parallel Example: User Stories 3 + 4 + 5 + 6

```bash
# Agent A: US3 (Fixed/Circulating) — different files from all others
Task: "Write tests in tests/unit/economics/circulation/test_fixed_circulating.py"
Task: "Implement in src/babylon/economics/circulation/fixed_circulating.py"

# Agent B: US4 (Reproduction) — different files
Task: "Write tests in tests/unit/economics/circulation/test_reproduction.py"
Task: "Implement in src/babylon/economics/circulation/reproduction.py"

# Agent C: US5 (Inventory) — different files
Task: "Write tests in tests/unit/economics/circulation/test_inventory.py"
Task: "Implement in src/babylon/economics/circulation/inventory.py"

# Agent D: US6 (Costs) — different files
Task: "Write tests in tests/unit/economics/circulation/test_costs.py"
Task: "Implement in src/babylon/economics/circulation/costs.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational types (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Circuit State)
4. Complete Phase 4: User Story 2 (Turnover & Annual Surplus)
5. **STOP and VALIDATE**: Test US1 + US2 independently
6. These two P1 stories deliver the core Volume II abstraction: capital as process with turnover dynamics

### Incremental Delivery

1. Setup + Foundational → Type system ready
2. US1 + US2 → MVP: Circuit tracking + turnover amplification
3. US3 + US4 → Fixed/circulating + reproduction conditions
4. US5 + US6 + US7 → Inventory + costs + integrated crisis
5. Integration → Wire into tick pipeline
6. Polish → CI-clean, documented, exported

### Parallel Team Strategy

With multiple agents:

1. All complete Setup + Foundational together
2. Once Foundational done:
   - Agent A: US1 (circuit) + US2 (turnover) — both P1
   - Agent B: US3 (fixed/circulating) + US4 (reproduction) — both P2
   - Agent C: US5 (inventory) + US6 (costs) — both P3
3. US7 (integrated crisis) starts when US1, US2, US4, US5 are done
4. Integration starts when all stories are done
5. Polish in parallel after integration

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable (except US7 which integrates)
- TDD enforced: RED tests first, verify they FAIL, then GREEN implementation
- Commit after each completed story phase
- Stop at any checkpoint to validate story independently
- All models use `ConfigDict(frozen=True)` — project standard
- Use `NoDataSentinel` pattern for missing industry data — project standard
- Use `Currency`, `LaborHours` constrained types — project standard
