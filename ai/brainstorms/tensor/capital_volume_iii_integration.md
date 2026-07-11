# Capital Volume III Integration

## The Distribution of Surplus Value: Interest, Rent, and Fictitious Capital

**Status**: Theoretical Framework
**Depends On**: Tensor Hierarchy, Dialectical Consciousness Model
**Scope**: Extending the primitive tensor to capture financial and landed capital

---

## 1. The Structure of Volume III

Capital Volume III addresses the **distribution** of surplus value, which our primitive tensor (c, v, s) captures at the point of production but not at the point of realization and appropriation.

Marx's structure:

| Part | Topic | Babylon Integration |
|------|-------|---------------------|
| I-II | Profit rate, equalization to average rate | Transformation: values → prices of production |
| III | Tendency of Rate of Profit to Fall (TRPF) | Already partially modeled; needs counter-tendencies |
| IV | Commercial/merchant capital | Circulation costs, value realization delays |
| V | Interest-bearing capital, credit, fictitious capital | **NEW**: Financial layer |
| VI | Ground rent | **NEW**: Rent extraction from monopolized nature |
| VII | Revenue and its sources (Trinity Formula) | Ideological mystification of exploitation |

The key insight: **surplus value (s) is produced in production but distributed in circulation**. Our tensor captures production; we need additional structures to capture distribution.

---

## 2. The Division of Surplus Value

### 2.1 The Split

Total surplus value (s) divides into:

```
s = profit_of_enterprise + interest + ground_rent
```

Where:
- **Profit of enterprise** (p): What the functioning capitalist retains
- **Interest** (i): Payment to money-capital for the use of capital
- **Ground rent** (r): Payment to landowners for access to monopolized nature

This is not three independent sources of value (the "Trinity Formula" mystification) but three **claims** on the single source: unpaid labor.

### 2.2 Tensor Representation

Extend the DepartmentRow to track distribution:

```python
class SurplusDistribution(BaseModel):
    """How surplus value is divided among claimants."""

    profit_of_enterprise: Currency
    """Retained by functioning industrial/commercial capitalist."""

    interest_paid: Currency
    """Transferred to money-capitalists (banks, bondholders)."""

    ground_rent_paid: Currency
    """Transferred to landowners (including resource extraction rents)."""

    @computed_field
    def total(self) -> Currency:
        return self.profit_of_enterprise + self.interest_paid + self.ground_rent_paid

    def validate_against_surplus(self, s: Currency) -> bool:
        """Distribution cannot exceed production."""
        return self.total <= s
```

---

## 3. Interest-Bearing Capital

### 3.1 Marx's Framework

Interest-bearing capital (IBC) is capital that functions purely as capital — it generates a return simply by being lent. The formula is M → M' without any intermediate commodity production.

Key relationships:

```
0 < interest_rate < profit_rate  (in general)
```

Interest is bounded above by the profit rate because interest is paid out of profit. If interest exceeded profit, no industrial capitalist would borrow.

### 3.2 Interest Rate Dynamics

Marx identifies that the interest rate:

1. **Has no "natural" rate** — unlike wages (bounded by reproduction) or profit (bounded by exploitation), interest is purely determined by supply/demand in the money market
2. **Tends to fall in the long run** — as capital accumulates, the supply of loanable money-capital increases
3. **Moves counter-cyclically** — low during expansion (abundant credit), high during crisis (credit crunch)

### 3.3 Tensor Integration

```python
class InterestRateState(BaseModel):
    """Interest rate dynamics within a territory."""

    base_rate: float = Field(ge=0.0)
    """Central bank or benchmark rate."""

    spread_by_class: dict[SocialRole, float]
    """Risk premium charged to different borrowers.

    Periphery pays higher spread than core.
    Workers pay higher than bourgeoisie.
    """

    def effective_rate(self, borrower: SocialRole) -> float:
        return self.base_rate + self.spread_by_class.get(borrower, 0.0)

    def interest_transfer(
        self,
        principal: Currency,
        borrower: SocialRole,
        period: float,
    ) -> Currency:
        """Value transferred from borrower to lender."""
        return principal * self.effective_rate(borrower) * period
```

**Data sources:**
- FRED: Federal funds rate, Treasury yields, corporate bond spreads
- BLS: Consumer credit interest rates by demographic

---

## 4. Fictitious Capital

### 4.1 Definition

Fictitious capital is Marx's term for financial assets whose market value is determined by **capitalization of expected future income**, not by any underlying labor-value.

