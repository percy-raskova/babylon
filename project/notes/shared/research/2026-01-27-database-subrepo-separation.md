---
date: 2026-01-27T11:02:47-05:00
researcher: Claude
git_commit: a3625b61ca08c10de711566a697d12672176917e
branch: dev
repository: babylon
topic: "Database Module Subrepo Separation Research"
tags: [research, codebase, database, etl, subrepo, architecture, sqlalchemy, 3nf]
status: complete
last_updated: 2026-01-27
last_updated_by: Claude
---

# Research: Database Module Subrepo Separation

**Date**: 2026-01-27T11:02:47-05:00
**Researcher**: Claude
**Git Commit**: a3625b61ca08c10de711566a697d12672176917e
**Branch**: dev
**Repository**: babylon

## Research Question

Prepare to separate the database engine and all its tests into a separate repository which babylon can call as a subrepo. Research how the database is implemented in `src/babylon/data/`, `tests/unit/data/`, and `tests/integration/data/`.

## Summary

The `babylon.data` module is a comprehensive, self-contained ETL (Extract-Transform-Load) system for ingesting federal statistical data into a 3NF normalized SQLite database for Marxian economic analysis. The module has **low coupling** to the core simulation engine - dependencies are limited to configuration, logging, and utility modules (~500 lines total). Separation into a standalone repository is feasible with careful handling of these infrastructure dependencies.

### Key Findings

1. **Self-Contained Architecture**: The data module has no imports from `babylon.engine`, `babylon.systems`, or graph topology code
2. **67 Database Tables**: 33 dimension tables, 34 fact tables following strict 3NF normalization
3. **19 Data Loaders**: Each loader implements the `DataLoader` ABC with standardized interfaces
4. **6 External API Clients**: Census, FRED, QCEW, EIA, ArcGIS, CFS - all using httpx
5. **Comprehensive Test Suite**: 56 unit test files, 7 integration test files (~4,000 lines)
6. **Minimal External Dependencies**: ~500 lines of babylon.* code would need vendoring/replacement

## Detailed Findings

### 1. Database Architecture

#### Multi-Database Pattern
The system uses a **dual-database architecture**:
- **SQLite** (`data/sqlite/marxist-data-3NF.sqlite`): ETL target with reliable UPSERT support
- **DuckDB** (`data/runs/{run_id}.duckdb`): Columnar storage for simulation state (converted from SQLite)

#### Database Modules
| File | Purpose |
|------|---------|
| `src/babylon/data/database.py` | Main app database (legacy) |
| `src/babylon/data/reference/database.py` | 3NF reference database (primary) |
| `src/babylon/data/simulation/database.py` | Ephemeral DuckDB per-run |
| `src/babylon/data/census/database.py` | Legacy Census database (backwards compat) |

#### Session Management
- `get_reference_session()` - Read-only for simulation
- `get_normalized_session()` - Write access for loaders
- Foreign key enforcement via SQLite `PRAGMA foreign_keys=ON` on every connection

### 2. Schema Structure (67 Tables)

#### Dimension Tables (33)
| Category | Tables | Key Examples |
|----------|--------|--------------|
| Geographic | 10 | DimState, DimCounty, DimCountyGeometry, DimMetroArea, DimGeographicHierarchy |
| Industry | 5 | DimIndustry, DimSector, DimOwnership, DimBEAIndustry, BridgeNAICSBEA |
| Census Codes | 9 | DimIncomeBracket, DimWorkerClass, DimOccupation, DimRentBurden |
| Energy/FRED | 5 | DimEnergyTable, DimEnergySeries, DimFredSeries, DimWealthClass |
| Commodities | 3 | DimSCTGCommodity, DimCommodity, DimCommodityMetric |
| Metadata | 4 | DimTime, DimGender, DimDataSource, DimRace |
| Coercive | 1 | DimCoerciveType |

