# Research: 020-detroit-vertical-slice

**Date**: 2026-02-23

## Research Questions & Findings

### RQ-1: How do calculators reach systems during tick execution?

**Finding**: The module-level `step()` function (`simulation_engine.py:367`) creates a **fresh** `ServiceContainer` every tick via `ServiceContainer.create(config, effective_defines)`. `Simulation._services` is never passed to `step()`. `Simulation._step_single()` calls `step(state, config, persistent_context, defines)` — no services parameter.

**Decision**: Add an optional `calculator_overrides: dict[str, Any] | None = None` parameter to `step()`. When provided, these are forwarded to `ServiceContainer.create(**calculator_overrides)`. This preserves the fresh-ServiceContainer-per-tick lifecycle (fresh EventBus, etc.) while injecting pre-built calculators.

**Rationale**: Passing a pre-built ServiceContainer would require managing EventBus lifecycle across ticks. Passing calculator instances as kwargs is simpler — `ServiceContainer.create()` already accepts all 7 calculator keyword arguments.

**Alternatives considered**:
- Pass full ServiceContainer to step() — rejected (EventBus lifecycle issues)
- Store calculators in persistent_context dict — rejected (mixing concerns, persistent_context is for tick-level data like previous_wages)
- Modify GameDefines to carry calculators — rejected (GameDefines is configuration, not runtime objects)

### RQ-2: How does TensorRegistry reach systems?

**Finding**: `ServiceContainer` has no `tensor_registry` field. `TickDynamicsSystem._get_profit_rate()` already uses `getattr(services, "tensor_registry", None)` at line 634, which always returns None. TensorRegistry lives only on `Simulation._tensor_registry`.

**Decision**: Add a `tensor_registry: Any = field(default=None)` field to `ServiceContainer` dataclass and a corresponding `tensor_registry` kwarg to `ServiceContainer.create()`. Pass it through `calculator_overrides` alongside the 7 calculators.

**Rationale**: The code already expects it via getattr. Making it a real field gives type safety and IDE support. Using `Any` matches the existing calculator field pattern.

**Alternatives considered**:
- Store on graph metadata — rejected (graph is rebuilt from WorldState each tick via to_graph/from_graph, metadata would be lost)
- Store on TickContext — rejected (TickContext is per-tick lifecycle, registry persists across ticks)

### RQ-3: What calculator sub-dependencies are missing?

**Finding**: Three protocols have NO production implementation in `src/`:

| Protocol | Required By | Missing Implementation |
|----------|------------|----------------------|
| `melt.data_sources.BEADataSource` | DefaultMELTCalculator | `get_gdp(year) -> float \| None` — needs to aggregate `fact_bea_national_industry.value_added_millions` |
| `melt.data_sources.QCEWDataSource` | DefaultMELTCalculator | `get_national_employment(year) -> int \| None` — needs to aggregate `fact_qcew_annual.employment` nationally |
| `gamma.data_sources.UnpaidCareHoursSource` | DefaultGammaIIICalculator | `get_unpaid_care_hours(year) -> float \| None` — no ATUS data in database |

All other sub-dependencies have production implementations:
- `BEACountyGDPSource` → `SQLiteBEACountyGDPSource` (throughput/adapters.py:73)
- `QCEWCountyNAICSSource` → `SQLiteQCEWCountyNAICSSource` (throughput/adapters.py:188)
- `SupplyChainAnalyzer` → `DefaultSupplyChainAnalyzer` (throughput/supply_chain.py:132)
- `AccumulationCalculator` → `DefaultAccumulationCalculator` (dynamics/accumulation.py:29)
- `DispossessionCalculator` → `DefaultDispossessionCalculator` (dynamics/dispossession.py:39)
- `CrisisAmplifier` → `DefaultCrisisAmplifier` (dynamics/crisis.py:58)
- `SavingsRateSource` → `DefaultSavingsRateSchedule` (dynamics/savings_schedule.py:35)
- `DispossessionDataSource` → `HardcodedNationalDispossessionSource` (dynamics/hardcoded_data.py:74)
- `PaidCareHoursSource` → `QCEWCareAdapter` (gamma/adapters.py:68)

**Decision**: Create three minimal adapters:
1. `SQLiteBEANationalGDPSource` — aggregates `fact_bea_national_industry.value_added_millions` by year
2. `SQLiteQCEWNationalEmploymentSource` — aggregates `fact_qcew_annual.employment` nationally
3. `MVPUnpaidCareHoursSource` — hardcoded ATUS estimates (same pattern as `HardcodedNationalDispossessionSource`)

