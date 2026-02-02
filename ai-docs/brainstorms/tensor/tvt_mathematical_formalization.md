# Topological Value Theory: Mathematical Formalization

**Status**: Axiomatic Foundation Document
**Purpose**: Rigorous specification of TVT's mathematical structure
**Audience**: Implementation, validation, and theoretical critique

---

## 1. Primitive Notions

The following are undefined terms from which all other concepts are derived:

| Primitive | Symbol | Interpretation |
|-----------|--------|----------------|
| Concrete labor time | L ∈ ℕ | Integer hours of sector-typed human labor |
| Location | fips ∈ F | Geographic unit (FIPS code, 5-digit string) |
| Time period | t ∈ T | Discrete time index (year) |
| Use-value type | u ∈ U | Physical output category |

---

## 2. Axiom System

### Axiom Group A: Conservation

**A1. (Labor-Value Conservation)**
Total value created in period t equals total labor performed in period t.

```
∀t: Σ_fips V[fips, t] = Σ_fips L[fips, t]
```

**A2. (Value Redistribution)**
Value is neither created nor destroyed in exchange; it is only redistributed.

```
∀t, ∀(a,b) ∈ edges: V_sent[a→b, t] = V_received[a←b, t] / γ[a,b,t]
```

The visibility coefficient γ determines how much of the sent value registers at the destination.

**A3. (Stock-Flow Consistency)**
Capital stock evolves by accumulation minus depreciation.

```
K[fips, t+1] = K[fips, t] × (1 - δ) + I[fips, t]
```

Where I is gross investment (new constant capital added).

### Axiom Group B: Temporalism (from TSSI)

**B1. (Input-Output Sequence)**
Output value at t+1 depends on input prices at t plus living labor during [t, t+1].

```
V[fips, t+1] = P_inputs[fips, t] + L[fips, t→t+1]
```

**B2. (Historical Cost)**
The value of constant capital is the price actually paid, not replacement cost.

```
c[fips, t] = P_paid[fips, t] (not P_current[fips, t])
```

**B3. (MELT Bridge)**
Labor-time and money-price are related by the Monetary Expression of Labor Time.

```
τ[fips, t] = GDP[fips, t] / L[fips, t]
P = τ × V (for any value V)
```

### Axiom Group C: Visibility (International Value Transfer)

**C1. (Visibility Range)**
The visibility coefficient is bounded:

```
∀(a,b,t): γ[a,b,t] ∈ [0, 1]
```

**C2. (Visibility as MELT Ratio)**
For spatial value transfer across currency zones, visibility equals the ratio of MELTs:

```
γ[a→b, t] = τ[a, t] / τ[b, t]
```

When τ_a < τ_b (lower productivity origin), γ < 1.

**Note**: This axiom applies to *international* transfers where PPP ≠ exchange rate. For domestic (same-currency) transfers, see §3.3 on Domestic Indicators.

**C3. (Department III Visibility)**
For reproductive labor, visibility equals the commodified fraction:

```
γ_III[fips, t] = L_paid[fips, t] / (L_paid[fips, t] + L_unpaid[fips, t])
```

**C4. (Multiplicative Chain Composition)**
For value flowing through multiple edges:

```
γ[a→c via b] = γ[a→b] × γ[b→c]
```

### Axiom Group C': Domestic Core/Periphery (Same-Currency Zones)

Within a single currency zone (e.g., the US), all actors spend the same money, which commands the same global labor. The imperial rent is embedded in the *currency*, not distributed by domestic class position.

Therefore, domestic core/periphery uses different indicators:

**C'1. (Net Commuter Flow)**
Labor flows from residence to workplace. Net flow determines domestic value geography:

```
NetFlow[fips, t] = Σ_j (workers[j→fips, t]) - Σ_j (workers[fips→j, t])
```

Core: NetFlow > 0 (imports labor)
Periphery: NetFlow < 0 (exports labor)

**C'2. (Ownership Concentration)**
Surplus surfaces as capital income where owners reside:

```
OwnershipRatio[fips, t] = Y_capital[fips, t] / Y_labor[fips, t]
```

