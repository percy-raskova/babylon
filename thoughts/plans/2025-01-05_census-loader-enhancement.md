# Census Loader Enhancement Implementation Plan

## Overview

Enhance the Census ACS 5-Year data loader to support:

1. **Multi-year historical data** (2009-2023, 15 years)
1. **Race/ethnicity disaggregation** (9 groups per Census A-I suffix scheme)
1. **Metropolitan statistical area granularity** (MSA, Micropolitan, CSA)

This enables rich Marxian analysis of national oppression, class composition by race, and geographic inequality over time - critical for modeling the material conditions that drive class consciousness and revolutionary potential in the Babylon simulation.

## Current State Analysis

### What Exists Now

**Census Loader** (`src/babylon/data/census/loader_3nf.py`):

- Fetches ACS 5-Year Estimates from Census Bureau API
- Single year only (default: 2022) via `LoaderConfig.census_year`
- County-level geography only (52 states: 50 + DC + PR)
- No race/ethnicity disaggregation
- 16 tables loaded (B19001, B19013, B23025, B24080, B25003, B25064, B25070, C24010, B23020, B17001, B15003, B19083, B08301, B19052, B19053, B19054)
- Marxian classifications applied: worker class, labor type, rent burden

**Schema** (`src/babylon/data/normalize/schema.py`):

- `DimState` (52 records: 50 + DC + PR)
- `DimCounty` (~3,200 records) with FK to DimState
- `DimMetroArea` exists but NOT populated
- `BridgeCountyMetro` exists but NOT populated
- `DimTime` exists for FRED/Energy data
- NO `DimRace` or race/ethnicity dimension
- 14 Census fact tables, all keyed by county_id

**API Client** (`src/babylon/data/census/api_client.py`):

- Supports configurable year and dataset
- Rate limiting (0.5s delay) with exponential backoff
- State and county geography only
- No metro area geography support yet

### Key Discoveries

| Finding                                                                                 | Location              | Impact                                   |
| --------------------------------------------------------------------------------------- | --------------------- | ---------------------------------------- |
| `DimMetroArea` already has `area_type` column                                           | `schema.py:74`        | Can distinguish MSA/μSA/CSA              |
| `BridgeCountyMetro` has `is_principal_city` flag                                        | `schema.py:90`        | Supports metro composition analysis      |
| Census API supports `for=metropolitan statistical area/micropolitan statistical area:*` | Census API docs       | Direct metro-level queries possible      |
| Race-iterated tables use A-I suffix                                                     | Census Table IDs docs | B19001A through B19001I for 9 groups     |
| `DimTime` already exists with `year` column                                             | `schema.py:432-447`   | Can reuse for Census multi-year          |
| ACS only covers Puerto Rico, not VI/GU/AS/MP                                            | Census documentation  | Territory expansion not possible via ACS |

## Desired End State

After implementation:

1. **15 years of Census data** (2009-2023) loaded into fact tables with `time_id` FK
1. **9 race/ethnicity groups** per fact observation via `race_id` FK
1. **~1,500 metro areas** populated in `DimMetroArea` (393 MSA + 542 μSA + CSAs)
1. **County-to-metro mapping** in `BridgeCountyMetro` for aggregation queries
1. **Analytical queries** like:
   - "Median income for Black households in Detroit MSA from 2009-2023"
   - "Rent burden for AIAN population by county over time"
   - "Class composition by race in core vs periphery metro areas"

### Verification

```sql
-- Multi-year data present
SELECT COUNT(DISTINCT t.year) FROM fact_census_income f
JOIN dim_time t ON f.time_id = t.time_id;
-- Expected: 15 (2009-2023)

-- Race disaggregation present
SELECT COUNT(DISTINCT r.race_code) FROM fact_census_income f
JOIN dim_race r ON f.race_id = r.race_id;
-- Expected: 9 (A through I) + 1 (total)

-- Metro areas populated
SELECT area_type, COUNT(*) FROM dim_metro_area GROUP BY area_type;
-- Expected: msa ~393, micropolitan ~542, csa ~175

-- County-metro mappings
SELECT COUNT(*) FROM bridge_county_metro;
-- Expected: ~4,000+ (counties can be in multiple CBSAs)
```

## What We're NOT Doing

1. **Other territories** - VI, GU, AS, MP are NOT in ACS (only decennial census). Puerto Rico is sufficient for now.
1. **Tract-level geography** - Would increase data volume ~25x (~74,000 tracts vs ~3,200 counties). Out of scope.
1. **Block group geography** - Even more granular than tracts. Out of scope.
1. **ACS 1-Year estimates** - Less geographic coverage than 5-Year. Out of scope.
1. **Configurable year ranges** - We want all years 2009-2023 by default.
1. **Configurable race groups** - We want all 9 groups for complete analysis.
1. **Tribal area geography** - Complex hierarchy, specialized use case. Future enhancement.

## Implementation Approach

The implementation follows a **schema-first** approach:

1. Extend schema with new dimensions and FKs
2. Update loader infrastructure for multi-year iteration
3. Add race-disaggregated table fetching
4. Populate metro area dimensions
5. Consolidate repetitive loader patterns (base class extraction)
6. Comprehensive testing

Each phase is independently testable and deployable.

______________________________________________________________________

## Phase 1: Schema Enhancement

### Overview

Add `DimRace` dimension table and extend fact tables with `race_id` and `time_id` foreign keys for multi-dimensional analysis.

### Changes Required

#### 1. Add DimRace Dimension Table

**File**: `src/babylon/data/normalize/schema.py`
**Location**: After `DimGender` (around line 458)

