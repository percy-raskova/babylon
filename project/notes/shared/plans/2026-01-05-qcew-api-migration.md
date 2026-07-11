# QCEW API Migration: Hybrid API + File-Based Implementation Plan

## Overview

Implement a **hybrid data loading strategy** for QCEW data that maximizes temporal coverage:
- **API-first**: Fetch recent 5 years (2021-2025) from BLS QCEW Open Data API
- **File fallback**: Load historical years (2013-2020) from downloaded CSV files
- **Geographic expansion**: Support State, MSA, Micropolitan, and County aggregates

This approach provides the best of both worlds: convenience for recent data, maximum coverage for historical analysis.

## Current State Analysis

### Existing Implementation

**File Location**: `src/babylon/data/qcew/`

| File | Purpose |
|------|---------|
| `loader_3nf.py` (465 lines) | File-based CSV loader using `Path.glob("*.csv")` |
| `parser.py` (369 lines) | CSV parsing with `QcewRecord` and `QcewRawRecord` dataclasses |
| `schema.py` | SQLAlchemy ORM models for raw QCEW data |
| `__init__.py` | Module exports |

**Current Flow**:
1. User downloads CSV files from BLS website to `data/qcew/`
2. `QcewLoader.load()` discovers CSVs via `glob("*.csv")`
3. `parse_qcew_csv()` reads each file and yields `QcewRecord` objects
4. Loader resolves dimensions (Industry, Ownership, Time, County)
5. Creates `FactQcewAnnual` records and commits to SQLite

**Configuration**: `LoaderConfig.qcew_years: list[int]` (default: 2015-2023)

### Key Discoveries

1. **QCEW Open Data API exists** at `https://data.bls.gov/cew/data/api/`
2. **Three data slice types**:
   - Area: `/api/{year}/{quarter}/area/{area_code}.csv`
   - Industry: `/api/{year}/{quarter}/industry/{naics_code}.csv`
   - Size: `/api/{year}/{quarter}/size/{size_class}.csv`
3. **CRITICAL: API provides only last 5 years** (rolling window, currently ~2021-2025)
4. **No authentication required** (unlike FRED)
5. **Annual data available** via quarter="a" for annual aggregates

### Historical Data Compatibility Issues

**MSA Definition Changes** (affects MSA/CSA codes):
- 1990-2012: December 2003 MSA definitions
- 2013+: 2010 Census-based MSA definitions
- This means MSA codes before 2013 won't match our current `DimMetroArea`

**Connecticut County FIPS Changes** (2024):
- Pre-2024: Legacy Connecticut county FIPS codes
- 2024+: New Planning Region-based codes
- Impact: Connecticut counties need code translation for 2024+ data

**County FIPS Codes**: Generally stable except rare changes

**Recommendation**: Load data from **2013+** to maintain MSA code compatibility with current schema. Earlier years (1990-2012) would require MSA code translation tables.

### Aggregation Level Codes (agglvl_code)

| Code Range | Geographic Level | Included in Plan |
|------------|------------------|------------------|
| 10-18 | National | No (too aggregated) |
| 20-28 | Statewide | **Yes** |
| 30-38 | MSA/CSA | **Yes** |
| 40-48 | Metropolitan/Micropolitan Division | **Yes** |
| 50-58 | CSA | **Yes** |
| 70-78 | County | **Yes** |

### Existing API Client Patterns to Follow

The FRED loader (`src/babylon/data/fred/api_client.py`) provides the template:
- Rate limiting via `REQUEST_DELAY_SECONDS`
- Retry logic with exponential backoff (`MAX_RETRIES`, `RETRY_BACKOFF_FACTOR`)
- Custom exception classes (`FredAPIError`)
- Dataclasses for API responses (`SeriesMetadata`, `Observation`)
- Context manager pattern (`__enter__`/`__exit__`)
- httpx for HTTP client (already in dependencies)

## Desired End State

After implementation:

1. **Hybrid loading**: API for recent years (2021+), files for historical (2013-2020)
2. **Maximum coverage**: Data from 2013-2025 (13 years vs current 9 years)
3. **Geographic expansion**: County + State + MSA + Micropolitan aggregates
4. **Console feedback**: Errors logged to console AND logger (not silent)
5. **Same database output**: `FactQcewAnnual` + new `FactQcewStateAnnual`, `FactQcewMetroAnnual`
6. **Configurable via LoaderConfig**: Year range, geographic scope, API vs files
7. **Rate-limited**: Respects BLS server limits (no auth = be polite)

### Verification Criteria

```bash
# Hybrid loading: API for recent, files for historical
mise run data:ingest --loaders qcew --years 2013-2025

# Check geographic coverage
sqlite3 data/sqlite/marxist-data-3NF.sqlite "
SELECT
  'Counties' as level, COUNT(*) as records FROM fact_qcew_annual
UNION ALL
SELECT 'States', COUNT(*) FROM fact_qcew_state_annual
UNION ALL
SELECT 'Metro Areas', COUNT(*) FROM fact_qcew_metro_annual
"
# Expected: County (~2.8M), State (~50K), Metro (~200K)

# Verify year coverage
sqlite3 data/sqlite/marxist-data-3NF.sqlite "
SELECT MIN(t.year), MAX(t.year) FROM fact_qcew_annual f
JOIN dim_time t ON f.time_id = t.time_id
"
# Expected: 2013, 2025
```

## What We're NOT Doing

1. **NOT loading pre-2013 data** - MSA codes incompatible with current schema
2. **NOT adding quarterly granularity** - Continue using annual aggregates only
3. **NOT supporting 1990-2012** - Would require MSA code translation tables
4. **NOT removing legacy parser** - Keep `parser.py` for file-based loading
5. **NOT adding new data fields** - Match current column set

## Implementation Approach

### Strategy: Hybrid Loading with Multi-Geographic Support

**Year-Based Data Source Selection**:
```
2021-2025: API (BLS QCEW Open Data)
2013-2020: Files (downloaded CSVs from BLS)
```

**Geographic Levels to Load**:
1. **County** (agglvl_code 70-78): Primary level, FK to `DimCounty`
2. **State** (agglvl_code 20-28): Aggregate, FK to `DimState`
3. **MSA** (agglvl_code 30-38): Metropolitan Statistical Areas, FK to `DimMetroArea`
4. **Micropolitan** (agglvl_code 40-48): Micropolitan Areas, FK to `DimMetroArea`
5. **CSA** (agglvl_code 50-58): Combined Statistical Areas, FK to `DimMetroArea`

**Area-based fetching** (for API mode):
- Each area file contains all industries and ownerships for that geographic unit
- ~3,200 county area codes per year
- ~400 MSA/micropolitan/CSA codes per year
- ~52 state area codes per year

**Error Handling Strategy**:
- Log errors to **both** console (`typer.echo()`) and logger (`logger.warning()`)
- Continue loading on 404 (area not available for year)
- Fail fast on 5xx server errors after retries
- Report error count in final statistics

