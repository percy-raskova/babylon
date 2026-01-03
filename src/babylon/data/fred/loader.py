"""FRED data loader for batch ingestion into SQLite.

Orchestrates fetching data from FRED API and loading it into the
research.sqlite database using batch inserts.

Example:
    from babylon.data.fred import load_fred_data

    stats = load_fred_data(year=2022, reset=True)
    print(f"Loaded {stats.national_records} national, "
          f"{stats.state_records} state, "
          f"{stats.industry_records} industry records")
"""

import logging
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from babylon.data.census.database import CensusBase, census_engine, get_census_db
from babylon.data.fred.api_client import (
    DFA_ASSET_CATEGORIES,
    DFA_WEALTH_CLASSES,
    DFA_WEALTH_LEVEL_SERIES,
    DFA_WEALTH_SHARE_SERIES,
    INDUSTRY_UNEMPLOYMENT_SERIES,
    NATIONAL_SERIES,
    US_STATES,
    FredAPIClient,
    FredAPIError,
)
from babylon.data.fred.parser import (
    get_national_series_list,
    parse_industry_unemployment,
    parse_national_series,
    parse_state_unemployment,
    parse_wealth_level,
    parse_wealth_share,
)
from babylon.data.fred.schema import (
    FredAssetCategory,
    FredIndustry,
    FredIndustryUnemployment,
    FredNational,
    FredSeries,
    FredState,
    FredStateUnemployment,
    FredWealthClass,
    FredWealthLevel,
    FredWealthShare,
)

logger = logging.getLogger(__name__)


@dataclass
class LoadStats:
    """Statistics from FRED data loading."""

    series_loaded: int = 0
    states_loaded: int = 0
    industries_loaded: int = 0
    wealth_classes_loaded: int = 0
    asset_categories_loaded: int = 0
    national_records: int = 0
    state_records: int = 0
    industry_records: int = 0
    wealth_level_records: int = 0
    wealth_share_records: int = 0
    api_calls: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def init_fred_tables() -> None:
    """Create FRED tables if they don't exist."""
    # Import schema to register models
    from babylon.data.fred import schema  # noqa: F401

    CensusBase.metadata.create_all(bind=census_engine)


def reset_fred_tables() -> None:
    """Drop and recreate FRED tables.

    Preserves other research tables (Census, QCEW, Trade, Productivity).
    """
    from sqlalchemy import inspect

    # First ensure tables exist
    init_fred_tables()

    # Check which tables exist
    inspector = inspect(census_engine)
    existing_tables = inspector.get_table_names()

    db = next(get_census_db())
    try:
        # Delete from fact tables first (foreign key constraints)
        if "fred_national" in existing_tables:
            db.execute(delete(FredNational))
        if "fred_state_unemployment" in existing_tables:
            db.execute(delete(FredStateUnemployment))
        if "fred_industry_unemployment" in existing_tables:
            db.execute(delete(FredIndustryUnemployment))
        if "fred_wealth_levels" in existing_tables:
            db.execute(delete(FredWealthLevel))
        if "fred_wealth_shares" in existing_tables:
            db.execute(delete(FredWealthShare))

        # Then dimension tables
        if "fred_series" in existing_tables:
            db.execute(delete(FredSeries))
        if "fred_states" in existing_tables:
            db.execute(delete(FredState))
        if "fred_industries" in existing_tables:
            db.execute(delete(FredIndustry))
        if "fred_wealth_classes" in existing_tables:
            db.execute(delete(FredWealthClass))
        if "fred_asset_categories" in existing_tables:
            db.execute(delete(FredAssetCategory))

        db.commit()
    finally:
        db.close()


