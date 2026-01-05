# Circulatory System API Loaders Implementation Plan

## Implementation Status

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. Schema Extensions | COMPLETE | 2026-01-05 |
| 2. ArcGIS API Client | COMPLETE | 2026-01-05 |
| 3. HIFLD Prison Loader | COMPLETE | 2026-01-05 |
| 4. HIFLD Police & Military Loaders | COMPLETE | 2026-01-05 |
| 5. HIFLD Electric Grid Loader | COMPLETE | 2026-01-05 |
| 6. Census CFS Loader | DEFERRED | - |
| 7. FCC Broadband Loader | DEFERRED | - |
| 8. CLI Integration | COMPLETE | 2026-01-05 |

**Deferred Items:**
- **CFS Loader**: Census CFS API only provides state-level and CFS-area data, NOT county-level. Requires county mapping table infrastructure to distribute state-level flows to counties.
- **FCC Loader**: BDC API is file-download oriented (not direct query). Requires account registration and investigation of downloaded file format for county extraction.

## Overview

Implement data loaders for seven API-accessible circulatory system datasets identified in the research document (`thoughts/shared/research/2026-01-05-dot-transportation-integration.md` Section 12). These loaders will ingest coercive infrastructure, commodity flow, and communications data into Babylon's 3NF database schema, enabling realistic simulation of state power geography and value extraction flows.

**Scope**: Only datasets with programmatic API access (not file-download-only datasets).

## Current State Analysis

### Existing Infrastructure

The `src/babylon/data/` directory follows a well-established pattern:

1. **API Client Pattern** (`census/api_client.py`):
   - Rate-limited HTTP client using `httpx`
   - Exponential backoff on rate limiting (429)
   - Environment variable for API keys
   - Context manager support

2. **DataLoader ABC** (`loader_base.py`):
   - `LoaderConfig` for parameterized loading
   - `LoadStats` for tracking load results
   - Abstract methods: `load()`, `get_dimension_tables()`, `get_fact_tables()`
   - `clear_tables()` respects FK constraint order

3. **3NF Schema** (`normalize/schema.py`):
   - SQLAlchemy 2.0 `DeclarativeBase` with `Mapped` types
   - `DimCounty` with 5-digit FIPS as canonical geographic key
   - `DimDataSource` for provenance tracking

4. **CLI Integration** (`cli.py`):
   - `ALL_LOADERS` list for `mise run data:load`
   - Individual commands per loader (e.g., `mise run data:census`)

### Key Discoveries:
- Existing loaders iterate by state FIPS for geographic scoping (`src/babylon/data/census/loader_3nf.py:492`)
- API clients use `_request()` pattern with retry logic (`src/babylon/data/census/api_client.py:121-183`)
- Dimensions load first, facts second, within transaction (`src/babylon/data/census/loader_3nf.py:299-398`)
- Progress tracking via `tqdm` with `disable=not verbose`

## Desired End State

After implementation:

1. **Seven new loaders** accessible via `mise run data:load --loaders=hifld,mirta,cfs,fcc`
2. **New schema tables** for coercive infrastructure, broadband coverage
3. **Unified ArcGIS client** reusable across HIFLD datasets
4. **County-level aggregation** from facility-level source data

### Success Verification:
```bash
# Load all API-based circulatory loaders
mise run data:load --loaders=hifld_prisons,hifld_police,hifld_electric,mirta,cfs,fcc

# Verify data loaded
sqlite3 data/sqlite/marxist-data-3NF.sqlite \
  "SELECT coercive_type, SUM(facility_count), SUM(total_capacity)
   FROM fact_coercive_infrastructure f
   JOIN dim_coercive_type t ON f.coercive_type_id = t.coercive_type_id
   GROUP BY coercive_type"
```

## What We're NOT Doing

- **FAF** (Freight Analysis Framework) - No API, CSV download only
- **LEHD LODES** - LED Tool not scriptable, CSV by state
- **NBI** (National Bridge Inventory) - ASCII files only
- **ICE Detention** - FOIA data via Marshall Project GitHub (no API)
- **Full facility detail storage** - We aggregate to county-level, not per-facility
- **Geographic polygon storage** - Store centroids/aggregates only, not full geometries

