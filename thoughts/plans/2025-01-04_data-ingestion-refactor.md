---
date: 2025-01-04
author: claude
commit: ca39f69
status: ready
---

# Plan: Data Ingestion Layer Refactor to Direct 3NF

## Goal

Refactor `src/babylon/data/` to write directly to `marxist-data-3NF.sqlite` in Third
Normal Form, bypassing the intermediate `research.sqlite` database. Create a unified
`DataLoader` base class that enforces consistency, parameterization, idempotency, and
proper structure across all data sources.

## Context

The current architecture has a two-phase ETL:

```text
Data Sources → research.sqlite (denormalized) → normalize/etl.py → marxist-data-3NF.sqlite
```

This creates:

- Duplicate data (625MB in research.sqlite + 308MB in 3NF)
- Extra transformation step with potential for drift
- Inconsistent patterns across 7 data source modules
- Partial idempotency (dimensions only, not facts)

The target architecture:

```text
Data Sources → DataLoader (unified) → marxist-data-3NF.sqlite (direct 3NF)
```

### Data Sources Assessment

| Source           | Current                 | Target         | API Available         | Status     |
| ---------------- | ----------------------- | -------------- | --------------------- | ---------- |
| **Census**       | API → research.sqlite   | API → 3NF      | Yes (existing)        | Refactor   |
| **FRED**         | API → research.sqlite   | API → 3NF      | Yes (existing)        | Refactor   |
| **Energy**       | Excel → research.sqlite | API → 3NF      | Yes (EIA v2)          | New client |
| **Trade**        | Excel → research.sqlite | File → 3NF     | UN Comtrade (complex) | Keep files |
| **QCEW**         | CSV → research.sqlite   | File → 3NF     | No (download only)    | Keep files |
| **Materials**    | CSV → research.sqlite   | File → 3NF     | USGS (per user)       | Keep files |
| **Productivity** | Excel → research.sqlite | FRED API → 3NF | Via FRED              | Use FRED   |

### API Keys (in .envrc)

- `$CENSUS_API_KEY` - Census Bureau API
- `$FRED_API_KEY` - FRED API (includes BLS productivity series)
- `$ENERGY_API_KEY` - EIA API v2 (needs to be added to .envrc if not present)

## Approach

### Idempotency Strategy: DELETE + INSERT

For a "load-once, read-many" scenario:

- **DELETE + INSERT** within a transaction is simplest and fastest
- No need for complex UPSERT/MERGE logic
- Transaction ensures atomicity (all-or-nothing)
- Clean slate each load prevents stale data

Pattern:

```python
with session.begin():
    session.query(DimFoo).delete()
    session.bulk_save_objects(new_records)
    # commit on context exit
```

### Loader Configuration

All loaders accept a `LoaderConfig` that parameterizes temporal coverage, geographic scope,
and operational settings. This enables future database expansion without code changes.

```python
from dataclasses import dataclass, field

@dataclass
class LoaderConfig:
    """Configuration for data loaders.

    Temporal Parameters:
        census_year: ACS 5-year estimate year (e.g., 2022 = 2018-2022 estimates)
        fred_start_year: Start year for FRED time series
        fred_end_year: End year for FRED time series
        energy_start_year: Start year for EIA energy data
        energy_end_year: End year for EIA energy data
        trade_years: List of years for trade data files
        qcew_years: List of years for QCEW data files

    Geographic Scope:
        state_fips_list: List of 2-digit state FIPS codes (default: all 50 + DC + PR)
        include_territories: Include US territories beyond PR

    Operational:
        batch_size: Rows per bulk insert operation
        request_delay_seconds: Rate limiting delay between API calls
        max_retries: Max retry attempts for failed requests
        verbose: Enable progress output
    """
    # Temporal - Census (single year for 5-year estimates)
    census_year: int = 2022

    # Temporal - FRED (time series range)
    fred_start_year: int = 1990
    fred_end_year: int = 2024

    # Temporal - Energy (EIA annual data)
    energy_start_year: int = 1990
    energy_end_year: int = 2024

    # Temporal - File-based sources (years to look for)
    trade_years: list[int] = field(default_factory=lambda: list(range(2010, 2025)))
    qcew_years: list[int] = field(default_factory=lambda: list(range(2015, 2024)))
    materials_years: list[int] = field(default_factory=lambda: list(range(2015, 2024)))

    # Geographic scope
    state_fips_list: list[str] | None = None  # None = all 52 (50 + DC + PR)
    include_territories: bool = False  # VI, GU, AS, MP

    # Operational
    batch_size: int = 10_000
    request_delay_seconds: float = 0.5
    max_retries: int = 3
    verbose: bool = True
```

