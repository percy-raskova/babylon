# Implementation Prompt: Critical Volume I Gaps for Detroit Vertical Slice

**Load this into plan mode. Read every file referenced. Implement in order.**

---

## Context

Three critical theoretical concepts from Capital Volume I have no implementation
despite being foundational to the Detroit vertical slice (branch
`020-detroit-vertical-slice`). The existing `economics/dynamics/` module
(Feature 016) provides the scaffolding — class transitions, dispossession
risk computation, crisis amplification — but stops short of modeling the
*mechanisms* that drive those transitions in the real world.

Detroit 2007-2020 cannot be simulated without:

1. **Reserve Army of Labor** — the mechanism that disciplines wages downward
2. **Dispossession Event Ledger** — the mechanism that transfers accumulated
   wealth from one class/territory to another
3. **Housing Value Decomposition** — the spatial expression of class struggle
   in Wayne vs Oakland County

These three form a causal chain:
```
Reserve Army (unemployment) -> wage suppression -> foreclosure ->
Dispossession Events -> housing equity transfer ->
Housing Decomposition (Wayne->Oakland value flow)
```

---

## What Already Exists (READ ALL OF THESE FIRST)

### Economics Layer (the foundation you're extending)

```
src/babylon/economics/dynamics/types.py          # ClassDistribution, EconomicConditions, DispossessionRisk
src/babylon/economics/dynamics/data_sources.py    # DispossessionDataSource protocol, others
src/babylon/economics/dynamics/dispossession.py   # DefaultDispossessionCalculator (composite risk)
src/babylon/economics/dynamics/hardcoded_data.py  # HardcodedNationalDispossessionSource (MVP data)
src/babylon/economics/dynamics/transition_engine.py # DefaultClassTransitionEngine (flow equations)
src/babylon/economics/dynamics/accumulation.py    # DefaultAccumulationCalculator
src/babylon/economics/dynamics/crisis.py          # DefaultCrisisAmplifier, PhasedCrisisAmplifier
src/babylon/economics/dynamics/validation.py      # Three-tier validation
src/babylon/economics/tensor.py                   # NoDataSentinel pattern
src/babylon/economics/melt/types.py               # ClassPosition enum
src/babylon/economics/melt/class_position.py      # DefaultClassPositionClassifier
src/babylon/economics/tick/types.py               # CrisisPhase, CountyEconomicState, etc.
src/babylon/economics/tick/system.py              # TickDynamicsSystem
src/babylon/economics/tick/graph_bridge.py        # write_tick_state_to_graph, read_tick_state_from_graph
```

### Brainstorm Documents (theoretical specifications)

```
ai-docs/brainstorms/tensor/capital_volume_i_integration.md     # Sections 2.1 (Reserve Army) and 2.2 (Primitive Accumulation)
ai-docs/brainstorms/tensor/capital_volume_ii_integration.md    # Section 6 (Storage/Inventory, for housing stock context)
ai-docs/brainstorms/tensor/capital_volume_iii_integration.md   # Section 6 (Ground Rent, Housing Value Decomposition)
ai-docs/brainstorms/tensor/capital_volume_integration_memo.md  # TVT framework mappings
```

### Engine Systems (where these feed into the simulation)

```
src/babylon/engine/systems/struggle.py            # StruggleSystem (uprising, wealth destruction)
src/babylon/engine/systems/decomposition.py       # DecompositionSystem (LA decomposition)
src/babylon/engine/systems/economic.py            # ImperialRentSystem (extraction)
src/babylon/engine/systems/territory.py           # TerritorySystem (heat, eviction pipeline)
src/babylon/config/defines.py                     # GameDefines (all tunable coefficients)
```

### Existing Patterns to Follow

- **Protocol + Default impl**: Every calculator uses a Protocol for DI +
  `DefaultXxxCalculator` concrete class. See `melt/melt_calculator.py`.
- **Frozen Pydantic models**: `model_config = ConfigDict(frozen=True)` on all types.
- **NoDataSentinel**: Return `NoDataSentinel(fips=, year=, reason=)` when data
  is unavailable. Never raise on missing data — propagate sentinels.
