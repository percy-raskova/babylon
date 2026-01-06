"""Census data loader for direct 3NF schema population.

Loads ACS 5-Year Estimates directly from Census Bureau API into the normalized
3NF schema (marxist-data-3NF.sqlite), bypassing the intermediate research.sqlite.

This loader:
- Uses LoaderConfig for parameterized temporal/geographic/operational settings
- Applies Marxian classifications inline during load
- Uses DELETE+INSERT pattern for idempotency
- Writes to 14 census fact tables and supporting dimensions

Usage:
    from babylon.data.census.loader_3nf import CensusLoader
    from babylon.data import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session_factory

    config = LoaderConfig(census_years=[2022], state_fips_list=["06"])  # CA only
    loader = CensusLoader(config)

    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
        print(stats)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.census.api_client import CensusAPIClient
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.classifications import (
    classify_labor_type,
    classify_marxian_class,
    classify_rent_burden,
)
from babylon.data.normalize.schema import (
    DimCommuteMode,
    DimCounty,
    DimDataSource,
    DimEducationLevel,
    DimEmploymentStatus,
    DimGender,
    DimHousingTenure,
    DimIncomeBracket,
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


class CensusLoader(DataLoader):
    """Loader for Census ACS data into 3NF schema.

    Fetches ACS 5-Year Estimates from Census Bureau API and loads directly
    into the normalized 3NF schema with Marxian classifications applied inline.

    Attributes:
        config: LoaderConfig controlling year, geographic scope, and operations.

    Example:
        config = LoaderConfig(census_years=[2022], state_fips_list=["06", "36"])
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

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates.

        Order matters for FK constraints: child tables must be listed before
        parent tables they reference (e.g., DimCounty before DimState).
        """
        return [
            # Shared dimensions - order respects FK dependencies
            DimCounty,  # References DimState, must be deleted first
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
        census_years = self.config.census_years
        state_fips_list = self.config.state_fips_list or DEFAULT_STATE_FIPS

        # Use first year for dimensions that need API metadata
        initial_year = census_years[0] if census_years else 2022

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
            self._client = CensusAPIClient(year=initial_year)

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
                print(f"  Loaded {time_count} new time records ({len(census_years)} total years)")

            state_count = self._load_states(session, state_fips_list, verbose)
            stats.dimensions_loaded["dim_state"] = state_count

            county_count = self._load_counties(session, state_fips_list, verbose)
            stats.dimensions_loaded["dim_county"] = county_count

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
                self._client = CensusAPIClient(year=year)
                time_id = self._year_to_time_id[year]

                # Load Total race first (base tables without race suffix)
                race_id_total = self._race_code_to_id["T"]
                if verbose:
                    print("  Loading base tables (race: Total)...")

                for spec in FACT_TABLE_SPECS:
                    fact_count = self._load_fact_table(
                        spec, session, state_fips_list, verbose, time_id, race_id_total
                    )
                    table_name: str = spec.fact_class.__tablename__  # type: ignore[attr-defined]
                    stats.facts_loaded[table_name] = (
                        stats.facts_loaded.get(table_name, 0) + fact_count
                    )
                    stats.api_calls += len(state_fips_list)

                # Load special case fact tables for Total race
                hours_count = self._load_fact_hours(
                    session, state_fips_list, verbose, time_id, race_id_total
                )
                stats.facts_loaded["fact_census_hours"] = (
                    stats.facts_loaded.get("fact_census_hours", 0) + hours_count
                )
                stats.api_calls += len(state_fips_list)

                sources_count = self._load_fact_income_sources(
                    session, state_fips_list, verbose, time_id, race_id_total
                )
                stats.facts_loaded["fact_census_income_sources"] = (
                    stats.facts_loaded.get("fact_census_income_sources", 0) + sources_count
                )
                stats.api_calls += len(state_fips_list) * 3

                # Load race-disaggregated data (A-I suffixed tables)
                self._load_race_iterated_tables(session, state_fips_list, time_id, stats, verbose)

                session.flush()

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

    def _load_race_iterated_tables(
        self,
        session: Session,
        state_fips_list: list[str],
        time_id: int,
        stats: LoadStats,
        verbose: bool,
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
        """
        for race_data in RACE_CODES[1:]:  # Skip "T" (Total) - already loaded
            race_code = str(race_data["code"])
            race_id = self._race_code_to_id[race_code]
            race_name = str(race_data["short"])

            if verbose:
                print(f"  Loading race-iterated tables for {race_name} ({race_code})...")

            for spec in FACT_TABLE_SPECS:
                # Skip tables without race iterations
                if race_code not in spec.race_suffixes:
                    continue

                race_spec = self._create_race_suffixed_spec(spec, race_code)

                try:
                    fact_count = self._load_fact_table(
                        race_spec, session, state_fips_list, False, time_id, race_id
                    )
                    table_name: str = spec.fact_class.__tablename__  # type: ignore[attr-defined]
                    stats.facts_loaded[table_name] = (
                        stats.facts_loaded.get(table_name, 0) + fact_count
                    )
                    stats.api_calls += len(state_fips_list)
                except Exception as e:
                    # Some race-iterated tables may not exist for all races
                    error_str = str(e).lower()
                    if "unknown variable" not in error_str:
                        stats.errors.append(f"{race_spec.table_id}: {e}")

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
        source = DimDataSource(
            source_code=source_code,
            source_name=f"ACS 5-Year Estimates {year} (Census API)",
            source_year=year,
            source_agency="U.S. Census Bureau",
            coverage_start_year=year - 4,
            coverage_end_year=year,
        )
        session.add(source)
        session.flush()
        self._source_id = source.source_id

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

        states = self._client.get_all_states()
        count = 0

        for fips, name in states:
            if fips not in state_fips_list:
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
    ) -> int:
        """Load county dimension from API."""
        assert self._client is not None

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
            except Exception as e:
                logger.warning(f"Failed to fetch counties for state {state_fips}: {e}")
                continue

            for county_data in data:
                # Parse county name
                name_parts = county_data.name.split(", ")
                county_name = name_parts[0] if name_parts else county_data.name

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

    def _load_income_brackets(self, session: Session, _verbose: bool) -> int:
        """Load income bracket dimension from B19001 metadata."""
        assert self._client is not None

        variables = self._client.get_variables("B19001")
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

        variables = self._client.get_variables("B23025")
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

        variables = self._client.get_variables("B24080")
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

        variables = self._client.get_variables("C24010")
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

        variables = self._client.get_variables("B15003")
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

        variables = self._client.get_variables("B25070")
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

        variables = self._client.get_variables("B08301")
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

        variables = self._client.get_variables("B17001")
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

    def _process_county_facts(
        self,
        spec: FactTableSpec,
        session: Session,
        county_id: int,
        county_values: dict[str, int | float | None],
        dim_map: dict[str, int],
        variables: dict[str, Any],
        time_id: int,
        race_id: int,
    ) -> int:
        """Process and create fact records for a single county.

        Dispatches to the appropriate pattern based on spec configuration.
        """
        count = 0

        # Pattern B: Scalar value (single variable per county)
        if spec.scalar_var:
            value = county_values.get(spec.scalar_var)
            if value is not None:
                kwargs = self._build_fact_kwargs(spec, county_id, time_id, race_id, value)
                session.add(spec.fact_class(**kwargs))
                count += 1
            return count

        # Pattern E: Hardcoded variable mapping
        if spec.var_mapping:
            for var_code, dim_value in spec.var_mapping.items():
                value = county_values.get(var_code)
                if value is None:
                    continue
                dim_id = dim_map.get(dim_value)
                if dim_id:
                    kwargs = self._build_fact_kwargs(
                        spec, county_id, time_id, race_id, value, dim_id
                    )
                    session.add(spec.fact_class(**kwargs))
                    count += 1
            return count

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

            kwargs = self._build_fact_kwargs(
                spec, county_id, time_id, race_id, value, dim_id, gender_id
            )
            session.add(spec.fact_class(**kwargs))
            count += 1

        return count

    def _load_fact_table(
        self,
        spec: FactTableSpec,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        time_id: int,
        race_id: int,
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

        dim_map = self._build_dimension_map(spec, session)
        count = 0
        state_iter = tqdm(state_fips_list, desc=spec.label, disable=not verbose)

        for state_fips in state_iter:
            variables: dict[str, Any] = {}
            if spec.extract_gender:
                variables = self._client.get_variables(spec.table_id)

            data = self._client.get_table_data(spec.table_id, state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                count += self._process_county_facts(
                    spec,
                    session,
                    county_id,
                    county_data.values,
                    dim_map,
                    variables,
                    time_id,
                    race_id,
                )

            session.flush()

        return count

    # =========================================================================
    # SPECIAL CASE FACT LOADERS (Pattern D and F)
    # =========================================================================

    def _load_fact_hours(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        time_id: int,
        race_id: int,
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
            variables = self._client.get_variables("B23020")
            data = self._client.get_table_data("B23020", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                # Group by gender
                gender_data: dict[str, dict[str, Decimal | None]] = {
                    "total": {"aggregate": None, "mean": None},
                    "male": {"aggregate": None, "mean": None},
                    "female": {"aggregate": None, "mean": None},
                }

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    var_info = variables.get(var_code)
                    label = var_info.label if var_info else ""
                    gender = _extract_gender(label)

                    if "Aggregate" in label:
                        gender_data[gender]["aggregate"] = Decimal(str(value))
                    elif "Mean" in label:
                        gender_data[gender]["mean"] = Decimal(str(value))

                for gender, values in gender_data.items():
                    if values["aggregate"] is None and values["mean"] is None:
                        continue

                    gender_id = self._gender_to_id.get(gender, self._gender_to_id["total"])

                    fact = FactCensusHours(
                        county_id=county_id,
                        source_id=self._source_id,
                        gender_id=gender_id,
                        time_id=time_id,
                        race_id=race_id,
                        aggregate_hours=values["aggregate"],
                        mean_hours=values["mean"],
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_income_sources(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
        time_id: int,
        race_id: int,
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
            # Fetch all three tables
            wage_data = self._client.get_table_data("B19052", state_fips=state_fips)
            self_emp_data = self._client.get_table_data("B19053", state_fips=state_fips)
            invest_data = self._client.get_table_data("B19054", state_fips=state_fips)

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

                fact = FactCensusIncomeSources(
                    county_id=county_id,
                    source_id=self._source_id,
                    time_id=time_id,
                    race_id=race_id,
                    total_households=_safe_int(wage_vals.get("B19052_001E")),
                    with_wage_income=_safe_int(wage_vals.get("B19052_002E")),
                    with_self_employment_income=_safe_int(self_emp_vals.get("B19053_002E")),
                    with_investment_income=_safe_int(invest_vals.get("B19054_002E")),
                )
                session.add(fact)
                count += 1

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
