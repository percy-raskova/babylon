---
date: 2026-01-08T11:06:54-05:00
researcher: Claude
git_commit: e8463c7207edadcdec6e839c435aa57f9ed19f1e
branch: feature/duckdb
repository: babylon
topic: "Data Layer Architecture Documentation"
tags: [research, codebase, data-layer, loaders, api-clients, schema, utilities]
status: complete
last_updated: 2026-01-08
last_updated_by: Claude
---

# Research: Data Layer Architecture Documentation

**Date**: 2026-01-08T11:06:54-05:00
**Researcher**: Claude
**Git Commit**: e8463c7207edadcdec6e839c435aa57f9ed19f1e
**Branch**: feature/duckdb
**Repository**: babylon

## Research Question

Comprehensive documentation of the `src/babylon/data/` module structure, including loaders, API clients, database schema, utilities, and exception hierarchy.

## Summary

The `src/babylon/data/` directory is the data ingestion layer for the Babylon simulation. It manages:

1. **Static game data** (JSON entity collections in `game/`)
2. **Real-world economic data** from US government APIs (Census, FRED, EIA, QCEW, FCC, etc.)
3. **Infrastructure data** from ArcGIS services (HIFLD, MIRTA)

The module is organized **by data source** rather than by function. Each data source has its own subdirectory containing:
- API client (`api_client.py`)
- Parser (`parser.py`)
- Schema models (`schema.py`)
- 3NF loader (`loader_3nf.py`)

All loaders inherit from `DataLoader` ABC and write to a shared 3NF DuckDB database at `data/duckdb/marxist-data-3NF.duckdb`.

## Detailed Findings

### Module Organization

#### Top-Level Files

| File | Purpose |
|------|---------|
| `loader_base.py` | `DataLoader` ABC, `LoaderConfig`, `LoadStats` classes |
| `api_loader_base.py` | `ApiLoaderBase` with API client lifecycle management |
| `database.py` | Game state SQLite engine/session management |
| `schema.py` | Simple game state ORM models |
| `exceptions.py` | Data layer API exceptions (8 classes) |
| `cli.py` | Typer CLI for unified data loading |
| `preflight.py` | Preflight checks for data ingestion prerequisites |
| `chroma_manager.py` | ChromaDB vector database management |
| `export_sqlite.py` | DuckDB → SQLite export utility |

#### Subdirectories by Category

**Core Infrastructure:**
- `game/` - Static JSON entity data (18 files: characters, classes, factions, etc.)
- `models/` - Backwards-compat layer for Pydantic/SQLAlchemy models
- `normalize/` - 3NF research database (schema, views, classifications)
- `utils/` - Shared utilities (FIPS resolver, batch writer, API resilience)
- `parsers/` - Data parsing utilities (placeholder)
- `data_sources/` - JSON config loader for ArcGIS services

**Government API Data Sources:**
- `census/` - Census Bureau ACS data
- `qcew/` - BLS Quarterly Census of Employment and Wages
- `fred/` - Federal Reserve Economic Data
- `energy/` - EIA energy data
- `lodes/` - LEHD Origin-Destination Employment Statistics
- `dot/` - Department of Transportation HPMS
- `employment_industry/` - Employment by industry
- `materials/` - Raw materials and strategic resources
- `trade/` - International trade data
- `cfs/` - Census Commodity Flow Survey
- `geography/` - Geographic hierarchy and allocation weights
- `fcc/` - FCC Broadband Data Collection

**Infrastructure Data (ArcGIS):**
- `hifld/` - Homeland Infrastructure (prisons, police, electric grid)
- `mirta/` - Military installations
- `external/arcgis/` - Shared ArcGIS REST API client

---

### Loader Infrastructure

#### DataLoader ABC (`loader_base.py:241-435`)

All loaders must inherit from `DataLoader` and implement:

```python
@abstractmethod
def load(session: Session, reset: bool = True, verbose: bool = True, **kwargs) -> LoadStats

@abstractmethod
def get_dimension_tables() -> list[type]

@abstractmethod
def get_fact_tables() -> list[type]
```