```
Price of fictitious capital = Expected yield / Interest rate
```

Examples:
- Government bonds (claims on future tax revenue)
- Corporate stocks (claims on future profits)
- Mortgages (claims on future rent/income)
- Derivatives (claims on claims)

### 4.2 The Doubling/Tripling of Capital

Marx observed that the credit system makes "all capital seem to double itself, and sometimes treble itself":

1. Industrial capitalist has real capital (machinery, materials) worth $1M
2. Issues stocks worth $1M (fictitious)
3. Takes loan of $500K, secured by stocks (fictitious on fictitious)
4. Bank counts the loan as an asset (fictitious)

Total paper claims: $2.5M+ on $1M real capital.

### 4.3 Fictitious Capital Tensor

```python
class FictitiousCapitalStock(BaseModel):
    """Accumulated claims on future value production."""

    government_debt: Currency
    """Bonds backed by state's taxing power."""

    corporate_equity: Currency
    """Market cap of publicly traded companies."""

    corporate_debt: Currency
    """Outstanding bonds and loans to businesses."""

    household_debt: Currency
    """Mortgages, consumer credit, student loans."""

    derivatives_notional: Currency
    """Face value of derivative contracts (much larger than others)."""

    @computed_field
    def total_claims(self) -> Currency:
        """Total fictitious capital (excluding derivatives)."""
        return (
            self.government_debt +
            self.corporate_equity +
            self.corporate_debt +
            self.household_debt
        )

    def ratio_to_real(self, real_capital: Currency) -> float:
        """How many times has capital been 'doubled'?"""
        return self.total_claims / real_capital if real_capital > 0 else float('inf')
```

### 4.4 The Fictitious/Real Divergence

The ratio of fictitious to real capital is a **crisis indicator**:

```python
def financialization_index(
    fictitious: FictitiousCapitalStock,
    real_gdp: Currency,
) -> float:
    """Degree of financialization.

    Higher values indicate greater divergence between
    paper claims and real production capacity.

    Historical pattern:
    - 1929: ratio peaked before crash
    - 1980s: began secular rise
    - 2008: ratio peaked before crash
    - 2020s: ratio at all-time highs
    """
    return fictitious.total_claims / real_gdp
```

**Data sources:**
- FRED: Total credit market debt outstanding (TCMDO)
- BEA: GDP
- Federal Reserve: Financial Accounts (Z.1)
- World Bank: Stock market capitalization

---

## 5. Credit and Crisis

### 5.1 Marx on Credit Crisis

From Chapter 30:

> "In a system of production, where the entire continuity of the reproduction process rests upon credit, a crisis must obviously occur — a tremendous rush for means of payment — when credit suddenly ceases and only cash payments have validity."

The credit system:
1. **Accelerates circulation** — reduces need for actual money
2. **Enables overproduction** — expands market beyond actual purchasing power
3. **Creates fragility** — when confidence breaks, the whole edifice collapses

### 5.2 Crisis Dynamics Model

```python
class CreditState(BaseModel):
    """State of the credit system."""

    credit_expansion_rate: float
    """Year-over-year growth in total credit."""

    default_rate: float
    """Fraction of loans in default."""

    spread_to_treasuries: float
    """Risk premium over "risk-free" rate."""

    velocity_of_money: float
    """GDP / Money supply — how fast money circulates."""


class CreditCrisisIndicator(BaseModel):
    """Conditions that precede credit crisis."""

    overproduction_signal: bool
    """Inventories rising, capacity utilization falling."""

    profit_squeeze: bool
    """Profit rate falling while debt service rising."""

    liquidity_crisis: bool
    """Spread spiking, credit contracting."""

    def crisis_probability(self) -> Probability:
        """Heuristic crisis probability."""
        signals = [
            self.overproduction_signal,
            self.profit_squeeze,
            self.liquidity_crisis,
        ]
        return Probability(sum(signals) / len(signals))
```

### 5.3 The Credit Cycle and TRPF

Credit cycles interact with the tendency of the rate of profit to fall:

1. **Expansion phase**: Credit enables accumulation despite falling profit rate
2. **Peak**: Debt service exceeds profit generation capacity
3. **Crisis**: Credit contracts, revealing overaccumulation
4. **Devaluation**: Capital destroyed, clearing ground for new cycle