## Implementation Approach

Create a shared ArcGIS client for HIFLD/MIRTA datasets, then implement loaders in priority order:
1. **Coercive Infrastructure** (HIFLD Prisons, Police, MIRTA Military)
2. **Supporting Infrastructure** (HIFLD Electric Grid)
3. **Commodity Flows** (Census CFS)
4. **Communications** (FCC Broadband)

Each loader follows the established `DataLoader` ABC pattern with new schema tables.

---

## Phase 1: Schema Extensions

### Overview
Add dimension and fact tables for circulatory system data to the 3NF schema.

### Changes Required:

#### 1. New Dimension: Coercive Type
**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add `DimCoerciveType` after line 473

```python
class DimCoerciveType(NormalizedBase):
    """Coercive infrastructure type classification."""

    __tablename__ = "dim_coercive_type"

    coercive_type_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # carceral, enforcement, military
    command_chain: Mapped[str] = mapped_column(String(20), nullable=False)  # federal, state, local

    __table_args__ = (
        Index("idx_coercive_category", "category"),
        CheckConstraint(
            "category IN ('carceral', 'enforcement', 'military')",
            name="ck_coercive_category",
        ),
        CheckConstraint(
            "command_chain IN ('federal', 'state', 'local', 'mixed')",
            name="ck_command_chain",
        ),
    )
```

#### 2. New Fact: Coercive Infrastructure
**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add `FactCoerciveInfrastructure` after facts section

```python
class FactCoerciveInfrastructure(NormalizedBase):
    """County-level coercive infrastructure capacity."""

    __tablename__ = "fact_coercive_infrastructure"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    coercive_type_id: Mapped[int] = mapped_column(
        ForeignKey("dim_coercive_type.coercive_type_id"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    facility_count: Mapped[int] = mapped_column(default=0)
    total_capacity: Mapped[int | None] = mapped_column()  # beds, personnel, etc.

    __table_args__ = (
        Index("idx_coercive_county", "county_id"),
        Index("idx_coercive_type", "coercive_type_id"),
    )
```

#### 3. New Fact: Broadband Coverage
**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add `FactBroadbandCoverage`

```python
class FactBroadbandCoverage(NormalizedBase):
    """County-level broadband coverage metrics."""

    __tablename__ = "fact_broadband_coverage"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    pct_25_3: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # % with 25/3 Mbps
    pct_100_20: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # % with 100/20 Mbps
    pct_1000_100: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # % with gigabit
    provider_count: Mapped[int | None] = mapped_column()
```

#### 4. New Fact: Electric Grid Infrastructure
**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add `FactElectricGrid`

```python
class FactElectricGrid(NormalizedBase):
    """County-level electric grid infrastructure metrics."""

    __tablename__ = "fact_electric_grid"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    substation_count: Mapped[int] = mapped_column(default=0)
    total_capacity_mw: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    transmission_line_miles: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
```

#### 5. Update `__all__` exports
**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add new classes to `__all__`

### Success Criteria:

#### Automated Verification:
- [x] Schema imports without error: `python -c "from babylon.data.normalize.schema import DimCoerciveType, FactCoerciveInfrastructure"`
- [x] Type checking passes: `mise run typecheck`
- [x] Database initializes with new tables: `mise run data:load --loaders=census --states 06 --quiet`

**Status: COMPLETE** - Schema tables implemented in `src/babylon/data/normalize/schema.py` (lines 481-513, 974-1035)

---

## Phase 2: ArcGIS API Client

### Overview
Create a reusable ArcGIS REST API client for HIFLD and MIRTA datasets, following the `CensusAPIClient` pattern.

### Changes Required:

#### 1. Create ArcGIS Client Module
**File**: `src/babylon/data/external/arcgis/__init__.py`
**Changes**: New file

```python
"""ArcGIS REST API client for HIFLD and MIRTA data.

Provides paginated query access to ArcGIS Feature Services used by DHS HIFLD
and DoD MIRTA for infrastructure data.

API Documentation: https://developers.arcgis.com/rest/services-reference/
"""

from babylon.data.external.arcgis.client import ArcGISClient, ArcGISFeature

__all__ = ["ArcGISClient", "ArcGISFeature"]
```