**Database Schema Changes**:
Two new fact tables for geographic aggregates:
- `FactQcewStateAnnual`: State-level aggregates
- `FactQcewMetroAnnual`: MSA/Micropolitan/CSA aggregates

---

## Phase 0: Schema Extensions for Geographic Aggregates

### Overview

Add new fact tables for state-level and metro-area-level QCEW aggregates, enabling richer geographic analysis.

### Changes Required

#### 1. Update: `src/babylon/data/normalize/schema.py`

Add two new fact tables after `FactQcewAnnual`:

```python
class FactQcewStateAnnual(NormalizedBase):
    """State-level QCEW employment/wage aggregates.

    Stores annual aggregates at the state level (agglvl_code 20-28).
    Complements county-level data with higher-level geographic patterns.
    """

    __tablename__ = "fact_qcew_state_annual"

    fact_id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("dim_state.state_id"), nullable=False)
    industry_id: Mapped[int] = mapped_column(ForeignKey("dim_industry.industry_id"), nullable=False)
    ownership_id: Mapped[int] = mapped_column(ForeignKey("dim_ownership.ownership_id"), nullable=False)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), nullable=False)

    # Core metrics
    establishments: Mapped[int | None]
    employment: Mapped[int | None]
    total_wages_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    avg_weekly_wage_usd: Mapped[int | None]
    avg_annual_pay_usd: Mapped[int | None]

    # Location quotients
    lq_employment: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    lq_annual_pay: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Metadata
    disclosure_code: Mapped[str | None] = mapped_column(String(5))
    agglvl_code: Mapped[int | None]  # Specific aggregation level

    __table_args__ = (
        Index("idx_qcew_state_time", "state_id", "time_id"),
        Index("idx_qcew_state_industry", "industry_id"),
    )


class FactQcewMetroAnnual(NormalizedBase):
    """Metro-area-level QCEW employment/wage aggregates.

    Stores annual aggregates at MSA/Micropolitan/CSA levels (agglvl_code 30-58).
    Links to DimMetroArea for geographic identification.
    """

    __tablename__ = "fact_qcew_metro_annual"

    fact_id: Mapped[int] = mapped_column(primary_key=True)
    metro_area_id: Mapped[int] = mapped_column(
        ForeignKey("dim_metro_area.metro_area_id"), nullable=False
    )
    industry_id: Mapped[int] = mapped_column(ForeignKey("dim_industry.industry_id"), nullable=False)
    ownership_id: Mapped[int] = mapped_column(ForeignKey("dim_ownership.ownership_id"), nullable=False)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), nullable=False)

    # Core metrics
    establishments: Mapped[int | None]
    employment: Mapped[int | None]
    total_wages_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    avg_weekly_wage_usd: Mapped[int | None]
    avg_annual_pay_usd: Mapped[int | None]

    # Location quotients
    lq_employment: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    lq_annual_pay: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Metadata
    disclosure_code: Mapped[str | None] = mapped_column(String(5))
    agglvl_code: Mapped[int | None]  # 30-38=MSA, 40-48=Micro, 50-58=CSA
    area_type: Mapped[str | None] = mapped_column(String(15))  # msa/micropolitan/csa

    __table_args__ = (
        Index("idx_qcew_metro_time", "metro_area_id", "time_id"),
        Index("idx_qcew_metro_industry", "industry_id"),
        Index("idx_qcew_metro_type", "area_type"),
    )
```

#### 2. Update: `src/babylon/data/normalize/schema.py` `__all__`

Add new tables to exports:

```python
__all__ = [
    # ... existing exports ...
    "FactQcewStateAnnual",
    "FactQcewMetroAnnual",
]
```

### Success Criteria

#### Automated Verification:
- [ ] Type checking passes: `poetry run mypy src/babylon/data/normalize/schema.py`
- [ ] Database initializes with new tables: `mise run data:db-init`
- [ ] Schema tests pass: `poetry run pytest tests/unit/data/test_normalize/ -v`

#### Manual Verification:
- [ ] Tables appear in SQLite: `sqlite3 data/sqlite/marxist-data-3NF.sqlite ".tables"`
- [ ] Indexes created correctly: `.indices fact_qcew_state_annual`

---

## Phase 1: Create QCEW API Client

### Overview

Create a new `api_client.py` module following the FRED pattern with BLS QCEW Open Data API integration.

### Changes Required

#### 1. New File: `src/babylon/data/qcew/api_client.py`

**Purpose**: HTTP client for BLS QCEW Open Data API with rate limiting and error handling.

