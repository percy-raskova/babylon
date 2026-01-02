"""Batch ingestion for BLS Industry Productivity data.

Loads parsed Excel data into SQLite database, creating dimension
and fact tables joinable with QCEW via NAICS codes.

Usage:
    from babylon.data.productivity.loader import load_productivity_data
    from pathlib import Path

    stats = load_productivity_data(Path("data/productivity"), year=2022, reset=True)
"""

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from babylon.data.census.database import get_census_db, init_census_db
from babylon.data.productivity.parser import (
    ParsedProductivityData,
    discover_available_years,
    parse_productivity_data,
)
from babylon.data.productivity.schema import ProductivityAnnual, ProductivityIndustry


@dataclass
class LoadStats:
    """Statistics from productivity data load."""

    industries_loaded: int = 0
    records_loaded: int = 0
    year: int = 0
    available_years: list[int] = field(default_factory=list)


def _reset_productivity_tables(db: Session) -> None:
    """Drop and recreate productivity tables."""
    # Delete in reverse FK order
    db.execute(delete(ProductivityAnnual))
    db.execute(delete(ProductivityIndustry))
    db.commit()


def _load_industries(
    db: Session,
    data: ParsedProductivityData,
) -> dict[str, int]:
    """Load industry dimension table.

    Args:
        db: Database session
        data: Parsed productivity data

    Returns:
        Mapping of naics_code -> industry_id for FK lookups
    """
    naics_to_id: dict[str, int] = {}

    for industry in data.industries:
        record = ProductivityIndustry(
            naics_code=industry.naics_code,
            industry_title=industry.industry_title,
            sector=industry.sector,
            digit_level=industry.digit_level,
        )
        db.add(record)
        db.flush()  # Get the ID
        naics_to_id[industry.naics_code] = record.id

    db.commit()
    return naics_to_id


def _load_annual_records(
    db: Session,
    data: ParsedProductivityData,
    naics_to_id: dict[str, int],
) -> int:
    """Load annual productivity fact records.

    Args:
        db: Database session
        data: Parsed productivity data
        naics_to_id: Mapping of naics_code -> industry_id

    Returns:
        Count of records loaded
    """
    count = 0
    batch: list[ProductivityAnnual] = []
    batch_size = 500

    for record in data.records:
        industry_id = naics_to_id.get(record.naics_code)
        if industry_id is None:
            continue  # Skip if industry not found

        annual = ProductivityAnnual(
            industry_id=industry_id,
            year=record.year,
            labor_productivity_index=record.labor_productivity_index,
            labor_productivity_pct_chg=record.labor_productivity_pct_chg,
            hours_worked_index=record.hours_worked_index,
            hours_worked_millions=record.hours_worked_millions,
            employment_thousands=record.employment_thousands,
            hourly_compensation_index=record.hourly_compensation_index,
            unit_labor_costs_index=record.unit_labor_costs_index,
            real_output_index=record.real_output_index,
            sectoral_output_index=record.sectoral_output_index,
            labor_compensation_millions=record.labor_compensation_millions,
            sectoral_output_millions=record.sectoral_output_millions,
        )
        batch.append(annual)
        count += 1

        if len(batch) >= batch_size:
            db.add_all(batch)
            db.commit()
            batch = []

    # Final batch
    if batch:
        db.add_all(batch)
        db.commit()

    return count


def load_productivity_data(
    productivity_dir: Path,
    year: int = 2022,
    reset: bool = False,
) -> LoadStats:
    """Load BLS productivity data into SQLite.

    Args:
        productivity_dir: Path to data/productivity/ directory
        year: Year to load (default: 2022)
        reset: If True, drop and recreate productivity tables

    Returns:
        LoadStats with counts and metadata

    Raises:
        FileNotFoundError: If Excel files not found
    """
    # Initialize database (creates tables if needed)
    init_census_db()

    # Get database session
    db = next(get_census_db())

    try:
        # Discover available years
        available_years = discover_available_years(productivity_dir)

        if reset:
            _reset_productivity_tables(db)

        # Parse Excel files
        data = parse_productivity_data(productivity_dir, year=year)

        # Load dimension table
        naics_to_id = _load_industries(db, data)

        # Load fact table
        records_count = _load_annual_records(db, data, naics_to_id)

        return LoadStats(
            industries_loaded=len(naics_to_id),
            records_loaded=records_count,
            year=year,
            available_years=available_years,
        )

    finally:
        db.close()


def load_multi_year_productivity(
    productivity_dir: Path,
    years: list[int] | None = None,
    reset: bool = False,
) -> LoadStats:
    """Load multiple years of productivity data.

    Args:
        productivity_dir: Path to data/productivity/ directory
        years: Years to load (default: all available)
        reset: If True, drop and recreate tables first

    Returns:
        LoadStats with aggregate counts
    """
    init_census_db()
    db = next(get_census_db())

    try:
        available_years = discover_available_years(productivity_dir)

        if years is None:
            years = available_years

        if reset:
            _reset_productivity_tables(db)

        # Load industries once from first year
        first_data = parse_productivity_data(productivity_dir, year=years[0])
        naics_to_id = _load_industries(db, first_data)

        # Load all years' fact records
        total_records = 0
        for year in years:
            data = parse_productivity_data(productivity_dir, year=year)
            count = _load_annual_records(db, data, naics_to_id)
            total_records += count

        return LoadStats(
            industries_loaded=len(naics_to_id),
            records_loaded=total_records,
            year=years[-1],  # Last year loaded
            available_years=available_years,
        )

    finally:
        db.close()