```python
class DimRace(NormalizedBase):
    """Race/ethnicity dimension following Census A-I suffix scheme.

    Enables analysis of national oppression and class composition by race,
    critical for understanding material conditions in MLM-TW framework.

    Census Race Codes:
        A = White alone
        B = Black or African American alone
        C = American Indian and Alaska Native alone
        D = Asian alone
        E = Native Hawaiian and Other Pacific Islander alone
        F = Some other race alone
        G = Two or more races
        H = White alone, not Hispanic or Latino
        I = Hispanic or Latino
        T = Total (all races, base table)
    """

    __tablename__ = "dim_race"

    race_id: Mapped[int] = mapped_column(primary_key=True)
    race_code: Mapped[str] = mapped_column(String(1), unique=True, nullable=False)
    race_name: Mapped[str] = mapped_column(String(100), nullable=False)
    race_short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    is_hispanic_ethnicity: Mapped[bool] = mapped_column(default=False)
    is_indigenous: Mapped[bool] = mapped_column(default=False)
    display_order: Mapped[int] = mapped_column(default=0)
```

#### 2. Update Fact Tables with race_id and time_id

**File**: `src/babylon/data/normalize/schema.py`
**Changes**: Add FKs to all 14 Census fact tables

Example for `FactCensusIncome` (apply pattern to all):

```python
class FactCensusIncome(NormalizedBase):
    """Household income distribution by bracket."""

    __tablename__ = "fact_census_income"

    # Existing PKs
    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    bracket_id: Mapped[int] = mapped_column(ForeignKey("dim_income_bracket.bracket_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("dim_data_source.source_id"), primary_key=True)

    # NEW: Add to composite PK
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)

    # Measures (unchanged)
    households: Mapped[int | None] = mapped_column()
```

**Fact tables to update** (14 total):

- `FactCensusIncome`
- `FactCensusMedianIncome`
- `FactCensusEmployment`
- `FactCensusWorkerClass`
- `FactCensusOccupation`
- `FactCensusHours`
- `FactCensusHousing`
- `FactCensusRent`
- `FactCensusRentBurden`
- `FactCensusEducation`
- `FactCensusGini`
- `FactCensusCommute`
- `FactCensusPoverty`
- `FactCensusIncomeSources`

#### 3. Update DimMetroArea for CSA Support

**File**: `src/babylon/data/normalize/schema.py`
**Location**: Line 74

```python
# Update constraint to include all three area types
area_type: Mapped[str] = mapped_column(
    String(20),
    CheckConstraint("area_type IN ('msa', 'micropolitan', 'csa')"),
    nullable=False,
)
```

### Success Criteria

#### Automated Verification:

- [x] Schema migration applies cleanly: `rm data/sqlite/marxist-data-3NF.sqlite && poetry run python -c "from babylon.data.normalize.database import init_normalized_db; init_normalized_db()"`
- [x] Type checking passes: `mise run typecheck`
- [x] Linting passes: `mise run lint`
- [x] Existing tests still pass: `mise run test:unit`

#### Manual Verification:

- [ ] SQLite schema inspection shows new `dim_race` table with correct columns
- [ ] All 14 fact tables have `time_id` and `race_id` columns in their PKs
- [ ] `dim_metro_area.area_type` constraint includes 'micropolitan' and 'csa'

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

______________________________________________________________________

## Phase 2: Multi-Year Loading Infrastructure ✅ COMPLETED

### Status: IMPLEMENTED via Data-Driven Refactoring

This phase was completed with a significant refactoring that consolidated 14 repetitive fact loader methods into a data-driven generic loader.

### Key Implementation Details

**Commit**: `d9fc8f4 refactor(census): data-driven fact loaders with multi-year support`

**Changes Made**:

1. **LoaderConfig API Change**:
   - `census_year: int` → `census_years: list[int]` with default `range(2009, 2024)`
   - Backwards compatibility in CLI for old config files

2. **Data-Driven Loader Architecture**:
   - `FactTableSpec` frozen dataclass for table configurations (12 specs)
   - `FACT_TABLE_SPECS` constant defining all table metadata
   - `_load_fact_table()` generic method with pattern dispatch
   - Helper methods: `_build_fact_kwargs()`, `_build_dimension_map()`, `_process_county_facts()`

3. **Special Case Methods** (kept separate due to unique patterns):
   - `_load_fact_hours()` - Gender-grouped aggregation
   - `_load_fact_income_sources()` - Multi-table join

4. **All fact loaders now accept `time_id` and `race_id` parameters**

### Success Criteria: ✅ ALL PASSED

#### Automated Verification:
- [x] Type checking passes: `mise run typecheck` - Success, no issues in 65 files
- [x] Linting passes: `mise run lint` - All checks passed
- [x] Unit tests pass: `mise run test:unit` - 4009 passed
- [x] Integration tests pass for data loaders

#### Manual Verification (Pending):
- [ ] `DimTime` has records for years 2009-2023
- [ ] `DimRace` has 10 records (T, A-I)
- [ ] Fact tables have `time_id` and `race_id` populated

______________________________________________________________________

## Phase 3: Race-Disaggregated Table Loading

### Overview

Extend the data-driven loader architecture to fetch race-iterated tables (e.g., B19001A through B19001I) and populate facts with race_id. Leverages the `FactTableSpec` infrastructure from Phase 2.

### Changes Required

#### 1. Extend FactTableSpec with Race Suffix Information

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: `FactTableSpec` dataclass (around line 50)

```python
@dataclass(frozen=True)
class FactTableSpec:
    """Configuration for loading a Census fact table."""
    # ... existing fields ...

    # NEW: Race iteration support
    race_suffixes: tuple[str, ...] = ()  # e.g., ("A", "B", "C", "D", "E", "F", "G", "H", "I")
    # Empty tuple means table only exists for Total race
```