Where:
- Y_capital = interest + dividends + rental income
- Y_labor = wages + salaries

**C'3. (Hours as Class Signal)**
Access to labor-hours is class-stratified:

| Class Position | Hours Dynamic |
|----------------|---------------|
| Labor Aristocracy | H > H_mean (hours hoarding) |
| Proletariat | H rationed by capital |
| Lumpen | H ≈ 0 in formal economy |

```
MeanHours[fips, t] = Σ hours_worked / Σ employed
```

Higher MeanHours indicates more labor aristocracy composition.

**C'4. (Domestic Core Index)**
Composite measure of domestic core position:

```
CoreIndex[fips, t] = f(τ[fips,t], NetFlow[fips,t], OwnershipRatio[fips,t], MeanHours[fips,t])
```

Functional form to be determined empirically; all components should correlate positively with core position.

### Axiom Group D: Departmental Structure

**D1. (Four Departments)**
Economic production divides into four departments:

```
μ ∈ {I, IIa, IIb, III}

I   = Production of means of production
IIa = Production of wage goods (necessary consumption)
IIb = Production of luxury goods
III = Production of labor-power (reproductive labor)
```

**D2. (Three Value Components)**
Each department's output decomposes into:

```
ν ∈ {c, v, s}

c = constant capital (transferred from past dead labor)
v = variable capital (wages, value of labor-power)
s = surplus value (unpaid labor)
```

**D3. (Departmental Closure)**
Department III's output (labor-power) enters Departments I, IIa, IIb as input:

```
L_living[I, t] + L_living[IIa, t] + L_living[IIb, t] = output[III, t-1]
```

### Axiom Group E: Network Structure

**E1. (Graph Representation)**
The economy is a directed graph G = (N, E) where:
- N = nodes (locations × classes)
- E = edges (value flow relationships)

**E2. (Edge Types)**
Edges are typed:

```
EdgeType ∈ {EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC}
```

**E3. (Topology as Material Base)**
Network structure is part of the relations of production, not superstructure. Changes to E affect dynamics.

### Axiom Group F: Lifecycle Circuit (D-P-D')

**F1. (Lifecycle Phases)**
Every human passes through three phases:

```
Phase ∈ {D, P, D'}

D  = Dependent (pre-productive): ages 0-17 typically
P  = Productive: ages 18-64 typically, selling labor-power
D' = Dependent' (post-productive): ages 65+ or disabled
```

**F2. (Intergenerational Spiral)**
The circuit does not repeat for individuals but spirals across generations:

```
Generation_n: D → P → D' → death
                  ↓
                produces
                  ↓
Generation_{n+1}: D → P → D' → death
```

**F3. (Three Functions)**
D-P-D' serves three structural functions:

```
F_ideology: D phase transmits consciousness, hegemony, cultural capital
F_legitimation: D' promise secures consent to P-phase exploitation
F_inheritance: D' terminus transfers accumulated value to next generation's D
```

**F4. (Circuit Nesting)**
The three circuits nest hierarchically:

```
D-P-D' contains:
  └── P phase contains:
        └── C-M-C (daily reproduction)
              └── provides LP to M-C-M' (capital's circuit)
```

**F5. (Inheritance as Class Reproduction)**
Inheritance at D' terminus determines class reproduction:

```
Inheritance[class, fips, t] = Accumulated[class, fips, t] - D'_care_costs[class, fips, t]

If Inheritance > 0: Class position reproduces or elevates
If Inheritance ≤ 0: Class position reproduces or degrades
```

**F6. (Legitimation Condition)**
System stability requires credible D' promise:

```
LegitimationIndex[fips, t] = f(pension_coverage, SS_replacement, healthcare_security, home_ownership)

If LegitimationIndex < threshold: Legitimation crisis risk
```

---

## 3. Defined Terms

### 3.1 The Value Tensor

**Definition (ValueTensor4×3)**:

```
T^μ_ν[fips, t] : F × T → ℝ^(4×3)

Where:
  μ ∈ {I, IIa, IIb, III}  (row index: department)
  ν ∈ {c, v, s}           (column index: value component)
```

