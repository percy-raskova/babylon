# Research: Simulation Tick Dynamics (Feature 017)

**Date**: 2026-02-06
**Feature**: 017-simulation-tick-dynamics

## R1. Two-Mode Architecture (Initialization vs Simulation)

**Decision**: The tick dynamics system operates in two distinct modes: (1) initialization from census data, and (2) simulation tick execution.

**Rationale**: During initialization, QCEW/BEA/ATUS data seeds the initial SimulationTickState. Data gaps are expected (BEA lags 1-2 years, QCEW suppresses small counties). During simulation ticks, the engine produces all county values deterministically from prior state -- there are no data gaps because the simulation IS the data source.

**Alternatives considered**:
- Single-mode design where every tick queries external data sources. Rejected: creates unnecessary coupling to data availability during ongoing simulation, and conflicts with the pure-function constraint.
- Lazy initialization where counties initialize on first access. Rejected: makes tick execution non-deterministic and harder to test.

## R2. Integration Point: Standalone Pipeline vs Engine System

**Decision**: Feature 017 implements as a standalone `TickSimulator` service (Protocol + DefaultTickSimulator) in `src/babylon/economics/tick/`, not as a new System in the engine's System chain.

**Rationale**: The existing simulation engine operates on a graph of SocialClass and Territory nodes with in-place mutation. Feature 017 operates on aggregated county-level economic state (FIPS-coded counties, class distributions, tensor data). These are fundamentally different abstraction levels. The tick simulator orchestrates Feature 012-016 calculators into a pipeline that produces `SimulationTickState` -- this is a higher-level orchestration than the per-node graph mutation the engine Systems perform.

Future enhancement FE-007 can bridge the two by having an engine System read from the tick simulator's output state.

**Alternatives considered**:
- New System in the engine's `_DEFAULT_SYSTEMS` list. Rejected: System protocol expects `step(graph, services, context) -> None` with in-place graph mutation. County-level economic orchestration doesn't fit this pattern -- it produces new aggregate state, not node-level mutations.
- Extend ServiceContainer with all calculators. Rejected for MVP: would require wiring 6+ calculator services into ServiceContainer, which is a larger refactor than needed. The tick simulator can own its calculator dependencies independently.

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

**Decision**: The `TickSimulator` owns its calculator dependencies via constructor injection, following the same Protocol pattern used throughout `babylon.economics`.

**Pattern** (from Feature 016's `DefaultClassTransitionEngine`):
```
TickSimulator(
    melt_calculator: MELTCalculator,
    basket_calculator: BasketVisibilityCalculator,
    gamma_calculator: GammaIIICalculator,
    capital_calculator: CapitalStockCalculator,
    throughput_calculator: ThroughputCalculator,
    transition_engine: ClassTransitionEngine,
    imperial_rent_calculator: ImperialRentCalculator,
)
```

Each calculator is injected as a Protocol, enabling mock substitution in tests. The TickSimulator coordinates the call order but doesn't duplicate any calculator logic.

## R8. Timescale: Annual vs Weekly Ticks

**Decision**: Feature 017 ticks are annual (one tick = one year). This is distinct from the existing engine's weekly ticks.

**Rationale**: All Feature 012-016 calculators operate on annual data (QCEW annual, BEA annual GDP, ATUS annual surveys). The class transition engine (Feature 016) models annual transitions. Forcing weekly granularity would require interpolating annual data to weekly, adding noise without information.

The existing engine uses `defines.timescale.weeks_per_year` for weekly conversion. Feature 017 operates at the annual level and does not need this conversion.

**Integration note**: When FE-007 bridges tick dynamics into the engine System chain, the annual results would be spread across ~52 weekly engine ticks via interpolation or step-function application.
