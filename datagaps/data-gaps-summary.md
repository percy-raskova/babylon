# Babylon Data Gaps: Tensor & Spatial Infrastructure

## Summary

Two foundational capabilities require additional data:

1. **Rank-2 Value Tensor** T[territory, sector, {c, v, s}] — requires constant capital estimation
1. **H3 Spatial Manifold** — requires county geometries and hex grid infrastructure

______________________________________________________________________

## Current State

What you have and can derive today:

| Component             | Source                                         | Status                |
| --------------------- | ---------------------------------------------- | --------------------- |
| v (wages)             | QCEW `total_annual_wages`                      | ✅ Direct measurement |
| Employment            | QCEW `annual_avg_emplvl`                       | ✅ Direct measurement |
| v + s (value-added)   | BEA GDP by county                              | ✅ Direct measurement |
| s (surplus)           | BEA GDP − QCEW wages                           | ✅ Derivable          |
| Sector classification | `dim_sector.class_composition`                 | ✅ Complete           |
| International flows   | Census trade × `dim_country.world_system_tier` | ✅ Complete           |

**BEA Data Availability by Geographic Level:**

| Level    | Gross Output     | Intermediate Inputs (c) | Value Added (v+s)          |
| -------- | ---------------- | ----------------------- | -------------------------- |
| National | ✅ Direct        | ✅ Direct               | ✅ Direct                  |
| State    | ❌ Not published | ❌ Not published        | ✅ Direct                  |
| County   | ❌ Not published | ❌ Not published        | ✅ Direct (~20 industries) |

This is why we need national-level ratios: BEA measures c directly at national level, but only publishes (v+s) at county level. The solution is to apply national `c / gross_output` ratios to county-level estimates of gross output.

______________________________________________________________________

## Critical Gaps

### 1. Constant Capital (c) — Completes the Value Tensor

**Key Insight:** BEA publishes gross output, intermediate inputs, and value added directly at the national level by industry. This is simpler than using I-O Use Tables — the decomposition is already done.

| Measure             | BEA Definition                     | Marxist Equivalent       |
| ------------------- | ---------------------------------- | ------------------------ |
| Gross Output        | Total production value             | c + v + s                |
| Intermediate Inputs | Purchased inputs consumed          | **c (constant capital)** |
| Value Added         | Gross output − intermediate inputs | v + s                    |

| Data Need                              | Source              | URL                                                                                                         | Format  | Grain                            |
| -------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------- | ------- | -------------------------------- |
| **Gross Output by Industry**           | BEA GDP by Industry | https://apps.bea.gov/iTable/?reqid=150                                                                      | CSV/API | National, ~70 industries, annual |
| **Intermediate Inputs by Industry**    | BEA GDP by Industry | https://apps.bea.gov/iTable/?reqid=150                                                                      | CSV/API | National, ~70 industries, annual |
| **Value Added by Industry**            | BEA GDP by Industry | https://apps.bea.gov/iTable/?reqid=150                                                                      | CSV/API | National, ~70 industries, annual |
| **GDP by County with Industry Detail** | BEA Regional        | https://apps.bea.gov/iTable/?reqid=70                                                                       | CSV/API | County, ~20 industries, annual   |
| **BEA-NAICS Concordance**              | BEA                 | https://www.bea.gov/sites/default/files/2023-10/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx | XLSX    | Industry crosswalk               |

**Schema additions required:**

