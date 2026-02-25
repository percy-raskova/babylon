# Data Model: Capital Volume III Integration

**Feature**: 024-capital-volume-iii | **Date**: 2026-02-25

## Entity Relationship Overview

```
NationalFinancialParameters (1 per tick)
├── InterestRateState         (national)
├── CreditState               (national)
├── FictitiousCapitalStock    (national)
├── CreditCyclePhase          (national, enum)
├── CounterTendencyStrength   (national)
└── MonetaryAdjustment        (national)

CountyEconomicState (1 per county per tick) ── extends existing
├── SurplusValueDistribution  (county-level, references national interest/tax data)
├── RentExtraction            (county-level, from Census/BEA)
├── HousingValueDecomposition (county-level, from Census/ACS)
├── DebtAccumulation          (county-level, cross-tick state)
└── FinancialCrisisAssessment (county-level, integrates national + county signals)
```

## Enums

### CreditCyclePhase

```
Values: EXPANSION, OVEREXTENSION, CRISIS, RECOVERY, STAGNATION

State Machine:
  EXPANSION → OVEREXTENSION → CRISIS → RECOVERY → EXPANSION  (main cycle)
  OVEREXTENSION → STAGNATION  (shortcut)
  RECOVERY → STAGNATION       (shortcut)
  STAGNATION → (terminal, no exits)
```

### ValueBasis

```
Values: NOMINAL, REAL, LABOR_TIME
```

### RentCategory

```
Values: AGRICULTURAL, RESOURCE, URBAN
```

## National-Level Entities

### InterestRateState

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| year | int | ge=2007, le=2040 | Parameter year |
| base_rate | float | ge=0.0 | Federal funds rate or benchmark (FEDFUNDS) |
| treasury_10y | float | ge=0.0 | 10-year Treasury yield (DGS10) |
| baa_spread | float | ge=0.0 | Baa corporate spread over Treasury (BAA10Y) |
| effective_rate | float | ge=0.0 | Base rate + Baa spread (computed) |

Computed fields:
- `effective_rate`: base_rate + baa_spread

### CreditState

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| year | int | ge=2007, le=2040 | Parameter year |
| total_credit | Currency | ge=0 | Total credit market debt (TCMDO) |
| credit_expansion_rate | float | — | YoY growth in total credit |
| default_rate | float | ge=0, le=1 | Fraction of loans in default |
| spread_to_treasuries | float | ge=0 | Risk premium (BAA10Y) |
| phase | CreditCyclePhase | — | Current cycle position |
| prev_phase | CreditCyclePhase | None | Previous phase for transition validation |

Computed fields:
- `credit_fragility`: default_rate * spread_to_treasuries

### FictitiousCapitalStock

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| year | int | ge=2007, le=2040 | Parameter year |
| government_debt | Currency | ge=0 | Federal debt (GFDEBTN) |
| corporate_equity | Currency | ge=0 | Stock market capitalization (WILL5000PR proxy) |
| corporate_debt | Currency | ge=0 | Corporate bonds and loans (Z.1) |
| household_debt | Currency | ge=0 | Mortgages, consumer credit, student loans (Z.1) |
| derivatives_notional | Currency | ge=0 | Face value of derivatives (tracked, excluded from index) |

Computed fields:
- `total_claims`: government_debt + corporate_equity + corporate_debt + household_debt
- `ratio_to_real(real_gdp)`: total_claims / real_gdp (financialization index)

### CounterTendencyStrength

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| year | int | ge=2007, le=2040 | Parameter year |
| exploitation_rate_change | float | — | Delta(s/v) year-over-year |
| wage_suppression | float | ge=0 | Gap: productivity growth - wage growth |
| constant_capital_cheapening | float | — | Rate of decline in capital goods prices (PPI) |
| reserve_army_size | float | ge=0, le=1 | U-6 unemployment rate |
| imperial_rent_flow | Currency | ge=0 | Net unequal exchange Phi (from Feature 013) |
| fictitious_profit_share | float | ge=0, le=1 | Financial sector share of reported profits |

Computed fields:
- `net_counter_tendency`: Weighted sum of normalized indicators. Positive = counter-tendencies dominating, negative = TRPF dominating.

### MonetaryAdjustment

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| year | int | ge=2007, le=2040 | Parameter year |
| cpi_index | float | gt=0 | CPI (base year = 100) |
| gdp_deflator | float | gt=0 | GDP deflator (base year = 100) |
| snlt_per_dollar | float | gt=0 | Labor-hours per dollar of GDP |
| base_year | int | ge=2007 | Reference year for real conversion |

Methods:
- `nominal_to_real(nominal, target_year_cpi)`: nominal * (base_cpi / current_cpi)
- `nominal_to_labor_time(nominal)`: nominal * snlt_per_dollar
- `real_to_nominal(real, target_year_cpi)`: real * (current_cpi / base_cpi)

### NationalFinancialParameters

Extends `NationalTickParameters` pattern. Contains:

| Field | Type | Description |
|-------|------|-------------|
| interest_rate_state | InterestRateState | National interest environment |
| credit_state | CreditState | Credit system health |
| fictitious_capital | FictitiousCapitalStock | Accumulated financial claims |
| counter_tendencies | CounterTendencyStrength | TRPF offsetting factors |
| monetary_adjustment | MonetaryAdjustment | Value basis conversion factors |

## County-Level Entities

### SurplusValueDistribution

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips_code | str | len=5 | County FIPS |
| year | int | ge=2007, le=2040 | Distribution year |
| total_surplus_produced | Currency | ge=0 | From ValueTensor4x3 total_s |
| interest_payments | Currency | ge=0 | Transferred to money-capitalists |
| ground_rent | Currency | ge=0 | Transferred to landowners |
| taxes_on_surplus | Currency | ge=0 | State appropriation |