#### 2. ArcGIS Client Implementation
**File**: `src/babylon/data/external/arcgis/client.py`
**Changes**: New file

```python
"""ArcGIS REST API client with pagination and rate limiting."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import httpx

logger = logging.getLogger(__name__)

# ArcGIS Feature Service limits
MAX_RECORD_COUNT = 2000  # Default server limit
REQUEST_DELAY_SECONDS = 0.2  # Conservative rate limit
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0


@dataclass
class ArcGISAPIError(Exception):
    """Error from ArcGIS REST API."""

    status_code: int
    message: str
    url: str


@dataclass
class ArcGISFeature:
    """Single feature from ArcGIS Feature Service."""

    object_id: int
    attributes: dict[str, Any]
    geometry: dict[str, Any] | None = None


class ArcGISClient:
    """Client for ArcGIS REST API Feature Services.

    Handles pagination for large datasets and rate limiting.

    Attributes:
        base_url: Base URL for the Feature Service (e.g., services1.arcgis.com/...)
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
    ) -> None:
        """Initialize ArcGIS client.

        Args:
            base_url: Base URL for Feature Service (without /query suffix).
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "ArcGISClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _request(
        self,
        endpoint: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        """Make rate-limited API request with retries."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(endpoint, params=params)

                if response.status_code == 200:
                    data = response.json()
                    # Check for ArcGIS error in response body
                    if "error" in data:
                        raise ArcGISAPIError(
                            status_code=data["error"].get("code", 0),
                            message=data["error"].get("message", "Unknown error"),
                            url=str(response.url),
                        )
                    return data

                if response.status_code == 429:
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue

                raise ArcGISAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=str(response.url),
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise ArcGISAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=endpoint,
        )

    def query_all(
        self,
        where: str = "1=1",
        out_fields: str = "*",
        return_geometry: bool = False,
    ) -> Iterator[ArcGISFeature]:
        """Query all features with automatic pagination.

        Args:
            where: SQL WHERE clause for filtering.
            out_fields: Comma-separated field names or "*" for all.
            return_geometry: Whether to include geometry in results.

        Yields:
            ArcGISFeature objects for each record.
        """
        endpoint = f"{self.base_url}/query"
        offset = 0

        while True:
            params = {
                "where": where,
                "outFields": out_fields,
                "returnGeometry": str(return_geometry).lower(),
                "f": "json",
                "resultOffset": str(offset),
                "resultRecordCount": str(MAX_RECORD_COUNT),
            }

            data = self._request(endpoint, params)
            features = data.get("features", [])

            if not features:
                break

            for feature in features:
                yield ArcGISFeature(
                    object_id=feature.get("attributes", {}).get("OBJECTID", 0),
                    attributes=feature.get("attributes", {}),
                    geometry=feature.get("geometry") if return_geometry else None,
                )

            # Check if more results available
            if len(features) < MAX_RECORD_COUNT:
                break

            offset += len(features)
            logger.debug(f"Fetched {offset} features, continuing...")

    def get_record_count(self, where: str = "1=1") -> int:
        """Get total record count for a query."""
        endpoint = f"{self.base_url}/query"
        params = {
            "where": where,
            "returnCountOnly": "true",
            "f": "json",
        }
        data = self._request(endpoint, params)
        return data.get("count", 0)


__all__ = ["ArcGISClient", "ArcGISFeature", "ArcGISAPIError"]
```

### Success Criteria:

#### Automated Verification:
- [x] Client imports: `python -c "from babylon.data.external.arcgis import ArcGISClient"`
- [x] Type checking passes: `mise run typecheck`
- [x] Unit test passes: `mise run test:unit -k test_arcgis_client`

**Status: COMPLETE** - ArcGIS client implemented in `src/babylon/data/external/arcgis/client.py`

---

## Phase 3: HIFLD Prison Loader

### Overview
Implement loader for HIFLD Prison Boundaries dataset (~7,000 facilities) with county-level aggregation.

### Changes Required:

#### 1. Create HIFLD Package
**File**: `src/babylon/data/hifld/__init__.py`
**Changes**: New file

```python
"""HIFLD (Homeland Infrastructure Foundation-Level Data) loaders.

Provides loaders for DHS infrastructure datasets:
- Prison Boundaries
- Local Law Enforcement Locations
- Electric Substations/Transmission Lines
"""

from babylon.data.hifld.prisons import HIFLDPrisonsLoader
from babylon.data.hifld.police import HIFLDPoliceLoader
from babylon.data.hifld.electric import HIFLDElectricLoader

__all__ = ["HIFLDPrisonsLoader", "HIFLDPoliceLoader", "HIFLDElectricLoader"]
```

#### 2. Prison Loader Implementation
**File**: `src/babylon/data/hifld/prisons.py`
**Changes**: New file

```python
"""HIFLD Prison Boundaries loader.

Loads prison/correctional facility data from HIFLD ArcGIS Feature Service
and aggregates to county-level capacity metrics.

Source: https://hifld-geoplatform.opendata.arcgis.com/datasets/prison-boundaries
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.external.arcgis import ArcGISClient
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimCoerciveType,
    DimCounty,
    DimDataSource,
    FactCoerciveInfrastructure,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# HIFLD Prison Boundaries Feature Service
PRISONS_SERVICE_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "Prison_Boundaries/FeatureServer/0"
)

# Prison type mapping to coercive type codes
PRISON_TYPE_MAP = {
    "FEDERAL": ("prison_federal", "Federal Prison", "carceral", "federal"),
    "STATE": ("prison_state", "State Prison", "carceral", "state"),
    "LOCAL": ("prison_local", "Local Jail/Detention", "carceral", "local"),
    "PRIVATE": ("prison_private", "Private Prison", "carceral", "mixed"),
}


class HIFLDPrisonsLoader(DataLoader):
    """Loader for HIFLD Prison Boundaries data.

    Fetches prison facility data from HIFLD ArcGIS Feature Service and
    aggregates to county-level coercive infrastructure metrics.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize prison loader."""
        super().__init__(config)
        self._client: ArcGISClient | None = None
        self._fips_to_county: dict[str, int] = {}
        self._type_to_id: dict[str, int] = {}
        self._source_id: int | None = None

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (coercive type dimension)."""
        return [DimCoerciveType]

    def get_fact_tables(self) -> list[type]:
        """Return fact tables."""
        return [FactCoerciveInfrastructure]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load prison data into 3NF schema."""
        stats = LoadStats(source="hifld_prisons")

        if verbose:
            print("Loading HIFLD Prison Boundaries from ArcGIS Feature Service")

        try:
            self._client = ArcGISClient(PRISONS_SERVICE_URL)

            # Get record count for progress bar
            total_count = self._client.get_record_count()
            if verbose:
                print(f"Total facilities: {total_count:,}")

            if reset:
                if verbose:
                    print("Clearing existing prison data...")
                self._clear_prison_data(session)
                session.flush()

            # Load county lookup
            self._load_county_lookup(session)

            # Load/ensure coercive types
            type_count = self._load_coercive_types(session)
            stats.dimensions_loaded["dim_coercive_type"] = type_count

            # Load data source
            self._load_data_source(session)
            stats.dimensions_loaded["dim_data_source"] = 1

            session.flush()

            # Aggregate facilities by county
            fact_count = self._load_aggregated_facts(session, total_count, verbose)
            stats.facts_loaded["fact_coercive_infrastructure"] = fact_count
            stats.api_calls = (total_count // 2000) + 1  # Paginated queries

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        finally:
            if self._client:
                self._client.close()
                self._client = None

        return stats

    def _clear_prison_data(self, session: Session) -> None:
        """Clear only prison-related coercive infrastructure data."""
        # Get prison type IDs
        prison_type_codes = [code for code, _, _, _ in PRISON_TYPE_MAP.values()]
        types = session.query(DimCoerciveType).filter(
            DimCoerciveType.code.in_(prison_type_codes)
        ).all()
        type_ids = [t.coercive_type_id for t in types]

        if type_ids:
            session.query(FactCoerciveInfrastructure).filter(
                FactCoerciveInfrastructure.coercive_type_id.in_(type_ids)
            ).delete(synchronize_session=False)

    def _load_county_lookup(self, session: Session) -> None:
        """Build FIPS -> county_id lookup."""
        counties = session.query(DimCounty).all()
        self._fips_to_county = {c.fips: c.county_id for c in counties}

    def _load_coercive_types(self, session: Session) -> int:
        """Load/ensure coercive type dimension for prisons."""
        count = 0
        for code, name, category, command_chain in PRISON_TYPE_MAP.values():
            existing = session.query(DimCoerciveType).filter(
                DimCoerciveType.code == code
            ).first()

            if existing:
                self._type_to_id[code] = existing.coercive_type_id
            else:
                coercive_type = DimCoerciveType(
                    code=code,
                    name=name,
                    category=category,
                    command_chain=command_chain,
                )
                session.add(coercive_type)
                session.flush()
                self._type_to_id[code] = coercive_type.coercive_type_id
                count += 1

        return count

    def _load_data_source(self, session: Session) -> None:
        """Load data source dimension."""
        source = DimDataSource(
            source_code="HIFLD_PRISONS_2024",
            source_name="HIFLD Prison Boundaries",
            source_url="https://hifld-geoplatform.opendata.arcgis.com/datasets/prison-boundaries",
            source_agency="DHS HIFLD",
            source_year=2024,
        )
        session.add(source)
        session.flush()
        self._source_id = source.source_id

    def _load_aggregated_facts(
        self,
        session: Session,
        total_count: int,
        verbose: bool,
    ) -> int:
        """Load county-aggregated prison facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Aggregate: county_fips -> type_code -> {count, capacity}
        aggregates: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"count": 0, "capacity": 0})
        )

        features = self._client.query_all(
            out_fields="COUNTYFIPS,TYPE,CAPACITY,STATUS",
        )
        feature_iter = tqdm(features, total=total_count, desc="Prisons", disable=not verbose)

        for feature in feature_iter:
            attrs = feature.attributes

            # Get county FIPS (may be COUNTYFIPS or need construction from state+county)
            county_fips = attrs.get("COUNTYFIPS") or attrs.get("CNTY_FIPS")
            if not county_fips or len(str(county_fips)) < 5:
                continue
            county_fips = str(county_fips).zfill(5)

            # Skip if not in our county list
            if county_fips not in self._fips_to_county:
                continue

            # Map facility type to coercive type
            facility_type = (attrs.get("TYPE") or "").upper()
            type_info = PRISON_TYPE_MAP.get(facility_type)
            if not type_info:
                # Default to local if unknown
                type_info = PRISON_TYPE_MAP["LOCAL"]
            type_code = type_info[0]

            # Only count active facilities
            status = (attrs.get("STATUS") or "").upper()
            if status and "CLOSED" in status:
                continue

            # Aggregate
            capacity = attrs.get("CAPACITY") or 0
            if isinstance(capacity, str):
                try:
                    capacity = int(capacity)
                except ValueError:
                    capacity = 0

            aggregates[county_fips][type_code]["count"] += 1
            aggregates[county_fips][type_code]["capacity"] += capacity

        # Insert aggregated facts
        count = 0
        for county_fips, type_data in aggregates.items():
            county_id = self._fips_to_county.get(county_fips)
            if not county_id:
                continue

            for type_code, metrics in type_data.items():
                type_id = self._type_to_id.get(type_code)
                if not type_id:
                    continue

                fact = FactCoerciveInfrastructure(
                    county_id=county_id,
                    coercive_type_id=type_id,
                    source_id=self._source_id,
                    facility_count=metrics["count"],
                    total_capacity=metrics["capacity"] if metrics["capacity"] > 0 else None,
                )
                session.add(fact)
                count += 1

        session.flush()
        return count


__all__ = ["HIFLDPrisonsLoader"]
```