```sql
-- Dimension: BEA industry definitions (from GDP by Industry tables)
CREATE TABLE dim_bea_industry (
    bea_industry_id INTEGER PRIMARY KEY,
    bea_code VARCHAR(10) UNIQUE NOT NULL,
    bea_title VARCHAR(200) NOT NULL,
    parent_bea_code VARCHAR(10),  -- for hierarchy (sector → subsector)
    is_goods_producing BOOLEAN,
    is_service_producing BOOLEAN
);

-- Bridge: NAICS → BEA industry (many-to-one)
CREATE TABLE bridge_naics_bea (
    naics_code VARCHAR(20) PRIMARY KEY,
    bea_industry_id INTEGER REFERENCES dim_bea_industry,
    mapping_quality VARCHAR(20)  -- 'exact', 'approximate', 'sector_fallback'
);

-- Fact: National industry coefficients (direct from BEA GDP by Industry)
CREATE TABLE fact_bea_industry_national (
    bea_industry_id INTEGER REFERENCES dim_bea_industry,
    time_id INTEGER REFERENCES dim_time,
    gross_output_millions DECIMAL(15,2),
    intermediate_inputs_millions DECIMAL(15,2),  -- THIS IS c AT NATIONAL LEVEL
    value_added_millions DECIMAL(15,2),          -- THIS IS (v+s) AT NATIONAL LEVEL
    -- Derived ratios for county-level application
    c_ratio DECIMAL(8,6) GENERATED ALWAYS AS
        (intermediate_inputs_millions / NULLIF(gross_output_millions, 0)) STORED,
    va_ratio DECIMAL(8,6) GENERATED ALWAYS AS
        (value_added_millions / NULLIF(gross_output_millions, 0)) STORED,
    PRIMARY KEY (bea_industry_id, time_id)
);

-- Fact: County GDP (value-added only — what BEA provides at county level)
CREATE TABLE fact_bea_county_gdp (
    county_id INTEGER REFERENCES dim_county,
    bea_industry_id INTEGER REFERENCES dim_bea_industry,
    time_id INTEGER REFERENCES dim_time,
    gdp_millions DECIMAL(15,2),  -- This is value-added (v+s)
    PRIMARY KEY (county_id, bea_industry_id, time_id)
);
```

**Derivation formula:**

```sql
-- Step 1: Get national ratios (direct from BEA)
c_ratio[industry] = intermediate_inputs[industry] / gross_output[industry]
va_ratio[industry] = value_added[industry] / gross_output[industry]

-- Step 2: Estimate county gross output from county value-added
gross_output[county, industry] = value_added[county, industry] / va_ratio[industry]

-- Step 3: Apply c_ratio to get county-level constant capital
c[county, industry] = gross_output[county, industry] × c_ratio[industry]
```

**Geographic limitation:** BEA publishes county GDP at ~20 industry level (less detailed than national ~70). The bridge table handles this by mapping detailed NAICS to the appropriate BEA industry level available at each geographic grain.

______________________________________________________________________

### 2. Price Deflators — Methodological Necessity

| Data Need             | Source     | URL                                          | Format    | Grain                 |
| --------------------- | ---------- | -------------------------------------------- | --------- | --------------------- |
| **CPI by Metro Area** | BLS        | https://www.bls.gov/cpi/data.htm             | API / CSV | Metro area, monthly   |
| **PCE Price Index**   | BEA        | https://apps.bea.gov/iTable/ → Price Indexes | CSV       | National, by category |
| **GDP Deflator**      | BEA / FRED | FRED series `GDPDEF`                         | API       | National, quarterly   |

**Schema additions required:**

```sql
CREATE TABLE dim_deflator_series (
    deflator_id INTEGER PRIMARY KEY,
    series_code VARCHAR(50) UNIQUE NOT NULL,
    series_name VARCHAR(200),
    base_year INTEGER,  -- e.g., 2017
    geographic_scope VARCHAR(50)  -- 'national', 'metro', 'state'
);

CREATE TABLE fact_price_deflator (
    deflator_id INTEGER REFERENCES dim_deflator_series,
    time_id INTEGER REFERENCES dim_time,
    metro_area_id INTEGER REFERENCES dim_metro_area,  -- NULL for national
    deflator_value DECIMAL(10,6),  -- base_year = 1.0 or 100.0
    PRIMARY KEY (deflator_id, time_id, metro_area_id)
);
```

**Usage:** Multiply all nominal dollar values by `(base_year_deflator / current_deflator)` to get real values.

______________________________________________________________________

### 3. County Geometries — Enables All Spatial Operations

| Data Need                        | Source  | URL                                                                                   | Format              | Grain           |
| -------------------------------- | ------- | ------------------------------------------------------------------------------------- | ------------------- | --------------- |
| **TIGER/Line County Boundaries** | Census  | https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html | Shapefile / GeoJSON | County polygons |
| **County Centroids**             | Derived | (calculate from polygons)                                                             | —                   | Points          |

