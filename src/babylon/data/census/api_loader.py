"""API-based Census data loader.

Fetches ACS 5-Year Estimates directly from Census Bureau API at county level,
matching QCEW geographic granularity for cross-dataset labor analysis.

Replaces CSV-based loader with API-first approach covering 16 tables:
- 8 original tables (B19001, B19013, B23025, B24080, B25003, B25064, B25070, C24010)
- 8 new Marxian analysis tables (B23020, B17001, B15003, B19083, B08301, B19052-54)
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session
from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.census.api_client import CensusAPIClient
from babylon.data.census.database import census_engine, init_census_db
from babylon.data.census.schema import (
    CensusColumnMetadata,
    CensusCommute,
    CensusCounty,
    CensusDataSource,
    CensusEducation,
    CensusEmploymentStatus,
    CensusGini,
    CensusHoursWorked,
    CensusHousingTenure,
    CensusIncomeDistribution,
    CensusInvestmentIncome,
    CensusMedianIncome,
    CensusMedianRent,
    CensusOccupation,
    CensusPoverty,
    CensusRentBurden,
    CensusSelfEmployment,
    CensusWageIncome,
    CensusWorkerClass,
)

logger = logging.getLogger(__name__)

# All supported Census tables
ORIGINAL_TABLES = ["B19001", "B19013", "B23025", "B24080", "B25003", "B25064", "B25070", "C24010"]
MARXIAN_TABLES = ["B23020", "B17001", "B15003", "B19083", "B08301", "B19052", "B19053", "B19054"]
ALL_TABLES = ORIGINAL_TABLES + MARXIAN_TABLES

# State FIPS codes (for progress tracking)
STATE_FIPS = [
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
    "72",  # 50 states + DC + PR
]


@dataclass
class LoadStats:
    """Statistics from a load operation."""

    counties: int = 0
    records: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.records is None:
            self.records = {}


# =============================================================================
# DIMENSION LOADERS
# =============================================================================


def load_data_source(session: Session, year: int) -> int:
    """Create or get data source record for API year.

    Args:
        session: SQLAlchemy session
        year: ACS data year

    Returns:
        Data source ID
    """
    variant = f"ACS5Y{year}_API"

    # Check for existing
    existing = session.query(CensusDataSource).filter_by(variant=variant).first()
    if existing:
        return existing.id

    source = CensusDataSource(
        variant=variant,
        year=year,
        description=f"ACS 5-Year Estimates {year} (Census API)",
    )
    session.add(source)
    session.flush()
    return source.id


def load_counties(
    session: Session,
    client: CensusAPIClient,
    verbose: bool = True,
) -> dict[str, int]:
    """Load county dimension from API.

    Fetches all US counties and creates CensusCounty records with
    5-digit FIPS codes matching QCEW geography.

    Args:
        session: SQLAlchemy session
        client: Census API client
        verbose: Show progress bar

    Returns:
        Dict mapping 5-digit FIPS to county_id
    """
    fips_to_id: dict[str, int] = {}

    # First check existing counties
    existing = session.query(CensusCounty).all()
    for county in existing:
        fips_to_id[county.fips] = county.id

    if fips_to_id:
        logger.info(f"Found {len(fips_to_id)} existing counties")
        return fips_to_id

    # Fetch counties from API (use a simple table that all counties have)
    logger.info("Fetching counties from Census API...")

    states = client.get_all_states()
    state_iter = tqdm(states, desc="States", disable=not verbose)

    for state_fips, state_name in state_iter:
        state_iter.set_postfix(state=state_fips)

        # Get county names from B19013 (median income - every county has this)
        try:
            data = client.get_county_data(
                variables=["B19013_001E"],
                state_fips=state_fips,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch counties for state {state_fips}: {e}")
            continue

        for county_data in data:
            fips = county_data.fips

            if fips in fips_to_id:
                continue

            # Parse county name from "County Name, State"
            name_parts = county_data.name.split(", ")
            county_name = name_parts[0] if name_parts else county_data.name

            county = CensusCounty(
                fips=fips,
                state_fips=county_data.state_fips,
                county_fips=county_data.county_fips,
                name=county_name,
                state_name=state_name,
            )
            session.add(county)
            session.flush()
            fips_to_id[fips] = county.id

    session.commit()
    logger.info(f"Loaded {len(fips_to_id)} counties")
    return fips_to_id


# =============================================================================
# ORIGINAL FACT TABLE LOADERS (8)
# =============================================================================


def load_median_income(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B19013 median income data."""
    count = 0
    data = client.get_table_data("B19013")

    for county_data in tqdm(data, desc="B19013", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        estimate = county_data.values.get("B19013_001E")
        if estimate is None:
            continue

        record = CensusMedianIncome(
            county_id=county_id,
            source_id=source_id,
            estimate=float(estimate),
        )
        session.add(record)
        count += 1

    return count


def load_income_distribution(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B19001 income distribution data."""
    count = 0
    data = client.get_table_data("B19001")
    labels = client.get_variables("B19001")

    for county_data in tqdm(data, desc="B19001", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            # Skip total (001)
            if var_code == "B19001_001E":
                continue

            if value is None:
                continue

            label_info = labels.get(var_code)
            bracket_label = _parse_label(label_info.label) if label_info else None

            record = CensusIncomeDistribution(
                county_id=county_id,
                source_id=source_id,
                bracket_code=var_code.replace("E", ""),
                bracket_label=bracket_label,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_employment_status(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B23025 employment status data."""
    count = 0
    data = client.get_table_data("B23025")
    labels = client.get_variables("B23025")

    for county_data in tqdm(data, desc="B23025", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            if value is None:
                continue

            label_info = labels.get(var_code)
            category_label = _parse_label(label_info.label) if label_info else None

            record = CensusEmploymentStatus(
                county_id=county_id,
                source_id=source_id,
                category_code=var_code.replace("E", ""),
                category_label=category_label,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_worker_class(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B24080 worker class data."""
    count = 0
    data = client.get_table_data("B24080")
    labels = client.get_variables("B24080")

    for county_data in tqdm(data, desc="B24080", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            if value is None:
                continue

            label_info = labels.get(var_code)
            label = label_info.label if label_info else ""

            gender = _extract_gender(label)
            class_label = _parse_label(label)

            record = CensusWorkerClass(
                county_id=county_id,
                source_id=source_id,
                gender=gender,
                class_code=var_code.replace("E", ""),
                class_label=class_label,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_housing_tenure(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B25003 housing tenure data."""
    count = 0
    data = client.get_table_data("B25003")

    tenure_map = {
        "B25003_001E": "total",
        "B25003_002E": "owner",
        "B25003_003E": "renter",
    }

    for county_data in tqdm(data, desc="B25003", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, tenure_type in tenure_map.items():
            value = county_data.values.get(var_code)
            if value is None:
                continue

            record = CensusHousingTenure(
                county_id=county_id,
                source_id=source_id,
                tenure_type=tenure_type,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_median_rent(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B25064 median rent data."""
    count = 0
    data = client.get_table_data("B25064")

    for county_data in tqdm(data, desc="B25064", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        estimate = county_data.values.get("B25064_001E")
        if estimate is None:
            continue

        record = CensusMedianRent(
            county_id=county_id,
            source_id=source_id,
            estimate=float(estimate),
        )
        session.add(record)
        count += 1

    return count


def load_rent_burden(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B25070 rent burden data."""
    count = 0
    data = client.get_table_data("B25070")
    labels = client.get_variables("B25070")

    for county_data in tqdm(data, desc="B25070", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            # Skip total
            if var_code == "B25070_001E":
                continue

            if value is None:
                continue

            label_info = labels.get(var_code)
            burden_bracket = _parse_label(label_info.label) if label_info else None

            record = CensusRentBurden(
                county_id=county_id,
                source_id=source_id,
                bracket_code=var_code.replace("E", ""),
                burden_bracket=burden_bracket,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_occupation(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load C24010 occupation data."""
    count = 0
    data = client.get_table_data("C24010")
    labels = client.get_variables("C24010")

    for county_data in tqdm(data, desc="C24010", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            if value is None:
                continue

            label_info = labels.get(var_code)
            label = label_info.label if label_info else ""

            gender = _extract_gender(label)
            occupation_label = _parse_label(label)
            occupation_category = _extract_occupation_category(label)

            record = CensusOccupation(
                county_id=county_id,
                source_id=source_id,
                gender=gender,
                occupation_code=var_code.replace("E", ""),
                occupation_label=occupation_label,
                occupation_category=occupation_category,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


# =============================================================================
# MARXIAN ANALYSIS FACT TABLE LOADERS (8 new)
# =============================================================================


def load_hours_worked(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B23020 hours worked data (Marxian value proxy)."""
    count = 0
    data = client.get_table_data("B23020")
    labels = client.get_variables("B23020")

    for county_data in tqdm(data, desc="B23020", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        # Group by gender (total, male, female)
        gender_groups: dict[str, dict[str, float | None]] = {
            "total": {"aggregate": None, "mean": None},
            "male": {"aggregate": None, "mean": None},
            "female": {"aggregate": None, "mean": None},
        }

        for var_code, value in county_data.values.items():
            label_info = labels.get(var_code)
            label = label_info.label if label_info else ""

            gender = _extract_gender(label)

            if "Aggregate" in label:
                gender_groups[gender]["aggregate"] = value
            elif "Mean" in label:
                gender_groups[gender]["mean"] = value

        for gender, values in gender_groups.items():
            if values["aggregate"] is None and values["mean"] is None:
                continue

            record = CensusHoursWorked(
                county_id=county_id,
                source_id=source_id,
                gender=gender,
                aggregate_hours=values["aggregate"],
                mean_hours=values["mean"],
            )
            session.add(record)
            count += 1

    return count


def load_poverty(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B17001 poverty status data (reserve army metric)."""
    count = 0
    data = client.get_table_data("B17001")
    labels = client.get_variables("B17001")

    for county_data in tqdm(data, desc="B17001", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            if value is None:
                continue

            label_info = labels.get(var_code)
            category_label = _parse_label(label_info.label) if label_info else None

            record = CensusPoverty(
                county_id=county_id,
                source_id=source_id,
                category_code=var_code.replace("E", ""),
                category_label=category_label,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_education(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B15003 educational attainment data (skills reproduction)."""
    count = 0
    data = client.get_table_data("B15003")
    labels = client.get_variables("B15003")

    for county_data in tqdm(data, desc="B15003", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            if value is None:
                continue

            label_info = labels.get(var_code)
            level_label = _parse_label(label_info.label) if label_info else None

            record = CensusEducation(
                county_id=county_id,
                source_id=source_id,
                level_code=var_code.replace("E", ""),
                level_label=level_label,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_gini(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B19083 GINI coefficient data (inequality measure)."""
    count = 0
    data = client.get_table_data("B19083")

    for county_data in tqdm(data, desc="B19083", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        gini_value = county_data.values.get("B19083_001E")
        if gini_value is None:
            continue

        record = CensusGini(
            county_id=county_id,
            source_id=source_id,
            gini_index=float(gini_value),
        )
        session.add(record)
        count += 1

    return count


def load_commute(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B08301 commute mode data (unproductive labor time)."""
    count = 0
    data = client.get_table_data("B08301")
    labels = client.get_variables("B08301")

    for county_data in tqdm(data, desc="B08301", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        for var_code, value in county_data.values.items():
            if value is None:
                continue

            label_info = labels.get(var_code)
            mode_label = _parse_label(label_info.label) if label_info else None

            record = CensusCommute(
                county_id=county_id,
                source_id=source_id,
                mode_code=var_code.replace("E", ""),
                mode_label=mode_label,
                estimate=int(value),
            )
            session.add(record)
            count += 1

    return count


def load_wage_income(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B19052 wage income data (proletariat flag)."""
    count = 0
    data = client.get_table_data("B19052")

    for county_data in tqdm(data, desc="B19052", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        record = CensusWageIncome(
            county_id=county_id,
            source_id=source_id,
            total_households=_safe_int(county_data.values.get("B19052_001E")),
            with_wages=_safe_int(county_data.values.get("B19052_002E")),
            without_wages=_safe_int(county_data.values.get("B19052_003E")),
        )
        session.add(record)
        count += 1

    return count


def load_self_employment(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B19053 self-employment data (petty bourgeois flag)."""
    count = 0
    data = client.get_table_data("B19053")

    for county_data in tqdm(data, desc="B19053", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        record = CensusSelfEmployment(
            county_id=county_id,
            source_id=source_id,
            total_households=_safe_int(county_data.values.get("B19053_001E")),
            with_self_employment=_safe_int(county_data.values.get("B19053_002E")),
            without_self_employment=_safe_int(county_data.values.get("B19053_003E")),
        )
        session.add(record)
        count += 1

    return count


def load_investment_income(
    session: Session,
    client: CensusAPIClient,
    source_id: int,
    fips_to_county: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load B19054 investment income data (bourgeoisie flag)."""
    count = 0
    data = client.get_table_data("B19054")

    for county_data in tqdm(data, desc="B19054", disable=not verbose):
        county_id = fips_to_county.get(county_data.fips)
        if not county_id:
            continue

        record = CensusInvestmentIncome(
            county_id=county_id,
            source_id=source_id,
            total_households=_safe_int(county_data.values.get("B19054_001E")),
            with_investment_income=_safe_int(county_data.values.get("B19054_002E")),
            without_investment_income=_safe_int(county_data.values.get("B19054_003E")),
        )
        session.add(record)
        count += 1

    return count


def load_column_metadata(
    session: Session,
    client: CensusAPIClient,
    tables: list[str],
    verbose: bool = True,
) -> int:
    """Load column metadata from API for specified tables.

    Args:
        session: SQLAlchemy session
        client: Census API client
        tables: List of table codes to fetch metadata for
        verbose: Show progress

    Returns:
        Number of metadata records loaded
    """
    count = 0

    for table in tqdm(tables, desc="Metadata", disable=not verbose):
        try:
            variables = client.get_variables(table)
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {table}: {e}")
            continue

        for var_code, var_info in variables.items():
            record = CensusColumnMetadata(
                table_code=table,
                column_code=var_code,
                column_label=var_info.label,
            )
            session.add(record)
            count += 1

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


# =============================================================================
# TABLE LOADER REGISTRY
# =============================================================================


TableLoader = Callable[
    [Session, CensusAPIClient, int, dict[str, int], bool],
    int,
]

TABLE_LOADERS: dict[str, TableLoader] = {
    # Original 8
    "B19001": load_income_distribution,
    "B19013": load_median_income,
    "B23025": load_employment_status,
    "B24080": load_worker_class,
    "B25003": load_housing_tenure,
    "B25064": load_median_rent,
    "B25070": load_rent_burden,
    "C24010": load_occupation,
    # Marxian analysis 8
    "B23020": load_hours_worked,
    "B17001": load_poverty,
    "B15003": load_education,
    "B19083": load_gini,
    "B08301": load_commute,
    "B19052": load_wage_income,
    "B19053": load_self_employment,
    "B19054": load_investment_income,
}


# =============================================================================
# MAIN LOADER ORCHESTRATION
# =============================================================================


def load_census_from_api(
    year: int = 2022,
    tables: list[str] | None = None,
    api_key: str | None = None,
    reset: bool = False,
    verbose: bool = True,
) -> dict[str, int]:
    """Load Census data from API into SQLite database.

    Args:
        year: ACS data year (default 2022 for 2018-2022 5-year estimates)
        tables: Specific tables to load (default: all 16)
        api_key: Census API key (or from CENSUS_API_KEY env var)
        reset: If True, drop and recreate all census tables
        verbose: Show progress bars

    Returns:
        Dict with table names and record counts
    """
    from sqlalchemy.orm import sessionmaker

    if tables is None:
        tables = ALL_TABLES.copy()

    # Initialize database
    if reset:
        logger.info("Resetting census tables...")
        _reset_census_tables()

    init_census_db()

    Session = sessionmaker(bind=census_engine)
    session = Session()

    stats: dict[str, int] = {}

    try:
        with CensusAPIClient(api_key=api_key, year=year) as client:
            if verbose:
                print(f"Loading ACS {year} 5-Year Estimates from Census API")
                print(f"Tables: {', '.join(tables)}")

            # Load data source
            source_id = load_data_source(session, year)
            session.commit()
            stats["data_source"] = 1

            # Load counties
            fips_to_county = load_counties(session, client, verbose=verbose)
            stats["counties"] = len(fips_to_county)

            # Load each table
            for table in tables:
                if table not in TABLE_LOADERS:
                    logger.warning(f"Unknown table: {table}")
                    continue

                try:
                    loader = TABLE_LOADERS[table]
                    count = loader(session, client, source_id, fips_to_county, verbose)
                    session.commit()
                    stats[table] = count

                    if verbose:
                        print(f"  {table}: {count:,} records")

                except Exception as e:
                    logger.error(f"Failed to load {table}: {e}")
                    session.rollback()
                    stats[table] = 0

            # Load column metadata
            stats["column_metadata"] = load_column_metadata(session, client, tables, verbose)
            session.commit()

            if verbose:
                print("\nIngestion complete:")
                total = sum(stats.values())
                print(f"  Total: {total:,} records")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return stats


def _reset_census_tables() -> None:
    """Drop only census tables, preserving qcew and trade data."""
    from babylon.data.census.schema import (
        CensusColumnMetadata,
        CensusCommute,
        CensusCounty,
        CensusDataSource,
        CensusEducation,
        CensusEmploymentStatus,
        CensusGini,
        CensusHoursWorked,
        CensusHousingTenure,
        CensusIncomeDistribution,
        CensusInvestmentIncome,
        CensusMedianIncome,
        CensusMedianRent,
        CensusOccupation,
        CensusPoverty,
        CensusRentBurden,
        CensusSelfEmployment,
        CensusWageIncome,
        CensusWorkerClass,
    )

    # Drop fact tables first (foreign key order)
    fact_tables = [
        CensusMedianIncome,
        CensusIncomeDistribution,
        CensusEmploymentStatus,
        CensusWorkerClass,
        CensusHousingTenure,
        CensusMedianRent,
        CensusRentBurden,
        CensusOccupation,
        CensusHoursWorked,
        CensusPoverty,
        CensusEducation,
        CensusGini,
        CensusCommute,
        CensusWageIncome,
        CensusSelfEmployment,
        CensusInvestmentIncome,
        CensusColumnMetadata,
    ]

    for table in fact_tables:
        table.__table__.drop(census_engine, checkfirst=True)  # type: ignore[attr-defined]

    # Drop dimension tables last
    CensusDataSource.__table__.drop(census_engine, checkfirst=True)  # type: ignore[attr-defined]
    CensusCounty.__table__.drop(census_engine, checkfirst=True)  # type: ignore[attr-defined]
