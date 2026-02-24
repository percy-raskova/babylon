# Tasks: Detroit Vertical Slice Integration

**Input**: Design documents from `/specs/020-detroit-vertical-slice/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included (project mandates TDD per CLAUDE.md)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Exact file paths included in descriptions

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Verify prerequisites and ensure clean starting state

- [X] T001 Verify database exists at data/sqlite/marxist-data-3NF.sqlite with QCEW data for FIPS 26163/26125 (years 2015-2023) and all existing tests pass (mise run test:unit)

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure changes that MUST be complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add tensor_registry field (type Any, default None) to ServiceContainer dataclass and add tensor_registry kwarg to ServiceContainer.create() classmethod in src/babylon/engine/services.py
- [X] T003 [P] Add calculator_overrides parameter (dict[str, Any] | None = None) to step() function and forward as **kwargs to ServiceContainer.create() in src/babylon/engine/simulation_engine.py
- [X] T004 [P] Create SQLiteBEANationalGDPSource (get_gdp(year) -> float | None, aggregates fact_bea_national_industry.value_added_millions) and SQLiteQCEWNationalEmploymentSource (get_national_employment(year) -> int | None, aggregates fact_qcew_annual.employment) implementing melt/data_sources.py protocols in src/babylon/economics/melt/adapters.py (new file)
- [X] T005 [P] Add MVPUnpaidCareHoursSource class implementing UnpaidCareHoursSource protocol with hardcoded ATUS year-keyed estimates (pattern: HardcodedNationalDispossessionSource in dynamics/hardcoded_data.py) in src/babylon/economics/gamma/adapters.py

**Checkpoint**: ServiceContainer accepts tensor_registry and calculator overrides; step() forwards overrides; all 3 missing adapter classes exist

______________________________________________________________________

## Phase 3: User Story 1 — Calculator Factory Wiring (Priority: P0) MVP

**Goal**: Economics calculators auto-instantiated and injected into ServiceContainer when simulation created from database

**Independent Test**: Create simulation via from_sqlite() with years param, verify all 7 ServiceContainer calculator fields are non-None, confirm TickDynamicsSystem executes full 8-step pipeline on first year-boundary tick

### Tests for User Story 1

> Write these tests FIRST, ensure they FAIL before implementation (TDD Red Phase)

- [X] T006 [P] [US1] Write unit tests for create_economics_services() verifying: returns dict with 8 keys (7 calculators + tensor_registry), all values non-None, keys match ServiceContainer field names in tests/unit/economics/test_factory.py (new file)

### Implementation for User Story 1

- [X] T007 [US1] Create create_economics_services(session_factory, tensor_registry) factory function implementing 4-level dependency wiring (L0: basket/imperial_rent, L1: data adapters, L2: melt/capital/gamma/accumulation/dispossession/crisis, L3: supply_chain/throughput/transition_engine) per research.md RQ-7 in src/babylon/economics/factory.py (new file)
- [X] T008 [US1] Modify Simulation.from_sqlite() to accept years: Sequence[int] | None parameter; when provided, hydrate TensorRegistry for all years, call create_economics_services(), store result in self._calculator_overrides in src/babylon/engine/simulation.py
- [X] T009 [US1] Modify Simulation._step_single() to pass self._calculator_overrides (or None) as calculator_overrides kwarg to step() in src/babylon/engine/simulation.py

**Checkpoint**: `Simulation.from_sqlite(["26163","26125"], year=2022, years=[2022])` produces ServiceContainer with all 7 calculators non-None; TickDynamicsSystem runs full pipeline (does not early-return)

______________________________________________________________________

## Phase 4: User Story 2 — Production from Tensor Data (Priority: P0)

**Goal**: ProductionSystem derives production values from ValueTensor4x3 variable capital (v) instead of flat base_labor_power constant, so counties produce different amounts

**Independent Test**: Run one tick of two-county simulation, compare production values for Wayne (26163) and Oakland (26125) — must differ

### Tests for User Story 2

> Write these tests FIRST, ensure they FAIL before implementation (TDD Red Phase)

- [X] T010 [P] [US2] Write unit tests for tensor-aware production: tensor lookup by FIPS succeeds and uses total_v, NoDataSentinel triggers fallback to base_labor_power, two different FIPS produce different values in tests/unit/engine/systems/test_production.py

### Implementation for User Story 2

- [X] T011 [US2] Modify ProductionSystem.step() to check services.tensor_registry for territory's fips_code, use tensor.total_v for production when available (replacing base_labor_power), fallback to base_labor_power when tensor is NoDataSentinel or registry is None in src/babylon/engine/systems/production.py

**Checkpoint**: Wayne County and Oakland County produce different values reflecting their QCEW wage structures; counties without tensor data use base_labor_power

______________________________________________________________________

## Phase 5: User Story 3 — Multi-Year Time Series (Priority: P1)

**Goal**: Run simulation across 2015-2023 QCEW time series (468 ticks), observe class composition shifts, extract structured time series output

**Independent Test**: Run 468-tick simulation, verify year-boundary updates use different tensor data per year, get_time_series() returns 18 records (9 years x 2 counties)

### Implementation for User Story 3

- [X] T012 [US3] Make TickDynamicsSystem._determine_year() read base_year from graph metadata (graph.graph.get("base_year", 2010)) instead of hardcoded 2010 in src/babylon/economics/tick/system.py
- [X] T013 [US3] Set base_year in graph metadata during simulation initialization (graph.graph["base_year"] = min(years)) when years param provided to Simulation.from_sqlite() in src/babylon/engine/simulation.py
- [X] T014 [US3] Implement year carry-forward logic in TickDynamicsSystem: when TensorRegistry returns NoDataSentinel at year boundary, query available_years, use most recent year with data, log warning, tag record data_source="carry-forward" in src/babylon/economics/tick/system.py
- [X] T015 [US3] Add get_time_series() method to Simulation returning list[dict[str, Any]] with keys: year, fips, class_distribution, profit_rate, phi_hour, throughput_position, tau, data_source — one record per county per year-boundary tick in src/babylon/engine/simulation.py

**Checkpoint**: 468-tick simulation completes; get_time_series() returns 18 records; years with missing data use carry-forward; profit rates vary across years

______________________________________________________________________

## Phase 6: User Story 4 — Validation Harness (Priority: P2)

**Goal**: Script runs Detroit time series and outputs comparison table vs Census/ACS 2023 ground truth with divergence metrics

**Independent Test**: Run validation script, verify structured comparison table produced with divergence column

### Implementation for User Story 4

- [X] T016 [US4] Create validation harness: run multi-year Detroit simulation (2015-2023), load Census ACS 2023 income distribution for Wayne/Oakland from database, compute KL divergence or similar metric between model class distribution and Census proxy, output comparison table, handle missing ground truth gracefully in tools/validate_detroit.py (new file)

**Checkpoint**: `python tools/validate_detroit.py` produces a comparison table with columns: year, fips, model_LA_share, census_proxy_LA_share, divergence

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, CI verification, backward compatibility

- [ ] T017 Write end-to-end integration test: from_sqlite() with years → multi-year run (468 ticks) → get_time_series() → verify record count, field presence, value variation across years in tests/integration/economics/test_detroit_wiring.py (new file)
- [ ] T018 Run full CI gate (mise run check) and verify zero test regressions — all existing unit tests must still pass
- [ ] T019 Verify quickstart.md scenarios execute successfully: single-year wired simulation, multi-year Detroit time series, time series extraction

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify prerequisites
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 2 completion; unit tests independent; full integration benefits from US1
- **US3 (Phase 5)**: Depends on US1 (TickDynamicsSystem needs wired calculators to execute)
- **US4 (Phase 6)**: Depends on US1 + US2 + US3 (needs full pipeline for time series)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P0)**: After Phase 2 — no dependencies on other stories
- **US2 (P0)**: After Phase 2 — unit tests independent; integration requires US1
- **US3 (P1)**: After US1 — TickDynamicsSystem needs wired calculators
- **US4 (P2)**: After US1 + US2 + US3 — needs complete pipeline

### Within Each User Story

- Tests (TDD red phase) MUST be written BEFORE implementation
- Factory before wiring (US1: T007 before T008)
- Same-file tasks sequential (T008 before T009, T012 before T014, T013 before T015)

### Parallel Opportunities

- Phase 2: All 4 tasks [P] (different files: services.py, simulation_engine.py, melt/adapters.py, gamma/adapters.py)
- T006 [P] can start while Phase 2 completes (writes new test file)
- T010 [P] can start while US1 implementation proceeds (writes new test file)

______________________________________________________________________

## Parallel Example: Phase 2 (Foundational)

```bash
# All 4 tasks in parallel (different files):
Task T002: "Add tensor_registry to ServiceContainer in services.py"
Task T003: "Add calculator_overrides to step() in simulation_engine.py"
Task T004: "Create melt national adapters in melt/adapters.py"
Task T005: "Add MVPUnpaidCareHoursSource to gamma/adapters.py"
```

## Parallel Example: User Story 1

```bash
# TDD Red Phase (can overlap with Phase 2):
Task T006: "Unit tests for factory in test_factory.py"