```python
"""BLS QCEW (Quarterly Census of Employment and Wages) API client.

Provides rate-limited access to the BLS QCEW Open Data API for fetching
employment and wage data by area, industry, or establishment size class.

API Documentation: https://www.bls.gov/cew/additional-resources/open-data/
"""

import csv
import io
import logging
import time
from dataclasses import dataclass
from typing import Iterator

import httpx

logger = logging.getLogger(__name__)

# QCEW API configuration
BASE_URL = "https://data.bls.gov/cew/data/api"

# Rate limiting: BLS has no official limit, but be polite
# Conservative 0.5s delay between requests
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_TIMEOUT = 60.0  # Large CSV files may take time


@dataclass
class QcewAPIError(Exception):
    """Error from QCEW API."""
    status_code: int
    message: str
    url: str


@dataclass
class QcewAreaRecord:
    """Parsed record from QCEW area slice CSV."""
    # Geographic
    area_fips: str
    own_code: str
    industry_code: str
    agglvl_code: int
    size_code: str
    year: int
    qtr: str

    # Core metrics
    disclosure_code: str
    annual_avg_estabs: int | None
    annual_avg_emplvl: int | None
    total_annual_wages: float | None
    taxable_annual_wages: float | None
    annual_contributions: float | None
    annual_avg_wkly_wage: int | None
    avg_annual_pay: int | None

    # Location quotients
    lq_disclosure_code: str
    lq_annual_avg_estabs: float | None
    lq_annual_avg_emplvl: float | None
    lq_total_annual_wages: float | None
    lq_taxable_annual_wages: float | None
    lq_annual_contributions: float | None
    lq_annual_avg_wkly_wage: float | None
    lq_avg_annual_pay: float | None

    # Year-over-year changes
    oty_disclosure_code: str
    oty_annual_avg_estabs_chg: int | None
    oty_annual_avg_estabs_pct_chg: float | None
    oty_annual_avg_emplvl_chg: int | None
    oty_annual_avg_emplvl_pct_chg: float | None
    oty_total_annual_wages_chg: float | None
    oty_total_annual_wages_pct_chg: float | None
    oty_taxable_annual_wages_chg: float | None
    oty_taxable_annual_wages_pct_chg: float | None
    oty_annual_contributions_chg: float | None
    oty_annual_contributions_pct_chg: float | None
    oty_annual_avg_wkly_wage_chg: int | None
    oty_annual_avg_wkly_wage_pct_chg: float | None
    oty_avg_annual_pay_chg: int | None
    oty_avg_annual_pay_pct_chg: float | None


class QcewAPIClient:
    """Client for BLS QCEW Open Data API.

    Fetches employment and wage data with rate limiting and error handling.
    No authentication required.

    Example:
        with QcewAPIClient() as client:
            for record in client.get_area_data(2023, "01001"):
                print(f"{record.industry_code}: {record.annual_avg_emplvl}")
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize QCEW API client."""
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "QcewAPIClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _fetch_csv(self, url: str) -> str:
        """Fetch CSV data from URL with retries."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(url)

                if response.status_code == 200:
                    return response.text

                if response.status_code == 404:
                    # Area/year combination doesn't exist - log and raise
                    msg = f"Data not available: {url}"
                    logger.info(msg)  # Info level - expected for some areas
                    raise QcewAPIError(
                        status_code=404,
                        message="Data not available for this area/year",
                        url=url,
                    )

                if response.status_code == 429:
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR ** attempt)
                    msg = f"Rate limited, waiting {wait_time:.1f}s"
                    logger.warning(msg)
                    print(msg)  # Console output for visibility
                    time.sleep(wait_time)
                    continue

                # Unexpected error - log to both console and logger
                msg = f"API error {response.status_code}: {url}"
                logger.error(msg)
                print(f"ERROR: {msg}")  # Console visibility
                raise QcewAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=url,
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR ** attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise QcewAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=url,
        )

    def get_area_annual_data(
        self,
        year: int,
        area_fips: str,
    ) -> Iterator[QcewAreaRecord]:
        """Fetch annual QCEW data for a specific area.

        Args:
            year: Calendar year (e.g., 2023).
            area_fips: Area FIPS code (e.g., "01001" for Autauga County, AL).

        Yields:
            QcewAreaRecord for each data row.

        Raises:
            QcewAPIError: If request fails.
        """
        url = f"{BASE_URL}/{year}/a/area/{area_fips}.csv"
        csv_text = self._fetch_csv(url)
        yield from self._parse_area_csv(csv_text)

    def get_industry_annual_data(
        self,
        year: int,
        naics_code: str,
    ) -> Iterator[QcewAreaRecord]:
        """Fetch annual QCEW data for a specific industry.

        Args:
            year: Calendar year.
            naics_code: NAICS code (hyphens converted to underscores).

        Yields:
            QcewAreaRecord for each data row.
        """
        # Convert hyphens to underscores for API
        api_code = naics_code.replace("-", "_")
        url = f"{BASE_URL}/{year}/a/industry/{api_code}.csv"
        csv_text = self._fetch_csv(url)
        yield from self._parse_area_csv(csv_text)

    def _parse_area_csv(self, csv_text: str) -> Iterator[QcewAreaRecord]:
        """Parse CSV text into QcewAreaRecord objects."""
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                yield QcewAreaRecord(
                    area_fips=row["area_fips"].strip(),
                    own_code=row["own_code"].strip(),
                    industry_code=row["industry_code"].strip(),
                    agglvl_code=int(row["agglvl_code"]),
                    size_code=row["size_code"].strip(),
                    year=int(row["year"]),
                    qtr=row["qtr"].strip(),
                    disclosure_code=row.get("disclosure_code", "").strip(),
                    annual_avg_estabs=_safe_int(row.get("annual_avg_estabs", "")),
                    annual_avg_emplvl=_safe_int(row.get("annual_avg_emplvl", "")),
                    total_annual_wages=_safe_float(row.get("total_annual_wages", "")),
                    taxable_annual_wages=_safe_float(row.get("taxable_annual_wages", "")),
                    annual_contributions=_safe_float(row.get("annual_contributions", "")),
                    annual_avg_wkly_wage=_safe_int(row.get("annual_avg_wkly_wage", "")),
                    avg_annual_pay=_safe_int(row.get("avg_annual_pay", "")),
                    lq_disclosure_code=row.get("lq_disclosure_code", "").strip(),
                    lq_annual_avg_estabs=_safe_float(row.get("lq_annual_avg_estabs", "")),
                    lq_annual_avg_emplvl=_safe_float(row.get("lq_annual_avg_emplvl", "")),
                    lq_total_annual_wages=_safe_float(row.get("lq_total_annual_wages", "")),
                    lq_taxable_annual_wages=_safe_float(row.get("lq_taxable_annual_wages", "")),
                    lq_annual_contributions=_safe_float(row.get("lq_annual_contributions", "")),
                    lq_annual_avg_wkly_wage=_safe_float(row.get("lq_annual_avg_wkly_wage", "")),
                    lq_avg_annual_pay=_safe_float(row.get("lq_avg_annual_pay", "")),
                    oty_disclosure_code=row.get("oty_disclosure_code", "").strip(),
                    oty_annual_avg_estabs_chg=_safe_int(row.get("oty_annual_avg_estabs_chg", "")),
                    oty_annual_avg_estabs_pct_chg=_safe_float(row.get("oty_annual_avg_estabs_pct_chg", "")),
                    oty_annual_avg_emplvl_chg=_safe_int(row.get("oty_annual_avg_emplvl_chg", "")),
                    oty_annual_avg_emplvl_pct_chg=_safe_float(row.get("oty_annual_avg_emplvl_pct_chg", "")),
                    oty_total_annual_wages_chg=_safe_float(row.get("oty_total_annual_wages_chg", "")),
                    oty_total_annual_wages_pct_chg=_safe_float(row.get("oty_total_annual_wages_pct_chg", "")),
                    oty_taxable_annual_wages_chg=_safe_float(row.get("oty_taxable_annual_wages_chg", "")),
                    oty_taxable_annual_wages_pct_chg=_safe_float(row.get("oty_taxable_annual_wages_pct_chg", "")),
                    oty_annual_contributions_chg=_safe_float(row.get("oty_annual_contributions_chg", "")),
                    oty_annual_contributions_pct_chg=_safe_float(row.get("oty_annual_contributions_pct_chg", "")),
                    oty_annual_avg_wkly_wage_chg=_safe_int(row.get("oty_annual_avg_wkly_wage_chg", "")),
                    oty_annual_avg_wkly_wage_pct_chg=_safe_float(row.get("oty_annual_avg_wkly_wage_pct_chg", "")),
                    oty_avg_annual_pay_chg=_safe_int(row.get("oty_avg_annual_pay_chg", "")),
                    oty_avg_annual_pay_pct_chg=_safe_float(row.get("oty_avg_annual_pay_pct_chg", "")),
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping malformed row: {e}")
                continue


def _safe_int(value: str) -> int | None:
    """Convert string to int, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _safe_float(value: str) -> float | None:
    """Convert string to float, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


# Area code utilities
def get_state_area_code(state_fips: str) -> str:
    """Convert 2-digit state FIPS to QCEW area code.

    State-level area codes are state FIPS + "000".
    Example: "01" (Alabama) -> "01000"
    """
    return f"{state_fips}000"


def get_county_area_codes(state_fips: str) -> list[str]:
    """Get list of county FIPS codes for a state.

    This requires DimCounty to be populated first (by CensusLoader).
    Returns 5-digit county FIPS codes.
    """
    # This will be called from the loader with session access
    raise NotImplementedError("Call from loader with session access")


__all__ = [
    "QcewAPIClient",
    "QcewAPIError",
    "QcewAreaRecord",
    "get_state_area_code",
]
```

