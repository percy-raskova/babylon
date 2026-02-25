# Data Model: Capital Volume II Integration

**Feature**: 023-capital-volume-ii
**Date**: 2026-02-25
**Depends On**: ValueTensor4x3 (Feature 011), CrisisState (Feature 018)

## Entity Relationship Overview

```
ValueTensor4x3 (existing)
├── dept_I: DepartmentRow (c, v, s)
├── dept_IIa: DepartmentRow
├── dept_IIb: DepartmentRow
└── dept_III: DepartmentRow
        │
        ▼ (consumed by)
┌─────────────────────────┐     ┌──────────────────────┐
│   ReproductionChecker   │────▶│  ReproductionBalance  │
│ (simple + extended)     │     │  ReproductionAnalysis │
└─────────────────────────┘     └──────────────────────┘

CapitalStockCalculator (existing)
        │
        ▼ (K used by)
┌─────────────────────────┐
│ FixedCirculatingDecomposer │
│ (splits c into fixed/circ) │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐     ┌──────────────────────┐
│    DepreciationTracker   │────▶│ DepreciationFundState │
│ (fund accumulation)      │     │ MoralDepreciation     │
└─────────────────────────┘     └──────────────────────┘

TurnoverProfile (per-industry)
        │
        ▼ (drives timing)
┌─────────────────────────┐     ┌──────────────────────┐
│      CircuitState        │────▶│ AnnualSurplusValue   │
│ (M, P, C distribution)  │     │ (turnover-amplified)  │
└─────────────────────────┘     └──────────────────────┘

InventoryState (per-entity, per-tick)
        │
        ▼ (feeds)
┌─────────────────────────┐     ┌──────────────────────┐
│ RealizationCrisisChecker │────▶│   RealizationCrisis  │
│ (trend detection)        │     │ DisproportionalityCrisis │
└─────────────────────────┘     └──────────────────────┘

All crisis signals ──▶ CirculationCrisisAssessment
```

## Entities

### 1. CapitalForm (Enum)

The three forms capital takes in circulation.

| Value | Meaning | Marx Symbol |
|-------|---------|-------------|
| `MONEY` | Liquidity, purchasing power | M |
| `PRODUCTIVE` | Engaged in production | P |
| `COMMODITY` | Finished goods awaiting sale | C |

**Location**: `src/babylon/economics/circulation/types.py`
**Pattern**: `StrEnum` (consistent with `CrisisPhase`)

### 2. CircuitState (Frozen Model)

Distribution of an entity's capital across the three forms at a given tick.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `fips_code` | `str` | 5-digit | County identifier |
| `year` | `int` | >= 2010 | Data year |
| `money_capital` | `Currency` | >= 0 | M: cash, deposits, receivables |
| `productive_capital` | `Currency` | >= 0 | P: fixed + working capital in production |
| `commodity_capital` | `Currency` | >= 0 | C: finished goods awaiting sale |
| `fixed_capital` | `Currency` | >= 0 | Durable means of production subset of P |
| `circulating_capital` | `Currency` | >= 0 | Raw materials + labor power subset of P |

**Computed fields**:
- `total_capital`: M + P + C
- `liquidity_ratio`: M / total (0.0 if total = 0)
- `commodity_overhang`: C / total (0.0 if total = 0)

**Validation**: `productive_capital >= fixed_capital + circulating_capital` (or equal, allowing rounding)

**Relationships**: Composed into `CountyEconomicState` as a field with factory default.

### 3. TurnoverProfile (Frozen Model)

Temporal characteristics of capital circulation for an industry.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `naics_code` | `str` | 2-6 digit | Industry code |
| `working_period_days` | `int` | > 0 | Days of actual labor per cycle |
| `non_working_production_days` | `int` | >= 0 | Drying, aging, etc. |
| `purchase_time_days` | `int` | >= 0 | Days to acquire inputs |
| `sale_time_days` | `int` | >= 0 | Days to sell output |
| `fixed_capital_ratio` | `float` | [0, 1] | Fraction of c that is fixed |

**Computed fields**:
- `production_time`: working_period + non_working_production
- `circulation_time`: purchase_time + sale_time
- `turnover_time`: production_time + circulation_time
- `turnovers_per_year`: 365 / turnover_time (0.0 if turnover_time = 0)
- `production_ratio`: production_time / turnover_time

**Relationships**: Referenced by CircuitState for transition timing. Keyed by NAICS code, maps through existing DepartmentMapper infrastructure.

### 4. AnnualSurplusValue (Frozen Model)

Annual surplus value accounting for turnover speed.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `fips_code` | `str` | 5-digit | County identifier |
| `year` | `int` | >= 2010 | Data year |
| `variable_capital_advanced` | `Currency` | > 0 | v per production cycle |
| `surplus_value_per_cycle` | `Currency` | >= 0 | s per cycle |
| `turnover_time_days` | `int` | > 0 | Days per complete circuit |

