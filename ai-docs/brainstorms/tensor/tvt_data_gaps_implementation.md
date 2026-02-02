# TVT Data Gaps and Implementation Analysis

**Status**: Implementation Planning Document
**Purpose**: Identify data gaps, rank solutions by rigor vs. complexity tradeoff
**Context**: Babylon simulation engine—rigor matters, but playable approximations are acceptable

---

## 1. Critical Data Requirements

For Topological Value Theory to function, we need:

| Quantity | Symbol | Required For | Current Status |
|----------|--------|--------------|----------------|
| Labor hours by location | L[fips] | τ (MELT) calculation | **GAP** (but see §2.1) |
| GDP by location | GDP[fips] | τ (MELT) calculation | Available (BEA) |
| Wages by location/industry | W[fips, naics] | T^μ_ν tensor | Available (QCEW) |
| Capital stock | K[fips] | Profit rate r | **GAP** |
| Net commuter flows | F[a,b] | Domestic value transfer | Available (LODES) |
| Ownership income by county | Y_capital[fips] | Where surplus lands | Available (ACS) |
| Hours distribution | H[fips, class] | Class composition signal | **GAP** |
| Depreciation rates | δ | Capital stock evolution | Available (BEA) |
| PPP ratios | PPP/XR | International γ | Available (FRED) |
| Unpaid labor hours | L_unpaid | γ_III (Dept III visibility) | **GAP** (needs ATUS) |

### 1.1 The Domestic vs International Distinction

**Critical insight**: The mechanism of value transfer differs between scales:

| Scale | Mechanism | Data Required |
|-------|-----------|---------------|
| International | PPP/exchange rate compression (γ_exchange) | Penn World Tables, trade data |
| Domestic (US) | Commuting, ownership patterns, hours access | LODES, ACS, hours data |

Everyone in the US spends dollars. A homeless person's dollar commands the same global labor as a hedge fund manager's dollar. The imperial rent is embedded in the *currency*, not distributed proportionally to domestic class position.

This means **domestic core/periphery requires different indicators than international γ**.

---

## 2. Gap Analysis and Solutions

### Gap 1: Labor Hours (L) — Hours as Class Signal

**The Problem**: QCEW provides employment (headcount) and wages, not hours worked. τ = GDP/L requires L.

**Critical insight**: Hours are not just a data gap—they're a *class signal*:

| Class Position | Hours Dynamic |
|----------------|---------------|
| Labor Aristocracy | Hoards hours (overtime, salaried blur, multiple income streams) |
| Proletariat | Hours rationed by capital ("my hours got cut") |
| Lumpen | Excluded from formal labor (QCEW hours ≈ 0) |

The *distribution* of hours across a county's population indicates class composition. A county with the same employment but higher total hours has different class structure—more labor aristocracy, less precarious proletariat.

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: Fixed hours** | L = employment × 2080 hrs/year | ★★☆☆☆ | ★☆☆☆☆ | **Only for τ ratios** |
| **B: Industry-adjusted** | L = Σ(emp_i × avg_hours_i) using BLS industry data | ★★★☆☆ | ★★☆☆☆ | Good upgrade path |
| **C: ACS hours** | Use ACS "usual hours worked" at county level | ★★★★☆ | ★★☆☆☆ | **Best for class signal** |
| **D: CPS microdata** | Current Population Survey has actual hours | ★★★★★ | ★★★★★ | Research-grade |

**When Option A is acceptable**:

For computing τ ratios (GDP per worker), the hours assumption cancels:

```
τ_ratio = τ_a / τ_b
        = (GDP_a / (emp_a × 2080)) / (GDP_b / (emp_b × 2080))
        = (GDP_a / emp_a) / (GDP_b / emp_b)
```

The 2080 constant vanishes in ratios.

**When Option A fails**:

For class composition analysis, the *distribution* of hours matters. If Oakland has 1.1 average hours per employed person vs Wayne's 0.9, that's a class signal the 2080 assumption obscures.

**Recommended approach**:
- Use Option A for τ calculations (acceptable approximation)
- Use Option C (ACS) separately for hours distribution as class indicator
- Treat these as **two different quantities**, not interchangeable

