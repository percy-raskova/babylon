# Research: Capital Volume I Production Dynamics

**Feature**: 021-capital-volume-i | **Date**: 2026-02-25

---

## R1. How Reserve Army Wage Pressure Integrates with the Tensor

**Decision**: Reserve army wage pressure operates on `CountyEconomicState.median_wage` (the mutable scalar in the tick dynamics pipeline), NOT on the frozen `ValueTensor4x3`.

**Rationale**: The tensor is a frozen Pydantic model constructed once per `hydrate()` call. Its `v` field equals QCEW wages allocated by department (scaled by SNLT factor, currently 1.0). No mechanism modifies tensor fields after construction. The tick dynamics pipeline (`src/babylon/economics/tick/system.py`) already modifies `median_wage` via wage compression during crisis phases. The reserve army acts as an additional downward modifier on `median_wage`, analogous to how `apply_wage_compression` works in `crisis/wage_compression.py`.

**Alternatives considered**:
- Modify tensor directly: Rejected — tensor is frozen, designed as a historical snapshot. Modifying it would violate II.2 (Primitives vs Derived) since `v` is derived from QCEW primitives.
- Create a new tensor variant: Rejected — adds complexity without benefit. The `median_wage` path is already where dynamic wage adjustments happen.

---

## R2. Where New Systems Fit in the Execution Order

**Decision**: Add two new systems to `_DEFAULT_SYSTEMS`:
- `ReserveArmySystem` at position 5 (after `TickDynamicsSystem`, before `SolidaritySystem`) — wage pressure must be computed before survival calculus reads wages.
- `DispossessionEventSystem` at position 8 (after `ImperialRentSystem`, before `DecompositionSystem`) — dispossession events must be computed after extraction dynamics but before decomposition reads class transitions.

Working day classification does NOT need its own system — it is a quasi-static classification computed from loaded data and stored in `persistent_data`, updated by `TickDynamicsSystem` when data changes.

**Rationale**: The ordering follows materialist causality (ADR032). Reserve army is a material-base mechanism (wages are material). Dispossession transfers value between territories (material redistribution). Working day classification is a derived label, not a per-tick computation.

**Alternatives considered**:
- Single combined system: Rejected — reserve army and dispossession have different inputs and outputs; combining violates single responsibility.
- Three separate systems: Rejected — working day classification doesn't need per-tick computation; quasi-static classifications belong in initialization or periodic updates via `persistent_data`.

---

## R3. How Dispossession Events Connect to Feature 016

**Decision**: New aggregate dispossession events feed updated rates into the existing `DispossessionDataSource` protocol, replacing the `HardcodedNationalDispossessionSource` with a county-level implementation backed by loaded data.

**Rationale**: The existing pipeline is:
1. `DispossessionDataSource.get_foreclosure_rate(fips, year) -> float | None`
2. `DefaultDispossessionCalculator.compute()` applies composite weights: LA→P = 0.6*foreclosure + 0.3*bankruptcy + 0.1*eviction
3. `DefaultClassTransitionEngine.simulate_transitions()` consumes the result

The new loaders (Eviction Lab, CoreLogic) provide county-level rates that slot directly into this protocol. The aggregate dispossession events (FR-004) are a *recording* mechanism layered on top — they capture what happened per tick for observation/narrative, while the rate data feeds the class transition engine.

**Alternatives considered**:
- Bypass existing calculator: Rejected — the composite weighting logic is already correct and tested.
- Modify DispossessionRisk to include aggregate counts: Considered — would add `event_count` and `total_value_transferred` fields alongside existing rate fields. Deferred to implementation; may be cleaner as a separate event model.

---

## R4. New Fact Tables Required

**Decision**: Five new fact tables in the 3NF schema:

1. `FactBLSUnemploymentDecomposition` — county-level U-3, U-6, PTER, discouraged, marginally attached
2. `FactEvictionLabFiling` — county-level eviction filings and executions
3. `FactForeclosureRate` — county-level foreclosure rates (ATTOM or HUD proxy)
4. `FactCensusHousingTenure` — county-level tenure changes, institutional ownership
5. `FactBLSProductivity` — sector-level average weekly hours, output per hour, unit labor costs

