# Tasks: Capital Volume I Production Dynamics

**Input**: Design documents from `/specs/021-capital-volume-i/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md, data-model.md, contracts/

**Tests**: Included per project TDD mandate (CLAUDE.md). Red-Green-Refactor cycle.

**Organization**: Tasks grouped by user story. US1/US2/US3 are independently testable with mock data. US5 adds real data. US4 validates the full pipeline.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: New enums, configuration defines, and shared types needed by all user stories

- [ ] T001 Add DispossessionType and ExploitationMode enums to src/babylon/models/enums.py
- [ ] T002 Add new EventType members (RESERVE_ARMY_PRESSURE, DISPOSSESSION_EVENT, VALUE_TRANSFER, EXPLOITATION_MODE_SHIFT) to src/babylon/models/enums.py
- [ ] T003 [P] Add ReserveArmyDefines configuration class to src/babylon/config/defines.py with sigmoid params k=20, r0=0.08, and saturation ceiling
- [ ] T004 [P] Add DispossessionDefines configuration class to src/babylon/config/defines.py with 8-type intensity weights (foreclosure=0.4, eviction=0.3, displacement=0.15, etc.)
- [ ] T005 [P] Add WorkingDayDefines configuration class to src/babylon/config/defines.py with hours/intensity thresholds (absolute_hours=45, relative_hours=40, intensity_threshold=1.2)
- [ ] T006 Integrate ReserveArmyDefines, DispossessionDefines, WorkingDayDefines into GameDefines in src/babylon/config/defines.py
- [ ] T007 Verify all new enums and defines pass existing test suite with `mise run test:unit`

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema extensions and data source protocols that MUST exist before any mechanism can be implemented

- [ ] T008 Add FactBLSUnemploymentDecomposition table to src/babylon/data/reference/schema.py (county_id, time_id, labor_force, unemployed_u3, unemployed_u6, part_time_economic, discouraged, marginally_attached)
- [ ] T009 [P] Add FactEvictionLabFiling table to src/babylon/data/reference/schema.py (county_id, time_id, filings, executions, filing_rate, execution_rate, renter_households)
- [ ] T010 [P] Add FactForeclosureRate table to src/babylon/data/reference/schema.py (county_id, time_id, filings, completions, filing_rate, completion_rate, mortgaged_units)
- [ ] T011 [P] Add FactCensusInstitutionalOwnership table to src/babylon/data/reference/schema.py (county_id, time_id, total_units, owner_occupied, renter_occupied, institutional_owned, absentee_owned, net_migration_renters)
- [ ] T012 [P] Add FactBLSProductivity table to src/babylon/data/reference/schema.py (industry_id, time_id, avg_weekly_hours, avg_hourly_earnings, output_per_hour, unit_labor_costs)
- [ ] T013 Update __all__ exports in src/babylon/data/reference/schema.py with all 5 new fact tables
- [ ] T014 Add bls_unemployment_years and eviction_lab_years fields to LoaderConfig in src/babylon/data/loader_base.py
- [ ] T015 Verify schema creates cleanly with `mise run test:unit` (no migration errors)

**Checkpoint**: Foundation ready — mechanism and loader implementation can begin

______________________________________________________________________

## Phase 3: User Story 1 — Reserve Army of Labor (Priority: P1)

**Goal**: Compute reserve army composition from labor market data, derive wage pressure coefficient that modifies median_wage

**Independent Test**: Compute reserve army state from mock BLS inputs; verify higher reserve_ratio produces stronger wage pressure via bounded sigmoid

### TDD RED Phase (US1)

- [ ] T016 [P] [US1] Write unit tests for ReserveArmyState model (decomposition, reserve_ratio, wage_pressure) in tests/unit/economics/reserve_army/test_types.py
- [ ] T017 [P] [US1] Write unit tests for DefaultWagePressureCalculator (sigmoid saturation, monotonicity, edge cases) in tests/unit/economics/reserve_army/test_calculator.py
- [ ] T018 [P] [US1] Write unit tests for ReserveArmySystem (graph mutations, event publishing, wage modification) in tests/unit/engine/systems/test_reserve_army_system.py

### TDD GREEN Phase (US1)

- [ ] T019 [P] [US1] Create ReserveArmyState and ReserveArmyDynamics frozen Pydantic models in src/babylon/economics/reserve_army/types.py
- [ ] T020 [P] [US1] Create ReserveArmyDataSource protocol in src/babylon/economics/reserve_army/data_sources.py with get_unemployment_decomposition(fips, year) method
- [ ] T021 [US1] Create SQLiteReserveArmyDataSource implementation reading from FactBLSUnemploymentDecomposition in src/babylon/economics/reserve_army/data_sources.py
- [ ] T022 [US1] Implement DefaultWagePressureCalculator with bounded sigmoid in src/babylon/economics/reserve_army/calculator.py
- [ ] T023 [US1] Implement ReserveArmySystem (System #17) in src/babylon/engine/systems/reserve_army.py — read unemployment data, compute composition, apply wage pressure to territory median_wage
- [ ] T024 [US1] Create src/babylon/economics/reserve_army/__init__.py with package exports
- [ ] T025 [US1] Register ReserveArmySystem at position 5 in _DEFAULT_SYSTEMS in src/babylon/engine/simulation_engine.py (after TickDynamicsSystem, before SolidaritySystem)
- [ ] T026 [US1] Verify all US1 tests pass GREEN with `poetry run pytest tests/unit/economics/reserve_army/ tests/unit/engine/systems/test_reserve_army_system.py -v`

**Checkpoint**: Reserve army computes composition and wage pressure independently with mock data

______________________________________________________________________

## Phase 4: User Story 2 — Dispossession Events (Priority: P1)

**Goal**: Track aggregate dispossession events per territory-tick with value transfer accounting; feed rates to existing class transition engine

**Independent Test**: Emit dispossession events from mock data; verify value transfers balance, intensity computes correctly, class transition engine receives updated rates

### TDD RED Phase (US2)

- [ ] T027 [P] [US2] Write unit tests for DispossessionEvent and TerritoryDispossessionState models in tests/unit/economics/dispossession/test_types.py
- [ ] T028 [P] [US2] Write unit tests for DispossessionIntensityCalculator (weighted sum, zero rates, boundary clamping) in tests/unit/economics/dispossession/test_intensity.py
- [ ] T029 [P] [US2] Write unit tests for DispossessionEventSystem (graph mutations, value transfer balance, event publishing) in tests/unit/engine/systems/test_dispossession_event_system.py

### TDD GREEN Phase (US2)

- [ ] T030 [P] [US2] Create DispossessionEvent and TerritoryDispossessionState frozen Pydantic models in src/babylon/economics/dispossession/types.py
- [ ] T031 [P] [US2] Create TerritoryDispossessionDataSource protocol in src/babylon/economics/dispossession/data_sources.py with get_foreclosure_rate, get_eviction_rate, get_displacement_rate, get_institutional_ownership methods
- [ ] T032 [US2] Create SQLiteDispossessionDataSource implementation reading from FactEvictionLabFiling, FactForeclosureRate, FactCensusInstitutionalOwnership in src/babylon/economics/dispossession/data_sources.py
- [ ] T033 [US2] Implement DispossessionIntensityCalculator with configurable 8-type weights from DispossessionDefines in src/babylon/economics/dispossession/intensity.py
- [ ] T034 [US2] Implement DispossessionEventSystem (System #18) in src/babylon/engine/systems/dispossession_events.py — compute aggregate events, track value transfers, feed rates to existing DispossessionDataSource protocol
- [ ] T035 [US2] Create src/babylon/economics/dispossession/__init__.py with package exports
- [ ] T036 [US2] Register DispossessionEventSystem at position 8 in _DEFAULT_SYSTEMS in src/babylon/engine/simulation_engine.py (after ImperialRentSystem, before DecompositionSystem)
- [ ] T037 [US2] Verify all US2 tests pass GREEN with `poetry run pytest tests/unit/economics/dispossession/ tests/unit/engine/systems/test_dispossession_event_system.py -v`

**Checkpoint**: Dispossession events emit with balanced value transfers and correct intensity independently with mock data

______________________________________________________________________

## Phase 5: User Story 3 — Working Day Characterization (Priority: P2)

**Goal**: Classify territory-sector pairs by exploitation mode (ABSOLUTE/RELATIVE/MIXED); compute consciousness visibility modifier

**Independent Test**: Classify sectors from mock hours/productivity data; verify correct mode assignment and visibility modifier values

### TDD RED Phase (US3)

- [ ] T038 [P] [US3] Write unit tests for WorkingDayState model and ExploitationMode classification in tests/unit/economics/working_day/test_types.py
- [ ] T039 [P] [US3] Write unit tests for DefaultWorkingDayClassifier (threshold logic, visibility modifier, edge cases) in tests/unit/economics/working_day/test_classifier.py

### TDD GREEN Phase (US3)

- [ ] T040 [P] [US3] Create WorkingDayState frozen Pydantic model in src/babylon/economics/working_day/types.py
- [ ] T041 [P] [US3] Create ProductivityDataSource protocol in src/babylon/economics/working_day/data_sources.py with get_avg_weekly_hours and get_labor_intensity_index methods
- [ ] T042 [US3] Create SQLiteProductivityDataSource implementation reading from FactBLSProductivity in src/babylon/economics/working_day/data_sources.py
- [ ] T043 [US3] Implement DefaultWorkingDayClassifier with configurable thresholds from WorkingDayDefines in src/babylon/economics/working_day/classifier.py
- [ ] T044 [US3] Create src/babylon/economics/working_day/__init__.py with package exports
- [ ] T045 [US3] Verify all US3 tests pass GREEN with `poetry run pytest tests/unit/economics/working_day/ -v`

**Checkpoint**: Working day classification produces correct exploitation modes and visibility modifiers independently

______________________________________________________________________

## Phase 6: User Story 5 — Data Loaders (Priority: P1)

**Goal**: Ingest real-world data from BLS, Eviction Lab, HUD/FRED, Census ACS, and BLS Productivity into the 3NF reference database

**Independent Test**: Run each loader against sample data files; verify correct row counts, geographic coverage (Wayne/Oakland/Macomb), and schema validation

### TDD RED Phase (US5)

- [ ] T046 [P] [US5] Write unit tests for BLS unemployment loader (parsing, checkpoint resume, data quality warnings) in tests/unit/data/test_bls_unemployment_loader.py
- [ ] T047 [P] [US5] Write unit tests for Eviction Lab loader (parsing, NoDataSentinel for gaps) in tests/unit/data/test_eviction_lab_loader.py
- [ ] T048 [P] [US5] Write unit tests for foreclosure rate loader (HUD/FRED source, county-level rates) in tests/unit/data/test_foreclosure_loader.py
- [ ] T049 [P] [US5] Write unit tests for Census housing loader (tenure, institutional ownership) in tests/unit/data/test_census_housing_loader.py
- [ ] T050 [P] [US5] Write unit tests for BLS productivity loader (hours, output per hour, NAICS linking) in tests/unit/data/test_bls_productivity_loader.py

### TDD GREEN Phase (US5)

- [ ] T051 [P] [US5] Implement BLSUnemploymentLoader extending DataLoader in src/babylon/data/bls_unemployment/loader.py with VerificationProtocol and checkpoint support
- [ ] T052 [P] [US5] Implement EvictionLabLoader extending DataLoader in src/babylon/data/eviction_lab/loader.py with VerificationProtocol and checkpoint support
- [ ] T053 [P] [US5] Implement ForeclosureRateLoader extending DataLoader in src/babylon/data/foreclosure/loader.py with VerificationProtocol and checkpoint support (HUD/FRED source)
- [ ] T054 [P] [US5] Implement CensusHousingLoader extending DataLoader in src/babylon/data/census_housing/loader.py with VerificationProtocol and checkpoint support
- [ ] T055 [P] [US5] Implement BLSProductivityLoader extending DataLoader in src/babylon/data/bls_productivity/loader.py with VerificationProtocol and checkpoint support
- [ ] T056 [US5] Register all 5 loaders in src/babylon/data/cli.py with mise task entries
- [ ] T057 [US5] Verify all US5 tests pass GREEN with `poetry run pytest tests/unit/data/test_bls_unemployment_loader.py tests/unit/data/test_eviction_lab_loader.py tests/unit/data/test_foreclosure_loader.py tests/unit/data/test_census_housing_loader.py tests/unit/data/test_bls_productivity_loader.py -v`

**Checkpoint**: All 5 data loaders ingest, validate, and checkpoint correctly against sample data

______________________________________________________________________

## Phase 7: User Story 4 — Cross-System Integration (Priority: P2)

**Goal**: Wire reserve army wage pressure into median_wage, dispossession events into class transitions, working day visibility into consciousness; verify feedback loops

**Independent Test**: Run multi-tick simulation with all 3 mechanisms active; verify wage suppression feedback loop, class transition triggering, and consciousness visibility effects

### TDD RED Phase (US4)

- [ ] T058 [US4] Write integration tests for reserve army → median_wage → tensor v feedback in tests/integration/test_volume_i_integration.py
- [ ] T059 [US4] Write integration tests for dispossession events → class transition engine in tests/integration/test_volume_i_integration.py
- [ ] T060 [US4] Write integration tests for exploitation mode visibility → consciousness dynamics in tests/integration/test_volume_i_integration.py

### TDD GREEN Phase (US4)

- [ ] T061 [US4] Wire ReserveArmySystem wage_pressure output to CountyEconomicState.median_wage modifier in src/babylon/engine/systems/reserve_army.py
- [ ] T062 [US4] Wire DispossessionEventSystem rates into existing DispossessionDataSource protocol for DefaultClassTransitionEngine in src/babylon/economics/dispossession/data_sources.py
- [ ] T063 [US4] Wire WorkingDayClassifier visibility_modifier into ConsciousnessSystem exploitation visibility in src/babylon/engine/systems/consciousness.py (or via persistent_data)
- [ ] T064 [US4] Add SimulationEvent subclasses for new EventTypes in src/babylon/models/events.py and wire _convert_bus_event_to_pydantic in src/babylon/engine/simulation_engine.py
- [ ] T065 [US4] Inject reserve_army_data_source, dispossession_data_source, productivity_data_source into ServiceContainer in src/babylon/engine/services.py
- [ ] T066 [US4] Verify multi-tick feedback loop: mechanization → rising reserve army → falling wages → rising s/v with `poetry run pytest tests/integration/test_volume_i_integration.py -v`

**Checkpoint**: All 3 mechanisms produce verified feedback loops in multi-tick simulation

______________________________________________________________________

## Phase 8: Polish and Cross-Cutting Concerns

**Purpose**: Final validation, edge case handling, and full test suite verification

- [ ] T067 [P] Verify all edge cases from spec: reserve_ratio saturation, zero dispossession, empty sectors, flow clamping, value transfer clamping in tests/unit/ (add missing edge case tests)
- [ ] T068 [P] Add SC-001 falsification test: verify reserve army wage pressure produces negative correlation with subsequent wage growth using loaded BLS data for Wayne/Oakland/Macomb counties in tests/integration/test_falsification_criteria.py
- [ ] T069 [P] Add SC-007 calibration test: verify Wayne County dispossession intensity exceeds Oakland County by at least 3x during 2008-2012 using loaded Eviction Lab and foreclosure data in tests/integration/test_falsification_criteria.py
- [ ] T070 [P] Run full lint + typecheck + test suite with `mise run check`
- [ ] T071 Update src/babylon/engine/systems/__init__.py with new system exports
- [ ] T072 Verify EventType count test in tests/unit/topology/test_phase_transition.py matches new count (30 + 4 = 34)
- [ ] T073 Run `mise run qa:verify` to validate formula correctness including wage pressure sigmoid
- [ ] T074 Run quickstart.md validation — verify documented architecture matches implementation

______________________________________________________________________

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (enums and defines must exist for schema references)
- **US1 (Phase 3)**: Depends on Phase 2 — independent of US2, US3, US5
- **US2 (Phase 4)**: Depends on Phase 2 — independent of US1, US3, US5
- **US3 (Phase 5)**: Depends on Phase 2 — independent of US1, US2, US5
- **US5 (Phase 6)**: Depends on Phase 2 (schema tables must exist) — independent of US1, US2, US3
- **US4 (Phase 7)**: Depends on US1 + US2 + US3 completion (wires them together)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Independence

- **US1 (Reserve Army)**: Fully testable with mock ReserveArmyDataSource
- **US2 (Dispossession)**: Fully testable with mock TerritoryDispossessionDataSource
- **US3 (Working Day)**: Fully testable with mock ProductivityDataSource
- **US5 (Data Loaders)**: Fully testable with sample data files against schema
- **US4 (Integration)**: Requires US1+US2+US3 implementations

### Parallel Opportunities

After Phase 2 completes, US1, US2, US3, and US5 can all proceed in parallel:

```
Phase 1 (Setup) → Phase 2 (Foundational) ─┬─► US1 (Reserve Army)      ─┐
                                            ├─► US2 (Dispossession)     ├─► US4 (Integration) → Phase 8
                                            ├─► US3 (Working Day)       ─┘
                                            └─► US5 (Data Loaders)