Computed fields:
- `profit_of_enterprise`: total_surplus_produced - interest_payments - ground_rent - taxes_on_surplus (may be negative)
- `distribution_complete`: abs(sum - total) < EPSILON
- `financialization_share`: interest_payments / total_surplus_produced
- `rentier_share`: ground_rent / total_surplus_produced
- `claims_exceed_surplus`: (interest_payments + ground_rent + taxes_on_surplus) > total_surplus_produced

### RentExtraction

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips_code | str | len=5 | County FIPS |
| year | int | ge=2007, le=2040 | Rent year |
| agricultural_rent | Currency | ge=0 | Farmland rent |
| resource_rent | Currency | ge=0 | Mining, oil/gas rent |
| urban_rent | Currency | ge=0 | Building site rent, commercial real estate |

Computed fields:
- `total_rent`: agricultural_rent + resource_rent + urban_rent
- `rent_share_of_surplus(total_surplus)`: total_rent / total_surplus

### HousingValueDecomposition

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips_code | str | len=5 | County FIPS |
| year | int | ge=2007, le=2040 | Assessment year |
| construction_value | Currency | ge=0 | Labor-value of structure (c+v+s of construction) |
| ground_rent_capitalized | Currency | ge=0 | Location rent capitalized at interest rate |
| speculative_premium | Currency | ge=0 | Excess of market price over fundamentals |

Computed fields:
- `market_price`: construction_value + ground_rent_capitalized + speculative_premium
- `fictitious_fraction`: (ground_rent_capitalized + speculative_premium) / market_price

### DebtAccumulation

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips_code | str | len=5 | County FIPS |
| year | int | ge=2007, le=2040 | Current year |
| accumulated_debt | Currency | ge=0 | Running cumulative shortfall |
| consecutive_deficit_ticks | int | ge=0 | Ticks with p < 0 |

Methods:
- `update(enterprise_profit)`: If profit < 0, add |profit| to debt. If profit > 0, subtract min(profit, debt) from debt.

### CreditCrisisIndicator

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| overproduction_signal | bool | — | Inventories rising, capacity utilization falling |
| profit_squeeze | bool | — | Profit rate falling while debt service rising |
| liquidity_crisis | bool | — | Spread spiking, credit contracting |

Computed fields:
- `crisis_probability`: sum(signals) / 3

### FinancialCrisisAssessment

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips_code | str | len=5 | County FIPS |
| year | int | ge=2007, le=2040 | Assessment year |
| profit_squeeze | bool | — | Interest burden > threshold |
| overaccumulation | bool | — | Financialization ratio > threshold |
| credit_fragility | bool | — | Default rate * spread > threshold |
| claims_exceed_surplus | bool | — | i + r + t > s |
| credit_crisis_indicator | CreditCrisisIndicator | — | Composite credit-specific signals |

Computed fields:
- `active_signals`: Count of True flags (profit_squeeze, overaccumulation, credit_fragility, claims_exceed_surplus)
- `crisis_probability`: active_signals / 4

## Extended Existing Entities

### CountyEconomicState (extend)

New fields added:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| surplus_distribution | SurplusValueDistribution | factory | Surplus split for this county-year |
| rent_extraction | RentExtraction | factory | Ground rent by category |
| housing_decomposition | HousingValueDecomposition | None | Housing value split (optional) |
| debt_accumulation | DebtAccumulation | factory | Cumulative deficit tracker |
| financial_crisis | FinancialCrisisAssessment | factory | Integrated crisis flags |

### Graph Bridge Extensions (tick_* attributes)

New territory node attributes:

| Attribute | Source | Type |
|-----------|--------|------|
| tick_interest_burden | national rate * county capital | float |
| tick_ground_rent | county rent_extraction.total_rent | float |
| tick_rentier_share | county rent / surplus | float |
| tick_profit_of_enterprise | residual p | float |
| tick_financialization_share | interest / surplus | float |
| tick_accumulated_debt | county debt_accumulation | float |
| tick_claims_exceed_surplus | bool flag | bool |
| tick_housing_fictitious_fraction | housing decomposition | float or None |
| tick_credit_cycle_phase | national credit phase (shared) | str |
| tick_financial_crisis_signals | active signal count | int |

## Threshold Constants

All with `Final[float]` type and traceability docstrings:

| Constant | Value | Traceability |
|----------|-------|--------------|
| INTEREST_BURDEN_SQUEEZE | 0.4 | FRED: Historical ratio of net interest to corporate profits (NIPA) |
| FINANCIALIZATION_BUBBLE | 3.5 | FRED: TCMDO/GDP ratio peaked at ~3.7 in 2008; 3.5 as warning |
| CREDIT_FRAGILITY_THRESHOLD | 0.02 | FRED: BAA spread * default rate product during 2008 crisis |
| STAGNATION_CREDIT_GROWTH | 0.01 | FRED: Near-zero credit growth threshold for stagnation diagnosis |
| OVEREXTENSION_DEFAULT_RATE | 0.03 | FRED: Default rate threshold triggering crisis transition |
| RECOVERY_CONSECUTIVE_PERIODS | 2 | Matches Feature 018 m_recovery parameter |
| DEBT_SPIRAL_THRESHOLD | 0.5 | Accumulated debt / annual surplus ratio triggering crisis flag |
| COUNTER_TENDENCY_WEIGHTS | [0.2, 0.15, 0.15, 0.15, 0.2, 0.15] | Equal-ish weighting; imperial rent and exploitation weighted higher per MLM-TW theory |
