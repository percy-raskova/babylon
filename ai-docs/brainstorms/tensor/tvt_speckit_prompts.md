# TVT Physics Engine: Spec-Kit Prompts

**Purpose**: Prompts for Claude Code + spec-kit to generate specifications for each implementation phase
**Usage**: Feed each prompt to spec-kit after completing the prior phase
**Context**: These prompts assume spec `011-fundamental-tensor-primitive` is implemented

---

## Phase 1: Capital Stock & Profit Rate

### Spec ID: `012-capital-stock-dynamics`

### Prompt:

```
Create a specification for Capital Stock Dynamics.

CONTEXT:
- The primitive ValueTensor4x3 (spec 011) provides c, v, s flows per fips/year
- We need to derive capital STOCK (K) from capital FLOWS (c) for profit rate calculation
- This is required for testing the Tendency of the Rate of Profit to Fall (TRPF)

THEORETICAL FOUNDATION (from project docs):
- TSSI historical cost valuation: capital stock = what was actually paid, not replacement cost
- Perpetual inventory method: K[t+1] = K[t] × (1 - δ) + c[t]
- Initialization assumption: K_0 = c_0 / δ (steady-state, error decays exponentially)
- Depreciation rate δ ≈ 0.07 (BEA average, single national rate initially)

REQUIRED DERIVED FIELDS:
- K[fips, year]: Capital stock (accumulated constant capital minus depreciation)
- r[fips, year]: Profit rate = Σ_μ s^μ / (K + Σ_μ v^μ)
- OCC[fips, year]: Organic composition = Σ_μ c^μ / Σ_μ v^μ
- e[fips, year]: Exploitation rate = Σ_μ s^μ / Σ_μ v^μ

CONSTRAINTS:
- K must be computed from the primitive tensor, not database queries
- K[fips, 2010] initialization uses steady-state assumption
- Derived rates (r, OCC, e) are dimensionless ratios
- Must handle missing years gracefully (interpolation or skip)

VALIDATION CRITERIA:
- r should show secular decline over 2010-2024 (TRPF prediction)
- OCC should correlate positively with τ (core position proxy)
- Sensitivity test: vary δ from 0.05-0.10, check if TRPF trend is robust

DEPENDENCIES:
- Requires: 011-fundamental-tensor-primitive
- Data: Primitive tensor loaded with QCEW/BEA data

Reference existing code in src/babylon/economics/ for patterns. The tensor.py and hydrator.py show current architecture.
```

---

## Phase 2: MELT Calculation

### Spec ID: `013-melt-computation`

### Prompt:

```
Create a specification for MELT (Monetary Expression of Labor Time) Computation.

CONTEXT:
- MELT (τ) bridges labor-time and money-price: Price = τ × Value
- Required for international visibility coefficient (γ) calculation
- Required for converting tensor wage-proxies to true labor-hours

THEORETICAL FOUNDATION (from project docs):
- τ[fips, year] = GDP[fips, year] / L[fips, year]
- L (total labor hours) approximated as: employment × 2080 hours/year
- The 2080 assumption cancels in τ ratios, making γ = τ_a / τ_b exact
- τ varies by location and time (not a single national constant)

REQUIRED OUTPUTS:
- τ[fips, year]: MELT per county per year (dollars per labor-hour)
- τ_ratio[fips_a, fips_b, year]: Ratio of MELTs (foundation for γ)

DATA REQUIREMENTS:
- BEA GDP by county (verify loader exists, check data/duckdb schema)
- QCEW employment by county (already loaded)
- Computation: τ = GDP / (employment × 2080)

CONSTRAINTS:
- Must use BEA GDP data, not QCEW wages (GDP is output measure)
- Handle missing GDP gracefully (some counties may lack BEA data)
- τ must be positive (GDP and employment both positive)

VALIDATION CRITERIA:
- τ[Oakland] > τ[Wayne] for most years (core has higher GDP/worker)
- National τ should approximate $50-80/hour range (sanity check)
- τ ratios should correlate with wage ratios (consistency check)

DEPENDENCIES:
- Requires: 011-fundamental-tensor-primitive
- Data: BEA GDP by county (verify this is loaded in DuckDB)

Check existing BEA loaders in src/babylon/data/bea/ and verify GDP data availability in the schema.
```

---