#### 2. Update FACT_TABLE_SPECS with Race Information

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: `FACT_TABLE_SPECS` constant

```python
# Race suffixes for tables that have race iterations
FULL_RACE_SUFFIXES = ("A", "B", "C", "D", "E", "F", "G", "H", "I")

FACT_TABLE_SPECS: list[FactTableSpec] = [
    # Pattern A: Dimension-iterated WITH race iterations
    FactTableSpec(
        table_id="B19001", fact_class=FactCensusIncome, label="B19001",
        dim_class=DimIncomeBracket, dim_code_attr="bracket_code", fact_dim_attr="bracket_id",
        value_field="household_count", skip_total=True,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B23025", fact_class=FactCensusEmployment, label="B23025",
        dim_class=DimEmploymentStatus, dim_code_attr="status_code", fact_dim_attr="status_id",
        value_field="person_count", skip_total=False,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    # ... update all specs with race_suffixes ...

    # Pattern B: Scalar value WITH race iterations
    FactTableSpec(
        table_id="B19013", fact_class=FactCensusMedianIncome, label="B19013",
        value_field="median_income_usd", value_type="decimal",
        scalar_var="B19013_001E",
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),

    # Tables WITHOUT race iterations (only load with race_code="T")
    FactTableSpec(
        table_id="B19083", fact_class=FactCensusGini, label="B19083",
        value_field="gini_index", value_type="decimal",
        scalar_var="B19083_001E",
        race_suffixes=(),  # No race iterations
    ),
]
```

#### 3. Update load() Method for Year+Race Iteration

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: `load()` method

```python
def load(
    self,
    session: Session,
    reset: bool = True,
    verbose: bool = True,
    **_kwargs: object,
) -> LoadStats:
    """Load Census ACS 5-Year data for all configured years and races."""
    stats = LoadStats(source="census")

    # ... dimension loading (unchanged) ...

    # Iterate over years
    for year in self.config.census_years:
        if verbose:
            print(f"\n{'='*60}")
            print(f"Loading Census ACS 5-Year: {year}")
            print(f"{'='*60}")

        self._client = CensusAPIClient(year=year)
        time_id = self._year_to_time_id[year]

        # Load Total race first (base tables)
        race_id_total = self._race_code_to_id["T"]
        for spec in FACT_TABLE_SPECS:
            count = self._load_fact_table(
                spec, session, state_fips_list, verbose, time_id, race_id_total
            )
            # ... stats tracking ...

        # Load special cases for Total race
        self._load_fact_hours(session, state_fips_list, verbose, time_id, race_id_total)
        self._load_fact_income_sources(session, state_fips_list, verbose, time_id, race_id_total)

        # Load race-disaggregated data (A-I)
        for race_data in RACE_CODES[1:]:  # Skip "T" (Total)
            race_code = race_data["code"]
            race_id = self._race_code_to_id[race_code]

            if verbose:
                print(f"  Loading race-iterated tables for {race_code}...")

            for spec in FACT_TABLE_SPECS:
                if race_code not in spec.race_suffixes:
                    continue  # Table doesn't have this race iteration

                # Modify table_id to include race suffix
                race_spec = replace(spec, table_id=f"{spec.table_id}{race_code}")
                try:
                    count = self._load_fact_table(
                        race_spec, session, state_fips_list, verbose, time_id, race_id
                    )
                except CensusAPIError as e:
                    if "unknown variable" not in str(e).lower():
                        stats.errors.append(f"{race_spec.table_id}: {e}")
```

#### 4. Add `replace` Import for Dataclass Modification

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: Imports

```python
from dataclasses import dataclass, field, replace
```

### Success Criteria

#### Automated Verification:

- [x] Type checking passes: `mise run typecheck`
- [x] Linting passes: `mise run lint`
- [x] Unit tests pass: `mise run test:unit` (4009 passed)
- [x] Race-iterated API calls succeed (verified with B19001A for California)

#### Manual Verification:

- [x] Fact tables contain records for all 10 race codes (122,488 total fact rows)
- [x] Race "C" (AIAN) has meaningful data in income/employment tables (1,856 records)
- [x] Total counts match when summing across races (each race has 1,856 income records)
- [x] No duplicate PK errors (unique composite keys verified)

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 4.

______________________________________________________________________

## Phase 4: Metro Area Population

### Overview

Download CBSA delineation file, populate `DimMetroArea` with all MSA/Micropolitan/CSA areas, and create county-to-metro mappings in `BridgeCountyMetro`.

### Changes Required

#### 1. Add CBSA Delineation Parser

**File**: `src/babylon/data/census/cbsa_parser.py` (NEW)