def _load_series_dimension(
    db: Session,
    series_ids: list[str],
    client: FredAPIClient,
) -> dict[str, int]:
    """Load series dimension table from API.

    Args:
        db: Database session.
        series_ids: List of series IDs to load.
        client: FRED API client.

    Returns:
        Mapping of series_id to database id.
    """
    series_to_id: dict[str, int] = {}

    for series_id in series_ids:
        # Check if already exists
        existing = db.query(FredSeries).filter_by(series_id=series_id).first()
        if existing:
            series_to_id[series_id] = existing.id
            continue

        try:
            metadata = client.get_series_info(series_id)
            series = FredSeries(
                series_id=series_id,
                title=metadata.title,
                units=metadata.units,
                frequency=metadata.frequency,
                seasonal_adjustment=metadata.seasonal_adjustment,
                source=metadata.source,
                last_updated=metadata.last_updated,
            )
            db.add(series)
            db.flush()  # Get ID
            series_to_id[series_id] = series.id
        except FredAPIError as e:
            logger.warning(f"Failed to fetch series info for {series_id}: {e}")
            continue

    db.commit()
    return series_to_id


def _load_state_dimension(db: Session) -> dict[str, int]:
    """Load state dimension table from static data.

    Args:
        db: Database session.

    Returns:
        Mapping of FIPS code to database id.
    """
    fips_to_id: dict[str, int] = {}

    for fips_code, (name, abbreviation) in US_STATES.items():
        # Check if already exists
        existing = db.query(FredState).filter_by(fips_code=fips_code).first()
        if existing:
            fips_to_id[fips_code] = existing.id
            continue

        state = FredState(
            fips_code=fips_code,
            name=name,
            abbreviation=abbreviation,
        )
        db.add(state)
        db.flush()
        fips_to_id[fips_code] = state.id

    db.commit()
    return fips_to_id


def _load_industry_dimension(db: Session) -> dict[str, int]:
    """Load industry dimension table from static data.

    Args:
        db: Database session.

    Returns:
        Mapping of LNU code to database id.
    """
    lnu_to_id: dict[str, int] = {}

    for lnu_code, (name, naics_sector) in INDUSTRY_UNEMPLOYMENT_SERIES.items():
        # Check if already exists
        existing = db.query(FredIndustry).filter_by(lnu_code=lnu_code).first()
        if existing:
            lnu_to_id[lnu_code] = existing.id
            continue

        industry = FredIndustry(
            lnu_code=lnu_code,
            name=name,
            naics_sector=naics_sector,
        )
        db.add(industry)
        db.flush()
        lnu_to_id[lnu_code] = industry.id

    db.commit()
    return lnu_to_id


def _load_wealth_class_dimension(db: Session) -> dict[str, int]:
    """Load wealth class dimension table from static data.

    Args:
        db: Database session.

    Returns:
        Mapping of percentile_code to database id.
    """
    code_to_id: dict[str, int] = {}

    for code, metadata in DFA_WEALTH_CLASSES.items():
        # Check if already exists
        existing = db.query(FredWealthClass).filter_by(percentile_code=code).first()
        if existing:
            code_to_id[code] = existing.id
            continue

        wealth_class = FredWealthClass(
            percentile_code=code,
            percentile_label=str(metadata["label"]),
            percentile_min=float(metadata["percentile_min"]),
            percentile_max=float(metadata["percentile_max"]),
            babylon_class=str(metadata["babylon_class"]),
            description=str(metadata["description"]),
        )
        db.add(wealth_class)
        db.flush()
        code_to_id[code] = wealth_class.id

    db.commit()
    return code_to_id


def _load_asset_category_dimension(db: Session) -> dict[str, int]:
    """Load asset category dimension table from static data.

    Args:
        db: Database session.

    Returns:
        Mapping of category_code to database id.
    """
    code_to_id: dict[str, int] = {}

    for code, metadata in DFA_ASSET_CATEGORIES.items():
        # Check if already exists
        existing = db.query(FredAssetCategory).filter_by(category_code=code).first()
        if existing:
            code_to_id[code] = existing.id
            continue

        category = FredAssetCategory(
            category_code=code,
            category_label=metadata["label"],
            marxian_interpretation=metadata["interpretation"],
        )
        db.add(category)
        db.flush()
        code_to_id[code] = category.id

    db.commit()
    return code_to_id