## Phase 3: Domestic Indicators

### Spec ID: `014-domestic-core-periphery-indicators`

### Prompt:

```
Create a specification for Domestic Core/Periphery Indicators.

CONTEXT:
- Within the US (single currency zone), everyone spends dollars
- Imperial rent is in the CURRENCY, not distributed by domestic class
- Therefore domestic core/periphery requires DIFFERENT indicators than international γ
- We need five indicators that together identify domestic value geography

THEORETICAL FOUNDATION (from TVT docs and Capital Volume I):
1. τ ratio (GDP per worker) - where value surfaces
2. Net commuter flow - where labor lives vs works
3. Ownership ratio - where capital income lands
4. Mean hours worked - class composition signal (LA hoards hours, proletariat rationed)
5. Reserve army pressure - labor discipline mechanism (from Vol I, Ch 25)

The reserve army is CRITICAL: it explains WHY hours get rationed for the proletariat. Capital can cut hours because there's always someone desperate enough to take what's offered. Marx identifies three forms:
- Floating: Regularly expelled/absorbed by industry cycles
- Latent: Underemployed, want more hours but can't get them
- Stagnant: Gig workers, precarious, irregular employment

INDICATOR DEFINITIONS:

**NetFlow[fips, year]**:
- Inflow = workers who live elsewhere but work in fips
- Outflow = workers who live in fips but work elsewhere
- NetFlow = Inflow - Outflow
- Source: LODES Origin-Destination data
- Core: NetFlow > 0 (imports labor)
- Periphery: NetFlow < 0 (exports labor)

**OwnershipRatio[fips, year]**:
- Y_capital = interest + dividends + rental income
- Y_labor = wages + salaries
- OwnershipRatio = Y_capital / Y_labor
- Source: ACS income by source tables
- High ratio = owner-residence county (surplus lands here)

**MeanHours[fips, year]**:
- Mean usual hours worked per employed person
- Source: ACS table B23020 or similar
- Higher hours = labor aristocracy composition
- Lower hours = precarious proletariat (hours rationed)

**ReserveArmyPressure[fips, year]**:
- Composite of unemployment metrics that discipline labor
- Components:
  - U6_rate: Broad unemployment (includes marginally attached, PTER)
  - PTER_rate: Part-Time for Economic Reasons ("my hours got cut")
  - Discouraged_rate: Want work but stopped looking
- Source: BLS Local Area Unemployment Statistics (LAUS), ACS employment status
- Higher pressure = more labor discipline = periphery characteristic
- Lower pressure = tighter labor market = core characteristic
- Formula: ReserveArmyPressure = w1*U6 + w2*PTER + w3*Discouraged (weights TBD)

**CoreIndex[fips, year]** (composite):
- Normalized weighted sum of above indicators
- Note: ReserveArmyPressure is INVERTED (high pressure = low core score)
- Weights initially equal (0.20 each), calibrate empirically
- Range [0, 1]: 0 = periphery, 1 = core

DATA REQUIREMENTS:
- LODES OD files (currently have crosswalk, need main OD files)
- ACS income by source (verify tables loaded)
- ACS hours worked (verify tables loaded)
- BLS LAUS data (new loader needed for county-level unemployment)
- ACS employment status tables (for PTER, discouraged workers)

VALIDATION CRITERIA (Wayne County = 26163, Oakland County = 26125):
- NetFlow[Oakland] > 0, NetFlow[Wayne] < 0
- OwnershipRatio[Oakland] > OwnershipRatio[Wayne]
- MeanHours[Oakland] > MeanHours[Wayne]
- ReserveArmyPressure[Oakland] < ReserveArmyPressure[Wayne]
- All five indicators should correlate in expected directions (coherence test)

THEORETICAL VALIDATION:
- During 2008-2012 crisis, Wayne County's ReserveArmyPressure should spike
- This spike should correlate with subsequent wage suppression (declining v)
- Oakland's ReserveArmyPressure should remain lower throughout

DEPENDENCIES:
- Requires: 013-melt-computation (for τ component)
- Data: LODES OD, ACS income, ACS hours, BLS LAUS

Check existing Census/ACS loaders in src/babylon/data/census/ and LODES crosswalk in data/lodes/. Reference capital_volume_i_integration.md for ReserveArmyState model. Determine what additional data loads are needed.
```

---

