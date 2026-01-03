"""USGS materials data loader for batch ingestion into SQLite.

Orchestrates parsing USGS MCS CSV files and loading them into the
research.sqlite database using batch inserts.

Example:
    from babylon.data.materials import load_materials_data

    stats = load_materials_data(Path("data/raw_mats"), reset=True)
    print(f"Loaded {stats.observations_loaded} observations "
          f"from {stats.commodities_loaded} commodities")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from babylon.data.census.database import CensusBase, census_engine, get_census_db
from babylon.data.materials.parser import (
    CommodityRecord,
    StateRecord,
    TrendRecord,
    discover_aggregate_files,
    discover_commodity_files,
    get_metric_category,
    parse_commodity_csv,
    parse_state_csv,
    parse_trends_csv,
)
from babylon.data.materials.schema import (
    CRITICAL_MINERALS,
    METRIC_INTERPRETATIONS,
    Commodity,
    CommodityMetric,
    CommodityObservation,
    ImportSource,
    MaterialsState,
    MineralTrend,
    StateMineral,
)

logger = logging.getLogger(__name__)

# State FIPS codes for geographic joins
STATE_FIPS: dict[str, str] = {
    "Alabama": "01",
    "Alaska": "02",
    "Arizona": "04",
    "Arkansas": "05",
    "California": "06",
    "Colorado": "08",
    "Connecticut": "09",
    "Delaware": "10",
    "Florida": "12",
    "Georgia": "13",
    "Hawaii": "15",
    "Idaho": "16",
    "Illinois": "17",
    "Indiana": "18",
    "Iowa": "19",
    "Kansas": "20",
    "Kentucky": "21",
    "Louisiana": "22",
    "Maine": "23",
    "Maryland": "24",
    "Massachusetts": "25",
    "Michigan": "26",
    "Minnesota": "27",
    "Mississippi": "28",
    "Missouri": "29",
    "Montana": "30",
    "Nebraska": "31",
    "Nevada": "32",
    "New Hampshire": "33",
    "New Jersey": "34",
    "New Mexico": "35",
    "New York": "36",
    "North Carolina": "37",
    "North Dakota": "38",
    "Ohio": "39",
    "Oklahoma": "40",
    "Oregon": "41",
    "Pennsylvania": "42",
    "Rhode Island": "44",
    "South Carolina": "45",
    "South Dakota": "46",
    "Tennessee": "47",
    "Texas": "48",
    "Utah": "49",
    "Vermont": "50",
    "Virginia": "51",
    "Washington": "53",
    "West Virginia": "54",
    "Wisconsin": "55",
    "Wyoming": "56",
    "District of Columbia": "11",
}


@dataclass
class MaterialsLoadStats:
    """Statistics from materials data loading."""

    commodities_loaded: int = 0
    metrics_loaded: int = 0
    observations_loaded: int = 0
    states_loaded: int = 0
    state_minerals_loaded: int = 0
    trends_loaded: int = 0
    import_sources_loaded: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def init_materials_tables() -> None:
    """Create materials tables if they don't exist."""
    # Import schema to register models
    from babylon.data.materials import schema  # noqa: F401

    CensusBase.metadata.create_all(bind=census_engine)


def reset_materials_tables() -> None:  # noqa: C901
    """Drop and recreate materials tables.

    Preserves other research tables (Census, QCEW, FRED, Energy, etc.).
    """
    from sqlalchemy import inspect

    # First ensure tables exist
    init_materials_tables()

    # Check which tables exist
    inspector = inspect(census_engine)
    existing_tables = inspector.get_table_names()

    db = next(get_census_db())
    try:
        # Delete from fact tables first (foreign key constraints)
        if "commodity_observations" in existing_tables:
            db.execute(delete(CommodityObservation))
        if "state_minerals" in existing_tables:
            db.execute(delete(StateMineral))
        if "mineral_trends" in existing_tables:
            db.execute(delete(MineralTrend))

        # Then dimension tables
        if "commodity_metrics" in existing_tables:
            db.execute(delete(CommodityMetric))
        if "commodities" in existing_tables:
            db.execute(delete(Commodity))
        if "materials_states" in existing_tables:
            db.execute(delete(MaterialsState))
        if "import_sources" in existing_tables:
            db.execute(delete(ImportSource))

        db.commit()
    finally:
        db.close()


def _load_commodity_dimension(
    db: Session,
    commodity_code: str,
    commodity_name: str,
    _verbose: bool = True,
) -> int:
    """Load or get commodity dimension.

    Args:
        db: Database session.
        commodity_code: Short code (e.g., "lithium").
        commodity_name: Full name (e.g., "Lithium").
        verbose: Print progress.

    Returns:
        Database ID for the commodity.
    """
    # Check if exists
    existing = db.query(Commodity).filter(Commodity.code == commodity_code).first()
    if existing:
        return existing.id

    is_critical = commodity_code in CRITICAL_MINERALS

    commodity = Commodity(
        code=commodity_code,
        name=commodity_name,
        is_critical=is_critical,
    )
    db.add(commodity)
    db.flush()

    return commodity.id