#### Fact Tables (34)
| Category | Count | Key Examples |
|----------|-------|--------------|
| Census | 14 | FactCensusIncome, FactCensusMedianIncome, FactCensusEmployment |
| QCEW/Productivity | 5 | FactQcewAnnual, FactQcewStateAnnual, FactProductivityAnnual |
| BEA | 2 | FactBEANationalIndustry, FactBEACountyGDP |
| Trade | 1 | FactTradeMonthly |
| Energy | 1 | FactEnergyAnnual |
| FRED | 5 | FactFredNational, FactFredWealthLevels, FactFredStateUnemployment |
| Commodities | 1 | FactCommodityObservation |
| Materials | 3 | FactStateMinerals, FactMineralProduction, FactMineralEmployment |
| Circulatory | 3 | FactCoerciveInfrastructure, FactBroadbandCoverage, FactCommodityFlow |
| DOT | 1 | FactHpmsRoadSegment |

#### Infrastructure Tables
- `IngestCheckpoint` - ETL resume capability
- `StagingArcGISFeature` - Two-phase streaming loader staging

### 3. Data Loader Architecture

#### Class Hierarchy
```
DataLoader (ABC) - src/babylon/data/loader_base.py
├── ApiLoaderBase - src/babylon/data/api_loader_base.py
│   └── CensusLoader, FredLoader, QcewLoader, EnergyLoader, CFSLoader
└── ArcGISStreamingLoader - src/babylon/data/arcgis_loader_base.py
    └── HIFLDPrisonsLoader, HIFLDPoliceLoader, MIRTAMilitaryLoader
```

#### Loader Registry (19 loaders)
| Loader | Data Source | CLI Command |
|--------|-------------|-------------|
| CensusLoader | Census Bureau ACS | `mise run data:census` |
| FredLoader | Federal Reserve FRED | `mise run data:fred` |
| QcewLoader | BLS QCEW | `mise run data:qcew` |
| EnergyLoader | EIA API | `mise run data:energy` |
| TradeLoader | UN Trade (Excel) | `mise run data:trade` |
| MaterialsLoader | USGS MCS (CSV) | `mise run data:materials` |
| BEANationalLoader | BEA GDP-by-Industry | `mise run data:bea_national` |
| BEACountyGDPLoader | BEA County GDP | `mise run data:bea_county` |
| CFSLoader | Census CFS | `mise run data:cfs` |
| GeographicHierarchyLoader | Derived weights | `mise run data:geography` |
| TIGERCountyLoader | TIGER shapefiles | `mise run data:tiger` |
| H3GridLoader | Derived H3 hexagons | `mise run data:h3` |
| HIFLDPrisonsLoader | HIFLD ArcGIS | `mise run data:hifld_prisons` |
| HIFLDPoliceLoader | HIFLD ArcGIS | `mise run data:hifld_police` |
| MIRTAMilitaryLoader | MIRTA ArcGIS | `mise run data:mirta` |
| FCCBroadbandLoader | FCC BDC | `mise run data:fcc` |
| DotHpmsLoader | FHWA HPMS | `mise run data:dot_hpms` |
| LodesCrosswalkLoader | LEHD LODES | `mise run data:lodes` |
| NAICSBEAConcordanceLoader | Derived crosswalk | `mise run data:naics_bea` |

#### Configuration System
`LoaderConfig` dataclass controls:
- **Temporal**: `census_years`, `fred_start_year`/`fred_end_year`, `qcew_years`, etc.
- **Geographic**: `state_fips_list`, `include_territories`
- **Operational**: `batch_size`, `request_delay_seconds`, `max_retries`, `api_error_policy`

### 4. API Client Architecture

All clients follow consistent patterns:
- **HTTP Client**: `httpx.Client` (synchronous)
- **Rate Limiting**: 0.2-0.5s delay between requests
- **Retry Logic**: Exponential backoff on 429/5xx
- **Context Manager**: `__enter__`/`__exit__` for cleanup