### Success Criteria

#### Automated Verification:
- [ ] File exists at `src/babylon/data/qcew/api_client.py`
- [ ] Type checking passes: `poetry run mypy src/babylon/data/qcew/api_client.py`
- [ ] Linting passes: `poetry run ruff check src/babylon/data/qcew/api_client.py`
- [ ] Unit tests pass: `poetry run pytest tests/unit/data/test_qcew_api_client.py -v`

#### Manual Verification:
- [ ] API client can fetch data for a known area/year combination
- [ ] Rate limiting delays are observed between requests
- [ ] 404 errors are handled gracefully for missing data

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Create API Client Unit Tests

### Overview

Create comprehensive unit tests for the QCEW API client using mocked responses.

### Changes Required

#### 1. New File: `tests/unit/data/test_qcew_api_client.py`

```python
"""Unit tests for QCEW API client.

Tests HTTP interaction, rate limiting, error handling, and CSV parsing
using mocked responses.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
import httpx

from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAPIError,
    QcewAreaRecord,
    get_state_area_code,
    _safe_int,
    _safe_float,
)


# Sample CSV response for testing
SAMPLE_CSV = '''area_fips,own_code,industry_code,agglvl_code,size_code,year,qtr,disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages,taxable_annual_wages,annual_contributions,annual_avg_wkly_wage,avg_annual_pay,lq_disclosure_code,lq_annual_avg_estabs,lq_annual_avg_emplvl,lq_total_annual_wages,lq_taxable_annual_wages,lq_annual_contributions,lq_annual_avg_wkly_wage,lq_avg_annual_pay,oty_disclosure_code,oty_annual_avg_estabs_chg,oty_annual_avg_estabs_pct_chg,oty_annual_avg_emplvl_chg,oty_annual_avg_emplvl_pct_chg,oty_total_annual_wages_chg,oty_total_annual_wages_pct_chg,oty_taxable_annual_wages_chg,oty_taxable_annual_wages_pct_chg,oty_annual_contributions_chg,oty_annual_contributions_pct_chg,oty_annual_avg_wkly_wage_chg,oty_annual_avg_wkly_wage_pct_chg,oty_avg_annual_pay_chg,oty_avg_annual_pay_pct_chg
01001,5,10,78,0,2023,A,,1234,5678,123456789.00,100000000.00,1234567.00,456,23456,N,1.23,0.89,1.05,1.02,0.95,1.01,1.03,,10,0.8,50,0.9,1234567.00,1.0,1000000.00,1.0,12345.00,1.0,5,1.1,500,2.2
'''


class TestQcewAPIClient:
    """Tests for QcewAPIClient class."""

    def test_context_manager(self) -> None:
        """Client works as context manager."""
        with QcewAPIClient() as client:
            assert client._client is not None
        # Client should be closed after context

    @patch.object(httpx.Client, "get")
    def test_get_area_annual_data_success(self, mock_get: MagicMock) -> None:
        """Successfully fetches and parses area data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_CSV
        mock_get.return_value = mock_response

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        assert len(records) == 1
        record = records[0]
        assert record.area_fips == "01001"
        assert record.industry_code == "10"
        assert record.annual_avg_estabs == 1234
        assert record.annual_avg_emplvl == 5678
        assert record.avg_annual_pay == 23456

    @patch.object(httpx.Client, "get")
    def test_get_area_annual_data_404(self, mock_get: MagicMock) -> None:
        """Handles 404 for missing area/year combination."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with QcewAPIClient() as client:
            with pytest.raises(QcewAPIError) as exc_info:
                list(client.get_area_annual_data(2023, "99999"))

        assert exc_info.value.status_code == 404

    @patch.object(httpx.Client, "get")
    def test_retry_on_rate_limit(self, mock_get: MagicMock) -> None:
        """Retries on 429 rate limit response."""
        mock_rate_limited = MagicMock()
        mock_rate_limited.status_code = 429

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.text = SAMPLE_CSV

        mock_get.side_effect = [mock_rate_limited, mock_success]

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        assert len(records) == 1
        assert mock_get.call_count == 2


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_safe_int_valid(self) -> None:
        """Converts valid integers."""
        assert _safe_int("123") == 123
        assert _safe_int("0") == 0
        assert _safe_int("-456") == -456

    def test_safe_int_invalid(self) -> None:
        """Returns None for invalid integers."""
        assert _safe_int("") is None
        assert _safe_int("  ") is None
        assert _safe_int("abc") is None
        assert _safe_int("12.34") is None

    def test_safe_float_valid(self) -> None:
        """Converts valid floats."""
        assert _safe_float("123.45") == 123.45
        assert _safe_float("0.0") == 0.0
        assert _safe_float("-456.78") == -456.78

    def test_safe_float_invalid(self) -> None:
        """Returns None for invalid floats."""
        assert _safe_float("") is None
        assert _safe_float("  ") is None
        assert _safe_float("abc") is None

    def test_get_state_area_code(self) -> None:
        """Converts state FIPS to area code."""
        assert get_state_area_code("01") == "01000"
        assert get_state_area_code("06") == "06000"
        assert get_state_area_code("56") == "56000"
```

### Success Criteria

#### Automated Verification:
- [ ] Tests pass: `poetry run pytest tests/unit/data/test_qcew_api_client.py -v`
- [ ] Coverage is adequate: `poetry run pytest tests/unit/data/test_qcew_api_client.py --cov=babylon.data.qcew.api_client`
- [ ] Type checking passes: `poetry run mypy tests/unit/data/test_qcew_api_client.py`

**Implementation Note**: After completing this phase and all automated verification passes, proceed to Phase 3.

---

## Phase 3: Update QcewLoader for Hybrid + Multi-Geographic Support

### Overview

Modify `loader_3nf.py` to:
1. Use hybrid loading: API for 2021+, files for 2013-2020
2. Support all geographic levels: County, State, MSA, Micropolitan, CSA
3. Populate new fact tables: `FactQcewStateAnnual`, `FactQcewMetroAnnual`
4. Log errors to console AND logger (not silent)

### Changes Required

#### 1. Update: `src/babylon/data/qcew/loader_3nf.py`

Key changes:
1. Add `QcewAPIClient` import and new fact table imports
2. Implement hybrid year logic: `API_CUTOFF_YEAR = 2021`
3. Add geographic routing by `agglvl_code`:
   - 20-28 → `FactQcewStateAnnual`
   - 30-58 → `FactQcewMetroAnnual`
   - 70-78 → `FactQcewAnnual` (county, existing)
4. Add console logging via `typer.echo()` or `print()`
5. Track stats per geographic level

