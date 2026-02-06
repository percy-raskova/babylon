# Research: Simulation Tick Dynamics (Feature 017)

**Date**: 2026-02-06
**Feature**: 017-simulation-tick-dynamics

## R1. Two-Mode Architecture (Initialization vs Simulation)

**Decision**: The tick dynamics system operates in two distinct modes: (1) initialization from census data, and (2) simulation tick execution.

**Rationale**: During initialization, QCEW/BEA/ATUS data seeds the initial SimulationTickState. Data gaps are expected (BEA lags 1-2 years, QCEW suppresses small counties). During simulation ticks, the engine produces all county values deterministically from prior state -- there are no data gaps because the simulation IS the data source.

**Alternatives considered**:
- Single-mode design where every tick queries external data sources. Rejected: creates unnecessary coupling to data availability during ongoing simulation, and conflicts with the pure-function constraint.
- Lazy initialization where counties initialize on first access. Rejected: makes tick execution non-deterministic and harder to test.

## R2. Integration Point: Engine System (TickDynamicsSystem)

**Decision**: Feature 017 implements as a `TickDynamicsSystem` conforming to the engine's System protocol (`step(graph, services, context) -> None`), registered in the `_DEFAULT_SYSTEMS` materialist causality chain. The ServiceContainer is extended with economics calculator fields for dependency injection.

**Rationale**: All simulation mechanics must integrate through the existing engine infrastructure rather than building parallel systems. The System protocol is the established interface for simulation components, and the ServiceContainer is the established DI mechanism. While the tick dynamics pipeline operates at a different abstraction level (county aggregates vs per-node mutations) and timescale (annual vs weekly), these differences are bridged within the System implementation:

1. **Abstraction level**: Territory nodes in the graph carry FIPS codes and economic attributes. The TickDynamicsSystem reads county data from Territory nodes, runs the 8-step pipeline, and writes results back to Territory nodes and graph metadata. Downstream Systems access results through the standard graph interface.
2. **Timescale**: The System gates full pipeline execution to year boundaries (`context.tick % weeks_per_year == 0`). On intermediate weekly ticks, cached annual results remain in graph metadata without re-computation.
3. **State storage**: National parameters and tick summary are stored in `graph.graph["tick_dynamics"]`. County-level state is stored on Territory nodes. This follows the same pattern as ProductionSystem storing `la_production` in graph metadata.

**ServiceContainer extension**: Economics calculator fields (MELTCalculator, CapitalStockCalculator, etc.) are added as optional fields (default `None`) to preserve backward compatibility. Only Systems that need economics calculators access them.

**Alternatives considered**:
- Standalone service outside the engine System chain. Rejected: creates a parallel system that doesn't integrate with existing infrastructure. Other Systems cannot access economics data through the standard graph interface, and the materialist causality ordering is broken.
- Separate DI container for economics calculators. Rejected: the ServiceContainer already exists for this purpose. Adding fields is simpler and more consistent than introducing a second DI mechanism.

## R3. Precarity Indicator Data Sources (FRED Series)

**Decision**: Precarity indicators (U-6, PTER, NILF) are seeded from FRED/BLS data during initialization. During simulation ticks, they are derived from the engine's class distribution and transition rates.

**FRED Series Identification** (requires further investigation during implementation):
- **U-6**: FRED series `U6RATE` (Total unemployed + marginally attached + employed part time for economic reasons). National monthly data, available 1994-present.
- **PTER**: FRED series `LNS12032194` (Employed usually working part time, economic reasons). National monthly data.
- **NILF**: FRED series `LNU05000000` (Not in labor force). National monthly data.
- County-level breakdown may require BLS Local Area Unemployment Statistics (LAUS) for U-3, with U-6 estimated via national U-6/U-3 ratio applied to county U-3.

**Simulation-mode derivation formulas** (to be calibrated during implementation):
- `U-6_sim ≈ lumpenproletariat_share + precaritization_rate * proletariat_share`
- `PTER_sim ≈ precaritization_rate * proletariat_share * pter_fraction` (where pter_fraction ~ 0.4)
- `NILF_sim ≈ lumpenproletariat_share * nilf_fraction` (where nilf_fraction ~ 0.6)

**Rationale**: These derivation formulas ensure that simulation-produced precarity indicators respond to class dynamics without requiring external data during tick execution.

## R4. MVP County Set Selection

**Decision**: 10-20 representative counties across diverse economic profiles.

**Proposed County Set** (to be finalized during implementation):

| FIPS | County | Profile | Why |
|------|--------|---------|-----|
| 26163 | Wayne County, MI | Deindustrialized, Black internal colony | Detroit case study (Constitution IV) |
| 26125 | Oakland County, MI | Affluent suburb | Detroit comparison (Constitution IV) |
| 36061 | New York County, NY | Financial hub | Global finance node |
| 06037 | Los Angeles County, CA | Mixed economy, large | Immigration, tech, service |
| 17031 | Cook County, IL | Industrial-to-service transition | Chicago Rust Belt |
| 48201 | Harris County, TX | Energy, petrochemical | Oil economy dynamics |
| 06085 | Santa Clara County, CA | Tech corridor | Silicon Valley |
| 19153 | Polk County, IA | Agricultural heartland | Rural economy |
| 42003 | Allegheny County, PA | Post-industrial recovery | Pittsburgh transition |
| 12086 | Miami-Dade County, FL | Service, tourism, immigration | Peripheral economy |
| 51760 | Richmond City, VA | Government, service | Southern urbanism |
| 39035 | Cuyahoga County, OH | Deindustrialized | Cleveland Rust Belt |

