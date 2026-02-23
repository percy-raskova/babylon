# Implementation Plan: Detroit Vertical Slice Integration

**Branch**: `020-detroit-vertical-slice` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/020-detroit-vertical-slice/spec.md`

## Summary

Wire existing data layer (TensorRegistry + QCEW/BEA data), economics calculators (7 standalone classes), and game engine (12-system tick loop) into a single pipeline. The core problem: `step()` creates a fresh ServiceContainer every tick with all calculator slots set to None. The solution: a factory function that instantiates all calculators from a database session, passed through `step()` as `calculator_overrides` to `ServiceContainer.create()`. Additionally, add `tensor_registry` to ServiceContainer so ProductionSystem and TickDynamicsSystem can access real county-level data.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x, NetworkX 3.x, SQLAlchemy 2.x (all existing)
**Storage**: SQLite (marxist-data-3NF.sqlite) — read-only during simulation
**Testing**: pytest with markers (unit, integration, math)
**Target Platform**: Linux (local simulation)
**Project Type**: Single Python package (src/babylon/)
**Performance Goals**: 468-tick simulation (9 years) completes without timeout. No specific latency target.
**Constraints**: No database I/O during tick execution (Constitution II.6). All data hydrated at simulation creation.
**Scale/Scope**: 2 counties (Wayne, Oakland), 9 years (2015-2023), 468 ticks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | PASS | Wiring DefaultImperialRentCalculator computes Phi from real MELT data |
| I.3 TRPF with Counter-Tendencies | PASS | Profit rates derived from tensor data, not assumed stable |
| I.5 Department III | PASS | ValueTensor4x3 includes Dept III; GammaIIICalculator wired |
| II.2 Primitives vs Derived | PASS | QCEW wages are primitives; calculators derive v, s, c, r, Phi |
| II.4 Quantities vs Coefficients | PASS | TickDynamicsSystem uses alpha-smoothing on coefficients |
| II.5 AI Observes, Never Controls | PASS | No AI involvement in this feature |
| II.6 State is Data, Engine is Transformation | PASS | No DB I/O during ticks. Factory creates calculators at startup; step() is pure transformation |
| III.1 No Magic Constants | PASS | Production values derived from QCEW data, not hardcoded. Fallback to base_labor_power only when data absent |
| III.2 Falsifiability Required | PASS | US4 validation harness provides falsifiability gate |
| III.4 Data Source Traceability | PASS | All data from QCEW, BEA, Census (approved sources). New adapters query existing tables |
| IV. Metro Detroit Test Case | PASS | **This feature IS the Detroit test case** — directly implements Constitution Section IV |
| V.1 Material Base First | PASS | Economic dynamics only; no superstructure mechanics |
| V.2 Zoom Where Data Exists | PASS | Detroit has rich QCEW/BEA data in DB |
| V.3 Flag Scope Creep | PASS | Tightly scoped to wiring existing components |

No violations detected. This feature directly fulfills the constitutional mandate for the Detroit 2010-2025 test case (Section IV).

## Project Structure

### Documentation (this feature)

```text
specs/020-detroit-vertical-slice/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 entity definitions
├── quickstart.md        # Phase 1 usage guide
├── contracts/
│   └── internal-api.md  # Internal Python API contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── economics/
│   ├── factory.py                    # NEW: Calculator factory function
│   ├── melt/
│   │   ├── adapters.py               # NEW: SQLiteBEANationalGDPSource, SQLiteQCEWNationalEmploymentSource
│   │   ├── melt_calculator.py        # EXISTING (unchanged)
│   │   ├── basket_visibility.py      # EXISTING (unchanged)
│   │   ├── imperial_rent.py          # EXISTING (unchanged)
│   │   └── data_sources.py           # EXISTING (unchanged)
│   ├── gamma/
│   │   ├── adapters.py               # MODIFIED: Add MVPUnpaidCareHoursSource
│   │   └── gamma_iii.py              # EXISTING (unchanged)
│   ├── throughput/
│   │   ├── adapters.py               # EXISTING (unchanged) — SQLiteBEACountyGDPSource, SQLiteQCEWCountyNAICSSource
│   │   └── calculator.py             # EXISTING (unchanged)
│   ├── dynamics/
│   │   ├── transition_engine.py      # EXISTING (unchanged)
│   │   ├── accumulation.py           # EXISTING (unchanged)
│   │   ├── dispossession.py          # EXISTING (unchanged)
│   │   └── crisis.py                 # EXISTING (unchanged)
│   ├── capital_stock.py              # EXISTING (unchanged)
│   └── tick/
│       └── system.py                 # EXISTING (minor mod: configurable base year)
├── engine/
│   ├── services.py                   # MODIFIED: Add tensor_registry field
│   ├── simulation_engine.py          # MODIFIED: Add calculator_overrides param to step()
│   ├── simulation.py                 # MODIFIED: Wire factory in from_sqlite(), add get_time_series()
│   └── systems/
│       └── production.py             # MODIFIED: Read tensor data for production
└── config/
    └── defines.py                    # EXISTING (unchanged)