```python
"""QCEW data loader for direct 3NF schema population.

Loads BLS Quarterly Census of Employment and Wages data using a hybrid approach:
- API for recent years (2021+): Fetches directly from BLS QCEW Open Data API
- Files for historical years (2013-2020): Reads from local CSV downloads

Supports three geographic levels:
- County (agglvl_code 70-78) → FactQcewAnnual
- State (agglvl_code 20-28) → FactQcewStateAnnual
- Metro/Micro/CSA (agglvl_code 30-58) → FactQcewMetroAnnual

Example:
    from babylon.data.qcew import QcewLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(qcew_years=list(range(2013, 2026)))
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session)  # Hybrid: API for 2021+, files for 2013-2020
        print(f"Loaded {stats.facts_loaded} QCEW observations")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import delete
from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.normalize.classifications import classify_class_composition
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    DimIndustry,
    DimMetroArea,
    DimOwnership,
    DimState,
    DimTime,
    FactQcewAnnual,
    FactQcewMetroAnnual,
    FactQcewStateAnnual,
)
from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAPIError,
    get_state_area_code,
)
from babylon.data.qcew.parser import (
    determine_naics_level,
    extract_state_fips,
    parse_qcew_csv,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Year cutoff for hybrid loading
# API provides rolling 5 years; files for earlier
API_CUTOFF_YEAR = 2021


class QcewLoader(DataLoader):
    """Loader for BLS QCEW data into 3NF schema.

    Uses hybrid loading strategy:
    - API for years >= API_CUTOFF_YEAR (2021+)
    - Files for years < API_CUTOFF_YEAR (2013-2020)

    Supports three geographic levels:
    - County (agglvl_code 70-78) → FactQcewAnnual
    - State (agglvl_code 20-28) → FactQcewStateAnnual
    - Metro/Micro/CSA (agglvl_code 30-58) → FactQcewMetroAnnual

    The loader populates:
    - DimIndustry: NAICS industries with class composition
    - DimOwnership: Ownership types (private/government)
    - DimTime: Temporal dimension (shared with other loaders)
    - FactQcewAnnual: County-level employment/wage observations
    - FactQcewStateAnnual: State-level aggregates
    - FactQcewMetroAnnual: MSA/Micropolitan/CSA aggregates
    """

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimIndustry, DimOwnership, DimTime]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactQcewAnnual, FactQcewStateAnnual, FactQcewMetroAnnual]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load QCEW data into 3NF schema using hybrid approach.

        Args:
            session: SQLAlchemy session for normalized database.
            reset: If True, clear existing QCEW data before loading.
            verbose: If True, log progress messages to console AND logger.
            **kwargs: Additional options including:
                force_api: If True, use API for all years (may fail for old years).
                force_files: If True, use files for all years.
                data_path: Path to QCEW CSV directory for file-based loading.

        Returns:
            LoadStats with counts of loaded records by geographic level.
        """
        force_api = kwargs.get("force_api", False)
        force_files = kwargs.get("force_files", False)
        data_path = kwargs.get("data_path")

        # Partition years into API vs file-based
        api_years = []
        file_years = []

        for year in self.config.qcew_years:
            if force_files:
                file_years.append(year)
            elif force_api or year >= API_CUTOFF_YEAR:
                api_years.append(year)
            else:
                file_years.append(year)

        if verbose:
            if api_years:
                msg = f"API years: {min(api_years)}-{max(api_years)}"
                logger.info(msg)
                print(msg)
            if file_years:
                msg = f"File years: {min(file_years)}-{max(file_years)}"
                logger.info(msg)
                print(msg)

        stats = LoadStats(source="qcew_hybrid")

        if reset:
            self._clear_qcew_tables(session, verbose)

        # Load from API for recent years
        if api_years:
            api_stats = self._load_from_api(session, api_years, verbose)
            self._merge_stats(stats, api_stats)

        # Load from files for historical years
        if file_years:
            file_stats = self._load_from_files(session, file_years, verbose, data_path)
            self._merge_stats(stats, file_stats)

        return stats

    def _merge_stats(self, target: LoadStats, source: LoadStats) -> None:
        """Merge source stats into target."""
        for k, v in source.dimensions_loaded.items():
            target.dimensions_loaded[k] = target.dimensions_loaded.get(k, 0) + v
        for k, v in source.facts_loaded.items():
            target.facts_loaded[k] = target.facts_loaded.get(k, 0) + v
        target.api_calls += source.api_calls
        target.files_processed += source.files_processed
        target.errors.extend(source.errors)

    def _load_from_api(
        self,
        session: Session,
        years: list[int],
        verbose: bool,
    ) -> LoadStats:
        """Load QCEW data from BLS API for specified years.

        Processes all geographic levels:
        - County (agglvl_code 70-78) → FactQcewAnnual
        - State (agglvl_code 20-28) → FactQcewStateAnnual
        - Metro/Micro/CSA (agglvl_code 30-58) → FactQcewMetroAnnual
        """
        stats = LoadStats(source="qcew_api")

        # Load data source dimension
        self._load_data_source(session, verbose)

        # Get geographic lookups
        states = session.query(DimState).all()
        if not states:
            msg = "No states in DimState - run CensusLoader first"
            stats.errors.append(msg)
            logger.error(msg)
            print(f"ERROR: {msg}")
            return stats

        # Build lookup caches
        state_lookup = self._build_state_lookup(session)
        county_lookup = self._build_county_lookup(session)
        metro_lookup = self._build_metro_lookup(session)  # NEW
        industry_lookup: dict[str, int] = {}
        ownership_lookup: dict[str, int] = {}
        time_cache: dict[int, int] = {}

        # Counters per geographic level
        county_count = 0
        state_count = 0
        metro_count = 0

        if verbose:
            msg = f"API: Fetching {len(years)} years, {len(states)} states"
            logger.info(msg)
            print(msg)

        with QcewAPIClient() as client:
            for year in years:
                if verbose:
                    msg = f"Processing {year} via API..."
                    logger.info(msg)
                    print(msg)

                state_iter = tqdm(states, desc=f"States {year}", disable=not verbose)

                for state in state_iter:
                    area_code = get_state_area_code(state.state_fips)
                    stats.api_calls += 1

                    try:
                        for record in client.get_area_annual_data(year, area_code):
                            # Route by aggregation level
                            agglvl = record.agglvl_code

                            # Resolve shared dimensions
                            industry_id = self._get_or_create_industry(
                                session, record.industry_code,
                                f"Industry {record.industry_code}",
                                industry_lookup,
                            )
                            ownership_id = self._get_or_create_ownership(
                                session, record.own_code,
                                f"Ownership {record.own_code}",
                                ownership_lookup,
                            )
                            time_id = self._get_or_create_time(session, year, time_cache)

                            # Route to appropriate fact table
                            if 70 <= agglvl <= 78:
                                # County level
                                county_id = county_lookup.get(record.area_fips)
                                if county_id is None:
                                    county_id = self._get_or_create_county(
                                        session, record.area_fips,
                                        f"County {record.area_fips}",
                                        state_lookup.get(state.state_fips, state.state_id),
                                        county_lookup,
                                    )
                                fact = FactQcewAnnual(
                                    county_id=county_id,
                                    industry_id=industry_id,
                                    ownership_id=ownership_id,
                                    time_id=time_id,
                                    establishments=record.annual_avg_estabs,
                                    employment=record.annual_avg_emplvl,
                                    total_wages_usd=record.total_annual_wages,
                                    avg_weekly_wage_usd=record.annual_avg_wkly_wage,
                                    avg_annual_pay_usd=record.avg_annual_pay,
                                    lq_employment=record.lq_annual_avg_emplvl,
                                    lq_annual_pay=record.lq_avg_annual_pay,
                                    disclosure_code=record.disclosure_code or None,
                                )
                                session.add(fact)
                                county_count += 1

                            elif 20 <= agglvl <= 28:
                                # State level
                                state_id = state_lookup.get(record.area_fips[:2])
                                if state_id:
                                    fact = FactQcewStateAnnual(
                                        state_id=state_id,
                                        industry_id=industry_id,
                                        ownership_id=ownership_id,
                                        time_id=time_id,
                                        establishments=record.annual_avg_estabs,
                                        employment=record.annual_avg_emplvl,
                                        total_wages_usd=record.total_annual_wages,
                                        avg_weekly_wage_usd=record.annual_avg_wkly_wage,
                                        avg_annual_pay_usd=record.avg_annual_pay,
                                        lq_employment=record.lq_annual_avg_emplvl,
                                        lq_annual_pay=record.lq_avg_annual_pay,
                                        disclosure_code=record.disclosure_code or None,
                                        agglvl_code=agglvl,
                                    )
                                    session.add(fact)
                                    state_count += 1

                            elif 30 <= agglvl <= 58:
                                # MSA/Micropolitan/CSA level
                                metro_id = metro_lookup.get(record.area_fips)
                                if metro_id:
                                    area_type = self._determine_metro_type(agglvl)
                                    fact = FactQcewMetroAnnual(
                                        metro_area_id=metro_id,
                                        industry_id=industry_id,
                                        ownership_id=ownership_id,
                                        time_id=time_id,
                                        establishments=record.annual_avg_estabs,
                                        employment=record.annual_avg_emplvl,
                                        total_wages_usd=record.total_annual_wages,
                                        avg_weekly_wage_usd=record.annual_avg_wkly_wage,
                                        avg_annual_pay_usd=record.avg_annual_pay,
                                        lq_employment=record.lq_annual_avg_emplvl,
                                        lq_annual_pay=record.lq_avg_annual_pay,
                                        disclosure_code=record.disclosure_code or None,
                                        agglvl_code=agglvl,
                                        area_type=area_type,
                                    )
                                    session.add(fact)
                                    metro_count += 1

                            # Batch flush
                            total = county_count + state_count + metro_count
                            if total % 10000 == 0:
                                session.flush()
                                if verbose:
                                    print(f"  Loaded {total:,} observations...")

                    except QcewAPIError as e:
                        if e.status_code == 404:
                            logger.debug(f"No data for {area_code} in {year}")
                        else:
                            msg = f"API error for {area_code}/{year}: {e.message}"
                            stats.errors.append(msg)
                            logger.warning(msg)
                            print(f"WARNING: {msg}")  # Console visibility

        session.commit()

        stats.dimensions_loaded["industries"] = len(industry_lookup)
        stats.dimensions_loaded["ownerships"] = len(ownership_lookup)
        stats.facts_loaded["qcew_county"] = county_count
        stats.facts_loaded["qcew_state"] = state_count
        stats.facts_loaded["qcew_metro"] = metro_count

        if verbose:
            msg = (
                f"API loading complete: {county_count:,} county, "
                f"{state_count:,} state, {metro_count:,} metro records"
            )
            logger.info(msg)
            print(msg)

        return stats

    def _determine_metro_type(self, agglvl_code: int) -> str:
        """Determine metro area type from aggregation level code."""
        if 30 <= agglvl_code <= 38:
            return "msa"
        elif 40 <= agglvl_code <= 48:
            return "micropolitan"
        elif 50 <= agglvl_code <= 58:
            return "csa"
        return "unknown"

    def _build_metro_lookup(self, session: Session) -> dict[str, int]:
        """Build metro area FIPS/CBSA to metro_area_id lookup."""
        metros = session.query(DimMetroArea).all()
        lookup = {}
        for m in metros:
            if m.cbsa_code:
                lookup[m.cbsa_code] = m.metro_area_id
            if m.geo_id:
                lookup[m.geo_id] = m.metro_area_id
        return lookup

    def _load_from_files(
        self,
        session: Session,
        years: list[int],
        verbose: bool,
        data_path: object,
    ) -> LoadStats:
        """Load QCEW data from local CSV files for historical years.

        Processes all geographic levels (same as API):
        - County (agglvl_code 70-78) → FactQcewAnnual
        - State (agglvl_code 20-28) → FactQcewStateAnnual
        - Metro/Micro/CSA (agglvl_code 30-58) → FactQcewMetroAnnual
        """
        stats = LoadStats(source="qcew_files")
        csv_dir = Path(data_path) if isinstance(data_path, (str, Path)) else Path("data/qcew")

        if not csv_dir.exists():
            msg = f"QCEW data directory not found: {csv_dir}"
            stats.errors.append(msg)
            logger.error(msg)
            print(f"ERROR: {msg}")  # Console visibility
            return stats

        # Load data source dimension
        self._load_data_source(session, verbose)

        # Build lookup caches
        state_lookup = self._build_state_lookup(session)
        county_lookup = self._build_county_lookup(session)
        metro_lookup = self._build_metro_lookup(session)
        industry_lookup: dict[str, int] = {}
        ownership_lookup: dict[str, int] = {}
        time_cache: dict[int, int] = {}

        # Counters per geographic level
        county_count = 0
        state_count = 0
        metro_count = 0

        # Discover CSV files
        csv_files = list(csv_dir.glob("*.csv"))
        stats.files_processed = len(csv_files)

        if not csv_files:
            msg = f"No CSV files found in {csv_dir}"
            stats.errors.append(msg)
            logger.error(msg)
            print(f"ERROR: {msg}")
            return stats

        if verbose:
            msg = f"Files: Processing {len(csv_files)} CSV files for years {years}"
            logger.info(msg)
            print(msg)

        years_to_load = set(years)
        file_iter = tqdm(csv_files, desc="CSV files", disable=not verbose)

        for csv_file in file_iter:
            if verbose:
                logger.debug(f"Processing {csv_file.name}...")

            for record in parse_qcew_csv(csv_file):
                # Filter by year
                if record.year not in years_to_load:
                    continue

                # Get aggregation level from record (if available)
                agglvl = getattr(record, "agglvl_code", 78)  # Default to county

                # Resolve shared dimensions
                industry_id = self._get_or_create_industry(
                    session,
                    record.industry_code,
                    record.industry_title,
                    industry_lookup,
                )
                ownership_id = self._get_or_create_ownership(
                    session,
                    record.own_code,
                    record.own_title,
                    ownership_lookup,
                )
                time_id = self._get_or_create_time(session, record.year, time_cache)

                # Route to appropriate fact table by aggregation level
                if 70 <= agglvl <= 78:
                    # County level
                    county_id = county_lookup.get(record.area_fips)
                    if county_id is None:
                        state_fips = extract_state_fips(record.area_fips)
                        if state_fips and state_fips in state_lookup:
                            county_id = self._get_or_create_county(
                                session,
                                record.area_fips,
                                record.area_title,
                                state_lookup[state_fips],
                                county_lookup,
                            )
                        else:
                            continue  # Skip non-county areas

                    fact = FactQcewAnnual(
                        county_id=county_id,
                        industry_id=industry_id,
                        ownership_id=ownership_id,
                        time_id=time_id,
                        establishments=record.establishments,
                        employment=record.employment,
                        total_wages_usd=record.total_wages,
                        avg_weekly_wage_usd=record.avg_weekly_wage,
                        avg_annual_pay_usd=record.avg_annual_pay,
                        lq_employment=record.lq_employment,
                        lq_annual_pay=record.lq_avg_annual_pay,
                        disclosure_code=record.disclosure_code or None,
                    )
                    session.add(fact)
                    county_count += 1

                elif 20 <= agglvl <= 28:
                    # State level
                    state_fips = record.area_fips[:2]
                    state_id = state_lookup.get(state_fips)
                    if state_id:
                        fact = FactQcewStateAnnual(
                            state_id=state_id,
                            industry_id=industry_id,
                            ownership_id=ownership_id,
                            time_id=time_id,
                            establishments=record.establishments,
                            employment=record.employment,
                            total_wages_usd=record.total_wages,
                            avg_weekly_wage_usd=record.avg_weekly_wage,
                            avg_annual_pay_usd=record.avg_annual_pay,
                            lq_employment=record.lq_employment,
                            lq_annual_pay=record.lq_avg_annual_pay,
                            disclosure_code=record.disclosure_code or None,
                            agglvl_code=agglvl,
                        )
                        session.add(fact)
                        state_count += 1

                elif 30 <= agglvl <= 58:
                    # MSA/Micropolitan/CSA level
                    metro_id = metro_lookup.get(record.area_fips)
                    if metro_id:
                        area_type = self._determine_metro_type(agglvl)
                        fact = FactQcewMetroAnnual(
                            metro_area_id=metro_id,
                            industry_id=industry_id,
                            ownership_id=ownership_id,
                            time_id=time_id,
                            establishments=record.establishments,
                            employment=record.employment,
                            total_wages_usd=record.total_wages,
                            avg_weekly_wage_usd=record.avg_weekly_wage,
                            avg_annual_pay_usd=record.avg_annual_pay,
                            lq_employment=record.lq_employment,
                            lq_annual_pay=record.lq_avg_annual_pay,
                            disclosure_code=record.disclosure_code or None,
                            agglvl_code=agglvl,
                            area_type=area_type,
                        )
                        session.add(fact)
                        metro_count += 1

                # Batch flush
                total = county_count + state_count + metro_count
                if total % 10000 == 0:
                    session.flush()
                    if verbose:
                        print(f"  Loaded {total:,} observations...")

        session.commit()

        stats.dimensions_loaded["industries"] = len(industry_lookup)
        stats.dimensions_loaded["ownerships"] = len(ownership_lookup)
        stats.facts_loaded["qcew_county"] = county_count
        stats.facts_loaded["qcew_state"] = state_count
        stats.facts_loaded["qcew_metro"] = metro_count

        if verbose:
            msg = (
                f"File loading complete: {county_count:,} county, "
                f"{state_count:,} state, {metro_count:,} metro records"
            )
            logger.info(msg)
            print(msg)

        return stats

    # Existing helper methods preserved below (from current loader_3nf.py)
    # _clear_qcew_tables, _load_data_source, _build_state_lookup, _build_county_lookup,
    # _get_or_create_county, _get_or_create_industry, _get_or_create_ownership, _get_or_create_time
```

