# Babylon Data Infrastructure: Investigation Guide for Claude Code

## Purpose

This document provides guidance for investigating the `/data/` directory and implementing the data infrastructure needed for Babylon's Marxist value tensor. The goal is autonomous investigation and implementation — understand the landscape, identify what exists, fill gaps, and wire everything together.

______________________________________________________________________

## The Core Problem

We need to derive **constant capital (c)** at county level. BEA publishes it at national level only. The solution:

```
c[county, industry] = gross_output[county, industry] × c_ratio[industry, national]
```

Where `c_ratio = intermediate_inputs / gross_output` comes from national BEA data.

Everything else flows from this.

______________________________________________________________________

## What Already Exists (Investigate First)

Before adding anything, understand what's already in place:

### Database Schema

- Look in `/data/duckdb/` for the main database (`marxist-data-3NF.duckdb` or similar)
- Examine existing dimension tables: `dim_county`, `dim_industry`, `dim_sector`, `dim_time`
- Check existing fact tables: `fact_qcew_annual`, `fact_census_*`, `fact_fred_*`
- Look for existing bridge tables and understand the patterns used

### Loader Infrastructure

- Check `src/babylon/data/` for existing loader patterns
- Each data source typically has: `api_client.py`, `loader_3nf.py`, `schema.py`, `parser.py`
- Understand the `LoaderConfig` and `DataLoader` base class patterns
- Look at how existing loaders handle rate limiting, caching, error recovery

### Already-Downloaded Data

- Survey `/data/` subdirectories for CSV/Excel files already present
- Check for BEA data that may already be downloaded but not loaded
- Look for TIGER/shapefiles for county geometries

______________________________________________________________________

## Data Sources to Investigate

### BEA GDP by Industry (CRITICAL — provides c_ratio)

**What we need:** National-level gross output, intermediate inputs, value added by industry

**Where to look:**