tests/
├── unit/
│   ├── economics/
│   │   └── test_factory.py           # NEW: Factory unit tests
│   └── engine/
│       ├── test_services.py          # MODIFIED: Test tensor_registry field
│       └── systems/
│           └── test_production.py    # MODIFIED: Test tensor-aware production
├── integration/
│   └── economics/
│       └── test_detroit_wiring.py    # NEW: End-to-end wiring integration test
└── constants.py                      # EXISTING (may need new test constants)

tools/
└── validate_detroit.py               # NEW: US4 validation harness script
```

**Structure Decision**: All new code fits within the existing `src/babylon/economics/` and `src/babylon/engine/` hierarchy. One new module (`factory.py`), one new adapter file (`melt/adapters.py`), and modifications to 5 existing files. No structural changes to the project layout.

## Implementation Architecture

### Wiring Flow

```
Simulation.from_sqlite(fips, year, years=[2015..2023])
    │
    ├─1─► TensorRegistry.hydrate_counties(hydrator, fips, years)
    │     (existing — already works for multi-year)
    │
    ├─2─► create_economics_services(session_factory, tensor_registry)
    │     │
    │     ├─► Level 0: BasketVisibility(), ImperialRent()
    │     ├─► Level 1: BEANationalGDP(session), QCEWNationalEmployment(session),
    │     │            MVPUnpaidCare(), QCEWCareAdapter(), SavingsSchedule(),
    │     │            HardcodedDispossession(), BEACountyGDP(session),
    │     │            QCEWCountyNAICS(session)
    │     ├─► Level 2: MELT(bea, qcew), CapitalStock(registry), GammaIII(unpaid, paid),
    │     │            Accumulation(savings), Dispossession(data), CrisisAmplifier()
    │     └─► Level 3: SupplyChain(qcew_county), Throughput(bea, qcew, chain, melt),
    │                  TransitionEngine(acc, disp, crisis)
    │
    ├─3─► self._calculator_overrides = {
    │       "melt_calculator": melt, "basket_calculator": basket, ...,
    │       "tensor_registry": tensor_registry
    │     }
    │
    └─4─► Each tick: step(state, config, persistent_ctx, defines, calculator_overrides)
                        │
                        └─► ServiceContainer.create(config, defines, **calculator_overrides)
                              │
                              └─► services.melt_calculator is NOT None
                                  services.tensor_registry is NOT None
                                  → TickDynamicsSystem executes full 8-step pipeline
                                  → ProductionSystem reads tensor data