**Rationale**: Covers the Constitution's Detroit test case (Wayne/Oakland), plus diversity across economic base (finance, tech, energy, agriculture, service, industrial), geography (Midwest, South, West, Northeast), and demographic composition.

## R5. Alpha-Smoothing Parameter Calibration

**Decision**: Default alpha = 0.3 for all coefficients. Configurable per coefficient type.

**Rationale**: Alpha = 0.3 gives a half-life of approximately 2 ticks (years), meaning a sudden shock is 50% absorbed after 2 years. This matches the empirical observation that structural economic parameters (like wage shares, import visibility) adjust over multi-year timescales rather than instantaneously.

**Formula**: `smoothed[t] = smoothed[t-1] + alpha * (raw[t] - smoothed[t-1])`
- Half-life: `ln(0.5) / ln(1 - alpha) ≈ 1.94` ticks for alpha=0.3
- After 5 ticks: 83% converged to new level

**Coefficients subject to smoothing**:
- `gamma_basket` (basket visibility)
- `gamma_III` (reproductive visibility)
- `gamma_import` (import visibility)

**Quantities NOT smoothed** (update directly):
- Value tensor (T)
- Capital stock (K) -- already has its own perpetual inventory dynamics
- Unemployment rate, PTER, NILF
- Foreclosure, bankruptcy, eviction rates

## R6. Crisis Detection Thresholds

**Decision**: Simple threshold-based crisis detection for MVP.

**Crisis triggers** (ANY one triggers crisis flag):
1. Unemployment rate > 8% (configurable threshold)
2. Year-over-year profit rate decline > 15% (configurable threshold)

**Rationale**: Feature 016's CrisisAmplifier expects a boolean `crisis` flag. The MVP uses simple thresholds that capture obvious crisis periods (2008-2012 unemployment spike, 2020 pandemic spike). Future enhancement FE-005 replaces this with endogenous TRPF-based detection.

**Alternatives considered**:
- Multi-factor composite score. Rejected for MVP: adds complexity without clear calibration data.
- TRPF-based detection from Feature 012 profit rate trends. Deferred to FE-005: requires multi-year profit rate history to detect tendency vs counter-tendency.

## R7. Existing Calculator Integration Pattern

**Decision**: Economics calculators are injected via the extended ServiceContainer, following the existing DI pattern. The `TickDynamicsSystem` accesses them through `services.melt_calculator`, `services.capital_calculator`, etc.

**ServiceContainer extension** (new optional fields):
```
ServiceContainer(
    # ... existing fields (config, database, event_bus, formulas, defines, metrics) ...
    melt_calculator: MELTCalculator | None = None,
    basket_calculator: BasketVisibilityCalculator | None = None,
    gamma_calculator: GammaIIICalculator | None = None,
    capital_calculator: CapitalStockCalculator | None = None,
    throughput_calculator: ThroughputCalculator | None = None,
    transition_engine: ClassTransitionEngine | None = None,
    imperial_rent_calculator: ImperialRentCalculator | None = None,
)
```

Each calculator is typed as a Protocol, enabling mock substitution in tests. Optional fields preserve backward compatibility -- existing code that doesn't use economics calculators continues unchanged. The TickDynamicsSystem coordinates the call order but doesn't duplicate any calculator logic. Internal helpers (CrisisDetector, CoefficientSmoother, DerivedRateCalculator, PrecarityDeriver) are owned by the System directly, not shared via ServiceContainer.

## R8. Timescale: Annual System Within Weekly Engine

**Decision**: Feature 017's economics pipeline is annual (one pipeline execution = one year). Within the engine's weekly tick cycle, the TickDynamicsSystem gates execution to year boundaries and provides cached results on intermediate ticks.

**Rationale**: All Feature 012-016 calculators operate on annual data (QCEW annual, BEA annual GDP, ATUS annual surveys). The class transition engine (Feature 016) models annual transitions. Forcing weekly granularity would require interpolating annual data to weekly, adding noise without information.

**Gating mechanism**: The TickDynamicsSystem checks `context.tick % defines.timescale.weeks_per_year == 0`. On year-boundary ticks, the full 8-step pipeline executes and writes results to graph metadata and Territory nodes. On intermediate weekly ticks, the System is a no-op (cached results from the last annual execution remain in the graph for other Systems to consume).

**Downstream System access**: Other Systems (ImperialRentSystem, SurvivalSystem, etc.) can read economics data from graph metadata (`graph.graph["tick_dynamics"]`) or Territory node attributes on any tick within the year. The data represents the most recent annual computation.