## Phase 4: Gamma Tensor

### Spec ID: `015-gamma-visibility-tensor`

### Prompt:

```
Create a specification for the Gamma (Visibility) Tensor.

CONTEXT:
- γ measures fraction of labor-time that survives transformation to price-space
- γ = 1: fully visible; γ = 0: fully invisible (shadow labor)
- γ is INTENSIVE (weighted-averages under aggregation), unlike T which is EXTENSIVE (sums)
- Two distinct mechanisms: international (PPP) and domestic (naturalization)

THEORETICAL FOUNDATION (from gamma_tensor_theory.md and TVT docs):

**Department III (Reproductive Labor)**:
- γ_III = paid_hours / (paid_hours + unpaid_hours)
- paid_hours: QCEW care sector employment
- unpaid_hours: ATUS unpaid household/care labor
- This measures commodification of reproductive work
- Spec 005 (ATUS) provides foundation, integrate it here

**International (Departments I, IIa, IIb)**:
- γ[a→b] = τ[a] / τ[b] for cross-currency-zone flows
- For periphery→core: γ < 1 (value compressed)
- Requires trade data for weighting (out of scope initially)
- Approximation: γ_country from Penn World Tables PPP ratios

TENSOR STRUCTURE:
- γ_μ[fips, year] where μ ∈ {I, IIa, IIb, III}
- Range: [0, 1] for all components
- Transformation: weighted-average under geographic aggregation (NOT sum)

DERIVED QUANTITIES:
- T_price^μ_ν = γ_μ × T^μ_ν (price-visible value)
- S^μ_ν = (1 - γ_μ) × T^μ_ν (shadow value)
- Φ_shadow = Σ_μ (1 - γ_μ) × T^μ_total (total shadow subsidy)

CONSTRAINTS:
- γ is separate from T (different aggregation rules)
- γ_III computed from ATUS + QCEW
- γ for Depts I/II initially set to 1.0 domestically (placeholder until trade data)
- Composition: γ[a→c via b] = γ[a→b] × γ[b→c] (multiplicative along chains)

VALIDATION CRITERIA:
- γ_III < 1 (reproductive labor partially invisible)
- γ_III varies by county demographics (higher FLFP → higher γ_III)
- Shadow subsidy Φ should correlate with profitability

DEPENDENCIES:
- Requires: 011-fundamental-tensor-primitive, 013-melt-computation
- Requires: 005-atus-department-iii (already exists, integrate)
- Data: ATUS time use, QCEW care sectors

Reference existing visibility_g33 field in ValueTensor4x3 and shadow_labor module in src/babylon/economics/.
```

---

## Phase 5: Temporal Dynamics

### Spec ID: `016-simulation-tick-dynamics`

### Prompt:
```
Create a specification for Simulation Tick Dynamics.

CONTEXT:
- The simulation advances in discrete time steps (ticks = years)
- State at t+1 depends on state at t plus new inputs
- This is the core "physics engine" that makes the simulation run
- Must implement TSSI temporal determination

THEORETICAL FOUNDATION (from TSSI and TVT docs):

**TSSI Temporal Principle**:
- V[t+1] = P_inputs[t] + L[t→t+1]
- Output value depends on input PRICES (historical cost) plus living labor
- Input prices at t become embedded in output values at t+1

**State Vector per Node**:
- T^μ_ν[fips, t]: Value tensor (from primitive)
- K[fips, t]: Capital stock (from Phase 1)
- γ_μ[fips, t]: Visibility tensor (from Phase 4)
- Domestic indicators: NetFlow, OwnershipRatio, MeanHours (from Phase 3)

**Update Rules**:
- T^μ_ν[fips, t+1] = hydrate(QCEW[fips, t+1], BEA_ratios[t+1])
- K[fips, t+1] = K[fips, t] × (1 - δ) + Σ_μ c^μ[fips, t+1]
- γ evolves slowly (α-smoothing): γ[t+1] = α × γ_new + (1-α) × γ[t]
- Derived fields (r, OCC, e) recomputed each tick

**Coefficient vs Quantity Distinction**:
- Quantities (T, K, flows) change each tick
- Coefficients (γ, δ, ratios) change slowly via α-smoothing
- α derived from empirical autocorrelation of the coefficient

REQUIRED FUNCTIONALITY:
- SimulationState: Container for all state at time t
- tick(state_t) → state_t+1: Advance simulation one period
- Lazy evaluation: Don't recompute unchanged values
- History tracking: Store state snapshots for analysis

CONSTRAINTS:
- All data flows through tensor layer (no direct DB queries during tick)
- Deterministic: same inputs → same outputs
- Must handle missing data years gracefully

VALIDATION CRITERIA:
- Running 2010-2024 should reproduce historical trajectories
- Profit rate r[t] series should show TRPF tendency
- K[t] series should show accumulation with crisis-year dips

DEPENDENCIES:
- Requires: All prior phases (011, 012, 013, 014, 015)
- Data: Full 2010-2024 time series loaded

Reference existing simulation architecture in src/babylon/simulation/ and engine patterns.
```

