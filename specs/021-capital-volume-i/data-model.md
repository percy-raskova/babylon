# Data Model: Capital Volume I Production Dynamics

**Feature**: 021-capital-volume-i | **Date**: 2026-02-25

---

## Domain Entities

### ReserveArmyState (frozen Pydantic model)

Composition and dynamics of the industrial reserve army for a territory.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| fips_code | str | len=5 | County FIPS code |
| year | int | 2005-2030 | Calendar year |
| floating_reserve | int | >= 0 | Workers between jobs (approx. U-3 count) |
| latent_reserve | int | >= 0 | Underemployed/discouraged (approx. U-6 - U-3 count) |
| stagnant_reserve | int | >= 0 | Chronic irregular employment (PTER count) |
| pauperized | int | >= 0 | Unable to work (Census disability + institutionalized) |
| labor_force | int | > 0 | Total civilian labor force |

**Computed properties** (not stored):
- `total_reserve -> int`: floating + latent + stagnant (excludes pauperized per Marx)
- `reserve_ratio -> float`: total_reserve / labor_force, in [0, 1]
- `wage_pressure -> float`: sigmoid(reserve_ratio; k, r0), in [0, 1]

**State transitions**: None — this is a snapshot entity. Updated each tick from loaded data + simulation dynamics.

---

### ReserveArmyDynamics (frozen Pydantic model)

Per-tick flow rates governing reserve army formation and absorption.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| fips_code | str | len=5 | County FIPS code |
| tick | int | >= 0 | Simulation tick |
| mechanization_displacement | int | >= 0 | Workers displaced by automation this tick |
| firm_failures | int | >= 0 | Workers from bankrupt enterprises |
| expansion_absorption | int | >= 0 | Workers hired during expansion |
| emigration | int | >= 0 | Workers leaving territory |

**Validation**: All inflows + outflows clamped to prevent labor force from going negative.

---

### DispossessionEvent (frozen Pydantic model)

Aggregate record of primitive accumulation activity per territory per tick.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| fips_code | str | len=5 | Territory FIPS code |
| tick | int | >= 0 | Simulation tick |
| dispossession_type | DispossessionType | enum | One of 8 categories |
| event_count | int | >= 0 | Number of events this tick |
| total_value_transferred | Currency | >= 0 | Total value moved |
| affected_class | SocialRole | enum | Class category losing wealth |
| receiving_category | str | max 50 chars | Entity category gaining wealth (e.g., "institutional_investor", "state") |

**Identity**: Unique by (fips_code, tick, dispossession_type).

---

### DispossessionType (StrEnum)

Eight categories of ongoing primitive accumulation:

| Value | Description |
|-------|-------------|
| FORECLOSURE | Bank seizure of mortgaged property |
| EVICTION | Removal of tenant |
| TAX_SALE | Seizure for unpaid property taxes |
| EMINENT_DOMAIN | State seizure for public use |
| WAGE_THEFT | Unpaid wages, tip theft, misclassification |
| INCARCERATION_SEIZURE | Asset forfeiture from carceral system |
| PENSION_DEFAULT | Corporate bankruptcy eliminating earned pension |
| GENTRIFICATION_DISPLACEMENT | Forced relocation due to rent increases |

---

### TerritoryDispossessionState (frozen Pydantic model)

Aggregate dispossession metrics for a territory.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| fips_code | str | len=5 | Territory FIPS code |
| year | int | 2005-2030 | Calendar year |
| foreclosure_rate | float | [0, 1] | Foreclosures per mortgaged unit |
| eviction_rate | float | [0, 1] | Evictions per renter household |
| displacement_rate | float | [0, 1] | Net out-migration due to housing costs |
| concentrated_ownership | float | [0, 1] | Fraction owned by institutional investors |
| absentee_landlord_share | float | [0, 1] | Fraction of rentals owned by non-residents |

**Computed properties**:
- `dispossession_intensity -> float`: weighted sum of all rates (weights from GameDefines)

---

### WorkingDayState (frozen Pydantic model)

Characteristics of the working day for a territory-sector pair.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| fips_code | str | len=5 | Territory FIPS code |
| naics_sector | str | 2-digit | NAICS sector code |
| year | int | 2005-2030 | Calendar year |
| avg_weekly_hours | float | [0, 168] | Average actual hours worked per week |
| labor_intensity_index | float | > 0 | Output per hour relative to baseline (1.0 = baseline) |