**Rationale**: These are database ADAPTERS (bridge code between existing tables and existing protocols), not new data sources or loaders. The spec forbids new data sources/loaders but requires wiring. Without these adapters, DefaultMELTCalculator and DefaultGammaIIICalculator cannot be instantiated. The UnpaidCareHoursSource uses hardcoded estimates following the same pattern as the existing `HardcodedNationalDispossessionSource`.

### RQ-4: What data actually exists in the database?

**Finding**:

| Data | Years in DB | Notes |
|------|------------|-------|
| QCEW county (Wayne/Oakland) | **2015-2023** (default loader config) | Files on disk cover 2010-2024 but only 2015-2023 loaded |
| BEA County GDP | **2001-2023** | 1.99M rows, covers both target FIPS codes |
| BEA National Industry | **In DB** (2000-2020+) | Source XLSX files no longer on disk but data was loaded |
| Census ACS | **2010, 2023** (two vintages) | 14 fact tables with income, employment, housing data |

**Decision**: The vertical slice time series will span **2015-2023 (9 years, 468 ticks)**, not 2010-2025 (15 years, 780 ticks). The spec assumption already allows this: "If years 2010-2012 are unavailable, the time series will start from 2013."

**Implication for US4 (Validation)**: Census comparison is limited to **2023 only** (2010 census data exists but QCEW starts at 2015, so model output at 2010 is unavailable). Validation harness should compare model 2023 output against Census 2023 data.

### RQ-5: How is TickDynamicsSystem's base year determined?

**Finding**: `_determine_year()` at system.py:204 uses `2010 + tick // WEEKS_PER_YEAR`. This is hardcoded. If QCEW data starts at 2015, the first 260 ticks (years 2010-2014) would have no tensor data, triggering carry-forward from... nothing (no earlier data exists).

**Decision**: Make the base year configurable. The factory will determine the earliest available year in TensorRegistry and configure the simulation's start year accordingly. `TickDynamicsSystem._determine_year()` should read the base year from graph metadata or SimulationConfig rather than hardcoding 2010.

**Rationale**: The carry-forward clarification (use most recent data + warning) only works when there IS earlier data. Starting the simulation at the first available data year avoids this edge case entirely.

### RQ-6: How should ProductionSystem access tensor data?

**Finding**: `ProductionSystem.step()` receives `ServiceContainer` which will now have a `tensor_registry` field. Territory nodes in the graph have a `fips_code` attribute (set during territory hydration in `Simulation.from_sqlite()` at lines 191-195). The current production formula is: `produced_value = (base_labor_power * population) * bio_ratio`.

**Decision**: ProductionSystem checks `services.tensor_registry` for the territory's tensor. If available, uses `tensor.total_v` (total variable capital across all departments) as a proxy for productive capacity. Falls back to `base_labor_power` if tensor is unavailable.

**Rationale**: Variable capital (v) represents the living labor employed in production — the most direct proxy for productive capacity available in the tensor. `total_v` aggregates across all four departments, giving a comprehensive measure of county-level production.

### RQ-7: What is the complete dependency wiring graph?

**Finding**: The full instantiation order with transitive dependencies:

```
Level 0 (no deps):
  DefaultBasketVisibilityCalculator()
  DefaultImperialRentCalculator()

Level 1 (data source adapters):
  SQLiteBEANationalGDPSource(session_factory)       [NEW]
  SQLiteQCEWNationalEmploymentSource(session_factory) [NEW]
  MVPUnpaidCareHoursSource()                          [NEW]
  QCEWCareAdapter()                                   [existing]
  DefaultSavingsRateSchedule()                        [existing]
  HardcodedNationalDispossessionSource()              [existing]
  SQLiteBEACountyGDPSource(session_factory)           [existing]
  SQLiteQCEWCountyNAICSSource(session_factory)        [existing]

Level 2 (calculators with data deps):
  DefaultMELTCalculator(bea_national, qcew_national)
  CapitalStockCalculator(tensor_registry)
  DefaultGammaIIICalculator(unpaid_source, paid_source)
  DefaultAccumulationCalculator(savings_source)
  DefaultDispossessionCalculator(disp_data_source)
  DefaultCrisisAmplifier()

Level 3 (calculators with calculator deps):
  DefaultSupplyChainAnalyzer(qcew_county_source)
  DefaultThroughputCalculator(bea_county, qcew_county, supply_chain, melt_calculator)
  DefaultClassTransitionEngine(acc_calc, disp_calc, crisis_amp)
```

Total: 3 new adapter classes + 1 factory function + modifications to 4 existing files.