### Success Criteria:

#### Automated Verification:
- [x] Loader imports: `python -c "from babylon.data.hifld import HIFLDPrisonsLoader"`
- [x] Type checking passes: `mise run typecheck`
- [x] Load succeeds: `mise run data:load --loaders=hifld_prisons --states 06 --quiet`

#### Manual Verification:
- [x] Verify prison counts are reasonable for California (should have ~100+ facilities)
- [x] Verify data shows in query: `SELECT * FROM fact_coercive_infrastructure WHERE coercive_type_id IN (SELECT coercive_type_id FROM dim_coercive_type WHERE category='carceral')`

**Status: COMPLETE** - Prison loader implemented in `src/babylon/data/hifld/prisons.py`

---

## Phase 4: HIFLD Police & Military Loaders

### Overview
Implement loaders for HIFLD Law Enforcement Locations (~18,000 stations) and MIRTA Military Installations (~800 sites).

### Changes Required:

#### 1. Police Loader Implementation
**File**: `src/babylon/data/hifld/police.py`
**Changes**: New file - follows same pattern as prisons.py

Key differences:
- Service URL: `https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Local_Law_Enforcement_Locations/FeatureServer/0`
- Type codes: `police_local`, `police_sheriff`, `police_campus`
- No capacity field (count only)

