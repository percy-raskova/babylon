# SQLite Documentation Update Plan

## Overview

Update `data/sqlite/README.md` and `data/sqlite/data_dictionary.md` to accurately reflect the actual schema and data in `marxist-data-3NF.sqlite`. The README will become a comprehensive how-to guide for SQLite setup on all platforms, while the data dictionary will document all 68 database objects with accurate row counts and technical descriptions with brief Marxian context.

## Current State Analysis

The existing documentation is significantly out of date:

| Category | Documented | Actual | Gap |
|----------|------------|--------|-----|
| Dimension tables | 28 | 35 | +7 |
| Fact tables | 21 | 28 | +7 |
| Bridge tables | 1 | 5 | +4 |
| Views | 8 | 10 | +2 |
| Database size | ~500MB | 3.4GB | +2.9GB |

### Key Discoveries

1. **Database file**: 3.4GB (documented as ~500MB)
2. **Time coverage**: 1997-2024 (verified from `dim_time`)
3. **Schema source**: `src/babylon/data/reference/schema.py`
4. **Many documented tables have 0 rows** - ETL pipelines exist but data not yet loaded
5. **Several undocumented tables have millions of rows** (e.g., `fact_bea_county_gdp`: 2M rows)

## Desired End State

### README.md
A complete how-to guide that enables any user to:
1. Install SQLite on Windows, macOS, or Linux
2. Connect to the database via CLI and Python
3. Run basic queries with Pandas
4. Understand the schema structure at a glance

### data_dictionary.md
A complete technical reference that documents:
1. All 35 dimension tables with columns, constraints, and brief Marxian context
2. All 28 fact tables with measures, foreign keys, and row counts
3. All 5 bridge tables with their mapping purpose
4. All 10 analytical views with their SQL definitions and use cases
5. Data source attribution and coverage periods

### Verification

After completion:
- All table/view counts in docs match `sqlite3 .tables` output
- All row counts are accurate (within 1% for large tables)
- All column names match `sqlite3 .schema` output
- Example queries execute successfully

## What We're NOT Doing

- Not modifying any Python code or schema definitions
- Not loading data into empty tables
- Not changing the database structure
- Not creating new views or indexes
- Not adding documentation outside `data/sqlite/` directory

## Implementation Approach

Two-phase approach:
1. **Phase 1**: Update README.md as a comprehensive SQLite setup and usage guide
2. **Phase 2**: Update data_dictionary.md with accurate schema documentation

Both phases use data extracted directly from the database to ensure accuracy.

---

## Phase 1: Update README.md

### Overview
Transform the README into a complete SQLite setup and usage guide for Windows, macOS, and Linux, with Python integration examples.

### Changes Required

#### File: `data/sqlite/README.md`

Complete rewrite with the following sections:

1. **Header & Overview**
   - Database name, size (3.4GB), and purpose
   - Quick summary of contents (35 dimensions, 28 facts, 5 bridges, 10 views)

2. **SQLite Installation (Full Guide)**
   - **Windows**: Chocolatey, Winget, and manual download instructions
   - **macOS**: Homebrew and manual download instructions
   - **Linux**: apt (Debian/Ubuntu), dnf (Fedora/RHEL), pacman (Arch) instructions
   - Version verification commands for each platform

3. **Connecting to the Database**
   - CLI connection with examples
   - Useful SQLite dot commands (`.tables`, `.schema`, `.mode`, `.headers`)
   - Python connection with `sqlite3` module
   - Python connection with Pandas

4. **Schema Overview**
   - Table counts by category (accurate)
   - File size and time coverage
   - Link to data_dictionary.md for details

5. **Quick Reference Tables**
   - Top 10 populated dimension tables with row counts
   - Top 10 populated fact tables with row counts
   - Empty tables note (data awaiting ETL)

6. **Example Queries**
   - Basic dimension query
   - Fact table with JOIN
   - View usage
   - Pandas integration example

7. **Performance Tips**
   - Index coverage
   - Query optimization basics
   - Memory settings for large queries

8. **Data Loading**
   - Brief mention of ETL pipeline location
   - Link to mise tasks for data loading

### Success Criteria

#### Automated Verification:
- [ ] File exists at `data/sqlite/README.md`
- [ ] All example queries execute without error: `sqlite3 marxist-data-3NF.sqlite < test_queries.sql`
- [ ] Table counts in docs match: `sqlite3 marxist-data-3NF.sqlite "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"`
- [ ] Markdown linting passes: `markdownlint data/sqlite/README.md`

#### Manual Verification:
- [ ] SQLite installation instructions work on a fresh Windows machine
- [ ] SQLite installation instructions work on a fresh macOS machine
- [ ] Python connection example executes successfully
- [ ] Pandas example produces expected output

---

## Phase 2: Update data_dictionary.md

### Overview
Complete rewrite of the data dictionary with accurate schema documentation for all 68 database objects, organized by category with brief Marxian context.

### Changes Required

#### File: `data/sqlite/data_dictionary.md`

Complete rewrite with the following sections:

1. **Header & Metadata**
   - Database file path
   - Schema source file reference
   - Last updated date
   - Data coverage period (1997-2024)

2. **Overview**
   - 3NF star schema description
   - Table count summary (35 dim, 28 fact, 5 bridge, 10 view)
   - Brief Marxian framework context

