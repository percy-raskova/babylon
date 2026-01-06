# SQLite Data Directory

This directory contains SQLite databases for the Babylon simulation engine.

## Databases

| File                      | Description                                 | Size   |
| ------------------------- | ------------------------------------------- | ------ |
| `marxist-data-3NF.sqlite` | Normalized data warehouse (3NF star schema) | ~500MB |
| `research.sqlite`         | Legacy research database (being migrated)   | Varies |

## Quick Start

### Prerequisites

```bash
# Ensure SQLite is available
sqlite3 --version

# Or use Python
poetry run python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

### Basic Connection

**Command Line:**

```bash
sqlite3 marxist-data-3NF.sqlite
```

**Python:**

```python
import sqlite3
from pathlib import Path

db_path = Path("data/sqlite/marxist-data-3NF.sqlite")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Example query
cursor.execute("SELECT COUNT(*) FROM dim_county")
print(f"Counties: {cursor.fetchone()[0]}")

conn.close()
```

**With Pandas:**

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect("data/sqlite/marxist-data-3NF.sqlite")

# Load a dimension table
df = pd.read_sql("SELECT * FROM dim_state", conn)

# Load fact data with joins
query = """
SELECT c.county_name, s.state_abbrev, m.median_income_usd
FROM fact_census_median_income m
JOIN dim_county c ON m.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
ORDER BY m.median_income_usd DESC
LIMIT 20
"""
top_income = pd.read_sql(query, conn)
conn.close()
```

## Database Schema

The `marxist-data-3NF.sqlite` database uses a Third Normal Form (3NF) star schema:

- **28 dimension tables** (`dim_*`) - Reference data with surrogate keys
- **21 fact tables** (`fact_*`) - Measurements linking to dimensions
- **1 bridge table** (`bridge_*`) - Many-to-many relationships

### List All Tables

```bash
sqlite3 marxist-data-3NF.sqlite ".tables"
```

### View Table Schema

```bash
sqlite3 marxist-data-3NF.sqlite ".schema dim_county"
```

### Row Counts

```sql
SELECT 'dim_state' as tbl, COUNT(*) as cnt FROM dim_state
UNION ALL SELECT 'dim_county', COUNT(*) FROM dim_county
UNION ALL SELECT 'fact_qcew_annual', COUNT(*) FROM fact_qcew_annual;
```

## Key Tables

### Geographic Dimensions

| Table            | Records | Description                        |
| ---------------- | ------- | ---------------------------------- |
| `dim_state`      | 52      | US states and territories          |
| `dim_county`     | 3,222   | US counties                        |
| `dim_metro_area` | 392     | Metropolitan Statistical Areas     |
| `dim_country`    | 263     | Countries (with world-system tier) |

### Economic Dimensions

| Table           | Records | Description          |
| --------------- | ------- | -------------------- |
| `dim_industry`  | 2,283   | NAICS industry codes |
| `dim_sector`    | 27      | NAICS sectors        |
| `dim_ownership` | 7       | QCEW ownership types |

### Fact Tables

| Table                    | Records | Description                         |
| ------------------------ | ------- | ----------------------------------- |
| `fact_qcew_annual`       | 2.8M+   | Employment/wages by county/industry |
| `fact_qcew_state_annual` | 50K+    | Employment/wages by state/industry  |
| `fact_qcew_metro_annual` | 200K+   | Employment/wages by MSA/Micro/CSA   |
| `fact_trade_monthly`     | 107K+   | Import/export by country            |
| `fact_census_income`     | 51K+    | Income distribution by county       |
| `fact_energy_annual`     | 16K     | Energy data by series               |

## Marxian Classifications

The schema embeds Marxian analytical categories:

### World-System Tiers (`dim_country.world_system_tier`)

```sql
SELECT world_system_tier, COUNT(*)
FROM dim_country
WHERE world_system_tier IS NOT NULL
GROUP BY world_system_tier;
```

- `core` - Imperial metropoles (USA, EU, Japan)
- `semi_periphery` - Intermediate states (Mexico, Brazil)
- `periphery` - Exploited nations

### Class Composition (`dim_sector.class_composition`)

```sql
SELECT class_composition, COUNT(*)
FROM dim_sector
GROUP BY class_composition;
```

- `goods_producing` - Manufacturing, construction
- `service_producing` - Services, retail
- `circulation` - Finance, real estate (non-productive)
- `government` - Public administration
- `extraction` - Mining, resources

### Wealth Classes (`dim_wealth_class.babylon_class`)

```sql
SELECT * FROM dim_wealth_class;
```

- `core_bourgeoisie` - Top 1% (ruling class)
- `petty_bourgeoisie` - 90-99%
- `labor_aristocracy` - 50-90%
- `internal_proletariat` - Bottom 50%

## Common Queries

### Employment by Class Composition