#### 2. MIRTA Military Loader
**File**: `src/babylon/data/mirta/__init__.py` and `src/babylon/data/mirta/loader.py`
**Changes**: New files

Key differences:
- Service URL: `https://services7.arcgis.com/n1YM8pTrFmm7L4hs/arcgis/rest/services/mirta/FeatureServer/0`
- Type codes: `military_army`, `military_navy`, `military_air_force`, `military_other`
- Category: `military`, command_chain: `federal`

### Success Criteria:

#### Automated Verification:
- [x] Both loaders import successfully
- [x] Type checking passes: `mise run typecheck`
- [x] Load succeeds: `mise run data:load --loaders=hifld_police,mirta --states 06 --quiet`

**Status: COMPLETE** - Police loader in `src/babylon/data/hifld/police.py`, Military loader in `src/babylon/data/mirta/loader.py`

---

## Phase 5: HIFLD Electric Grid Loader

### Overview
Implement loader for HIFLD Electric Substations and Transmission Lines datasets.

### Changes Required:

#### 1. Electric Grid Loader
**File**: `src/babylon/data/hifld/electric.py`
**Changes**: New file

Two data sources:
- Substations: `https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Substations/FeatureServer/0`
- Transmission: `https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0`

Aggregation: County-level substation count, total capacity (MW), transmission line miles.

### Success Criteria:

#### Automated Verification:
- [x] Loader imports successfully
- [x] Load succeeds for single state: `mise run data:load --loaders=hifld_electric --states 06 --quiet`

**Status: COMPLETE** - Electric grid loader in `src/babylon/data/hifld/electric.py`

---

## Phase 6: Census CFS Loader [DEFERRED]

### Overview
Implement loader for Census Bureau Commodity Flow Survey 2022 API.

### Changes Required:

#### 1. CFS API Client
**File**: `src/babylon/data/external/census/cfs_client.py`
**Changes**: New file extending census API client pattern

API: `https://api.census.gov/data/2022/cfsarea`
Requires: Census API key (environment variable `CENSUS_API_KEY`)

#### 2. CFS Schema Tables
**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add commodity flow tables per research document Section 12.5

```python
class DimCFSCommodity(NormalizedBase):
    """CFS commodity classification."""
    ...

class FactCommodityFlow(NormalizedBase):
    """County-to-county commodity flow from CFS."""
    ...
```

#### 3. CFS Loader
**File**: `src/babylon/data/cfs/loader.py`
**Changes**: New file

### Success Criteria:

#### Automated Verification:
- [ ] CFS loader imports and loads successfully
- [ ] Commodity flows queryable by origin/destination county

**Status: DEFERRED** - CFS API only provides state-level and CFS-area geography, NOT county-level. To use this data, we need:
1. A county-to-state mapping table in the schema
2. Logic to distribute state-level flows proportionally to counties (e.g., by population or employment)

This is planned for future work when we build the geographic hierarchy infrastructure.

---

## Phase 7: FCC Broadband Loader [DEFERRED]

