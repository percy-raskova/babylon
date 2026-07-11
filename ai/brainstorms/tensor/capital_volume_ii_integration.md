# Capital Volume II Integration

## The Circulation of Capital: Time, Turnover, and Reproduction

**Status**: Theoretical Framework
**Depends On**: ValueTensor4x3, Department Schemata
**Scope**: Temporal dynamics, circulation costs, realization crisis

---

## 1. Volume II Structure and Purpose

Where Volume I analyzes **production** (extraction of surplus value) and Volume III analyzes **distribution** (division of surplus value), Volume II analyzes **circulation** — the movement of capital through its metamorphoses and the conditions for its reproduction.

| Part | Topic | Babylon Integration |
|------|-------|---------------------|
| I | Metamorphoses of Capital (Circuits) | Circuit tracking, state transitions |
| II | Turnover of Capital | Temporal dynamics, fixed vs circulating |
| III | Reproduction of Total Social Capital | **Already have**: Department schemata |

Key insight: **Capital is not a thing but a process** — a continuous flow of value through different forms. Volume II provides the temporal and circulatory dimensions missing from our static tensor.

---

## 2. The Three Circuits of Capital

### 2.1 The Basic Formula

Capital exists in three forms, cycling continuously:

```
M → C{LP, MP} ... P ... C' → M'
```

Where:
- **M** = Money capital (liquidity, purchasing power)
- **C** = Commodity capital (means of production + labor power)
- **LP** = Labor power
- **MP** = Means of production
- **P** = Productive capital (actually producing)
- **C'** = Commodity capital with surplus value embodied
- **M'** = Money capital with surplus value realized

### 2.2 Three Circuit Perspectives

The same process viewed from different starting points:

| Circuit | Formula | Focus |
|---------|---------|-------|
| Money Capital | M → C ... P ... C' → M' | Investment and return |
| Productive Capital | P ... C' → M' → C ... P | Continuous production |
| Commodity Capital | C' → M' → C ... P ... C' | Realization and reproduction |

