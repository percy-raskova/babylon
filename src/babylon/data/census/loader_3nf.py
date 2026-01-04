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

    config = LoaderConfig(census_year=2022, state_fips_list=["06"])  # CA only
    loader = CensusLoader(config)

    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
        print(stats)
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import TYPE_CHECKING

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
    DimRentBurden,
    DimState,
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
        config = LoaderConfig(census_year=2022, state_fips_list=["06", "36"])
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
        self._source_id: int | None = None

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [
            DimState,
            DimCounty,
            DimDataSource,
            DimGender,
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

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing census data before loading.
            verbose: If True, print progress information.
            **kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="census")
        year = self.config.census_year
        state_fips_list = self.config.state_fips_list or DEFAULT_STATE_FIPS

        if verbose:
            print(f"Loading ACS {year} 5-Year Estimates from Census API")
            print(f"States: {len(state_fips_list)} ({', '.join(state_fips_list[:5])}...)")

        try:
            # Create API client
            self._client = CensusAPIClient(year=year)

            # Clear existing data if reset
            if reset:
                if verbose:
                    print("Clearing existing census data...")
                self.clear_tables(session)
                session.flush()

            # Load dimensions first
            self._load_data_source(session, year)
            stats.dimensions_loaded["dim_data_source"] = 1

            self._load_genders(session)
            stats.dimensions_loaded["dim_gender"] = 3

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

            # Load fact tables
            income_count = self._load_fact_income(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_income"] = income_count
            stats.api_calls += len(state_fips_list)

            median_count = self._load_fact_median_income(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_median_income"] = median_count
            stats.api_calls += len(state_fips_list)

            emp_count = self._load_fact_employment(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_employment"] = emp_count
            stats.api_calls += len(state_fips_list)

            worker_count = self._load_fact_worker_class(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_worker_class"] = worker_count
            stats.api_calls += len(state_fips_list)

            occ_fact_count = self._load_fact_occupation(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_occupation"] = occ_fact_count
            stats.api_calls += len(state_fips_list)

            hours_count = self._load_fact_hours(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_hours"] = hours_count
            stats.api_calls += len(state_fips_list)

            housing_count = self._load_fact_housing(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_housing"] = housing_count
            stats.api_calls += len(state_fips_list)

            rent_count = self._load_fact_rent(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_rent"] = rent_count
            stats.api_calls += len(state_fips_list)

            burden_fact_count = self._load_fact_rent_burden(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_rent_burden"] = burden_fact_count
            stats.api_calls += len(state_fips_list)

            edu_fact_count = self._load_fact_education(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_education"] = edu_fact_count
            stats.api_calls += len(state_fips_list)

            gini_count = self._load_fact_gini(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_gini"] = gini_count
            stats.api_calls += len(state_fips_list)

            commute_fact_count = self._load_fact_commute(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_commute"] = commute_fact_count
            stats.api_calls += len(state_fips_list)

            poverty_fact_count = self._load_fact_poverty(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_poverty"] = poverty_fact_count
            stats.api_calls += len(state_fips_list)

            sources_count = self._load_fact_income_sources(session, state_fips_list, verbose)
            stats.facts_loaded["fact_census_income_sources"] = sources_count
            stats.api_calls += len(state_fips_list) * 3  # B19052, B19053, B19054

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
    # FACT TABLE LOADERS
    # =========================================================================

    def _load_fact_income(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B19001 income distribution facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get bracket_code -> bracket_id mapping
        brackets = session.query(DimIncomeBracket).all()
        bracket_map = {b.bracket_code: b.bracket_id for b in brackets}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B19001", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B19001", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    # Skip total
                    if var_code == "B19001_001E":
                        continue
                    if value is None:
                        continue

                    bracket_code = var_code.replace("E", "")
                    bracket_id = bracket_map.get(bracket_code)
                    if not bracket_id:
                        continue

                    fact = FactCensusIncome(
                        county_id=county_id,
                        source_id=self._source_id,
                        bracket_id=bracket_id,
                        household_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_median_income(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B19013 median income facts."""
        assert self._client is not None
        assert self._source_id is not None

        count = 0
        state_iter = tqdm(state_fips_list, desc="B19013", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B19013", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                value = county_data.values.get("B19013_001E")
                if value is None:
                    continue

                fact = FactCensusMedianIncome(
                    county_id=county_id,
                    source_id=self._source_id,
                    median_income_usd=Decimal(str(value)),
                )
                session.add(fact)
                count += 1

            session.flush()

        return count

    def _load_fact_employment(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B23025 employment status facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get status_code -> status_id mapping
        statuses = session.query(DimEmploymentStatus).all()
        status_map = {s.status_code: s.status_id for s in statuses}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B23025", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B23025", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    status_code = var_code.replace("E", "")
                    status_id = status_map.get(status_code)
                    if not status_id:
                        continue

                    fact = FactCensusEmployment(
                        county_id=county_id,
                        source_id=self._source_id,
                        status_id=status_id,
                        person_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_worker_class(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B24080 worker class facts with gender breakdown."""
        assert self._client is not None
        assert self._source_id is not None

        # Get class_code -> class_id mapping
        classes = session.query(DimWorkerClass).all()
        class_map = {c.class_code: c.class_id for c in classes}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B24080", disable=not verbose)

        for state_fips in state_iter:
            variables = self._client.get_variables("B24080")
            data = self._client.get_table_data("B24080", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    class_code = var_code.replace("E", "")
                    class_id = class_map.get(class_code)
                    if not class_id:
                        continue

                    # Determine gender from variable metadata
                    var_info = variables.get(var_code)
                    gender = _extract_gender(var_info.label if var_info else "")
                    gender_id = self._gender_to_id.get(gender, self._gender_to_id["total"])

                    fact = FactCensusWorkerClass(
                        county_id=county_id,
                        source_id=self._source_id,
                        gender_id=gender_id,
                        class_id=class_id,
                        worker_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_occupation(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load C24010 occupation facts with gender breakdown."""
        assert self._client is not None
        assert self._source_id is not None

        # Get occupation_code -> occupation_id mapping
        occupations = session.query(DimOccupation).all()
        occ_map = {o.occupation_code: o.occupation_id for o in occupations}

        count = 0
        state_iter = tqdm(state_fips_list, desc="C24010", disable=not verbose)

        for state_fips in state_iter:
            variables = self._client.get_variables("C24010")
            data = self._client.get_table_data("C24010", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    occ_code = var_code.replace("E", "")
                    occ_id = occ_map.get(occ_code)
                    if not occ_id:
                        continue

                    var_info = variables.get(var_code)
                    gender = _extract_gender(var_info.label if var_info else "")
                    gender_id = self._gender_to_id.get(gender, self._gender_to_id["total"])

                    fact = FactCensusOccupation(
                        county_id=county_id,
                        source_id=self._source_id,
                        gender_id=gender_id,
                        occupation_id=occ_id,
                        worker_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_hours(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B23020 hours worked facts."""
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
                        aggregate_hours=values["aggregate"],
                        mean_hours=values["mean"],
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_housing(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B25003 housing tenure facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get tenure mapping
        tenures = session.query(DimHousingTenure).all()
        tenure_map = {t.tenure_type: t.tenure_id for t in tenures}

        tenure_codes = {
            "B25003_001E": "total",
            "B25003_002E": "owner",
            "B25003_003E": "renter",
        }

        count = 0
        state_iter = tqdm(state_fips_list, desc="B25003", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B25003", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, tenure_type in tenure_codes.items():
                    value = county_data.values.get(var_code)
                    if value is None:
                        continue

                    tenure_id = tenure_map.get(tenure_type)
                    if not tenure_id:
                        continue

                    fact = FactCensusHousing(
                        county_id=county_id,
                        source_id=self._source_id,
                        tenure_id=tenure_id,
                        household_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_rent(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B25064 median rent facts."""
        assert self._client is not None
        assert self._source_id is not None

        count = 0
        state_iter = tqdm(state_fips_list, desc="B25064", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B25064", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                value = county_data.values.get("B25064_001E")
                if value is None:
                    continue

                fact = FactCensusRent(
                    county_id=county_id,
                    source_id=self._source_id,
                    median_rent_usd=Decimal(str(value)),
                )
                session.add(fact)
                count += 1

            session.flush()

        return count

    def _load_fact_rent_burden(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B25070 rent burden facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get burden mapping
        burdens = session.query(DimRentBurden).all()
        burden_map = {b.bracket_code: b.burden_id for b in burdens}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B25070", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B25070", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    # Skip total
                    if var_code == "B25070_001E":
                        continue
                    if value is None:
                        continue

                    bracket_code = var_code.replace("E", "")
                    burden_id = burden_map.get(bracket_code)
                    if not burden_id:
                        continue

                    fact = FactCensusRentBurden(
                        county_id=county_id,
                        source_id=self._source_id,
                        burden_id=burden_id,
                        household_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_education(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B15003 education facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get level mapping
        levels = session.query(DimEducationLevel).all()
        level_map = {lv.level_code: lv.level_id for lv in levels}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B15003", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B15003", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    level_code = var_code.replace("E", "")
                    level_id = level_map.get(level_code)
                    if not level_id:
                        continue

                    fact = FactCensusEducation(
                        county_id=county_id,
                        source_id=self._source_id,
                        level_id=level_id,
                        person_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_gini(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B19083 GINI coefficient facts."""
        assert self._client is not None
        assert self._source_id is not None

        count = 0
        state_iter = tqdm(state_fips_list, desc="B19083", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B19083", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                value = county_data.values.get("B19083_001E")
                if value is None:
                    continue

                fact = FactCensusGini(
                    county_id=county_id,
                    source_id=self._source_id,
                    gini_coefficient=Decimal(str(value)),
                )
                session.add(fact)
                count += 1

            session.flush()

        return count

    def _load_fact_commute(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B08301 commute mode facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get mode mapping
        modes = session.query(DimCommuteMode).all()
        mode_map = {m.mode_code: m.mode_id for m in modes}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B08301", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B08301", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    mode_code = var_code.replace("E", "")
                    mode_id = mode_map.get(mode_code)
                    if not mode_id:
                        continue

                    fact = FactCensusCommute(
                        county_id=county_id,
                        source_id=self._source_id,
                        mode_id=mode_id,
                        worker_count=int(value),
                    )
                    session.add(fact)
                    count += 1

            session.flush()

        return count

    def _load_fact_poverty(
        self,
        session: Session,
        state_fips_list: list[str],
        verbose: bool,
    ) -> int:
        """Load B17001 poverty facts."""
        assert self._client is not None
        assert self._source_id is not None

        # Get category mapping
        categories = session.query(DimPovertyCategory).all()
        cat_map = {c.category_code: c.category_id for c in categories}

        count = 0
        state_iter = tqdm(state_fips_list, desc="B17001", disable=not verbose)

        for state_fips in state_iter:
            data = self._client.get_table_data("B17001", state_fips=state_fips)

            for county_data in data:
                county_id = self._fips_to_county.get(county_data.fips)
                if not county_id:
                    continue

                for var_code, value in county_data.values.items():
                    if value is None:
                        continue

                    cat_code = var_code.replace("E", "")
                    cat_id = cat_map.get(cat_code)
                    if not cat_id:
                        continue

                    fact = FactCensusPoverty(
                        county_id=county_id,
                        source_id=self._source_id,
                        category_id=cat_id,
                        person_count=int(value),
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
    ) -> int:
        """Load B19052/B19053/B19054 income sources facts."""
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