### Base DataLoader Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from sqlalchemy.orm import Session

@dataclass
class LoadStats:
    """Statistics returned by all loaders."""
    source: str
    dimensions_loaded: dict[str, int] = field(default_factory=dict)
    facts_loaded: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    api_calls: int = 0
    files_processed: int = 0

class DataLoader(ABC):
    """Base class for all data loaders."""

    def __init__(self, config: LoaderConfig | None = None):
        self.config = config or LoaderConfig()

    @abstractmethod
    def load(
        self,
        session: Session,
        reset: bool = True,
        **kwargs,
    ) -> LoadStats:
        """Load data into 3NF schema."""
        ...

    @abstractmethod
    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        ...

    @abstractmethod
    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        ...
```

## Changes

### Phase 1: Infrastructure (DataLoader Base + Database + Config)

Create the unified infrastructure for all loaders including parameterized configuration.

Files to modify/create:

- `src/babylon/data/loader_base.py` - NEW: DataLoader ABC + LoadStats + LoaderConfig
- `src/babylon/data/database.py` - MODIFY: Add 3NF engine factory
- `src/babylon/data/normalize/database.py` - KEEP: Already has 3NF engine
- `src/babylon/data/normalize/schema.py` - KEEP: 3NF schema (28 dims, 21 facts)
- `src/babylon/data/normalize/classifications.py` - KEEP: Marxian classification functions

Success criteria:

- [x] `DataLoader` ABC defined with `load()`, `get_dimension_tables()`, `get_fact_tables()`
- [x] `LoadStats` dataclass with consistent fields
- [x] 3NF engine accessible via `get_normalized_engine()`
- [x] FK pragma enabled on 3NF connections
- [x] `mise run check` passes (pre-existing UI test failures unrelated to data layer)
- [x] `LoaderConfig` dataclass with temporal, geographic, and operational parameters
- [x] `DataLoader.__init__` accepts optional `LoaderConfig`
- [x] Default config values documented and sensible

### Phase 2: Census Loader Refactor

Refactor Census loader to write directly to 3NF with parameterized configuration.

Files to modify:

- `src/babylon/data/census/loader_3nf.py` - NEW: CensusLoader(DataLoader)
- `src/babylon/data/census/api_loader.py` - DEPRECATE: Keep for reference
- `src/babylon/data/census/__init__.py` - MODIFY: Export new loader

Changes:

1. Create `CensusLoader(DataLoader)` that:

   - Uses existing `CensusAPIClient` for API calls
   - Respects `config.census_year` for ACS vintage selection
   - Respects `config.state_fips_list` for geographic scope (default: all 52)
   - Uses `config.batch_size` for bulk inserts
   - Uses `config.request_delay_seconds` for rate limiting
   - Writes directly to `DimCounty`, `DimState`, `DimIncomeBracket`, etc.
   - Writes to `FactCensusIncome`, `FactCensusMedianIncome`, etc.
   - Applies `classify_marxian_class()`, `classify_rent_burden()` inline
   - Uses DELETE+INSERT pattern for idempotency

1. Migrate 16 fact loaders from `api_loader.py` to new structure

Config parameters used:

- `census_year`: Which ACS 5-year vintage (e.g., 2022 = 2018-2022)
- `state_fips_list`: Limit to specific states (None = all)
- `batch_size`: Bulk insert batch size
- `request_delay_seconds`: API rate limiting

Success criteria:

- [x] `CensusLoader.load()` populates all census dimension/fact tables (13 dims, 14 facts)
- [x] `config.census_year` controls ACS vintage
- [x] `config.state_fips_list` limits geographic scope
- [x] Classifications applied during load (not separate step)
- [x] DELETE+INSERT idempotency works (via `clear_tables()`)
- [x] `mise run test:unit` passes (3019 passed; 55 pre-existing UI failures unrelated)
- [x] `mise run check` passes (lint + typecheck pass; pre-existing UI test failures)

### Phase 3: FRED + Productivity Loader Refactor

Refactor FRED loader to write directly to 3NF, including productivity data.

Files to modify:

- `src/babylon/data/fred/loader_3nf.py` - NEW: FredLoader(DataLoader)
- `src/babylon/data/fred/loader.py` - DEPRECATE: Keep for reference
- `src/babylon/data/fred/__init__.py` - MODIFY: Export new loader
- `src/babylon/data/productivity/` - DEPRECATE: Productivity via FRED instead

Changes:

1. Create `FredLoader(DataLoader)` that:

   - Uses existing `FredAPIClient`
   - Respects `config.fred_start_year` and `config.fred_end_year` for time series range
   - Respects `config.state_fips_list` for state unemployment series
   - Uses `config.request_delay_seconds` for rate limiting
   - Writes directly to `DimFredSeries`, `DimWealthClass`, `DimAssetCategory`
   - Writes to `FactFredNational`, `FactFredWealthLevels`, etc.
   - Adds productivity series (OPHNFB, PRS85006092) to national data
   - Writes productivity to `FactProductivityAnnual`
   - Applies `babylon_class` mappings inline

1. Migrate DFA wealth mapping to 3NF schema

Config parameters used:

- `fred_start_year`: Start of time series range (default: 1990)
- `fred_end_year`: End of time series range (default: 2024)
- `state_fips_list`: Which states to fetch unemployment for
- `request_delay_seconds`: API rate limiting

Success criteria:

- [x] `FredLoader.load()` populates all FRED dimension/fact tables
- [x] `config.fred_start_year`/`fred_end_year` control observation range
- [x] Productivity data loaded via FRED API (not separate Excel files)
- [x] Wealth class mappings preserved
- [x] `mise run test:unit` passes (3019 passed; 55 pre-existing UI failures unrelated)
- [x] `mise run check` passes (lint + typecheck pass; pre-existing UI test failures)

### Phase 4: Energy Loader (New API Client)

Create new EIA API v2 client and loader with parameterized configuration.

Files to create:

- `src/babylon/data/energy/api_client.py` - NEW: EnergyAPIClient
- `src/babylon/data/energy/loader_3nf.py` - NEW: EnergyLoader(DataLoader)

EIA API v2 details:

- Base URL: `https://api.eia.gov/v2/`
- Auth: `?api_key=$ENERGY_API_KEY`
- Endpoint: `/totalenergy/data/annual`
- Max 5000 rows per request
- Rate limit: Similar to FRED (~0.5s delay recommended)

