"""Census data loader for direct 3NF schema population.

Loads ACS 5-Year Estimates directly from Census Bureau API into the normalized
3NF schema (marxist-data-3NF.duckdb), bypassing the intermediate research.sqlite.

This loader:
- Uses LoaderConfig for parameterized temporal/geographic/operational settings
- Applies Marxian classifications inline during load
- Uses DELETE+INSERT pattern for idempotency
- Writes to 14 census fact tables and supporting dimensions

Usage:
    from babylon.data.census.loader_3nf import CensusLoader
    from babylon.data import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session_factory

    config = LoaderConfig(census_years=[2021], state_fips_list=["06"])  # CA only
    loader = CensusLoader(config)

    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
        print(stats)
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from tqdm import tqdm

from babylon.data.api_loader_base import ApiLoaderBase
from babylon.data.census.api_client import CensusAPIClient, CountyData, VariableMetadata
from babylon.data.exceptions import CensusAPIError
from babylon.data.loader_base import LoaderConfig, LoadStats
from babylon.data.normalize.classifications import (
    classify_labor_type,
    classify_marxian_class,
    classify_rent_burden,
)
from babylon.data.normalize.schema import (
    BridgeCountyMetro,
    DimCommuteMode,
    DimCounty,
    DimDataSource,
    DimEducationLevel,
    DimEmploymentStatus,
    DimGender,
    DimHousingTenure,
    DimIncomeBracket,
    DimMetroArea,
    DimOccupation,
    DimPovertyCategory,
    DimRace,
    DimRentBurden,
    DimState,
    DimTime,
    DimWorkerClass,
    FactCensusCommute,
    FactCensusEducation,
    FactCensusEmployment,
    FactCensusGini,
    FactCensusHours,
    FactCensusHousing,
    FactCensusIncome,
    FactCensusIncomeSources,
    FactCensusMedianIncome,
    FactCensusOccupation,
    FactCensusPoverty,
    FactCensusRent,
    FactCensusRentBurden,
    FactCensusWorkerClass,
)
from babylon.data.utils import BatchWriter
from babylon.data.utils.logging_helpers import log_api_error

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Census tables to load
ORIGINAL_TABLES = ["B19001", "B19013", "B23025", "B24080", "B25003", "B25064", "B25070", "C24010"]
MARXIAN_TABLES = ["B23020", "B17001", "B15003", "B19083", "B08301", "B19052", "B19053", "B19054"]
ALL_TABLES = ORIGINAL_TABLES + MARXIAN_TABLES

# Race code definitions following Census A-I suffix scheme
# T = Total (base table without race suffix), A-I = race-iterated tables
RACE_CODES: list[dict[str, object]] = [
    {
        "code": "T",
        "name": "Total (all races)",
        "short": "Total",
        "hispanic": False,
        "indigenous": False,
        "order": 0,
    },
    {
        "code": "A",
        "name": "White alone",
        "short": "White",
        "hispanic": False,
        "indigenous": False,
        "order": 1,
    },
    {
        "code": "B",
        "name": "Black or African American alone",
        "short": "Black",
        "hispanic": False,
        "indigenous": False,
        "order": 2,
    },
    {
        "code": "C",
        "name": "American Indian and Alaska Native alone",
        "short": "AIAN",
        "hispanic": False,
        "indigenous": True,
        "order": 3,
    },
    {
        "code": "D",
        "name": "Asian alone",
        "short": "Asian",
        "hispanic": False,
        "indigenous": False,
        "order": 4,
    },
    {
        "code": "E",
        "name": "Native Hawaiian and Other Pacific Islander alone",
        "short": "NHPI",
        "hispanic": False,
        "indigenous": False,
        "order": 5,
    },
    {
        "code": "F",
        "name": "Some other race alone",
        "short": "Other",
        "hispanic": False,
        "indigenous": False,
        "order": 6,
    },
    {
        "code": "G",
        "name": "Two or more races",
        "short": "Multiracial",
        "hispanic": False,
        "indigenous": False,
        "order": 7,
    },
    {
        "code": "H",
        "name": "White alone, not Hispanic or Latino",
        "short": "White NH",
        "hispanic": False,
        "indigenous": False,
        "order": 8,
    },
    {
        "code": "I",
        "name": "Hispanic or Latino",
        "short": "Hispanic",
        "hispanic": True,
        "indigenous": False,
        "order": 9,
    },
]


@dataclass(frozen=True)
class FactTableSpec:
    """Configuration for loading a Census fact table via the generic loader.

    Supports three loading patterns:
    - Dimension-iterated: Maps variable codes to dimension FKs (most tables)
    - Scalar: Single value per county from a specific variable
    - Hardcoded mapping: Uses explicit var_code -> dim_value mapping

    Attributes:
        table_id: Census table ID (e.g., "B19001").
        fact_class: SQLAlchemy fact model class.
        label: Label for tqdm progress bar.
        value_field: Field name on fact model for the measure value.
        value_type: Type of value - "int" or "decimal".
        dim_class: Dimension model class for FK lookup (optional).
        dim_code_attr: Attribute on dimension for code lookup (e.g., "bracket_code").
        fact_dim_attr: Attribute on fact for dimension FK (e.g., "bracket_id").
        skip_total: Whether to skip the _001E total variable.
        extract_gender: Whether to extract gender from variable labels.
        scalar_var: For scalar tables, the specific variable to fetch.
        var_mapping: For hardcoded mapping, dict of var_code -> dimension value.
    """

    # Required fields
    table_id: str
    fact_class: type
    label: str
    value_field: str
    value_type: Literal["int", "decimal"] = "int"

    # Dimension mapping (for iterated tables)
    dim_class: type | None = None
    dim_code_attr: str = ""
    fact_dim_attr: str = ""

    # Behavior flags
    skip_total: bool = True
    extract_gender: bool = False

    # Scalar tables (single value per county)
    scalar_var: str | None = None

    # Hardcoded variable mapping (for housing)
    var_mapping: dict[str, str] = field(default_factory=dict)

    # Race iteration support (Phase 3)
    # Tables with race iterations have A-I suffixed versions (e.g., B19001A-I)
    # Empty tuple means table only exists for Total race
    race_suffixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FactLoadPlan:
    """Load-plan entry for a single fact ingestion step."""

    kind: Literal["spec", "hours", "income_sources"]
    spec: FactTableSpec | None
    time_id: int
    race_code: str
    race_id: int
    race_name: str


# Race suffixes for tables that have race iterations (Census A-I scheme)
# Most demographic tables have race-iterated versions (e.g., B19001A through B19001I)
FULL_RACE_SUFFIXES = ("A", "B", "C", "D", "E", "F", "G", "H", "I")

# Fact table specifications for the generic loader
# Handles 12 of 14 fact tables; hours and income_sources have special loaders
FACT_TABLE_SPECS: list[FactTableSpec] = [
    # Pattern A: Dimension-iterated tables
    FactTableSpec(
        table_id="B19001",
        fact_class=FactCensusIncome,
        label="B19001",
        dim_class=DimIncomeBracket,
        dim_code_attr="bracket_code",
        fact_dim_attr="bracket_id",
        value_field="household_count",
        skip_total=True,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B23025",
        fact_class=FactCensusEmployment,
        label="B23025",
        dim_class=DimEmploymentStatus,
        dim_code_attr="status_code",
        fact_dim_attr="status_id",
        value_field="person_count",
        skip_total=False,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B25070",
        fact_class=FactCensusRentBurden,
        label="B25070",
        dim_class=DimRentBurden,
        dim_code_attr="bracket_code",
        fact_dim_attr="burden_id",
        value_field="household_count",
        skip_total=True,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B15003",
        fact_class=FactCensusEducation,
        label="B15003",
        dim_class=DimEducationLevel,
        dim_code_attr="level_code",
        fact_dim_attr="level_id",
        value_field="person_count",
        skip_total=False,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B08301",
        fact_class=FactCensusCommute,
        label="B08301",
        dim_class=DimCommuteMode,
        dim_code_attr="mode_code",
        fact_dim_attr="mode_id",
        value_field="worker_count",
        skip_total=False,
        # No race iterations for commute mode table
    ),
    FactTableSpec(
        table_id="B17001",
        fact_class=FactCensusPoverty,
        label="B17001",
        dim_class=DimPovertyCategory,
        dim_code_attr="category_code",
        fact_dim_attr="category_id",
        value_field="person_count",
        skip_total=False,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    # Pattern B: Scalar value tables
    FactTableSpec(
        table_id="B19013",
        fact_class=FactCensusMedianIncome,
        label="B19013",
        value_field="median_income_usd",
        value_type="decimal",
        scalar_var="B19013_001E",
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B25064",
        fact_class=FactCensusRent,
        label="B25064",
        value_field="median_rent_usd",
        value_type="decimal",
        scalar_var="B25064_001E",
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="B19083",
        fact_class=FactCensusGini,
        label="B19083",
        value_field="gini_coefficient",
        value_type="decimal",
        scalar_var="B19083_001E",
        # No race iterations for Gini coefficient table
    ),
    # Pattern C: Gender-extracted dimension tables
    FactTableSpec(
        table_id="B24080",
        fact_class=FactCensusWorkerClass,
        label="B24080",
        dim_class=DimWorkerClass,
        dim_code_attr="class_code",
        fact_dim_attr="class_id",
        value_field="worker_count",
        extract_gender=True,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    FactTableSpec(
        table_id="C24010",
        fact_class=FactCensusOccupation,
        label="C24010",
        dim_class=DimOccupation,
        dim_code_attr="occupation_code",
        fact_dim_attr="occupation_id",
        value_field="worker_count",
        extract_gender=True,
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
    # Pattern E: Hardcoded variable mapping
    FactTableSpec(
        table_id="B25003",
        fact_class=FactCensusHousing,
        label="B25003",
        dim_class=DimHousingTenure,
        dim_code_attr="tenure_type",
        fact_dim_attr="tenure_id",
        value_field="household_count",
        var_mapping={
            "B25003_001E": "total",
            "B25003_002E": "owner",
            "B25003_003E": "renter",
        },
        race_suffixes=FULL_RACE_SUFFIXES,  # Has race iterations
    ),
]

# Default state FIPS codes (50 states + DC + PR)
DEFAULT_STATE_FIPS = [
    "01",
    "02",
    "04",
    "05",
    "06",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "50",
    "51",
    "53",
    "54",
    "55",
    "56",
    "72",
]

# State abbreviations for DimState
STATE_ABBREVS: dict[str, str] = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "72": "PR",
}


class CensusLoader(ApiLoaderBase):
    """Loader for Census ACS data into 3NF schema.

    Fetches ACS 5-Year Estimates from Census Bureau API and loads directly
    into the normalized 3NF schema with Marxian classifications applied inline.

    Attributes:
        config: LoaderConfig controlling year, geographic scope, and operations.

    Example:
        config = LoaderConfig(census_years=[2021], state_fips_list=["06", "36"])
        loader = CensusLoader(config)
        stats = loader.load(session, reset=True)
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize Census loader with configuration."""
        super().__init__(config)
        self._client: CensusAPIClient | None = None
        self._fips_to_county: dict[str, int] = {}
        self._state_fips_to_id: dict[str, int] = {}
        self._gender_to_id: dict[str, int] = {}
        self._race_code_to_id: dict[str, int] = {}
        self._year_to_time_id: dict[int, int] = {}
        self._source_id: int | None = None
        self._base_table_missing_by_year: dict[int, dict[str, set[str]]] = {}
        self._race_table_skips_by_year: dict[int, dict[str, set[str]]] = {}
        self._race_tables_unavailable_by_year: dict[int, set[str]] = {}
        self._missing_tables_by_year: dict[int, set[str]] = {}
        self._variables_by_year: dict[int, dict[str, dict[str, VariableMetadata]]] = {}
        self._variables_from_base_by_year: dict[int, set[str]] = {}

    def _make_client(self, year: int) -> CensusAPIClient:
        """Create a Census API client for a specific year."""
        return CensusAPIClient(year=year, timeout=30.0)

    def _fetch_variables(self, table_id: str) -> dict[str, Any]:
        """Fetch variable metadata for a table via the active client."""
        assert self._client is not None
        return self._client.get_variables(table_id)

    def _fetch_table_data(self, table_id: str, state_fips: str | None) -> list[Any]:
        """Fetch table data for a state (or all states) via the active client."""
        assert self._client is not None
        return self._client.get_table_data(table_id, state_fips=state_fips)

    def _is_race_suffixed_table(self, table_id: str) -> bool:
        """Return True if the table id ends with a race suffix (A-I)."""
        return len(table_id) > 1 and table_id[-1] in FULL_RACE_SUFFIXES

    def _base_table_id(self, table_id: str) -> str:
        """Return the base table id for a race-suffixed table."""
        if self._is_race_suffixed_table(table_id):
            return table_id[:-1]
        return table_id

    def _record_base_table_missing(self, year: int, table_id: str, state_fips: str) -> None:
        """Track when a base table is missing for a state/year."""
        year_missing = self._base_table_missing_by_year.setdefault(year, {})
        year_missing.setdefault(table_id, set()).add(state_fips)

    def _is_base_table_missing(self, year: int, table_id: str, state_fips: str) -> bool:
        """Return True if the base table was missing for a state/year."""
        year_missing = self._base_table_missing_by_year.get(year, {})
        return state_fips in year_missing.get(table_id, set())

    def _record_race_table_skip(self, year: int, table_id: str, state_fips: str) -> None:
        """Track when race tables are skipped due to base table missing."""
        year_skips = self._race_table_skips_by_year.setdefault(year, {})
        year_skips.setdefault(table_id, set()).add(state_fips)

    def _record_race_tables_unavailable(self, year: int, base_table_id: str, reason: str) -> None:
        """Track when race-iterated tables are unavailable for a base table/year."""
        year_unavailable = self._race_tables_unavailable_by_year.setdefault(year, set())
        if base_table_id in year_unavailable:
            return
        year_unavailable.add(base_table_id)
        logger.info(
            "Race-iterated tables for base table %s unavailable for year %s (%s).",
            base_table_id,
            year,
            reason,
            extra={
                "loader": "census",
                "operation": "race_tables_unavailable",
                "base_table_id": base_table_id,
                "year": year,
                "reason": reason,
            },
        )

    def _is_race_tables_unavailable(self, year: int, base_table_id: str) -> bool:
        """Return True if race-iterated tables are unavailable for a base table/year."""
        return base_table_id in self._race_tables_unavailable_by_year.get(year, set())

    def _is_table_missing(self, year: int, table_id: str) -> bool:
        """Return True if the table is known missing for a year."""
        return table_id in self._missing_tables_by_year.get(year, set())

    def _record_missing_table(
        self,
        year: int,
        table_id: str,
        reason: str,
        stats: LoadStats | None = None,
    ) -> None:
        """Track a table that is unavailable for an entire year."""
        year_missing = self._missing_tables_by_year.setdefault(year, set())
        if table_id in year_missing:
            return
        year_missing.add(table_id)
        logger.warning(
            "Skipping Census table %s for year %s (%s).",
            table_id,
            year,
            reason,
            extra={
                "loader": "census",
                "operation": "table_missing_for_year",
                "table_id": table_id,
                "year": year,
                "reason": reason,
            },
        )
        if stats is not None:
            stats.record_ingest(f"census:{year}:missing_table:{table_id}", 1)

    def _get_variables_for_table(
        self, table_id: str, year: int
    ) -> tuple[dict[str, VariableMetadata], bool]:
        """Return variable metadata for a table.

        Returns:
            Tuple of (variables, from_base). from_base is always False for
            race-suffixed tables that lack metadata (race tables are skipped).
        """
        year_cache = self._variables_by_year.setdefault(year, {})
        from_base_cache = self._variables_from_base_by_year.setdefault(year, set())
        if table_id in year_cache:
            return year_cache[table_id], table_id in from_base_cache

        if self._is_race_suffixed_table(table_id):
            base_table_id = self._base_table_id(table_id)
            if self._is_race_tables_unavailable(year, base_table_id):
                year_cache[table_id] = {}
                return {}, False

        variables = self._fetch_variables(table_id)
        if variables:
            year_cache[table_id] = variables
            return variables, False

        if self._is_race_suffixed_table(table_id):
            base_table_id = self._base_table_id(table_id)
            self._record_race_tables_unavailable(
                year,
                base_table_id,
                reason="variable_metadata_missing",
            )

        year_cache[table_id] = {}
        return {}, False

    def _fetch_county_data_chunked(self, variables: list[str], state_fips: str) -> list[CountyData]:
        """Fetch county data with variable chunking to respect API limits."""
        assert self._client is not None
        if not variables:
            return []

        chunk_size = 45
        merged: dict[str, CountyData] = {}
        for i in range(0, len(variables), chunk_size):
            chunk = variables[i : i + chunk_size]
            data = self._client.get_county_data(chunk, state_fips=state_fips)
            for row in data:
                existing = merged.get(row.fips)
                if existing is None:
                    merged[row.fips] = CountyData(
                        state_fips=row.state_fips,
                        county_fips=row.county_fips,
                        fips=row.fips,
                        name=row.name,
                        values=dict(row.values),
                    )
                else:
                    existing.values.update(row.values)

        return list(merged.values())

    def _log_race_table_skip_summary(self, year: int, stats: LoadStats | None = None) -> None:
        """Log a summary of skipped race-iterated tables for a year."""
        skipped = self._race_table_skips_by_year.pop(year, {})
        if not skipped:
            return

        for base_table_id, states in sorted(skipped.items()):
            state_fips_list = sorted(states)
            logger.warning(
                "Skipping race-iterated tables for base table %s because base table data "
                "is missing for %s states.",
                base_table_id,
                len(state_fips_list),
                extra={
                    "loader": "census",
                    "operation": "race_iterated_skip",
                    "base_table_id": base_table_id,
                    "year": year,
                    "state_fips": state_fips_list,
                    "skip_reason": "base_table_missing",
                },
            )
            if stats is not None:
                stats.record_ingest(
                    f"census:{year}:race_table_skips:{base_table_id}",
                    len(state_fips_list),
                )

    def _handle_api_error(
        self,
        error: CensusAPIError,
        *,
        table_id: str,
        state_fips: str,
        operation: str,
        stats: LoadStats | None = None,
    ) -> None:
        """Handle API errors according to loader policy."""
        year = self._client.year if self._client else None
        dataset = self._client.dataset if self._client else None
        detail_context: dict[str, object] = {
            "loader": "census",
            "operation": operation,
            "table_id": table_id,
            "state_fips": state_fips,
            "year": year,
            "dataset": dataset,
            "api_error_policy": self.config.api_error_policy,
        }
        log_api_error(
            logger,
            error,
            context=detail_context,
            level=logging.WARNING,
        )
        if stats is not None:
            year_label = str(year) if year is not None else "unknown"
            stats.record_api_error(
                error,
                context=f"census:{year_label}:{table_id}:{state_fips}",
                details=detail_context,
            )
        if self.config.api_error_policy == "abort":
            raise error

    def _iter_base_fact_plan(self, time_id: int, race_id: int) -> Iterator[FactLoadPlan]:
        """Yield the base load plan for Total race tables and special cases."""
        for spec in FACT_TABLE_SPECS:
            yield FactLoadPlan(
                kind="spec",
                spec=spec,
                time_id=time_id,
                race_code="T",
                race_id=race_id,
                race_name="Total",
            )

        yield FactLoadPlan(
            kind="hours",
            spec=None,
            time_id=time_id,
            race_code="T",
            race_id=race_id,
            race_name="Total",
        )

        yield FactLoadPlan(
            kind="income_sources",
            spec=None,
            time_id=time_id,
            race_code="T",
            race_id=race_id,
            race_name="Total",
        )

    def _iter_race_fact_plan(self, time_id: int) -> Iterator[FactLoadPlan]:
        """Yield fact-table load plan entries for race-iterated tables."""
        for race_data in RACE_CODES[1:]:
            race_code = str(race_data["code"])
            race_name = str(race_data["short"])
            race_id = self._race_code_to_id[race_code]

            for spec in FACT_TABLE_SPECS:
                if race_code not in spec.race_suffixes:
                    continue

                yield FactLoadPlan(
                    kind="spec",
                    spec=self._create_race_suffixed_spec(spec, race_code),
                    time_id=time_id,
                    race_code=race_code,
                    race_id=race_id,
                    race_name=race_name,
                )

    def _execute_fact_plan(
        self,
        plan: FactLoadPlan,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        stats: LoadStats | None = None,
    ) -> int:
        """Execute a load-plan entry."""
        if plan.kind == "spec":
            assert plan.spec is not None
            return self._load_fact_table(
                plan.spec,
                session,
                state_fips_list,
                verbose,
                plan.time_id,
                plan.race_id,
                stats,
            )
        if plan.kind == "hours":
            return self._load_fact_hours(
                session,
                state_fips_list,
                verbose,
                plan.time_id,
                plan.race_id,
                stats,
            )
        return self._load_fact_income_sources(
            session,
            state_fips_list,
            verbose,
            plan.time_id,
            plan.race_id,
            stats,
        )

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates.

        Order matters for FK constraints: child tables must be listed before
        parent tables they reference (e.g., DimCounty before DimState).
        """
        return [
            # Bridge tables - delete first (FK dependencies)
            BridgeCountyMetro,  # References DimCounty and DimMetroArea
            # Shared dimensions - order respects FK dependencies
            DimCounty,  # References DimState, must be deleted first
            DimMetroArea,  # Metro areas (MSA, Micropolitan, CSA)
            DimState,  # Parent of DimCounty
            DimDataSource,
            # Census-specific dimensions
            DimGender,
            DimRace,  # Race dimension for disaggregated analysis
            DimTime,  # Time dimension for multi-year loading
            DimIncomeBracket,
            DimEmploymentStatus,
            DimWorkerClass,
            DimOccupation,
            DimEducationLevel,
            DimHousingTenure,
            DimRentBurden,
            DimCommuteMode,
            DimPovertyCategory,
        ]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [
            FactCensusIncome,
            FactCensusMedianIncome,
            FactCensusEmployment,
            FactCensusWorkerClass,
            FactCensusOccupation,
            FactCensusHours,
            FactCensusHousing,
            FactCensusRent,
            FactCensusRentBurden,
            FactCensusEducation,
            FactCensusGini,
            FactCensusCommute,
            FactCensusPoverty,
            FactCensusIncomeSources,
        ]

    def clear_tables(self, session: Session) -> None:
        """Clear Census tables without deleting shared dimensions."""
        self._delete_tables(session, self.get_fact_tables())
        self._delete_tables(
            session,
            [
                BridgeCountyMetro,
                DimIncomeBracket,
                DimEmploymentStatus,
                DimWorkerClass,
                DimOccupation,
                DimEducationLevel,
                DimHousingTenure,
                DimRentBurden,
                DimCommuteMode,
                DimPovertyCategory,
                DimGender,
                DimRace,
            ],
        )

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load Census data into 3NF schema.

        Loads ACS 5-Year Estimates for all configured years and race groups.
        Phase 2 infrastructure loads dimensions once (shared across years),
        then iterates over years for fact loading.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing census data before loading.
            verbose: If True, print progress information.
            **kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="census")
        self._base_table_missing_by_year.clear()
        self._race_table_skips_by_year.clear()
        self._race_tables_unavailable_by_year.clear()
        self._missing_tables_by_year.clear()
        self._variables_by_year.clear()
        self._variables_from_base_by_year.clear()
        census_years = self.config.census_years
        state_fips_list = self.config.state_fips_list or DEFAULT_STATE_FIPS

        # Use first year for dimensions that need API metadata
        initial_year = census_years[0] if census_years else 2021

        if verbose:
            year_range = (
                f"{min(census_years)}-{max(census_years)}"
                if len(census_years) > 1
                else str(census_years[0])
            )
            print("Loading ACS 5-Year Estimates from Census API")
            print(f"Years: {year_range} ({len(census_years)} years)")
            print(f"States: {len(state_fips_list)} ({', '.join(state_fips_list[:5])}...)")

        try:
            # Create API client for initial dimension loading
            with self._client_scope(self._make_client(initial_year)):
                # Clear existing data if reset
                if reset:
                    if verbose:
                        print("Clearing existing census data...")
                    self.clear_tables(session)
                    session.flush()

                # Load dimensions first (shared across all years)
                self._load_data_source(session, initial_year)
                stats.dimensions_loaded["dim_data_source"] = 1

                self._load_genders(session)
                stats.dimensions_loaded["dim_gender"] = 3

                # Load race dimension (10 records: T + A-I)
                race_count = self._load_races(session)
                stats.dimensions_loaded["dim_race"] = race_count
                if verbose:
                    print(f"  Loaded {race_count} race categories")

                # Load time dimension for all configured years
                time_count = self._load_time_dimension(session)
                stats.dimensions_loaded["dim_time"] = len(census_years)
                if verbose:
                    print(
                        f"  Loaded {time_count} new time records ({len(census_years)} total years)"
                    )

                state_count = self._load_states(session, state_fips_list, verbose)
                stats.dimensions_loaded["dim_state"] = state_count

                county_count = self._load_counties(session, state_fips_list, verbose, stats)
                stats.dimensions_loaded["dim_county"] = county_count

                # Load metro areas and county-metro bridge (Phase 4)
                metro_count, bridge_count = self._load_metro_areas(session, verbose)
                stats.dimensions_loaded["dim_metro_area"] = metro_count
                stats.dimensions_loaded["bridge_county_metro"] = bridge_count

                # Load code dimensions from variable metadata
                bracket_count = self._load_income_brackets(session, verbose)
                stats.dimensions_loaded["dim_income_bracket"] = bracket_count

                status_count = self._load_employment_statuses(session, verbose)
                stats.dimensions_loaded["dim_employment_status"] = status_count

                class_count = self._load_worker_classes(session, verbose)
                stats.dimensions_loaded["dim_worker_class"] = class_count

                occ_count = self._load_occupations(session, verbose)
                stats.dimensions_loaded["dim_occupation"] = occ_count

                edu_count = self._load_education_levels(session, verbose)
                stats.dimensions_loaded["dim_education_level"] = edu_count

                tenure_count = self._load_housing_tenures(session)
                stats.dimensions_loaded["dim_housing_tenure"] = tenure_count

                burden_count = self._load_rent_burdens(session, verbose)
                stats.dimensions_loaded["dim_rent_burden"] = burden_count

                commute_count = self._load_commute_modes(session, verbose)
                stats.dimensions_loaded["dim_commute_mode"] = commute_count

                poverty_count = self._load_poverty_categories(session, verbose)
                stats.dimensions_loaded["dim_poverty_category"] = poverty_count

                session.flush()

            # Phase 3: Iterate over years and race groups
            # Load fact tables for each year, then for each race within that year
            for year in census_years:
                if verbose:
                    print(f"\n{'=' * 60}")
                    print(f"Loading Census ACS 5-Year: {year}")
                    print(f"{'=' * 60}")

                # Create new API client for this year
                with self._client_scope(self._make_client(year)):
                    time_id = self._year_to_time_id[year]

                    # Load Total race first (base tables without race suffix)
                    race_id_total = self._race_code_to_id["T"]
                    if verbose:
                        print("  Loading base tables (race: Total)...")

                    for plan in self._iter_base_fact_plan(time_id, race_id_total):
                        fact_count = self._execute_fact_plan(
                            plan, session, state_fips_list, verbose, stats
                        )
                        if plan.kind == "spec":
                            assert plan.spec is not None
                            table_name: str = plan.spec.fact_class.__tablename__  # type: ignore[attr-defined]
                            stats.facts_loaded[table_name] = (
                                stats.facts_loaded.get(table_name, 0) + fact_count
                            )
                            stats.record_ingest(
                                f"census:{year}:T:{table_name}",
                                fact_count,
                            )
                            stats.api_calls += len(state_fips_list)
                        elif plan.kind == "hours":
                            stats.facts_loaded["fact_census_hours"] = (
                                stats.facts_loaded.get("fact_census_hours", 0) + fact_count
                            )
                            stats.record_ingest(
                                f"census:{year}:T:fact_census_hours",
                                fact_count,
                            )
                            stats.api_calls += len(state_fips_list)
                        else:
                            stats.facts_loaded["fact_census_income_sources"] = (
                                stats.facts_loaded.get("fact_census_income_sources", 0) + fact_count
                            )
                            stats.record_ingest(
                                f"census:{year}:T:fact_census_income_sources",
                                fact_count,
                            )
                            stats.api_calls += len(state_fips_list) * 3

                    # Load race-disaggregated data (A-I suffixed tables)
                    self._load_race_iterated_tables(
                        session, state_fips_list, time_id, stats, verbose, year
                    )

                    session.flush()

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.record_api_error(e, context="census:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _load_race_iterated_tables(
        self,
        session: Session,
        state_fips_list: list[str],
        time_id: int,
        stats: LoadStats,
        verbose: bool,
        year: int,
    ) -> None:
        """Load race-iterated fact tables for races A-I.

        For each race code, iterates through specs with race_suffixes and loads
        the race-suffixed table (e.g., B19001A for White alone).

        Args:
            session: SQLAlchemy session.
            state_fips_list: State FIPS codes to load.
            time_id: FK to dim_time.
            stats: LoadStats object to accumulate results.
            verbose: Whether to show progress.
            year: Census year for logging and breakdown keys.
        """
        current_race: str | None = None
        for plan in self._iter_race_fact_plan(time_id):
            if current_race != plan.race_code:
                if verbose:
                    print(
                        f"  Loading race-iterated tables for {plan.race_name} ({plan.race_code})..."
                    )
                current_race = plan.race_code

            try:
                fact_count = self._execute_fact_plan(plan, session, state_fips_list, False, stats)
                assert plan.spec is not None
                table_name: str = plan.spec.fact_class.__tablename__  # type: ignore[attr-defined]
                stats.facts_loaded[table_name] = stats.facts_loaded.get(table_name, 0) + fact_count
                stats.record_ingest(
                    f"census:{year}:{plan.race_code}:{table_name}",
                    fact_count,
                )
                stats.api_calls += len(state_fips_list)
            except Exception as e:
                # Some race-iterated tables may not exist for all races
                error_str = str(e).lower()
                if "unknown variable" not in error_str:
                    table_id = plan.spec.table_id if plan.spec else plan.kind
                    stats.record_api_error(
                        e,
                        context=f"census:{year}:{plan.race_code}:{table_id}",
                        details={
                            "loader": "census",
                            "operation": "race_iterated_table",
                            "table_id": table_id,
                            "race_code": plan.race_code,
                            "year": year,
                        },
                    )
                    stats.errors.append(f"{table_id}: {e}")

        self._log_race_table_skip_summary(year, stats)

    def _create_race_suffixed_spec(self, spec: FactTableSpec, race_code: str) -> FactTableSpec:
        """Create a race-suffixed FactTableSpec.

        Updates table_id, scalar_var, and var_mapping to use race suffix.

        Args:
            spec: Original FactTableSpec.
            race_code: Race code (A-I).

        Returns:
            New FactTableSpec with race-suffixed identifiers.
        """
        race_table_id = f"{spec.table_id}{race_code}"

        # Update scalar_var if present (e.g., B19013_001E -> B19013A_001E)
        new_scalar_var = spec.scalar_var
        if spec.scalar_var:
            new_scalar_var = spec.scalar_var.replace(spec.table_id, race_table_id)

        # Update var_mapping if present
        new_var_mapping = spec.var_mapping
        if spec.var_mapping:
            new_var_mapping = {
                var_code.replace(spec.table_id, race_table_id): dim_value
                for var_code, dim_value in spec.var_mapping.items()
            }

        return replace(
            spec,
            table_id=race_table_id,
            scalar_var=new_scalar_var,
            var_mapping=new_var_mapping,
        )

    # =========================================================================
    # DIMENSION LOADERS
    # =========================================================================

    def _load_data_source(self, session: Session, year: int) -> None:
        """Load data source dimension."""
        source_code = f"ACS5Y{year}_API"
        self._source_id = self._get_or_create_data_source(
            session,
            source_code=source_code,
            source_name=f"ACS 5-Year Estimates {year} (Census API)",
            source_year=year,
            source_agency="U.S. Census Bureau",
            coverage_start_year=year - 4,
            coverage_end_year=year,
        )

    def _load_genders(self, session: Session) -> None:
        """Load gender dimension (static values)."""
        genders = [
            ("total", "Total"),
            ("male", "Male"),
            ("female", "Female"),
        ]
        for code, label in genders:
            gender = DimGender(gender_code=code, gender_label=label)
            session.add(gender)
            session.flush()
            self._gender_to_id[code] = gender.gender_id

    def _load_races(self, session: Session) -> int:
        """Load race/ethnicity dimension (static, 10 records including Total).

        Populates DimRace with Census race codes following the A-I suffix scheme.

        Returns:
            Number of race records loaded.
        """
        for race_data in RACE_CODES:
            race = DimRace(
                race_code=str(race_data["code"]),
                race_name=str(race_data["name"]),
                race_short_name=str(race_data["short"]),
                is_hispanic_ethnicity=bool(race_data["hispanic"]),
                is_indigenous=bool(race_data["indigenous"]),
                display_order=int(race_data["order"]),  # type: ignore[call-overload]
            )
            session.add(race)
        session.flush()

        # Build lookup for fact loading
        self._race_code_to_id = {r.race_code: r.race_id for r in session.query(DimRace).all()}

        return len(RACE_CODES)

    def _load_time_dimension(self, session: Session) -> int:
        """Populate DimTime for all configured census years if not already present.

        Creates annual time records for each year in config.census_years, enabling
        multi-year Census data loading. Existing year records are reused.

        Returns:
            Number of time records created (newly added only).
        """
        existing_years = {t.year for t in session.query(DimTime).all()}
        new_count = 0

        for year in self.config.census_years:
            if year not in existing_years:
                time_record = DimTime(
                    year=year,
                    quarter=None,  # Annual data
                    month=None,
                    is_annual=True,
                )
                session.add(time_record)
                new_count += 1

        session.flush()

        # Build lookup for all census years (including existing)
        self._year_to_time_id = {
            t.year: t.time_id
            for t in session.query(DimTime).filter(DimTime.year.in_(self.config.census_years)).all()
        }

        return new_count

    def _load_states(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load state dimension from API."""
        assert self._client is not None

        existing_states = {state.state_fips: state for state in session.query(DimState).all()}
        states = self._client.get_all_states()
        count = 0

        for fips, name in states:
            if fips not in state_fips_list:
                continue

            existing = existing_states.get(fips)
            if existing:
                self._state_fips_to_id[fips] = existing.state_id
                if existing.state_name != name:
                    existing.state_name = name
                abbrev = STATE_ABBREVS.get(fips, fips)
                if existing.state_abbrev != abbrev:
                    existing.state_abbrev = abbrev
                continue

            abbrev = STATE_ABBREVS.get(fips, fips)
            state = DimState(
                state_fips=fips,
                state_name=name,
                state_abbrev=abbrev,
            )
            session.add(state)
            session.flush()
            self._state_fips_to_id[fips] = state.state_id
            count += 1

        if verbose:
            print(f"  Loaded {count} states")

        return count

    def _load_counties(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        stats: LoadStats | None = None,
    ) -> int:
        """Load county dimension from API."""
        assert self._client is not None

        existing_counties = {county.fips: county for county in session.query(DimCounty).all()}
        count = 0
        state_iter = tqdm(state_fips_list, desc="Counties", disable=not verbose)

        for state_fips in state_iter:
            state_id = self._state_fips_to_id.get(state_fips)
            if not state_id:
                continue

            try:
                data = self._client.get_county_data(
                    variables=["B19013_001E"],
                    state_fips=state_fips,
                )
            except CensusAPIError as exc:
                self._handle_api_error(
                    exc,
                    table_id="B19013_001E",
                    state_fips=state_fips,
                    operation="load_counties",
                    stats=stats,
                )
                continue
            except Exception as e:
                logger.warning("Failed to fetch counties for state %s: %s", state_fips, e)
                continue

            for county_data in data:
                # Parse county name
                name_parts = county_data.name.split(", ")
                county_name = name_parts[0] if name_parts else county_data.name

                existing = existing_counties.get(county_data.fips)
                if existing:
                    self._fips_to_county[county_data.fips] = existing.county_id
                    if existing.county_name != county_name:
                        existing.county_name = county_name
                    if existing.county_fips != county_data.county_fips:
                        existing.county_fips = county_data.county_fips
                    if existing.state_id != state_id:
                        existing.state_id = state_id
                    continue

                county = DimCounty(
                    fips=county_data.fips,
                    state_id=state_id,
                    county_fips=county_data.county_fips,
                    county_name=county_name,
                )
                session.add(county)
                session.flush()
                self._fips_to_county[county_data.fips] = county.county_id
                count += 1

        if verbose:
            print(f"  Loaded {count} counties")

        return count

    def _get_existing_metro_keys(self, session: Session) -> tuple[set[str], set[str]]:
        """Return existing CBSA codes and geo IDs for metro areas."""
        existing_metros = session.query(DimMetroArea).all()
        existing_cbsa = {m.cbsa_code for m in existing_metros if m.cbsa_code}
        existing_geo = {m.geo_id for m in existing_metros if m.geo_id}
        return existing_cbsa, existing_geo

    def _load_cbsa_metros(
        self,
        session: Session,
        cbsas: list[dict[str, str]],
        existing_cbsa: set[str],
        existing_geo: set[str],
    ) -> tuple[int, int, int]:
        """Insert CBSA metro areas and return counts."""
        new_cbsas = 0
        new_msas = 0
        new_micros = 0
        for cbsa in cbsas:
            geo_id = f"cbsa_{cbsa['cbsa_code']}"
            if cbsa["cbsa_code"] in existing_cbsa or geo_id in existing_geo:
                continue
            metro = DimMetroArea(
                geo_id=geo_id,
                cbsa_code=cbsa["cbsa_code"],
                metro_name=cbsa["metro_name"],
                area_type=cbsa["area_type"],
            )
            session.add(metro)
            new_cbsas += 1
            if cbsa["area_type"] == "msa":
                new_msas += 1
            elif cbsa["area_type"] == "micropolitan":
                new_micros += 1
        return new_cbsas, new_msas, new_micros

    def _load_csa_metros(
        self,
        session: Session,
        csas: list[dict[str, str]],
        existing_cbsa: set[str],
        existing_geo: set[str],
    ) -> int:
        """Insert CSA metro areas and return count."""
        new_csas = 0
        for csa in csas:
            geo_id = f"csa_{csa['cbsa_code']}"
            if csa["cbsa_code"] in existing_cbsa or geo_id in existing_geo:
                continue
            metro = DimMetroArea(
                geo_id=geo_id,
                cbsa_code=csa["cbsa_code"],
                metro_name=csa["metro_name"],
                area_type=csa["area_type"],
            )
            session.add(metro)
            new_csas += 1
        return new_csas

    def _build_metro_lookup(self, session: Session) -> dict[str, int]:
        """Build CBSA code to metro_area_id lookup."""
        return {
            m.cbsa_code: m.metro_area_id for m in session.query(DimMetroArea).all() if m.cbsa_code
        }

    def _load_metro_bridges(
        self,
        session: Session,
        mappings: list[dict[str, str | bool]],
        metro_lookup: dict[str, int],
        verbose: bool,
    ) -> int:
        """Load county-to-metro bridge mappings."""
        existing_bridges = {
            (bridge.county_id, bridge.metro_area_id)
            for bridge in session.query(BridgeCountyMetro).all()
        }
        bridge_count = 0

        for mapping in mappings:
            county_fips = str(mapping["county_fips"])
            cbsa_code = str(mapping["cbsa_code"])

            county_id = self._fips_to_county.get(county_fips)
            metro_id = metro_lookup.get(cbsa_code)

            if county_id and metro_id:
                if (county_id, metro_id) in existing_bridges:
                    continue
                bridge = BridgeCountyMetro(
                    county_id=county_id,
                    metro_area_id=metro_id,
                    is_principal_city=bool(mapping["is_principal_city"]),
                )
                session.add(bridge)
                bridge_count += 1

        session.flush()

        if verbose:
            print(f"    Created {bridge_count} county-to-metro mappings")

        return bridge_count

    def _load_metro_areas(self, session: Session, verbose: bool = True) -> tuple[int, int]:
        """Load metropolitan statistical areas from CBSA delineation file.

        Populates DimMetroArea with MSA, Micropolitan, and CSA areas, then
        creates BridgeCountyMetro mappings for county-to-metro aggregation.

        Requires counties to be loaded first (uses _fips_to_county lookup).

        Args:
            session: SQLAlchemy session.
            verbose: Whether to show progress.

        Returns:
            Tuple of (metro_count, bridge_count).
        """
        from babylon.data.census.cbsa_parser import (
            CBSA_EXCEL_PATH,
            get_county_metro_mappings,
            get_unique_cbsas,
            get_unique_csas,
            parse_cbsa_delineation,
        )

        if not CBSA_EXCEL_PATH.exists():
            if verbose:
                print(f"  CBSA delineation file not found at {CBSA_EXCEL_PATH}")
                print("  Skipping metro area loading (download from Census Bureau)")
            return (0, 0)

        if verbose:
            print("  Loading metropolitan statistical areas...")

        try:
            records = parse_cbsa_delineation(CBSA_EXCEL_PATH)
        except Exception as e:
            logger.warning(f"Failed to parse CBSA delineation file: {e}")
            return (0, 0)

        existing_cbsa, existing_geo = self._get_existing_metro_keys(session)

        # Load CBSAs (MSA and Micropolitan)
        cbsas = get_unique_cbsas(records)
        new_cbsas, new_msas, new_micros = self._load_cbsa_metros(
            session,
            cbsas,
            existing_cbsa,
            existing_geo,
        )

        # Load CSAs
        csas = get_unique_csas(records)
        new_csas = self._load_csa_metros(session, csas, existing_cbsa, existing_geo)

        session.flush()
        metro_count = new_cbsas + new_csas

        if verbose:
            print(f"    Loaded {new_cbsas} CBSAs ({new_msas} MSA, {new_micros} micropolitan)")
            print(f"    Loaded {new_csas} CSAs")

        # Build lookup for bridge table: cbsa_code -> metro_area_id
        metro_lookup = self._build_metro_lookup(session)

        # Load county-to-metro mappings
        if verbose:
            print("  Loading county-to-metro mappings...")

        mappings = get_county_metro_mappings(records)
        bridge_count = self._load_metro_bridges(session, mappings, metro_lookup, verbose)

        return (metro_count, bridge_count)

    def _load_income_brackets(self, session: Session, _verbose: bool) -> int:
        """Load income bracket dimension from B19001 metadata."""
        assert self._client is not None

        variables = self._fetch_variables("B19001")
        count = 0
        order = 1

        # Income bracket parsing patterns
        bracket_patterns = [
            (r"Less than \$10,000", 0, 9999),
            (r"\$10,000 to \$14,999", 10000, 14999),
            (r"\$15,000 to \$19,999", 15000, 19999),
            (r"\$20,000 to \$24,999", 20000, 24999),
            (r"\$25,000 to \$29,999", 25000, 29999),
            (r"\$30,000 to \$34,999", 30000, 34999),
            (r"\$35,000 to \$39,999", 35000, 39999),
            (r"\$40,000 to \$44,999", 40000, 44999),
            (r"\$45,000 to \$49,999", 45000, 49999),
            (r"\$50,000 to \$59,999", 50000, 59999),
            (r"\$60,000 to \$74,999", 60000, 74999),
            (r"\$75,000 to \$99,999", 75000, 99999),
            (r"\$100,000 to \$124,999", 100000, 124999),
            (r"\$125,000 to \$149,999", 125000, 149999),
            (r"\$150,000 to \$199,999", 150000, 199999),
            (r"\$200,000 or more", 200000, None),
        ]

        for var_code, var_info in sorted(variables.items()):
            # Skip total
            if var_code == "B19001_001E":
                continue

            bracket_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            # Find bracket bounds
            bracket_min = None
            bracket_max = None
            for pattern, min_val, max_val in bracket_patterns:
                if label and pattern in label:
                    bracket_min = min_val
                    bracket_max = max_val
                    break

            bracket = DimIncomeBracket(
                bracket_code=bracket_code,
                bracket_label=label or bracket_code,
                bracket_min_usd=bracket_min,
                bracket_max_usd=bracket_max,
                bracket_order=order,
            )
            session.add(bracket)
            order += 1
            count += 1

        return count

    def _load_employment_statuses(self, session: Session, _verbose: bool) -> int:
        """Load employment status dimension from B23025 metadata."""
        assert self._client is not None

        variables = self._fetch_variables("B23025")
        count = 0
        order = 1

        for var_code, var_info in sorted(variables.items()):
            status_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            # Determine labor force and employment flags
            is_labor_force = None
            is_employed = None
            if label:
                label_lower = label.lower()
                if "in labor force" in label_lower:
                    is_labor_force = True
                elif "not in labor force" in label_lower:
                    is_labor_force = False
                if "employed" in label_lower and "unemployed" not in label_lower:
                    is_employed = True
                elif "unemployed" in label_lower:
                    is_employed = False

            status = DimEmploymentStatus(
                status_code=status_code,
                status_label=label or status_code,
                is_labor_force=is_labor_force,
                is_employed=is_employed,
                status_order=order,
            )
            session.add(status)
            order += 1
            count += 1

        return count

    def _load_worker_classes(self, session: Session, _verbose: bool) -> int:
        """Load worker class dimension from B24080 metadata with Marxian mapping."""
        assert self._client is not None

        variables = self._fetch_variables("B24080")
        count = 0
        order = 1

        for var_code, var_info in sorted(variables.items()):
            class_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            # Apply Marxian classification
            marxian_class = classify_marxian_class(class_code, label or "")

            worker_class = DimWorkerClass(
                class_code=class_code,
                class_label=label or class_code,
                marxian_class=marxian_class,
                class_order=order,
            )
            session.add(worker_class)
            order += 1
            count += 1

        return count

    def _load_occupations(self, session: Session, _verbose: bool) -> int:
        """Load occupation dimension from C24010 metadata with labor type."""
        assert self._client is not None

        variables = self._fetch_variables("C24010")
        count = 0
        order = 1

        for var_code, var_info in sorted(variables.items()):
            occ_code = var_code.replace("E", "")
            label = var_info.label or ""
            occ_label = _parse_label(label)
            occ_category = _extract_occupation_category(label)

            # Apply labor type classification
            labor_type = classify_labor_type(occ_category)

            occupation = DimOccupation(
                occupation_code=occ_code,
                occupation_label=occ_label or occ_code,
                occupation_category=occ_category,
                labor_type=labor_type,
                occupation_order=order,
            )
            session.add(occupation)
            order += 1
            count += 1

        return count

    def _load_education_levels(self, session: Session, _verbose: bool) -> int:
        """Load education level dimension from B15003 metadata."""
        assert self._client is not None

        variables = self._fetch_variables("B15003")
        count = 0
        order = 1

        # Years of schooling mapping
        years_map = {
            "No schooling completed": 0,
            "Nursery school": 1,
            "Kindergarten": 1,
            "1st grade": 1,
            "2nd grade": 2,
            "3rd grade": 3,
            "4th grade": 4,
            "5th grade": 5,
            "6th grade": 6,
            "7th grade": 7,
            "8th grade": 8,
            "9th grade": 9,
            "10th grade": 10,
            "11th grade": 11,
            "12th grade, no diploma": 11,
            "Regular high school diploma": 12,
            "GED or alternative credential": 12,
            "Some college, less than 1 year": 13,
            "Some college, 1 or more years, no degree": 14,
            "Associate's degree": 14,
            "Bachelor's degree": 16,
            "Master's degree": 18,
            "Professional school degree": 19,
            "Doctorate degree": 21,
        }

        for var_code, var_info in sorted(variables.items()):
            level_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            years = None
            if label:
                for pattern, yrs in years_map.items():
                    if pattern.lower() in label.lower():
                        years = yrs
                        break

            level = DimEducationLevel(
                level_code=level_code,
                level_label=label or level_code,
                years_of_schooling=years,
                level_order=order,
            )
            session.add(level)
            order += 1
            count += 1

        return count

    def _load_housing_tenures(self, session: Session) -> int:
        """Load housing tenure dimension (static values)."""
        tenures = [
            ("total", "Total occupied housing units", False),
            ("owner", "Owner-occupied housing units", True),
            ("renter", "Renter-occupied housing units", False),
        ]
        for code, label, is_owner in tenures:
            tenure = DimHousingTenure(
                tenure_type=code,
                tenure_label=label,
                is_owner=is_owner,
            )
            session.add(tenure)

        return 3

    def _load_rent_burdens(self, session: Session, _verbose: bool) -> int:
        """Load rent burden dimension from B25070 metadata."""
        assert self._client is not None

        variables = self._fetch_variables("B25070")
        count = 0
        order = 1

        for var_code, var_info in sorted(variables.items()):
            # Skip total
            if var_code == "B25070_001E":
                continue

            bracket_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            # Apply rent burden classification
            is_burdened, is_severe = classify_rent_burden(label or "")

            # Parse burden percentage bounds
            burden_min = None
            burden_max = None
            if label:
                # Extract percentages from label like "30.0 to 34.9 percent"
                pct_match = re.search(r"(\d+\.?\d*)\s*(?:to|percent)", label)
                if pct_match:
                    burden_min = Decimal(pct_match.group(1))
                if "or more" in label.lower():
                    burden_max = None
                elif "Less than" in label:
                    burden_min = Decimal("0")
                    max_match = re.search(r"Less than (\d+\.?\d*)", label)
                    if max_match:
                        burden_max = Decimal(max_match.group(1))

            burden = DimRentBurden(
                bracket_code=bracket_code,
                burden_bracket=label or bracket_code,
                burden_min_pct=burden_min,
                burden_max_pct=burden_max,
                is_cost_burdened=is_burdened,
                is_severely_burdened=is_severe,
                bracket_order=order,
            )
            session.add(burden)
            order += 1
            count += 1

        return count

    def _load_commute_modes(self, session: Session, _verbose: bool) -> int:
        """Load commute mode dimension from B08301 metadata."""
        assert self._client is not None

        variables = self._fetch_variables("B08301")
        count = 0
        order = 1

        public_transit_keywords = {"bus", "subway", "streetcar", "railroad", "ferryboat"}
        active_transport_keywords = {"walked", "bicycle"}

        for var_code, var_info in sorted(variables.items()):
            mode_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            is_public = None
            is_active = None
            if label:
                label_lower = label.lower()
                if any(kw in label_lower for kw in public_transit_keywords):
                    is_public = True
                if any(kw in label_lower for kw in active_transport_keywords):
                    is_active = True

            mode = DimCommuteMode(
                mode_code=mode_code,
                mode_label=label or mode_code,
                is_public_transit=is_public,
                is_active_transport=is_active,
                mode_order=order,
            )
            session.add(mode)
            order += 1
            count += 1

        return count

    def _load_poverty_categories(self, session: Session, _verbose: bool) -> int:
        """Load poverty category dimension from B17001 metadata."""
        assert self._client is not None

        variables = self._fetch_variables("B17001")
        count = 0
        order = 1

        for var_code, var_info in sorted(variables.items()):
            category_code = var_code.replace("E", "")
            label = _parse_label(var_info.label)

            is_below = None
            if label:
                label_lower = label.lower()
                if "below poverty" in label_lower:
                    is_below = True
                elif "at or above poverty" in label_lower:
                    is_below = False

            category = DimPovertyCategory(
                category_code=category_code,
                category_label=label or category_code,
                is_below_poverty=is_below,
                category_order=order,
            )
            session.add(category)
            order += 1
            count += 1

        return count

    # =========================================================================
    # GENERIC FACT TABLE LOADER
    # =========================================================================

    def _build_fact_kwargs(
        self,
        spec: FactTableSpec,
        county_id: int,
        time_id: int,
        race_id: int,
        value: int | float,
        dim_id: int | None = None,
        gender_id: int | None = None,
    ) -> dict[str, Any]:
        """Build kwargs dict for fact class instantiation.

        Constructs the parameters needed to create a fact record, including
        optional dimension FK and type-converted value field.

        Args:
            spec: Fact table specification.
            county_id: FK to dim_county.
            time_id: FK to dim_time.
            race_id: FK to dim_race.
            value: The measure value to store.
            dim_id: Optional FK to the primary dimension.
            gender_id: Optional FK to dim_gender.

        Returns:
            Dict of kwargs for fact class constructor.
        """
        kwargs: dict[str, Any] = {
            "county_id": county_id,
            "source_id": self._source_id,
            "time_id": time_id,
            "race_id": race_id,
        }

        # Add dimension FK if specified
        if dim_id is not None and spec.fact_dim_attr:
            kwargs[spec.fact_dim_attr] = dim_id

        # Add gender FK if specified
        if gender_id is not None:
            kwargs["gender_id"] = gender_id

        # Add value field with type conversion
        if spec.value_type == "decimal":
            kwargs[spec.value_field] = Decimal(str(value))
        else:
            kwargs[spec.value_field] = int(value)

        return kwargs

    def _write_rows(
        self,
        session: Session,
        model: type,
        rows: Iterable[dict[str, Any]],
    ) -> int:
        """Persist rows to the session using ORM models."""
        writer = BatchWriter(session, self.config.batch_size)
        return writer.write(model, rows)

    def _build_dimension_map(self, spec: FactTableSpec, session: Session) -> dict[str, int]:
        """Build mapping from dimension code to dimension ID for a fact spec."""
        dim_map: dict[str, int] = {}
        if not spec.dim_class or not spec.fact_dim_attr:
            return dim_map

        dims: list[Any] = session.query(spec.dim_class).all()
        for dim in dims:
            code = getattr(dim, spec.dim_code_attr)
            # fact_dim_attr is the FK column name on fact table AND
            # the PK column name on the dimension table (they always match)
            dim_map[code] = getattr(dim, spec.fact_dim_attr)
        return dim_map

    def _build_fact_rows_for_county(
        self,
        spec: FactTableSpec,
        county_id: int,
        county_values: dict[str, int | float | None],
        dim_map: dict[str, int],
        variables: dict[str, Any],
        time_id: int,
        race_id: int,
    ) -> list[dict[str, Any]]:
        """Build fact rows for a single county.

        Dispatches to the appropriate pattern based on spec configuration.
        """
        rows: list[dict[str, Any]] = []

        # Pattern B: Scalar value (single variable per county)
        if spec.scalar_var:
            value = county_values.get(spec.scalar_var)
            if value is not None:
                rows.append(self._build_fact_kwargs(spec, county_id, time_id, race_id, value))
            return rows

        # Pattern E: Hardcoded variable mapping
        if spec.var_mapping:
            for var_code, dim_value in spec.var_mapping.items():
                value = county_values.get(var_code)
                if value is None:
                    continue
                dim_id = dim_map.get(dim_value)
                if dim_id:
                    rows.append(
                        self._build_fact_kwargs(spec, county_id, time_id, race_id, value, dim_id)
                    )
            return rows

        # Pattern A/C: Dimension-iterated
        for var_code, value in county_values.items():
            if spec.skip_total and var_code.endswith("_001E"):
                continue
            if value is None:
                continue

            dim_code = var_code.replace("E", "")

            # For race-suffixed tables (e.g., B19001A), normalize dim_code to
            # match base dimension codes (e.g., "B19001A_002" -> "B19001_002")
            table_id = spec.table_id
            if table_id and len(table_id) > 1 and table_id[-1] in "ABCDEFGHI":
                base_table_id = table_id[:-1]
                dim_code = dim_code.replace(table_id, base_table_id)

            dim_id = dim_map.get(dim_code)
            if not dim_id:
                continue

            gender_id = None
            if spec.extract_gender:
                var_info = variables.get(var_code)
                gender = _extract_gender(var_info.label if var_info else "")
                gender_id = self._gender_to_id.get(gender, self._gender_to_id["total"])

            rows.append(
                self._build_fact_kwargs(spec, county_id, time_id, race_id, value, dim_id, gender_id)
            )

        return rows

    def _prepare_fact_variables(
        self,
        spec: FactTableSpec,
        year: int,
        stats: LoadStats | None,
    ) -> tuple[dict[str, VariableMetadata], bool] | None:
        """Resolve variable metadata needed for a fact table load."""
        if self._is_race_suffixed_table(spec.table_id):
            variables, use_variable_fallback = self._get_variables_for_table(spec.table_id, year)
            if not variables:
                return None
            return variables, use_variable_fallback

        if spec.extract_gender:
            variables, _ = self._get_variables_for_table(spec.table_id, year)
            if not variables:
                self._record_missing_table(
                    year,
                    spec.table_id,
                    reason="variable_metadata_missing",
                    stats=stats,
                )
                return None
            return variables, False

        return {}, False

    def _should_skip_race_state(self, year: int, base_table_id: str, state_fips: str) -> bool:
        """Return True if race tables should skip the current state."""
        if self._is_table_missing(year, base_table_id):
            self._record_race_table_skip(year, base_table_id, state_fips)
            return True
        if self._is_base_table_missing(year, base_table_id, state_fips):
            self._record_race_table_skip(year, base_table_id, state_fips)
            return True
        return False

    def _fetch_fact_data_for_state(
        self,
        spec: FactTableSpec,
        state_fips: str,
        variables: dict[str, VariableMetadata],
        use_variable_fallback: bool,
        stats: LoadStats | None,
    ) -> list[CountyData] | None:
        """Fetch fact data for a table/state with fallback handling."""
        try:
            if use_variable_fallback:
                return self._fetch_county_data_chunked(list(variables.keys()), state_fips)
            data = self._fetch_table_data(spec.table_id, state_fips)
            if data or not self._is_race_suffixed_table(spec.table_id) or not variables:
                return data
            return self._fetch_county_data_chunked(list(variables.keys()), state_fips)
        except CensusAPIError as exc:
            self._handle_api_error(
                exc,
                table_id=spec.table_id,
                state_fips=state_fips,
                operation="fact_table",
                stats=stats,
            )
            return None

    def _load_fact_table(
        self,
        spec: FactTableSpec,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        time_id: int,
        race_id: int,
        stats: LoadStats | None = None,
    ) -> int:
        """Generic fact table loader driven by FactTableSpec configuration.

        Args:
            spec: Fact table specification.
            session: SQLAlchemy session.
            state_fips_list: List of state FIPS codes to load.
            verbose: Whether to show progress bar.
            time_id: FK to dim_time for this load.
            race_id: FK to dim_race for this load.

        Returns:
            Count of fact records created.
        """
        assert self._client is not None
        assert self._source_id is not None
        year = self._client.year

        race_table = self._is_race_suffixed_table(spec.table_id)
        base_table_id = self._base_table_id(spec.table_id) if race_table else None
        if race_table and base_table_id and self._is_race_tables_unavailable(year, base_table_id):
            return 0

        dim_map = self._build_dimension_map(spec, session)
        count = 0
        state_iter = tqdm(state_fips_list, desc=spec.label, disable=not verbose)
        variable_payload = self._prepare_fact_variables(spec, year, stats)
        if variable_payload is None:
            return 0
        variables, use_variable_fallback = variable_payload

        for state_fips in state_iter:
            if self._is_table_missing(year, spec.table_id):
                break
            if (
                race_table
                and base_table_id
                and self._should_skip_race_state(
                    year,
                    base_table_id,
                    state_fips,
                )
            ):
                continue

            data = self._fetch_fact_data_for_state(
                spec,
                state_fips,
                variables,
                use_variable_fallback,
                stats,
            )
            if data is None:
                continue

            if not data and not race_table:
                self._record_base_table_missing(year, spec.table_id, state_fips)
                continue

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                rows = self._build_fact_rows_for_county(
                    spec,
                    county_id,
                    county_data.values,
                    dim_map,
                    variables,
                    time_id,
                    race_id,
                )
                count += self._write_rows(session, spec.fact_class, rows)

            session.flush()

        return count

    # =========================================================================
    # SPECIAL CASE FACT LOADERS (Pattern D and F)
    # =========================================================================

    def _build_hours_rows_for_county(
        self,
        county_id: int,
        county_values: dict[str, int | float | None],
        variables: dict[str, Any],
        time_id: int,
        race_id: int,
    ) -> list[dict[str, Any]]:
        """Build fact rows for the B23020 hours table for a single county."""
        gender_data: dict[str, dict[str, Decimal | None]] = {
            "total": {"aggregate": None, "mean": None},
            "male": {"aggregate": None, "mean": None},
            "female": {"aggregate": None, "mean": None},
        }

        for var_code, value in county_values.items():
            if value is None:
                continue

            var_info = variables.get(var_code)
            label = var_info.label if var_info else ""
            gender = _extract_gender(label)

            if "Aggregate" in label:
                gender_data[gender]["aggregate"] = Decimal(str(value))
            elif "Mean" in label:
                gender_data[gender]["mean"] = Decimal(str(value))

        rows: list[dict[str, Any]] = []
        for gender, values in gender_data.items():
            if values["aggregate"] is None and values["mean"] is None:
                continue

            gender_id = self._gender_to_id.get(gender, self._gender_to_id["total"])
            rows.append(
                {
                    "county_id": county_id,
                    "source_id": self._source_id,
                    "gender_id": gender_id,
                    "time_id": time_id,
                    "race_id": race_id,
                    "aggregate_hours": values["aggregate"],
                    "mean_hours": values["mean"],
                }
            )

        return rows

    def _load_fact_hours(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        time_id: int,
        race_id: int,
        stats: LoadStats | None = None,
    ) -> int:
        """Load B23020 hours worked facts (Pattern D: gender-grouped aggregation).

        This loader uses a special pattern that groups values by gender and
        creates 3 facts per county (total, male, female) with aggregate/mean values.
        Cannot be handled by the generic loader.

        Args:
            session: SQLAlchemy session.
            state_fips_list: List of state FIPS codes.
            verbose: Whether to show progress.
            time_id: FK to dim_time.
            race_id: FK to dim_race.

        Returns:
            Count of fact records created.
        """
        assert self._client is not None
        assert self._source_id is not None

        count = 0
        state_iter = tqdm(state_fips_list, desc="B23020", disable=not verbose)

        for state_fips in state_iter:
            try:
                variables = self._fetch_variables("B23020")
                data = self._fetch_table_data("B23020", state_fips)
            except CensusAPIError as exc:
                self._handle_api_error(
                    exc,
                    table_id="B23020",
                    state_fips=state_fips,
                    operation="fact_hours",
                    stats=stats,
                )
                continue

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                rows = self._build_hours_rows_for_county(
                    county_id,
                    county_data.values,
                    variables,
                    time_id,
                    race_id,
                )
                count += self._write_rows(session, FactCensusHours, rows)

            session.flush()

        return count

    def _build_income_sources_row(
        self,
        county_id: int,
        wage_vals: dict[str, int | float | None],
        self_emp_vals: dict[str, int | float | None],
        invest_vals: dict[str, int | float | None],
        time_id: int,
        race_id: int,
    ) -> dict[str, Any]:
        """Build a fact row for income sources (B19052/B19053/B19054)."""
        return {
            "county_id": county_id,
            "source_id": self._source_id,
            "time_id": time_id,
            "race_id": race_id,
            "total_households": _safe_int(wage_vals.get("B19052_001E")),
            "with_wage_income": _safe_int(wage_vals.get("B19052_002E")),
            "with_self_employment_income": _safe_int(self_emp_vals.get("B19053_002E")),
            "with_investment_income": _safe_int(invest_vals.get("B19054_002E")),
        }

    def _load_fact_income_sources(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        time_id: int,
        race_id: int,
        stats: LoadStats | None = None,
    ) -> int:
        """Load B19052/B19053/B19054 income sources facts (Pattern F: multi-table join).

        This loader fetches 3 separate Census tables and joins them by FIPS code
        to create a single fact record with nullable fields from each table.
        Cannot be handled by the generic loader.

        Args:
            session: SQLAlchemy session.
            state_fips_list: List of state FIPS codes.
            verbose: Whether to show progress.
            time_id: FK to dim_time.
            race_id: FK to dim_race.

        Returns:
            Count of fact records created.
        """
        assert self._client is not None
        assert self._source_id is not None

        count = 0
        state_iter = tqdm(state_fips_list, desc="Income Sources", disable=not verbose)

        for state_fips in state_iter:
            try:
                # Fetch all three tables
                wage_data = self._fetch_table_data("B19052", state_fips)
                self_emp_data = self._fetch_table_data("B19053", state_fips)
                invest_data = self._fetch_table_data("B19054", state_fips)
            except CensusAPIError as exc:
                self._handle_api_error(
                    exc,
                    table_id="B19052/B19053/B19054",
                    state_fips=state_fips,
                    operation="fact_income_sources",
                    stats=stats,
                )
                continue

            # Build lookup by FIPS
            wage_by_fips = {d.fips: d.values for d in wage_data}
            self_emp_by_fips = {d.fips: d.values for d in self_emp_data}
            invest_by_fips = {d.fips: d.values for d in invest_data}

            # Get all FIPS from any table
            all_fips = (
                set(wage_by_fips.keys()) | set(self_emp_by_fips.keys()) | set(invest_by_fips.keys())
            )

            for fips in all_fips:
                county_id = self._fips_to_county.get(fips)
                if not county_id:
                    continue

                wage_vals = wage_by_fips.get(fips, {})
                self_emp_vals = self_emp_by_fips.get(fips, {})
                invest_vals = invest_by_fips.get(fips, {})

                row = self._build_income_sources_row(
                    county_id,
                    wage_vals,
                    self_emp_vals,
                    invest_vals,
                    time_id,
                    race_id,
                )
                count += self._write_rows(session, FactCensusIncomeSources, [row])

            session.flush()

        return count


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _parse_label(label: str) -> str | None:
    """Parse Census label to extract clean label text."""
    if not label:
        return None

    # Remove "Estimate!!" prefix
    clean = label.replace("Estimate!!", "").replace("Margin of Error!!", "")

    # Get last meaningful part
    parts = clean.split("!!")
    if parts:
        return parts[-1].strip().rstrip(":")

    return None


def _extract_gender(label: str) -> str:
    """Extract gender from Census label."""
    if "!!Male:" in label or "!!Male!!" in label:
        return "male"
    elif "!!Female:" in label or "!!Female!!" in label:
        return "female"
    return "total"


def _extract_occupation_category(label: str) -> str | None:
    """Extract top-level occupation category from label."""
    cat_match = re.search(r"!!(Management|Service|Sales|Natural|Production)[^!]+:", label)
    if cat_match:
        parts = label.split("!!")
        for part in parts:
            if part.startswith(cat_match.group(1)):
                return part.rstrip(":")
    return None


def _safe_int(value: int | float | None) -> int | None:
    """Safely convert value to int."""
    if value is None:
        return None
    return int(value)


__all__ = [
    "CensusLoader",
    "ALL_TABLES",
    "ORIGINAL_TABLES",
    "MARXIAN_TABLES",
]