def _load_national_observations(
    db: Session,
    series_to_id: dict[str, int],
    client: FredAPIClient,
    year: int,
    stats: LoadStats,
    verbose: bool = True,
) -> None:
    """Load national series observations.

    Args:
        db: Database session.
        series_to_id: Mapping of series_id to database id.
        client: FRED API client.
        year: Year to load data for.
        stats: LoadStats to update.
        verbose: Print progress messages.
    """
    observation_start = f"{year}-01-01"
    observation_end = f"{year}-12-31"
    batch: list[FredNational] = []
    batch_size = 1000

    for series_id, db_id in series_to_id.items():
        try:
            if verbose:
                title = NATIONAL_SERIES.get(series_id, series_id)
                print(f"  Fetching {series_id} ({title})...")

            series_data = client.get_series_observations(
                series_id,
                observation_start=observation_start,
                observation_end=observation_end,
            )
            stats.api_calls += 1

            records = parse_national_series(series_data, year=year)

            for record in records:
                observation = FredNational(
                    series_id=db_id,
                    date=record.date,
                    year=record.year,
                    month=record.month,
                    quarter=record.quarter,
                    value=record.value,
                )
                batch.append(observation)
                stats.national_records += 1

                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    batch = []

        except FredAPIError as e:
            error_msg = f"Failed to fetch {series_id}: {e.message}"
            logger.warning(error_msg)
            if stats.errors is not None:
                stats.errors.append(error_msg)

    # Commit remaining
    if batch:
        db.add_all(batch)
        db.commit()


def _load_state_unemployment_observations(
    db: Session,
    fips_to_id: dict[str, int],
    client: FredAPIClient,
    year: int,
    stats: LoadStats,
    verbose: bool = True,
) -> None:
    """Load state unemployment observations.

    Args:
        db: Database session.
        fips_to_id: Mapping of FIPS code to database id.
        client: FRED API client.
        year: Year to load data for.
        stats: LoadStats to update.
        verbose: Print progress messages.
    """
    observation_start = f"{year}-01-01"
    observation_end = f"{year}-12-31"
    batch: list[FredStateUnemployment] = []
    batch_size = 1000

    if verbose:
        print(f"  Fetching state unemployment for {len(fips_to_id)} states...")

    for fips_code, db_id in fips_to_id.items():
        try:
            series_data = client.get_state_unemployment(
                fips_code,
                observation_start=observation_start,
                observation_end=observation_end,
            )
            stats.api_calls += 1

            records = parse_state_unemployment(series_data, fips_code, year=year)

            for record in records:
                observation = FredStateUnemployment(
                    state_id=db_id,
                    date=record.date,
                    year=record.year,
                    month=record.month,
                    unemployment_rate=record.unemployment_rate,
                )
                batch.append(observation)
                stats.state_records += 1

                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    batch = []

        except FredAPIError as e:
            state_name = US_STATES.get(fips_code, ("Unknown",))[0]
            error_msg = f"Failed to fetch unemployment for {state_name}: {e.message}"
            logger.warning(error_msg)
            if stats.errors is not None:
                stats.errors.append(error_msg)

    # Commit remaining
    if batch:
        db.add_all(batch)
        db.commit()

    if verbose:
        print(f"    Loaded {stats.state_records} state unemployment records")