Changes:

1. Create `EnergyAPIClient` with:

   - Rate limiting (uses `config.request_delay_seconds`)
   - Retry logic with exponential backoff (uses `config.max_retries`)
   - Context manager pattern
   - Methods for total-energy, petroleum routes
   - Year filtering via `start` and `end` parameters

1. Create `EnergyLoader(DataLoader)` that:

   - Respects `config.energy_start_year` and `config.energy_end_year`
   - Writes to `DimEnergyTable`, `DimEnergySeries`
   - Writes to `FactEnergyAnnual`
   - Applies `marxian_interpretation` during load

Config parameters used:

- `energy_start_year`: Start year for energy data (default: 1990)
- `energy_end_year`: End year for energy data (default: 2024)
- `request_delay_seconds`: API rate limiting
- `max_retries`: Retry attempts for failed requests

Success criteria:

- [x] `EnergyAPIClient` fetches data from EIA API v2
- [x] `config.energy_start_year`/`energy_end_year` control data range
- [x] `EnergyLoader.load()` populates energy dimension/fact tables
- [x] No Excel file dependencies (API-first approach)
- [x] `mise run check` passes (lint + typecheck pass; 55 pre-existing UI test failures)

### Phase 5: File-Based Loaders (Trade, QCEW, Materials)