# Green Phase (sequential):
Task T007: "Factory function in factory.py"
Task T008: "Modify from_sqlite() in simulation.py"
Task T009: "Modify _step_single() in simulation.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify prerequisites)
2. Complete Phase 2: Foundational (ServiceContainer + step() + adapters)
3. Complete Phase 3: User Story 1 (factory + wiring)
4. **STOP and VALIDATE**: TickDynamicsSystem executes full 8-step pipeline
5. Commit and verify CI passes

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. US1 (Calculator Wiring) → TickDynamicsSystem runs → Commit (MVP!)
3. US2 (Tensor Production) → Counties produce different values → Commit
4. US3 (Multi-Year) → 468-tick simulation with time series → Commit
5. US4 (Validation) → Census comparison table → Commit
6. Each story adds value without breaking previous stories

### File Modification Summary

| File | Phase | Change |
|------|-------|--------|
| `src/babylon/engine/services.py` | Phase 2 | Add tensor_registry field + kwarg (~5 LOC) |
| `src/babylon/engine/simulation_engine.py` | Phase 2 | Add calculator_overrides to step() (~5 LOC) |
| `src/babylon/economics/melt/adapters.py` | Phase 2 | NEW: 2 SQLite adapter classes (~80 LOC) |
| `src/babylon/economics/gamma/adapters.py` | Phase 2 | Add MVPUnpaidCareHoursSource (~30 LOC) |
| `src/babylon/economics/factory.py` | US1 | NEW: create_economics_services() (~100 LOC) |
| `src/babylon/engine/simulation.py` | US1, US3 | Modify from_sqlite(), _step_single(), add get_time_series() (~100 LOC) |
| `src/babylon/engine/systems/production.py` | US2 | Tensor lookup with fallback (~20 LOC) |
| `src/babylon/economics/tick/system.py` | US3 | Configurable base year + carry-forward (~30 LOC) |
| `tools/validate_detroit.py` | US4 | NEW: Validation harness (~100 LOC) |
| `tests/unit/economics/test_factory.py` | US1 | NEW: Factory unit tests |
| `tests/unit/engine/systems/test_production.py` | US2 | Add tensor-aware production tests |
| `tests/integration/economics/test_detroit_wiring.py` | Polish | NEW: E2E integration test |

**Total**: ~290 LOC production code + ~200 LOC tests across 7 production files (4 new, 3 modified) and 3 test files
