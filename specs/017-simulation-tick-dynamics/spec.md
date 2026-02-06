# Feature Specification: Simulation Tick Dynamics

**Feature Branch**: `017-simulation-tick-dynamics`
**Created**: 2026-02-06
**Status**: Draft
**Input**: User description: "Create a specification for Simulation Tick Dynamics - integrates all prior economic phases (012-016) into unified per-tick state evolution with national parameters, county-level state, and derived fields"

## Clarifications

### Session 2026-02-06

- Q: What percentage of county failures within a tick should trigger a halt vs allowing the tick to proceed? → A: Data unavailability only applies during initialization from census data (historical validation mode), not during simulation ticks. During simulation, the engine produces all county values; there are no missing counties because the simulation state IS the data source. Census/BEA/QCEW data is only used for seeding initial state.
- Q: Where do precarity indicators (U-6, PTER, NILF) come from? → A: FRED/BLS data seeds initial precarity values during initialization; the simulation derives them from class distribution and transition rates during ticks. The specific FRED series for U-6, PTER, and NILF need further investigation during planning phase to identify the correct connectors.
- Q: How many counties should the MVP support? → A: 10-20 representative counties across diverse economic profiles (deindustrialized Rust Belt, financial hub, agricultural, tech corridor, etc.) to validate the pipeline across different economic contexts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute National Economic Parameters Per Tick (Priority: P1)

As a simulation researcher, I need to compute the national-level economic parameters (MELT, basket visibility, reproductive visibility) for a given simulation year so that all county-level computations within that tick share a consistent national context.

**Why this priority**: National parameters are the foundation that every county-level computation depends on. MELT (tau) is required by throughput position (Feature 014), gamma visibility (Feature 015), and class dynamics (Feature 016). Without computing national parameters first, no downstream computation can proceed. This is the minimum viable tick entry point.

**Independent Test**: Can be fully tested by providing economic data for a known year (e.g., 2015) and validating that computed tau, gamma_basket, and gamma_III match expected values from existing Feature 013/015 calculators.

**Acceptance Scenarios**:

1. **Given** QCEW employment data and BEA GDP data for year 2015, **When** I compute national parameters for that tick, **Then** the returned MELT (tau) equals GDP / (employment x 2080) consistent with Feature 013 calculator output
2. **Given** ATUS care data and QCEW care sector data for year 2015, **When** I compute national parameters, **Then** gamma_III (reproductive visibility) matches Feature 015 calculator output for the same year
3. **Given** import/ERDI data for year 2015, **When** I compute national parameters, **Then** gamma_basket (basket visibility) matches Feature 013 calculator output for the same year
4. **Given** initialization from census data for a year where BEA GDP data is unavailable (e.g., 2023 if not yet released), **When** I attempt to seed national parameters, **Then** the system returns an unavailability indicator identifying the specific missing data source

______________________________________________________________________

### User Story 2 - Compute County-Level Economic State Per Tick (Priority: P1)

As a simulation researcher, I need to compute the full county-level economic state (value tensor, capital stock, throughput position, supply chain depth) for each county in a given tick year so that class dynamics can use these as inputs.

**Why this priority**: County-level state provides the material conditions that drive class transitions. Without knowing a county's throughput position and capital stock, the system cannot determine wage levels, profit rates, or imperial rent flows that ultimately drive class composition changes. Co-priority with US1 because national parameters (US1) must run first, but county computation is equally essential.

**Independent Test**: Can be tested by computing county state for a known FIPS code and year, validating that value tensor, capital stock, throughput position, and profit rate match the outputs of existing Feature 012/014 calculators for the same inputs.

**Acceptance Scenarios**:

1. **Given** a county FIPS code and year with complete QCEW and BEA data, **When** I compute county economic state, **Then** the capital stock (K) matches Feature 012 calculator output and the throughput position (pi) matches Feature 014 calculator output
2. **Given** initialization from census data for a county with partial data availability (e.g., BEA GDP available but QCEW suppressed), **When** I seed county state, **Then** available fields are computed and unavailable fields return descriptive unavailability indicators with the specific missing source identified
3. **Given** national parameters already computed for the tick year, **When** I compute county throughput position, **Then** pi = tau_through / tau_national uses the national MELT from the current tick (not a stale cached value)
4. **Given** the same county computed across two consecutive tick years, **When** I compare capital stock values, **Then** K[t+1] = K[t] x (1 - delta) + investment[t], demonstrating proper temporal accumulation

______________________________________________________________________

### User Story 3 - Execute Full Tick State Evolution (Priority: P1)

As a simulation researcher, I need to execute one complete tick of state evolution that chains national parameters, county-level state, imperial rent flows, and class transitions in the correct dependency order, producing an updated simulation state for the next tick.

**Why this priority**: This is the core integration point that transforms independent calculators into a unified simulation pipeline. Without orchestrated tick execution, the individual economic computations remain disconnected from each other and from the class dynamics engine. This completes the minimum viable simulation tick.

**Independent Test**: Can be tested by providing a complete simulation state at tick t (with known initial class distribution and economic data) and validating that the output state at tick t+1 has updated class distributions, imperial rent flows, and derived rates consistent with the defined update rules.

**Acceptance Scenarios**:

1. **Given** a complete simulation state at year 2015 with known class distribution, **When** I execute one tick, **Then** the output state has year 2016, updated class distribution (shares sum to 1.0), and computed derived rates (profit rate, imperial rent)
2. **Given** a stable economic year (low unemployment, no crisis), **When** I execute one tick, **Then** class distribution changes are small (total share change less than 2% across all classes)
3. **Given** a crisis economic year (high unemployment, elevated foreclosure), **When** I execute one tick, **Then** downward transitions are amplified and the tick produces crisis-related events
4. **Given** execution of the update rules, **When** I verify the ordering, **Then** steps execute in strict dependency order: (1) load data, (2) national params, (3a) county state, (3b) coefficient smoothing, (4) imperial rent, (5) dispossession check, (6) class transitions, (7) validate and commit class distribution, (8) derived rates — where steps 3a and 3b execute in parallel after step 2

______________________________________________________________________

### User Story 4 - Multi-Tick Historical Simulation (Priority: P2)

As a simulation researcher, I need to run a sequence of ticks covering a historical period (e.g., 2010-2024) to validate that the simulation reproduces historical trajectories of class composition and economic indicators.

**Why this priority**: Historical validation is essential for establishing model credibility, but it depends on single-tick execution (US3) being correct first. Lower priority because it extends single-tick to multi-tick chaining rather than introducing new computation.

**Independent Test**: Can be tested by running 14 consecutive ticks (2010-2024) from a known starting state and comparing output class distributions to historical estimates from Fed SCF wealth surveys.

**Acceptance Scenarios**:

1. **Given** an initial state at year 2010 with plausible class distribution, **When** I run 14 ticks through 2024, **Then** each intermediate state is valid (shares sum to 1.0, no negative shares) and the final distribution falls within expected ranges (bourgeoisie 0.5-2%, petit-bourgeoisie 5-15%, LA 30-50%, proletariat 25-45%, lumpen 10-25%)
2. **Given** the 2010-2024 simulation, **When** I examine the 2008-2012 sub-period (crisis years), **Then** LA share declines and lumpen share increases, matching the directional pattern of the Great Recession
3. **Given** the 2010-2024 simulation, **When** I examine aggregate imperial rent (Phi_aggregate) per year, **Then** values maintain Hickel-scale magnitude (hundreds of billions annually for the US)
4. **Given** a historical validation run where census data coverage ends before the target year range, **When** I inspect the initialization output, **Then** the system reports which years lack sufficient census data for seeding and uses the last available values for initialization

______________________________________________________________________

### User Story 5 - Coefficient Smoothing vs Quantity Updates (Priority: P2)

As a simulation researcher, I need the tick dynamics to distinguish between quantities (which change each tick based on new data) and coefficients (which change slowly via exponential smoothing), so that the simulation maintains stability while remaining responsive to real economic shifts.