**Key Features:**
- `LoaderConfig` dataclass with temporal, geographic, and operational parameters
- `LoadStats` dataclass for tracking dimension/fact counts and errors
- `_get_or_create_time()` for time dimension management with caching
- `_get_or_create_data_source()` for data source registration
- `_build_county_lookup()` for FIPS → county_id mapping
- `clear_tables()` respects FK constraints (facts first, then dimensions)

#### ApiLoaderBase (`api_loader_base.py:12-32`)

Extends `DataLoader` with API client lifecycle management:

```python
@contextmanager
def _client_scope(self, client: Any) -> Iterator[Any]:
    """Ensures client cleanup even on exceptions."""
```

#### LoaderConfig Parameters

| Category | Parameters |
|----------|------------|
| Temporal | `census_years`, `fred_start_year`, `fred_end_year`, `energy_start_year`, `energy_end_year`, `trade_years`, `qcew_years`, `materials_years` |
| Geographic | `state_fips_list`, `include_territories` |
| Operational | `batch_size`, `request_delay_seconds`, `max_retries`, `api_error_policy`, `verbose` |

#### Idempotency Strategy

All loaders use DELETE + INSERT within a transaction. DuckDB-specific: commits between deletes to avoid false FK constraint violations.

---

### API Clients

Seven API client implementations follow consistent patterns:

| Client | API | Auth | Rate Limit | Timeout |
|--------|-----|------|------------|---------|
| `CensusAPIClient` | Census Bureau | Optional | 0.5s | 30s |
| `FredAPIClient` | Federal Reserve | Required | 0.5s | 30s |
| `EnergyAPIClient` | EIA v2 | Required | 0.5s | 30s |
| `QcewAPIClient` | BLS QCEW | None | 0.5s | 60s |
| `CFSAPIClient` | Census CFS | Optional | 0.5s | 30s |
| `ArcGISClient` | ArcGIS REST | None | 0.2s | 30s |
| `FCCBDCClient` | FCC BDC | Required | 6.0s | 60s |

**Common Patterns:**
- `httpx.Client` for HTTP requests
- `_rate_limit()` with `time.sleep()` between requests
- Retry loop with exponential backoff (`MAX_RETRIES=3`, `BACKOFF_FACTOR=2.0`)
- Context manager protocol (`__enter__`, `__exit__`, `close`)
- Service-specific exceptions inheriting from `DataAPIError`
- Dataclass-based result types (`CountyData`, `SeriesData`, etc.)

**Error Handling:**
- 429 (rate limit): Exponential backoff and retry
- 5xx (server error): Exponential backoff and retry
- 404 (Census tables): Return empty list instead of raising
- Error messages truncated to 500 characters

---

### Database Schema

#### Two Parallel Database Systems

1. **Game State Database** (`database.py`)
   - Location: `data/babylon.db`
   - Purpose: Simulation events and logs
   - Tables: `states`, `metro_areas`, `census_population`, `fred_indicators`, etc.

2. **Normalized Research Database** (`normalize/database.py`)
   - Location: `data/duckdb/marxist-data-3NF.duckdb`
   - Purpose: Marxian economic analysis
   - Tables: 33 dimension tables + 28 fact tables

#### 3NF Schema Structure

**Dimension Tables (33):**

| Category | Tables |
|----------|--------|
| Geographic | `dim_state`, `dim_county`, `dim_metro_area`, `bridge_county_metro`, `dim_geographic_hierarchy`, `dim_cfs_area`, `bridge_cfs_county`, `dim_sctg_commodity`, `dim_country`, `dim_import_source` |
| Industry | `dim_industry`, `dim_sector`, `dim_ownership` |
| Census Codes | `dim_income_bracket`, `dim_employment_status`, `dim_worker_class`, `dim_occupation`, `dim_education_level`, `dim_housing_tenure`, `dim_rent_burden`, `dim_commute_mode`, `dim_poverty_category` |
| Energy | `dim_energy_table`, `dim_energy_series` |
| FRED | `dim_wealth_class`, `dim_asset_category`, `dim_fred_series` |
| Commodities | `dim_commodity`, `dim_commodity_metric` |
| Metadata | `dim_time`, `dim_gender`, `dim_data_source`, `dim_race` |
| Coercive | `dim_coercive_type` |