**Properties**:
- Extensive: sums under geographic aggregation
- Temporal: indexed by period t
- Unit: labor-hours (via MELT conversion)

### 3.2 The Gamma Tensor

**Definition (GammaTensor)**:

```
γ_μ[fips, t] : F × T → [0,1]^4

Where:
  μ ∈ {I, IIa, IIb, III}  (department index)
```

**Properties**:
- Intensive: weighted-averages under aggregation
- Dimensionless ratio
- Department-specific visibility

### 3.3 Price-Visible Value

**Definition**:

```
T_price^μ_ν[fips, t] = γ_μ[fips, t] × T^μ_ν[fips, t]
```

This is the value that appears in the price system.

### 3.4 Shadow Value

**Definition**:

```
S^μ_ν[fips, t] = (1 - γ_μ[fips, t]) × T^μ_ν[fips, t]
```

This is value produced but not compensated—extracted as rent.

### 3.5 Total Shadow Subsidy

**Definition**:

```
Φ_shadow[fips, t] = Σ_μ Σ_ν S^μ_ν[fips, t]
                  = Σ_μ (1 - γ_μ) × T^μ_total[fips, t]
```

### 3.6 Profit Rate

**Definition**:

```
r[fips, t] = Σ_μ s^μ[fips, t] / (K[fips, t] + Σ_μ v^μ[fips, t])
```

Where K is capital stock (accumulated c minus depreciation).

### 3.7 Organic Composition of Capital

**Definition**:

```
OCC[fips, t] = Σ_μ c^μ[fips, t] / Σ_μ v^μ[fips, t]
```

### 3.8 Rate of Exploitation

**Definition**:

```
e[fips, t] = Σ_μ s^μ[fips, t] / Σ_μ v^μ[fips, t]
```

### 3.9 Domestic Indicators (Same-Currency Zone)

**Definition (Net Commuter Flow)**:

```
NetFlow[fips, t] = Inflow[fips, t] - Outflow[fips, t]

Where:
  Inflow[fips, t] = Σ_{j ≠ fips} workers[residence=j, workplace=fips, t]
  Outflow[fips, t] = Σ_{j ≠ fips} workers[residence=fips, workplace=j, t]
```

**Properties**:
- Σ_fips NetFlow[fips, t] = 0 (flows sum to zero nationally)
- NetFlow > 0 indicates labor importer (core)
- NetFlow < 0 indicates labor exporter (periphery)

**Definition (Ownership Ratio)**:

```
OwnershipRatio[fips, t] = Y_capital[fips, t] / Y_labor[fips, t]

Where:
  Y_capital = aggregate (interest + dividends + rental income)
  Y_labor = aggregate (wages + salaries)
```

**Properties**:
- Dimensionless ratio
- Higher values indicate capital income concentration (owner-residence)
- National benchmark: ~0.3-0.4 (from Piketty/WID)

**Definition (Mean Hours Worked)**:

```
MeanHours[fips, t] = Σ hours_worked[fips, t] / employed[fips, t]
```

**Properties**:
- Unit: hours per worker per year
- Benchmark: ~2080 for full-time equivalent
- Higher indicates labor aristocracy hours-hoarding
- Lower indicates precarious proletariat (hours rationing)

**Definition (Hours Distribution—Class Signal)**:

```
HoursGini[fips, t] = Gini coefficient of hours distribution across workers
```

High inequality indicates stratified class structure (some hoarding, some rationed).

**Definition (Domestic Core Index)**:

```
CoreIndex[fips, t] = w_τ × norm(τ) + w_F × norm(NetFlow) + w_O × norm(OwnershipRatio) + w_H × norm(MeanHours) - w_R × norm(ReserveArmyPressure)

Where:
  norm(x) = (x - x_min) / (x_max - x_min) (min-max normalization across fips)
  w_i = weights (to be calibrated, initially equal: 0.20 each)
  Note: ReserveArmyPressure is SUBTRACTED (high pressure = periphery)
```

**Properties**:
- Range: [0, 1] after normalization
- CoreIndex → 1 indicates core position
- CoreIndex → 0 indicates periphery position