```python
def credit_cycle_phase(
    profit_rate: float,
    profit_rate_trend: float,  # derivative
    credit_growth: float,
    default_rate: float,
) -> CyclePhase:
    """Determine position in credit cycle."""

    if profit_rate_trend > 0 and credit_growth > 0:
        return CyclePhase.EXPANSION

    if profit_rate_trend < 0 and credit_growth > 0:
        return CyclePhase.OVEREXTENSION  # Danger zone

    if default_rate > CRISIS_THRESHOLD:
        return CyclePhase.CRISIS

    if profit_rate_trend > 0 and credit_growth < 0:
        return CyclePhase.RECOVERY

    return CyclePhase.STAGNATION
```

---

## 6. Ground Rent

### 6.1 Marx's Rent Theory

Ground rent arises from the **monopoly of landed property**. Unlike industrial profit, which arises from exploitation of labor, rent arises from control over a non-reproducible condition of production.

Two forms:

| Type | Source | Formula |
|------|--------|---------|
| **Differential Rent** | Differences in land productivity/location | Surplus profit from better land captured by landowner |
| **Absolute Rent** | Monopoly power of all landowners | Exists even on worst land because landowners won't allow use without payment |

### 6.2 Rent as Counter-Tendency to TRPF

Rent extraction is a **counter-tendency** to the falling rate of profit from the perspective of landed capital, but a **drain** on industrial profit.

```python
class RentExtraction(BaseModel):
    """Ground rent by type and sector."""

    agricultural_rent: Currency
    """Rent from farmland."""

    resource_rent: Currency
    """Rent from mining, oil/gas, etc."""

    urban_rent: Currency
    """Building site rent, commercial real estate."""

    @computed_field
    def total_rent(self) -> Currency:
        return self.agricultural_rent + self.resource_rent + self.urban_rent

    def rent_share_of_surplus(self, total_surplus: Currency) -> float:
        """What fraction of surplus value goes to landowners?"""
        return self.total_rent / total_surplus if total_surplus > 0 else 0.0
```

### 6.3 Housing and Fictitious Capital

Marx noted that building site rent exhibits "the most shameless exploitation of poverty." Housing combines:

1. **Ground rent** (location monopoly)
2. **Interest** (mortgage payments)
3. **Fictitious capital** (housing as speculative asset)

This is directly relevant to the Detroit gentrification model:

```python
class HousingValueDecomposition(BaseModel):
    """Decompose housing price into value components."""

    construction_value: Currency
    """Labor-value of the structure (c + v + s of construction)."""

    ground_rent_capitalized: Currency
    """Location rent capitalized at going interest rate."""

    speculative_premium: Currency
    """Excess of market price over (construction + capitalized rent)."""

    @computed_field
    def market_price(self) -> Currency:
        return (
            self.construction_value +
            self.ground_rent_capitalized +
            self.speculative_premium
        )

    @computed_field
    def fictitious_fraction(self) -> float:
        """How much of the price is fictitious?"""
        return (
            (self.ground_rent_capitalized + self.speculative_premium) /
            self.market_price
        )
```

**Data sources:**
- Census: Median home values, rent prices
- Zillow/Redfin: Housing price indices
- BLS: Rent of primary residence CPI component
- Construction cost indices

---

## 7. The Complete Surplus Distribution Tensor

### 7.1 Integrated Model

Combining all claims on surplus value:

```python
class SurplusValueDistribution(BaseModel):
    """Complete decomposition of surplus value distribution.

    s = p + i + r + taxes

    Where:
    - p = profit of enterprise (retained by functioning capitalists)
    - i = interest (to money-capitalists)
    - r = rent (to landowners)
    - taxes = state appropriation (for reproduction of conditions)
    """

    fips_code: str
    year: int

    # Production side (from ValueTensor4x3)
    total_surplus_produced: Currency

    # Distribution side
    profit_of_enterprise: Currency
    interest_payments: Currency
    ground_rent: Currency
    taxes_on_surplus: Currency

    @computed_field
    def distribution_complete(self) -> bool:
        """Verify accounting identity."""
        distributed = (
            self.profit_of_enterprise +
            self.interest_payments +
            self.ground_rent +
            self.taxes_on_surplus
        )
        return abs(distributed - self.total_surplus_produced) < EPSILON

    @computed_field
    def financialization_share(self) -> float:
        """Interest as share of surplus — measure of financial dominance."""
        return self.interest_payments / self.total_surplus_produced

    @computed_field
    def rentier_share(self) -> float:
        """Rent as share of surplus — measure of landed capital power."""
        return self.ground_rent / self.total_surplus_produced
```