def _load_metric_dimension(
    db: Session,
    metric_code: str,
    metric_name: str,
    _verbose: bool = True,
) -> int:
    """Load or get metric dimension.

    Args:
        db: Database session.
        metric_code: Metric code (e.g., "USprod_t").
        metric_name: Human-readable name.
        verbose: Print progress.

    Returns:
        Database ID for the metric.
    """
    # Check if exists
    existing = db.query(CommodityMetric).filter(CommodityMetric.code == metric_code).first()
    if existing:
        return existing.id

    category = get_metric_category(metric_code)

    # Get Marxian interpretation if available
    marxian = None
    for key, interp in METRIC_INTERPRETATIONS.items():
        if key in metric_code.upper():
            marxian = interp
            break

    # Infer units from metric code
    units = None
    code_lower = metric_code.lower()
    if "_t" in code_lower or "_kt" in code_lower:
        units = "metric tons" if "_t" in code_lower else "thousand metric tons"
    elif "_pct" in code_lower:
        units = "percent"
    elif "_num" in code_lower:
        units = "number"
    elif "_dt" in code_lower or "_dols" in code_lower:
        units = "dollars"

    metric = CommodityMetric(
        code=metric_code,
        name=metric_name,
        units=units,
        category=category,
        marxian_interpretation=marxian,
    )
    db.add(metric)
    db.flush()

    return metric.id


def _load_commodity_observations(
    db: Session,
    records: list[CommodityRecord],
    commodity_code_to_id: dict[str, int],
    metric_code_to_id: dict[str, int],
    _verbose: bool = True,
) -> int:
    """Load commodity observations from parsed records.

    Args:
        db: Database session.
        records: List of parsed commodity records.
        commodity_code_to_id: Mapping of commodity codes to IDs.
        metric_code_to_id: Mapping of metric codes to IDs.
        verbose: Print progress.

    Returns:
        Number of observations loaded.
    """
    count = 0
    batch: list[CommodityObservation] = []

    for record in records:
        commodity_id = commodity_code_to_id.get(record.commodity_code)
        metric_id = metric_code_to_id.get(record.metric_code)

        if commodity_id is None or metric_id is None:
            continue

        obs = CommodityObservation(
            commodity_id=commodity_id,
            metric_id=metric_id,
            year=record.year,
            value=record.value,
            value_text=record.value_text,
        )
        batch.append(obs)
        count += 1

        # Batch insert every 500 records
        if len(batch) >= 500:
            db.add_all(batch)
            db.flush()
            batch = []

    # Insert remaining
    if batch:
        db.add_all(batch)
        db.flush()

    return count


def _load_states_dimension(db: Session, verbose: bool = True) -> dict[str, int]:
    """Load states dimension table.

    Args:
        db: Database session.
        verbose: Print progress.

    Returns:
        Mapping of state names to database IDs.
    """
    state_name_to_id: dict[str, int] = {}

    for state_name, fips_code in STATE_FIPS.items():
        existing = db.query(MaterialsState).filter(MaterialsState.name == state_name).first()
        if existing:
            state_name_to_id[state_name] = existing.id
            continue

        state = MaterialsState(name=state_name, fips_code=fips_code)
        db.add(state)
        db.flush()
        state_name_to_id[state_name] = state.id

    if verbose:
        logger.info(f"  Loaded {len(state_name_to_id)} states")

    return state_name_to_id


def _load_state_minerals(
    db: Session,
    records: list[StateRecord],
    state_name_to_id: dict[str, int],
    _verbose: bool = True,
) -> int:
    """Load state mineral production data.

    Args:
        db: Database session.
        records: List of parsed state records.
        state_name_to_id: Mapping of state names to IDs.
        verbose: Print progress.

    Returns:
        Number of state mineral records loaded.
    """
    count = 0

    for record in records:
        state_id = state_name_to_id.get(record.state_name)
        if state_id is None:
            # Try to add missing state
            state = MaterialsState(name=record.state_name, fips_code=None)
            db.add(state)
            db.flush()
            state_name_to_id[record.state_name] = state.id
            state_id = state.id

        mineral = StateMineral(
            state_id=state_id,
            year=record.year,
            value_millions=record.value_millions,
            rank=record.rank,
            percent_total=record.percent_total,
            principal_commodities=record.principal_commodities,
        )
        db.add(mineral)
        count += 1

    db.flush()
    return count