#### 2. Update: `src/babylon/data/qcew/__init__.py`

Add API client exports:

```python
"""BLS QCEW data loading infrastructure.

Provides loading of Quarterly Census of Employment and Wages data
from the BLS Open Data API or local CSV files.
"""

from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAPIError,
    QcewAreaRecord,
    get_state_area_code,
)
from babylon.data.qcew.loader_3nf import QcewLoader
from babylon.data.qcew.parser import (
    QcewRecord,
    parse_qcew_csv,
    parse_all_area_files,
)

__all__ = [
    # API Client
    "QcewAPIClient",
    "QcewAPIError",
    "QcewAreaRecord",
    "get_state_area_code",
    # Loader
    "QcewLoader",
    # Parser (legacy/offline)
    "QcewRecord",
    "parse_qcew_csv",
    "parse_all_area_files",
]
```

### Success Criteria

#### Automated Verification:
- [ ] Type checking passes: `poetry run mypy src/babylon/data/qcew/`
- [ ] Linting passes: `poetry run ruff check src/babylon/data/qcew/`
- [ ] Unit tests pass: `poetry run pytest tests/unit/data/test_qcew*.py -v`
- [ ] Integration tests pass: `poetry run pytest tests/integration/data/test_loaders/ -v -k qcew`

#### Manual Verification:
- [ ] Run `mise run data:ingest --loaders qcew` and verify data loads
- [ ] Query database to confirm expected record counts
- [ ] Verify no regression in existing QCEW data quality

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 4.