### 3.10 Reserve Army Pressure (from Capital Vol I)

**Definition (Reserve Army Pressure)**:

```
ReserveArmyPressure[fips, t] = w_1 × U6[fips,t] + w_2 × PTER[fips,t] + w_3 × Discouraged[fips,t]

Where:
  U6 = Broad unemployment rate (includes marginally attached, PTER)
  PTER = Part-Time for Economic Reasons rate ("my hours got cut")
  Discouraged = Discouraged worker rate (want work but stopped looking)
  w_i = weights (default: 0.5, 0.3, 0.2)
```

**Theoretical Foundation** (Capital Vol I, Ch 25):

Marx identifies three forms of the reserve army:
- Floating: Regularly expelled/absorbed by cycles → captured by U6
- Latent: Available but not seeking → captured by Discouraged
- Stagnant: Irregularly employed, precarious → captured by PTER

**Properties**:
- Unit: percentage (rate)
- Higher values indicate more labor discipline (periphery characteristic)
- Disciplines v: high reserve army → wages suppressed toward subsistence
- Inversely related to core position

### 3.11 Dispossession Rate (Primitive Accumulation)

**Definition (Dispossession Rate)**:

```
DispossessionRate[fips, t] = w_f × Foreclosure[fips,t] + w_e × Eviction[fips,t] + w_t × TaxSale[fips,t]

Where:
  Foreclosure = foreclosures per 1000 housing units
  Eviction = evictions per 1000 renter households
  TaxSale = tax foreclosures per 1000 parcels
  w_i = weights (default: 0.5, 0.3, 0.2)
```

**Properties**:
- Unit: events per 1000 units
- Measures ongoing primitive accumulation
- Produces reserve army (displaced people need work)
- Concentrates ownership (transfers property to accumulators)
- Precedes gentrification indicators by 2-3 years (leading indicator)

### 3.12 Lifecycle Distribution (D-P-D')

**Definition (Population by Phase)**:

```
Pop_D[fips, t] = population in D phase (ages 0-17)
Pop_P[fips, t] = population in P phase (ages 18-64, able to work)
Pop_D'[fips, t] = population in D' phase (ages 65+ or disabled)
```

**Definition (Dependency Ratio)**:

```
DependencyRatio[fips, t] = (Pop_D + Pop_D') / Pop_P
```

**Properties**:
- Dimensionless ratio
- Higher ratio = more burden on productive population
- Affects available labor supply and care demands

**Definition (Phase Transition Rates)**:

```
r_D→P[fips, t] = annual rate of D → P transition (youth entering workforce)
r_P→D'[fips, t] = annual rate of P → D' transition (retirement, disability)
r_D'→death[fips, t] = annual mortality rate in D' phase
```

### 3.13 Inheritance Flow

**Definition (Inheritance by Class)**:

```
Inheritance[class, fips, t] = Σ (Accumulated_wealth × mortality_rate)_class

Where accumulated wealth is measured at D' terminus for those who died in year t.
```

**Properties**:
- Unit: currency (or labor-hours via MELT)
- Mechanism of intergenerational class reproduction
- Severed by dispossession (foreclosure transfers wealth to capital, not heirs)

**Definition (Inheritance Gini)**:

```
InheritanceGini[fips, t] = Gini coefficient of inheritance distribution across population
```

**Prediction**: InheritanceGini > IncomeGini (inheritance more unequal than income)

### 3.14 Legitimation Index

**Definition (Legitimation Index)**:

```
LegitimationIndex[fips, t] = w_1×PensionCoverage + w_2×SSReplacement + w_3×HealthcareSecurity + w_4×HomeOwnership + w_5×RetirementConfidence

Where:
  PensionCoverage = fraction of P-phase workers with pension access
  SSReplacement = Social Security benefits / pre-retirement income
  HealthcareSecurity = fraction with secure D' healthcare
  HomeOwnership = P-phase home ownership rate (inheritance vehicle)
  RetirementConfidence = survey-based expectation of secure D'
  w_i = weights (default: 0.25, 0.25, 0.25, 0.15, 0.10)
```