- Check if any BEA data exists in `/data/bea/` or similar
- The BEA API (https://apps.bea.gov/api/) provides this programmatically
- Look for tables with names like "GDPbyInd", "ValueAdded", "GrossOutput", "IntermediateInputs"

**Key identifiers:**

- Dataset: `GDPbyIndustry`
- Tables: `ValueAdded`, `GrossOutput`, `IntermediateInputs`
- Industry codes: Match the ~15 sector codes (11, 21, 22, 23, 31G, 42, 44RT, 48TW, 51, FIRE, PROF, 6, 7, 81, G) or ~70 summary industries

**Validation:** `gross_output ≈ intermediate_inputs + value_added` for each industry-year

### BEA Regional (County GDP)

**What we need:** County-level GDP (value-added) by industry

**Where to look:**

- BEA Regional Economic Accounts
- Dataset: `Regional` or `CAGDP`
- Look for county FIPS codes in existing data

**Key insight:** County GDP is published at ~20 industry level, coarser than national ~70. The bridge table must handle this.

### BEA-NAICS Concordance

**What we need:** Mapping from NAICS codes to BEA industry codes

**Where to look:**

- Official concordance: `BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx`
- May already be partially encoded in existing `dim_industry` or `dim_sector` tables
- Check if `class_composition` field exists and how it maps

**Key insight:** This is a many-to-one mapping. Many 6-digit NAICS codes roll up to one BEA industry.

### Price Deflators (CRITICAL — methodological necessity)

**What we need:** GDP deflator or CPI to convert nominal → real values

**Where to look:**

- FRED data in `/data/fred/` — series `GDPDEF` (GDP deflator)
- Check if existing FRED loader already pulls this
- BEA also publishes price indexes with the GDP by Industry tables

**Validation:** All monetary values from different years must be deflated to a common base year before comparison.

### County Geometries (CRITICAL — enables spatial operations)

**What we need:** Polygon boundaries for all ~3,200 US counties

**Where to look:**

- Census TIGER/Line files in `/data/census/` or `/data/tiger/`
- Look for `.shp`, `.geojson`, or `.gpkg` files
- May need to download from Census Bureau if not present

**Key insight:** Without geometries, no spatial operations are possible. This is a hard blocker for H3 grid generation.

### H3 Grid (derived from geometries)

**What we need:** Hex grid covering CONUS, linked to counties

**Approach:**

- Generate hexes using `h3` Python library once geometries exist
- Resolution 5 (~250 km²) or 6 (~35 km²) appropriate for county-scale analysis
- Spatial join to compute `bridge_h3_county.coverage_fraction`

______________________________________________________________________

## Implementation Patterns

### Follow Existing Conventions

When creating new loaders/schemas, match the patterns already established:

```python
# Typical loader structure
class BEAIndustryLoader(DataLoader):
    def get_dimension_tables(self) -> list[type]:
        return [DimBEAIndustry, DimDeflatorSeries]

    def get_fact_tables(self) -> list[type]:
        return [FactBEAIndustryNational, FactPriceDeflator]

    def load(self, session, reset=True, verbose=True, **kwargs) -> LoadStats:
        # Implementation follows existing loader patterns
        ...
```

### Bridge Table Patterns

Bridge tables in this codebase typically:

- Use composite primary keys
- Include a `mapping_quality` or similar confidence field
- Handle many-to-many relationships with coverage fractions where appropriate

### Ratio Derivation

The key derived quantities should be computed at query time or as generated columns, not stored redundantly:

```sql
-- Prefer generated columns for ratios
c_ratio DECIMAL(8,6) GENERATED ALWAYS AS
    (intermediate_inputs_millions / NULLIF(gross_output_millions, 0)) STORED
```

______________________________________________________________________

## Priorities

### P0 — Blockers (nothing works without these)

1. **Price deflators** — If not already in FRED tables, add them. All time-series analysis is invalid without deflation.

1. **County geometries** — If no shapefiles exist, download TIGER/Line. All spatial work is blocked.

### P1 — Core Tensor

3. **BEA national industry data** — Gross output, intermediate inputs, value added. This gives us `c_ratio`.

1. **BEA county GDP** — If not already loaded, add it. Check if existing county data covers this.

1. **NAICS-BEA bridge** — Map existing NAICS codes to BEA industries.

### P2 — Spatial Infrastructure

6. **H3 grid generation** — Once geometries exist, generate hexes and county bridge.

### P3 — Enhancements

7. **Carceral data** — For George Jackson model calibration
1. **International wages** — For imperial rent magnitude
1. **Labor productivity** — Direct SNLT measurement

______________________________________________________________________

## Validation Checks

### After Loading BEA National Data

```sql
-- Accounting identity check
SELECT year,
       SUM(gross_output_millions) as go,
       SUM(intermediate_inputs_millions) as ii,
       SUM(value_added_millions) as va,
       SUM(intermediate_inputs_millions) + SUM(value_added_millions) as ii_plus_va,
       ABS(SUM(gross_output_millions) - (SUM(intermediate_inputs_millions) + SUM(value_added_millions))) as discrepancy
FROM fact_bea_industry_national
JOIN dim_time USING (time_id)
GROUP BY year;
-- discrepancy should be small (rounding only)
```

### After Loading County GDP

```sql
-- State totals sanity check
SELECT s.state_name,
       SUM(gdp.gdp_millions) as county_total,
       state_gdp.gdp_millions as published_state_gdp
FROM fact_bea_county_gdp gdp
JOIN dim_county c USING (county_id)
JOIN dim_state s USING (state_id)
-- Would need state GDP table to compare
GROUP BY s.state_name;
```

### After Creating Bridge Tables

```sql
-- Coverage check: all NAICS codes should map
SELECT COUNT(*) as unmapped
FROM dim_industry i
LEFT JOIN bridge_naics_bea b ON i.naics_code = b.naics_code
WHERE b.bea_industry_id IS NULL;
-- Should be 0 or very small
```

### Final Tensor Query Test

```sql
-- The target query should execute and return plausible values
-- c > 0, v > 0, s can be negative in edge cases but usually positive
-- c + v + s should roughly equal gross output estimates
```

______________________________________________________________________

## Decision Framework

### When Multiple Data Sources Exist

- Prefer official sources (BEA, Census, BLS) over derived/commercial data
- Prefer API access over manual downloads for reproducibility
- Prefer finer geographic grain where available
- Match temporal coverage to existing data (2013-2024 typical range)

### When Data is Missing or Suppressed

- BLS/BEA suppress county data for confidentiality in small cells
- Use state-level fallbacks where county data is suppressed
- Document assumptions in code comments
- Add `mapping_quality` or `disclosure_code` fields to track data quality

### When Schema Decisions Arise

- Follow existing naming conventions (`dim_*`, `fact_*`, `bridge_*`)
- Use surrogate keys (auto-increment integers) as primary keys
- Include `time_id` foreign keys for temporal data
- Add indexes for common query patterns

______________________________________________________________________

## Files to Reference

These project files contain relevant context:

- `docs/database-3nf.rst` — Current schema documentation
- `docs/data-downloads.rst` — Manual download instructions
- `docs/qcew-data.rst`, `docs/fred-data.rst` — Existing loader documentation
- `src/babylon/data/normalize/schema.py` — SQLAlchemy models
- `src/babylon/data/loader_base.py` — Base loader class

______________________________________________________________________

## Success State

The infrastructure is complete when:

1. The target tensor query (from end-state document) executes successfully
1. Results cover 3,000+ counties × 5+ class compositions × 10+ years
1. No NULL values in c, v, s where source data exists
1. Accounting identities validate within rounding tolerance
1. Spatial queries work (hex ↔ county joins return results)
1. All loaders are idempotent (can re-run without duplication)
