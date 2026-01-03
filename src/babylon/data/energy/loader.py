"""EIA energy data loader for batch ingestion into SQLite.

Orchestrates parsing EIA MER Excel files and loading them into the
research.sqlite database using batch inserts.

Example:
    from babylon.data.energy import load_energy_data

    stats = load_energy_data(Path("data/energy"), reset=True)
    print(f"Loaded {stats.observations_loaded} observations "
          f"from {stats.tables_loaded} tables")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from babylon.data.census.database import CensusBase, census_engine, get_census_db
from babylon.data.energy.parser import (
    EnergyTableData,
    discover_energy_files,
    parse_energy_excel,
)
from babylon.data.energy.schema import (
    EIA_PRIORITY_TABLES,
    EnergyAnnual,
    EnergySeries,
    EnergyTable,
)

logger = logging.getLogger(__name__)


@dataclass
class EnergyLoadStats:
    """Statistics from energy data loading."""

    tables_loaded: int = 0
    series_loaded: int = 0
    observations_loaded: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def init_energy_tables() -> None:
    """Create energy tables if they don't exist."""
    # Import schema to register models
    from babylon.data.energy import schema  # noqa: F401

    CensusBase.metadata.create_all(bind=census_engine)


def reset_energy_tables() -> None:  # noqa: C901
    """Drop and recreate energy tables.

    Preserves other research tables (Census, QCEW, FRED, Trade, Productivity).
    """
    from sqlalchemy import inspect

    # First ensure tables exist
    init_energy_tables()

    # Check which tables exist
    inspector = inspect(census_engine)
    existing_tables = inspector.get_table_names()

    db = next(get_census_db())
    try:
        # Delete from fact tables first (foreign key constraints)
        if "energy_annual" in existing_tables:
            db.execute(delete(EnergyAnnual))

        # Then dimension tables (series before tables due to FK)
        if "energy_series" in existing_tables:
            db.execute(delete(EnergySeries))
        if "energy_tables" in existing_tables:
            db.execute(delete(EnergyTable))

        db.commit()
    finally:
        db.close()


def _load_table_dimension(
    db: Session,
    table_code: str,
    table_title: str,
    verbose: bool = True,
) -> int:
    """Load or get energy table dimension.

    Args:
        db: Database session.
        table_code: EIA table code (e.g., "01.01").
        table_title: Table title from Excel.
        verbose: Print progress.

    Returns:
        Database ID for the table.
    """
    # Check if exists
    existing = db.query(EnergyTable).filter(EnergyTable.table_code == table_code).first()
    if existing:
        return existing.id

    # Get metadata from priority tables config
    table_config = EIA_PRIORITY_TABLES.get(table_code, {})
    category = table_config.get("category", "other")
    marxian = table_config.get("marxian")

    table = EnergyTable(
        table_code=table_code,
        title=table_title,
        category=category,
        marxian_interpretation=marxian,
    )
    db.add(table)
    db.flush()

    if verbose:
        logger.info(f"  Loaded table dimension: {table_code}")

    return table.id


def _load_series_dimensions(
    db: Session,
    table_id: int,
    series_list: list[dict[str, str | int]],
    verbose: bool = True,
) -> dict[str, int]:
    """Load series dimensions for a table.

    Args:
        db: Database session.
        table_id: Parent table ID.
        series_list: List of series metadata dicts.
        verbose: Print progress.

    Returns:
        Mapping of series_name to database ID.
    """
    name_to_id: dict[str, int] = {}

    for series_info in series_list:
        series_name = str(series_info["series_name"])
        units = str(series_info["units"])
        column_index = int(series_info["column_index"])

        # Check if exists
        existing = (
            db.query(EnergySeries)
            .filter(
                EnergySeries.table_id == table_id,
                EnergySeries.series_name == series_name,
            )
            .first()
        )
        if existing:
            name_to_id[series_name] = existing.id
            continue

        series = EnergySeries(
            table_id=table_id,
            series_name=series_name,
            units=units,
            column_index=column_index,
        )
        db.add(series)
        db.flush()
        name_to_id[series_name] = series.id

    if verbose and name_to_id:
        logger.info(f"  Loaded {len(name_to_id)} series dimensions")

    return name_to_id


def _load_observations(
    db: Session,
    table_data: EnergyTableData,
    series_name_to_id: dict[str, int],
    verbose: bool = True,
) -> int:
    """Load annual observations from parsed data.

    Args:
        db: Database session.
        table_data: Parsed table data.
        series_name_to_id: Mapping of series names to IDs.
        verbose: Print progress.

    Returns:
        Number of observations loaded.
    """
    count = 0
    batch: list[EnergyAnnual] = []

    for record in table_data.records:
        series_id = series_name_to_id.get(record.series_name)
        if series_id is None:
            continue

        obs = EnergyAnnual(
            series_id=series_id,
            year=record.year,
            value=record.value,
        )
        batch.append(obs)
        count += 1

        # Batch insert every 1000 records
        if len(batch) >= 1000:
            db.add_all(batch)
            db.flush()
            batch = []

    # Insert remaining
    if batch:
        db.add_all(batch)
        db.flush()

    if verbose:
        logger.info(f"  Loaded {count} observations")

    return count


def load_energy_data(
    energy_dir: Path,
    reset: bool = False,
    verbose: bool = True,
    priority_only: bool = True,
) -> EnergyLoadStats:
    """Load EIA MER energy data into SQLite.

    Args:
        energy_dir: Path to data/energy/ directory.
        reset: Drop and recreate energy tables.
        verbose: Print progress messages.
        priority_only: Only load priority tables (default True).

    Returns:
        EnergyLoadStats with counts.
    """
    stats = EnergyLoadStats()

    # Initialize or reset tables
    if reset:
        if verbose:
            print("Resetting energy tables...")
        reset_energy_tables()
    else:
        init_energy_tables()

    # Discover files
    priority_tables = set(EIA_PRIORITY_TABLES.keys()) if priority_only else None
    files = discover_energy_files(energy_dir, priority_tables)

    if not files:
        stats.errors.append(f"No energy files found in {energy_dir}")
        return stats

    if verbose:
        print(f"Found {len(files)} energy files to process")

    # Process each file
    db = next(get_census_db())
    try:
        for _table_code, file_path in sorted(files.items()):
            if verbose:
                print(f"\nProcessing {file_path.name}...")

            try:
                # Parse Excel file
                table_data = parse_energy_excel(file_path)
                stats.files_processed += 1

                # Load table dimension
                table_id = _load_table_dimension(
                    db, table_data.table_code, table_data.table_title, verbose
                )
                stats.tables_loaded += 1

                # Load series dimensions
                series_name_to_id = _load_series_dimensions(
                    db, table_id, table_data.series, verbose
                )
                stats.series_loaded += len(series_name_to_id)

                # Load observations
                obs_count = _load_observations(db, table_data, series_name_to_id, verbose)
                stats.observations_loaded += obs_count

                db.commit()

            except Exception as e:
                error_msg = f"Error processing {file_path.name}: {e}"
                stats.errors.append(error_msg)
                stats.files_skipped += 1
                if verbose:
                    print(f"  ERROR: {e}")
                db.rollback()

    finally:
        db.close()

    if verbose:
        print("\nEnergy data loading complete!")
        print(f"  Tables: {stats.tables_loaded}")
        print(f"  Series: {stats.series_loaded}")
        print(f"  Observations: {stats.observations_loaded}")
        if stats.errors:
            print(f"  Errors: {len(stats.errors)}")

    return stats