**Fact Tables (28):**

| Category | Tables |
|----------|--------|
| Census | 14 tables (`fact_census_income`, `fact_census_employment`, `fact_census_housing`, etc.) |
| QCEW | 4 tables (`fact_qcew_annual`, `fact_qcew_state_annual`, `fact_qcew_metro_annual`, `fact_productivity_annual`) |
| Trade | 1 table (`fact_trade_monthly`) |
| Energy | 1 table (`fact_energy_annual`) |
| FRED | 5 tables (`fact_fred_national`, `fact_fred_wealth_levels`, etc.) |
| Commodities | 1 table (`fact_commodity_observation`) |
| Materials | 3 tables (`fact_state_minerals`, `fact_mineral_production`, `fact_mineral_employment`) |
| Infrastructure | 4 tables (`fact_coercive_infrastructure`, `fact_broadband_coverage`, `fact_electric_grid`, `fact_commodity_flow`) |

**Marxian Analysis Fields:**
- `marxian_class`: 'proletariat', 'petty_bourgeois', 'state_worker', 'unpaid_labor'
- `labor_type`: 'productive', 'unproductive', 'reproductive', 'managerial'
- `class_composition`: 'goods_producing', 'service_producing', 'circulation', 'government', 'extraction'
- `world_system_tier`: 'core', 'semi_periphery', 'periphery'

#### Analytical Views (10)

| View | Purpose |
|------|---------|
| `view_imperial_rent` | Fundamental theorem: wages - value = imperial rent |
| `view_surplus_value` | Exploitation: output - wages = surplus value |
| `view_unequal_exchange` | World-system tier analysis |
| `view_class_composition` | County-level class breakdown |
| `view_rent_crisis` | Housing burden metrics |
| `view_wealth_concentration` | FRED wealth by percentile |
| `view_critical_materials` | Strategic commodities |
| `view_energy_consumption` | Energy by sector |
| `view_labor_type` | Occupation analysis |
| `view_trade_annual` | Monthly → annual aggregation |

---

### Utilities (`utils/`)

| Module | Purpose |
|--------|---------|
| `fips_resolver.py` | FIPS code normalization and extraction |
| `bulk_insert.py` | `BatchWriter` for chunked SQLAlchemy inserts |
| `api_resilience.py` | `RetryPolicy` dataclass for backoff configuration |
| `logging_helpers.py` | `log_api_error()`, `log_api_retry()` with sanitization |
| `h3_spatial.py` | H3-based county boundary spatial joins |

**Key Functions:**
- `normalize_fips(value, expected_length, min_length)` → zero-padded FIPS
- `build_county_fips(state_fips, county_part)` → 5-digit FIPS
- `extract_county_fips_from_attrs(attrs)` → FIPS from ArcGIS features
- `BatchWriter.write(model, rows)` → chunked bulk insert

---

### Exception Hierarchy

```
BabylonError
├── InfrastructureError
│   ├── DatabaseError
│   │   └── SchemaError
│   │       └── SchemaCheckError
│   └── DataAPIError
│       ├── CensusAPIError
│       ├── FredAPIError
│       ├── EIAAPIError
│       ├── FCCAPIError
│       ├── ArcGISAPIError
│       ├── CFSAPIError
│       └── QcewAPIError
```

**DataAPIError Features:**
- Automatic URL redaction for sensitive parameters
- Error codes: `DAPI_{status_code:03d}`
- Custom `__str__()`: `"{service_name} Error {status}: {message}"`

---

## Code References

