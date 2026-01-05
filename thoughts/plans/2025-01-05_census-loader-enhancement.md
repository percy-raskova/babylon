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
1. Update loader infrastructure for multi-year iteration
1. Add race-disaggregated table fetching
1. Populate metro area dimensions
1. Comprehensive testing

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

- [ ] Schema migration applies cleanly: `rm data/sqlite/marxist-data-3NF.sqlite && poetry run python -c "from babylon.data.normalize.database import init_normalized_db; init_normalized_db()"`
- [ ] Type checking passes: `mise run typecheck`
- [ ] Linting passes: `mise run lint`
- [ ] Existing tests still pass: `mise run test:unit`

#### Manual Verification:

- [ ] SQLite schema inspection shows new `dim_race` table with correct columns
- [ ] All 14 fact tables have `time_id` and `race_id` columns in their PKs
- [ ] `dim_metro_area.area_type` constraint includes 'micropolitan' and 'csa'

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

______________________________________________________________________

## Phase 2: Multi-Year Loading Infrastructure

### Overview

Update LoaderConfig and CensusLoader to iterate over multiple years (2009-2023), populating `DimTime` and using `time_id` in fact tables.

### Changes Required

#### 1. Update LoaderConfig

**File**: `src/babylon/data/loader_base.py`
**Location**: Line 63

```python
# BEFORE
census_year: int = 2022

# AFTER
census_years: list[int] = field(
    default_factory=lambda: list(range(2009, 2024))  # 2009-2023 inclusive
)
```

#### 2. Add DimRace Population

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: After `_load_genders()` method

```python
# Race code definitions
RACE_CODES: list[dict[str, Any]] = [
    {"code": "T", "name": "Total (all races)", "short": "Total", "hispanic": False, "indigenous": False, "order": 0},
    {"code": "A", "name": "White alone", "short": "White", "hispanic": False, "indigenous": False, "order": 1},
    {"code": "B", "name": "Black or African American alone", "short": "Black", "hispanic": False, "indigenous": False, "order": 2},
    {"code": "C", "name": "American Indian and Alaska Native alone", "short": "AIAN", "hispanic": False, "indigenous": True, "order": 3},
    {"code": "D", "name": "Asian alone", "short": "Asian", "hispanic": False, "indigenous": False, "order": 4},
    {"code": "E", "name": "Native Hawaiian and Other Pacific Islander alone", "short": "NHPI", "hispanic": False, "indigenous": False, "order": 5},
    {"code": "F", "name": "Some other race alone", "short": "Other", "hispanic": False, "indigenous": False, "order": 6},
    {"code": "G", "name": "Two or more races", "short": "Multiracial", "hispanic": False, "indigenous": False, "order": 7},
    {"code": "H", "name": "White alone, not Hispanic or Latino", "short": "White NH", "hispanic": False, "indigenous": False, "order": 8},
    {"code": "I", "name": "Hispanic or Latino", "short": "Hispanic", "hispanic": True, "indigenous": False, "order": 9},
]

def _load_races(self, session: Session) -> None:
    """Load race/ethnicity dimension (static, 10 records including Total)."""
    for race_data in RACE_CODES:
        race = DimRace(
            race_code=race_data["code"],
            race_name=race_data["name"],
            race_short_name=race_data["short"],
            is_hispanic_ethnicity=race_data["hispanic"],
            is_indigenous=race_data["indigenous"],
            display_order=race_data["order"],
        )
        session.add(race)
    session.flush()

    # Build lookup
    self._race_code_to_id = {
        r.race_code: r.race_id
        for r in session.query(DimRace).all()
    }
```

#### 3. Update DimTime Population

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: New method

```python
def _load_time_dimension(self, session: Session) -> None:
    """Populate DimTime for all census years if not already present."""
    existing_years = {t.year for t in session.query(DimTime).all()}

    for year in self.config.census_years:
        if year not in existing_years:
            time_record = DimTime(
                year=year,
                quarter=None,  # Annual data
                month=None,
            )
            session.add(time_record)
    session.flush()

    # Build lookup
    self._year_to_time_id = {
        t.year: t.time_id
        for t in session.query(DimTime).filter(DimTime.year.in_(self.config.census_years)).all()
    }
```