- **Three-tier validation**: Expected/Warning/Fail ranges. See
  `dynamics/validation.py` and `gamma/validation.py`.
- **Package exports**: `__all__` list in every module, grouped imports in
  `__init__.py`.
- **Test patterns**: Frozen dataclass test constants in `tests/constants.py`,
  mock data sources in `conftest.py`, TDD red-green-refactor.
- **Commit convention**: `feat(economics): add ReserveArmyState model` etc.

---

## Feature 1: Reserve Army of Labor

### Why This Is Critical

The reserve army is Marx's mechanism for how unemployment disciplines wages.
Without it, variable capital (v) in the tensor has no endogenous downward
pressure. The existing `EconomicConditions.unemployment_rate` is a flat
input — it doesn't decompose unemployment into its structural forms or
compute wage pressure from it.

For Detroit: Wayne County's U-6 hit ~25% in 2009-2010. This didn't just mean
people were jobless — it meant *employed* workers accepted wage cuts, lost
bargaining power, and watched benefits erode. The reserve army is the
transmission mechanism between unemployment and proletarianization.

### What to Build

#### 1.1 New Package: `src/babylon/economics/reserve_army/`

```
src/babylon/economics/reserve_army/
    __init__.py
    types.py              # ReserveArmyState, ReserveArmyDynamics
    data_sources.py       # UnemploymentDataSource protocol
    calculator.py         # ReserveArmyCalculator protocol + Default impl
    wage_pressure.py      # WagePressureCalculator protocol + Default impl
    hardcoded_data.py     # HardcodedUnemploymentSource (MVP, national data)
    validation.py         # Three-tier validation for reserve army metrics
```

#### 1.2 Type Definitions (`types.py`)

**ReserveArmyState** — frozen Pydantic model:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `fips` | `str` | input | County FIPS code |
| `year` | `int` | input | Calendar year |
| `floating_reserve` | `float` | BLS U-3 | Actively unemployed, between jobs. Rate [0,1]. |
| `latent_reserve` | `float` | U-6 minus U-3 | Underemployed, discouraged, marginally attached. Rate [0,1]. |
| `stagnant_reserve` | `float` | PTER + gig | Chronic irregular employment. Rate [0,1]. |
| `labor_force_participation` | `float` | BLS LAUS | LFP rate [0,1] — captures discouraged workers who left entirely |
| `total_reserve_ratio` | `float` | computed | Sum of three reserves / labor force. Key disciplinary metric. |
| `wage_pressure` | `float` | computed | Downward pressure on wages [0,1]. 0=no pressure, 1=maximum. |

**Computed fields**:
- `total_reserve_ratio`: floating + latent + stagnant
- `wage_pressure`: calibrated function of total_reserve_ratio. Higher ratio =
  more pressure. Use an empirically-grounded curve — not linear. The Phillips
  curve literature suggests a convex relationship: pressure increases
  acceleratingly as reserve ratio grows. A reasonable functional form:
  `wage_pressure = 1 - exp(-k * total_reserve_ratio)` where k ~ 3.0-5.0
  (calibrate against Detroit data where U-6 ~25% clearly suppressed wages).

**ReserveArmyDynamics** — frozen Pydantic model for flow tracking:

| Field | Type | Description |
|-------|------|-------------|
| `fips` | `str` | County FIPS |
| `year` | `int` | Calendar year |
| `mechanization_displacement` | `float` | Rate of workers displaced by automation |
| `firm_failure_displacement` | `float` | Rate from bankruptcies |
| `expansion_absorption` | `float` | Rate hired during expansion |
| `net_flow` | `float` | computed: displacement - absorption |

#### 1.3 Data Sources (`data_sources.py`)

Protocol `UnemploymentDataSource`:
- `get_u3_rate(fips, year) -> float | None`
- `get_u6_rate(fips, year) -> float | None`
- `get_lfp_rate(fips, year) -> float | None`
- `get_pter_rate(fips, year) -> float | None` (part-time for economic reasons)