**Why this priority**: Without the coefficient/quantity distinction, the simulation will either be too volatile (coefficients jumping year-to-year from noisy data) or too rigid (quantities not reflecting actual economic changes). This is essential for realistic multi-tick behavior but can be implemented after basic tick execution works.

**Independent Test**: Can be tested by introducing a sudden spike in gamma_basket (e.g., from import data anomaly) and verifying that the smoothed coefficient changes gradually while quantity fields (tensor values, capital stock) update immediately.

**Acceptance Scenarios**:

1. **Given** a coefficient (gamma_basket) with value 0.68 at tick t and new data suggesting 0.75 at tick t+1, **When** I apply alpha-smoothing with alpha=0.3, **Then** the smoothed coefficient at t+1 is approximately 0.68 + 0.3 x (0.75 - 0.68) = 0.701 (not the raw 0.75)
2. **Given** a quantity (value tensor T) with new data at tick t+1, **When** I update the simulation state, **Then** T takes the new data value directly (no smoothing applied)
3. **Given** a sequence of 5 ticks where gamma_III oscillates between 0.30 and 0.35 due to noisy ATUS data, **When** I examine the smoothed coefficient trajectory, **Then** it converges toward the mean (~0.325) rather than oscillating at full amplitude
4. **Given** a crisis year where unemployment spikes from 4% to 10%, **When** I update the simulation, **Then** the unemployment quantity reflects the actual 10% immediately (no smoothing on precarity indicators)

______________________________________________________________________

### User Story 6 - Derived Economic Indicators Per Tick (Priority: P3)

As a simulation researcher, I need the tick to compute derived economic indicators (profit rate, organic composition of capital, exploitation rate, aggregate imperial rent) from the updated state so that I can analyze macro-economic trends across the simulation timeline.

**Why this priority**: Derived indicators are outputs consumed by analysis and visualization, not inputs to core simulation dynamics. They can be computed after all state updates are complete, making them lower priority than the core tick pipeline.

**Independent Test**: Can be tested by computing derived indicators for a known county-year state and validating against manual calculations of profit rate (r = s / (K + v)), OCC (c / v), and exploitation rate (s / v).

**Acceptance Scenarios**:

1. **Given** an updated county state with known surplus (s), variable capital (v), and capital stock (K), **When** I compute derived rates, **Then** profit rate r = s / (K + v), OCC = c / v, and exploitation rate e = s / v match manual calculations
2. **Given** all county imperial rent flows for a tick year, **When** I compute aggregate imperial rent (Phi_aggregate), **Then** the sum represents total national imperial rent for that year
3. **Given** a multi-tick simulation, **When** I plot profit rate over time, **Then** TRPF (Tendency of the Rate of Profit to Fall) is observable as a declining trend with counter-tendencies
4. **Given** initialization from census data where a county's capital stock cannot be seeded (missing BEA data), **When** I compute derived rates for that county, **Then** rates depending on K return unavailability indicators while rates computable without K (e.g., exploitation rate e = s / v) are still computed

______________________________________________________________________

### Edge Cases