def _load_industry_unemployment_observations(
    db: Session,
    lnu_to_id: dict[str, int],
    client: FredAPIClient,
    year: int,
    stats: LoadStats,
    verbose: bool = True,
) -> None:
    """Load industry unemployment observations.

    Args:
        db: Database session.
        lnu_to_id: Mapping of LNU code to database id.
        client: FRED API client.
        year: Year to load data for.
        stats: LoadStats to update.
        verbose: Print progress messages.
    """
    observation_start = f"{year}-01-01"
    observation_end = f"{year}-12-31"
    batch: list[FredIndustryUnemployment] = []
    batch_size = 1000

    if verbose:
        print(f"  Fetching industry unemployment for {len(lnu_to_id)} sectors...")

    for lnu_code, db_id in lnu_to_id.items():
        try:
            series_data = client.get_series_observations(
                lnu_code,
                observation_start=observation_start,
                observation_end=observation_end,
            )
            stats.api_calls += 1

            records = parse_industry_unemployment(series_data, lnu_code, year=year)

            for record in records:
                observation = FredIndustryUnemployment(
                    industry_id=db_id,
                    date=record.date,
                    year=record.year,
                    month=record.month,
                    unemployment_rate=record.unemployment_rate,
                )
                batch.append(observation)
                stats.industry_records += 1

                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    batch = []

        except FredAPIError as e:
            industry_name = INDUSTRY_UNEMPLOYMENT_SERIES.get(lnu_code, ("Unknown",))[0]
            error_msg = f"Failed to fetch unemployment for {industry_name}: {e.message}"
            logger.warning(error_msg)
            if stats.errors is not None:
                stats.errors.append(error_msg)

    # Commit remaining
    if batch:
        db.add_all(batch)
        db.commit()

    if verbose:
        print(f"    Loaded {stats.industry_records} industry unemployment records")


def _load_wealth_level_observations(
    db: Session,
    series_to_id: dict[str, int],
    class_to_id: dict[str, int],
    category_to_id: dict[str, int],
    client: FredAPIClient,
    start_year: int,
    end_year: int | None,
    stats: LoadStats,
    verbose: bool = True,
) -> None:
    """Load DFA wealth level observations.

    Args:
        db: Database session.
        series_to_id: Mapping of series_id to database id.
        class_to_id: Mapping of percentile_code to database id.
        category_to_id: Mapping of category_code to database id.
        client: FRED API client.
        start_year: Start year for data range.
        end_year: End year for data range (None for current).
        stats: LoadStats to update.
        verbose: Print progress messages.
    """
    observation_start = f"{start_year}-01-01"
    observation_end = f"{end_year}-12-31" if end_year else None
    batch: list[FredWealthLevel] = []
    batch_size = 500

    if verbose:
        print(f"  Fetching DFA wealth levels ({len(DFA_WEALTH_LEVEL_SERIES)} series)...")

    for (percentile_code, asset_category), series_id in DFA_WEALTH_LEVEL_SERIES.items():
        try:
            series_data = client.get_series_observations(
                series_id,
                observation_start=observation_start,
                observation_end=observation_end,
            )
            stats.api_calls += 1

            # Ensure series is in dimension table
            if series_id not in series_to_id:
                series_obj = FredSeries(
                    series_id=series_id,
                    title=series_data.metadata.title,
                    units=series_data.metadata.units,
                    frequency=series_data.metadata.frequency,
                    seasonal_adjustment=series_data.metadata.seasonal_adjustment,
                    source=series_data.metadata.source,
                    last_updated=series_data.metadata.last_updated,
                )
                db.add(series_obj)
                db.flush()
                series_to_id[series_id] = series_obj.id

            records = parse_wealth_level(series_data, percentile_code, asset_category)

            for record in records:
                observation = FredWealthLevel(
                    series_id=series_to_id[series_id],
                    wealth_class_id=class_to_id[percentile_code],
                    asset_category_id=category_to_id[asset_category],
                    date=record.date,
                    year=record.year,
                    quarter=record.quarter,
                    value_millions=record.value_millions,
                )
                batch.append(observation)
                stats.wealth_level_records += 1

                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    batch = []

        except FredAPIError as e:
            error_msg = f"Failed to fetch DFA level {series_id}: {e.message}"
            logger.warning(error_msg)
            if stats.errors is not None:
                stats.errors.append(error_msg)

    # Commit remaining
    if batch:
        db.add_all(batch)
        db.commit()

    if verbose:
        print(f"    Loaded {stats.wealth_level_records} wealth level records")