#### 4. Update Main Load Method for Multi-Year Iteration

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
    """Load Census ACS 5-Year data for all configured years."""
    stats = LoadStats(source="census")

    try:
        if reset:
            if verbose:
                print("Clearing existing census data...")
            self.clear_tables(session)
            session.flush()

        # Load dimensions (once, shared across years)
        self._load_data_source(session, min(self.config.census_years))  # Use earliest year
        self._load_races(session)
        stats.dimensions_loaded["dim_race"] = 10

        self._load_time_dimension(session)
        stats.dimensions_loaded["dim_time"] = len(self.config.census_years)

        self._load_genders(session)
        self._load_states(session)
        # ... other dimension loads ...

        # Iterate over years
        for year in self.config.census_years:
            if verbose:
                print(f"\n{'='*60}")
                print(f"Loading Census ACS 5-Year: {year}")
                print(f"{'='*60}")

            self._client = CensusAPIClient(year=year)
            time_id = self._year_to_time_id[year]

            # Load facts for this year (for Total race first)
            self._load_facts_for_year(session, stats, year, time_id, race_code="T", verbose=verbose)

            # Load race-disaggregated facts
            for race_data in RACE_CODES[1:]:  # Skip "T" (Total)
                self._load_facts_for_year(
                    session, stats, year, time_id,
                    race_code=race_data["code"],
                    verbose=verbose
                )

        session.commit()

    except Exception as e:
        session.rollback()
        stats.errors.append(str(e))
        raise

    return stats
```

### Success Criteria

#### Automated Verification:

- [ ] Type checking passes: `mise run typecheck`
- [ ] Linting passes: `mise run lint`
- [ ] Unit tests pass: `mise run test:unit`
- [ ] Single-year load works: `poetry run python -m babylon.data.cli census` (with modified config for single year test)

#### Manual Verification:

- [ ] `DimTime` has records for years 2009-2023
- [ ] `DimRace` has 10 records (T, A-I)
- [ ] Fact tables have `time_id` and `race_id` populated
- [ ] Progress output shows year-by-year loading

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 3.

______________________________________________________________________

## Phase 3: Race-Disaggregated Table Loading

### Overview

Update API client and loader to fetch race-iterated tables (e.g., B19001A through B19001I) and populate facts with race_id.

### Changes Required

#### 1. Define Race-Iterated Table Mapping

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: After table lists

```python
# Tables that have race iterations (A-I suffixes)
# Not all Census tables have race variants
RACE_ITERATED_TABLES: dict[str, list[str]] = {
    # Income tables
    "B19001": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],  # Income distribution
    "B19013": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],  # Median income
    # Employment tables
    "B23025": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],  # Employment status
    # Housing tables
    "B25003": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],  # Tenure
    # Poverty tables
    "B17001": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],  # Poverty status
    # Education tables
    "B15003": [],  # No race iterations for this table
    # Worker class - uses C-table race iterations
    "C24010": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],  # Occupation by race
}

# Tables without race iterations (load only with race_code="T")
NON_RACE_TABLES = ["B19083", "B08301", "B19052", "B19053", "B19054", "B23020", "B25064", "B25070", "B24080"]
```

#### 2. Update Fact Loading to Include Race

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: New helper method

```python
def _load_facts_for_year(
    self,
    session: Session,
    stats: LoadStats,
    year: int,
    time_id: int,
    race_code: str,
    verbose: bool,
) -> None:
    """Load all fact tables for a specific year and race code."""
    race_id = self._race_code_to_id[race_code]

    # Determine which tables to load for this race code
    if race_code == "T":
        tables_to_load = ALL_TABLES
    else:
        # Only load tables that have this race iteration
        tables_to_load = [
            f"{base}{race_code}"
            for base, suffixes in RACE_ITERATED_TABLES.items()
            if race_code in suffixes
        ]

    if verbose and race_code != "T":
        print(f"  Loading race-iterated tables for {race_code}...")

    for state_fips in tqdm(
        self._state_fips_list,
        desc=f"Year {year}, Race {race_code}",
        disable=not verbose,
    ):
        for table in tables_to_load:
            try:
                # Fetch data
                data = self._client.get_table_data(table, state_fips=state_fips)
                stats.api_calls += 1

                # Route to appropriate fact loader
                base_table = table.rstrip("ABCDEFGHI")  # Strip race suffix
                self._route_to_fact_loader(
                    session, base_table, data, time_id, race_id, stats
                )

            except CensusAPIError as e:
                if "unknown variable" in str(e).lower():
                    # Table doesn't exist for this year/race combo - skip
                    continue
                stats.errors.append(f"{table} {state_fips}: {e}")