- **What happens when QCEW or BEA data is unavailable during initialization?** This only applies when seeding initial state from census data (historical validation mode). The initialization proceeds with available data; unavailable fields propagate descriptive unavailability indicators. During simulation ticks, the engine produces all values and data gaps cannot occur.
- **What happens when a county has no QCEW employment records during initialization?** County is skipped for initial state seeding; it receives no initial class distribution. This only affects census-data initialization, not simulation ticks.
- **What happens when all counties fail during initialization?** Initialization halts and returns a diagnostic summary listing all county-level failures. The simulation cannot start without at least one initialized county.
- **What happens when the coefficient smoothing alpha is set to extreme values?** Alpha must be in range (0, 1]. Alpha near 0 means very slow adaptation (coefficient barely moves). Alpha=1 means no smoothing (coefficient tracks raw data exactly). Values outside (0, 1] are rejected with a validation error.
- **How does the system handle the first tick (no previous state)?** The initial state must be provided with seed values for class distribution, capital stock, and coefficients. The first tick does not perform smoothing (no previous value to smooth against); it uses raw computed values.
- **What happens when class distribution from Feature 016 violates the sum-to-one invariant?** The tick validates the invariant after class transitions and raises an error if violated (within tolerance of 0.001). This is a hard constraint that must never be silently ignored.
- **What happens during years with overlapping data vintage changes?** (e.g., BEA revises prior-year GDP) The tick uses the most recent data available at computation time. No retroactive adjustment of prior ticks.
- **What happens when derived rate formulas produce division by zero?** For profit rate `r = s / (K + v)`: if `K = 0` and `v = 0`, profit_rate = None. For OCC `c / v` and exploitation rate `e = s / v`: if `v = 0`, both = None. DerivedRates uses `Optional[float]` for all rate fields; None indicates a mathematically undefined result (distinct from NoDataSentinel, which indicates data unavailability during initialization).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute national parameters (MELT tau, basket visibility gamma_basket, reproductive visibility gamma_III) once per tick year using existing Feature 013 and Feature 015 calculators
- **FR-002**: System MUST compute county-level economic state (value tensor, capital stock, throughput position, supply chain depth) per county per tick year using existing Feature 011, 012, and 014 calculators
- **FR-003**: System MUST execute tick update rules in strict dependency order: (1) load new economic data (initialization only — during simulation ticks, state is produced by the engine), (2) compute national parameters, (3a) compute county-level state (K, pi, D per county) and (3b) apply coefficient smoothing (these two steps execute in parallel after step 2), (4) compute imperial rent flows (phi_hour per county), (5) check dispossession triggers (crisis flag detection), (6) simulate class transitions via `ClassTransitionEngine.simulate_transitions()` producing updated ClassDistribution, (7) validate sum-to-one invariant and commit updated class distribution shares, (8) compute derived rates (r, OCC, e, Phi_aggregate)
  **Pipeline Step I/O Mapping**:

  | Step | Inputs | Outputs | Calculator |
  |------|--------|---------|------------|
  | 1 | External sources (QCEW, BEA, ATUS, FRED) | Raw data | Data connectors (initialization only) |
  | 2 | GDP, employment, ATUS, import data | NationalTickParameters (tau, gamma_basket, gamma_III) | `MELTCalculator.get_melt()`, `BasketVisibilityCalculator.get_gamma_basket()`, `GammaIIICalculator.compute()` |
  | 3a | National tau, QCEW/BEA county data | K, pi, D per county | `CapitalStockCalculator.get_K()`, `ThroughputCalculator.compute_metrics()` |
  | 3b | Raw gammas, previous smoothed values | SmoothedCoefficients | `CoefficientSmoother.smooth()` |
  | 4 | County wages, national params, pi | phi_hour per county | `ImperialRentCalculator.compute_phi_hour()` |
  | 5 | unemployment, profit rate history | crisis flag per county | `ThresholdCrisisDetector.is_crisis()` |
  | 6 | EconomicConditions, ClassDistribution | Updated ClassDistribution | `ClassTransitionEngine.simulate_transitions()` |
  | 7 | Updated ClassDistribution | Validated distribution (sum-to-one confirmed) | Invariant validator |
  | 8 | s, v, c, K, phi_hour per county | DerivedRates, Phi_aggregate, TickSummary | `DerivedRateCalculator` |