```

### Data Flow Per Tick

```
Tick N (week W of year Y):
  │
  ├─ ProductionSystem:
  │    for territory in graph:
  │      fips = territory.fips_code
  │      tensor = services.tensor_registry.get(fips, Y)
  │      if tensor is NoDataSentinel:
  │        use base_labor_power (fallback)
  │      else:
  │        produced_value = f(tensor.total_v, population, bio_ratio)
  │
  └─ TickDynamicsSystem (only on year boundary: tick % 52 == 0):
       Y = start_year + tick // 52
       Step 2: tau = services.melt_calculator.get_melt(Y)
       Step 3a: K = services.capital_calculator.estimate(fips, Y)
                pi = services.throughput_calculator.compute_throughput_position(fips, Y)
       Step 4: phi = services.imperial_rent_calculator.compute_phi_hour(wage, params)
       Step 5: crisis = MultiPeriodCrisisDetector.evaluate(...)
       Step 6: dist = services.transition_engine.simulate_transitions(dist, conditions)
       Step 7: validate distributions sum to 1.0
       Step 8: compute tick summary (r, OCC, exploitation, national class dist)
```

### Year Carry-Forward Logic

When TickDynamicsSystem crosses a year boundary and TensorRegistry returns NoDataSentinel for the new year:

1. Query `tensor_registry.available_years(fips)` for the county
2. Find the most recent year <= current year with data
3. Use that year's tensor
4. Log warning: "FIPS {fips}: using {available_year} tensor data for year {current_year}"
5. Mark time series record with `data_source="carry-forward"`

## Key Design Decisions

### D-1: calculator_overrides dict vs pre-built ServiceContainer

**Chosen**: Pass `calculator_overrides` dict to `step()`, forwarded to `ServiceContainer.create()`.

**Why**: ServiceContainer.create() already accepts all calculator kwargs. Creating a fresh ServiceContainer per tick preserves EventBus lifecycle (cleared each tick). Passing the full container would require manual EventBus management.

### D-2: tensor_registry on ServiceContainer vs graph metadata

**Chosen**: Add `tensor_registry` field to ServiceContainer dataclass.

**Why**: TickDynamicsSystem already expects `getattr(services, "tensor_registry", None)`. Making it a real field gives type safety. Graph metadata would be lost during to_graph/from_graph round-trip.

### D-3: Three new adapter classes vs test mocks in production

**Chosen**: Create proper production adapter classes.

**Why**: Test mocks have hardcoded values for specific years. Production adapters query the actual database. The existing pattern (`SQLiteBEACountyGDPSource`, `SQLiteQCEWCountyNAICSSource`) provides a template. MVPUnpaidCareHoursSource follows `HardcodedNationalDispossessionSource` pattern (acceptable per Constitution III.4 data source traceability — ATUS is in the approved list, and the hardcoded values will be documented as ATUS 2015-2022 estimates).

### D-4: Time series span is 2015-2023 (9 years), not 2010-2025

**Chosen**: Use available data range.

**Why**: QCEW data in the database covers 2015-2023 (default loader config). Files on disk cover 2010-2024 but weren't loaded for the full range. The spec assumption explicitly allows reduced range. Reloading the database is out of scope (data operations, not code changes). The factory determines available years dynamically.

### D-5: Configurable base year in TickDynamicsSystem

**Chosen**: Read base year from graph metadata (set during simulation initialization) instead of hardcoded 2010.

**Why**: If data starts at 2015, tick 0 should map to 2015, not 2010. The carry-forward clarification only works when earlier data exists. Starting at the first available year avoids 5 years of data-less ticks.

## Complexity Tracking

No constitution violations to justify. All changes are minimal wiring.

| New Code | Complexity | Justification |
|----------|-----------|---------------|
| `factory.py` (~100 LOC) | Low | Dependency graph is documented in research.md RQ-7. Pure instantiation, no business logic. |
| `melt/adapters.py` (~80 LOC) | Low | SQL aggregate queries. Pattern matches existing SQLiteBEACountyGDPSource. |
| `gamma/adapters.py` addition (~30 LOC) | Low | Hardcoded dict. Pattern matches HardcodedNationalDispossessionSource. |
| `simulation.py` changes (~50 LOC) | Medium | from_sqlite() gains multi-year path. get_time_series() traverses history. |
| `production.py` changes (~20 LOC) | Low | Add tensor lookup with fallback. |
| `simulation_engine.py` changes (~5 LOC) | Low | One new parameter, one line forwarded to create(). |
| `services.py` changes (~5 LOC) | Low | One new field + kwarg. |