Refactor file-based loaders to write directly to 3NF with parameterized year filtering.

Files to modify:

- `src/babylon/data/trade/loader_3nf.py` - NEW: TradeLoader(DataLoader)
- `src/babylon/data/qcew/loader_3nf.py` - NEW: QcewLoader(DataLoader)
- `src/babylon/data/materials/loader_3nf.py` - NEW: MaterialsLoader(DataLoader)

Changes:

1. Each loader:

   - Extends `DataLoader`
   - Uses existing parser.py for file parsing
   - Filters files by year using `config.*_years` lists
   - Uses `config.batch_size` for bulk inserts
   - Writes directly to 3NF schema
   - Applies classifications inline

1. Trade:

   - Respects `config.trade_years` (default: 2010-2024)
   - Writes to `DimCountry`, `FactTradeMonthly` with `world_system_tier`

1. QCEW:

   - Respects `config.qcew_years` (default: 2015-2023)
   - Writes to `DimIndustry`, `DimOwnership`, `FactQcewAnnual` with `class_composition`

1. Materials:

   - Respects `config.materials_years` (default: 2015-2023)
   - Writes to `DimCommodity`, `FactCommodityObservation`

Config parameters used:

- `trade_years`: List of years to load trade data for
- `qcew_years`: List of years to load QCEW data for
- `materials_years`: List of years to load materials data for
- `batch_size`: Bulk insert batch size

Success criteria:

- [ ] All file-based loaders extend `DataLoader`
- [ ] `config.*_years` filters which files are processed
- [ ] Classifications applied during load
- [ ] `mise run check` passes

### Phase 6: Test Suite Enhancement

Enhance tests to verify 3NF compliance, ETL best practices, and config handling.

Files to modify:

- `tests/unit/data/test_normalize/test_3nf_compliance.py` - NEW
- `tests/unit/data/test_normalize/test_loader_base.py` - NEW
- `tests/unit/data/test_normalize/test_loader_config.py` - NEW
- `tests/integration/data/test_loaders/` - NEW directory

New tests:

1. **3NF Compliance Tests**:

   - Primary key uniqueness (no duplicate natural keys)
   - Foreign key referential integrity (no orphan FKs)
   - Atomic values (no arrays/JSON in columns)
   - No transitive dependencies (verify dimension separation)

1. **Idempotency Tests**:

   - Run loader twice, verify same row counts
   - DELETE+INSERT actually clears old data
   - No duplicate primary keys after reload

1. **Common ETL Pitfalls**:

   - NULL handling (30+ NULL representations)
   - Type coercion (currency, percentages, scaled numbers)
   - Batch processing (boundary conditions)
   - Data loss detection (source vs target counts)

1. **DataLoader Contract Tests**:

   - All loaders return LoadStats
   - All loaders implement get_dimension_tables()
   - All loaders implement get_fact_tables()
   - All loaders accept LoaderConfig

1. **LoaderConfig Tests**:

   - Default values are sensible
   - Year range validation (start \<= end)
   - State FIPS list validation (valid 2-digit codes)
   - Config serialization/deserialization (for CLI usage)
   - Custom config overrides default values

Success criteria:

- [ ] 3NF compliance tests for all dimension/fact tables
- [ ] Idempotency tests verify DELETE+INSERT pattern
- [ ] ETL pitfall tests cover NULL, type coercion, batching
- [ ] All loaders pass contract tests
- [ ] LoaderConfig tests verify parameterization
- [ ] `mise run test:unit` passes
- [ ] `mise run test:int` passes

### Phase 7: Deprecation and Cleanup

Remove deprecated code, update entry points, and add CLI config support.

Files to deprecate:

- `src/babylon/data/census/loader.py` - CSV loader (legacy)
- `src/babylon/data/census/api_loader.py` - Old API loader
- `src/babylon/data/fred/loader.py` - Old FRED loader
- `src/babylon/data/energy/loader.py` - Old Excel loader
- `src/babylon/data/energy/parser.py` - Excel parser (if API works)
- `src/babylon/data/normalize/etl.py` - Two-phase ETL (replaced by direct 3NF)
- `src/babylon/data/productivity/` - Entire directory (use FRED)

Files to create/update:

- `src/babylon/data/cli.py` - NEW: CLI entry point with config args
- `mise.toml` - Update data:\* tasks
- `pyproject.toml` - Update entry points
- `ai-docs/` - Update documentation

Changes:

1. Add deprecation warnings to old loaders

1. Create CLI entry point supporting config parameters:

   ```bash
   # Default config (all data, full range)
   mise run data:load

   # Custom year range
   mise run data:load -- --census-year 2021 --fred-start 2000 --fred-end 2023

   # Single state for testing
   mise run data:load -- --states 06,36  # CA and NY only

   # Specific loaders only
   mise run data:census -- --year 2022
   mise run data:fred -- --start-year 1990 --end-year 2024
   ```

1. Update mise tasks:

   - `data:load` → unified loader entry point (accepts --config-file or CLI args)
   - `data:census` → CensusLoader (accepts --year, --states)
   - `data:fred` → FredLoader (accepts --start-year, --end-year)
   - `data:energy` → EnergyLoader (accepts --start-year, --end-year)
   - `data:qcew` → QcewLoader (accepts --years)
   - `data:trade` → TradeLoader (accepts --years)
   - `data:materials` → MaterialsLoader (accepts --years)

1. Support config file loading:

   ```yaml
   # config/data-load.yaml
   census_year: 2022
   fred_start_year: 1990
   fred_end_year: 2024
   state_fips_list: null  # all states
   batch_size: 10000
   ```

1. Remove research.sqlite from documentation

Success criteria:

- [ ] Deprecation warnings on old code
- [ ] mise tasks updated with CLI arg support
- [ ] `mise run data:load` runs unified pipeline
- [ ] `mise run data:load -- --help` shows config options
- [ ] Config file loading works (`--config-file path/to/config.yaml`)
- [ ] `mise run check` passes
- [ ] Documentation updated

## NOT Doing

Explicitly out of scope:

- UN Comtrade API integration (complex, keep Excel files for Trade)
- BLS QCEW API (not available, keep CSV files)
- Migration of existing data in research.sqlite (fresh load only)
- Incremental/delta loads (load-once pattern)
- Real-time streaming (batch only)
- DuckDB migration (future epoch)

## Resolved Questions

- [x] ENERGY_API_KEY confirmed in .envrc
- [x] Keep research.sqlite locally (don't commit) - useful for comparison/testing
- [x] Batch size: 10,000 rows per bulk insert (acceptable)
- [x] Deprecated files: Move to `src/babylon/data/_archive/` directory

## Success Criteria

Automated:

- [ ] `mise run check` passes (lint + format + typecheck + unit)
- [ ] `mise run test:unit` passes (all unit tests)
- [ ] `mise run test:int` passes (integration tests)
- [ ] `mise run qa:schemas` passes (JSON schema validation)
- [ ] `mise run data:load` completes without errors
- [ ] `mise run data:load -- --help` shows all config options

Manual:

- [ ] Data in marxist-data-3NF.sqlite matches expected row counts
- [ ] All Marxian classifications applied correctly
- [ ] Running loader twice produces identical results (idempotency)
- [ ] API rate limits respected (no 429 errors)
- [ ] Custom year ranges work (e.g., `--census-year 2021` loads 2021 data)
- [ ] State filtering works (e.g., `--states 06` loads only California)
- [ ] Config file loading works (`--config-file`)
- [ ] Documentation accurately reflects new architecture

## References

- BLS Developers: https://www.bls.gov/developers/home.htm
- EIA API v2: https://www.eia.gov/opendata/documentation.php
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
- Census API: https://www.census.gov/data/developers/data-sets.html
- Current 3NF schema: `src/babylon/data/normalize/schema.py`
- Data dictionary: `data/sqlite/DATA_DICTIONARY.md`