---

## Phase 4: Add Integration Tests

### Overview

Create integration tests that verify end-to-end API loading with real BLS API calls (network-dependent).

### Changes Required

#### 1. New File: `tests/integration/data/test_qcew_api_integration.py`

```python
"""Integration tests for QCEW API loader.

These tests make real API calls to BLS servers and are marked
as slow/network tests. They verify end-to-end data loading.
"""

import pytest
from sqlalchemy import func

from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize.database import get_normalized_session, init_normalized_db
from babylon.data.normalize.schema import FactQcewAnnual, DimIndustry
from babylon.data.qcew import QcewLoader, QcewAPIClient


@pytest.mark.integration
@pytest.mark.network
class TestQcewAPIIntegration:
    """Integration tests requiring network access."""

    @pytest.fixture(autouse=True)
    def setup_db(self) -> None:
        """Ensure normalized database is initialized."""
        init_normalized_db()

    def test_api_client_fetches_real_data(self) -> None:
        """API client can fetch real data from BLS."""
        with QcewAPIClient() as client:
            # Fetch 2023 data for Alabama state-level
            records = list(client.get_area_annual_data(2023, "01000"))

        assert len(records) > 0
        # Should have multiple industries
        industries = {r.industry_code for r in records}
        assert len(industries) > 10

    def test_loader_populates_database(self) -> None:
        """Loader populates 3NF tables from API."""
        config = LoaderConfig(
            qcew_years=[2023],  # Single year for speed
        )
        loader = QcewLoader(config)

        with get_normalized_session() as session:
            stats = loader.load(session, reset=True, verbose=False)

        assert stats.facts_loaded.get("qcew_annual", 0) > 0
        assert stats.api_calls > 0
        assert not stats.has_errors

    def test_idempotency_on_reload(self) -> None:
        """Reloading same data produces same counts."""
        config = LoaderConfig(qcew_years=[2023])
        loader = QcewLoader(config)

        with get_normalized_session() as session:
            stats1 = loader.load(session, reset=True, verbose=False)

        with get_normalized_session() as session:
            stats2 = loader.load(session, reset=True, verbose=False)

        assert stats1.facts_loaded == stats2.facts_loaded
```