3. **Dimension Tables (35 total)**

   **Geographic Dimensions (9 tables)**
   - `dim_state` (52 rows) - US states and territories
   - `dim_county` (3,234 rows) - Primary domestic grain
   - `dim_county_geometry` (3,222 rows) - Spatial coordinates
   - `dim_metro_area` (1,119 rows) - MSA/Micropolitan/CSA
   - `dim_cfs_area` (0 rows) - Census CFS zones (awaiting data)
   - `dim_geographic_hierarchy` (6,468 rows) - State-county allocation weights
   - `dim_country` (0 rows) - Trade partners (awaiting data)
   - `dim_import_source` (0 rows) - Import sources (awaiting data)
   - `dim_employment_area` (0 rows) - Employment areas (awaiting data)

   **Industry & Economic Dimensions (6 tables)**
   - `dim_industry` (2,416 rows) - NAICS hierarchy with class composition
   - `dim_sector` (0 rows) - 2-digit sectors (awaiting data)
   - `dim_ownership` (6 rows) - QCEW ownership types
   - `dim_bea_industry` (100 rows) - BEA industry classification
   - `dim_sctg_commodity` (42 rows) - Transported goods codes
   - `dim_coercive_type` (0 rows) - State apparatus (awaiting data)

   **Census Code Dimensions (10 tables)**
   - `dim_income_bracket` (17 rows) - Income distribution brackets
   - `dim_employment_status` (8 rows) - Labor force status
   - `dim_worker_class` (22 rows) - Class of worker with Marxian mapping
   - `dim_occupation` (74 rows) - Occupations with labor type
   - `dim_education_level` (26 rows) - Educational attainment
   - `dim_housing_tenure` (3 rows) - Owner/renter status
   - `dim_rent_burden` (11 rows) - Rent burden brackets
   - `dim_commute_mode` (22 rows) - Transportation modes
   - `dim_poverty_category` (60 rows) - Poverty status
   - `dim_race` (10 rows) - Race/ethnicity (Census A-I scheme)

   **Energy & FRED Dimensions (6 tables)**
   - `dim_energy_table` (0 rows) - Energy tables (awaiting data)
   - `dim_energy_series` (0 rows) - Energy series (awaiting data)
   - `dim_wealth_class` (4 rows) - FRED wealth percentiles
   - `dim_asset_category` (3 rows) - Asset categories
   - `dim_fred_series` (31 rows) - FRED series metadata

   **Material Dimensions (2 tables)**
   - `dim_commodity` (0 rows) - Critical commodities (awaiting data)
   - `dim_commodity_metric` (0 rows) - Commodity metrics (awaiting data)

   **Metadata Dimensions (2 tables)**
   - `dim_time` (268 rows) - Calendar dimension (1997-2024)
   - `dim_gender` (3 rows) - Male/Female/Total
   - `dim_data_source` (6 rows) - Data provenance

4. **Fact Tables (28 total)**

   **Census Facts (17 tables)** - Source: US Census Bureau ACS
   - Document all with row counts and measures

   **QCEW & Productivity Facts (3 tables)** - Source: BLS
   - Document with employment/wage measures

   **BEA GDP Facts (2 tables)** - Source: Bureau of Economic Analysis
   - Document with GDP measures

   **FRED Facts (5 tables)** - Source: Federal Reserve
   - Document with wealth/unemployment measures

   **Trade & Materials Facts (1+ tables)**
   - Document with import/export measures

5. **Bridge Tables (5 total)**
   - `bridge_county_metro` (3,256 rows)
   - `bridge_county_h3` (38,538 rows)
   - `bridge_cfs_county` (0 rows)
   - `bridge_lodes_block` (0 rows)
   - `bridge_naics_bea` (0 rows)

6. **Analytical Views (10 total)**
   - Full SQL definition for each
   - Key metrics returned
   - Use case description

7. **Indexes**
   - List of custom indexes with their purpose

8. **Data Sources Reference**
   - Table of all sources with URLs and coverage

### Table Documentation Format

For each table:
```markdown
#### `table_name`
Brief description with Marxian context where relevant.

| Column | Type | Description |
|--------|------|-------------|
| col1 | TYPE | Description |

**Row Count**: X rows
**Foreign Keys**: list
**Indexes**: list
```

### Success Criteria

#### Automated Verification:
- [ ] File exists at `data/sqlite/data_dictionary.md`
- [ ] Table count matches schema: 35 dim + 28 fact + 5 bridge = 68 tables
- [ ] View count matches: 10 views
- [ ] Markdown linting passes: `markdownlint data/sqlite/data_dictionary.md`

#### Manual Verification:
- [ ] All column names verified against `sqlite3 .schema` output
- [ ] Row counts spot-checked for 10 largest tables
- [ ] View definitions match actual SQL in database
- [ ] Marxian context is technically accurate but not overwhelming

---

## Testing Strategy

### Automated Tests
1. **Schema Accuracy**: Script to compare documented tables vs actual tables
2. **Query Execution**: All example queries execute without error
3. **Markdown Quality**: Linting and formatting checks

### Manual Testing Steps
1. Follow README instructions on fresh Windows install
2. Follow README instructions on fresh macOS install
3. Execute each example query in documentation
4. Verify Pandas examples produce expected output
5. Cross-reference 5 random tables against schema source file

## References

- Actual database: `data/sqlite/marxist-data-3NF.sqlite` (3.4GB)
- Schema source: `src/babylon/data/reference/schema.py`
- Current README: `data/sqlite/README.md`
- Current data dictionary: `data/sqlite/data_dictionary.md`