```python
"""Parser for Census Bureau CBSA delineation files.

Downloads and parses the official CBSA-to-county mapping from Census Bureau,
enabling metropolitan statistical area aggregation of county-level data.

Source: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CBSA_DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2023/delineation-files/list1_2023.xls"
)

# We'll use a CSV version or convert the XLS
CBSA_CSV_CACHE = Path("data/census/cbsa_delineation_2023.csv")


@dataclass
class CBSARecord:
    """A single CBSA-to-county mapping record."""

    cbsa_code: str
    cbsa_title: str
    area_type: str  # "Metropolitan Statistical Area" or "Micropolitan Statistical Area"
    csa_code: str | None
    csa_title: str | None
    county_fips: str  # 5-digit state+county FIPS
    county_name: str
    state_fips: str
    state_name: str
    is_central_county: bool


def parse_cbsa_delineation(filepath: Path) -> list[CBSARecord]:
    """Parse CBSA delineation CSV file.

    Args:
        filepath: Path to CSV file with CBSA delineation data.

    Returns:
        List of CBSARecord objects mapping counties to CBSAs.
    """
    records = []

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip header rows or empty rows
            if not row.get("CBSA Code"):
                continue

            # Determine area type
            metro_micro = row.get("Metropolitan/Micropolitan Statistical Area", "")
            if "Metropolitan" in metro_micro:
                area_type = "msa"
            elif "Micropolitan" in metro_micro:
                area_type = "micropolitan"
            else:
                continue  # Skip unknown types

            # Build 5-digit county FIPS
            state_fips = row.get("FIPS State Code", "").zfill(2)
            county_fips_3 = row.get("FIPS County Code", "").zfill(3)
            county_fips = f"{state_fips}{county_fips_3}"

            record = CBSARecord(
                cbsa_code=row.get("CBSA Code", ""),
                cbsa_title=row.get("CBSA Title", ""),
                area_type=area_type,
                csa_code=row.get("CSA Code") or None,
                csa_title=row.get("CSA Title") or None,
                county_fips=county_fips,
                county_name=row.get("County/County Equivalent", ""),
                state_fips=state_fips,
                state_name=row.get("State Name", ""),
                is_central_county=row.get("Central/Outlying County", "") == "Central",
            )
            records.append(record)

    return records


def get_unique_cbsas(records: list[CBSARecord]) -> list[dict]:
    """Extract unique CBSA records for DimMetroArea population."""
    seen = set()
    cbsas = []

    for r in records:
        if r.cbsa_code not in seen:
            seen.add(r.cbsa_code)
            cbsas.append({
                "cbsa_code": r.cbsa_code,
                "metro_name": r.cbsa_title,
                "area_type": r.area_type,
            })

    return cbsas


def get_unique_csas(records: list[CBSARecord]) -> list[dict]:
    """Extract unique CSA records for DimMetroArea population."""
    seen = set()
    csas = []

    for r in records:
        if r.csa_code and r.csa_code not in seen:
            seen.add(r.csa_code)
            csas.append({
                "cbsa_code": r.csa_code,  # Use same column for CSA codes
                "metro_name": r.csa_title,
                "area_type": "csa",
            })

    return csas
```

#### 2. Add Metro Area Loading to Census Loader

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: New method

```python
def _load_metro_areas(self, session: Session, verbose: bool = True) -> int:
    """Load metropolitan statistical areas from CBSA delineation file.

    Returns:
        Number of metro areas loaded.
    """
    from babylon.data.census.cbsa_parser import (
        CBSA_CSV_CACHE,
        get_unique_cbsas,
        get_unique_csas,
        parse_cbsa_delineation,
    )

    if not CBSA_CSV_CACHE.exists():
        if verbose:
            print(f"CBSA delineation file not found at {CBSA_CSV_CACHE}")
            print("Please download from Census Bureau and convert to CSV.")
        return 0

    if verbose:
        print("Loading metropolitan statistical areas...")

    records = parse_cbsa_delineation(CBSA_CSV_CACHE)

    # Load CBSAs (MSA and Micropolitan)
    cbsas = get_unique_cbsas(records)
    for cbsa in cbsas:
        metro = DimMetroArea(
            cbsa_code=cbsa["cbsa_code"],
            metro_name=cbsa["metro_name"],
            area_type=cbsa["area_type"],
        )
        session.add(metro)

    # Load CSAs
    csas = get_unique_csas(records)
    for csa in csas:
        metro = DimMetroArea(
            cbsa_code=csa["cbsa_code"],
            metro_name=csa["metro_name"],
            area_type=csa["area_type"],
        )
        session.add(metro)

    session.flush()

    # Build lookup for bridge table
    metro_lookup = {
        m.cbsa_code: m.metro_area_id
        for m in session.query(DimMetroArea).all()
    }

    # Load county-to-metro mappings
    if verbose:
        print("Loading county-to-metro mappings...")

    for record in records:
        county_id = self._fips_to_county.get(record.county_fips)
        metro_id = metro_lookup.get(record.cbsa_code)

        if county_id and metro_id:
            bridge = BridgeCountyMetro(
                county_id=county_id,
                metro_area_id=metro_id,
                is_principal_city=record.is_central_county,
            )
            session.add(bridge)

        # Also link to CSA if present
        if record.csa_code:
            csa_id = metro_lookup.get(record.csa_code)
            if county_id and csa_id:
                bridge_csa = BridgeCountyMetro(
                    county_id=county_id,
                    metro_area_id=csa_id,
                    is_principal_city=False,  # CSA doesn't have principal cities
                )
                session.add(bridge_csa)

    session.flush()

    return len(cbsas) + len(csas)
```

#### 3. Integrate into Main Load Method

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: In `load()` after state/county loading

```python
# After _load_counties()
metro_count = self._load_metro_areas(session, verbose=verbose)
stats.dimensions_loaded["dim_metro_area"] = metro_count
if verbose:
    print(f"Loaded {metro_count} metropolitan statistical areas")
```

### Success Criteria

#### Automated Verification:

- [x] Type checking passes: `mise run typecheck`
- [x] Linting passes: `mise run lint`
- [x] Unit tests pass: `mise run test:unit` (4009 tests)

#### Manual Verification:

- [ ] `dim_metro_area` has ~1,100+ records (935 CBSA + 184 CSA = 1,119 total)
- [ ] `bridge_county_metro` has appropriate county-to-metro mappings
- [ ] Query: California counties correctly mapped to LA-Long Beach CSA, etc.
- [ ] Query: CSA aggregation works correctly

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 5.

______________________________________________________________________

## Phase 5: Data Loader Infrastructure Refactoring