**Computed fields**:
- `rate_of_surplus_value`: s / v (per cycle)
- `turnovers_per_year`: 365 / turnover_time_days
- `annual_surplus_value`: s * turnovers_per_year
- `annual_rate_of_surplus_value`: (s/v) * turnovers_per_year

### 5. FixedCapitalItem (Frozen Model)

A durable means of production with per-item depreciation tracking. Used for FR-009 (straight-line depreciation) and US3 acceptance scenarios 1-2.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `item_id` | `str` | non-empty | Unique identifier |
| `category` | `str` | non-empty | machinery, buildings, vehicles, etc. |
| `initial_value` | `Currency` | > 0 | Original cost |
| `service_life_years` | `float` | > 0 | Expected productive lifetime |
| `current_age_years` | `float` | >= 0 | Time since acquisition |

**Computed fields**:
- `annual_depreciation`: initial_value / service_life_years (straight-line)
- `remaining_value`: max(0, initial_value - annual_depreciation * current_age_years)
- `depreciation_fund_required`: initial_value - remaining_value

**Validation**: `current_age_years <= service_life_years` (fully depreciated items have remaining_value = 0)

### 6. DepreciationFundState (Frozen Model)

Economy-level tracking of fixed capital depreciation and replacement.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `fips_code` | `str` | 5-digit | County identifier |
| `year` | `int` | >= 2010 | Data year |
| `total_fixed_capital` | `Currency` | >= 0 | Gross value of fixed capital stock |
| `accumulated_depreciation` | `Currency` | >= 0 | Total depreciation fund |
| `annual_depreciation_flow` | `Currency` | > 0 | Current year's depreciation charges |
| `replacement_expenditure` | `Currency` | >= 0 | Actual fixed capital purchases |

**Computed fields**:
- `fund_adequacy`: accumulated / annual_flow
- `replacement_cycle_position`: str enum based on replacement/annual_flow ratio

**State transitions for replacement_cycle_position**:
- ratio > 1.5 → `INVESTMENT_BOOM`
- ratio > 1.0 → `EXPANSION`
- ratio > 0.7 → `MAINTENANCE`
- ratio <= 0.7 → `DISINVESTMENT`

### 7. MoralDepreciation (Frozen Model)

Obsolescence tracking for fixed capital.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `naics_code` | `str` | Industry identifier | |
| `physical_remaining_life` | `float` | >= 0 | Years of physical function left |
| `economic_remaining_life` | `float` | >= 0 | Years before replacement needed |

**Computed fields**:
- `obsolescence_factor`: economic / physical (1.0 if physical = 0)

### 8. ReplacementCyclePosition (Enum)

| Value | Meaning |
|-------|---------|
| `INVESTMENT_BOOM` | replacement/depreciation > 1.5 |
| `EXPANSION` | ratio > 1.0 |
| `MAINTENANCE` | ratio > 0.7 |
| `DISINVESTMENT` | ratio <= 0.7 |

### 9. InventoryState (Frozen Model)

Stock of commodities in various stages.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `fips_code` | `str` | 5-digit | County identifier |
| `year` | `int` | >= 2010 | Data year |
| `raw_materials` | `Currency` | >= 0 | Unprocessed inputs |
| `work_in_progress` | `Currency` | >= 0 | Partially completed |
| `finished_goods` | `Currency` | >= 0 | Awaiting sale |
| `days_inventory_raw` | `float` | >= 0 | Days of production covered |
| `days_inventory_finished` | `float` | >= 0 | Days of sales in stock |

**Computed fields**:
- `total_inventory`: raw + wip + finished
- `inventory_problem`: `OVERPRODUCTION` if finished > 60 days, `SUPPLY_CRISIS` if raw < 7 days, else `NORMAL`

### 10. InventoryDiagnosis (Enum)

| Value | Condition |
|-------|-----------|
| `NORMAL` | 7 <= raw_days, finished_days <= 60 |
| `OVERPRODUCTION` | finished_days > 60 |
| `SUPPLY_CRISIS` | raw_days < 7 |

### 11. ReproductionBalance (Frozen Model)

Result of checking simple reproduction condition I(v+s) = IIc.

| Field | Type | Description |
|-------|------|-------------|
| `condition_met` | `bool` | Whether gap < tolerance |
| `gap` | `float` | I(v+s) - IIc |
| `interpretation` | `str` | Direction of imbalance |

### 12. ReproductionAnalysis (Frozen Model)

Result of extended reproduction check including Department III.

| Field | Type | Description |
|-------|------|-------------|
| `labor_power_demand` | `float` | Sum of all departments' v |
| `reproduction_capacity` | `float` | III's c + v + s |
| `gap` | `float` | demand - capacity |
| `sustainability` | `bool` | gap <= 0 |

### 13. RealizationCrisis (Frozen Model)

Metrics for the gap between value produced and realized.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `fips_code` | `str` | 5-digit | |
| `year` | `int` | | |
| `commodity_value_produced` | `Currency` | > 0 | Total produced |
| `commodity_value_realized` | `Currency` | >= 0 | Actually sold |