def _load_trends(
    db: Session,
    records: list[TrendRecord],
    _verbose: bool = True,
) -> int:
    """Load mineral industry trends.

    Args:
        db: Database session.
        records: List of parsed trend records.
        verbose: Print progress.

    Returns:
        Number of trend records loaded.
    """
    count = 0

    for record in records:
        values = record.values

        trend = MineralTrend(
            year=record.year,
            mine_production_metals_millions=values.get("Mine_Production_Metals_mil_dols"),
            mine_production_industrial_millions=values.get("Mine_Production_Industrial_mil_dols"),
            mine_production_coal_millions=values.get("Mine_Production_Coal_mil_dols"),
            employment_coal_thousands=values.get("Employment_All_Coal_thsnds"),
            employment_nonfuel_thousands=values.get("Employment_All_Nonfuel_thsnds"),
            employment_chemicals_thousands=values.get("Employment_Chemicals_thsnds"),
            employment_stone_clay_glass_thousands=values.get("Employment_Stone_Clay_Glass_thsnds"),
            employment_primary_metal_thousands=values.get("Employment_Primary_Metal_thsnds"),
            avg_weekly_earnings_coal=values.get("Avg_Weekly_Earnings_All_Coal_dols"),
            avg_weekly_earnings_all=values.get("Avg_Weekly_Earnings_dols"),
            avg_weekly_earnings_stone_clay_glass=values.get(
                "Avg_Weekly_Earnings_Stone_Clay_Glass_dols"
            ),
            avg_weekly_earnings_primary_metal=values.get("Avg_Weekly_Earnings_Primary_Metal_dols"),
        )
        db.add(trend)
        count += 1

    db.flush()
    return count


def load_materials_data(  # noqa: C901
    materials_dir: Path,
    reset: bool = False,
    verbose: bool = True,
) -> MaterialsLoadStats:
    """Load USGS MCS materials data into SQLite.

    Args:
        materials_dir: Path to data/raw_mats/ directory.
        reset: Drop and recreate materials tables.
        verbose: Print progress messages.

    Returns:
        MaterialsLoadStats with counts.
    """
    stats = MaterialsLoadStats()

    # Initialize or reset tables
    if reset:
        if verbose:
            print("Resetting materials tables...")
        reset_materials_tables()
    else:
        init_materials_tables()

    # Discover files
    commodity_files = discover_commodity_files(materials_dir)
    aggregate_files = discover_aggregate_files(materials_dir)

    if not commodity_files and not any(aggregate_files.values()):
        stats.errors.append(f"No materials files found in {materials_dir}")
        return stats

    if verbose:
        print(f"Found {len(commodity_files)} commodity files")
        print(f"Found aggregate files: {[k for k, v in aggregate_files.items() if v]}")

    db = next(get_census_db())
    try:
        # Track dimension mappings
        commodity_code_to_id: dict[str, int] = {}
        metric_code_to_id: dict[str, int] = {}
        all_records: list[CommodityRecord] = []

        # First pass: parse all files and collect dimensions
        for file_path in commodity_files:
            if verbose:
                print(f"\nParsing {file_path.name}...")

            try:
                records = parse_commodity_csv(file_path)
                stats.files_processed += 1

                # Collect unique commodities and metrics
                for record in records:
                    if record.commodity_code not in commodity_code_to_id:
                        commodity_id = _load_commodity_dimension(
                            db, record.commodity_code, record.commodity_name, verbose
                        )
                        commodity_code_to_id[record.commodity_code] = commodity_id
                        stats.commodities_loaded += 1

                    if record.metric_code not in metric_code_to_id:
                        metric_id = _load_metric_dimension(
                            db, record.metric_code, record.metric_name, verbose
                        )
                        metric_code_to_id[record.metric_code] = metric_id
                        stats.metrics_loaded += 1

                all_records.extend(records)

            except Exception as e:
                error_msg = f"Error parsing {file_path.name}: {e}"
                stats.errors.append(error_msg)
                stats.files_skipped += 1
                if verbose:
                    print(f"  ERROR: {e}")

        # Commit dimensions
        db.commit()

        if verbose:
            print(
                f"\nLoaded {stats.commodities_loaded} commodities, {stats.metrics_loaded} metrics"
            )
            print(f"Loading {len(all_records)} observations...")

        # Load all observations
        obs_count = _load_commodity_observations(
            db, all_records, commodity_code_to_id, metric_code_to_id, verbose
        )
        stats.observations_loaded = obs_count
        db.commit()

        # Load aggregate data
        # States
        if aggregate_files["states"]:
            if verbose:
                print(f"\nLoading state data from {aggregate_files['states'].name}...")
            state_name_to_id = _load_states_dimension(db, verbose)
            stats.states_loaded = len(state_name_to_id)

            state_records = parse_state_csv(aggregate_files["states"])
            state_count = _load_state_minerals(db, state_records, state_name_to_id, verbose)
            stats.state_minerals_loaded = state_count
            db.commit()

        # Trends
        if aggregate_files["trends"]:
            if verbose:
                print(f"\nLoading trends from {aggregate_files['trends'].name}...")
            trend_records = parse_trends_csv(aggregate_files["trends"])
            trend_count = _load_trends(db, trend_records, verbose)
            stats.trends_loaded = trend_count
            db.commit()

    except Exception as e:
        stats.errors.append(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    if verbose:
        print("\nMaterials data loading complete!")
        print(f"  Commodities: {stats.commodities_loaded}")
        print(f"  Metrics: {stats.metrics_loaded}")
        print(f"  Observations: {stats.observations_loaded}")
        print(f"  States: {stats.states_loaded}")
        print(f"  State minerals: {stats.state_minerals_loaded}")
        print(f"  Trends: {stats.trends_loaded}")
        if stats.errors:
            print(f"  Errors: {len(stats.errors)}")

    return stats