**Computed properties**:
- `exploitation_mode -> ExploitationMode`: ABSOLUTE_DOMINANT if hours > 45 and intensity < 1.1, RELATIVE_DOMINANT if hours <= 40 and intensity > 1.2, else MIXED
- `visibility_modifier -> float`: 1.0 for ABSOLUTE, 0.3 for RELATIVE, interpolated for MIXED

---

### ExploitationMode (StrEnum)

| Value | Description |
|-------|-------------|
| ABSOLUTE_DOMINANT | Long hours, low productivity growth |
| RELATIVE_DOMINANT | Standard hours, high productivity growth |
| MIXED | Blend of both modes |

---

## New 3NF Fact Tables

### FactBLSUnemploymentDecomposition

County-level unemployment decomposition from BLS Local Area Unemployment Statistics.

| Column | Type | FK | Description |
|--------|------|----|-------------|
| county_id | int | dim_county | County reference |
| time_id | int | dim_time | Year reference |
| source_id | int | dim_data_source | Data source reference |
| labor_force | int | — | Civilian labor force |
| employed | int | — | Employed count |
| unemployed_u3 | int | — | Official unemployed (U-3) |
| unemployed_u6 | int | — | Broader measure (U-6) |
| part_time_economic | int | — | Part-time for economic reasons (PTER) |
| discouraged | int | — | Discouraged workers |
| marginally_attached | int | — | Marginally attached |

**PK**: (county_id, time_id)

### FactEvictionLabFiling

County-level eviction filings and executions from Eviction Lab.

| Column | Type | FK | Description |
|--------|------|----|-------------|
| county_id | int | dim_county | County reference |
| time_id | int | dim_time | Year reference |
| source_id | int | dim_data_source | Data source reference |
| filings | int | — | Eviction filings count |
| executions | int | — | Completed evictions |
| filing_rate | decimal(8,6) | — | Filings per renter household |
| execution_rate | decimal(8,6) | — | Executions per renter household |
| renter_households | int | — | Denominator for rates |

**PK**: (county_id, time_id)

### FactForeclosureRate

County-level foreclosure rates from HUD/FRED/state sources.

| Column | Type | FK | Description |
|--------|------|----|-------------|
| county_id | int | dim_county | County reference |
| time_id | int | dim_time | Year reference |
| source_id | int | dim_data_source | Data source reference |
| filings | int | — | Foreclosure filings count |
| completions | int | — | Completed foreclosures |
| filing_rate | decimal(8,6) | — | Filings per mortgaged unit |
| completion_rate | decimal(8,6) | — | Completions per mortgaged unit |
| mortgaged_units | int | — | Denominator for rates |

**PK**: (county_id, time_id)

### FactCensusInstitutionalOwnership

County-level housing institutional ownership from Census ACS.

| Column | Type | FK | Description |
|--------|------|----|-------------|
| county_id | int | dim_county | County reference |
| time_id | int | dim_time | Year reference |
| source_id | int | dim_data_source | Data source reference |
| total_units | int | — | Total housing units |
| owner_occupied | int | — | Owner-occupied count |
| renter_occupied | int | — | Renter-occupied count |
| institutional_owned | int | — | Institutionally owned estimate |
| absentee_owned | int | — | Non-resident owned estimate |
| net_migration_renters | int | — | Net renter migration (signed) |

**PK**: (county_id, time_id)

### FactBLSProductivity

Sector-level hours and productivity from BLS Current Employment Statistics / Productivity program.

| Column | Type | FK | Description |
|--------|------|----|-------------|
| industry_id | int | dim_industry | NAICS sector reference |
| time_id | int | dim_time | Year reference |
| source_id | int | dim_data_source | Data source reference |
| avg_weekly_hours | decimal(5,2) | — | Average weekly hours |
| avg_hourly_earnings | decimal(8,2) | — | Average hourly earnings |
| output_per_hour | decimal(10,4) | — | Labor productivity index |
| unit_labor_costs | decimal(10,4) | — | Unit labor cost index |

**PK**: (industry_id, time_id)

---

## Entity Relationships

```
ReserveArmyState ──── one per territory-year ──── Territory
     │
     └── wage_pressure ──► CountyEconomicState.median_wage (modifier)

DispossessionEvent ──── many per territory-tick ──── Territory
     │
     ├── rates ──► DispossessionDataSource protocol (feeds existing calculator)
     └── class_transitions ──► DefaultClassTransitionEngine (via TransitionRates)

WorkingDayState ──── one per territory-sector-year ──── Territory × Sector
     │
     └── visibility_modifier ──► ConsciousnessSystem (exploitation visibility)

TerritoryDispossessionState ──── one per territory-year ──── Territory
     │
     └── intensity ──► TerritorySystem (value transfer accounting)
```