- **FR-004**: System MUST chain tick outputs to tick inputs: the state produced at tick t becomes the input state at tick t+1
- **FR-005**: System MUST distinguish between quantities and coefficients. **Quantities** (update directly each tick): T (value tensor), K (capital stock — via perpetual inventory dynamics), unemployment_rate, u6_rate, pter_rate, nilf_rate, median_wage, employment, foreclosure_rate, bankruptcy_rate, eviction_rate, supply_chain_depth (computed fresh each tick). **Coefficients** (update via alpha-smoothing): gamma_basket, gamma_III, gamma_import. Smoothing formula: `smoothed[t] = smoothed[t-1] + alpha x (raw[t] - smoothed[t-1])`. This classification is exhaustive for all fields in CountyEconomicState and NationalTickParameters
- **FR-006**: System MUST apply alpha-smoothing with a configurable smoothing parameter alpha (default: 0.3) for coefficient updates

  **Required Calculator Protocol Methods** (verified against Features 011-016 implementations):

  | Calculator | Method | Signature | Returns |
  |------------|--------|-----------|---------|
  | MELTCalculator | `get_melt` | `(year: int)` | `float \| NoDataSentinel` |
  | BasketVisibilityCalculator | `get_gamma_basket` | `(year: int, alpha: float \| None = None, gamma_import: float \| None = None)` | `tuple[float, bool]` |
  | GammaIIICalculator | `compute` | `(year: int)` | `GammaIII \| NoDataSentinel` |
  | CapitalStockCalculator | `get_K` | `(fips: str, year: int)` | `float \| NoDataSentinel` |
  | CapitalStockCalculator | `get_metrics` | `(fips: str, year: int)` | `DerivedTensorMetrics \| NoDataSentinel` |
  | ThroughputCalculator | `compute_metrics` | `(fips: str, year: int)` | `ThroughputMetrics \| NoDataSentinel` |
  | ClassTransitionEngine | `simulate_transitions` | `(dist: ClassDistribution, conditions: EconomicConditions)` | `ClassDistribution \| NoDataSentinel` |
  | ImperialRentCalculator | `compute_phi_hour` | `(wage: float, params: NationalParameters)` | `float` |

- **FR-007**: System MUST compute aggregate imperial rent (Phi_aggregate) per tick year using the annualization formula: `Phi_aggregate = sum over all counties of (phi_hour x county_employment x 2080)`, where phi_hour is imperial rent per labor-hour (from `ImperialRentCalculator.compute_phi_hour()`), county_employment is total county employment, and 2080 is annual hours per worker (52 weeks x 40 hours)
- **FR-008**: System MUST compute derived rates (profit rate r, organic composition OCC, exploitation rate e) per county per tick from the updated state
- **FR-009**: System MUST validate class distribution invariant (shares non-negative, sum to 1.0 within tolerance 0.001) after every tick's class transition step
- **FR-010**: During initialization from census data (historical validation mode), the system MUST propagate unavailability indicators through the pipeline: if a required input is unavailable, dependent outputs also return unavailability indicators with causal chain identifying the original missing source. During simulation ticks, all county values are produced by the engine and unavailability does not occur
- **FR-011**: System MUST support multi-tick execution by iterating single ticks over a year range, accumulating state across ticks
- **FR-012**: System MUST accept an initial simulation state with seed values for class distribution, capital stock, and initial coefficient values for the starting year
- **FR-013**: System MUST integrate with Feature 016 class transition engine to update class distributions using EconomicConditions synthesized from the tick's computed state
- **FR-014**: System MUST synthesize EconomicConditions (unemployment rate, median wage, MELT, phi_hour, foreclosure rate, bankruptcy rate, eviction rate, crisis flag) from the tick's computed state. During initialization, precarity indicators (U-6, PTER, NILF) are seeded from FRED/BLS data. During simulation ticks, precarity indicators are derived from class distribution and transition rates using the following formulas:
  - `U-6 ≈ lumpen_share + precaritization_rate x proletariat_share`
  - `PTER ≈ precaritization_rate x proletariat_share x pter_fraction` (configurable, default 0.4)
  - `NILF ≈ lumpen_share x nilf_fraction` (configurable, default 0.6)

  The `precaritization_rate` is the proletariat-to-lumpen transition rate computed internally by `ClassTransitionEngine` (Feature 016) as `unemployment_rate x eviction_weight + eviction_rate x (1 - eviction_weight)` (default `eviction_weight=0.5`). It is available as the `TransitionRates.precaritization` field produced during `simulate_transitions()`. Coefficients (pter_fraction, nilf_fraction) are traceable to BLS cross-tabulation ratios and are configurable for calibration. **Handoff rule**: The first simulation tick overwrites initialized FRED/BLS precarity values with derived values (no blending); from that point forward, precarity is entirely endogenous