**Properties**:
- Range: [0, 1]
- Measures credibility of the D' promise
- Low values indicate legitimation crisis risk
- Connects to bifurcation: failed legitimation + weak solidarity → fascist potential

---

## 4. Transformation Rules

### 4.1 Geographic Aggregation

**For extensive quantities (T, K, Φ)**:

```
T^μ_ν[state, t] = Σ_{fips ∈ state} T^μ_ν[fips, t]
```

**For intensive quantities (γ, τ, r)**:

```
γ_μ[state, t] = Σ_{fips} (T^μ_total[fips,t] × γ_μ[fips,t]) / Σ_{fips} T^μ_total[fips,t]
```

(Value-weighted average)

### 4.2 Temporal Aggregation

**For flow quantities (T per period)**:

```
T^μ_ν[fips, decade] = Σ_{t ∈ decade} T^μ_ν[fips, t]
```

**For stock quantities (K at point in time)**:

Not aggregated; use end-of-period value.

### 4.3 Currency ↔ Labor-Time Conversion

```
Value_labor = Value_price / τ
Value_price = Value_labor × τ
```

Where τ = MELT = GDP / L.

---

## 5. Dynamical Equations

### 5.1 Value Tensor Evolution

The tensor at t+1 depends on:
- Prior period's capital stock (c component)
- Current period's labor (v, s components)

```
T^μ_c[fips, t+1] = f_c(K[fips, t], depreciation_flows[t])
T^μ_v[fips, t+1] = wages_paid[fips, μ, t+1] / τ[fips, t+1]
T^μ_s[fips, t+1] = T^μ_v[fips, t+1] × e[μ, t+1]
```

Where e[μ, t] is the exploitation rate for department μ.

### 5.2 Capital Stock Evolution

```
K[fips, t+1] = K[fips, t] × (1 - δ) + Σ_μ c^μ[fips, t+1]
```

During crisis, δ_effective > δ_normal (accelerated depreciation).

### 5.3 MELT Evolution

```
τ[fips, t+1] = GDP[fips, t+1] / L[fips, t+1]
```

MELT can change due to:
- Productivity changes
- Inflation/deflation
- Structural economic shifts

### 5.4 Visibility Evolution

**For Departments I, IIa, IIb** (trade-mediated):

```
γ_μ[fips, t+1] = Σ_origin (import_share[fips, origin, t+1] × γ_country[origin, t+1])
```

Visibility changes slowly as trade patterns shift.

**For Department III** (demographically-mediated):

```
γ_III[fips, t+1] = f(FLFP[fips, t+1], care_sector_employment[fips, t+1])
```

Visibility increases with commodification of care.

### 5.5 Profit Rate Dynamics

From the definitions:

```
r[t+1] = (e × v[t+1]) / (K[t+1] + v[t+1])
       = e / (K[t+1]/v[t+1] + 1)
       = e / (OCC × (v[t+1]/c[t+1]) × (K[t+1]/accumulated_c) + 1)
```

If OCC rises faster than e, r falls. This is TRPF.

---

## 6. Derived Theorems

### Theorem 1: Conservation Under Visibility

**Statement**: Total labor equals total visible value plus total shadow value.

```
Σ_fips L[fips, t] = Σ_fips (T_price_total[fips, t] + S_total[fips, t])
```

**Proof**: By A1 (conservation) and definitions:
```
L = V (by A1)
V = T_total (by definition of T)
T = T_price + S (by definitions of T_price, S)
∴ L = T_price + S ∎
```

### Theorem 2: Shadow Subsidy as Rent Source

**Statement**: Total profit equals explicit surplus value plus shadow subsidy.

```
Π_total[t] = Σ_fips s[fips, t] + Φ_shadow[t]
```

**Proof**: Capitalists receive:
1. Explicit surplus (s) from workers they directly employ
2. Shadow subsidy (Φ) from invisible labor

Both appear as profit in the price system. ∎

### Theorem 3: γ < 1 Implies Net Transfer

**Statement**: If γ[a→b] < 1, node b extracts value from node a.

**Proof**:
```
Value sent from a: V_a
Value registered at b: γ × V_a < V_a
Difference captured by b: (1 - γ) × V_a > 0
```