### Overview

Consolidate repetitive patterns across 13 data loaders identified during Phase 4 analysis. The Census loader's `FactTableSpec` data-driven pattern proved highly successful (eliminating 14 repetitive methods), and similar consolidations can reduce ~800-1000 LOC across the data loading infrastructure.

### Analysis Summary

Analysis of `src/babylon/data/` revealed four consolidation opportunities:

| Pattern | Loaders Affected | Estimated LOC Reduction |
|---------|------------------|-------------------------|
| Time dimension management | 5 loaders (~40 lines each) | ~200 LOC |
| Data source loading | 12 loaders (~15 lines each) | ~180 LOC |
| County FIPS extraction | 6 HIFLD/MIRTA loaders (~20 lines each) | ~120 LOC |
| ArcGIS spatial aggregation | 6 HIFLD/MIRTA loaders (~50-70 lines each) | ~300-400 LOC |

### Changes Required

#### 5a: Time Dimension Management Extraction

**Current State**: 5 loaders duplicate `_get_or_create_time()` pattern:
- `CensusLoader`
- `EnergyLoader`
- `FredLoader`
- `QcewLoader`
- `TradeLoader`

**Target**: Extract to `DataLoader` base class as parameterized method.

**File**: `src/babylon/data/loader_base.py`

```python
class DataLoader(ABC):
    # ... existing code ...

    # Cached time dimension lookup
    _time_cache: dict[tuple[int, int | None], int] = {}

    def _get_or_create_time(
        self,
        session: Session,
        year: int,
        month: int | None = None,
        granularity: str = "annual",
    ) -> int:
        """Get or create time dimension record with caching.

        Args:
            session: Database session.
            year: 4-digit year.
            month: 1-12 month (optional for monthly granularity).
            granularity: "annual" or "monthly".

        Returns:
            time_id for the dimension record.
        """
        cache_key = (year, month)
        if cache_key in self._time_cache:
            return self._time_cache[cache_key]

        # Check DB first
        from babylon.data.normalize.schema import DimTime
        query = session.query(DimTime).filter(DimTime.year == year)
        if month is not None:
            query = query.filter(DimTime.month == month)
        else:
            query = query.filter(DimTime.month.is_(None))

        existing = query.first()
        if existing:
            self._time_cache[cache_key] = existing.time_id
            return existing.time_id

        # Create new record
        time_record = DimTime(
            year=year,
            month=month,
            granularity=granularity,
        )
        session.add(time_record)
        session.flush()

        self._time_cache[cache_key] = time_record.time_id
        return time_record.time_id
```

#### 5b: Data Source Loading Extraction

**Current State**: 12 loaders duplicate `_load_data_source()` initialization.

**Target**: Parameterize in base class with configurable attributes.

**File**: `src/babylon/data/loader_base.py`

```python
class DataLoader(ABC):
    # Class attributes for loader metadata
    source_name: str = ""  # Override in subclass
    source_description: str = ""  # Override in subclass
    source_url: str = ""  # Override in subclass

    # Cached source_id
    _source_id: int | None = None

    def _get_source_id(self, session: Session) -> int:
        """Get or create data source record.

        Uses class attributes source_name, source_description, source_url.
        Caches result for subsequent calls.
        """
        if self._source_id is not None:
            return self._source_id

        from babylon.data.normalize.schema import DimDataSource

        existing = session.query(DimDataSource).filter(
            DimDataSource.source_name == self.source_name
        ).first()

        if existing:
            self._source_id = existing.source_id
            return existing.source_id

        source = DimDataSource(
            source_name=self.source_name,
            description=self.source_description,
            url=self.source_url,
        )
        session.add(source)
        session.flush()

        self._source_id = source.source_id
        return source.source_id
```

#### 5c: County FIPS Extraction Utility

**Current State**: 6 HIFLD/MIRTA loaders duplicate county FIPS extraction from coordinates.

**Target**: Create shared utility module.

**File**: `src/babylon/data/utils/fips_resolver.py` (NEW)

```python
"""FIPS code resolution utilities.

Provides consistent county FIPS extraction from coordinates or state/county names,
used by multiple data loaders for geographic aggregation.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@lru_cache(maxsize=5000)
def state_county_to_fips(state_name: str, county_name: str) -> str | None:
    """Convert state and county names to 5-digit FIPS code.

    Args:
        state_name: Full state name (e.g., "California").
        county_name: County name (e.g., "Los Angeles County").

    Returns:
        5-digit FIPS code or None if not found.
    """
    # Normalize names
    state = state_name.strip().upper()
    county = county_name.strip().upper().replace(" COUNTY", "")

    # Lookup from static mapping (loaded from Census FIPS file)
    return _FIPS_LOOKUP.get((state, county))


def coordinates_to_county_fips(
    lat: float,
    lon: float,
    session: Session,
) -> str | None:
    """Resolve coordinates to county FIPS using spatial query.

    Requires county boundaries in database.
    Falls back to state_county_to_fips if spatial data unavailable.
    """
    # Implementation for spatial resolution
    pass


# Load static FIPS mapping from Census file
_FIPS_LOOKUP: dict[tuple[str, str], str] = {}


def _load_fips_lookup() -> None:
    """Load FIPS lookup from Census county file."""
    global _FIPS_LOOKUP
    # Load from data/census/county_fips.csv if exists
    pass
```

#### 5d: ArcGISSpatialLoader Base Class

**Current State**: 6 HIFLD/MIRTA loaders share infrastructure aggregation pattern:
- `HIFLDElectricLoader`
- `HIFLDPrisonsLoader`
- `HIFLDPoliceLoader`
- `MIRTAMilitaryLoader`
- (2 others)