- **FR-015**: System MUST detect crisis conditions using configurable thresholds and set the crisis flag consumed by the class transition engine's crisis amplifier. A county enters crisis when either: (1) `unemployment_rate > unemployment_threshold` (configurable, default 0.08 / 8%), or (2) year-over-year profit rate decline exceeds `profit_rate_decline_threshold` (configurable, default 0.15 / 15%). Both thresholds are exposed as configuration parameters with documented defaults
- **FR-016**: During initialization from census data, the system MUST carry forward the previous tick's class distribution unchanged for any county where data unavailability prevents transition computation. During simulation ticks, all counties produce values and this fallback is not needed
- **FR-017**: System MUST use FIPS codes consistent with existing economics modules for all county-level identification
- **FR-018**: System MUST handle the first tick specially: use raw computed values instead of smoothed coefficients (no previous value exists for smoothing)
- **FR-019**: System MUST produce a per-tick summary including: year, number of counties processed, aggregate imperial rent, national MELT, mean profit rate, and class distribution aggregated across all processed counties
- **FR-020**: During initialization from census data, the system MUST halt and return a diagnostic summary if zero counties can be initialized for a year (complete data failure). During simulation ticks, this cannot occur because the engine produces all values
- **FR-021**: The tick dynamics pipeline MUST be implemented as a System conforming to the engine's System protocol (`step(graph, services, context) -> None`), registered in the materialist causality chain alongside existing Systems
- **FR-022**: The ServiceContainer MUST be extended with economics calculator fields (MELTCalculator, BasketVisibilityCalculator, GammaIIICalculator, CapitalStockCalculator, ThroughputCalculator, ClassTransitionEngine, ImperialRentCalculator) so that the tick dynamics System and other Systems can access them via dependency injection
- **FR-023**: The tick dynamics System MUST store its computed state (national parameters, county economic state, tick summary) in the shared graph metadata so that downstream Systems in the causality chain can consume it
- **FR-024**: The tick dynamics System MUST handle the timescale difference between annual tick computation and the engine's weekly tick cycle by gating full pipeline execution to year boundaries (every `weeks_per_year` engine ticks) and providing cached annual results on intermediate ticks
- **FR-025**: During simulation ticks, if a required upstream calculator (Features 011-016) raises an exception, the tick pipeline MUST halt with an enhanced error context including the pipeline step number, calculator name, county FIPS code (if applicable), and the original exception. Calculator exceptions during simulation MUST NOT be silently converted to NoDataSentinel; NoDataSentinel is reserved for initialization mode only
- **FR-026**: The county set MUST be fixed for the duration of a simulation run. The set of county FIPS codes is defined at initialization and MUST NOT change between ticks. No counties may be added or removed after the simulation begins
- **FR-027**: During initialization from census data, the system MUST behave according to county success rate: 0% initialized = halt with diagnostic summary (per FR-020); 1-89% initialized = proceed with a warning listing all failed counties and their failure reasons; >=90% initialized = proceed normally. All thresholds are relative to the configured county set size
- **FR-028**: When a multi-tick simulation reaches year 2040 (the upper bound of the year constraint) and the next tick would produce year 2041, the system MUST halt and return the final valid state at year 2040 with a diagnostic indicating expected termination at year boundary (not an error condition)
- **FR-029**: When consecutive ticks produce near-identical state (all class distribution share changes < 0.001 across all counties), the system MUST continue execution normally. Economic equilibrium/convergence is an observable outcome, not an error or halt trigger. The TickSummary SHOULD note convergence detection for analysis purposes

### Key Entities