### Overview
Implement loader for FCC Broadband Data Collection (BDC) API.

### Changes Required:

#### 1. FCC API Client
**File**: `src/babylon/data/external/fcc/bdc_client.py`
**Changes**: New file

API spec: https://www.fcc.gov/sites/default/files/bdc-public-data-api-spec.pdf
Requires: Registration for username/token
Rate limit: 10 calls/minute

#### 2. FCC Loader
**File**: `src/babylon/data/fcc/loader.py`
**Changes**: New file

### Success Criteria:

#### Automated Verification:
- [ ] FCC loader imports and loads successfully
- [ ] Broadband coverage queryable by county

**Status: DEFERRED** - The FCC BDC API is file-download oriented rather than direct query:
1. Requires FCC account registration to get username + hash_value token
2. API downloads availability data files (CSV/GIS), not direct data query
3. Rate limit: 10 calls/minute
4. Downloaded files have `state_fips` field; need to investigate county extraction

API spec available at: `data/fcc/bdc-public-data-api-spec.pdf`

---

## Phase 8: CLI Integration

### Overview
Add new loaders to CLI and create `mise` tasks.

### Changes Required:

#### 1. Update ALL_LOADERS
**File**: `src/babylon/data/cli.py`
**Changes**: Add to ALL_LOADERS list and `_run_loader()` function

```python
ALL_LOADERS = [
    "census", "fred", "energy", "qcew", "trade", "materials",
    # New circulatory system loaders
    "hifld_prisons", "hifld_police", "hifld_electric",
    "mirta", "cfs", "fcc",
]
```

#### 2. Add individual CLI commands
**File**: `src/babylon/data/cli.py`
**Changes**: Add commands like `@app.command() def hifld_prisons(...)`

#### 3. Add mise tasks
**File**: `mise.toml`
**Changes**: Add `data:hifld`, `data:mirta`, `data:cfs`, `data:fcc` tasks

### Success Criteria:

#### Automated Verification:
- [x] `mise run data:load --help` shows new loaders
- [x] `mise run data:hifld-prisons --quiet` runs without error
- [x] All new loaders pass lint and type checks

**Status: COMPLETE** - CLI integration implemented:
- Added to `ALL_LOADERS`: `hifld_prisons`, `hifld_police`, `hifld_electric`, `mirta`
- Added individual CLI commands: `hifld-prisons`, `hifld-police`, `hifld-electric`, `mirta`
- Added mise tasks: `data:hifld-prisons`, `data:hifld-police`, `data:hifld-electric`, `data:mirta`
- Files modified: `src/babylon/data/cli.py`, `.mise.toml`
- All 782 unit tests passing

---

## Testing Strategy

### Unit Tests:
- ArcGIS client pagination (mock HTTP responses)
- County FIPS lookup edge cases (missing FIPS, malformed)
- Type mapping (unknown facility types default correctly)
- Aggregation logic (count, capacity accumulation)

### Integration Tests:
- Single-state load/query cycle for each loader
- Schema migration with new tables
- Foreign key integrity (all county_ids valid)

### Manual Testing Steps:
1. Load California only: `mise run data:load --loaders=hifld_prisons,hifld_police,mirta --states 06`
2. Verify counts: `sqlite3 data/sqlite/marxist-data-3NF.sqlite "SELECT * FROM fact_coercive_infrastructure LIMIT 10"`
3. Cross-reference with HIFLD web portal counts

---

## Performance Considerations

- **Pagination**: ArcGIS limits to 2000 records per request; client handles automatically
- **Rate Limiting**: 0.2s delay between requests to avoid 429 errors
- **Memory**: Aggregate in-memory before bulk insert (fits in RAM for ~20K facilities)
- **Batch Size**: Use config.batch_size for bulk inserts (default 10,000)

---

## References

- Research document: `thoughts/shared/research/2026-01-05-dot-transportation-integration.md`
- Schema pattern: `src/babylon/data/normalize/schema.py`
- Loader pattern: `src/babylon/data/census/loader_3nf.py`
- API client pattern: `src/babylon/data/census/api_client.py`
- CLI pattern: `src/babylon/data/cli.py`
