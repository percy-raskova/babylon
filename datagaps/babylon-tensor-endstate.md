# Babylon Tensor Infrastructure: Desired End State

## Overview

This document describes the target state for Babylon's economic data infrastructure. The goal is a **rank-2 value tensor** T[territory, sector, {c, v, s}] populated entirely from federal statistical data, enabling empirically-grounded simulation of Marxist value dynamics.

______________________________________________________________________

## The Fundamental Equation

For any territory × sector combination:

```
Gross Output = Constant Capital + Variable Capital + Surplus Value
(c + v + s)   =       c         +        v         +       s
```

Where:

- **c (Constant Capital)**: Dead labor — value of intermediate inputs consumed in production
- **v (Variable Capital)**: Living labor — wages paid to workers
- **s (Surplus Value)**: Extracted value — the difference between value created and wages paid

______________________________________________________________________

## Target Schema

### Core Dimension Tables

```sql
-- BEA industry classification (the ~15-70 industries BEA uses)
dim_bea_industry (
    bea_industry_id INTEGER PRIMARY KEY,
    bea_code VARCHAR(10) UNIQUE,      -- '11', '21', '31G', 'FIRE', etc.
    bea_title VARCHAR(200),
    parent_bea_code VARCHAR(10),       -- hierarchy support
    is_goods_producing BOOLEAN,
    is_service_producing BOOLEAN
)

-- Bridge: NAICS → BEA (many NAICS codes map to one BEA industry)
bridge_naics_bea (
    naics_code VARCHAR(20) PRIMARY KEY,
    bea_industry_id INTEGER REFERENCES dim_bea_industry,
    mapping_quality VARCHAR(20)        -- 'exact', 'approximate', 'sector_fallback'
)

-- Price deflator series metadata
dim_deflator_series (
    deflator_id INTEGER PRIMARY KEY,
    series_code VARCHAR(50) UNIQUE,    -- 'GDPDEF', 'CPIAUCSL', etc.
    series_name VARCHAR(200),
    base_year INTEGER,
    geographic_scope VARCHAR(50)       -- 'national', 'metro', 'state'
)
```

### Core Fact Tables

```sql
-- National industry data (WHERE WE GET c_ratio)
-- Source: BEA GDP by Industry tables
fact_bea_industry_national (
    bea_industry_id INTEGER REFERENCES dim_bea_industry,
    time_id INTEGER REFERENCES dim_time,
    gross_output_millions DECIMAL(15,2),
    intermediate_inputs_millions DECIMAL(15,2),   -- THIS IS c
    value_added_millions DECIMAL(15,2),           -- THIS IS (v+s)
    -- Derived ratios
    c_ratio AS (intermediate_inputs / gross_output),
    va_ratio AS (value_added / gross_output),
    PRIMARY KEY (bea_industry_id, time_id)
)

-- County GDP (WHERE WE GET territorial value-added)
-- Source: BEA Regional Economic Accounts
fact_bea_county_gdp (
    county_id INTEGER REFERENCES dim_county,
    bea_industry_id INTEGER REFERENCES dim_bea_industry,
    time_id INTEGER REFERENCES dim_time,
    gdp_millions DECIMAL(15,2),        -- This is value-added (v+s) only
    PRIMARY KEY (county_id, bea_industry_id, time_id)
)

-- Price deflators for real vs nominal conversion
fact_price_deflator (
    deflator_id INTEGER REFERENCES dim_deflator_series,
    time_id INTEGER REFERENCES dim_time,
    deflator_value DECIMAL(10,6),      -- base_year = 100.0
    PRIMARY KEY (deflator_id, time_id)
)
```

### Spatial Tables (for H3 hex grid)

```sql
-- County geometries (polygons for spatial operations)
dim_county_geometry (
    county_id INTEGER PRIMARY KEY REFERENCES dim_county,
    geometry GEOMETRY,                 -- MultiPolygon, WGS84
    centroid GEOMETRY,                 -- Point
    area_sq_km FLOAT
)

-- H3 hexagons as first-class territorial units
dim_h3_hex (
    hex_id VARCHAR(20) PRIMARY KEY,    -- H3 index string
    resolution INTEGER,
    center_lat DECIMAL(10,7),
    center_lon DECIMAL(10,7),
    area_sq_km FLOAT
)

-- Hex ↔ County bridge (many-to-many with coverage fraction)
bridge_h3_county (
    hex_id VARCHAR(20) REFERENCES dim_h3_hex,
    county_id INTEGER REFERENCES dim_county,
    coverage_fraction DECIMAL(5,4),    -- what % of hex is in this county
    PRIMARY KEY (hex_id, county_id)
)
```

______________________________________________________________________

## The Target Query

When complete, this query should produce the empirically-grounded tensor:

```sql
WITH national_ratios AS (
    SELECT
        bea_industry_id,
        time_id,
        intermediate_inputs_millions / NULLIF(gross_output_millions, 0) as c_ratio,
        value_added_millions / NULLIF(gross_output_millions, 0) as va_ratio
    FROM fact_bea_industry_national
),
county_tensor AS (
    SELECT
        c.fips as territory,
        sec.class_composition,
        t.year,
        -- Constant capital (derived)
        SUM((gdp.gdp_millions / NULLIF(nr.va_ratio, 0)) * nr.c_ratio) as c,
        -- Variable capital (direct from QCEW)
        SUM(q.total_annual_wages / 1e6) as v,
        -- Surplus value (residual)
        SUM(gdp.gdp_millions - q.total_annual_wages / 1e6) as s
    FROM fact_bea_county_gdp gdp
    JOIN national_ratios nr USING (bea_industry_id, time_id)
    JOIN dim_county c ON gdp.county_id = c.county_id
    JOIN dim_bea_industry bi ON gdp.bea_industry_id = bi.bea_industry_id
    JOIN bridge_naics_bea bnb ON bnb.bea_industry_id = bi.bea_industry_id
    JOIN fact_qcew_annual q ON c.county_id = q.county_id
    JOIN dim_industry i ON q.industry_id = i.industry_id
        AND i.naics_code = bnb.naics_code
    JOIN dim_sector sec ON i.sector_code = sec.sector_code
    JOIN dim_time t ON gdp.time_id = t.time_id
    GROUP BY c.fips, sec.class_composition, t.year
)
SELECT * FROM county_tensor;
```

Result shape: `T[territory (3000+ counties), class_composition (5-6 categories), {c, v, s}]`

______________________________________________________________________

## Data Availability Summary

| Component                | Measured Directly                | Derived From                         | Geographic Grain        |
| ------------------------ | -------------------------------- | ------------------------------------ | ----------------------- |
| **v** (wages)            | QCEW `total_annual_wages`        | —                                    | County                  |
| **v + s** (value-added)  | BEA County GDP                   | —                                    | County (~20 industries) |
| **s** (surplus)          | —                                | BEA GDP − QCEW wages                 | County                  |
| **c** (constant capital) | BEA national intermediate inputs | National ratio × county gross output | National ratio → County |
| **Gross output**         | BEA national                     | —                                    | National only           |

The key insight: BEA measures c directly at national level but only publishes (v+s) at county level. We bridge this by applying national `c / gross_output` ratios to county-level estimates.

______________________________________________________________________

## Success Criteria

### Data Completeness

- [ ] `fact_bea_industry_national` populated with gross output, intermediate inputs, value added for 2013-2024
- [ ] `fact_bea_county_gdp` populated for all ~3,200 counties, matching years
- [ ] `bridge_naics_bea` maps all NAICS codes in `dim_industry` to BEA industries
- [ ] `fact_price_deflator` has GDP deflator for all years in the dataset
- [ ] `dim_county_geometry` has polygons for all counties in `dim_county`
- [ ] `dim_h3_hex` generated at appropriate resolution (5-7) covering CONUS
- [ ] `bridge_h3_county` links hexes to counties with coverage fractions

### Accounting Identities

- [ ] National: `SUM(intermediate_inputs) + SUM(value_added) = SUM(gross_output)` (within rounding)
- [ ] By industry: `c_ratio + va_ratio ≈ 1.0` for each industry
- [ ] County totals: `SUM(county_gdp)` approximates state GDP (sanity check)

### Query Functionality

- [ ] Target tensor query executes without error
- [ ] Results have no NULL values for c, v, s where data should exist
- [ ] Results pass sanity checks: s > 0 (generally), c > 0, v > 0

______________________________________________________________________

## Key Relationships

```
                    ┌─────────────────────────────────────┐
                    │     fact_bea_industry_national      │
                    │  (gross_output, intermediate_inputs,│
                    │         value_added)                │
                    │         NATIONAL LEVEL              │
                    └───────────────┬─────────────────────┘
                                    │ c_ratio, va_ratio
                                    ▼
┌──────────────────┐    ┌─────────────────────────────────┐
│  fact_qcew_annual │───▶│      DERIVED TENSOR             │
│   (wages = v)     │    │   T[county, sector, {c,v,s}]    │
│   COUNTY LEVEL    │    └─────────────────────────────────┘
└──────────────────┘                ▲
                                    │
                    ┌───────────────┴─────────────────────┐
                    │       fact_bea_county_gdp           │
                    │      (gdp = value_added = v+s)      │
                    │          COUNTY LEVEL               │
                    └─────────────────────────────────────┘
```

______________________________________________________________________

## Marxist Interpretation

Once populated, this tensor enables:

1. **Exploitation rate** by territory: `s / v`
1. **Organic composition** by territory: `c / v`
1. **Profit rate** by territory: `s / (c + v)`
1. **Imperial rent** (when combined with international data): `W_core - V_core` where wages exceed value produced
1. **Unequal exchange**: Comparing `c/v/s` ratios across core vs periphery territories

The H3 hex grid enables spatial analysis of these dynamics — how exploitation clusters geographically, how profit rates vary by territory, where capital concentrates.
