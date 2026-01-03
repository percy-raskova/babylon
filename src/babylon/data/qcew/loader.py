"""Batch loader for QCEW data into research.sqlite.

Loads BLS QCEW annual employment/wage data into normalized schema
with dimension tables (areas, industries, ownership) and fact table (annual).

Usage:
    from babylon.data.qcew.loader import load_qcew_data
    stats = load_qcew_data(Path("data/employment_industry/2024.annual.by_area"))
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select

from babylon.data.census.database import (
    CensusSessionLocal,
    census_engine,
    init_census_db,
)
from babylon.data.qcew.parser import (
    QcewRecord,
    determine_area_type,
    determine_naics_level,
    extract_state_fips,
    parse_all_area_files,
    parse_raw_csv_chunked,
)
from babylon.data.qcew.schema import (
    QcewAnnual,
    QcewArea,
    QcewIndustry,
    QcewOwnership,
    QcewRaw2022,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def load_ownership_dimension(session: Session) -> dict[str, int]:
    """Load ownership dimension table with standard BLS ownership codes.

    Args:
        session: SQLAlchemy session

    Returns:
        Mapping of own_code -> id
    """
    ownership_types = [
        ("0", "Total Covered"),
        ("1", "Federal Government"),
        ("2", "State Government"),
        ("3", "Local Government"),
        ("5", "Private"),
        ("8", "Total Government"),
        ("9", "Total U.I. Covered (Excludes Federal)"),
    ]

    code_to_id: dict[str, int] = {}

    for own_code, own_title in ownership_types:
        # Check if exists
        existing = session.execute(
            select(QcewOwnership).where(QcewOwnership.own_code == own_code)
        ).scalar_one_or_none()

        if existing:
            code_to_id[own_code] = existing.id
        else:
            ownership = QcewOwnership(own_code=own_code, own_title=own_title)
            session.add(ownership)
            session.flush()
            code_to_id[own_code] = ownership.id

    session.commit()
    return code_to_id


def load_dimensions_from_records(
    session: Session,
    records: list[QcewRecord],
    verbose: bool = True,
) -> tuple[dict[str, int], dict[str, int]]:
    """Extract and load unique areas and industries from records.

    Args:
        session: SQLAlchemy session
        records: List of parsed QCEW records
        verbose: Print progress

    Returns:
        Tuple of (area_fips -> id, industry_code -> id) mappings
    """
    # Collect unique areas and industries
    areas: dict[str, tuple[str, str, str | None]] = {}  # fips -> (title, type, state)
    industries: dict[str, tuple[str, int, str | None]] = {}  # code -> (title, level, parent)

    for rec in records:
        # Area
        if rec.area_fips not in areas:
            area_type = determine_area_type(rec.agglvl_code, rec.area_fips)
            state_fips = extract_state_fips(rec.area_fips)
            areas[rec.area_fips] = (rec.area_title, area_type, state_fips)

        # Industry
        if rec.industry_code not in industries:
            naics_level = determine_naics_level(rec.industry_code)
            # Determine parent code for hierarchy
            parent = None
            code = rec.industry_code
            if len(code) > 2 and code.isdigit():
                parent = code[:-1]
            industries[rec.industry_code] = (rec.industry_title, naics_level, parent)

    if verbose:
        print(f"Found {len(areas)} unique areas, {len(industries)} unique industries")

    # Load areas
    area_to_id: dict[str, int] = {}
    for area_fips, (area_title, area_type, state_fips) in areas.items():
        existing = session.execute(
            select(QcewArea).where(QcewArea.area_fips == area_fips)
        ).scalar_one_or_none()

        if existing:
            area_to_id[area_fips] = existing.id
        else:
            area = QcewArea(
                area_fips=area_fips,
                area_title=area_title,
                area_type=area_type,
                state_fips=state_fips,
            )
            session.add(area)
            session.flush()
            area_to_id[area_fips] = area.id

    session.commit()
    if verbose:
        print(f"Loaded {len(area_to_id)} areas into dimension table")

    # Load industries
    industry_to_id: dict[str, int] = {}
    for industry_code, (industry_title, naics_level, parent_code) in industries.items():
        existing_industry = session.execute(
            select(QcewIndustry).where(QcewIndustry.industry_code == industry_code)
        ).scalar_one_or_none()

        if existing_industry:
            industry_to_id[industry_code] = existing_industry.id
        else:
            industry = QcewIndustry(
                industry_code=industry_code,
                industry_title=industry_title,
                naics_level=naics_level,
                parent_code=parent_code,
            )
            session.add(industry)
            session.flush()
            industry_to_id[industry_code] = industry.id

    session.commit()
    if verbose:
        print(f"Loaded {len(industry_to_id)} industries into dimension table")

    return area_to_id, industry_to_id


def load_annual_facts(
    session: Session,
    records: list[QcewRecord],
    area_to_id: dict[str, int],
    industry_to_id: dict[str, int],
    ownership_to_id: dict[str, int],
    verbose: bool = True,
    batch_size: int = 50000,
) -> int:
    """Load annual fact table from records.

    Args:
        session: SQLAlchemy session
        records: List of parsed QCEW records
        area_to_id: Area FIPS -> ID mapping
        industry_to_id: Industry code -> ID mapping
        ownership_to_id: Ownership code -> ID mapping
        verbose: Print progress
        batch_size: Commit every N records

    Returns:
        Number of records loaded
    """
    count = 0
    skipped = 0

    for rec in records:
        # Lookup dimension IDs
        area_id = area_to_id.get(rec.area_fips)
        industry_id = industry_to_id.get(rec.industry_code)
        ownership_id = ownership_to_id.get(rec.own_code)

        if not all([area_id, industry_id, ownership_id]):
            skipped += 1
            continue

        annual = QcewAnnual(
            area_id=area_id,
            industry_id=industry_id,
            ownership_id=ownership_id,
            year=rec.year,
            establishments=rec.establishments,
            employment=rec.employment,
            total_wages=rec.total_wages,
            avg_weekly_wage=rec.avg_weekly_wage,
            avg_annual_pay=rec.avg_annual_pay,
            lq_employment=rec.lq_employment,
            lq_avg_annual_pay=rec.lq_avg_annual_pay,
            oty_employment_chg=rec.oty_employment_chg,
            oty_employment_pct=rec.oty_employment_pct,
            disclosure_code=rec.disclosure_code,
        )
        session.add(annual)
        count += 1

        # Batch commit
        if count % batch_size == 0:
            session.commit()
            if verbose:
                print(f"  Loaded {count:,} records...")

    session.commit()

    if verbose:
        print(f"Loaded {count:,} annual records (skipped {skipped} with missing dimensions)")

    return count


def load_qcew_data(
    data_dir: Path,
    reset: bool = False,
    verbose: bool = True,
) -> dict[str, int]:
    """Load QCEW data from by_area directory into research.sqlite.

    Args:
        data_dir: Path to 2024.annual.by_area directory
        reset: If True, drop and recreate QCEW tables
        verbose: Print progress

    Returns:
        Dictionary with record counts by table
    """
    if verbose:
        print(f"Loading QCEW data from {data_dir}")

    # Reset tables if requested
    if reset:
        if verbose:
            print("Resetting QCEW tables...")
        QcewAnnual.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]
        QcewArea.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]
        QcewIndustry.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]
        QcewOwnership.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]

    # Ensure tables exist
    init_census_db()

    session = CensusSessionLocal()

    try:
        # Step 1: Load ownership dimension (static)
        if verbose:
            print("Loading ownership dimension...")
        ownership_to_id = load_ownership_dimension(session)

        # Step 2: Parse all records into memory
        if verbose:
            print("Parsing CSV files (this may take a while)...")

        records: list[QcewRecord] = []
        file_count = 0
        for rec in parse_all_area_files(data_dir):
            records.append(rec)
            if len(records) % 100000 == 0 and verbose:
                print(f"  Parsed {len(records):,} records...")

        file_count = len(list(data_dir.glob("*.csv")))
        if verbose:
            print(f"Parsed {len(records):,} records from {file_count} files")

        # Step 3: Load dimension tables
        if verbose:
            print("Loading dimension tables...")
        area_to_id, industry_to_id = load_dimensions_from_records(session, records, verbose)

        # Step 4: Load fact table
        if verbose:
            print("Loading annual fact table...")
        annual_count = load_annual_facts(
            session,
            records,
            area_to_id,
            industry_to_id,
            ownership_to_id,
            verbose,
        )

        return {
            "files": file_count,
            "records_parsed": len(records),
            "areas": len(area_to_id),
            "industries": len(industry_to_id),
            "ownership_types": len(ownership_to_id),
            "annual_facts": annual_count,
        }

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to load QCEW data: {e}") from e
    finally:
        session.close()


# =============================================================================
# RAW DATA LOADERS (Denormalized bulk ingestion)
# =============================================================================


def load_raw_2022_data(
    csv_path: Path,
    reset: bool = False,
    verbose: bool = True,
    chunk_size: int = 100_000,
) -> dict[str, int]:
    """Load raw QCEW 2022 CSV into qcew_raw_2022 table.

    Uses pandas to_sql() for fast bulk insertion (not row-by-row).

    Args:
        csv_path: Path to 2022.annual.singlefile.csv
        reset: If True, drop and recreate table
        verbose: Print progress
        chunk_size: Rows per chunk for pandas read_csv

    Returns:
        Dict with statistics (total_rows, chunks_processed)
    """

    if verbose:
        print(f"Loading raw QCEW 2022 data from {csv_path}")

    # Reset table if requested
    if reset:
        if verbose:
            print("Dropping qcew_raw_2022 table...")
        QcewRaw2022.__table__.drop(bind=census_engine, checkfirst=True)  # type: ignore[attr-defined]

    # Ensure table exists
    init_census_db()

    total_rows = 0
    chunks_processed = 0

    try:
        for chunk in parse_raw_csv_chunked(csv_path, chunk_size=chunk_size):
            chunks_processed += 1

            # Rename columns to match DB schema (most are same)
            # Fill NaN strings with empty string for text columns
            chunk["disclosure_code"] = chunk["disclosure_code"].fillna("")
            chunk["lq_disclosure_code"] = chunk["lq_disclosure_code"].fillna("")
            chunk["oty_disclosure_code"] = chunk["oty_disclosure_code"].fillna("")
            chunk["area_fips"] = chunk["area_fips"].fillna("")
            chunk["own_code"] = chunk["own_code"].fillna("0")
            chunk["industry_code"] = chunk["industry_code"].fillna("10")
            chunk["qtr"] = chunk["qtr"].fillna("A")

            # Fill NaN integers with 0 for required fields
            chunk["agglvl_code"] = chunk["agglvl_code"].fillna(0)
            chunk["size_code"] = chunk["size_code"].fillna(0)
            chunk["year"] = chunk["year"].fillna(2022)

            # Use pandas to_sql for bulk insert (executemany is fast enough for SQLite)
            chunk.to_sql(
                "qcew_raw_2022",
                census_engine,
                if_exists="append",
                index=False,
                # Don't use method="multi" - SQLite has variable limit (999)
            )

            total_rows += len(chunk)

            if verbose:
                print(
                    f"  Chunk {chunks_processed}: Loaded {len(chunk):,} rows (total: {total_rows:,})"
                )

        if verbose:
            print(f"Completed: {total_rows:,} rows in {chunks_processed} chunks")

        return {
            "total_rows": total_rows,
            "chunks_processed": chunks_processed,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to load raw QCEW 2022 data: {e}") from e


def print_class_composition(verbose: bool = True) -> dict[str, int | float]:
    """Print class composition validation after ingestion.

    Queries the raw 2022 data to show:
    - Total Employment in "Goods Producing" (industry_code 101)
    - Total Employment in "Service Providing" (industry_code 102)
    - Total Government Employment (own_code != 5)

    Uses national-level data (agglvl_code < 20) to avoid double-counting.

    Args:
        verbose: Print results

    Returns:
        Dict with employment totals by category
    """
    from sqlalchemy import func

    session = CensusSessionLocal()

    try:
        # Check if data exists
        total_count = session.query(func.count(QcewRaw2022.id)).scalar()
        if total_count == 0:
            if verbose:
                print("No data in qcew_raw_2022 table - run ingestion first")
            return {}

        # National level, Private, Goods Producing (101)
        goods_employment = (
            session.query(func.sum(QcewRaw2022.annual_avg_emplvl))
            .filter(
                QcewRaw2022.industry_code == "101",
                QcewRaw2022.own_code == "5",  # Private
                QcewRaw2022.agglvl_code < 20,  # National level
            )
            .scalar()
            or 0
        )

        # National level, Private, Service Providing (102)
        service_employment = (
            session.query(func.sum(QcewRaw2022.annual_avg_emplvl))
            .filter(
                QcewRaw2022.industry_code == "102",
                QcewRaw2022.own_code == "5",  # Private
                QcewRaw2022.agglvl_code < 20,  # National level
            )
            .scalar()
            or 0
        )

        # National level, Government (own_code 1, 2, 3), Total Industry (10)
        gov_employment = (
            session.query(func.sum(QcewRaw2022.annual_avg_emplvl))
            .filter(
                QcewRaw2022.industry_code == "10",  # Total all industries
                QcewRaw2022.own_code.in_(["1", "2", "3"]),  # Fed, State, Local
                QcewRaw2022.agglvl_code < 20,  # National level
            )
            .scalar()
            or 0
        )

        # National level, Total Covered (own_code 0)
        total_employment = (
            session.query(func.sum(QcewRaw2022.annual_avg_emplvl))
            .filter(
                QcewRaw2022.industry_code == "10",  # Total all industries
                QcewRaw2022.own_code == "0",  # Total Covered
                QcewRaw2022.agglvl_code < 20,  # National level
            )
            .scalar()
            or 0
        )

        # Calculate ratios
        parasitism_index = service_employment / goods_employment if goods_employment > 0 else 0

        if verbose:
            print("\n" + "=" * 50)
            print("CLASS COMPOSITION (2022)")
            print("=" * 50)
            print(f"Goods Producing (Private):     {goods_employment:>12,}")
            print(f"Service Providing (Private):  {service_employment:>12,}")
            print(f"Government (Fed+State+Local): {gov_employment:>12,}")
            print(f"Total Covered Employment:     {total_employment:>12,}")
            print("-" * 50)
            print(f"Parasitism Index (Service/Goods): {parasitism_index:.2f}")
            print("=" * 50)

        return {
            "goods_producing": int(goods_employment),
            "service_providing": int(service_employment),
            "government": int(gov_employment),
            "total_covered": int(total_employment),
            "parasitism_index": parasitism_index,
        }

    finally:
        session.close()


__all__ = [
    "load_qcew_data",
    "load_ownership_dimension",
    "load_dimensions_from_records",
    "load_annual_facts",
    "load_raw_2022_data",
    "print_class_composition",
]