### Success Criteria

#### Automated Verification:
- [ ] Integration tests pass: `poetry run pytest tests/integration/data/test_qcew_api_integration.py -v -m "integration and network"`
- [ ] No network errors or timeouts

#### Manual Verification:
- [ ] Review database contents after integration test run

---

## Phase 5: Update CLI and Configuration

### Overview

Update CLI to support hybrid loading with `--force-api` and `--force-files` flags, expand default year range to 2013-2025 for maximum historical coverage.

### Changes Required

#### 1. Update: `src/babylon/data/cli.py`

Add hybrid loading flags to QCEW command:

```python
@app.command()
def qcew(
    years: Annotated[
        str | None,
        typer.Option("--years", help="Years to load (e.g., 2020,2021,2022 or 2013-2025)"),
    ] = None,
    force_api: Annotated[
        bool,
        typer.Option("--force-api", help="Force API for all years (may fail for old years)"),
    ] = False,
    force_files: Annotated[
        bool,
        typer.Option("--force-files", help="Force file-based loading for all years"),
    ] = False,
    data_path: Annotated[
        str | None,
        typer.Option("--data-path", help="Path to CSV files (only with --force-files)"),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load BLS QCEW employment data into 3NF database.

    Uses hybrid loading by default:
    - API for years 2021+ (rolling 5-year BLS API window)
    - Files for years 2013-2020 (downloaded CSVs from BLS)

    Supports three geographic levels:
    - County (agglvl_code 70-78)
    - State (agglvl_code 20-28)
    - MSA/Micropolitan/CSA (agglvl_code 30-58)
    """
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db
    from babylon.data.qcew import QcewLoader

    if force_api and force_files:
        typer.echo("ERROR: Cannot use both --force-api and --force-files")
        raise typer.Exit(1)

    config = LoaderConfig(
        qcew_years=parse_years(years) or list(range(2013, 2026)),  # 2013-2025 default
        verbose=not quiet,
    )

    # Describe loading mode
    if force_api:
        mode = "API-only (all years)"
    elif force_files:
        mode = f"files-only ({data_path or 'data/qcew'})"
    else:
        mode = "hybrid (API for 2021+, files for 2013-2020)"

    if not quiet:
        typer.echo(f"Loading QCEW data for years {min(config.qcew_years)}-{max(config.qcew_years)} via {mode}")

    init_normalized_db()
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(
            session,
            reset=reset,
            verbose=not quiet,
            force_api=force_api,
            force_files=force_files,
            data_path=data_path,
        )

    print_stats(stats)
    if stats.has_errors:
        typer.echo(f"WARNING: {len(stats.errors)} errors occurred during loading")
        for err in stats.errors[:5]:  # Show first 5 errors
            typer.echo(f"  - {err}")
        if len(stats.errors) > 5:
            typer.echo(f"  ... and {len(stats.errors) - 5} more errors")
        raise typer.Exit(1)
```

#### 2. Update: `src/babylon/data/loader_base.py`

Update LoaderConfig with expanded default year range:

```python
@dataclass
class LoaderConfig:
    # ... existing fields ...

    # Temporal - QCEW (annual data) - expanded for maximum coverage
    # Default: 2013-2025 (13 years, pre-2013 MSA codes are incompatible)
    qcew_years: list[int] = field(default_factory=lambda: list(range(2013, 2026)))

    # QCEW API settings
    qcew_api_cutoff_year: int = 2021  # API for years >= this, files for earlier
    qcew_request_delay: float = 0.5  # Seconds between API requests
```

### Success Criteria

#### Automated Verification:
- [ ] CLI help shows new options: `python -m babylon.data.cli qcew --help`
- [ ] Type checking passes: `poetry run mypy src/babylon/data/cli.py`
- [ ] Linting passes: `poetry run ruff check src/babylon/data/cli.py`

#### Manual Verification:
- [ ] `mise run data:ingest --loaders qcew` works with API
- [ ] `mise run data:ingest --loaders qcew -- --files --data-path data/qcew` works with files

---

## Phase 6: Documentation and Cleanup

### Overview

Update documentation to reflect API-first approach and remove references to required CSV downloads.

### Changes Required

1. Update `data/sqlite/README.md` to document API-based QCEW loading
2. Add RST documentation in `docs/reference/qcew-data.rst`
3. Update `ai-docs/state.yaml` to reflect completed migration
4. Remove `data/qcew/` from expected paths (it's now optional)

### Success Criteria

#### Automated Verification:
- [ ] Documentation builds: `mise run docs`
- [ ] No Sphinx warnings

#### Manual Verification:
- [ ] README accurately describes API-first approach
- [ ] Users can follow documentation to load QCEW data without CSV files

---

## Testing Strategy

### Unit Tests

- `tests/unit/data/test_qcew_api_client.py`: API client with mocked responses
- Test rate limiting behavior
- Test error handling (404, 429, network errors)
- Test CSV parsing

### Integration Tests

- `tests/integration/data/test_qcew_api_integration.py`: Real API calls
- Mark as `@pytest.mark.network` for optional execution
- Test end-to-end loading for single year
- Test idempotency

### Manual Testing Steps

1. Delete `data/qcew/` directory
2. Run `mise run data:ingest --loaders qcew`
3. Verify no file-not-found errors
4. Query `SELECT COUNT(*) FROM fact_qcew_annual`
5. Verify counts match expectations (~2-3M records for 5 years)

---

## Performance Considerations

### API Rate Limiting

- BLS has no published rate limit, but be conservative
- Default 0.5s delay between requests
- With ~3,200 areas × 5 years = ~16,000 requests
- Estimated time: ~2.5 hours for full load (acceptable for batch ETL)

### Memory Efficiency

- Stream records from API (don't buffer entire response)
- Batch commits every 10,000 records
- Same memory pattern as file-based loader

### Caching

- Consider adding response caching for development
- Not needed for production (data changes quarterly)

---

## Migration Notes

### Backwards Compatibility

- File-based loading preserved via `--files` flag
- Existing workflows continue to work
- API mode is default but not required

### Data Quality

- API returns same schema as CSV downloads
- No data transformation differences expected
- LQ and OTY fields included in API responses

---

## References

- BLS QCEW Open Data API: https://www.bls.gov/cew/additional-resources/open-data/
- CSV Data Slices documentation: https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm
- Sample code: https://www.bls.gov/cew/additional-resources/open-data/sample-code.htm
- FRED loader pattern: `src/babylon/data/fred/api_client.py`
- Current QCEW loader: `src/babylon/data/qcew/loader_3nf.py`
- claude-mem observations: #15876, #15866, #15861
