# SQLite Data Directory

This directory contains the SQLite database for the Babylon simulation engine's data warehouse.

## Database Overview

| File                      | Description                                 | Size   |
| ------------------------- | ------------------------------------------- | ------ |
| `marxist-data-3NF.sqlite` | Normalized data warehouse (3NF star schema) | 3.4 GB |

**Contents:**

- 35 dimension tables (`dim_*`)
- 36 fact tables (`fact_*`)
- 5 bridge tables (`bridge_*`)
- 10 analytical views (`view_*`)
- 2 utility tables (`ingest_checkpoint`, `staging_arcgis_feature`)

**Time Coverage:** 1997-2024

______________________________________________________________________

## SQLite Installation

### Windows

**Chocolatey:**

```powershell
choco install sqlite
```

**Winget:**

```powershell
winget install SQLite.SQLite
```

**Manual:**

1. Download from [sqlite.org/download.html](https://sqlite.org/download.html)
1. Extract `sqlite-tools-win-x64-*.zip`
1. Add to PATH or run from extracted directory

### macOS

**Homebrew:**

```bash
brew install sqlite
```

SQLite is pre-installed on macOS. To get the latest version, use Homebrew.

### Linux

**Debian/Ubuntu:**

```bash
sudo apt update && sudo apt install sqlite3
```

**Fedora/RHEL:**

```bash
sudo dnf install sqlite
```

**Arch Linux:**

```bash
sudo pacman -S sqlite
```

### Verify Installation

```bash
sqlite3 --version
# Expected: 3.40+ (any recent version works)
```

______________________________________________________________________

## Connecting to the Database

### Command Line (sqlite3)

```bash
# Open the database
sqlite3 data/sqlite/marxist-data-3NF.sqlite

# Useful dot commands inside sqlite3:
.tables                  # List all tables
.schema dim_county       # Show table structure
.mode column             # Columnar output
.headers on              # Show column headers
.quit                    # Exit
```

**Quick queries from shell:**

```bash
# Count records
sqlite3 data/sqlite/marxist-data-3NF.sqlite "SELECT COUNT(*) FROM dim_county"

# Export to CSV
sqlite3 -header -csv data/sqlite/marxist-data-3NF.sqlite \
  "SELECT * FROM dim_state" > states.csv
```

### Python (sqlite3 module)

```python
import sqlite3
from pathlib import Path

db_path = Path("data/sqlite/marxist-data-3NF.sqlite")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Example: count counties
cursor.execute("SELECT COUNT(*) FROM dim_county")
print(f"Counties: {cursor.fetchone()[0]}")  # 3,234

# Example: list states
cursor.execute("SELECT state_abbrev, state_name FROM dim_state ORDER BY state_name")
for row in cursor.fetchall():
    print(row)

conn.close()
```

### Python (Pandas)

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect("data/sqlite/marxist-data-3NF.sqlite")

# Load a dimension table
df_states = pd.read_sql("SELECT * FROM dim_state", conn)
print(df_states.head())

# Load fact data with joins
query = """
SELECT
    c.county_name,
    s.state_abbrev,
    m.median_income_usd
FROM fact_census_median_income m
JOIN dim_county c ON m.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
JOIN dim_time t ON m.time_id = t.time_id
WHERE t.year = 2023
ORDER BY m.median_income_usd DESC
LIMIT 20
"""
top_income = pd.read_sql(query, conn)
print(top_income)

conn.close()
```

______________________________________________________________________

## Schema Overview

The database uses a **Third Normal Form (3NF) star schema** designed for Marxian economic analysis.

| Category   | Count | Description                        |
| ---------- | ----- | ---------------------------------- |
| Dimensions | 35    | Reference data with surrogate keys |
| Facts      | 36    | Measurements linking to dimensions |
| Bridges    | 5     | Many-to-many relationship mappings |
| Views      | 10    | Pre-built analytical queries       |

For complete schema documentation, see [data_dictionary.md](data_dictionary.md).

### List All Tables

```bash
sqlite3 data/sqlite/marxist-data-3NF.sqlite ".tables"
```

### View Table Schema

```bash
sqlite3 data/sqlite/marxist-data-3NF.sqlite ".schema dim_county"
```

______________________________________________________________________

## Quick Reference: Top Populated Tables

### Dimension Tables

| Table                      | Rows  | Description                          |
| -------------------------- | ----- | ------------------------------------ |
| `dim_geographic_hierarchy` | 6,468 | State-county allocation weights      |
| `dim_county`               | 3,234 | US counties (primary domestic grain) |
| `dim_county_geometry`      | 3,222 | County spatial coordinates           |
| `dim_industry`             | 2,416 | NAICS codes with class composition   |
| `dim_metro_area`           | 1,119 | MSA/Micropolitan/CSA areas           |
| `dim_time`                 | 268   | Time periods (1997-2024)             |
| `dim_bea_industry`         | 100   | BEA industry classification          |
| `dim_occupation`           | 74    | Census occupations with labor type   |
| `dim_poverty_category`     | 60    | Poverty ratio categories             |
| `dim_state`                | 52    | US states and territories            |

### Fact Tables

| Table                       | Rows       | Description                        |
| --------------------------- | ---------- | ---------------------------------- |
| `fact_census_poverty`       | 26,576,550 | Poverty status by county/category  |
| `fact_census_occupation`    | 8,108,076  | Employment by occupation/county    |
| `fact_census_income`        | 7,207,200  | Income distribution by county      |
| `fact_bea_county_gdp`       | 1,995,283  | County GDP by industry (1997-2024) |
| `fact_census_housing`       | 1,351,380  | Housing tenure by county           |
| `fact_census_commute`       | 945,945    | Commute mode by county             |
| `fact_census_worker_class`  | 900,900    | Worker class by county             |
| `fact_census_rent_burden`   | 450,450    | Rent burden by county              |
| `fact_census_median_income` | 314,704    | Median income by county/year       |
| `fact_qcew_metro_annual`    | 20,893     | Employment/wages by metro area     |

### Bridge Tables

| Table                 | Rows   | Description                  |
| --------------------- | ------ | ---------------------------- |
| `bridge_county_h3`    | 38,538 | H3 hexagon to county mapping |
| `bridge_county_metro` | 3,256  | County to MSA/CSA mapping    |

______________________________________________________________________

## Example Queries

### Basic Dimension Query

```sql
-- List all states with abbreviations
SELECT state_fips, state_abbrev, state_name
FROM dim_state
ORDER BY state_name;
```

### Fact Table with Joins

```sql
-- Top 10 counties by median income (2023)
SELECT
    c.county_name,
    s.state_abbrev,
    m.median_income_usd
FROM fact_census_median_income m
JOIN dim_county c ON m.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
JOIN dim_time t ON m.time_id = t.time_id
WHERE t.year = 2023
ORDER BY m.median_income_usd DESC
LIMIT 10;
```

### Analytical View Usage

```sql
-- Wealth distribution by Babylon class
SELECT * FROM view_wealth_concentration;
```

### County GDP Analysis

```sql
-- Total GDP by state (most recent year)
SELECT
    s.state_abbrev,
    ROUND(SUM(g.gdp_thousands) / 1000000.0, 2) as gdp_billions
FROM fact_bea_county_gdp g
JOIN dim_county c ON g.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
JOIN dim_time t ON g.time_id = t.time_id
WHERE t.year = 2023
GROUP BY s.state_id
ORDER BY gdp_billions DESC
LIMIT 10;
```

### Rent Burden Analysis

```sql
-- Counties with highest rent burden (% cost-burdened households)
SELECT
    c.county_name,
    s.state_abbrev,
    SUM(CASE WHEN rb.is_cost_burdened THEN f.household_count ELSE 0 END) as burdened,
    SUM(f.household_count) as total,
    ROUND(100.0 * SUM(CASE WHEN rb.is_cost_burdened THEN f.household_count ELSE 0 END) /
          NULLIF(SUM(f.household_count), 0), 1) as pct_burdened
FROM fact_census_rent_burden f
JOIN dim_rent_burden rb ON f.burden_id = rb.burden_id
JOIN dim_county c ON f.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
GROUP BY c.county_id
HAVING total > 10000
ORDER BY pct_burdened DESC
LIMIT 20;
```

______________________________________________________________________

## Data Loading

The ETL pipeline is located in `src/babylon/data/`. Use mise tasks to load data:

### Key Commands

```bash
# Load all data sources
mise run data:load

# Individual loaders
mise run data:census         # Census ACS data
mise run data:fred           # FRED macroeconomic data
mise run data:bea-county     # BEA county GDP
mise run data:qcew           # QCEW employment/wages
mise run data:geography      # Geographic hierarchies

# List all data tasks
mise tasks | grep "^data:"
```

### Data Sources

| Source     | Coverage   | Tables                      |
| ---------- | ---------- | --------------------------- |
| Census ACS | 2010, 2023 | `fact_census_*` (17 tables) |
| BEA        | 1997-2024  | `fact_bea_county_gdp`       |
| FRED       | 2010-2024  | `fact_fred_*` (5 tables)    |
| QCEW       | Various    | `fact_qcew_*` (3 tables)    |

______________________________________________________________________

## Performance Tips

### Use Indexes

Key columns are indexed for fast lookups:

```sql
-- View all indexes
SELECT name, tbl_name FROM sqlite_master WHERE type = 'index';
```

### PRAGMA Settings for Large Queries

```sql
-- Increase cache for large analytical queries
PRAGMA cache_size = -64000;  -- 64MB cache
PRAGMA temp_store = MEMORY;  -- Keep temp tables in memory
```

### Query Optimization

1. **Filter early**: Apply WHERE clauses on dimension tables before joining facts
1. **Use indexes**: Filter on indexed columns (county_id, time_id, state_id)
1. **Aggregate wisely**: Use GROUP BY at the appropriate grain
1. **Limit during exploration**: Use LIMIT when exploring large tables

### Example: Efficient Query Pattern

```sql
-- Filter on indexed dimension columns, then join
SELECT
    c.county_name,
    SUM(f.value) as total
FROM fact_census_poverty f
JOIN dim_county c ON f.county_id = c.county_id
JOIN dim_time t ON f.time_id = t.time_id
WHERE t.year = 2023           -- Filter on indexed column
  AND c.state_id = 6          -- Filter on indexed FK
GROUP BY c.county_id
ORDER BY total DESC
LIMIT 20;
```

______________________________________________________________________

## Detailed Reference

For complete schema documentation including all columns, constraints, and Marxian classifications:

- [data_dictionary.md](data_dictionary.md) - Full data dictionary
- `src/babylon/data/reference/schema.py` - Schema definitions in code