---

## Phase 6: Crisis Mechanics

### Spec ID: `017-crisis-devaluation`

### Prompt:

```
Create a specification for Crisis and Devaluation Mechanics.

CONTEXT:
- TRPF creates pressure toward crisis as profit rates decline
- Crisis = discontinuous reset where capital is devalued
- This restores profitability temporarily (destroys the K denominator)
- The simulation needs to model both gradual decline and sudden crisis

THEORETICAL FOUNDATION (from TSSI and TVT docs):

**Crisis Trigger**:
- When r[fips, t] < r_threshold for N consecutive periods
- r_threshold: minimum viable profit rate (calibrate empirically, ~2-3%?)
- N: persistence requirement (avoid triggering on noise, ~2-3 years?)

**Devaluation Mechanism**:
- During crisis: δ_effective = δ_crisis >> δ_normal
- δ_normal ≈ 0.07 (standard depreciation)
- δ_crisis ≈ 0.15-0.25 (accelerated capital destruction)
- K[t+1] = K[t] × (1 - δ_crisis) + c[t+1]

**Recovery Dynamics**:
- Post-crisis: return to δ_normal
- Profit rate rises because K denominator was destroyed
- Accumulation resumes, TRPF pressure rebuilds
- Cycle repeats

**Historical Validation Points**:
- 2008-2010: Financial crisis, should see K devaluation
- 2020: COVID shock, should see K devaluation
- Check if model reproduces observed profit rate dynamics

REQUIRED FUNCTIONALITY:
- CrisisDetector: Monitor r[t] series for threshold breach
- CrisisEvent: Trigger with parameters (start_t, severity, duration)
- DevaluationMode: Switch δ during crisis period
- RecoveryTransition: Gradual return to normal δ

PARAMETERS TO CALIBRATE:
- r_threshold: Minimum viable profit rate
- N: Consecutive periods below threshold to trigger
- δ_crisis: Crisis-period depreciation rate
- recovery_periods: How long elevated δ persists

CONSTRAINTS:
- Crisis is endogenous (triggered by model dynamics, not exogenous shock)
- But: allow exogenous shock injection for scenario testing
- Capital stock K must remain non-negative
- Crisis should be rare (not every year)

VALIDATION CRITERIA:
- Backtest: Model should flag crisis around 2008-2010
- Backtest: Model should flag crisis around 2020
- Post-crisis r should exceed pre-crisis r (profitability restored)
- Cycle: r should begin declining again after recovery

DEPENDENCIES:
- Requires: 016-simulation-tick-dynamics
- Requires: 012-capital-stock-dynamics
- Data: Full historical series for backtesting

This is the capstone of the physics engine. After this, we move to network topology and political dynamics.
```

---

## Phase 7: Primitive Accumulation & Dispossession

### Spec ID: `018-primitive-accumulation-dispossession`

### Prompt:

```
Create a specification for Primitive Accumulation and Dispossession Tracking.

CONTEXT:
- Capital Volume I, Part 8: Primitive accumulation is not just historical origin but ONGOING process
- Gentrification IS primitive accumulation operating post-frontier
- The 2008-2012 foreclosure wave was the largest peacetime dispossession event in US history
- Wayne County lost billions in accumulated housing equity → transferred to institutional investors → eventually Oakland County settlers
- This is the mechanism that PRODUCES the core/periphery geography we measure with other indicators

THEORETICAL FOUNDATION (from Capital Vol I and TVT docs):

**Primitive Accumulation Defined**:
Marx: "The so-called primitive accumulation is nothing else than the historical process of divorcing the producer from the means of production."

In contemporary terms:
- Foreclosure divorces homeowner from accumulated equity
- Eviction divorces tenant from place-based social capital
- Gentrification divorces community from neighborhood amenities they produced
- All transfer accumulated value from dispossessed to accumulators

**The Dispossession → Accumulation Pipeline**:
1. Crisis hits (2008 financial crisis, COVID, etc.)
2. Vulnerable populations cannot maintain payments
3. Foreclosure/eviction transfers property rights
4. Institutional capital buys distressed assets at discount
5. Property values recover → windfall to new owners
6. Original residents displaced, lose accumulated equity
7. New residents (settlers) capture amenities produced by displaced community

**Gentrification as Internal Colonization**:
- Same structure as frontier colonization but operating within metro areas
- Dispossession of existing residents
- Transfer of accumulated value (housing equity, community institutions)
- Settlement by population aligned with capital
- This is NOT just "neighborhood change" — it's primitive accumulation

REQUIRED MODELS:

**DispossessionEvent**:
- fips_code, year, event_type (FORECLOSURE, EVICTION, TAX_SALE, etc.)
- units_affected: Number of housing units
- estimated_equity_lost: Value transferred from dispossessed
- destination: Where did the property go? (INSTITUTIONAL_INVESTOR, INDIVIDUAL_BUYER, LAND_BANK, etc.)

**DispossessionRate[fips, year]**:
- foreclosure_rate: Foreclosures per 1000 housing units
- eviction_rate: Evictions per 1000 renter households
- tax_sale_rate: Tax foreclosures per 1000 parcels
- composite_dispossession: Weighted sum

**AccumulationFlow[origin_fips, dest_fips, year]**:
- Track where dispossessed value GOES
- Properties foreclosed in Wayne → purchased by Oakland residents/institutions
- This connects dispossession to the ownership patterns we measure

**GentrificationIndex[fips, year]**:
- Combines dispossession (push) with demographic change (pull)
- Components:
  - DispossessionRate (lagged) — displacement
  - Rent/price increase rate — price pressure
  - Demographic composition change — who's moving in
  - Income composition change — class character shift
- Distinguishes gentrification from other neighborhood change

DATA REQUIREMENTS:
- Foreclosure data: ATTOM, CoreLogic, or HUD (need to evaluate sources)
- Eviction data: Eviction Lab (Princeton) — county-level eviction rates
- Tax foreclosure data: County treasurer records (may need scraping for Detroit)
- Property transaction data: For tracking accumulation destination
- ACS demographic change: Already have loaders

VALIDATION CRITERIA (Detroit 2008-2015):
- Wayne County DispossessionRate should spike 2008-2012
- Spike should precede (by 2-3 years) demographic change indicators
- AccumulationFlow should show net transfer Wayne → Oakland
- Post-crisis, Oakland's property values should rise faster than Wayne's
- GentrificationIndex should identify known gentrifying neighborhoods

HISTORICAL VALIDATION:
- Model should reproduce known Detroit foreclosure crisis timeline
- Peak foreclosures ~2010-2011
- Institutional investor purchases accelerate 2012-2014
- Demographic shifts visible by 2015-2018

CONNECTION TO OTHER PHASES:
- Dispossession events are TRIGGERED by crisis (Phase 6)
- Dispossession PRODUCES the reserve army (Phase 3) — displaced people need work
- Dispossession CONCENTRATES ownership (increases OwnershipRatio differential)
- Dispossession is the MECHANISM of domestic core/periphery formation

CONSTRAINTS:
- DispossessionEvents are discrete (happen to specific properties)
- Rates are computed from event aggregation
- Must handle data gaps (not all counties have good foreclosure data)
- Privacy considerations for individual-level data

DEPENDENCIES:
- Requires: 017-crisis-devaluation (crisis triggers dispossession waves)
- Requires: 014-domestic-core-periphery-indicators (dispossession feeds into indicators)
- Data: Eviction Lab, ATTOM/CoreLogic, county records

Reference capital_volume_i_integration.md section on Primitive Accumulation. This phase bridges the economic physics engine to the political/geographic dynamics of settler colonialism.
```

---

## Phase 8: D-P-D' Lifecycle Circuit

### Spec ID: `019-dpd-prime-lifecycle-circuit`