### Entry Points
- `src/babylon/data/__init__.py:1-27` - Package exports
- `src/babylon/data/cli.py:47` - Typer CLI app
- `src/babylon/data/normalize/__init__.py:28-67` - 3NF database exports

### Base Classes
- `src/babylon/data/loader_base.py:241-435` - `DataLoader` ABC
- `src/babylon/data/loader_base.py:24-93` - `LoaderConfig` dataclass
- `src/babylon/data/loader_base.py:95-213` - `LoadStats` dataclass
- `src/babylon/data/api_loader_base.py:12-32` - `ApiLoaderBase`

### API Clients
- `src/babylon/data/census/api_client.py:57` - `CensusAPIClient`
- `src/babylon/data/fred/api_client.py:68` - `FredAPIClient`
- `src/babylon/data/energy/api_client.py:67` - `EnergyAPIClient`
- `src/babylon/data/qcew/api_client.py:86` - `QcewAPIClient`
- `src/babylon/data/external/arcgis/client.py:52` - `ArcGISClient`
- `src/babylon/data/fcc/downloader.py:65` - `FCCBDCClient`

### Schema
- `src/babylon/data/normalize/schema.py:42-1640` - All dimension/fact tables
- `src/babylon/data/normalize/views.py:20-206` - Analytical views
- `src/babylon/data/normalize/classifications.py:17-431` - Marxian classification logic

### Utilities
- `src/babylon/data/utils/fips_resolver.py:40-234` - FIPS normalization
- `src/babylon/data/utils/bulk_insert.py:14-40` - `BatchWriter`
- `src/babylon/data/utils/api_resilience.py:10-49` - `RetryPolicy`
- `src/babylon/data/utils/h3_spatial.py:125-188` - `CountyH3Index`

### Exceptions
- `src/babylon/data/exceptions.py:44-131` - All 8 data exceptions

---

## Architecture Documentation

### Design Patterns

1. **Star Schema**: Dimensions (lookups) separate from facts (measurements)
2. **Surrogate Keys**: Auto-incrementing IDs with SQLAlchemy `Sequence` for DuckDB
3. **Bridge Tables**: Many-to-many relationships (`bridge_county_metro`, `bridge_cfs_county`)
4. **Template Method**: `DataLoader.load()` calls abstract methods
5. **Context Manager**: API clients implement `__enter__`/`__exit__`
6. **Dataclass Results**: All API clients return structured dataclass objects
7. **Iterator Pattern**: Large datasets (QCEW, ArcGIS) return iterators

### Data Flow

1. **CLI** (`cli.py`) invokes loader with `LoaderConfig`
2. **Loader** creates API client via `_client_scope()`
3. **API Client** fetches data with rate limiting and retries
4. **Parser** transforms responses to dataclass records
5. **Loader** builds dimension lookups and iterates facts
6. **BatchWriter** inserts rows in chunks
7. **LoadStats** tracks counts and errors
8. **Session** commits on success, rollbacks on error

### Configuration

**Environment Variables:**
- `DATABASE_URL`: Game state database (default: `sqlite:///data/babylon.db`)
- `BABYLON_NORMALIZED_DB_PATH`: Research database (default: `data/duckdb/marxist-data-3NF.duckdb`)
- `CENSUS_API_KEY`: Census Bureau API key (optional)
- `FRED_API_KEY`: FRED API key (required)
- `ENERGY_API_KEY`: EIA API key (required)
- `FCC_USERNAME`, `FCC_API_KEY`: FCC credentials (required)

---

## Open Questions

1. **Async Support**: The plan (`census-production-reference-upgrade.md`) proposes adding async client with semaphore - not yet implemented
2. **Resume Capability**: No checkpoint tracking exists - loaders restart from scratch on failure
3. **Unused Exceptions**: `FredAPIError`, `CFSAPIError`, `ArcGISAPIError`, `QcewAPIError` defined but not raised
4. **SchemaCheckError**: Exported but not used anywhere in production code