This difference is rent extracted by b from a. ∎

### Theorem 4: TRPF Under Rising OCC

**Statement**: If OCC rises and e is constant, r falls.

**Proof**:
```
r = s / (K + v) = (e × v) / (K + v)

Let OCC = c/v rise, meaning c grows faster than v.
If investment I ∝ c, then K grows faster than v.
∴ K + v grows faster than e × v.
∴ r = (e × v) / (K + v) falls. ∎
```

### Theorem 5: Aggregation Consistency

**Statement**: Value-weighted averaging preserves MELT identity.

**Proof**:
```
τ[aggregate] = GDP[aggregate] / L[aggregate]
             = Σ GDP[i] / Σ L[i]
             = Σ (τ[i] × L[i]) / Σ L[i]
             = labor-weighted average of τ[i]

For γ = τ_a / τ_b:
γ[aggregate_a → aggregate_b] = τ[aggregate_a] / τ[aggregate_b]
                              = (Σ τ_a × L_a / Σ L_a) / (Σ τ_b × L_b / Σ L_b)
```

Which is consistent with computing γ from aggregated τ values. ∎

---

## 7. Consistency Checks

### Check 1: Single System Compliance

TVT maintains TSSI's single-system property:

- There is one accounting system (labor-time, converted via MELT)
- γ operates on price formation, not as a parallel "value" calculation
- The value entering production is the price paid (historical cost)

γ < 1 means the price paid is less than the labor content—but the price paid is still what enters the value calculation.

### Check 2: Non-Negative Values

All quantities remain non-negative under the dynamics:

- T^μ_ν ≥ 0 (flows of labor)
- γ ∈ [0, 1] (bounded by definition)
- K ≥ 0 (cannot have negative capital stock)
- r can be negative in crisis, but this triggers devaluation

### Check 3: Dimensional Consistency

| Quantity | Dimension |
|----------|-----------|
| T^μ_ν | labor-hours |
| γ | dimensionless |
| τ (MELT) | price / labor-hour |
| K | labor-hours |
| r | dimensionless (ratio) |
| Φ | labor-hours |

All equations are dimensionally consistent.

---

## 8. Falsification Criteria

### 8.1 Internal Consistency Tests

**Test 1 (Aggregation Invariance)**:
Compute γ two ways:
- Path A: county τ → county γ → aggregate via weighted average
- Path B: aggregate τ directly → compute γ

Result: Should match within floating-point tolerance.

**Test 2 (Conservation Check)**:
```
|Σ L - Σ (T_price + S)| < ε
```

If this fails by more than ε (rounding error), there's a bug.

**Test 3 (Bound Check)**:
```
∀ fips, t, μ: 0 ≤ γ_μ[fips, t] ≤ 1
```

Any γ outside [0,1] indicates error.

### 8.2 Empirical Falsification

**Prediction 1 (International γ)**: γ < 1 for periphery → core flows.
```
H₀: γ[periphery→core] ≥ 1
H₁: γ[periphery→core] < 1
```

**Prediction 2 (Domestic—Commuter Flow)**: Core counties have positive net commuter inflow.
```
H₀: NetFlow[Oakland] ≤ 0
H₁: NetFlow[Oakland] > 0

H₀: NetFlow[Wayne] ≥ 0
H₁: NetFlow[Wayne] < 0
```

**Prediction 3 (Domestic—Ownership)**: Core counties have higher ownership ratio.
```
H₀: OwnershipRatio[Oakland] ≤ OwnershipRatio[Wayne]
H₁: OwnershipRatio[Oakland] > OwnershipRatio[Wayne]
```

**Prediction 4 (Domestic—Hours)**: Core counties have higher mean hours (labor aristocracy).
```
H₀: MeanHours[Oakland] ≤ MeanHours[Wayne]
H₁: MeanHours[Oakland] > MeanHours[Wayne]
```

**Prediction 5 (τ Differential)**: Core counties have higher GDP per worker.
```
H₀: τ[Oakland] ≤ τ[Wayne]
H₁: τ[Oakland] > τ[Wayne]
```