#### 1.4 Calculator (`calculator.py`)

Protocol `ReserveArmyCalculator`:
- `compute(fips, year) -> ReserveArmyState | NoDataSentinel`

`DefaultReserveArmyCalculator`:
- Takes `UnemploymentDataSource` via DI
- Decomposes U-3, U-6, PTER into floating/latent/stagnant
- Computes wage_pressure from total_reserve_ratio
- Returns NoDataSentinel if U-3 unavailable (U-6 and PTER degrade gracefully)

#### 1.5 Wage Pressure Integration (`wage_pressure.py`)

Protocol `WagePressureCalculator`:
- `compute_wage_adjustment(reserve_state: ReserveArmyState, base_wage: float) -> float`

This is the critical integration point. The wage adjustment feeds into:
- `EconomicConditions.median_wage` (suppressed by wage_pressure)
- `AccumulationCalculator` inputs (lower wages = slower accumulation)
- `ClassTransitionEngine` dynamics (higher precaritization when wages fall)

#### 1.6 MVP Data (`hardcoded_data.py`)

Hardcode national-level BLS data for 2007-2020, following the exact pattern
in `dynamics/hardcoded_data.py`. Key data points for calibration:

| Year | U-3 | U-6 | LFPR |
|------|-----|-----|------|
| 2007 | 4.6% | 8.3% | 66.0% |
| 2008 | 5.8% | 10.5% | 66.0% |
| 2009 | 9.3% | 16.2% | 65.4% |
| 2010 | 9.6% | 16.7% | 64.7% |
| 2011 | 8.9% | 15.9% | 64.1% |
| 2012 | 8.1% | 14.7% | 63.7% |
| 2013 | 7.4% | 13.8% | 63.2% |
| 2014 | 6.2% | 12.0% | 62.9% |
| 2015 | 5.3% | 10.4% | 62.7% |
| 2016 | 4.9% | 9.7% | 62.8% |
| 2017 | 4.4% | 8.5% | 62.9% |
| 2018 | 3.9% | 7.4% | 62.9% |
| 2019 | 3.7% | 7.0% | 63.1% |
| 2020 | 8.1% | 14.2% | 61.7% |

Source: BLS Current Population Survey (CPS) annual averages.
Verify these against actual BLS data before hardcoding.

#### 1.7 Integration with Existing Code

Modify `EconomicConditions` in `dynamics/types.py` to accept an optional
`reserve_army_state: ReserveArmyState | None` field. When present, the
transition engine should use `wage_pressure` to adjust accumulation rates
downward. This is a backward-compatible addition.

#### 1.8 Tests

- Test the decomposition: U-3=5%, U-6=10% -> floating=0.05, latent=0.05
- Test wage_pressure curve: reserve_ratio=0.0 -> pressure=0.0,
  reserve_ratio=0.25 -> pressure high (~0.5-0.7)
- Test NoDataSentinel propagation when U-3 missing
- Test integration: high reserve_ratio suppresses accumulation rate
- Test Detroit calibration: 2010 conditions produce expected wage suppression

---

## Feature 2: Dispossession Event Ledger

### Why This Is Critical

The existing `DispossessionRisk` model computes *rates* but doesn't track
*events*. A rate tells you the probability of foreclosure; an event tells you
that 15,000 homes in Wayne County were foreclosed in 2010, transferring $2.1B
in housing equity. The event ledger is needed for:

1. Aggregate value transfer accounting (Wayne -> Oakland)
2. Class decomposition triggers (foreclosure -> LA -> Proletariat transition)
3. Historical narrative (which neighborhoods, which years, what scale)

### What to Build

#### 2.1 Extend `src/babylon/economics/dynamics/`

Add to the existing package rather than creating a new one:

```
src/babylon/economics/dynamics/
    ... (existing files)
    dispossession_types.py    # DispossessionType enum, DispossessionEvent, TerritoryDispossessionState
    dispossession_ledger.py   # DispossessionLedger (event store + aggregation)
```