- **SimulationTickState**: Complete state at a point in time, containing the year, national parameters, per-county economic state, per-county class distributions, and smoothed coefficients. Serves as both tick output and next tick input.
- **NationalTickParameters**: Year-scoped national economic context including MELT (tau), basket visibility (gamma_basket), reproductive visibility (gamma_III), and their smoothed variants. Computed once per tick, shared by all counties.
- **CountyEconomicState**: Per-county per-year economic snapshot including value tensor (T), capital stock (K), throughput position (pi), supply chain depth (D), employment (total county employment, used in Phi_aggregate annualization), precarity indicators (U-6, PTER, NILF), and class distribution. During initialization, precarity indicators are seeded from FRED/BLS data; during simulation ticks, they are derived from the engine's class distribution and transition rates.
- **TickSummary**: Aggregate statistics for a completed tick including year, county count, aggregate imperial rent (Phi_aggregate), national MELT, mean profit rate, and national class distribution summary.
- **SmoothedCoefficients**: Container for alpha-smoothed coefficients that persist across ticks, including gamma_basket, gamma_III, and any threshold values subject to smoothing. Carries both the smoothed value and the raw value for diagnostics.
- **UpdateRule**: Ordered step in the tick pipeline with its dependencies, inputs, outputs, and the calculator/engine it delegates to. Defines the execution DAG for one tick.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single tick completes without error for any year in the 2010-2024 range when provided with valid initial state and available economic data
- **SC-002**: Multi-tick simulation from 2010 initial state through 2024 produces final class distributions within expected ranges: bourgeoisie 0.5-2%, petit-bourgeoisie 5-15%, LA 30-50%, proletariat 25-45%, lumpen 10-25%
- **SC-003**: Crisis years (2008-2012 conditions) produce at least 2x the class transition magnitude of stable years (2015-2018 conditions), measured as sum of absolute share changes
- **SC-004**: Aggregate imperial rent (Phi_aggregate) maintains Hickel-scale magnitude across ticks (hundreds of billions of dollars annually for the US)
- **SC-005**: Coefficient smoothing reduces year-over-year coefficient variance by at least 50% compared to raw values when tested against noisy synthetic data
- **SC-006**: Class distribution invariant (sum to 1.0, non-negative shares) holds after every tick in a 14-year simulation without exception
- **SC-007**: Derived rates (profit rate, OCC, exploitation rate) computed per tick show plausible trends: profit rate exhibits gradual decline with counter-tendencies; OCC rises over time
- **SC-008**: During initialization from census data, data unavailability for a single county does not prevent other counties from being initialized; at least 90% of counties with available data initialize successfully. During simulation ticks, all counties always produce values
- **SC-009**: Tick execution order is deterministic: given identical inputs, the same tick produces identical outputs regardless of execution environment

## Assumptions

- The system operates in two modes: (1) initialization from census data, where QCEW/BEA/ATUS data seeds the initial state and data gaps are possible, and (2) simulation ticks, where the engine produces all county values and data unavailability cannot occur
- All Feature 012-016 calculators are implemented and provide their documented interfaces (get_melt, compute_metrics, simulate_transitions, etc.)
- Economic data sources (QCEW, BEA, ATUS, Fed SCF) are available for the 2010-2024 range with expected coverage gaps (BEA may lag 1-2 years)
- Feature 016 class transition engine handles one period of class dynamics and produces valid ClassDistribution outputs
- MVP dispossession data from Feature 016 uses hardcoded national averages by year, sufficient for tick integration
- The existing TensorRegistry (Feature 011) provides ValueTensor4x3 data for county-year lookups
- Bourgeoisie and petit-bourgeoisie class shares are externally determined and relatively stable (per Feature 016 constraint); the tick dynamics engine primarily evolves LA/proletariat/lumpen shares
- One tick of the economics pipeline equals one year of simulation time; however, the engine operates at weekly timescale (~52 engine ticks per year). The tick dynamics System gates its full pipeline execution to year boundaries and provides cached annual results on intermediate engine ticks
- The MVP operates on 10-20 representative counties spanning diverse economic profiles (deindustrialized Rust Belt, financial hub, agricultural, tech corridor, etc.); the county set is configurable as part of the initial state and can scale to all ~3,100 US counties in future enhancements
- Crisis detection uses a simple threshold-based approach for the MVP (see FR-015 for normative requirements and configurable threshold defaults)