| Client | API | Authentication |
|--------|-----|----------------|
| CensusAPIClient | Census Bureau ACS | Optional `CENSUS_API_KEY` |
| FredAPIClient | Federal Reserve FRED | Required `FRED_API_KEY` |
| QcewAPIClient | BLS QCEW | None |
| EnergyAPIClient | EIA v2 | Required `ENERGY_API_KEY` |
| ArcGISClient | ArcGIS Feature Services | None |
| CFSAPIClient | Census CFS | Optional `CENSUS_API_KEY` |

### 5. External Dependencies on Babylon

#### Configuration (`babylon.config.*`)
| Import | Used By | Purpose |
|--------|---------|---------|
| `BaseConfig` | database.py, preflight.py | `DATABASE_URL`, directory paths |
| `GameDefines` | hifld/*.py, mirta/loader.py | External API URLs |
| `ChromaDBConfig` | chroma_manager.py | Vector database config |
| `logging_config` | cli.py, census/loader_3nf.py | Logging setup |

#### Utilities (`babylon.utils.*`)
| Import | Used By | Purpose |
|--------|---------|---------|
| `log.redact_params/redact_url` | loader_base.py, logging_helpers.py | Credential sanitization |
| `exceptions.SchemaError` | exceptions.py | Base exception class |
| `exceptions.BabylonError` | cli.py | CLI error handling |
| `retry.retry_on_exception` | chroma_manager.py | Retry decorator |

#### Models (`babylon.models.*`)
| Import | Used By | Purpose |
|--------|---------|---------|
| `entities.EventTemplate` | game/__init__.py | Event validation (optional) |
| `entities.Contradiction/Effect/Trigger` | models/__init__.py | Re-export (deprecated) |

#### Exceptions (`babylon.exceptions`)
| Import | Used By | Purpose |
|--------|---------|---------|
| `DataAPIError` | exceptions.py | Base class for API errors |

**Total External Code**: ~500 lines across config, logging, and exceptions

### 6. External Package Dependencies

```toml
# Core dependencies for standalone package
sqlalchemy = "^2.0"      # ORM with 2.0 style
duckdb = "^0.10"         # Columnar database
httpx = "^0.27"          # HTTP client
pydantic = "^2.0"        # Data validation
pandas = "^2.0"          # Data processing
h3 = "^4.0"              # Hex indexing
geopandas = "^0.14"      # Geospatial data
shapely = "^2.0"         # Geometric operations
pyproj = "^3.6"          # Cartographic projections
openpyxl = "^3.1"        # Excel parsing
chromadb = "^0.4"        # Vector database
typer = "^0.12"          # CLI framework
pyyaml = "^6.0"          # YAML config
tqdm = "^4.66"           # Progress bars
```

### 7. Test Infrastructure

#### Unit Tests (`tests/unit/data/`)
- **56 test files** organized by domain
- **In-memory SQLite** with FK enforcement
- **Mocked API clients** for isolation
- **Pytest markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.network`

Key test categories:
- API client tests (5 files)
- Loader tests (10+ files)
- Parser tests (7 files)
- Schema/3NF compliance tests (8 files)
- Utility tests (4 files)

#### Integration Tests (`tests/integration/data/`)
- **7 test files** (~2,964 lines)
- Real database operations
- Checkpoint/resume verification
- Loader contract compliance
- Idempotency patterns

Key test scenarios:
| File | Purpose |
|------|---------|
| test_census_enhanced.py | Multi-year, race-disaggregated loading |
| test_checkpoint_resume.py | Resume after partial loads |
| test_qcew_api_integration.py | Real BLS API calls |
| test_arcgis_resume.py | ArcGIS streaming resume |
| test_loader_contracts.py | DataLoader ABC compliance |
| test_circulatory_loaders.py | HIFLD/MIRTA integration |
| test_idempotency.py | DELETE+INSERT pattern |

### 8. CLI Interface

Framework: **Typer** with subcommands per loader

```bash
# Core commands
mise run data:load              # Unified loader with dependency resolution
mise run data:schema-init       # Initialize database schema
mise run data:readiness         # Preflight + schema validation

# Loader commands (19 total)
mise run data:census
mise run data:fred
mise run data:qcew
# ... etc
```

Features:
- Dependency resolution via topological sort
- Preflight validation (API keys, files, directories)
- Schema drift detection with auto-repair
- YAML configuration support

## Architecture Documentation

### Separation Boundaries

The data module is cleanly separated from the simulation engine:

```
babylon/
├── src/babylon/
│   ├── data/           ← SEPARATE (subrepo candidate)
│   │   ├── reference/  ← 3NF database
│   │   ├── census/     ← Census loader + API
│   │   ├── fred/       ← FRED loader + API
│   │   ├── ...         ← Other loaders
│   │   ├── cli.py      ← CLI interface
│   │   └── loader_base.py
│   │
│   ├── engine/         ← KEEP (simulation)
│   ├── systems/        ← KEEP (simulation)
│   ├── models/         ← KEEP (simulation) - minor dependency
│   ├── config/         ← SHARED (needs vendor/interface)
│   └── utils/          ← SHARED (needs vendor/interface)
│
├── tests/
│   ├── unit/data/      ← SEPARATE
│   └── integration/data/ ← SEPARATE
```

### Subrepo Interface Design

The separated module would expose:

```python
# Public API
from babylon_data import (
    # Session management
    get_reference_session,
    get_normalized_session,
    init_normalized_db,

    # Loader infrastructure
    DataLoader,
    LoaderConfig,
    LoadStats,

    # Schema models (for queries)
    DimState, DimCounty, DimIndustry, DimTime,
    FactCensusIncome, FactQcewAnnual, ...

    # Classification functions
    classify_marxian_class,
    classify_world_system_tier,
    classify_class_composition,
)
```

### Migration Strategy

1. **Vendor Required Code** (~500 lines):
   - `BaseConfig` for paths/URLs
   - Logging utilities (redaction functions)
   - Exception hierarchy

2. **Replace with Environment Variables**:
   - `GameDefines.external_data.*` URLs → `HIFLD_POLICE_URL`, etc.
   - `ChromaDBConfig` → inline or separate optional package

3. **Make Optional**:
   - `babylon.models.entities` imports → remove re-exports, make EventTemplate optional

4. **Keep as Integration Points**:
   - `DataAPIError` hierarchy → define in new package
   - CLI framework → standalone entry point

## Code References

### Core Database Files
- `src/babylon/data/database.py:12-38` - Main database setup
- `src/babylon/data/reference/database.py:48-210` - Reference database with FK enforcement
- `src/babylon/data/reference/schema.py:1-1860` - 67 table definitions

### Loader Infrastructure
- `src/babylon/data/loader_base.py:25-697` - DataLoader ABC, LoaderConfig, LoadStats
- `src/babylon/data/api_loader_base.py:12-31` - API client lifecycle
- `src/babylon/data/arcgis_loader_base.py:59-537` - Two-phase streaming loader

### API Clients
- `src/babylon/data/census/api_client.py:18-419` - Census Bureau client
- `src/babylon/data/fred/api_client.py:20-517` - FRED client
- `src/babylon/data/qcew/api_client.py:18-327` - BLS QCEW client

### CLI
- `src/babylon/data/cli.py:34-2407` - Full CLI with 19 commands

### Key Tests
- `tests/unit/data/conftest.py:18-232` - Shared fixtures
- `tests/unit/data/test_reference/test_3nf_compliance.py:1-516` - Schema validation
- `tests/integration/data/test_loaders/conftest.py:34-287` - Integration fixtures

## Open Questions

1. **ChromaDB Dependency**: Should `chroma_manager.py` stay with the data module or move to a separate RAG package?

2. **Game Data Loading**: `src/babylon/data/game/` loads JSON entity data - should this stay with simulation or data?

3. **Classification Functions**: Should Marxian classification logic stay with data (for ETL) or move to simulation (for runtime)?

4. **Simulation Database**: `simulation/database.py` uses DuckDB for per-run state - should this stay with data or move to engine?

5. **Version Synchronization**: How to handle schema migrations when data module and simulation module version independently?
