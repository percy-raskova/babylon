# Babylon Data Requirements

Manual data collection guide for grounding the simulation in material reality.

---

## Overview

The simulation needs two types of data:

1. **Reality Data** - Static reference facts about the real world (census, economics, trade)
2. **Game Resources** - Stockpiles and flows that change during simulation

All data should be CSV format for easy import into SQLite.

---

## Priority Levels

- **P1 (Critical)**: Required for meaningful simulation - get these first
- **P2 (Important)**: Enables richer dynamics - get after P1 complete
- **P3 (Nice-to-have)**: Adds depth but not essential for MVP

---

## Part 1: Population & Demographics (P1)

### Dataset 1.1: State Population by Class Proxy

**Purpose**: Map real populations to game classes (Bourgeoisie, Proletariat, Petit Bourgeoisie, Lumpenproletariat)

**Source**: Census ACS 5-Year Estimates (2022 or 2023)
- URL: https://data.census.gov/

**Variables Needed**:
| Column | Census Variable | Description |
|--------|-----------------|-------------|
| state_fips | GEO_ID | State FIPS code |
| state_name | NAME | State name |
| total_pop | B01001_001E | Total population |
| employed | B23025_004E | Employed population |
| unemployed | B23025_005E | Unemployed population |
| not_in_labor_force | B23025_007E | Not in labor force |
| self_employed | B24080_012E | Self-employed (unincorporated) |
| median_income | B19013_001E | Median household income |
| poverty_pop | B17001_002E | Population below poverty |

**File**: `census_state_population.csv`