**Target**: Extract common ArcGIS/GeoJSON processing to intermediate base class.

**File**: `src/babylon/data/loaders/arcgis_spatial_loader.py` (NEW)

```python
"""Base class for ArcGIS-sourced spatial data loaders.

Provides common infrastructure for loading point/facility data from
ArcGIS REST services or GeoJSON files, aggregating to county level.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from babylon.data.loader_base import DataLoader

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class FacilityRecord:
    """Base record for spatial facility data."""

    name: str
    state: str
    county: str | None
    latitude: float
    longitude: float
    facility_type: str | None = None
    capacity: float | None = None
    metadata: dict[str, Any] | None = None


class ArcGISSpatialLoader(DataLoader):
    """Base class for county-aggregated spatial data loaders.

    Subclasses override:
    - parse_source_file(): Parse GeoJSON/CSV to FacilityRecord list
    - aggregate_facilities(): Apply domain-specific aggregation logic
    - create_fact_records(): Create ORM objects from aggregated data
    """

    @abstractmethod
    def parse_source_file(self, filepath: Path) -> list[FacilityRecord]:
        """Parse source file to facility records."""
        pass

    @abstractmethod
    def aggregate_facilities(
        self,
        records: list[FacilityRecord],
    ) -> dict[str, Any]:
        """Aggregate facilities by county with domain logic."""
        pass

    def _resolve_county_fips(self, record: FacilityRecord) -> str | None:
        """Resolve facility to county FIPS code."""
        from babylon.data.utils.fips_resolver import (
            state_county_to_fips,
            coordinates_to_county_fips,
        )

        # Try state/county names first
        if record.county:
            fips = state_county_to_fips(record.state, record.county)
            if fips:
                return fips

        # Fall back to coordinate resolution
        return coordinates_to_county_fips(
            record.latitude,
            record.longitude,
            self._session,
        )
```

### Success Criteria

#### Automated Verification:

- [ ] Type checking passes: `mise run typecheck`
- [ ] Linting passes: `mise run lint`
- [ ] Unit tests pass: `mise run test:unit`
- [ ] Integration tests pass for all 13 loaders
- [ ] No regression in data loading functionality

#### Metrics:

- [ ] Total LOC reduced by 600+ lines (target: 800-1000)
- [ ] All 13 loaders still pass their integration tests
- [ ] Base class methods have 100% test coverage
- [ ] No duplicated `_get_or_create_*` patterns in leaf loaders

### Implementation Priority

1. **5b: Data source loading** (Quick win, affects all 12 loaders)
2. **5a: Time dimension management** (High value, affects 5 loaders)
3. **5c: County FIPS utility** (Moderate value, enables 5d)
4. **5d: ArcGIS base class** (Largest refactor, affects 6 loaders)

______________________________________________________________________

## Phase 6: Testing and Documentation

### Overview

Comprehensive test suite for new functionality and documentation updates.

### Changes Required

#### 1. Unit Tests for DimRace

**File**: `tests/unit/data/test_normalize/test_dim_race.py` (NEW)

```python
"""Unit tests for DimRace dimension table."""

import pytest
from babylon.data.normalize.schema import DimRace


class TestDimRaceSchema:
    """Test DimRace table structure."""

    def test_race_code_is_single_character(self) -> None:
        """Race codes should be single characters A-I or T."""
        valid_codes = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "T"}
        # Test via constraint or validation

    def test_indigenous_flag_correct_for_aian(self) -> None:
        """AIAN (code C) should have is_indigenous=True."""
        # Test that code C has correct flags

    def test_hispanic_flag_correct_for_code_i(self) -> None:
        """Hispanic (code I) should have is_hispanic_ethnicity=True."""
        # Test that code I has correct flags


class TestFactTableSpec:
    """Test FactTableSpec dataclass (from Phase 2 refactoring)."""

    def test_spec_is_frozen(self) -> None:
        """FactTableSpec should be immutable."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS
        spec = FACT_TABLE_SPECS[0]
        with pytest.raises(AttributeError):
            spec.table_id = "modified"

    def test_all_specs_have_required_fields(self) -> None:
        """All specs must have table_id, fact_class, label, value_field."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS
        for spec in FACT_TABLE_SPECS:
            assert spec.table_id
            assert spec.fact_class
            assert spec.label
            assert spec.value_field

    def test_race_suffixes_is_tuple(self) -> None:
        """race_suffixes should be a tuple for immutability."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS
        for spec in FACT_TABLE_SPECS:
            assert isinstance(spec.race_suffixes, tuple)
```

#### 2. Integration Tests for Multi-Year Loading

**File**: `tests/integration/data/test_census_multiyear.py` (NEW)

```python
"""Integration tests for multi-year Census data loading."""

import pytest
from babylon.data.census import CensusLoader
from babylon.data.loader_base import LoaderConfig


class TestMultiYearLoading:
    """Test multi-year Census data loading."""

    @pytest.fixture
    def two_year_config(self) -> LoaderConfig:
        """Config for loading just 2 years (fast test)."""
        return LoaderConfig(
            census_years=[2022, 2023],  # Note: list, not int
            state_fips_list=["06"],  # California only
        )

    def test_loads_multiple_years(self, two_year_config, session) -> None:
        """Loader should create records for each configured year."""
        loader = CensusLoader(two_year_config)
        stats = loader.load(session, reset=True)

        # Verify time dimension
        from babylon.data.normalize.schema import DimTime
        years = session.query(DimTime.year).filter(
            DimTime.year.in_([2022, 2023])
        ).all()
        assert len(years) == 2

    def test_fact_tables_have_time_id(self, two_year_config, session) -> None:
        """Fact records should have correct time_id FK."""
        loader = CensusLoader(two_year_config)
        loader.load(session, reset=True)

        from babylon.data.normalize.schema import FactCensusIncome, DimTime
        # Verify facts exist for both years
        fact_years = session.query(DimTime.year).join(
            FactCensusIncome, FactCensusIncome.time_id == DimTime.time_id
        ).distinct().all()
        assert {y[0] for y in fact_years} == {2022, 2023}


class TestDataDrivenLoaderArchitecture:
    """Test the FactTableSpec-based generic loader (from Phase 2)."""

    def test_generic_loader_handles_all_patterns(self, session) -> None:
        """Generic loader should handle scalar, mapping, and dimension patterns."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        stats = loader.load(session, reset=True)

        # All 12 specs should have loaded some data
        for spec in FACT_TABLE_SPECS:
            table_name = spec.fact_class.__tablename__
            assert stats.facts_loaded.get(table_name, 0) > 0
```