**Prediction 6 (Reserve Army Pressure)**: Periphery counties have higher reserve army pressure.
```
H₀: ReserveArmyPressure[Wayne] ≤ ReserveArmyPressure[Oakland]
H₁: ReserveArmyPressure[Wayne] > ReserveArmyPressure[Oakland]
```

**Prediction 7 (Reserve Army → Wage Suppression)**: High reserve army pressure correlates with subsequent wage suppression.
```
H₀: corr(ReserveArmyPressure[t], Δv[t+1]) ≥ 0
H₁: corr(ReserveArmyPressure[t], Δv[t+1]) < 0 (high pressure → lower wage growth)
```

**Prediction 8 (Dispossession → Reserve Army)**: Dispossession events produce reserve army.
```
H₀: corr(DispossessionRate[t], ReserveArmyPressure[t+1]) ≤ 0
H₁: corr(DispossessionRate[t], ReserveArmyPressure[t+1]) > 0 (dispossession → more reserve army)
```

**Prediction 9 (TRPF)**: Profit rate trends downward absent devaluation.
```
H₀: dr/dt ≥ 0 (no TRPF)
H₁: dr/dt < 0 (TRPF operative)
```

**Prediction 10 (OCC-Core Correlation)**: OCC correlates positively with core position.
```
H₀: corr(OCC, CoreIndex) ≤ 0
H₁: corr(OCC, CoreIndex) > 0
```

**Prediction 11 (Indicator Coherence)**: Domestic indicators should correlate.
```
H₀: corr(τ, NetFlow, OwnershipRatio, MeanHours, -ReserveArmyPressure) ≤ 0 (indicators incoherent)
H₁: All pairwise correlations in expected direction (indicators identify same underlying structure)
```