Each reveals different dynamics:
- **Money circuit**: Emphasizes valorization (M → M')
- **Productive circuit**: Emphasizes continuity of production
- **Commodity circuit**: Emphasizes social reproduction, interdependence of capitals

### 2.3 Tensor Representation

```python
class CapitalForm(StrEnum):
    """The three forms capital takes in circulation."""
    MONEY = "money"           # M: Liquidity
    PRODUCTIVE = "productive" # P: Engaged in production
    COMMODITY = "commodity"   # C: Awaiting sale


class CircuitState(BaseModel):
    """State of capital in the circuit at a given moment."""

    entity_id: str
    tick: int

    # Distribution across forms
    money_capital: Currency
    """M: Cash, deposits, receivables."""

    productive_capital: Currency
    """P: Fixed capital + working capital in production."""

    commodity_capital: Currency
    """C: Finished goods awaiting sale."""

    # Breakdown of productive capital
    fixed_capital: Currency
    """Durable means of production (machinery, buildings)."""

    circulating_capital: Currency
    """Raw materials + labor power (consumed each cycle)."""

    @computed_field
    def total_capital(self) -> Currency:
        return self.money_capital + self.productive_capital + self.commodity_capital

    @computed_field
    def liquidity_ratio(self) -> float:
        """Fraction in money form — ability to respond to opportunities/crises."""
        return self.money_capital / self.total_capital if self.total_capital > 0 else 0.0

    @computed_field
    def commodity_overhang(self) -> float:
        """Fraction stuck in commodity form — realization problem indicator."""
        return self.commodity_capital / self.total_capital if self.total_capital > 0 else 0.0
```

---

## 3. Time Decomposition

### 3.1 Production Time vs Working Time

Production time is NOT the same as working time:

```
Production Time = Working Time + Non-Working Production Time
```

Where non-working production time includes:
- **Natural processes**: Fermentation, drying, aging (wine, cheese, lumber)
- **Interruptions**: Night shifts, maintenance downtime
- **Stock time**: Raw materials waiting to be processed

Example from Marx: American shoe-last manufacturing requires 18 months of wood drying before any labor can begin.

### 3.2 Circulation Time

```
Circulation Time = Purchase Time + Sale Time
```

- **Purchase time** (M → C): Finding and acquiring means of production and labor
- **Sale time** (C' → M'): Finding buyers, completing transactions

### 3.3 Total Turnover Time

```
Turnover Time = Production Time + Circulation Time
```

This is the complete cycle: M → ... → M'

### 3.4 Temporal Tensor

```python
class TurnoverProfile(BaseModel):
    """Temporal characteristics of capital circulation."""

    entity_id: str
    industry_code: str

    # Production phase
    working_period_days: int
    """Days of actual labor in production cycle."""

    non_working_production_days: int
    """Days capital sits in production without labor (drying, aging, etc)."""

    # Circulation phase
    purchase_time_days: int
    """Average days to acquire inputs."""

    sale_time_days: int
    """Average days to sell output."""

    @computed_field
    def production_time(self) -> int:
        return self.working_period_days + self.non_working_production_days

    @computed_field
    def circulation_time(self) -> int:
        return self.purchase_time_days + self.sale_time_days

    @computed_field
    def turnover_time(self) -> int:
        """Complete circuit duration."""
        return self.production_time + self.circulation_time

    @computed_field
    def turnovers_per_year(self) -> float:
        """How many times capital completes the circuit annually."""
        return 365 / self.turnover_time if self.turnover_time > 0 else 0.0

    @computed_field
    def production_ratio(self) -> float:
        """Fraction of time in productive phase."""
        return self.production_time / self.turnover_time


class IndustryTurnoverData(BaseModel):
    """Industry-level turnover characteristics from federal data."""

    naics_code: str
    year: int

    # From Census Annual Survey of Manufactures
    inventory_to_sales_ratio: float
    """Days of inventory on hand — proxy for sale time."""

    # From BEA Fixed Assets
    avg_equipment_life_years: float
    """Average depreciation period — fixed capital turnover."""

    # Derived
    working_capital_turnover: float
    """Sales / Working capital — circulating capital velocity."""
```

**Data sources:**
- Census Annual Survey of Manufactures: Inventory/sales ratios
- BEA Fixed Asset Tables: Depreciation schedules by industry
- BLS Productivity: Output per hour (working time efficiency)

---

## 4. Fixed vs Circulating Capital

### 4.1 The Distinction

This is NOT the same as constant vs variable capital:

| Distinction | Basis | Components |
|-------------|-------|------------|
| c vs v | Source of value | c = dead labor, v = living labor |
| Fixed vs Circulating | Mode of turnover | Fixed = gradual transfer, Circulating = complete transfer |

The cross-classification:

|  | Constant (c) | Variable (v) |
|--|--------------|--------------|
| **Fixed** | Machinery, buildings | — |
| **Circulating** | Raw materials, fuel | Wages |

Variable capital (v) is ALWAYS circulating — labor power is fully consumed each production cycle.

### 4.2 Fixed Capital Dynamics

Fixed capital transfers value gradually through **depreciation**:

```python
class FixedCapitalItem(BaseModel):
    """A durable means of production."""

    item_id: str
    category: str  # machinery, buildings, vehicles, etc.

    initial_value: Currency
    """Original cost."""

    service_life_years: float
    """Expected productive lifetime."""

    current_age_years: float
    """Time since acquisition."""

    @computed_field
    def annual_depreciation(self) -> Currency:
        """Value transferred to product per year (straight-line)."""
        return self.initial_value / self.service_life_years

    @computed_field
    def remaining_value(self) -> Currency:
        """Book value remaining."""
        depreciated = self.annual_depreciation * self.current_age_years
        return max(Currency(0), self.initial_value - depreciated)

    @computed_field
    def depreciation_fund_required(self) -> Currency:
        """Cash that should be accumulated for replacement."""
        return self.initial_value - self.remaining_value


class MoralDepreciation(BaseModel):
    """Value loss from obsolescence, not physical wear."""

    item_id: str

    physical_remaining_life: float
    """Years of physical functionality left."""

    economic_remaining_life: float
    """Years before replacement is economically necessary."""

    @computed_field
    def obsolescence_factor(self) -> float:
        """How much faster economic depreciation vs physical."""
        if self.physical_remaining_life <= 0:
            return 1.0
        return self.economic_remaining_life / self.physical_remaining_life
```

Marx emphasized **moral depreciation** — machinery becomes obsolete not because it wears out but because better machinery exists. This accelerates with technological change.

### 4.3 The Depreciation Fund Problem

Fixed capital creates a temporal mismatch:
1. Value transfers continuously (each production cycle)
2. Replacement happens discretely (when machine wears out)

This creates **latent money capital** — depreciation funds accumulating as hoards waiting for replacement. This is a material basis for the credit system and business cycles.

```python
class DepreciationFundState(BaseModel):
    """Accumulated depreciation funds across an economy."""

    fips_code: str
    year: int

    total_fixed_capital: Currency
    """Gross value of fixed capital stock."""

    accumulated_depreciation: Currency
    """Total depreciation fund accumulated."""

    annual_depreciation_flow: Currency
    """Current year's depreciation charges."""

    replacement_expenditure: Currency
    """Actual fixed capital purchases this year."""

    @computed_field
    def fund_adequacy(self) -> float:
        """Is the fund sufficient for needed replacements?"""
        # Rough proxy: depreciation fund vs annual depreciation
        return self.accumulated_depreciation / self.annual_depreciation_flow

    @computed_field
    def replacement_cycle_position(self) -> str:
        """Where in the replacement cycle is this economy?"""
        ratio = self.replacement_expenditure / self.annual_depreciation_flow
        if ratio > 1.5:
            return "INVESTMENT_BOOM"
        elif ratio > 1.0:
            return "EXPANSION"
        elif ratio > 0.7:
            return "MAINTENANCE"
        else:
            return "DISINVESTMENT"
```

**Data sources:**
- BEA Fixed Asset Tables: Capital stock, depreciation by industry
- Census Capital Expenditure Survey
- Federal Reserve: Capacity utilization

---

## 5. Costs of Circulation

### 5.1 Marx's Classification

| Category | Value-Creating? | Examples |
|----------|-----------------|----------|
| **Pure circulation costs** | No | Buying/selling labor, bookkeeping, advertising |
| **Storage costs** | Partially | Warehousing (if preserving use-value: yes) |
| **Transportation** | Yes | Shipping, freight — continues production |

Key insight: **Transportation is productive labor** — it produces a use-value (change of location) that adds to the commodity's value. Shipping a commodity from factory to market is part of production, not just circulation.

### 5.2 Pure Circulation Costs (Unproductive)

These costs are necessary for capitalism but create no value:

```python
class PureCirculationCosts(BaseModel):
    """Costs that do not add value but are necessary for exchange."""

    entity_id: str
    period: str

    # Labor costs
    sales_labor: Currency
    """Wages of salespeople, cashiers, etc."""

    accounting_labor: Currency
    """Wages of bookkeepers, accountants."""

    marketing_labor: Currency
    """Wages of advertising, branding personnel."""

    # Material costs
    sales_facilities: Currency
    """Depreciation of retail space, showrooms."""

    advertising_materials: Currency
    """Ad spend, promotional materials."""

    transaction_costs: Currency
    """Payment processing, banking fees."""

    @computed_field
    def total_pure_circulation(self) -> Currency:
        return (
            self.sales_labor +
            self.accounting_labor +
            self.marketing_labor +
            self.sales_facilities +
            self.advertising_materials +
            self.transaction_costs
        )

    def circulation_burden(self, total_revenue: Currency) -> float:
        """What fraction of revenue goes to pure circulation?"""
        return self.total_pure_circulation / total_revenue


class CirculationLaborClassification(BaseModel):
    """Classify labor as productive or unproductive of value."""

    occupation_code: str
    description: str

    is_productive: bool
    """Does this labor create value?"""

    rationale: str
    """Why classified this way."""

    # Examples:
    # Production worker: productive (transforms materials)
    # Truck driver: productive (changes location = use-value)
    # Cashier: unproductive (facilitates exchange only)
    # Warehouse worker: partially (preserving use-value = productive)
    # Advertising creative: unproductive (creates no use-value)
    # Security guard: unproductive (protects property relations)
```

### 5.3 Transportation as Productive

Transportation is "production continued in circulation":

```python
class TransportationValue(BaseModel):
    """Value added by transportation industry."""

    shipment_id: str

    commodity_value_at_origin: Currency
    """Value of goods before transport."""

    transport_labor_hours: float
    """Labor time in transportation."""

    transport_constant_capital: Currency
    """Vehicles, fuel, infrastructure depreciation."""

    transport_variable_capital: Currency
    """Wages of transport workers."""

    transport_surplus_value: Currency
    """Surplus extracted from transport labor."""

    @computed_field
    def value_added_by_transport(self) -> Currency:
        """Transportation adds c + v + s to commodity value."""
        return (
            self.transport_constant_capital +
            self.transport_variable_capital +
            self.transport_surplus_value
        )

    @computed_field
    def commodity_value_at_destination(self) -> Currency:
        """Value after transport."""
        return self.commodity_value_at_origin + self.value_added_by_transport

    @computed_field
    def transport_value_ratio(self) -> float:
        """Transport value as fraction of final value."""
        return self.value_added_by_transport / self.commodity_value_at_destination
```

This is crucial for understanding imperial rent: **transport costs mediate core-periphery value flows**. Cheaper transport for core imports than periphery exports is a mechanism of unequal exchange.

**Data sources:**
- BTS Freight Analysis Framework: Freight costs by mode, origin-destination
- BLS: Employment in transportation sector
- Surface Transportation Board: Rail rates

---

## 6. Storage and Inventory

### 6.1 Normal vs Abnormal Stock

Marx distinguishes:
- **Productive stock**: Raw materials waiting to enter production (necessary)
- **Commodity stock**: Finished goods awaiting sale (can be speculative)

Stock formation can be:
- **Normal**: Buffer stock needed for continuous production/circulation
- **Abnormal**: Unsold inventory due to overproduction (crisis indicator)

### 6.2 Inventory Tensor

```python
class InventoryState(BaseModel):
    """Stock of commodities in various stages."""

    entity_id: str
    tick: int

    # Productive stock (input side)
    raw_materials: Currency
    """Stock of unprocessed inputs."""

    work_in_progress: Currency
    """Partially completed production."""

    # Commodity stock (output side)
    finished_goods: Currency
    """Completed products awaiting sale."""

    # Metrics
    days_inventory_raw: float
    """Days of production covered by raw materials."""

    days_inventory_finished: float
    """Days of sales in finished goods."""

    @computed_field
    def total_inventory(self) -> Currency:
        return self.raw_materials + self.work_in_progress + self.finished_goods

    @computed_field
    def inventory_problem(self) -> str:
        """Diagnose inventory situation."""
        if self.days_inventory_finished > 60:
            return "OVERPRODUCTION"  # Can't sell
        elif self.days_inventory_raw < 7:
            return "SUPPLY_CRISIS"  # Can't produce
        else:
            return "NORMAL"


def inventory_to_realization_crisis(
    inventory_trend: list[InventoryState],
    production_trend: list[Currency],
) -> bool:
    """Rising inventory + flat/falling production = realization crisis."""

    inventory_rising = inventory_trend[-1].finished_goods > inventory_trend[0].finished_goods
    production_falling = production_trend[-1] <= production_trend[0]

    return inventory_rising and production_falling
```

**Data sources:**
- Census Quarterly Financial Report: Inventory levels by sector
- Census M3 Survey: Manufacturers' shipments, inventories, orders
- ISM Manufacturing Index: Inventory component

---

## 7. Annual Rate of Surplus Value

### 7.1 The Turnover Effect

A crucial Volume II discovery: **faster turnover increases the annual rate of surplus value** even with the same rate of exploitation per cycle.

```
Annual Rate of s/v = (s/v per cycle) × (turnovers per year)
```

Example:
- Rate of surplus value: 100% (s/v = 1)
- Turnover time: 2 months → 6 turnovers/year
- Annual s/v = 100% × 6 = 600%

If turnover time = 6 months → 2 turnovers/year
- Annual s/v = 100% × 2 = 200%

Same exploitation rate, different annual returns.

### 7.2 Implementation

```python
class AnnualSurplusValue(BaseModel):
    """Annual surplus value accounting for turnover."""

    entity_id: str
    year: int

    # Per-cycle values
    variable_capital_advanced: Currency
    """v: wages for one production cycle."""

    surplus_value_per_cycle: Currency
    """s: surplus extracted per cycle."""

    turnover_time_days: int
    """Days per complete circuit."""

    @computed_field
    def rate_of_surplus_value(self) -> float:
        """s/v: exploitation rate per cycle."""
        return self.surplus_value_per_cycle / self.variable_capital_advanced

    @computed_field
    def turnovers_per_year(self) -> float:
        return 365 / self.turnover_time_days

    @computed_field
    def annual_surplus_value(self) -> Currency:
        """Total surplus extracted over the year."""
        return self.surplus_value_per_cycle * self.turnovers_per_year

    @computed_field
    def annual_rate_of_surplus_value(self) -> float:
        """s'/v where s' = annual surplus."""
        return self.rate_of_surplus_value * self.turnovers_per_year


def compare_turnover_advantage(
    fast_turner: AnnualSurplusValue,
    slow_turner: AnnualSurplusValue,
) -> float:
    """How much more surplus does faster turnover extract?"""
    return (
        fast_turner.annual_surplus_value /
        slow_turner.annual_surplus_value
    )
```

This explains why capitalism relentlessly accelerates: faster turnover = more surplus from the same capital advanced.

---

## 8. The Circuit Formulas

### 8.1 Simple Commodity Circulation

Pre-capitalist exchange:
```
C → M → C  (Commodity → Money → Commodity)
```

Purpose: Obtain use-values. Money is means, not end.

### 8.2 Capital Circulation

Capitalist exchange:
```
M → C → M'  (Money → Commodity → More Money)
```

Purpose: Self-expansion of value. Use-value is means, not end.

### 8.3 Interest-Bearing Capital (from Volume III)

The most fetishized form:
```
M → M'  (Money → More Money)
```

Production disappears entirely from view.

### 8.4 Circuit Type Tracking

```python
class CircuitType(StrEnum):
    """Type of economic circuit."""

    SIMPLE_COMMODITY = "C-M-C"      # Use-value oriented
    INDUSTRIAL_CAPITAL = "M-C-M'"   # Surplus through production
    COMMERCIAL_CAPITAL = "M-C-M'"   # Surplus through exchange markup
    INTEREST_BEARING = "M-M'"       # Pure money lending
    FICTITIOUS = "M-M''"            # Claims on claims


class EntityCircuitProfile(BaseModel):
    """What type of circuit does an economic entity participate in?"""

    entity_id: str

    primary_circuit: CircuitType
    """Dominant mode of value extraction."""

    # Income composition revealing circuit type
    production_income_share: float
    """Income from industrial production."""

    commercial_income_share: float
    """Income from buying cheap / selling dear."""

    interest_income_share: float
    """Income from lending."""

    rent_income_share: float
    """Income from property ownership."""

    wage_income_share: float
    """Income from selling labor power."""

    def classify(self) -> CircuitType:
        """Determine primary circuit from income sources."""
        if self.wage_income_share > 0.5:
            return CircuitType.SIMPLE_COMMODITY  # Worker
        elif self.production_income_share > 0.3:
            return CircuitType.INDUSTRIAL_CAPITAL
        elif self.interest_income_share > 0.3:
            return CircuitType.INTEREST_BEARING
        elif self.rent_income_share > 0.3:
            return CircuitType.INTEREST_BEARING  # Similar logic
        else:
            return CircuitType.COMMERCIAL_CAPITAL
```

---

## 9. Conditions for Uninterrupted Reproduction

### 9.1 The Continuity Problem

For capital to flow continuously through M → C → P → C' → M' → ..., each phase must find its conditions ready:

1. **M → C**: Money must find commodities (LP, MP) available
2. **C ... P**: Production must have continuous inputs
3. **P ... C'**: Production must complete without disruption
4. **C' → M'**: Commodities must find buyers with money

Any break in this chain = crisis.

### 9.2 Reproduction Conditions

```python
class ReproductionConditions(BaseModel):
    """Conditions required for uninterrupted reproduction."""

    fips_code: str
    year: int

    # M → C conditions
    labor_supply_adequate: bool
    """Is there available labor power to hire?"""

    means_production_available: bool
    """Are required inputs in the market?"""

    credit_available: bool
    """Can capital be borrowed if needed?"""

    # P conditions
    capacity_utilized: float
    """What fraction of productive capacity is in use?"""

    input_supply_stable: bool
    """Are supply chains functioning?"""

    # C' → M' conditions
    effective_demand_adequate: bool
    """Can produced commodities be sold?"""

    payment_system_functioning: bool
    """Is money circulating normally?"""

    @computed_field
    def reproduction_secure(self) -> bool:
        """Are all conditions met?"""
        return all([
            self.labor_supply_adequate,
            self.means_production_available,
            self.input_supply_stable,
            self.effective_demand_adequate,
            self.payment_system_functioning,
        ])

    @computed_field
    def crisis_vulnerability(self) -> list[str]:
        """Which conditions are failing?"""
        vulnerabilities = []
        if not self.labor_supply_adequate:
            vulnerabilities.append("LABOR_SHORTAGE")
        if not self.means_production_available:
            vulnerabilities.append("SUPPLY_CHAIN_CRISIS")
        if not self.effective_demand_adequate:
            vulnerabilities.append("REALIZATION_CRISIS")
        if not self.payment_system_functioning:
            vulnerabilities.append("MONETARY_CRISIS")
        return vulnerabilities
```

---

## 10. Integration with Department Schemata

### 10.1 Connection to Existing Model

We already have Departments I, II, III. Volume II adds:

1. **Inter-departmental flows**: How does Department I's output become II's input?
2. **Temporal coordination**: Do departments produce at compatible rates?
3. **Proportionality conditions**: What ratios must hold for balanced reproduction?

### 10.2 Simple Reproduction Conditions

For the economy to reproduce at the same scale:

```
I(v + s) = IIc
```

Department I's wages + surplus must equal Department II's constant capital needs.

```python
def check_simple_reproduction(
    dept_i: DepartmentRow,
    dept_ii: DepartmentRow,
) -> ReproductionBalance:
    """Check if simple reproduction conditions hold."""

    i_output_for_ii = dept_i.v + dept_i.s  # What I sells to II
    ii_demand_from_i = dept_ii.c           # What II needs from I

    gap = i_output_for_ii - ii_demand_from_i

    return ReproductionBalance(
        condition_met=abs(gap) < TOLERANCE,
        gap=gap,
        interpretation="OVERPRODUCTION_DEPT_I" if gap > 0 else "UNDERPRODUCTION_DEPT_I",
    )
```

### 10.3 Extended Reproduction (Accumulation)

For growth, surplus must be partly reinvested:

```
s = s_consumed + s_accumulated
s_accumulated = Δc + Δv
```

The accumulation rate determines growth trajectory.

### 10.4 Adding Department III

Reproductive labor complicates the schema because it produces labor power, not commodities for sale:

```python
def extended_reproduction_with_dept_iii(
    dept_i: DepartmentRow,   # Means of production
    dept_ii: DepartmentRow,  # Means of consumption
    dept_iii: DepartmentRow, # Reproduction of labor power
) -> ReproductionAnalysis:
    """
    Extended reproduction accounting for reproductive labor.

    Key insight: Dept III produces labor power that all departments need,
    but this "product" doesn't circulate as a commodity in the same way.
    The value of labor power reproduction constrains v in all departments.
    """

    # Total labor power needed
    total_v = dept_i.v + dept_ii.v + dept_iii.v

    # Dept III must produce enough to reproduce all workers
    reproduction_capacity = dept_iii.c + dept_iii.v + dept_iii.s

    # Gap reveals exploitation of reproductive labor
    reproduction_gap = total_v - reproduction_capacity

    return ReproductionAnalysis(
        labor_power_demand=total_v,
        reproduction_capacity=reproduction_capacity,
        gap=reproduction_gap,
        sustainability=reproduction_gap <= 0,
    )
```

---

## 11. Crisis Tendencies in Volume II

### 11.1 Types of Crisis

Volume II reveals crisis tendencies distinct from TRPF:

| Crisis Type | Mechanism | Indicator |
|-------------|-----------|-----------|
| **Realization crisis** | C' → M' fails; can't sell | Rising inventories |
| **Disproportionality** | Departments out of balance | Sectoral imbalances |
| **Turnover disruption** | Circuit interrupted | Working capital shortage |
| **Fixed capital crisis** | Replacement wave | Investment surge/collapse |

### 11.2 Realization Crisis Model

```python
class RealizationCrisis(BaseModel):
    """Crisis arising from inability to sell produced commodities."""

    fips_code: str
    year: int

    # Production side
    commodity_value_produced: Currency
    """Total value of commodities produced."""

    # Circulation side
    commodity_value_realized: Currency
    """Value actually sold and converted to money."""

    @computed_field
    def realization_gap(self) -> Currency:
        """Value produced but not realized."""
        return self.commodity_value_produced - self.commodity_value_realized

    @computed_field
    def realization_rate(self) -> float:
        """What fraction of produced value was realized?"""
        return self.commodity_value_realized / self.commodity_value_produced

    @computed_field
    def crisis_severity(self) -> str:
        rate = self.realization_rate
        if rate > 0.95:
            return "NORMAL"
        elif rate > 0.85:
            return "MILD_SLOWDOWN"
        elif rate > 0.70:
            return "RECESSION"
        else:
            return "CRISIS"
```

### 11.3 Disproportionality Crisis

```python
class DisproportionalityCrisis(BaseModel):
    """Crisis from imbalance between departments."""

    year: int

    # Department outputs
    dept_i_output: Currency
    dept_ii_output: Currency

    # Required proportions
    dept_i_share_required: float
    dept_ii_share_required: float

    @computed_field
    def actual_i_share(self) -> float:
        total = self.dept_i_output + self.dept_ii_output
        return self.dept_i_output / total

    @computed_field
    def imbalance(self) -> float:
        """How far from required proportions?"""
        return abs(self.actual_i_share - self.dept_i_share_required)

    @computed_field
    def imbalance_direction(self) -> str:
        if self.actual_i_share > self.dept_i_share_required:
            return "OVERPRODUCTION_MEANS_PRODUCTION"
        else:
            return "OVERPRODUCTION_CONSUMPTION_GOODS"
```

---

## 12. Data Sources and Implementation

### 12.1 Turnover Data

| Data Need | Federal Source | Frequency |
|-----------|----------------|-----------|
| Inventory levels | Census M3, QFR | Monthly/Quarterly |
| Inventory/sales ratios | Census | Monthly |
| Fixed capital stock | BEA Fixed Assets | Annual |
| Depreciation rates | BEA | Annual |
| Capacity utilization | Federal Reserve | Monthly |
| Transport costs | BTS FAF | Annual |

### 12.2 New Loaders Required

```
src/babylon/data/
├── census/
│   ├── m3_loader.py          # Manufacturers' inventories
│   └── qfr_loader.py         # Quarterly Financial Report
├── bea/
│   └── fixed_assets_loader.py # Capital stock, depreciation
├── fed/
│   └── capacity_loader.py     # Capacity utilization
└── bts/
    └── faf_loader.py          # Freight costs (already planned)
```

### 12.3 Schema Extensions

```sql
-- Turnover profiles by industry
CREATE TABLE industry_turnover (
    naics_code TEXT,
    year INTEGER,
    avg_inventory_days REAL,
    working_capital_turnover REAL,
    fixed_capital_life_years REAL,
    PRIMARY KEY (naics_code, year)
);

-- Circulation costs breakdown
CREATE TABLE circulation_costs (
    fips_code TEXT,
    naics_code TEXT,
    year INTEGER,
    sales_labor Currency,
    transport_cost Currency,
    storage_cost Currency,
    advertising_cost Currency,
    PRIMARY KEY (fips_code, naics_code, year)
);

-- Fixed capital state
CREATE TABLE fixed_capital_state (
    fips_code TEXT,
    year INTEGER,
    gross_stock Currency,
    accumulated_depreciation Currency,
    net_stock Currency,
    current_year_depreciation Currency,
    investment_expenditure Currency,
    PRIMARY KEY (fips_code, year)
);
```

---

## 13. Integration with Babylon Architecture

### 13.1 Temporal Dimension

Volume II adds **time** as a first-class dimension:

```python
class TemporalValueTensor(BaseModel):
    """ValueTensor extended with temporal dynamics."""

    # Spatial
    fips_code: str

    # Temporal
    tick: int
    turnover_phase: int  # Which cycle we're in

    # Value components (from Volume I)
    c: Currency
    v: Currency
    s: Currency

    # Turnover components (from Volume II)
    fixed_c: Currency      # Portion of c that is fixed
    circulating_c: Currency # Portion of c that is circulating
    turnover_time: int     # Days per circuit

    # Circuit state
    current_form: CapitalForm
    days_in_current_form: int

    @computed_field
    def annual_surplus(self) -> Currency:
        """s adjusted for turnover."""
        turnovers = 365 / self.turnover_time
        return self.s * turnovers
```

### 13.2 Simulation Implications

1. **Tick granularity**: Must be fine enough to capture circuit phases
2. **State transitions**: Capital moves between M, P, C forms
3. **Inventory tracking**: Stock levels affect realization
4. **Depreciation flows**: Fixed capital decays, accumulates fund
5. **Transport costs**: Spatial flows have value implications

### 13.3 Crisis Detection

```python
def detect_circulation_crisis(
    circuit_state: CircuitState,
    turnover: TurnoverProfile,
    inventory: InventoryState,
    reproduction: ReproductionConditions,
) -> CrisisAssessment:
    """
    Detect Volume II-type crisis conditions.
    """

    # Realization problem
    realization_crisis = inventory.commodity_overhang > 0.3

    # Turnover disruption
    turnover_crisis = (
        circuit_state.liquidity_ratio < 0.1 and
        turnover.circulation_time > turnover.production_time
    )

    # Reproduction failure
    reproduction_crisis = not reproduction.reproduction_secure

    return CrisisAssessment(
        realization_crisis=realization_crisis,
        turnover_crisis=turnover_crisis,
        reproduction_crisis=reproduction_crisis,
        vulnerabilities=reproduction.crisis_vulnerability,
        recommended_action=determine_response(
            realization_crisis,
            turnover_crisis,
            reproduction_crisis,
        ),
    )
```

---

## 14. Summary: What Volume II Adds

| Concept | Theoretical Contribution | Simulation Implementation |
|---------|-------------------------|---------------------------|
| **Circuit M-C-P-C'-M'** | Capital as process, not thing | State machine tracking form transitions |
| **Turnover time** | Speed matters for accumulation | Temporal granularity in tick system |
| **Fixed vs circulating** | Different capital components have different temporalities | Separate tracking, depreciation fund |
| **Circulation costs** | Necessary but unproductive labor | Distinguish productive/unproductive in employment |
| **Transportation** | Production in circulation | Value-adding spatial flows |
| **Realization** | Production ≠ sale | Inventory tracking, demand modeling |
| **Reproduction schema** | Inter-departmental coordination | Balance conditions between Depts I, II, III |
| **Crisis tendencies** | Multiple crisis mechanisms | Early warning indicators |

Volume II transforms Babylon from a static value snapshot to a dynamic circulation model with temporal structure, crisis detection, and reproduction conditions.