**Schema additions required:**

```sql
-- If using SpatiaLite
CREATE TABLE dim_county_geometry (
    county_id INTEGER PRIMARY KEY REFERENCES dim_county,
    fips VARCHAR(5) NOT NULL,
    geometry MULTIPOLYGON,  -- WGS84 (EPSG:4326)
    centroid POINT,
    area_sq_km FLOAT,
    perimeter_km FLOAT
);

SELECT CreateSpatialIndex('dim_county_geometry', 'geometry');
```

```sql
-- If using DuckDB spatial extension
ALTER TABLE dim_county ADD COLUMN geometry GEOMETRY;
ALTER TABLE dim_county ADD COLUMN centroid GEOMETRY;
ALTER TABLE dim_county ADD COLUMN area_sq_km FLOAT;
```

______________________________________________________________________

### 4. H3 Hex Grid — The Discrete Manifold

| Data Need               | Source  | URL                | Format                | Grain          |
| ----------------------- | ------- | ------------------ | --------------------- | -------------- |
| **H3 Grid Generation**  | Uber H3 | https://h3geo.org/ | Library (Python `h3`) | Resolution 4-7 |
| **Hex ↔ County Bridge** | Derived | (spatial join)     | —                     | Many-to-many   |

**Schema additions required:**

```sql
-- H3 hexagons as first-class entities
CREATE TABLE dim_h3_hex (
    hex_id VARCHAR(20) PRIMARY KEY,  -- H3 index string
    resolution INTEGER NOT NULL,
    center_lat DECIMAL(10,7),
    center_lon DECIMAL(10,7),
    area_sq_km FLOAT
);

-- Bridge: hex ↔ county (many-to-many with coverage fraction)
CREATE TABLE bridge_h3_county (
    hex_id VARCHAR(20) REFERENCES dim_h3_hex,
    county_id INTEGER REFERENCES dim_county,
    coverage_fraction DECIMAL(5,4),  -- what % of hex is in this county
    PRIMARY KEY (hex_id, county_id)
);

-- Optional: precomputed adjacency for graph construction
CREATE TABLE bridge_h3_adjacency (
    hex_id VARCHAR(20) REFERENCES dim_h3_hex,
    neighbor_hex_id VARCHAR(20) REFERENCES dim_h3_hex,
    edge_type VARCHAR(20) DEFAULT 'ADJACENCY',
    PRIMARY KEY (hex_id, neighbor_hex_id)
);
```

**Generation workflow:**

```python
import h3

# Generate hexes covering CONUS at resolution 5 (~250 km² per hex)
hexes = h3.polyfill_geojson(conus_geojson, res=5)

# For each hex, spatial join to counties
for hex_id in hexes:
    boundary = h3.h3_to_geo_boundary(hex_id, geo_json=True)
    # intersect with county geometries, compute coverage_fraction
```

______________________________________________________________________

### 5. Carceral Data — George Jackson Model Calibration

| Data Need             | Source                  | URL                                                                  | Format  | Grain                       |
| --------------------- | ----------------------- | -------------------------------------------------------------------- | ------- | --------------------------- |
| **Jail Population**   | Vera Institute          | https://github.com/vera-institute/incarceration-trends               | CSV     | County, annual              |
| **Prison Population** | BJS                     | https://bjs.ojp.gov/data-collection/national-prisoner-statistics-nps | CSV/API | State (apportion to county) |
| **Police Employment** | FBI UCR / BLS           | https://crime-data-explorer.fr.cloud.gov/                            | API     | Agency → County             |
| **Police Killings**   | Mapping Police Violence | https://mappingpoliceviolence.org/aboutthedata                       | CSV     | Incident-level with county  |

**Schema additions required:**