If predictions 2-5 consistently hold for Wayne/Oakland, the domestic indicator set is validated. If prediction 11 fails (indicators don't correlate), the composite CoreIndex is meaningless and we need to investigate which indicators are actually tracking core/periphery.

If predictions 1-11 consistently fail across multiple test cases, TVT is empirically falsified.

**Prediction 12 (Inheritance Inequality)**: Inheritance is more unequal than income.
```
H₀: InheritanceGini ≤ IncomeGini
H₁: InheritanceGini > IncomeGini
```

**Prediction 13 (Dispossession → Broken Inheritance)**: High dispossession counties show lower intergenerational mobility.
```
H₀: corr(DispossessionRate, ChettyMobility) ≥ 0
H₁: corr(DispossessionRate, ChettyMobility) < 0
```

**Prediction 14 (Legitimation → Stability)**: Low legitimation index correlates with political instability.
```
H₀: corr(LegitimationIndex, PoliticalInstability) ≥ 0
H₁: corr(LegitimationIndex, PoliticalInstability) < 0 (low legitimation → more instability)
```

**Prediction 15 (D-phase Investment → P-phase Productivity)**: School spending predicts later productivity with ~20 year lag.
```
H₀: corr(SchoolSpending[t], τ[t+20]) ≤ 0
H₁: corr(SchoolSpending[t], τ[t+20]) > 0
```

**Prediction 16 (Eugenics Signature)**: Targeted populations show shortened P-phase.
```
H₀: Mean(P_phase_length) is equal across demographic groups
H₁: Mean(P_phase_length) is shorter for groups subject to eugenics pressures
```

If predictions 12-16 consistently fail, the D-P-D' extension to TVT is falsified.

---

## 9. Extensions and Open Problems

### 9.1 International γ

For cross-border flows, γ requires PPP data:

```
γ[country_a → country_b] = (PPP_a / XR_a) / (PPP_b / XR_b)
```

Where PPP = purchasing power parity, XR = market exchange rate.

This is available from Penn World Tables but not at sub-national resolution.

### 9.2 Vintage Capital

For rigorous TRPF, capital should track vintage:

```
K[fips, t] = Σ_{τ ≤ t} I[fips, τ] × (1 - δ)^(t-τ)
```

This requires tracking each year's investment separately, increasing state space.

### 9.3 Solidarity Measure

The George Jackson bifurcation requires a scalar solidarity measure:

```
σ[fips, t] = f(G_solidarity[fips, t])
```

Where G_solidarity is the subgraph of SOLIDARISTIC edges.

Candidates:
- Edge fraction: |E_solidarity| / |E_total|
- Algebraic connectivity: λ₂ of Laplacian of G_solidarity
- Clustering coefficient of solidarity subgraph

This remains underspecified.

### 9.4 Crisis Dynamics

The model currently treats crisis as exogenous (δ increases). A complete model would derive crisis endogenously:

```
Crisis triggers when: r[t] < r_threshold for sustained period
Crisis resolves via: K[t+1] = K[t] × (1 - δ_crisis), δ_crisis >> δ_normal
```

The determination of r_threshold and δ_crisis requires additional theory.

---

## 10. Summary of Mathematical Objects

| Object | Type | Indices | Dimension |
|--------|------|---------|-----------|
| T^μ_ν | Tensor | [fips, year, dept, component] | 4×3 per fips-year |
| γ_μ | Vector | [fips, year, dept] | 4×1 per fips-year |
| τ | Scalar field | [fips, year] | 1 per fips-year |
| K | Scalar field | [fips, year] | 1 per fips-year |
| r | Scalar field | [fips, year] | 1 per fips-year |
| G | Graph | nodes × edges | variable |
| F | Matrix | [origin_fips, dest_fips] | sparse, \|F\|² entries |
| NetFlow | Scalar field | [fips, year] | 1 per fips-year |
| OwnershipRatio | Scalar field | [fips, year] | 1 per fips-year |
| MeanHours | Scalar field | [fips, year] | 1 per fips-year |
| ReserveArmyPressure | Scalar field | [fips, year] | 1 per fips-year |
| DispossessionRate | Scalar field | [fips, year] | 1 per fips-year |
| CoreIndex | Scalar field | [fips, year] | 1 per fips-year |
| Pop_D, Pop_P, Pop_D' | Scalar fields | [fips, year] | 1 each per fips-year |
| DependencyRatio | Scalar field | [fips, year] | 1 per fips-year |
| Inheritance | Scalar field | [class, fips, year] | 1 per class-fips-year |
| LegitimationIndex | Scalar field | [fips, year] | 1 per fips-year |

---

## 11. Notation Reference

| Symbol | Meaning |
|--------|---------|
| T^μ_ν | Value tensor (μ=dept, ν=component) |
| γ_μ | Visibility coefficient for department μ (international) |
| τ | MELT (Monetary Expression of Labor Time) |
| c, v, s | Constant capital, variable capital, surplus value |
| K | Capital stock |
| r | Profit rate |
| e | Rate of exploitation (s/v) |
| OCC | Organic composition of capital (c/v) |
| Φ | Shadow subsidy / imperial rent |
| δ | Depreciation rate |
| L | Labor hours |
| F | Flow matrix (commuter or commodity) |
| G | Network graph |
| NetFlow | Net commuter flow (domestic indicator) |
| OwnershipRatio | Capital income / labor income (domestic indicator) |
| MeanHours | Average hours per worker (domestic indicator) |
| ReserveArmyPressure | Labor discipline pressure from unemployment (domestic indicator) |
| DispossessionRate | Foreclosure + eviction rate (primitive accumulation measure) |
| CoreIndex | Composite domestic core/periphery measure |
| D, P, D' | Lifecycle phases (Dependent, Productive, Dependent') |
| Pop_D, Pop_P, Pop_D' | Population in each lifecycle phase |
| DependencyRatio | (Pop_D + Pop_D') / Pop_P |
| Inheritance | Intergenerational wealth transfer at D' terminus |
| LegitimationIndex | Credibility of D' promise |
| fips | Location index (FIPS code) |
| t | Time index (year) |
| μ | Department index {I, IIa, IIb, III} |
| ν | Value component index {c, v, s} |
| Y_capital | Capital income (interest + dividends + rent) |
| Y_labor | Labor income (wages + salaries) |
| U6 | Broad unemployment rate |
| PTER | Part-time for economic reasons rate |