```

Within each user story, RED phase tests can run in parallel (different files), then GREEN phase proceeds sequentially (dependencies between models → calculators → systems).

______________________________________________________________________

## Parallel Example: User Story 1

```bash
# RED phase — all test files in parallel:
Task: "Write unit tests for ReserveArmyState model in tests/unit/economics/reserve_army/test_types.py"
Task: "Write unit tests for DefaultWagePressureCalculator in tests/unit/economics/reserve_army/test_calculator.py"
Task: "Write unit tests for ReserveArmySystem in tests/unit/engine/systems/test_reserve_army_system.py"

# GREEN phase — models in parallel, then sequential:
Task: "Create ReserveArmyState and ReserveArmyDynamics models in src/babylon/economics/reserve_army/types.py"
Task: "Create ReserveArmyDataSource protocol in src/babylon/economics/reserve_army/data_sources.py"
# Then sequential (depends on models):
Task: "Implement DefaultWagePressureCalculator in src/babylon/economics/reserve_army/calculator.py"
Task: "Implement ReserveArmySystem in src/babylon/engine/systems/reserve_army.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T015)
3. Complete Phase 3: US1 — Reserve Army (T016-T026)
4. **STOP and VALIDATE**: Reserve army computes composition and applies wage pressure
5. Can demo wage pressure effects on median_wage

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Reserve Army) → Test independently → Commit (MVP!)
3. US2 (Dispossession) → Test independently → Commit
4. US3 (Working Day) → Test independently → Commit
5. US5 (Data Loaders) → Test against sample data → Commit
6. US4 (Integration) → Multi-tick feedback loops verified → Commit
7. Polish + Calibration → Full suite green + falsification tests pass → Commit

### Parallel Team Strategy

With multiple agents:
1. All agents complete Setup + Foundational together
2. Once Foundational is done:
   - Agent A: US1 (Reserve Army)
   - Agent B: US2 (Dispossession)
   - Agent C: US3 (Working Day)
   - Agent D: US5 (Data Loaders — all 5 loaders are [P])
3. After A+B+C complete: Any agent handles US4 (Integration)
4. Any agent handles Polish

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD RED-GREEN-REFACTOR cycle mandatory per CLAUDE.md
- Commit after each phase checkpoint per project commit guidelines
- All constants in GameDefines, never hardcoded (Constitution III.1)
- All data sources traced to approved federal sources (Constitution III.4)