```

#### 3. Update Individual Fact Loaders

**File**: `src/babylon/data/census/loader_3nf.py`
**Location**: Each `_load_fact_*` method

Example for income facts:

```python
def _load_fact_income(
    self,
    session: Session,
    data: list[CountyData],
    time_id: int,
    race_id: int,
    stats: LoadStats,
) -> None:
    """Load household income distribution facts."""
    for county_data in data:
        county_id = self._fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            bracket_id = self._bracket_code_to_id.get(var_code)
            if not bracket_id:
                continue

            fact = FactCensusIncome(
                county_id=county_id,
                bracket_id=bracket_id,
                source_id=self._source_id,
                time_id=time_id,      # NEW
                race_id=race_id,      # NEW
                households=value,
            )
            session.add(fact)

    session.flush()
    stats.facts_loaded["fact_census_income"] = (
        stats.facts_loaded.get("fact_census_income", 0) + len(data)
    )
```

### Success Criteria

#### Automated Verification:

- [ ] Type checking passes: `mise run typecheck`
- [ ] Linting passes: `mise run lint`
- [ ] Unit tests pass: `mise run test:unit`
- [ ] Race-iterated API calls succeed (test with B19001A for single state)

#### Manual Verification:

- [ ] Fact tables contain records for all 10 race codes
- [ ] Race "C" (AIAN) has meaningful data in income/employment tables
- [ ] Total counts match when summing across races (approximately)
- [ ] No duplicate PK errors (county_id, bracket_id, source_id, time_id, race_id is unique)

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

- [ ] Type checking passes: `mise run typecheck`
- [ ] Linting passes: `mise run lint`
- [ ] Unit tests pass: `mise run test:unit`
- [ ] CBSA parser unit tests pass (new tests)

#### Manual Verification:

- [ ] `dim_metro_area` has ~1,100+ records (393 MSA + 542 μSA + CSAs)
- [ ] `bridge_county_metro` has ~4,000+ records
- [ ] Query: Counties in "New York-Newark-Jersey City, NY-NJ-PA" MSA returns ~23 counties
- [ ] Query: CSA aggregation works correctly

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 5.

______________________________________________________________________

## Phase 5: Testing and Documentation

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
            census_years=[2022, 2023],
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
        )

        # Query: Average median income by metro area
        result = session.query(
            DimMetroArea.metro_name,
            func.avg(FactCensusMedianIncome.median_income)
        ).join(
            BridgeCountyMetro, BridgeCountyMetro.metro_area_id == DimMetroArea.metro_area_id
        ).join(
            FactCensusMedianIncome, FactCensusMedianIncome.county_id == BridgeCountyMetro.county_id
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

### Unit Tests (Phase 5)

- `DimRace` schema validation
- CBSA parser correctness
- Race code mapping
- Year range handling

### Integration Tests (Phase 5)

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

   - Old queries without `race_id` filter will need updating
   - Add default `race_id` filter for "T" (Total) to maintain compatibility
   - Or create views that default to Total

## References

- Data ingestion refactor plan: `thoughts/plans/2025-01-04_data-ingestion-refactor.md`
- Census API documentation: https://api.census.gov/data/2023/acs/acs5.html
- CBSA delineation files: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html
- Table IDs explained: https://www.census.gov/programs-surveys/acs/data/data-tables/table-ids-explained.html
- Race iteration suffixes: A-I scheme documented in Census technical docs
- Current Census loader: `src/babylon/data/census/loader_3nf.py`
- Current schema: `src/babylon/data/normalize/schema.py`