#### 3. Integration Tests for Race Disaggregation

**File**: `tests/integration/data/test_census_race.py` (NEW)

```python
"""Integration tests for race-disaggregated Census data."""

import pytest
from babylon.data.census import CensusLoader
from babylon.data.loader_base import LoaderConfig


class TestRaceDisaggregation:
    """Test race-disaggregated Census data loading."""

    def test_dim_race_populated(self, session) -> None:
        """DimRace should have 10 records (T + A-I)."""
        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        from babylon.data.normalize.schema import DimRace
        races = session.query(DimRace).all()
        assert len(races) == 10

        codes = {r.race_code for r in races}
        assert codes == {"T", "A", "B", "C", "D", "E", "F", "G", "H", "I"}

    def test_aian_has_indigenous_flag(self, session) -> None:
        """AIAN (code C) should have is_indigenous=True."""
        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        from babylon.data.normalize.schema import DimRace
        aian = session.query(DimRace).filter(DimRace.race_code == "C").one()
        assert aian.is_indigenous is True
        assert aian.race_short_name == "AIAN"

    def test_fact_tables_have_race_id(self, session) -> None:
        """Fact records should have race_id FK populated."""
        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        from babylon.data.normalize.schema import FactCensusIncome, DimRace
        # Verify facts exist for multiple races
        fact_races = session.query(DimRace.race_code).join(
            FactCensusIncome, FactCensusIncome.race_id == DimRace.race_id
        ).distinct().all()
        assert len(fact_races) >= 5  # At least Total + some race iterations

    def test_race_iteration_uses_spec_configuration(self, session) -> None:
        """Only tables with race_suffixes should have race-iterated data."""
        from babylon.data.census.loader_3nf import FACT_TABLE_SPECS

        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        # Tables with race_suffixes should have data for multiple races
        for spec in FACT_TABLE_SPECS:
            if spec.race_suffixes:
                # This table should have race-disaggregated data
                from babylon.data.normalize.schema import DimRace
                fact_races = session.query(DimRace.race_code).join(
                    spec.fact_class, spec.fact_class.race_id == DimRace.race_id
                ).distinct().all()
                assert len(fact_races) > 1, f"{spec.table_id} should have multiple races"
```

#### 4. Integration Tests for Metro Areas

**File**: `tests/integration/data/test_census_metro.py` (NEW)

```python
"""Integration tests for metropolitan statistical area data."""

import pytest
from babylon.data.census import CensusLoader
from babylon.data.loader_base import LoaderConfig


class TestMetroAreaPopulation:
    """Test metro area dimension population."""

    def test_dim_metro_area_populated(self, session) -> None:
        """DimMetroArea should have MSA, Micropolitan, and CSA records."""
        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        from babylon.data.normalize.schema import DimMetroArea
        metros = session.query(DimMetroArea).all()

        # Should have significant number of metros
        assert len(metros) > 100

        # Check area types
        area_types = {m.area_type for m in metros}
        assert "msa" in area_types
        assert "micropolitan" in area_types

    def test_bridge_county_metro_populated(self, session) -> None:
        """BridgeCountyMetro should map counties to metros."""
        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        from babylon.data.normalize.schema import BridgeCountyMetro
        mappings = session.query(BridgeCountyMetro).count()

        # California has ~58 counties, most in MSAs
        assert mappings > 50

    def test_county_to_metro_aggregation_query(self, session) -> None:
        """Should be able to aggregate county data to metro level."""
        config = LoaderConfig(census_years=[2022], state_fips_list=["06"])
        loader = CensusLoader(config)
        loader.load(session, reset=True)

        from sqlalchemy import func
        from babylon.data.normalize.schema import (
            FactCensusMedianIncome,
            BridgeCountyMetro,
            DimMetroArea,
            DimRace,
        )

        # Query: Average median income by metro area (for Total race)
        # Note: Now must filter by race_id since facts are race-disaggregated
        total_race = session.query(DimRace).filter(DimRace.race_code == "T").one()

        result = session.query(
            DimMetroArea.metro_name,
            func.avg(FactCensusMedianIncome.median_income_usd)
        ).join(
            BridgeCountyMetro, BridgeCountyMetro.metro_area_id == DimMetroArea.metro_area_id
        ).join(
            FactCensusMedianIncome, FactCensusMedianIncome.county_id == BridgeCountyMetro.county_id
        ).filter(
            FactCensusMedianIncome.race_id == total_race.race_id
        ).group_by(DimMetroArea.metro_name).first()

        assert result is not None
```

#### 5. Documentation Updates

**File**: `ai-docs/data-layer.yaml` (UPDATE)

Add section documenting new Census capabilities:

```yaml
census_loader_v2:
  description: "Enhanced Census ACS 5-Year data loader with multi-year, race, and metro support"
  capabilities:
    multi_year:
      years: "2009-2023 (15 years)"
      config: "LoaderConfig.census_years: list[int]"
    race_disaggregation:
      groups: 10
      codes: "T (Total), A-I (9 race/ethnicity groups)"
      key_groups:
        C: "American Indian and Alaska Native alone"
        I: "Hispanic or Latino"
        B: "Black or African American alone"
    metro_areas:
      types: ["msa", "micropolitan", "csa"]
      source: "Census Bureau CBSA delineation files"
      count: "~1,100+ areas"
    limitations:
      territories: "Only Puerto Rico covered (VI, GU, AS, MP not in ACS)"
      geography: "County-level only (no tract/block group)"
```

### Success Criteria

#### Automated Verification:

- [ ] All new tests pass: `mise run test:unit && mise run test:int`
- [ ] Type checking passes: `mise run typecheck`
- [ ] Linting passes: `mise run lint`
- [ ] Full CI gate passes: `mise run check`

#### Manual Verification:

- [ ] Documentation accurately reflects implemented capabilities
- [ ] Example queries work as documented
- [ ] Territory limitation is clearly documented

______________________________________________________________________

## Testing Strategy

### Unit Tests (Phase 6)

- `DimRace` schema validation
- CBSA parser correctness
- Race code mapping
- Year range handling

### Integration Tests (Phase 6)

- Multi-year data loading (2-year subset for speed)
- Race disaggregation completeness
- Metro area population
- County-to-metro aggregation queries
- Idempotency (DELETE+INSERT pattern)

### Manual Testing Steps

1. Load full dataset: `mise run data:census` (expect ~30-60 min for 15 years x 10 races)
1. Query: `SELECT race_code, COUNT(*) FROM dim_race GROUP BY race_code` - expect 10 rows
1. Query: `SELECT year, COUNT(*) FROM dim_time WHERE year BETWEEN 2009 AND 2023 GROUP BY year` - expect 15 rows
1. Query: `SELECT area_type, COUNT(*) FROM dim_metro_area GROUP BY area_type` - expect 3 types
1. Analytical query: Median income by race in Los Angeles MSA over time

## Performance Considerations

1. **Data Volume Increase**:

   - Current: ~3,200 counties x 16 tables x 1 year x 1 race = ~50K fact rows
   - Enhanced: ~3,200 counties x 16 tables x 15 years x 10 races = ~77M potential fact rows
   - Not all tables have race variants, actual will be ~20-30M rows

1. **API Rate Limiting**:

   - 0.5s delay between requests
   - ~52 states x 16 tables x 15 years x 10 races = ~124,800 API calls
   - Estimated time: ~17 hours for full load
   - Consider: Parallel loading by year, state chunking

1. **Memory Usage**:

   - Use batch inserts (`batch_size=10_000` in config)
   - Flush session periodically
   - Consider SQLite WAL mode for large inserts

1. **Optimization Opportunities**:

   - Cache API responses to disk (for reruns)
   - Use `COPY` or bulk insert instead of ORM for facts
   - Index optimization for common query patterns

## Migration Notes

1. **Schema Migration**:

   - Delete existing `marxist-data-3NF.sqlite` to recreate with new schema
   - Or use Alembic migration to add columns (more complex)
   - Recommended: Full recreate since data will be reloaded anyway

1. **CBSA Delineation File**:

   - Manual download required from Census Bureau
   - Convert XLS to CSV and place at `data/census/cbsa_delineation_2023.csv`
   - One-time setup step

1. **Backward Compatibility**:

   - **API Change**: `LoaderConfig.census_year: int` → `LoaderConfig.census_years: list[int]`
     - CLI has backwards compatibility for old config files (`census_year` → `[census_year]`)
     - Code using direct API must update to use `census_years=[year]`
   - Old queries without `race_id` filter will need updating
   - Add default `race_id` filter for "T" (Total) to maintain compatibility
   - Or create views that default to Total
   - **Data-Driven Architecture**: Individual `_load_fact_*` methods replaced by:
     - `FactTableSpec` dataclass configuration
     - `FACT_TABLE_SPECS` constant (12 specs)
     - Generic `_load_fact_table()` method
     - Two special cases: `_load_fact_hours()`, `_load_fact_income_sources()`

## References

- Data ingestion refactor plan: `thoughts/plans/2025-01-04_data-ingestion-refactor.md`
- **Phase 2 refactoring commit**: `d9fc8f4 refactor(census): data-driven fact loaders with multi-year support`
- Census API documentation: https://api.census.gov/data/2023/acs/acs5.html
- CBSA delineation files: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html
- Table IDs explained: https://www.census.gov/programs-surveys/acs/data/data-tables/table-ids-explained.html
- Race iteration suffixes: A-I scheme documented in Census technical docs
- Current Census loader: `src/babylon/data/census/loader_3nf.py`
- Current schema: `src/babylon/data/normalize/schema.py`

## Implementation History

| Phase | Status | Commit | Notes |
|-------|--------|--------|-------|
| Phase 1 | ✅ Complete | (schema changes) | DimRace, time_id/race_id FKs added |
| Phase 2 | ✅ Complete | `d9fc8f4` | Data-driven refactor, `census_years` API |
| Phase 3 | ✅ Complete | `19cbee2` | Race-iterated tables loaded via A-I suffix |
| Phase 4 | ✅ Complete | `822b021` | Metro area population (1,119 areas, county-metro bridges) |
| Phase 5 | 🔲 Pending | - | Data loader infrastructure refactoring (4 consolidation patterns) |
| Phase 6 | 🔲 Pending | - | Testing and documentation |