#### 2.2 Type Definitions (`dispossession_types.py`)

**DispossessionType** — StrEnum:

```
FORECLOSURE          # Bank seizure of mortgaged property
EVICTION             # Removal of tenant
TAX_SALE             # Seizure for unpaid property taxes
EMINENT_DOMAIN       # State seizure for "public use"
WAGE_THEFT           # Unpaid wages, misclassification
INCARCERATION        # Asset forfeiture, job loss from carceral system
PENSION_DEFAULT      # Corporate bankruptcy eliminating earned pension
DISPLACEMENT         # Forced relocation due to unaffordable rent increases
```

**DispossessionEvent** — frozen Pydantic model:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` | Unique identifier (UUID or `{fips}_{year}_{type}_{seq}`) |
| `tick` | `int` | Simulation tick |
| `fips` | `str` | Territory where dispossession occurs |
| `year` | `int` | Calendar year |
| `dispossession_type` | `DispossessionType` | Mechanism |
| `affected_population` | `int` | Number of households affected |
| `value_transferred` | `float` | Dollar value of transferred assets |
| `dispossessed_class` | `str` | ClassPosition name of victims |
| `appropriator_class` | `str | None` | ClassPosition name of beneficiary (None if systemic) |
| `target_fips` | `str | None` | Destination territory for value (None if dissipated) |

**TerritoryDispossessionState** — frozen Pydantic model:

| Field | Type | Description |
|-------|------|-------------|
| `fips` | `str` | County FIPS |
| `year` | `int` | Calendar year |
| `foreclosure_count` | `int` | Number of foreclosure events |
| `eviction_count` | `int` | Number of eviction events |
| `tax_sale_count` | `int` | Number of tax sale events |
| `total_value_extracted` | `float` | Total dollar value dispossessed |
| `total_value_received` | `float` | Total dollar value received (from other territories) |
| `net_dispossession` | `float` | computed: extracted - received |
| `dispossession_intensity` | `float` | computed: weighted composite rate |

**Computed fields**:
- `net_dispossession = total_value_extracted - total_value_received`
- `dispossession_intensity`: Use the existing weight pattern from
  `dispossession.py` but on counts rather than rates. This creates a
  territory-level severity score.

#### 2.3 Dispossession Ledger (`dispossession_ledger.py`)

`DispossessionLedger` class (not frozen — it accumulates events):

- `record(event: DispossessionEvent) -> None` — append to internal list
- `get_events(fips: str | None, year: int | None, type: DispossessionType | None) -> list[DispossessionEvent]` — filtered query
- `aggregate_territory(fips: str, year: int) -> TerritoryDispossessionState` — compute territory summary
- `compute_value_transfer(source_fips: str, target_fips: str, year: int) -> float` — net value flow between territories
- `total_events() -> int` — count

The ledger should be injectable via DI (protocol + default impl pattern).
The simulation engine creates one ledger per run and passes it to systems
that generate dispossession events.

#### 2.4 Event Generation Integration

The following existing systems should generate `DispossessionEvent`s:

1. **DecompositionSystem** (`decomposition.py`): When LA decomposes, record
   a DISPLACEMENT event with the wealth delta.

2. **TerritorySystem** (`territory.py`): When eviction pipeline fires,
   record an EVICTION event.

3. **StruggleSystem** (`struggle.py`): When wealth destruction occurs during
   uprising, record the value transfer.

4. **ClassTransitionEngine** (`transition_engine.py`): When dispossession
   rate fires and LA->Proletariat transition occurs, record a FORECLOSURE or
   DISPLACEMENT event proportional to the population moved.

Don't modify these systems yet — just design the integration points. The
ledger should be available via `ServiceContainer` so systems can access it
when ready.

#### 2.5 Detroit-Specific MVP Data

For the MVP, generate synthetic events from the existing hardcoded rates.
The hardcoded data gives us national foreclosure/eviction rates by year.
For Wayne County (FIPS 26163) and Oakland County (FIPS 26125):

- Wayne County foreclosure rate was ~2-3x national average in 2008-2012
- Oakland County rate was ~0.7x national average
- Median home value Wayne ~$80K (2010), Oakland ~$200K (2010)

This allows computing approximate event counts and value transfers:
```
wayne_foreclosure_events = wayne_households * foreclosure_rate * wayne_multiplier
value_per_event = median_home_value * equity_fraction
total_value_extracted = events * value_per_event
```

#### 2.6 Tests

- Test event recording and retrieval by fips/year/type filters
- Test territory aggregation produces correct counts and sums
- Test value transfer computation between two territories
- Test that NoDataSentinel propagates when underlying rates missing
- Test Detroit scenario: Wayne County 2010 produces high dispossession intensity
- Test that total value extracted across all territories sums correctly

---

## Feature 3: Housing Value Decomposition

### Why This Is Critical

Housing is the primary wealth store for most American households and the
primary mechanism of spatial value transfer in the Detroit case study. The
2008 crisis destroyed ~$7 trillion in housing equity nationally. In Wayne
County, home values fell 40-60%. In Oakland County, they fell 20-30% then
recovered faster. This differential is the material basis for
gentrification-as-primitive-accumulation.

Marx's framework (Volume III, Chapter 46) decomposes housing price into:
1. **Construction value** — labor-value of the physical structure (c + v + s)
2. **Capitalized ground rent** — location monopoly capitalized at the going interest rate
3. **Speculative premium** — excess market price over fundamental value

The speculative premium is fictitious capital attached to housing. When it
collapses, the "wealth" evaporates — but the *real* value (construction +
location) transfers to whoever buys at the bottom. This is precisely what
happened in Detroit: institutional investors bought foreclosed homes at
pennies on the dollar, capturing the real value while the fictitious premium
had already been destroyed.

### What to Build

#### 3.1 New Package: `src/babylon/economics/housing/`

```
src/babylon/economics/housing/
    __init__.py
    types.py               # HousingValueDecomposition, TerritoryHousingState
    data_sources.py        # HousingDataSource protocol
    decomposition.py       # HousingDecompositionCalculator protocol + Default impl
    hardcoded_data.py      # HardcodedHousingSource (MVP, Wayne/Oakland data)
    validation.py          # Three-tier validation