All follow the existing `county_id + time_id` or `industry_id + time_id` FK pattern.

**Rationale**: Each table corresponds to one data source and one feature mechanism. Separation enables independent loading, validation, and checkpoint tracking.

**Alternatives considered**:
- Extend existing tables (e.g., add columns to FactCensusEmployment): Rejected — different source granularity (BLS vs Census) and different temporal coverage.
- Single omnibus table: Rejected — violates 3NF; different sources have different schemas.

---

## R5. Data Source Accessibility

**Decision**: For foreclosure data (FR-016), use HUD National Neighborhood Indicators / CoreLogic publicly available aggregates rather than requiring a CoreLogic commercial license. Where county-level foreclosure data is unavailable from free sources, use state-level FRED foreclosure series (`FactFredStateUnemployment` pattern) pro-rated by county mortgage counts from Census.

**Rationale**: CoreLogic data requires an expensive commercial license. ATTOM is also commercial. HUD and FRED provide free public data at coarser granularity. For the Detroit case study, Michigan-specific foreclosure data is available from the Michigan Housing Data Gateway (state source).

**Alternatives considered**:
- Require CoreLogic license: Rejected — creates a hard dependency on commercial data that blocks development.
- Skip foreclosure data entirely: Rejected — SC-002 and SC-007 require it for Wayne County calibration.

---

## R6. Wage Pressure Functional Form

**Decision**: Use a bounded sigmoid function calibrated against Phillips curve literature: `wage_pressure = 1 / (1 + exp(-k * (reserve_ratio - r0)))` where `k` (steepness) and `r0` (inflection point) are configurable in `GameDefines`. Default `r0 = 0.08` (natural rate baseline), `k = 20` (moderate steepness).

**Rationale**: The spec edge case requires saturation at high reserve ratios (no divergence). A sigmoid satisfies this. The Phillips curve literature provides empirical calibration data. The two parameters (`k`, `r0`) are tunable via `GameDefines` following the existing pattern.

**Alternatives considered**:
- Linear: Rejected — diverges at high reserve ratios, violating edge case.
- Logarithmic: Rejected — undefined at zero, requires special-casing.
- Piecewise: Rejected — discontinuous derivatives cause numerical issues in sensitivity analysis.

---

## R7. Dispossession Intensity Weights

**Decision**: Reuse the existing weight structure from `DefaultDispossessionCalculator` for consistency. The composite weights for `dispossession_intensity` are: foreclosure × 0.4, eviction × 0.3, displacement × 0.15, tax_sale × 0.05, eminent_domain × 0.05, wage_theft × 0.03, incarceration × 0.01, pension_default × 0.01. Weights are configurable in `GameDefines`.

**Rationale**: The existing LA→P weights (0.6/0.3/0.1) address class transition. The new intensity weights address *territory-level* impact, where foreclosure and eviction dominate but displacement (net out-migration) is also significant. All weights are configurable to support sensitivity analysis.

**Alternatives considered**:
- Equal weights: Rejected — violates III.1 (No Magic Constants); doesn't reflect that foreclosures transfer more value than wage theft per incident.
- Use only existing 3-category weights: Rejected — the 8-type dispossession taxonomy is richer than the 3-category class transition taxonomy.

---

## R8. Existing `FactCensusHousing` Coverage

**Decision**: The existing `FactCensusHousing` table already stores housing tenure data by county, tenure type, and race. The new `FactCensusHousingTenure` table focuses specifically on *changes* in tenure (year-over-year transitions) and institutional ownership metrics, which are NOT covered by the existing table.

**Rationale**: `FactCensusHousing` stores cross-sectional counts (how many owner-occupied vs renter-occupied). The dispossession mechanism needs *flow* data: how many units changed from owner to renter, how many became institutionally owned. These are computed from year-over-year deltas of the cross-sectional data or from dedicated Census variables (B25003 series for tenure, B25127 for year structure built).

**Alternatives considered**:
- Derive flows from existing FactCensusHousing deltas: Possible but lossy — missing institutional ownership detail. The separate table enables direct loading of ACS B25032 (units in structure by tenure) and B25071 (rent burden) alongside the tenure change computation.