### 7.2 Data Pipeline

```
ValueTensor4x3 (production)
    │
    ├── total_s = Σ dept.s
    │
    ▼
SurplusValueDistribution (circulation)
    │
    ├── interest_payments ◄─── FRED: Interest income data
    │                          BEA: Net interest by industry
    │
    ├── ground_rent ◄───────── BEA: Rental income of persons
    │                          Census: Aggregate rent paid
    │
    ├── taxes_on_surplus ◄──── IRS: Corporate income tax
    │                          BEA: Taxes on production
    │
    └── profit_of_enterprise = total_s - (interest + rent + taxes)
```

---

## 8. Inflation and Value

### 8.1 Marx on Money and Inflation

Marx distinguished:

1. **Commodity money** (gold): Has intrinsic labor-value
2. **Credit money** (bank notes): Promises to pay commodity money
3. **Fiat money**: State-enforced symbols with no intrinsic value

Inflation occurs when:
- Money supply grows faster than commodity production
- Credit expands beyond capacity to realize value
- Currency depreciates relative to labor-time standard

### 8.2 Real vs Nominal in the Tensor

All tensor values should be expressible in:

1. **Nominal terms**: Current dollars
2. **Real terms**: Constant dollars (inflation-adjusted)
3. **Labor-time terms**: Hours of SNLT

```python
class ValueBasis(StrEnum):
    NOMINAL = "nominal"
    REAL = "real"
    LABOR_TIME = "labor_time"


class MonetaryAdjustment(BaseModel):
    """Convert between value representations."""

    year: int

    cpi_index: float
    """Consumer Price Index (base year = 100)."""

    gdp_deflator: float
    """GDP deflator (base year = 100)."""

    snlt_per_dollar: float
    """Labor-hours per dollar of GDP.

    Computed as: Total labor hours / Nominal GDP
    """

    def nominal_to_real(self, nominal: Currency, base_year: int) -> Currency:
        """Deflate nominal to constant dollars."""
        # Would need base year CPI lookup
        ...

    def nominal_to_labor_time(self, nominal: Currency) -> float:
        """Convert dollars to labor-hours."""
        return nominal * self.snlt_per_dollar
```

**Data sources:**
- BLS: CPI, PPI
- BEA: GDP deflator
- BLS: Total nonfarm employment, average weekly hours

---

## 9. Counter-Tendencies to TRPF

Volume III identifies several counter-tendencies that offset the falling profit rate. Each can be modeled:

### 9.1 List of Counter-Tendencies

| Counter-Tendency | Mechanism | Data Source |
|------------------|-----------|-------------|
| Increasing exploitation rate | s/v rises even as s/(c+v) falls | BLS productivity vs compensation |
| Depression of wages below value | Real wages < reproduction cost | CEX vs living wage calculations |
| Cheapening of constant capital | Technology reduces c | PPI for capital goods |
| Relative surplus population | Reserve army depresses wages | BLS U-6 unemployment |
| Foreign trade | Unequal exchange, imperial rent | BEA trade data, our Φ calculation |
| Increase in stock capital | Fictitious profits boost reported returns | Financial Accounts Z.1 |

### 9.2 Counter-Tendency Index

```python
class CounterTendencyStrength(BaseModel):
    """Measure strength of TRPF counter-tendencies."""

    exploitation_rate_change: float
    """Δ(s/v) year-over-year."""

    wage_suppression: float
    """Gap between productivity growth and wage growth."""

    constant_capital_cheapening: float
    """Rate of decline in capital goods prices."""

    reserve_army_size: float
    """U-6 unemployment rate."""

    imperial_rent_flow: Currency
    """Net unequal exchange (Φ)."""

    fictitious_profit_share: float
    """Financial sector share of reported profits."""

    def net_counter_tendency(self) -> float:
        """Aggregate strength of counter-tendencies.

        Positive = counter-tendencies dominating
        Negative = TRPF tendency dominating
        """
        # Weighted sum of normalized indicators
        ...
```

---

## 10. Integration with Babylon Architecture

### 10.1 New Level 1 Tensors Required

| Tensor | Data Source | Priority |
|--------|-------------|----------|
| FictitiousCapitalStock | Fed Z.1, FRED | High |
| InterestRateState | FRED | High |
| RentExtraction | BEA rental income | Medium |
| CreditState | Fed H.8, FRED | High |
| HousingValueDecomposition | Census, Zillow | Medium (Detroit focus) |