**Computed fields**:
- `realization_gap`: produced - realized
- `realization_rate`: realized / produced
- `crisis_severity`: NORMAL (>95%), MILD_SLOWDOWN (>85%), RECESSION (>70%), CRISIS (<=70%)

### 14. CrisisSeverity (Enum)

| Value | Realization Rate |
|-------|-----------------|
| `NORMAL` | > 95% |
| `MILD_SLOWDOWN` | 85-95% |
| `RECESSION` | 70-85% |
| `CRISIS` | <= 70% |

### 15. DisproportionalityCrisis (Frozen Model)

Department-level output imbalance.

| Field | Type | Description |
|-------|------|-------------|
| `year` | `int` | |
| `dept_i_output` | `Currency` | |
| `dept_ii_output` | `Currency` | |
| `dept_i_share_required` | `float` | Expected proportion |

**Computed fields**:
- `actual_i_share`: dept_i / (dept_i + dept_ii)
- `imbalance`: |actual - required|
- `imbalance_direction`: OVERPRODUCTION_MEANS_PRODUCTION or OVERPRODUCTION_CONSUMPTION_GOODS

### 16. PureCirculationCosts (Frozen Model)

Unproductive circulation costs breakdown.

| Field | Type | Description |
|-------|------|-------------|
| `fips_code` | `str` | |
| `year` | `int` | |
| `sales_labor` | `Currency` | Salespeople, cashiers |
| `accounting_labor` | `Currency` | Bookkeepers |
| `marketing_labor` | `Currency` | Advertising personnel |
| `sales_facilities` | `Currency` | Retail space depreciation |
| `advertising_materials` | `Currency` | Ad spend |
| `transaction_costs` | `Currency` | Payment processing, banking |

**Computed fields**:
- `total_pure_circulation`: sum of all cost fields
- Method: `circulation_burden(total_revenue)` → ratio

### 17. TransportationValue (Frozen Model)

Value added by transportation.

| Field | Type | Description |
|-------|------|-------------|
| `origin_value` | `Currency` | Commodity value before transport |
| `transport_c` | `Currency` | Vehicles, fuel, infrastructure |
| `transport_v` | `Currency` | Transport worker wages |
| `transport_s` | `Currency` | Surplus from transport labor |

**Computed fields**:
- `value_added`: c + v + s
- `destination_value`: origin + value_added
- `transport_value_ratio`: value_added / destination_value

### 18. CirculationCrisisAssessment (Frozen Model)

Integrated crisis assessment combining all Volume II signals.

| Field | Type | Description |
|-------|------|-------------|
| `fips_code` | `str` | |
| `year` | `int` | |
| `realization_crisis` | `bool` | C' → M' failing |
| `turnover_crisis` | `bool` | Circuit interrupted |
| `reproduction_crisis` | `bool` | Departments out of balance |
| `vulnerabilities` | `list[str]` | Active vulnerability labels |

**Vulnerability derivation rules** (computed by `assess_circulation_crisis()`):

| Vulnerability String | Derived From | Condition |
|---------------------|--------------|-----------|
| `REALIZATION_CRISIS` | `CircuitState.commodity_overhang` | > 0.3 |
| `SUPPLY_CHAIN_CRISIS` | `InventoryState.inventory_problem` | == `SUPPLY_CRISIS` |
| `LABOR_SHORTAGE` | `ReproductionAnalysis.sustainability` | == False (demand > capacity) |
| `MONETARY_CRISIS` | `CircuitState.liquidity_ratio` | < 0.1 |

### 19. CirculationCrisisState (Frozen Model)

Per-county circulation crisis tracking (persists across ticks).

| Field | Type | Description |
|-------|------|-------------|
| `circuit_state` | `CircuitState` | Current capital form distribution |
| `inventory_state` | `InventoryState` | Current inventory levels |
| `depreciation_fund` | `DepreciationFundState` | Fixed capital fund tracking |
| `latest_assessment` | `CirculationCrisisAssessment | None` | Most recent crisis check |

Factory: `CirculationCrisisState.initial(fips, year)` → zeroed/neutral state.

**Relationship**: Composed into `CountyEconomicState` as a new field, alongside existing `crisis_state` (TRPF) and `bifurcation_risk`.

## Graph Bridge Serialization

New `tick_` prefixed attributes written to territory nodes:

| Attribute | Source |
|-----------|--------|
| `tick_liquidity_ratio` | `circulation.circuit_state.liquidity_ratio` |
| `tick_commodity_overhang` | `circulation.circuit_state.commodity_overhang` |
| `tick_turnovers_per_year` | Derived from industry-weighted turnover profile |
| `tick_annual_surplus_rate` | Annual rate of surplus value |
| `tick_replacement_cycle` | `circulation.depreciation_fund.replacement_cycle_position` |
| `tick_inventory_diagnosis` | `circulation.inventory_state.inventory_problem` |
| `tick_realization_crisis` | `circulation.latest_assessment.realization_crisis` |
| `tick_turnover_crisis` | `circulation.latest_assessment.turnover_crisis` |
| `tick_reproduction_crisis` | `circulation.latest_assessment.reproduction_crisis` |