```sql
CREATE TABLE fact_incarceration (
    county_id INTEGER REFERENCES dim_county,
    time_id INTEGER REFERENCES dim_time,
    jail_population INTEGER,
    jail_admissions INTEGER,
    incarceration_rate_per_100k DECIMAL(10,2),
    PRIMARY KEY (county_id, time_id)
);

CREATE TABLE fact_police_employment (
    county_id INTEGER REFERENCES dim_county,
    time_id INTEGER REFERENCES dim_time,
    sworn_officers INTEGER,
    civilian_employees INTEGER,
    officers_per_capita DECIMAL(10,4),
    PRIMARY KEY (county_id, time_id)
);

-- Feeds repression parameter in survival calculus
CREATE TABLE fact_police_violence (
    incident_id INTEGER PRIMARY KEY,
    county_id INTEGER REFERENCES dim_county,
    date DATE,
    was_fatal BOOLEAN,
    victim_armed BOOLEAN,
    victim_race_id INTEGER REFERENCES dim_race
);
```

______________________________________________________________________

### 6. International Wages — Imperial Rent Calculation

| Data Need             | Source      | URL                                             | Format    | Grain           |
| --------------------- | ----------- | ----------------------------------------------- | --------- | --------------- |
| **Wages by Country**  | ILO ILOSTAT | https://ilostat.ilo.org/data/                   | API / CSV | Country, annual |
| **PPP Conversion**    | World Bank  | https://data.worldbank.org/indicator/PA.NUS.PPP | API / CSV | Country, annual |
| **Penn World Tables** | GGDC        | https://www.rug.nl/ggdc/productivity/pwt/       | XLSX      | Country, annual |

**Schema additions required:**

```sql
ALTER TABLE dim_country ADD COLUMN avg_hourly_wage_usd DECIMAL(10,4);
ALTER TABLE dim_country ADD COLUMN ppp_conversion_factor DECIMAL(10,4);

CREATE TABLE fact_country_wages (
    country_id INTEGER REFERENCES dim_country,
    time_id INTEGER REFERENCES dim_time,
    avg_hourly_wage_local DECIMAL(15,4),
    avg_hourly_wage_usd DECIMAL(15,4),
    avg_hourly_wage_ppp DECIMAL(15,4),
    manufacturing_wage_usd DECIMAL(15,4),
    PRIMARY KEY (country_id, time_id)
);
```

**Imperial rent derivation:**

```
Φ = W_core - W_periphery  (for equivalent labor)
```

______________________________________________________________________

### 7. Labor Productivity — Direct SNLT Proxy

| Data Need                    | Source           | URL                                       | Format | Grain               |
| ---------------------------- | ---------------- | ----------------------------------------- | ------ | ------------------- |
| **Output per Hour**          | BLS Productivity | https://www.bls.gov/productivity/data.htm | API    | Industry, quarterly |
| **Multifactor Productivity** | BLS              | https://www.bls.gov/mfp/data.htm          | API    | Industry, annual    |

**Schema additions required:**

```sql
CREATE TABLE fact_productivity (
    industry_id INTEGER REFERENCES dim_industry,
    time_id INTEGER REFERENCES dim_time,
    output_per_hour_index DECIMAL(10,4),  -- base year = 100
    unit_labor_cost_index DECIMAL(10,4),
    multifactor_productivity_index DECIMAL(10,4),
    PRIMARY KEY (industry_id, time_id)
);
```

**SNLT derivation:**

```
SNLT_relative[sector_A, sector_B] = productivity[B] / productivity[A]
```

______________________________________________________________________

## Priority Ranking

| Priority | Gap                            | Rationale                                                            |
| -------- | ------------------------------ | -------------------------------------------------------------------- |
| **P0**   | Price deflators                | Without this, all time-series analysis is methodologically invalid   |
| **P0**   | County geometries              | Prerequisite for any spatial operations                              |
| **P1**   | BEA GDP by Industry (national) | Provides c_ratio and va_ratio — the key to deriving constant capital |
| **P1**   | BEA County GDP + NAICS bridge  | Completes c/v/s tensor when combined with QCEW                       |
| **P1**   | H3 grid + county bridge        | Enables territorial discretization                                   |
| **P2**   | Carceral data                  | Calibrates George Jackson bifurcation model                          |
| **P2**   | Labor productivity             | Direct SNLT measurement, enables unequal exchange                    |
| **P3**   | International wages            | Enables imperial rent magnitude calculation                          |
| **P3**   | Capital expenditure            | Investment flow dynamics (where is new c going?)                     |