```sql
SELECT
    sec.class_composition,
    SUM(q.employment) as total_employment,
    ROUND(SUM(q.total_wages_usd) / 1e9, 2) as wages_billions
FROM fact_qcew_annual q
JOIN dim_industry i ON q.industry_id = i.industry_id
JOIN dim_sector sec ON i.sector_code = sec.sector_code
JOIN dim_time t ON q.time_id = t.time_id
WHERE t.year = 2023 AND sec.class_composition IS NOT NULL
GROUP BY sec.class_composition
ORDER BY total_employment DESC;
```

### Trade Balance by World-System Position

```sql
SELECT
    c.world_system_tier,
    ROUND(SUM(f.imports_usd_millions) / 1000, 1) as imports_billions,
    ROUND(SUM(f.exports_usd_millions) / 1000, 1) as exports_billions,
    ROUND(SUM(f.exports_usd_millions - f.imports_usd_millions) / 1000, 1) as balance
FROM fact_trade_monthly f
JOIN dim_country c ON f.country_id = c.country_id
JOIN dim_time t ON f.time_id = t.time_id
WHERE c.world_system_tier IS NOT NULL AND t.year = 2024
GROUP BY c.world_system_tier;
```

### Rent-Burdened Counties

```sql
SELECT
    c.county_name,
    s.state_abbrev,
    SUM(CASE WHEN rb.is_cost_burdened THEN rb_f.household_count ELSE 0 END) as burdened,
    SUM(rb_f.household_count) as total,
    ROUND(100.0 * SUM(CASE WHEN rb.is_cost_burdened THEN rb_f.household_count ELSE 0 END) /
          SUM(rb_f.household_count), 1) as pct_burdened
FROM fact_census_rent_burden rb_f
JOIN dim_rent_burden rb ON rb_f.burden_id = rb.burden_id
JOIN dim_county c ON rb_f.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
GROUP BY c.county_id
HAVING total > 1000
ORDER BY pct_burdened DESC
LIMIT 20;
```

### Energy Metabolism Overview

```sql
SELECT
    et.title,
    et.marxian_interpretation,
    COUNT(es.series_id) as series_count
FROM dim_energy_table et
JOIN dim_energy_series es ON et.table_id = es.table_id
GROUP BY et.table_id
ORDER BY et.table_code;
```

## Data Sources

| Source       | Coverage  | Frequency | Tables                                                                 |
| ------------ | --------- | --------- | ---------------------------------------------------------------------- |
| Census ACS   | 2022      | 5-Year    | `fact_census_*`                                                        |
| BLS QCEW     | 2013-2025 | Annual    | `fact_qcew_annual`, `fact_qcew_state_annual`, `fact_qcew_metro_annual` |
| Census Trade | 1949-2025 | Monthly   | `fact_trade_monthly`                                                   |
| FRED         | Various   | Various   | `fact_fred_*`                                                          |
| EIA          | 1949-2023 | Annual    | `fact_energy_annual`                                                   |
| USGS         | Various   | Annual    | `fact_commodity_*`, `fact_mineral_*`                                   |

## Loading New Data

The ETL pipeline is in `src/babylon/data/`. Use mise tasks:

```bash
# Load all data
mise run data:ingest

# Load QCEW data (hybrid: API for 2021+, files for 2013-2020)
mise run data:qcew

# Force API-only loading (requires network)
mise run data:qcew -- --force-api

# Force file-based loading (requires downloaded CSVs)
mise run data:qcew -- --force-files --data-path data/qcew

# Load FRED data
mise run data:fred
```

### QCEW Loading Strategy

QCEW data uses a **hybrid loading strategy**:

- **API (2021-2025)**: Fetches directly from BLS QCEW Open Data API (no setup required)
- **Files (2013-2020)**: Reads from local CSV files downloaded from BLS website

This hybrid approach provides:

- **Convenience**: Recent years load automatically via API
- **Coverage**: 13 years of historical data (2013-2025)
- **Flexibility**: Use `--force-api` or `--force-files` to override defaults

Three geographic levels are loaded:

- **County** (agglvl_code 70-78) → `fact_qcew_annual`
- **State** (agglvl_code 20-28) → `fact_qcew_state_annual`
- **Metro/CSA** (agglvl_code 30-58) → `fact_qcew_metro_annual`

## Performance Tips

1. **Use indexes**: Key columns are indexed (see schema)
1. **Filter early**: Apply WHERE clauses on dimensions before joining facts
1. **Aggregate wisely**: Use GROUP BY at the right level
1. **Limit results**: Use LIMIT during exploration

### Index Coverage

```sql
-- View all indexes
SELECT name, tbl_name FROM sqlite_master WHERE type = 'index';
```

Key indexes exist on:

- `dim_county(county_name)`, `dim_county(state_id)`
- `dim_industry(naics_level)`, `dim_industry(class_composition)`
- `dim_country(world_system_tier)`
- `fact_qcew_annual(county_id, time_id)`
- `fact_trade_monthly(country_id, time_id)`

## Detailed Reference

For complete schema documentation, see:

- `DATA_DICTIONARY.md` (this directory) - Quick reference
- `docs/reference/database-3nf.rst` - Full RST documentation