### 10.2 Extended Hierarchy

```
Level 0: ValueTensor4x3 (production)
    │
    ├── Level 1A: Distribution Tensors
    │   ├── SurplusValueDistribution
    │   ├── InterestRateState
    │   └── RentExtraction
    │
    ├── Level 1B: Financial Tensors
    │   ├── FictitiousCapitalStock
    │   ├── CreditState
    │   └── HousingValueDecomposition
    │
    └── Level 2: Derived
        ├── FinancializationIndex = Fictitious / Real
        ├── CreditCyclePhase = f(profit_rate, credit_growth)
        └── CounterTendencyStrength = weighted(indicators)
```

### 10.3 Crisis Detection

The financial layer enables crisis prediction:

```python
def crisis_conditions(
    tensor: ValueTensor4x3,
    distribution: SurplusValueDistribution,
    credit: CreditState,
    fictitious: FictitiousCapitalStock,
) -> CrisisAssessment:
    """Evaluate structural crisis conditions.

    Marx's insight: Crisis appears as money/credit crisis
    but underlying cause is overproduction relative to
    profitable realization.
    """

    # Profit rate squeeze
    profit_rate = tensor.profit_rate
    interest_burden = distribution.interest_payments / distribution.profit_of_enterprise

    # Overaccumulation
    fictitious_ratio = fictitious.ratio_to_real(tensor.total_value)

    # Credit fragility
    credit_fragility = credit.default_rate * credit.spread_to_treasuries

    return CrisisAssessment(
        profit_squeeze=interest_burden > SQUEEZE_THRESHOLD,
        overaccumulation=fictitious_ratio > BUBBLE_THRESHOLD,
        credit_fragility=credit_fragility > FRAGILITY_THRESHOLD,
        crisis_phase=determine_phase(profit_rate, credit.credit_expansion_rate),
    )
```

---

## 11. Theoretical Summary

### 11.1 The Complete Picture

```
PRODUCTION (Volume I)
    │
    │ Labor process creates value: c + v + s
    │
    ▼
CIRCULATION (Volume II)
    │
    │ Value realizes through sale: M - C ... P ... C' - M'
    │
    ▼
DISTRIBUTION (Volume III)
    │
    │ Surplus value divides among claimants:
    │   s → profit + interest + rent + taxes
    │
    ├── Industrial capital claims profit of enterprise
    ├── Money capital claims interest
    ├── Landed capital claims rent
    └── State claims taxes
    │
    ▼
MYSTIFICATION (Trinity Formula)
    │
    │ Appears as: Capital → Interest
    │             Land → Rent
    │             Labor → Wages
    │
    │ Conceals: All value from labor, distributed by power
```

### 11.2 What This Adds to Babylon

1. **Financial layer**: Track fictitious capital accumulation and credit dynamics
2. **Rent theory**: Model housing/land markets in gentrification
3. **Crisis mechanics**: Detect structural conditions preceding rupture
4. **Counter-tendencies**: Explain why TRPF doesn't produce immediate collapse
5. **Distribution tracking**: See where surplus value actually flows

### 11.3 Connection to Imperial Rent

Volume III's analysis of interest and rent connects directly to our imperial rent framework:

- **Interest rate differentials** between core and periphery are a mechanism of unequal exchange
- **Ground rent** in the periphery (resource extraction) flows to core landowners/corporations
- **Fictitious capital** claims in the core are backed by real production in the periphery
- **Credit crises** propagate from core to periphery with amplified effects

The imperial rent calculation Φ = W_core - V_core should be understood as operating through these financial channels, not as pure commodity exchange.

---

## 12. Implementation Priorities

### Phase 1: Financial Data Infrastructure

1. Add FRED loader for interest rates, credit aggregates
2. Add Fed Z.1 Financial Accounts loader
3. Create FictitiousCapitalStock model
4. Implement financialization_index calculation

### Phase 2: Distribution Tracking

1. Integrate BEA rental income data
2. Create SurplusValueDistribution model
3. Validate: production-side s ≈ distribution-side claims

### Phase 3: Crisis Detection

1. Implement CreditState tracking
2. Create CrisisAssessment model
3. Backtest against historical crises (1929, 2008)

### Phase 4: Housing Integration (Detroit Focus)

1. Add Census/ACS housing value data
2. Create HousingValueDecomposition model
3. Track fictitious fraction of housing prices in Wayne vs Oakland County