### Prompt:

```
Create a specification for the D-P-D' Lifecycle Circuit.

CONTEXT:
- Labor-power doesn't just reproduce daily (C-M-C) — it reproduces across GENERATIONS
- The D-P-D' circuit (Dependent → Productive → Dependent') tracks humans through lifecycle phases
- This circuit serves three functions: ideological transmission, legitimation, and class reproduction via inheritance
- D-P-D' is the generational analogue of M-C-M' — but it spirals across generations rather than repeating

THEORETICAL FOUNDATION (from dpd_prime_lifecycle_circuit.md):

**The Three Phases**:
- D (Dependent, pre-productive): Ages 0-17 typically. Cannot sell labor-power. Receives care, socialization, education.
- P (Productive): Ages 18-64. Sells labor-power during this phase. C-M-C happens here.
- D' (Dependent', post-productive): Ages 65+ or disabled. Can no longer sell labor-power. Requires care.

**The Three Functions**:

1. **Ideological Reproduction (Superstructural)**:
   - D phase transmits religion, political orientation, class consciousness
   - Gramsci's hegemony is transmitted through D phase
   - Public schooling is pre-subsumption (shapes workers before they enter M-C-M')

2. **Legitimation (The Lifecycle Bargain)**:
   - Workers accept P-phase exploitation because they're promised D' security
   - Social Security, pensions, Medicare, family care = material basis of legitimation
   - When D' promise fails → legitimation crisis

3. **Class Reproduction (Inheritance)**:
   - At D' → death, accumulated value transfers to next generation
   - Bourgeoisie: substantial inheritance → reproduces as bourgeoisie
   - Proletariat: minimal inheritance (consumed by D' care) → reproduces as proletariat
   - Dispossession SEVERS this mechanism (foreclosure transfers wealth to capital, not heirs)

**The Eugenics Contradiction**:
- Capital wants faster turnover, but shortening D-P-D' by early death REDUCES total surplus extraction
- Capital wants standardized labor-power, but LP is frustratingly variable
- Eugenics attempts to control "quality" of LP output through D-phase interventions
- Public schooling disciplines D phase: sit still, follow instructions, accept hierarchy

**Circuit Nesting**:
```
D-P-D' (generational)
  └── P phase contains:
        └── C-M-C (daily reproduction)
              └── sells LP to M-C-M' (capital's circuit)
```

REQUIRED MODELS:

**DPDState[fips, year]**:
- Pop_D: Population in D phase (0-17)
- Pop_P: Population in P phase (18-64, able to work)
- Pop_D_prime: Population in D' phase (65+ or disabled)
- Transition rates: D→P, P→D', D'→death
- DependencyRatio = (Pop_D + Pop_D') / Pop_P

**InheritanceFlow[fips, year]**:
- By class: from_bourgeoisie, from_labor_aristocracy, from_proletariat, from_lumpen
- InheritanceGini: inequality of inheritance distribution
- Connection to dispossession: high DispossessionRate → severed inheritance → lower mobility

**LegitimationIndex[fips, year]**:
- Components: pension_coverage, SS_replacement_rate, healthcare_security, home_ownership, retirement_confidence
- Composite index measuring credibility of D' promise
- Low index → legitimation crisis risk → connects to bifurcation

DATA REQUIREMENTS:
- Census ACS: Population by age, disability status
- SSA: Disability rates, retirement rates
- Chetty Opportunity Atlas: Intergenerational mobility by county
- Fed SCF / IRS SOI: Inheritance data (limited, national)
- BLS NCS: Pension coverage rates
- Survey data: Retirement confidence (e.g., EBRI surveys)

VALIDATION CRITERIA:
- DependencyRatio should correlate with care sector employment
- InheritanceGini > IncomeGini (inheritance more unequal)
- corr(DispossessionRate, ChettyMobility) < 0 (dispossession breaks inheritance)
- corr(LegitimationIndex, political_instability) < 0 (low legitimation → instability)
- Counties with high D-phase investment (school spending) should show higher τ with ~20 year lag

TIMESCALE CHALLENGE:
- M-C-M' cycles in days/months
- C-M-C cycles daily
- D-P-D' cycles in ~80 years
- Solution: Model as population cohort dynamics, not individual lifecycles
- Track aggregate phase populations and transition rates

CONNECTION TO OTHER PHASES:
- Phase 7 (Dispossession): Dispossession severs inheritance mechanism
- Phase 3 (Domestic Indicators): DependencyRatio as additional indicator
- Phase 5 (Temporal Dynamics): Population transitions affect labor supply
- Future (Bifurcation): LegitimationIndex affects crisis outcome

CONSTRAINTS:
- D-P-D' operates at much slower timescale than tensor dynamics
- Individual-level inheritance data is sparse; use aggregate proxies
- Legitimation is partially subjective (requires survey data)

DEPENDENCIES:
- Requires: 014-domestic-core-periphery-indicators (phase populations integrate with indicators)
- Requires: 018-primitive-accumulation-dispossession (dispossession affects inheritance)
- Data: Census ACS (have), Chetty Opportunity Atlas (new), inheritance proxies

This phase extends the physics engine to capture intergenerational dynamics. After this, we have a complete multi-timescale model: daily (C-M-C), annual (tensor ticks), generational (D-P-D').
```