def _load_wealth_share_observations(
    db: Session,
    series_to_id: dict[str, int],
    class_to_id: dict[str, int],
    category_to_id: dict[str, int],
    client: FredAPIClient,
    start_year: int,
    end_year: int | None,
    stats: LoadStats,
    verbose: bool = True,
) -> None:
    """Load DFA wealth share observations.

    Args:
        db: Database session.
        series_to_id: Mapping of series_id to database id.
        class_to_id: Mapping of percentile_code to database id.
        category_to_id: Mapping of category_code to database id.
        client: FRED API client.
        start_year: Start year for data range.
        end_year: End year for data range (None for current).
        stats: LoadStats to update.
        verbose: Print progress messages.
    """
    observation_start = f"{start_year}-01-01"
    observation_end = f"{end_year}-12-31" if end_year else None
    batch: list[FredWealthShare] = []
    batch_size = 500

    if verbose:
        print(f"  Fetching DFA wealth shares ({len(DFA_WEALTH_SHARE_SERIES)} series)...")

    for (percentile_code, asset_category), series_id in DFA_WEALTH_SHARE_SERIES.items():
        try:
            series_data = client.get_series_observations(
                series_id,
                observation_start=observation_start,
                observation_end=observation_end,
            )
            stats.api_calls += 1

            # Ensure series is in dimension table
            if series_id not in series_to_id:
                series_obj = FredSeries(
                    series_id=series_id,
                    title=series_data.metadata.title,
                    units=series_data.metadata.units,
                    frequency=series_data.metadata.frequency,
                    seasonal_adjustment=series_data.metadata.seasonal_adjustment,
                    source=series_data.metadata.source,
                    last_updated=series_data.metadata.last_updated,
                )
                db.add(series_obj)
                db.flush()
                series_to_id[series_id] = series_obj.id

            records = parse_wealth_share(series_data, percentile_code, asset_category)

            for record in records:
                observation = FredWealthShare(
                    series_id=series_to_id[series_id],
                    wealth_class_id=class_to_id[percentile_code],
                    asset_category_id=category_to_id[asset_category],
                    date=record.date,
                    year=record.year,
                    quarter=record.quarter,
                    share_percent=record.share_percent,
                )
                batch.append(observation)
                stats.wealth_share_records += 1

                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    batch = []

        except FredAPIError as e:
            error_msg = f"Failed to fetch DFA share {series_id}: {e.message}"
            logger.warning(error_msg)
            if stats.errors is not None:
                stats.errors.append(error_msg)

    # Commit remaining
    if batch:
        db.add_all(batch)
        db.commit()

    if verbose:
        print(f"    Loaded {stats.wealth_share_records} wealth share records")


def _print_load_stats(stats: LoadStats) -> None:
    """Print loading statistics summary."""
    print("\nFRED data loading complete:")
    print(f"  Series loaded: {stats.series_loaded}")
    print(f"  States loaded: {stats.states_loaded}")
    print(f"  Industries loaded: {stats.industries_loaded}")
    print(f"  Wealth classes loaded: {stats.wealth_classes_loaded}")
    print(f"  Asset categories loaded: {stats.asset_categories_loaded}")
    print(f"  National records: {stats.national_records}")
    print(f"  State unemployment records: {stats.state_records}")
    print(f"  Industry unemployment records: {stats.industry_records}")
    print(f"  Wealth level records: {stats.wealth_level_records}")
    print(f"  Wealth share records: {stats.wealth_share_records}")
    print(f"  API calls made: {stats.api_calls}")
    if stats.errors:
        print(f"  Errors: {len(stats.errors)}")
        for error in stats.errors[:5]:
            print(f"    - {error}")