## Constraints

- Tick update rules MUST execute in the specified dependency order. Explicit parallelization boundaries: Steps 3a (county-level state) and 3b (coefficient smoothing) MAY execute in parallel after Step 2 completes; within Step 3a, individual county computations MAY execute in parallel across counties. All other steps (1, 2, 4, 5, 6, 7, 8) MUST execute sequentially in order
- SimulationTickState MUST be immutable (frozen Pydantic model with `ConfigDict(frozen=True)`). All state updates MUST produce new instances via `model_copy(update={...})`; in-place mutation is prohibited
- The tick pipeline MUST NOT modify or re-compute data from prior ticks; each tick is a forward-only transformation
- The tick MUST be a pure function of its inputs: given SimulationTickState at t and economic data for year t, it produces SimulationTickState at t+1 deterministically
- Coefficient smoothing alpha MUST be in range (0, 1]; alpha=0 is not permitted as it would freeze coefficients permanently
- The tick MUST NOT generate new economic data; it consumes data produced by external data sources and existing calculators
- Class distribution invariant (sum to 1.0, non-negative) is a hard constraint; any violation halts execution with a diagnostic error
- The tick pipeline MUST be implemented as a System conforming to the engine's System protocol (`step(graph, services, context) -> None`), composable with other Systems in the materialist causality chain. The System protocol may be extended (e.g., ServiceContainer fields) if needed to accommodate economics calculator injection, but the core `step()` contract must be preserved
- The tick dynamics System MUST be positioned in the materialist causality chain after ProductionSystem and before downstream Systems that consume economic state (e.g., ImperialRentSystem), ensuring county-level economic context is available to subsequent Systems within each engine tick

## Dependencies

- **Requires**: Feature 011 (Fundamental Tensor Primitive) for ValueTensor4x3 and TensorRegistry
- **Requires**: Feature 012 (Capital Stock Dynamics) for CapitalStockCalculator and DerivedTensorMetrics
- **Requires**: Feature 013 (MELT Basket Visibility) for MELTCalculator, BasketVisibilityCalculator, ImperialRentCalculator, ClassPositionClassifier
- **Requires**: Feature 014 (Throughput Position) for ThroughputCalculator and ThroughputMetrics
- **Requires**: Feature 015 (Gamma Visibility Tensor) for GammaIIICalculator and ShadowSubsidyCalculator
- **Requires**: Feature 016 (Class Dynamics Engine) for ClassTransitionEngine, ClassDistribution, EconomicConditions
- **Data**: QCEW employment data (2010-2024), BEA GDP data (2010-2022+), ATUS care data (2003-2024), Fed SCF wealth surveys, Eviction Lab/US Courts/ATTOM dispossession data (via Feature 016 hardcoded MVPs), FRED/BLS data for precarity indicators (U-6, PTER, NILF -- specific series TBD during planning)

## Future Enhancements

- **FE-001**: Parallel county computation within a tick using multiprocessing or async patterns for performance scaling to all ~3,100 US counties
- **FE-002**: Adaptive alpha-smoothing where the smoothing parameter adjusts based on data quality or economic regime (higher alpha during stable periods, lower during volatile periods)
- **FE-003**: Retroactive tick adjustment when data revisions arrive (e.g., BEA GDP revisions), allowing replay of affected ticks with corrected data
- **FE-004**: Event emission per tick (DispossessionEvent, CrisisOnsetEvent, RecoveryEvent) for integration with the existing EventBus and observer infrastructure
- **FE-005**: Endogenous crisis detection via TRPF (Tendency of the Rate of Profit to Fall) analysis from Feature 012 profit rate trends, replacing threshold-based crisis flags
- **FE-006**: Inter-county migration modeling where workers move between counties in response to economic conditions, affecting county-level class distributions
- **FE-007**: Bidirectional feedback between tick-level economics and agent-level dynamics, where agent-level outcomes (e.g., struggle events, consciousness shifts) feed back into the next annual tick's economic inputs