**ACS Hours Data**:

ACS variable B23020 provides "Mean usual hours worked" by county. This can be decomposed by occupation/industry to get at class-differentiated hours access.

---

### Gap 2: Capital Stock (K)

**The Problem**: TRPF requires r = s / (K + v). Our tensor gives flows (c, v, s per year), not stocks.

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: Flow proxy** | r ≈ s / (c + v) (current period only) | ★★☆☆☆ | ★☆☆☆☆ | Acceptable for trends |
| **B: Perpetual inventory** | K_t = K_{t-1}(1-δ) + c_t, initialized from 2010 | ★★★★☆ | ★★☆☆☆ | **Recommended** |
| **C: BEA fixed assets** | Use BEA county-level fixed asset estimates | ★★★★★ | ★★★☆☆ | If data available |
| **D: Vintage tracking** | Track each year's investment separately with asset-specific δ | ★★★★★ | ★★★★☆ | Future enhancement |

**Implementation for Option B**:

```python
def compute_capital_stock(c_flows: list[float], delta: float = 0.07) -> list[float]:
    """Perpetual inventory method for capital stock.

    Args:
        c_flows: Time series of constant capital flows [c_2010, c_2011, ...]
        delta: Annual depreciation rate (BEA average ≈ 7%)

    Returns:
        Time series of capital stocks [K_2010, K_2011, ...]
    """
    K = []
    for t, c in enumerate(c_flows):
        if t == 0:
            # Initialize: assume steady state K_0 = c_0 / δ
            K.append(c / delta)
        else:
            K.append(K[t-1] * (1 - delta) + c)
    return K
```

**Initialization assumption**: At t=0 (2010), assume economy was in steady state where investment = depreciation. This gives K_0 = c_0 / δ.

**Hand-wave acceptable?** YES. The initialization error decays exponentially—by year 5, it contributes <50% of K; by year 10, <25%. With 15 years of data, the late-period K is dominated by observed flows.

---

### Gap 3: Net Commuter Flows (Domestic Value Transfer)

**The Problem**: Within the US, value transfer doesn't operate through PPP differentials (everyone uses dollars). We need different indicators for domestic core/periphery.

**Why commuter flows matter**: Workers carry labor-power from home (where it's reproduced) to work (where it's consumed). Net commuter flows reveal where labor LIVES vs where value SURFACES:

- If Wayne residents work in Oakland: labor reproduced in Wayne, value appears in Oakland GDP
- Oakland captures value without reproducing the workers who produce it

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: LODES OD data** | Origin-Destination employment statistics | ★★★★☆ | ★★☆☆☆ | **Recommended** |
| **B: ACS commute** | "Place of work" vs residence | ★★★☆☆ | ★★☆☆☆ | Backup option |
| **C: Gravity model** | F[a,b] ∝ (pop_a × pop_b) / distance² | ★★☆☆☆ | ★☆☆☆☆ | Fallback only |

**LODES Data Structure** (you have the crosswalk):

LODES provides Origin-Destination Employment Statistics:
- `w_geocode`: Workplace census block
- `h_geocode`: Home census block
- `S000`: Total jobs
- `SA01-SA03`: Age brackets
- `SE01-SE03`: Earnings brackets

Aggregate to county level:
```sql
SELECT
    SUBSTR(h_geocode, 1, 5) as home_county,
    SUBSTR(w_geocode, 1, 5) as work_county,
    SUM(S000) as commuter_flow
FROM lodes_od
GROUP BY home_county, work_county;
```

**Net flow calculation**:
```sql
WITH flows AS (
    SELECT
        home_county, work_county, SUM(S000) as workers
    FROM lodes_od
    GROUP BY home_county, work_county
)
SELECT
    a.home_county as county,
    SUM(CASE WHEN a.work_county != a.home_county THEN a.workers ELSE 0 END) as outflow,
    SUM(CASE WHEN b.home_county != b.work_county THEN b.workers ELSE 0 END) as inflow,
    inflow - outflow as net_commuter_flow
FROM flows a
LEFT JOIN flows b ON a.home_county = b.work_county
GROUP BY a.home_county;
```

