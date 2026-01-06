"""USGS Materials data loader for direct 3NF schema population.

Loads USGS Mineral Commodity Summaries data directly into the normalized
marxist-data-3NF.sqlite schema.

This loader replaces the legacy loader (loader.py) with a direct
3NF approach using LoaderConfig for parameterization.

Example:
    from babylon.data.materials import MaterialsLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(materials_years=list(range(2015, 2025)))
    loader = MaterialsLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, data_path=Path("data/raw_mats"))
        print(f"Loaded {stats.facts_loaded} commodity observations")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.materials.parser import (
    discover_commodity_files,
    get_metric_category,
    parse_commodity_csv,
)
from babylon.data.normalize.schema import (
    DimCommodity,
    DimCommodityMetric,
    DimDataSource,
    DimTime,
    FactCommodityObservation,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data path for USGS materials CSV files
DEFAULT_MATERIALS_PATH = Path("data/raw_mats")

# Critical materials for strategic analysis
# These are commodities essential to modern production facing supply constraints
CRITICAL_MATERIALS = {
    "lithium": "Battery production - electric vehicle transition bottleneck",
    "cobalt": "Battery cathodes - Congo extraction dependency",
    "reare": "Electronics and magnets - Chinese near-monopoly",
    "copper": "Electrification - declining ore grades",
    "nickel": "Battery and steel - geopolitical concentration",
    "graphite": "Battery anodes - synthetic vs natural",
    "platinum": "Catalysts - hydrogen economy dependency",
    "palladium": "Catalysts - Russia/South Africa concentration",
    "manganese": "Steel and batteries - import dependency",
    "titanium": "Aerospace and defense - strategic reserve",
    "tungsten": "Machine tools and defense - Chinese dominance",
    "zinc": "Steel galvanization - mature industry",
    "aluminum": "Transport and construction - energy intensive",
}


class MaterialsLoader(DataLoader):
    """Loader for USGS Mineral Commodity Summaries into 3NF schema.

    Parses CSV files from USGS MCS data and loads directly into the
    normalized schema. Uses LoaderConfig for temporal filtering:
    - config.materials_years: List of years to include

    The loader populates:
    - DimCommodity: Mineral commodities with critical material flags
    - DimCommodityMetric: Metric definitions (production, reserves, etc.)
    - DimTime: Temporal dimension (shared with other loaders)
    - FactCommodityObservation: Annual commodity observations
    """

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimCommodity, DimCommodityMetric, DimTime]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactCommodityObservation]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load USGS materials data into 3NF schema.

        Args:
            session: SQLAlchemy session for normalized database.
            reset: If True, clear existing materials data before loading.
            verbose: If True, log progress messages.
            **kwargs: Additional options including:
                data_path: Path to materials CSV directory (default: data/raw_mats).

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="usgs")
        data_path = kwargs.get("data_path")
        csv_dir = Path(data_path) if isinstance(data_path, (str, Path)) else DEFAULT_MATERIALS_PATH

        if not csv_dir.exists():
            stats.errors.append(f"Materials data directory not found: {csv_dir}")
            logger.error(f"Materials data directory not found: {csv_dir}")
            return stats

        # Discover CSV files
        csv_files = discover_commodity_files(csv_dir)
        if not csv_files:
            stats.errors.append(f"No commodity CSV files found in {csv_dir}")
            logger.error(f"No commodity CSV files found in {csv_dir}")
            return stats

        stats.files_processed = len(csv_files)

        if verbose:
            logger.info(f"Found {len(csv_files)} commodity CSV files to process")

        try:
            if reset:
                self._clear_materials_tables(session, verbose)

            # Load data source dimension
            self._load_data_source(session, verbose)

            # Filter years based on config
            years_to_load = set(self.config.materials_years)

            # Build lookup caches
            commodity_lookup: dict[str, int] = {}
            metric_lookup: dict[str, int] = {}

            obs_count = 0

            # Process each CSV file
            for csv_file in csv_files:
                if verbose:
                    logger.info(f"Processing {csv_file.name}...")

                records = parse_commodity_csv(csv_file)

                for record in records:
                    # Filter by year
                    if record.year not in years_to_load:
                        continue

                    # Resolve commodity
                    commodity_id = self._get_or_create_commodity(
                        session,
                        record.commodity_code,
                        record.commodity_name,
                        commodity_lookup,
                    )

                    # Resolve metric
                    metric_id = self._get_or_create_metric(
                        session,
                        record.metric_code,
                        record.metric_name,
                        metric_lookup,
                    )

                    # Resolve time (uses base class method with instance caching)
                    time_id = self._get_or_create_time(session, record.year)

                    # Create fact record
                    fact = FactCommodityObservation(
                        commodity_id=commodity_id,
                        metric_id=metric_id,
                        time_id=time_id,
                        value=record.value,
                        value_text=record.value_text,
                    )
                    session.add(fact)
                    obs_count += 1

                    # Batch commit to avoid memory pressure
                    if obs_count % 5000 == 0:
                        session.flush()
                        if verbose:
                            logger.info(f"  Loaded {obs_count} observations...")

            session.commit()

            stats.dimensions_loaded["commodities"] = len(commodity_lookup)
            stats.dimensions_loaded["metrics"] = len(metric_lookup)
            stats.facts_loaded["commodity_observations"] = obs_count
            stats.record_ingest("materials:commodities", len(commodity_lookup))
            stats.record_ingest("materials:metrics", len(metric_lookup))
            stats.record_ingest("materials:commodity_observations", obs_count)

            if verbose:
                logger.info(
                    f"Materials loading complete: "
                    f"{len(commodity_lookup)} commodities, "
                    f"{len(metric_lookup)} metrics, "
                    f"{obs_count} observations"
                )
        except Exception as e:
            stats.record_api_error(e, context="materials:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _clear_materials_tables(self, session: Session, verbose: bool) -> None:
        """Clear materials-specific tables (not shared dimensions).

        Args:
            session: Database session.
            verbose: Log progress.
        """
        if verbose:
            logger.info("Clearing existing materials data...")

        # Delete facts first (foreign key constraints)
        session.execute(delete(FactCommodityObservation))

        # Delete materials dimensions
        session.execute(delete(DimCommodityMetric))
        session.execute(delete(DimCommodity))

        session.flush()

    def _load_data_source(self, session: Session, verbose: bool) -> int:
        """Load or get USGS data source dimension.

        Args:
            session: Database session.
            verbose: Log progress.

        Returns:
            Data source ID.
        """
        source_id = self._get_or_create_data_source(
            session,
            source_code="USGS",
            source_name="USGS Mineral Commodity Summaries",
            source_url="https://www.usgs.gov/centers/national-minerals-information-center",
            description=(
                "Annual data on U.S. mineral production, consumption, trade, and "
                "reserves. Critical for analyzing imperial access to strategic "
                "materials and resource extraction patterns."
            ),
        )

        if verbose:
            logger.info("  Loaded USGS data source")

        return source_id

    def _get_or_create_commodity(
        self,
        session: Session,
        commodity_code: str,
        commodity_name: str,
        commodity_lookup: dict[str, int],
    ) -> int:
        """Get or create commodity dimension.

        Args:
            session: Database session.
            commodity_code: Commodity code (e.g., "lithium").
            commodity_name: Commodity display name.
            commodity_lookup: Cache to update.

        Returns:
            Commodity ID.
        """
        if commodity_code in commodity_lookup:
            return commodity_lookup[commodity_code]

        existing = session.query(DimCommodity).filter(DimCommodity.code == commodity_code).first()
        if existing:
            commodity_lookup[commodity_code] = existing.commodity_id
            return existing.commodity_id

        # Check if critical material
        is_critical = commodity_code.lower() in CRITICAL_MATERIALS
        marxian_interp = CRITICAL_MATERIALS.get(commodity_code.lower())

        commodity = DimCommodity(
            code=commodity_code,
            name=commodity_name,
            is_critical=is_critical,
            primary_applications=None,  # Could be populated from MCS descriptions
            marxian_interpretation=marxian_interp,
        )
        session.add(commodity)
        session.flush()
        commodity_lookup[commodity_code] = commodity.commodity_id
        return commodity.commodity_id

    def _get_or_create_metric(
        self,
        session: Session,
        metric_code: str,
        metric_name: str,
        metric_lookup: dict[str, int],
    ) -> int:
        """Get or create metric dimension.

        Args:
            session: Database session.
            metric_code: Metric code (e.g., "USprod_t").
            metric_name: Metric display name.
            metric_lookup: Cache to update.

        Returns:
            Metric ID.
        """
        if metric_code in metric_lookup:
            return metric_lookup[metric_code]

        existing = (
            session.query(DimCommodityMetric).filter(DimCommodityMetric.code == metric_code).first()
        )
        if existing:
            metric_lookup[metric_code] = existing.metric_id
            return existing.metric_id

        # Derive category from code
        category = get_metric_category(metric_code)

        # Extract units from metric name if possible
        units = None
        if "_t" in metric_code or "_kt" in metric_code or "_mt" in metric_code:
            units = "metric tons"
        elif "_pct" in metric_code:
            units = "percent"
        elif "_usd" in metric_code or "price" in metric_code.lower():
            units = "USD"

        # Marxian interpretation for key metrics
        marxian_interp = None
        if category == "production":
            marxian_interp = "Extraction from biosphere - metabolic throughput"
        elif category == "strategic":
            marxian_interp = "Imperial dependency on periphery extraction"
        elif category == "trade":
            marxian_interp = "Unequal exchange of raw materials"

        metric = DimCommodityMetric(
            code=metric_code,
            name=metric_name,
            units=units,
            category=category,
            marxian_interpretation=marxian_interp,
        )
        session.add(metric)
        session.flush()
        metric_lookup[metric_code] = metric.metric_id
        return metric.metric_id