def load_fred_data(
    series_ids: list[str] | None = None,
    year: int = 2022,
    include_states: bool = True,
    include_industries: bool = True,
    include_wealth: bool = True,
    start_year: int = 2015,
    reset: bool = False,
    verbose: bool = True,
    api_key: str | None = None,
) -> LoadStats:
    """Load FRED data into SQLite database.

    Fetches macroeconomic time series from FRED API and loads them into
    the research.sqlite database. By default loads all 8 national series
    plus state and industry unemployment data for the specified year,
    and DFA wealth distribution data from start_year to present.

    Args:
        series_ids: Optional list of national series to load.
            If None, loads all NATIONAL_SERIES.
        year: Year to load data for national/state/industry (default 2022).
        include_states: Load state-level unemployment data.
        include_industries: Load industry-level unemployment data.
        include_wealth: Load DFA wealth distribution data (quarterly).
        start_year: Start year for DFA wealth data (default 2015).
        reset: Drop and recreate FRED tables before loading.
        verbose: Print progress messages.
        api_key: FRED API key. If None, reads from FRED_API_KEY env var.

    Returns:
        LoadStats with counts of records loaded.

    Raises:
        ValueError: If no API key available.

    Example:
        >>> stats = load_fred_data(year=2022, reset=True)
        >>> print(f"Loaded {stats.national_records} national records")
    """
    stats = LoadStats()

    if verbose:
        print(f"Loading FRED data for {year}...")
        if include_wealth:
            print(f"  DFA wealth data: {start_year}-present (quarterly)")

    # Reset if requested
    if reset:
        if verbose:
            print("Resetting FRED tables...")
        reset_fred_tables()
    else:
        init_fred_tables()

    # Determine series to load
    if series_ids is None:
        series_ids = get_national_series_list()

    # Get database session
    db = next(get_census_db())

    try:
        with FredAPIClient(api_key=api_key) as client:
            # Load dimension tables
            if verbose:
                print("Loading dimension tables...")

            # Series dimension (requires API calls)
            series_to_id = _load_series_dimension(db, series_ids, client)
            stats.series_loaded = len(series_to_id)
            stats.api_calls += len(series_ids)

            # State dimension (static data)
            if include_states:
                fips_to_id = _load_state_dimension(db)
                stats.states_loaded = len(fips_to_id)

            # Industry dimension (static data)
            if include_industries:
                lnu_to_id = _load_industry_dimension(db)
                stats.industries_loaded = len(lnu_to_id)

            # Wealth class dimension (static data)
            if include_wealth:
                class_to_id = _load_wealth_class_dimension(db)
                stats.wealth_classes_loaded = len(class_to_id)

                category_to_id = _load_asset_category_dimension(db)
                stats.asset_categories_loaded = len(category_to_id)

            # Load fact tables
            if verbose:
                print("Loading observations...")

            # National series
            _load_national_observations(db, series_to_id, client, year, stats, verbose)

            # State unemployment
            if include_states:
                _load_state_unemployment_observations(db, fips_to_id, client, year, stats, verbose)

            # Industry unemployment
            if include_industries:
                _load_industry_unemployment_observations(
                    db, lnu_to_id, client, year, stats, verbose
                )

            # DFA wealth distribution
            if include_wealth:
                _load_wealth_level_observations(
                    db,
                    series_to_id,
                    class_to_id,
                    category_to_id,
                    client,
                    start_year,
                    None,  # end_year=None for current
                    stats,
                    verbose,
                )
                _load_wealth_share_observations(
                    db,
                    series_to_id,
                    class_to_id,
                    category_to_id,
                    client,
                    start_year,
                    None,  # end_year=None for current
                    stats,
                    verbose,
                )

    finally:
        db.close()

    if verbose:
        _print_load_stats(stats)

    return stats