**Prediction**: Oakland has positive net commuter inflow (draws workers); Wayne has negative (exports workers).

---

### Gap 4: Ownership Patterns (Where Surplus Lands)

**The Problem**: Knowing where value is produced (QCEW) and where labor lives (LODES) isn't enough. We need to know where the *owners* live—where surplus value surfaces as capital income.

**The Solution**: ACS income by source at county level.

Census ACS breaks down income by source:
- Wages/salary income → v (labor income)
- Self-employment income → mixed (petty bourgeoisie)
- Interest, dividends, rental income → capital income (ownership returns)

**Key metric—Ownership Ratio**:
```sql
SELECT
    fips,
    year,
    (interest_income + dividend_income + rental_income) as capital_income,
    wage_salary_income as labor_income,
    capital_income / NULLIF(labor_income, 0) as ownership_ratio
FROM acs_income_by_source
WHERE fips IN ('26163', '26125');
```

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: ACS income by source** | Direct county-level ownership income | ★★★★☆ | ★★☆☆☆ | **Recommended** |
| **B: IRS SOI data** | Tax return data by county | ★★★★★ | ★★★☆☆ | More detailed but lagged |
| **C: Piketty/WID calibration** | National capital share as benchmark | ★★★☆☆ | ★☆☆☆☆ | For validation only |

**Piketty's role is calibration, not direct measurement**:

- WID gives national capital share of income (~30-40%)
- If Oakland's ownership_ratio >> national average → "owner-residence" county
- If Wayne's ownership_ratio << national average → "worker-residence" county

**Prediction**: Oakland has higher ownership_ratio than Wayne. Surplus produced in Wayne surfaces as capital income for Oakland residents.

**Implementation priority**: HIGH. This directly measures where surplus lands, independent of where it's produced.

---

### Gap 5: Department III Visibility (γ_III)

**The Problem**: γ_III = paid_hours / (paid_hours + unpaid_hours). QCEW has paid; ATUS has unpaid.

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: National constant** | Use national ATUS ratio for all counties | ★★☆☆☆ | ★☆☆☆☆ | **MVP acceptable** |
| **B: Demographic proxy** | γ_III[fips] = f(female_labor_force_participation[fips]) | ★★★☆☆ | ★★☆☆☆ | Better variation |
| **C: Full ATUS load** | Load ATUS, allocate to counties via ACS demographics | ★★★★☆ | ★★★☆☆ | Spec 005 exists |
| **D: Time diary imputation** | Model unpaid work from ACS household characteristics | ★★★★★ | ★★★★☆ | Academic research |

**Option A Implementation**:

National ATUS data (approximate):
- Average unpaid household labor: ~4 hours/day for women, ~2.5 hours/day for men
- Paid care sector (NAICS 624, etc.): ~5% of employment

Rough calculation:
```
unpaid_annual = (4 + 2.5) / 2 × 365 × adult_population
paid_annual = care_sector_employment × 2080

γ_III_national ≈ paid_annual / (paid_annual + unpaid_annual)
             ≈ 0.15 to 0.25 (varies by assumptions)
```

**Option B Implementation**:

Female labor force participation (FLFP) correlates with commodified care:
- High FLFP → more paid childcare, elder care → higher γ_III
- Low FLFP → more unpaid domestic labor → lower γ_III

```
γ_III[fips] = α + β × FLFP[fips]
```

Calibrate α, β from national ATUS.

**Hand-wave acceptable?** YES for MVP. Department III visibility varies less across US counties than across countries. The main insight (γ_III << 1) holds regardless of precise value.

---

### Gap 6: Reserve Army Pressure

**The Problem**: Capital Volume I shows that the reserve army disciplines labor—it's the mechanism that explains WHY hours get rationed, wages suppressed, and workers accept precarious conditions. We need to measure this pressure.

**Theoretical Foundation** (from Capital Vol I, Ch 25):