**Note on simplification:** The original approach used I-O Use Tables to derive intermediate input coefficients. The updated approach uses BEA GDP by Industry tables directly, which already decompose gross output into intermediate inputs + value added. This is simpler and more authoritative — BEA has already done the accounting.

______________________________________________________________________

## DuckDB vs SpatiaLite Decision

**Recommendation:** Hybrid architecture.

```
marxist-data-3NF.duckdb     → All fact/dimension tables, analytical queries
    ↓ (join on county FIPS)
geometry.sqlite (SpatiaLite) → County polygons, H3 grid, spatial indices
```

Rationale:

- DuckDB excels at columnar aggregation over millions of QCEW/Census rows
- SpatiaLite has mature, battle-tested spatial operations
- Both are single-file, embedded databases
- Join key (county FIPS) is simple and stable

Alternative: DuckDB spatial extension is maturing. If you want single-database simplicity and can accept younger spatial tooling, keep everything in DuckDB.

______________________________________________________________________

## Tensor Query (Once Gaps Filled)

```sql
-- T[county, class_composition, {c, v, s}] from real federal data
WITH national_ratios AS (
    -- Get c_ratio and va_ratio directly from BEA GDP by Industry (national)
    SELECT
        bea_industry_id,
        time_id,
        c_ratio,
        va_ratio
    FROM fact_bea_industry_national
),
county_decomposition AS (
    -- Apply national ratios to county-level value-added
    SELECT
        gdp.county_id,
        gdp.bea_industry_id,
        gdp.time_id,
        -- Estimate gross output from value-added
        gdp.gdp_millions / NULLIF(nr.va_ratio, 0) as gross_output,
        -- Derive c from gross output × c_ratio
        (gdp.gdp_millions / NULLIF(nr.va_ratio, 0)) * nr.c_ratio as c_millions,
        -- v comes from QCEW wages (joined separately)
        -- s = value_added - v (derived after QCEW join)
        gdp.gdp_millions as va_millions  -- (v + s)
    FROM fact_bea_county_gdp gdp
    JOIN national_ratios nr
        ON gdp.bea_industry_id = nr.bea_industry_id
        AND gdp.time_id = nr.time_id
)
SELECT
    c.fips as territory,
    sec.class_composition,
    -- Constant capital (derived via national ratios)
    SUM(cd.c_millions * deflator.adjustment) as c,
    -- Variable capital (direct from QCEW, deflated)
    SUM(q.total_annual_wages / 1e6 * deflator.adjustment) as v,
    -- Surplus value (value-added minus wages, deflated)
    SUM((cd.va_millions - q.total_annual_wages / 1e6) * deflator.adjustment) as s
FROM county_decomposition cd
JOIN dim_county c ON cd.county_id = c.county_id
JOIN fact_bea_county_gdp gdp ON cd.county_id = gdp.county_id AND cd.time_id = gdp.time_id
JOIN dim_bea_industry bi ON cd.bea_industry_id = bi.bea_industry_id
-- Bridge from QCEW NAICS to BEA industry
JOIN fact_qcew_annual q ON c.county_id = q.county_id
JOIN dim_industry i ON q.industry_id = i.industry_id
JOIN bridge_naics_bea bnb ON i.naics_code = bnb.naics_code AND bnb.bea_industry_id = cd.bea_industry_id
JOIN dim_sector sec ON i.sector_code = sec.sector_code
JOIN dim_time t ON cd.time_id = t.time_id
-- Deflator for real values
LEFT JOIN fact_price_deflator deflator
    ON t.time_id = deflator.time_id AND deflator.series_code = 'GDPDEF'
WHERE t.year = 2023
GROUP BY c.fips, sec.class_composition;
```

This produces the empirically-grounded rank-2 value tensor:

- **c**: Derived from BEA national intermediate inputs ratios applied to county gross output
- **v**: Direct from QCEW wages
- **s**: Residual (BEA county value-added minus QCEW wages)
- All values inflation-adjusted via GDP deflator