```

#### 3.2 Type Definitions (`types.py`)

**HousingValueDecomposition** — frozen Pydantic model:

| Field | Type | Description |
|-------|------|-------------|
| `fips` | `str` | County FIPS |
| `year` | `int` | Calendar year |
| `median_home_value` | `float` | Market price ($) |
| `construction_value` | `float` | Replacement cost of structure ($) |
| `ground_rent_capitalized` | `float` | Location rent / interest rate ($) |
| `speculative_premium` | `float` | computed: market - construction - ground_rent |
| `fictitious_fraction` | `float` | computed: (ground_rent + speculative) / market |
| `owner_occupied_rate` | `float` | Fraction of units owner-occupied [0,1] |
| `median_rent` | `float` | Monthly rent ($) for renter-occupied |
| `rent_burden` | `float` | Median rent / median income [0,1] |
| `institutional_ownership_rate` | `float` | Fraction owned by institutional investors [0,1] |

**Computed fields**:
- `speculative_premium = median_home_value - construction_value - ground_rent_capitalized`
  (clamped to 0 minimum — negative means market is below fundamental value,
  which happens in distressed markets like Detroit 2010-2013)
- `fictitious_fraction = (ground_rent_capitalized + max(0, speculative_premium)) / median_home_value`

**TerritoryHousingState** — frozen Pydantic model for aggregate housing dynamics:

| Field | Type | Description |
|-------|------|-------------|
| `fips` | `str` | County FIPS |
| `year` | `int` | Calendar year |
| `total_units` | `int` | Total housing units |
| `vacancy_rate` | `float` | Fraction vacant [0,1] |
| `total_housing_value` | `float` | Aggregate housing wealth ($) |
| `total_construction_value` | `float` | Aggregate construction value ($) |
| `total_speculative_premium` | `float` | Aggregate fictitious component ($) |
| `yoy_price_change` | `float` | Year-over-year price change rate |
| `bubble_indicator` | `str` | computed: NORMAL, INFLATING, BUBBLE, DEFLATING, DISTRESSED |

**Computed `bubble_indicator`**: Based on `fictitious_fraction` and `yoy_price_change`:
- `fictitious_fraction > 0.5 AND yoy_change > 0.05` -> BUBBLE
- `fictitious_fraction > 0.4 AND yoy_change > 0` -> INFLATING
- `yoy_change < -0.05` -> DEFLATING
- `speculative_premium < 0` -> DISTRESSED (market below fundamental)
- else -> NORMAL

#### 3.3 Data Sources (`data_sources.py`)

Protocol `HousingDataSource`:
- `get_median_home_value(fips, year) -> float | None`
- `get_construction_cost_index(fips, year) -> float | None`
- `get_median_rent(fips, year) -> float | None`
- `get_vacancy_rate(fips, year) -> float | None`
- `get_owner_occupied_rate(fips, year) -> float | None`
- `get_median_household_income(fips, year) -> float | None`
- `get_total_housing_units(fips, year) -> int | None`

#### 3.4 Decomposition Calculator (`decomposition.py`)

Protocol `HousingDecompositionCalculator`:
- `compute(fips, year) -> HousingValueDecomposition | NoDataSentinel`
- `compute_territory_state(fips, year) -> TerritoryHousingState | NoDataSentinel`

`DefaultHousingDecompositionCalculator`:
- Takes `HousingDataSource` and an interest rate parameter via DI
- Construction value = per-sq-ft construction cost * median sq footage.
  In the MVP, approximate as: `construction_cost_index * BASELINE_SQ_FT * COST_PER_SQFT`.
  BLS/Census RSMeans data gives regional construction costs.
- Ground rent = annual rent equivalent / interest rate (capitalization formula).
  Annual rent equivalent = `median_rent * 12 * rent_to_land_ratio` where
  `rent_to_land_ratio` is the fraction of rent attributable to location
  (typically 0.3-0.5 for urban areas, higher in desirable locations).
- Speculative premium = market price - construction - ground rent (residual)
- Returns NoDataSentinel if median_home_value unavailable

#### 3.5 MVP Data (`hardcoded_data.py`)

Hardcode Wayne County (26163) and Oakland County (26125) housing data
for 2007-2020. Key data points to verify against Census ACS:

**Wayne County (26163)**:

| Year | Median Home | Median Rent | Vacancy | Owner-Occ |
|------|-------------|-------------|---------|-----------|
| 2007 | $130,000 | $750 | 12% | 68% |
| 2008 | $105,000 | $740 | 14% | 66% |
| 2009 | $80,000 | $720 | 16% | 64% |
| 2010 | $68,000 | $710 | 18% | 62% |
| 2011 | $55,000 | $700 | 20% | 60% |
| 2012 | $52,000 | $710 | 19% | 59% |
| 2013 | $58,000 | $720 | 18% | 58% |
| 2014 | $65,000 | $740 | 16% | 58% |
| 2015 | $72,000 | $760 | 15% | 57% |
| 2016 | $80,000 | $790 | 14% | 57% |
| 2017 | $90,000 | $820 | 13% | 57% |
| 2018 | $100,000 | $860 | 12% | 57% |
| 2019 | $110,000 | $900 | 11% | 57% |
| 2020 | $120,000 | $930 | 10% | 57% |

**Oakland County (26125)**:

| Year | Median Home | Median Rent | Vacancy | Owner-Occ |
|------|-------------|-------------|---------|-----------|
| 2007 | $220,000 | $900 | 7% | 76% |
| 2008 | $190,000 | $890 | 8% | 75% |
| 2009 | $160,000 | $870 | 9% | 74% |
| 2010 | $155,000 | $860 | 9% | 73% |
| 2011 | $150,000 | $860 | 9% | 73% |
| 2012 | $155,000 | $870 | 8% | 73% |
| 2013 | $170,000 | $890 | 8% | 73% |
| 2014 | $185,000 | $910 | 7% | 73% |
| 2015 | $195,000 | $940 | 6% | 74% |
| 2016 | $210,000 | $970 | 6% | 74% |
| 2017 | $225,000 | $1000 | 5% | 74% |
| 2018 | $240,000 | $1040 | 5% | 74% |
| 2019 | $250,000 | $1070 | 5% | 74% |
| 2020 | $260,000 | $1100 | 5% | 74% |

**IMPORTANT**: These numbers are approximate from Census ACS. Verify every
value against actual Census data before committing. If actual data isn't
immediately available, mark fields with comments citing the approximation
method and add a TODO for data verification.

#### 3.6 Integration with Dispossession Ledger

The housing decomposition feeds the dispossession ledger:
- When a foreclosure event occurs, `value_transferred` should equal
  the home's `construction_value + ground_rent_capitalized` (the real value),
  not the `median_home_value` (which includes the now-destroyed speculative premium).
- The `speculative_premium` component is *destroyed*, not transferred — it
  was fictitious capital that ceased to exist.
- The `institutional_ownership_rate` tracks post-crisis capital consolidation.

#### 3.7 Integration with Reserve Army

Housing costs are a major component of V_reproduction (cost of reproducing
labor power). When `rent_burden > 0.30`, workers are "cost-burdened" by
federal definition. When `rent_burden > 0.50`, they're "severely burdened."
High rent burden + wage pressure from reserve army = compounding
precaritization pressure:

```
effective_precaritization = base_rate * (1 + rent_burden_multiplier) * (1 + wage_pressure)
```

This creates a feedback loop: unemployment -> wage suppression -> can't pay
rent -> eviction -> dispossession -> lumpenproletariat.

#### 3.8 Tests

- Test decomposition: known inputs produce correct construction/ground_rent/speculative split
- Test speculative_premium clamped to 0 in distressed markets (Detroit 2011)
- Test fictitious_fraction computation
- Test bubble_indicator classification for each phase
- Test rent_burden computation
- Test Wayne vs Oakland differential: Wayne has higher fictitious_fraction
  volatility, Oakland has higher absolute values but more stability
- Test integration with dispossession: foreclosure value = real value, not market value

---

## Implementation Order

1. **Reserve Army** (Feature 1) — pure data model + calculator, no system dependencies
2. **Dispossession Event Ledger** (Feature 2) — extends existing dynamics module
3. **Housing Value Decomposition** (Feature 3) — uses Reserve Army for wage_pressure,
   feeds Dispossession Ledger with value_transferred

Each feature: write types first, then data sources, then calculator, then
hardcoded MVP data, then tests, then integration points.

**Commit after each feature passes all tests.**

## Verification Criteria

After all three features:

1. `mise run test:unit` — all pass
2. `mise run lint` — clean
3. `mise run typecheck` — clean (MyPy strict on new modules)
4. Reserve Army: `DefaultReserveArmyCalculator.compute("26163", 2010)` returns
   `ReserveArmyState` with `total_reserve_ratio > 0.20` and `wage_pressure > 0.4`
5. Dispossession Ledger: Recording 100 events and querying by fips/year/type
   returns correct filtered subsets
6. Housing Decomposition: Wayne County 2011 shows `speculative_premium <= 0`
   (distressed market), Oakland County 2011 shows `speculative_premium > 0`
7. Integration: Wayne -> Oakland `compute_value_transfer` returns positive
   value for 2008-2013 (net flow from Wayne to Oakland)

## What NOT to Build

- No database loaders — hardcoded data only for now (MVP behind protocols)
- No UI integration — these are economics layer models only
- No modification to existing engine systems yet — design integration points
  but don't wire them until the models are validated
- No Volume II temporal dynamics (turnover, circuits) — out of scope
- No Volume III financial layer (fictitious capital stock, credit system) — out of scope
  except for the housing-specific fictitious fraction which is a narrow slice
