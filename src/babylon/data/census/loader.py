"""Batch ingestion logic for Census data.

Loads parsed Census CSV data into SQLite database using SQLAlchemy ORM.
Handles all 8 ACS tables with proper normalization and relationship management.
"""

import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session
from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.census.database import CensusBase, census_engine, init_census_db
from babylon.data.census.parser import (
    AIAN_VARIANT,
    MAIN_VARIANT,
    CensusDataFrame,
    discover_census_files,
    extract_cbsa_code,
    get_estimate_columns,
    parse_column_label,
    parse_data_csv,
    parse_metadata_csv,
    safe_float,
    safe_int,
)
from babylon.data.census.schema import (
    CensusColumnMetadata,
    CensusDataSource,
    CensusEmploymentStatus,
    CensusHousingTenure,
    CensusIncomeDistribution,
    CensusMedianIncome,
    CensusMedianRent,
    CensusMetroArea,
    CensusOccupation,
    CensusRentBurden,
    CensusWorkerClass,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DIMENSION LOADERS
# =============================================================================


def load_data_sources(session: Session) -> dict[str, int]:
    """Load data source dimension records.

    Args:
        session: SQLAlchemy session

    Returns:
        Dict mapping variant name to source_id
    """
    sources = {
        MAIN_VARIANT: "ACS 5-Year Estimates 2017-2021 (Main)",
        AIAN_VARIANT: "ACS 5-Year Estimates 2017-2021 (American Indian/Alaska Native)",
    }

    variant_to_id: dict[str, int] = {}

    for variant, description in sources.items():
        source = CensusDataSource(variant=variant, description=description)
        session.add(source)
        session.flush()
        variant_to_id[variant] = source.id

    return variant_to_id


def load_metro_areas(session: Session, df: CensusDataFrame) -> dict[str, int]:
    """Load metro area dimension records from a data file.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data with GEO_ID and NAME columns

    Returns:
        Dict mapping geo_id to metro_id
    """
    geo_to_id: dict[str, int] = {}

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        name = row["NAME"]

        # Skip if already exists
        if geo_id in geo_to_id:
            continue

        # Check database for existing
        existing = session.query(CensusMetroArea).filter_by(geo_id=geo_id).first()
        if existing:
            geo_to_id[geo_id] = existing.id
            continue

        # Create new metro area
        cbsa_code = extract_cbsa_code(geo_id)
        metro = CensusMetroArea(geo_id=geo_id, name=name, cbsa_code=cbsa_code)
        session.add(metro)
        session.flush()
        geo_to_id[geo_id] = metro.id

    return geo_to_id


# =============================================================================
# FACT TABLE LOADERS
# =============================================================================


def load_median_income(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B19013 median income data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_col = "B19013_001E"

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        estimate = safe_float(row.get(estimate_col))
        if estimate is None:
            continue

        record = CensusMedianIncome(
            metro_id=metro_id,
            source_id=source_id,
            estimate=estimate,
        )
        session.add(record)
        count += 1

    return count


def load_income_distribution(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B19001 income distribution data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_cols = get_estimate_columns(df.data, "B19001")

    # Skip B19001_001E which is just total
    bracket_cols = [c for c in estimate_cols if c != "B19001_001E"]

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        for col in bracket_cols:
            estimate = safe_int(row.get(col))
            if estimate is None:
                continue

            # Extract bracket label from column labels
            label = df.column_labels.get(col, "")
            bracket_label, _ = parse_column_label(label)

            record = CensusIncomeDistribution(
                metro_id=metro_id,
                source_id=source_id,
                bracket_code=col.replace("E", ""),
                bracket_label=bracket_label or None,
                estimate=estimate,
            )
            session.add(record)
            count += 1

    return count


def load_employment_status(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B23025 employment status data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_cols = get_estimate_columns(df.data, "B23025")

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        for col in estimate_cols:
            estimate = safe_int(row.get(col))
            if estimate is None:
                continue

            label = df.column_labels.get(col, "")
            category_label, _ = parse_column_label(label)

            record = CensusEmploymentStatus(
                metro_id=metro_id,
                source_id=source_id,
                category_code=col.replace("E", ""),
                category_label=category_label or None,
                estimate=estimate,
            )
            session.add(record)
            count += 1

    return count


def load_worker_class(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B24080 worker class data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_cols = get_estimate_columns(df.data, "B24080")

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        for col in estimate_cols:
            estimate = safe_int(row.get(col))
            if estimate is None:
                continue

            label = df.column_labels.get(col, "")
            class_label, _ = parse_column_label(label)

            # Determine gender from label hierarchy
            gender = "total"
            if "!!Male:" in label or "!!Male!!" in label:
                gender = "male"
            elif "!!Female:" in label or "!!Female!!" in label:
                gender = "female"

            record = CensusWorkerClass(
                metro_id=metro_id,
                source_id=source_id,
                gender=gender,
                class_code=col.replace("E", ""),
                class_label=class_label or None,
                estimate=estimate,
            )
            session.add(record)
            count += 1

    return count


def load_housing_tenure(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B25003 housing tenure data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    # Map column codes to tenure types
    tenure_map = {
        "B25003_001E": "total",
        "B25003_002E": "owner",
        "B25003_003E": "renter",
    }

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        for col, tenure_type in tenure_map.items():
            if col not in df.data.columns:
                continue

            estimate = safe_int(row.get(col))
            if estimate is None:
                continue

            record = CensusHousingTenure(
                metro_id=metro_id,
                source_id=source_id,
                tenure_type=tenure_type,
                estimate=estimate,
            )
            session.add(record)
            count += 1

    return count


def load_median_rent(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B25064 median rent data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_col = "B25064_001E"

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        estimate = safe_float(row.get(estimate_col))
        if estimate is None:
            continue

        record = CensusMedianRent(
            metro_id=metro_id,
            source_id=source_id,
            estimate=estimate,
        )
        session.add(record)
        count += 1

    return count


def load_rent_burden(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load B25070 rent burden data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_cols = get_estimate_columns(df.data, "B25070")

    # Skip B25070_001E which is total
    bracket_cols = [c for c in estimate_cols if c != "B25070_001E"]

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        for col in bracket_cols:
            estimate = safe_int(row.get(col))
            if estimate is None:
                continue

            label = df.column_labels.get(col, "")
            burden_bracket, _ = parse_column_label(label)

            record = CensusRentBurden(
                metro_id=metro_id,
                source_id=source_id,
                bracket_code=col.replace("E", ""),
                burden_bracket=burden_bracket or None,
                estimate=estimate,
            )
            session.add(record)
            count += 1

    return count


def load_occupation(
    session: Session,
    df: CensusDataFrame,
    source_id: int,
    geo_to_metro: dict[str, int],
) -> int:
    """Load C24010 occupation data.

    Args:
        session: SQLAlchemy session
        df: Parsed Census data
        source_id: Data source foreign key
        geo_to_metro: Mapping from geo_id to metro_id

    Returns:
        Number of records loaded
    """
    count = 0
    estimate_cols = get_estimate_columns(df.data, "C24010")

    for _, row in df.data.iterrows():
        geo_id = row["GEO_ID"]
        metro_id = geo_to_metro.get(geo_id)
        if not metro_id:
            continue

        for col in estimate_cols:
            estimate = safe_int(row.get(col))
            if estimate is None:
                continue

            label = df.column_labels.get(col, "")

            # Determine gender from label hierarchy
            gender = "total"
            if "!!Male:" in label or "!!Male!!" in label:
                gender = "male"
            elif "!!Female:" in label or "!!Female!!" in label:
                gender = "female"

            # Parse occupation label and category
            occupation_label, occupation_category = parse_column_label(label)

            # Extract top-level occupation category from hierarchy
            # Pattern: ...!!CATEGORY:!!subcategory
            cat_match = re.search(r"!!(Management|Service|Sales|Natural|Production)[^!]+:", label)
            if cat_match:
                # Get the full category text
                parts = label.split("!!")
                for part in parts:
                    if part.startswith(cat_match.group(1)):
                        occupation_category = part.rstrip(":")
                        break

            record = CensusOccupation(
                metro_id=metro_id,
                source_id=source_id,
                gender=gender,
                occupation_code=col.replace("E", ""),
                occupation_label=occupation_label or None,
                occupation_category=occupation_category,
                estimate=estimate,
            )
            session.add(record)
            count += 1

    return count


def load_column_metadata(session: Session, census_dir: Path) -> int:
    """Load column metadata from all tables.

    Args:
        session: SQLAlchemy session
        census_dir: Path to data/census/ directory

    Returns:
        Number of metadata records loaded
    """
    count = 0

    for table_dir in census_dir.iterdir():
        if not table_dir.is_dir():
            continue

        # Find main variant metadata file
        metadata_files = list(table_dir.glob(f"{MAIN_VARIANT}.*-Column-Metadata.csv"))
        if not metadata_files:
            continue

        mapping = parse_metadata_csv(metadata_files[0])

        for code, label in mapping.code_to_label.items():
            # Skip non-data columns
            if code in ("GEO_ID", "NAME"):
                continue

            record = CensusColumnMetadata(
                table_code=mapping.table_code,
                column_code=code,
                column_label=label,
            )
            session.add(record)
            count += 1

    return count


# =============================================================================
# MAIN LOADER ORCHESTRATION
# =============================================================================

# Table code to loader function mapping
TABLE_LOADERS = {
    "B19001": load_income_distribution,
    "B19013": load_median_income,
    "B23025": load_employment_status,
    "B24080": load_worker_class,
    "B25003": load_housing_tenure,
    "B25064": load_median_rent,
    "B25070": load_rent_burden,
    "C24010": load_occupation,
}


def load_census_data(
    census_dir: Path,
    reset: bool = False,
    verbose: bool = True,
) -> dict[str, int]:
    """Load all Census data into SQLite database.

    Args:
        census_dir: Path to data/census/ directory
        reset: If True, drop and recreate all tables
        verbose: If True, show progress bars

    Returns:
        Dict with table names and record counts
    """
    from sqlalchemy.orm import sessionmaker

    # Initialize database
    if reset:
        CensusBase.metadata.drop_all(bind=census_engine)
    init_census_db()

    Session = sessionmaker(bind=census_engine)
    session = Session()

    stats: dict[str, int] = {}

    try:
        # Discover files
        files = discover_census_files(census_dir)
        if verbose:
            print(f"Discovered {len(files)} tables: {list(files.keys())}")

        # Load data sources
        variant_to_source = load_data_sources(session)
        session.commit()
        stats["data_sources"] = len(variant_to_source)

        # Collect all geo_ids from main variant
        geo_to_metro: dict[str, int] = {}

        # Process each table
        tables = list(TABLE_LOADERS.keys())
        table_iter = tqdm(tables, desc="Tables", disable=not verbose)

        for table_code in table_iter:
            if table_code not in files:
                logger.warning(f"Table {table_code} not found in census directory")
                continue

            table_iter.set_postfix(table=table_code)

            # Process each variant
            for variant, data_path in files[table_code].items():
                source_id = variant_to_source.get(variant)
                if not source_id:
                    continue

                # Parse CSV
                df = parse_data_csv(data_path, skip_moe=True)

                # Load metro areas (only need to do once per variant)
                new_metros = load_metro_areas(session, df)
                geo_to_metro.update(new_metros)
                session.commit()

                # Load fact data
                loader_func = TABLE_LOADERS[table_code]
                count = loader_func(session, df, source_id, geo_to_metro)
                session.commit()

                key = f"{table_code}_{variant}"
                stats[key] = count

        # Load column metadata
        stats["column_metadata"] = load_column_metadata(session, census_dir)
        session.commit()

        # Final metro count
        stats["metro_areas"] = len(geo_to_metro)

        if verbose:
            print("\nIngestion complete:")
            for key, count in sorted(stats.items()):
                print(f"  {key}: {count:,} records")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return stats