**Class Mapping Logic** (we'll implement in code):
- Bourgeoisie: Top 1% wealth holders (proxy: income > $500k)
- Petit Bourgeoisie: Self-employed + small business owners
- Proletariat: Employed wage workers
- Lumpenproletariat: Unemployed + below poverty line

---

### Dataset 1.2: Metropolitan Area Demographics

**Purpose**: Populate the `locations.json` metro areas with real data

**Source**: Census ACS, Metropolitan Statistical Areas
- URL: https://data.census.gov/ (filter by "Metropolitan Statistical Area")

**Variables Needed**:
| Column | Census Variable | Description |
|--------|-----------------|-------------|
| cbsa_code | GEO_ID | CBSA code (metro area ID) |
| metro_name | NAME | Metro area name |
| total_pop | B01001_001E | Total population |
| median_income | B19013_001E | Median household income |
| gini_index | B19083_001E | Income inequality (Gini) |
| rent_median | B25064_001E | Median gross rent |
| home_value_median | B25077_001E | Median home value |
| pct_renters | Derived | Renter-occupied / Total occupied |

**File**: `census_metro_demographics.csv`

**Metro Areas to Include** (match locations.json):
- Los Angeles-Long Beach-Anaheim (CBSA 31080)
- Chicago-Naperville-Elgin (CBSA 16980)
- Washington-Arlington-Alexandria (CBSA 47900)
- Denver-Aurora-Centennial (CBSA 19740)
- Baltimore-Columbia-Towson (CBSA 12580)
- Kansas City (CBSA 28140)

---

## Part 2: Economic Indicators (P1)

### Dataset 2.1: Federal Reserve Economic Data (FRED)

**Purpose**: Macro-economic conditions that affect all classes

**Source**: FRED (Federal Reserve Economic Data)
- URL: https://fred.stlouisfed.org/

**Variables Needed** (download as CSV, annual data 2000-2024):
| Series ID | Description | File |
|-----------|-------------|------|
| GDPC1 | Real GDP (billions) | `fred_gdp.csv` |
| UNRATE | Unemployment Rate (%) | `fred_unemployment.csv` |
| CPIAUCSL | Consumer Price Index | `fred_cpi.csv` |
| FEDFUNDS | Federal Funds Rate (%) | `fred_interest.csv` |
| GFDEBTN | Federal Debt (millions) | `fred_debt.csv` |
| M2SL | M2 Money Supply | `fred_money_supply.csv` |
| MEHOINUSA672N | Real Median Household Income | `fred_median_income.csv` |

**Consolidated File**: `fred_economic_indicators.csv`
```
year,gdp_billions,unemployment_pct,cpi,fed_funds_rate,federal_debt_millions,m2_money_supply,median_income
2020,18509.1,8.1,258.8,0.36,26945391,19412.0,67521
...
```

---

### Dataset 2.2: Wealth Distribution

**Purpose**: Calculate Bourgeoisie extraction capacity (Imperial Rent)

**Source**: Federal Reserve Survey of Consumer Finances (SCF)
- URL: https://www.federalreserve.gov/econres/scfindex.htm

**Variables Needed**:
| Column | Description |
|--------|-------------|
| year | Survey year (2019, 2022) |
| percentile | Wealth percentile (bottom 50%, 50-90%, 90-99%, top 1%) |
| net_worth_share | Share of total wealth held |
| income_share | Share of total income |
| avg_net_worth | Average net worth in bracket |

**File**: `fed_wealth_distribution.csv`

---

## Part 3: Trade & Imperial Rent (P2)

### Dataset 3.1: US Trade Balance by Country

**Purpose**: Model unequal exchange / value extraction from periphery

**Source**: US Census Bureau Foreign Trade
- URL: https://www.census.gov/foreign-trade/data/

**Variables Needed**:
| Column | Description |
|--------|-------------|
| year | Year |
| country_code | ISO 3166-1 alpha-3 |
| country_name | Country name |
| exports_millions | US exports to country |
| imports_millions | US imports from country |
| balance_millions | Trade balance (exports - imports) |

**File**: `trade_balance_by_country.csv`

**Key Countries** (major trade partners):
- China (CHN)
- Mexico (MEX)
- Canada (CAN)
- Japan (JPN)
- Germany (DEU)
- Vietnam (VNM)
- South Korea (KOR)
- India (IND)
- Taiwan (TWN)
- United Kingdom (GBR)

---

### Dataset 3.2: Import Categories

**Purpose**: Link trade to game resources (oil, steel, semiconductors)

**Source**: US Census Bureau Foreign Trade (HS Codes)
- URL: https://usatrade.census.gov/

**Variables Needed**:
| Column | Description |
|--------|-------------|
| year | Year |
| hs_code | Harmonized System code (2-digit) |
| category | Category name |
| import_value_millions | Total import value |
| top_source_country | Largest source country |

**File**: `imports_by_category.csv`

**Categories to Include** (map to resources.json):
- 27: Mineral fuels, oils (-> Crude Oil, Gasoline)
- 72: Iron and steel (-> Steel, Iron Ore)
- 84: Machinery (-> general industrial)
- 85: Electrical machinery (-> Semiconductors, Computer Chips)
- 87: Vehicles (-> Automobiles)

---

## Part 4: Labor & Production (P2)

### Dataset 4.1: Industry Employment by State

**Purpose**: Map labor to production capacity

**Source**: Bureau of Labor Statistics (BLS) QCEW
- URL: https://www.bls.gov/cew/

**Variables Needed**:
| Column | Description |
|--------|-------------|
| state_fips | State FIPS code |
| naics_code | Industry code (2-digit) |
| industry_name | Industry name |
| employment | Annual average employment |
| total_wages_thousands | Total wages paid |
| avg_weekly_wage | Average weekly wage |

**File**: `bls_employment_by_industry.csv`

**Industries to Include** (map to resources.json):
- 11: Agriculture (-> Wheat)
- 21: Mining (-> Iron Ore, Crude Oil)
- 31-33: Manufacturing (-> Steel, Automobiles, Semiconductors)
- 22: Utilities (-> Energy sector)

---

### Dataset 4.2: Union Membership by State

**Purpose**: Proxy for working class organization (P(S|R) formula input)

**Source**: Bureau of Labor Statistics
- URL: https://www.bls.gov/news.release/union2.toc.htm

**Variables Needed**:
| Column | Description |
|--------|-------------|
| state | State name |
| year | Year |
| total_employed | Total employed |
| union_members | Union members |
| union_pct | Percent unionized |
| covered_by_union | Covered by union contract |

**File**: `bls_union_membership.csv`

---

## Part 5: Housing & Cost of Living (P2)

### Dataset 5.1: Housing Costs by Metro

**Purpose**: Calculate subsistence threshold (P(S|A) formula input)

**Source**: Census ACS + HUD Fair Market Rents
- Census: https://data.census.gov/
- HUD: https://www.huduser.gov/portal/datasets/fmr.html

**Variables Needed**:
| Column | Description |
|--------|-------------|
| cbsa_code | Metro area code |
| metro_name | Metro name |
| median_rent | Median gross rent |
| fmr_2br | HUD Fair Market Rent (2BR) |
| median_home_price | Median home value |
| rent_burden_pct | Pct paying >30% income on rent |

**File**: `housing_costs_metro.csv`

---

## Part 6: Military & State Capacity (P3)

### Dataset 6.1: Military Installations by State

**Purpose**: Model state repression capacity

**Source**: Defense Manpower Data Center
- URL: https://dwp.dmdc.osd.mil/dwp/app/dod-data-reports/workforce-reports

**Variables Needed**:
| Column | Description |
|--------|-------------|
| state | State |
| active_duty | Active duty personnel |
| reserve | Reserve personnel |
| civilian_dod | DoD civilian employees |
| installations | Number of major installations |

**File**: `military_by_state.csv`

---

### Dataset 6.2: Law Enforcement

**Purpose**: Domestic repression capacity

**Source**: FBI UCR / Census of State and Local Law Enforcement
- URL: https://bjs.ojp.gov/data-collection/census-state-and-local-law-enforcement-agencies-csllea

**Variables Needed**:
| Column | Description |
|--------|-------------|
| state | State |
| total_officers | Full-time sworn officers |
| officers_per_capita | Officers per 1,000 residents |
| total_agencies | Number of agencies |

**File**: `law_enforcement_by_state.csv`

---

## Part 7: Game Resources - Initial Stockpiles (P1)

### Dataset 7.1: Strategic Reserves

**Purpose**: Initialize game resource quantities

**Source**: Various (EIA, USGS, USDA)
- EIA: https://www.eia.gov/
- USGS: https://www.usgs.gov/centers/national-minerals-information-center
- USDA: https://www.usda.gov/

**Manual Research Needed**:
| Resource | Source | Data Point |
|----------|--------|------------|
| Crude Oil | EIA | Strategic Petroleum Reserve (million barrels) |
| Iron Ore | USGS | Annual production (million metric tons) |
| Steel | USGS | Annual production (million metric tons) |
| Wheat | USDA | Annual production (million bushels) |
| Semiconductors | SIA | US market share / production |

**File**: `strategic_resources.csv`
```
resource_id,resource_name,annual_production,unit,strategic_reserve,reserve_unit
R002,Crude Oil,4300000000,barrels,350000000,barrels
R001,Iron Ore,48000000,metric_tons,0,metric_tons
...
```

---

## File Organization

Place all downloaded CSVs in:
```
babylon/data/external/
├── census/
│   ├── census_state_population.csv
│   └── census_metro_demographics.csv
├── fred/
│   └── fred_economic_indicators.csv
├── trade/
│   ├── trade_balance_by_country.csv
│   └── imports_by_category.csv
├── bls/
│   ├── bls_employment_by_industry.csv
│   └── bls_union_membership.csv
├── housing/
│   └── housing_costs_metro.csv
├── military/
│   ├── military_by_state.csv
│   └── law_enforcement_by_state.csv
└── resources/
    └── strategic_resources.csv
```

---

## Next Steps After Collection

1. Create SQLite schema matching these tables
2. Write import scripts (CSV -> SQLite)
3. Create Pydantic models for each table
4. Wire data to simulation initialization
5. Update scenarios.py to load from SQLite instead of hardcoded values

---

## Quick Start - Minimum Viable Data

If time is limited, get these first (enables basic simulation):

1. `census_state_population.csv` - Who lives where
2. `fred_economic_indicators.csv` - Macro conditions
3. `bls_union_membership.csv` - Organization levels
4. `strategic_resources.csv` - Resource quantities

These four files ground the simulation in material reality.