---

## Usage Notes

1. **Run in order**: Each phase depends on prior phases
2. **Validate between phases**: Run falsification tests before proceeding
3. **Reference project docs**: spec-kit should read TVT theory docs in project
4. **Check existing code**: Each prompt references relevant existing modules
5. **Iterate**: If spec-kit output is incomplete, refine prompt with specifics

## Validation Gates

| After Phase | Validation |
|-------------|------------|
| Phase 3 | Run domestic indicator tests on Wayne/Oakland (5 indicators) |
| Phase 5 | Run TRPF trajectory test (does r trend downward?) |
| Phase 6 | Backtest crisis detection against 2008-2010 and 2020 |
| Phase 7 | Validate dispossession timeline against known Detroit foreclosure crisis |

## Key Project Files for Reference

```
docs/
├── gamma_tensor_theory.md              # γ tensor formalization
├── tvt_mathematical_formalization.md   # Axioms and definitions
├── tvt_political_theoretical_exposition.md  # Theory overview
├── tvt_data_gaps_implementation.md     # Data sources and gaps
├── tensor_hierarchy.md                 # Tensor derivation hierarchy
├── capital_volume_i_integration.md     # Reserve army, primitive accumulation
├── capital_volume_ii_integration.md    # Reproduction schemas
└── capital_volume_iii_integration.md   # TRPF theory

src/babylon/economics/
├── tensor.py          # ValueTensor4x3, DepartmentRow
├── hydrator.py        # MarxianHydrator
├── reproduction.py    # Imperial rent calculation
└── shadow_labor.py    # Shadow labor visibility

specs/
├── 005-atus-department-iii/    # ATUS integration (exists)
└── 011-fundamental-tensor-primitive/  # Current spec
```

## Implementation Roadmap Summary

| Phase | Spec ID | Core Deliverable | Unlocks |
|-------|---------|------------------|---------|
| 1 | 012-capital-stock-dynamics | K, r, OCC, e | TRPF testing |
| 2 | 013-melt-computation | τ[fips, year] | International γ, labor-hour conversion |
| 3 | 014-domestic-core-periphery-indicators | NetFlow, OwnershipRatio, MeanHours, ReserveArmyPressure, CoreIndex | Domestic core/periphery classification |
| 4 | 015-gamma-visibility-tensor | γ_μ, T_price, Φ_shadow | Imperial rent quantification |
| 5 | 016-simulation-tick-dynamics | SimulationState, tick() | Actual simulation runs |
| 6 | 017-crisis-devaluation | CrisisDetector, DevaluationMode | Full cycle simulation |
| 7 | 018-primitive-accumulation-dispossession | DispossessionEvent, GentrificationIndex | Gentrification mechanics |
| 8 | 019-dpd-prime-lifecycle-circuit | DPDState, LegitimationIndex, InheritanceFlow | Intergenerational class reproduction |

After Phase 8, the physics engine is complete across all timescales:
- **Daily**: C-M-C (implicit in v)
- **Annual**: Tensor dynamics, profit rate, crisis
- **Generational**: D-P-D' lifecycle, inheritance, legitimation

Next would be:
- Network topology (edges, node relationships)
- George Jackson bifurcation (solidarity measure + legitimation crisis)
- Hexagonal map visualization
- Game/simulation UI