Marx identifies three forms of the reserve army:
1. **Floating**: Regularly expelled/absorbed by industry cycles (standard unemployment)
2. **Latent**: Available for absorption but not actively seeking (discouraged workers)
3. **Stagnant**: Irregularly employed, precarious (gig workers, PTER)

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: U-3 only** | Standard unemployment rate | ★★☆☆☆ | ★☆☆☆☆ | Too narrow |
| **B: U-6 composite** | Broad unemployment including marginally attached | ★★★★☆ | ★★☆☆☆ | **Recommended** |
| **C: Full decomposition** | Separate floating/latent/stagnant | ★★★★★ | ★★★★☆ | Research-grade |

**Option B Implementation**:

BLS publishes alternative unemployment measures:
- U-3: Official unemployment rate
- U-6: U-3 + marginally attached + PTER (part-time for economic reasons)
- PTER: "My hours got cut"
- Discouraged: Want work but stopped looking

```sql
SELECT
    fips,
    year,
    u6_rate,
    pter_rate,
    discouraged_rate,
    -- Composite measure
    (0.5 * u6_rate + 0.3 * pter_rate + 0.2 * discouraged_rate) as reserve_army_pressure
FROM bls_laus
WHERE fips IN ('26163', '26125');
```

**Data Sources**:
- BLS Local Area Unemployment Statistics (LAUS): County-level U-3, U-6
- ACS Employment Status tables: PTER, discouraged workers at county level
- BLS Current Population Survey: National detail (use for calibration)

**Validation Criteria**:
- ReserveArmyPressure[Wayne] > ReserveArmyPressure[Oakland] for most years
- Wayne should spike dramatically 2008-2012 (auto crisis)
- Post-spike, Wayne's suppressed wages (lower v growth) should correlate with elevated reserve army

**Hand-wave acceptable?** Partially. U-6 is well-defined but doesn't capture informal/gig economy fully. The qualitative insight (reserve army disciplines labor) is robust even if quantification is approximate.

---

### Gap 7: Dispossession Tracking

**The Problem**: Primitive accumulation is not just historical origin but ONGOING process. Gentrification IS primitive accumulation operating post-frontier. We need to track dispossession events to understand how core/periphery geography is PRODUCED.

**Theoretical Foundation** (from Capital Vol I, Part 8):

Marx: "The so-called primitive accumulation is nothing else than the historical process of divorcing the producer from the means of production."

Contemporary forms:
- **Foreclosure**: Divorces homeowner from accumulated equity
- **Eviction**: Divorces tenant from place-based social capital
- **Tax sale**: Divorces property owner from land
- **Gentrification**: Divorces community from neighborhood amenities they produced

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: Eviction Lab only** | County-level eviction rates | ★★★☆☆ | ★★☆☆☆ | Good starting point |
| **B: Eviction + Foreclosure** | Add ATTOM/CoreLogic foreclosure data | ★★★★☆ | ★★★☆☆ | **Recommended** |
| **C: Full dispossession ledger** | Track individual events with destinations | ★★★★★ | ★★★★★ | Research-grade |

**Option B Implementation**:

```python
class DispossessionRate(BaseModel):
    """Dispossession metrics for a territory."""

    fips_code: str
    year: int

    foreclosure_rate: float
    """Foreclosures per 1000 housing units."""

    eviction_rate: float
    """Evictions per 1000 renter households."""

    tax_sale_rate: float
    """Tax foreclosures per 1000 parcels."""

    @computed_field
    def composite_dispossession(self) -> float:
        """Weighted dispossession pressure."""
        return (
            0.5 * self.foreclosure_rate +
            0.3 * self.eviction_rate +
            0.2 * self.tax_sale_rate
        )
```

**Data Sources**:
- Eviction Lab (Princeton): County-level eviction rates
- ATTOM Data Solutions: Foreclosure rates (commercial, may need subscription)
- CoreLogic: Alternative foreclosure data
- County treasurer records: Tax sale data (varies by county)
- HUD: Some foreclosure data available

**Validation Criteria (Detroit)**:
- Wayne County dispossession should spike 2008-2012
- Peak should precede demographic change by 2-3 years
- Post-crisis, institutional investor purchases should accelerate
- Known gentrifying areas should show elevated pre-displacement dispossession

