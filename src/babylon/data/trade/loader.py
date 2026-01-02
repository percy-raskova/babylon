"""Batch ingestion logic for UN trade data.

Loads parsed Excel trade data into SQLite database using SQLAlchemy ORM.
Stores data in the unified research.sqlite alongside census data.
"""

import logging
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker
from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.census.database import CensusBase, census_engine
from babylon.data.trade.parser import TradeDataFrame, TradeRowData, parse_trade_excel
from babylon.data.trade.schema import TradeAnnual, TradeCountry, TradeMonthly

logger = logging.getLogger(__name__)


# =============================================================================
# DIMENSION LOADERS
# =============================================================================


def load_countries(
    session: Session,
    data: TradeDataFrame,
) -> dict[str, int]:
    """Load country dimension records.

    Args:
        session: SQLAlchemy session
        data: Parsed trade data with countries

    Returns:
        Dict mapping cty_code to country_id
    """
    code_to_id: dict[str, int] = {}

    for country_data in data.countries:
        # Check if already exists
        existing = session.query(TradeCountry).filter_by(cty_code=country_data.cty_code).first()

        if existing:
            code_to_id[country_data.cty_code] = existing.id
            continue

        # Create new country
        country = TradeCountry(
            cty_code=country_data.cty_code,
            name=country_data.name,
            is_region=country_data.is_region,
        )
        session.add(country)
        session.flush()
        code_to_id[country_data.cty_code] = country.id

    return code_to_id


# =============================================================================
# FACT TABLE LOADERS
# =============================================================================


def load_monthly_data(
    session: Session,
    rows: list[TradeRowData],
    code_to_id: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load monthly trade data.

    Args:
        session: SQLAlchemy session
        rows: Parsed trade rows
        code_to_id: Mapping from cty_code to country_id
        verbose: Show progress bar

    Returns:
        Number of records loaded
    """
    count = 0

    row_iter = tqdm(rows, desc="Monthly data", disable=not verbose)

    for row in row_iter:
        country_id = code_to_id.get(row.cty_code)
        if not country_id:
            continue

        # Insert one record per month
        for month_idx in range(12):
            imports_val = (
                row.monthly_imports[month_idx] if month_idx < len(row.monthly_imports) else None
            )
            exports_val = (
                row.monthly_exports[month_idx] if month_idx < len(row.monthly_exports) else None
            )

            # Skip if both are None
            if imports_val is None and exports_val is None:
                continue

            record = TradeMonthly(
                country_id=country_id,
                year=row.year,
                month=month_idx + 1,  # 1-indexed
                imports_usd_millions=imports_val,
                exports_usd_millions=exports_val,
            )
            session.add(record)
            count += 1

        # Batch commit every 10000 records
        if count % 10000 == 0:
            session.flush()

    return count


def load_annual_data(
    session: Session,
    rows: list[TradeRowData],
    code_to_id: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load annual trade aggregates.

    Args:
        session: SQLAlchemy session
        rows: Parsed trade rows
        code_to_id: Mapping from cty_code to country_id
        verbose: Show progress bar

    Returns:
        Number of records loaded
    """
    count = 0

    row_iter = tqdm(rows, desc="Annual data", disable=not verbose)

    for row in row_iter:
        country_id = code_to_id.get(row.cty_code)
        if not country_id:
            continue

        imports_total = row.annual_imports
        exports_total = row.annual_exports

        # Calculate trade balance (exports - imports)
        # Positive = US surplus, Negative = US deficit (extraction from that country)
        trade_balance = None
        if exports_total is not None and imports_total is not None:
            trade_balance = exports_total - imports_total

        record = TradeAnnual(
            country_id=country_id,
            year=row.year,
            imports_total=imports_total,
            exports_total=exports_total,
            trade_balance=trade_balance,
        )
        session.add(record)
        count += 1

    return count


# =============================================================================
# MAIN LOADER ORCHESTRATION
# =============================================================================


def init_trade_tables() -> None:
    """Create all trade database tables.

    Uses the shared research.sqlite database via CensusBase.
    """
    # Import schema to register all models with CensusBase.metadata
    from babylon.data.trade import schema  # noqa: F401

    CensusBase.metadata.create_all(bind=census_engine)


def reset_trade_tables() -> None:
    """Drop only trade tables, preserving census data."""
    from babylon.data.trade.schema import TradeAnnual, TradeCountry, TradeMonthly

    # Drop in reverse dependency order
    TradeMonthly.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]
    TradeAnnual.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]
    TradeCountry.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]


def load_trade_data(
    xlsx_path: Path,
    reset: bool = False,
    verbose: bool = True,
) -> dict[str, int]:
    """Load UN trade data into SQLite database.

    Args:
        xlsx_path: Path to country.xlsx file
        reset: If True, drop and recreate trade tables (census tables preserved)
        verbose: If True, show progress bars

    Returns:
        Dict with table names and record counts
    """
    # Reset trade tables only if requested
    if reset:
        if verbose:
            print("Resetting trade tables...")
        reset_trade_tables()

    # Initialize trade tables
    init_trade_tables()

    Session = sessionmaker(bind=census_engine)
    session = Session()

    stats: dict[str, int] = {}

    try:
        # Parse Excel file
        if verbose:
            print(f"Parsing {xlsx_path}...")
        data = parse_trade_excel(xlsx_path)

        if verbose:
            print(f"Found {len(data.countries)} countries, {len(data.rows)} rows")
            print(f"Year range: {data.year_range[0]} - {data.year_range[1]}")

        # Load countries
        if verbose:
            print("Loading countries...")
        code_to_id = load_countries(session, data)
        session.commit()
        stats["countries"] = len(code_to_id)

        # Load monthly data
        stats["monthly_records"] = load_monthly_data(session, data.rows, code_to_id, verbose)
        session.commit()

        # Load annual data
        stats["annual_records"] = load_annual_data(session, data.rows, code_to_id, verbose)
        session.commit()

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