**Connection to Other Indicators**:
- Dispossession PRODUCES reserve army (displaced people need work)
- Dispossession CONCENTRATES ownership (increases Oakland's OwnershipRatio)
- Dispossession is the MECHANISM that creates domestic core/periphery

**Hand-wave acceptable?** For MVP, yes—use Eviction Lab (freely available) and proxy foreclosure from FRED mortgage delinquency rates. Full dispossession tracking requires commercial data or county-level scraping.

---

### Gap 8: D-P-D' Lifecycle Data

**The Problem**: The D-P-D' lifecycle circuit (Dependent → Productive → Dependent') operates on generational timescales (~80 years). We need data to track population by phase, transitions between phases, and the inheritance mechanism that reproduces class structure.

**Theoretical Foundation** (from D-P-D' theory):

The three functions of D-P-D' require different data:
1. **Ideological reproduction**: Difficult to quantify (survey data on values transmission)
2. **Legitimation (D' promise credibility)**: Measurable via pension coverage, Social Security metrics, healthcare access
3. **Class reproduction (inheritance)**: Partially measurable via wealth surveys, mobility data

**Solution Options**:

| Option | Description | Rigor | Complexity | Recommendation |
|--------|-------------|-------|------------|----------------|
| **A: Age cohorts only** | Track Pop_D, Pop_P, Pop_D' from Census | ★★☆☆☆ | ★☆☆☆☆ | MVP baseline |
| **B: Add mobility data** | Chetty Opportunity Atlas for inheritance proxy | ★★★★☆ | ★★☆☆☆ | **Recommended** |
| **C: Full inheritance tracking** | Fed SCF + estate data + inter vivos transfers | ★★★★★ | ★★★★★ | Research-grade |

**Option A Implementation (Population by Phase)**:

```python
class DPDState(BaseModel):
    """D-P-D' population distribution."""

    fips_code: str
    year: int

    pop_D: int      # Ages 0-17
    pop_P: int      # Ages 18-64, not disabled
    pop_D_prime: int  # Ages 65+ or disabled

    @computed_field
    def dependency_ratio(self) -> float:
        return (self.pop_D + self.pop_D_prime) / self.pop_P
```

Data source: Census ACS age tables (already have loaders).

**Option B Implementation (Add Mobility)**:

Chetty's Opportunity Atlas provides county-level intergenerational mobility:
- Probability of child reaching top quintile given parent quintile
- Mean income rank of children by parent income rank

This proxies inheritance mechanism effectiveness:
- High mobility = inheritance mechanism weak (class not reproducing)
- Low mobility = inheritance mechanism strong (class sticky)

```sql
SELECT
    fips,
    kfr_pooled_pooled_p25,  -- Expected rank for children of 25th percentile parents
    kfr_pooled_pooled_p75,  -- Expected rank for children of 75th percentile parents
    (kfr_pooled_pooled_p75 - kfr_pooled_pooled_p25) as mobility_gap
FROM chetty_opportunity_atlas
WHERE fips IN ('26163', '26125');
```

**Prediction**: Oakland has higher mobility_gap (more class reproduction) than Wayne.

**Legitimation Index Data**:

| Component | Data Source | Resolution |
|-----------|-------------|------------|
| Pension coverage | BLS National Compensation Survey | National/state |
| SS replacement rate | SSA data | National |
| Healthcare security | ACS health insurance tables | County |
| Home ownership | ACS tenure tables | County |
| Retirement confidence | EBRI Retirement Confidence Survey | National |

```python
class LegitimationIndex(BaseModel):
    """Credibility of the D' promise."""

    fips_code: str
    year: int

    pension_coverage: float  # Fraction with pension access
    ss_replacement: float    # SS benefits / prior earnings
    healthcare_secure: float # Fraction with secure coverage
    home_ownership: float    # Fraction owning home
    retirement_confidence: float  # Survey-based expectation

    @computed_field
    def legitimation_index(self) -> float:
        return (
            0.25 * self.pension_coverage +
            0.25 * self.ss_replacement +
            0.25 * self.healthcare_secure +
            0.15 * self.home_ownership +
            0.10 * self.retirement_confidence
        )
```

**Data Sources Summary**:

| Data | Source | Resolution | Status |
|------|--------|------------|--------|
| Population by age | Census ACS | County, annual | Have loaders |
| Disability rates | ACS, SSA | County, annual | Need to verify tables |
| Intergenerational mobility | Chetty Opportunity Atlas | County | New loader needed |
| Life expectancy | CDC WONDER | County, annual | New loader needed |
| Pension coverage | BLS NCS | National/state | Limited resolution |
| Health insurance | ACS | County | Have loaders |
| Home ownership | ACS tenure | County | Have loaders |

**Validation Criteria**:

1. DependencyRatio should correlate with care sector employment (higher ratio = more care workers needed)
2. Low intergenerational mobility should correlate with high OwnershipRatio (sticky class = concentrated ownership)
3. corr(DispossessionRate[t], Mobility[t+10]) < 0 (dispossession breaks inheritance → lower mobility)
4. Wayne should show shorter life expectancy than Oakland (differential P-phase length = eugenics signature)

**Hand-wave acceptable?** Yes for MVP. Use Census age cohorts + Chetty mobility data. Full legitimation index requires national data applied uniformly (less useful for county comparison). Inheritance tracking would require longitudinal wealth data we don't have.

---

## 3. The Domestic Core/Periphery Indicator Set

For domestic (US) analysis, we use **five indicators** instead of international γ:

| Indicator | Data Source | What It Captures | Priority |
|-----------|-------------|------------------|----------|
| **τ ratio** (GDP/worker) | BEA + QCEW | Where value surfaces | P0 |
| **Net commuter flow** | LODES | Where labor lives vs works | P1 |
| **Ownership ratio** | ACS income by source | Where owners live | P1 |
| **Hours distribution** | ACS hours worked | Class composition | P2 |
| **Reserve army pressure** | BLS LAUS, ACS | Labor discipline mechanism | P1 |

**Combined interpretation**:

A **core** county has:
- High τ (high GDP per worker)
- Positive net commuter inflow (imports labor)
- High ownership ratio (capital income concentration)
- Higher average hours (labor aristocracy hours-hoarding)
- Low reserve army pressure (tight labor market)

A **periphery** county has the inverse pattern.

**Reserve Army Pressure** (from Capital Vol I, Ch 25):

The reserve army explains WHY hours get rationed. Capital can cut hours because there's always someone desperate enough to accept what's offered.

Components:
- U-6 unemployment (broad measure including marginally attached)
- PTER rate (Part-Time for Economic Reasons — "my hours got cut")
- Discouraged worker rate

```sql
SELECT
    fips,
    year,
    u6_rate,
    pter_rate,
    discouraged_rate,
    (0.5 * u6_rate + 0.3 * pter_rate + 0.2 * discouraged_rate) as reserve_army_pressure
FROM bls_laus_extended
WHERE fips IN ('26163', '26125');
```

**Prediction**: Wayne has higher ReserveArmyPressure than Oakland, especially during/after 2008-2012 crisis.

**Composite index** (future work):
```
CoreIndex[fips] = w1×τ_pct + w2×commute_pct + w3×ownership_pct + w4×hours_pct - w5×reserve_pct
```

Note: Reserve army pressure is SUBTRACTED (inverted) — high pressure indicates periphery.
Weights initially equal (0.20 each), calibrate empirically.

---

## 4. Implementation Priority Matrix

Combining rigor, complexity, and theoretical importance:

| Gap | Recommended Solution | Priority | Blocking? |
|-----|---------------------|----------|-----------|
| τ (productivity) | GDP / (emp × 2080) | P0 | No—have data |
| Net commuter flows | LODES OD | P1 | Yes for domestic core/periphery |
| Ownership ratio | ACS income by source | P1 | Yes for surplus destination |
| Reserve army pressure | BLS LAUS + ACS | P1 | Yes for labor discipline mechanism |
| Capital stock | Perpetual inventory | P1 | Yes for TRPF |
| Hours distribution | ACS hours worked | P2 | Enhances class composition |
| Dept III visibility | National constant | P3 | Refinement only |
| Dispossession tracking | Eviction Lab + ATTOM | P2 | Yes for gentrification mechanics |
| D-P-D' lifecycle | Census age + Chetty mobility | P2 | Yes for intergenerational dynamics |
| Legitimation index | ACS + national surveys | P3 | Enhances bifurcation model |

---

## 4. Data Source Rigor Rankings

### Tier 1: High Rigor (Direct Federal Measurement)

| Source | What It Provides | Caveats |
|--------|------------------|---------|
| QCEW | Employment, wages by NAICS by county | Suppression for small cells |
| BEA GDP | Output by county | 2-year lag |
| Census ACS | Demographics, income, commuting | Survey-based, MOE issues |
| LODES | Origin-destination employment | Privacy-protected (fuzzing) |

### Tier 2: Medium Rigor (Derived/Modeled)

| Source | What It Provides | Caveats |
|--------|------------------|---------|
| BEA I-O Tables | Inter-industry flow coefficients | National, not regional |
| FRED PPP | International price comparisons | Lagged, country-level |
| BLS Productivity | Output per hour by industry | National, not county |

### Tier 3: Lower Rigor (Requires Imputation)

| Quantity | Derivation | Uncertainty |
|----------|------------|-------------|
| County hours worked | Employment × 2080 | ±10-15% |
| Capital stock | Perpetual inventory | Sensitive to initialization |
| γ_III by county | Demographic proxy | Could be off by 0.1-0.2 |

---

## 5. Recommended Implementation Sequence

### Phase 1: Core Tensor (Current Sprint)

1. Implement τ approximation: `τ[fips] = GDP[fips] / (employment[fips] × 2080)`
2. Compute γ for Wayne/Oakland: `γ = τ_Wayne / τ_Oakland`
3. Run falsification tests 1-3

**Data required**: QCEW (have), BEA GDP (verify loaded)

### Phase 2: Capital Dynamics

1. Implement perpetual inventory for K
2. Compute profit rate time series: `r = s / (K + v)`
3. Test TRPF prediction

**Data required**: BEA depreciation rates (national by asset class)

### Phase 3: Flow Topology

1. Load LODES origin-destination data
2. Build commuter flow matrix F[a,b] for Detroit metro
3. Compute flow-weighted γ for multi-county analysis

**Data required**: LODES OD files (have crosswalk, need main files)

### Phase 4: Department III Refinement

1. Implement demographic proxy for γ_III
2. Load ATUS national data
3. Validate against Spec 005

**Data required**: ATUS (new load), ACS demographics (have)

---

## 6. Acceptable Hand-Waves (Documented)

For simulation purposes, the following approximations are acceptable:

| Approximation | Justification | Error Bound |
|---------------|---------------|-------------|
| L = emp × 2080 | Cancels in γ ratios | Exact for γ, ±15% for τ |
| K_0 = c_0 / δ | Decays to <25% influence by t=10 | ±20% early, ±5% late |
| γ_III = national constant | Within-US variation is small | ±0.1 |
| Commuting ≈ value flow | Labor flows dominate at metro scale | Unknown but directionally correct |
| No goods flow data | Acceptable for metro; problematic for state+ | Underestimates inter-regional transfer |

These hand-waves do not invalidate the theory—they introduce quantitative uncertainty while preserving qualitative predictions. The simulation can identify *which approximations matter* through sensitivity analysis.

---

## 7. Sensitivity Analysis Protocol

Before trusting any result, run:

1. **Hours assumption**: Vary assumed hours/year from 1800-2200. Does γ ranking change?
2. **Depreciation rate**: Vary δ from 0.05-0.10. Does TRPF trend reverse?
3. **Initialization**: Try K_0 = c_0/δ vs K_0 = 2×c_0/δ. When does difference become negligible?
4. **γ_III value**: Vary from 0.15-0.35. Does shadow subsidy ranking change?

If qualitative conclusions are robust to these variations, the approximations are acceptable. If conclusions flip, that parameter needs better data.
