"""QCEW data loader for direct 3NF schema population.

Loads BLS Quarterly Census of Employment and Wages data directly into
the normalized marxist-data-3NF.sqlite schema.

This loader replaces the legacy loader (loader.py) with a direct
3NF approach using LoaderConfig for parameterization.

Example:
    from babylon.data.qcew import QcewLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(qcew_years=[2020, 2021, 2022, 2023])
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, data_path=Path("data/qcew"))
        print(f"Loaded {stats.facts_loaded} QCEW observations")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.normalize.classifications import classify_class_composition
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    DimIndustry,
    DimOwnership,
    DimState,
    DimTime,
    FactQcewAnnual,
)
from babylon.data.qcew.parser import (
    determine_naics_level,
    extract_state_fips,
    parse_qcew_csv,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data path for QCEW CSV files
DEFAULT_QCEW_PATH = Path("data/qcew")


class QcewLoader(DataLoader):
    """Loader for BLS QCEW data into 3NF schema.

    Parses CSV files from BLS QCEW data and loads directly into
    the normalized schema. Uses LoaderConfig for temporal filtering:
    - config.qcew_years: List of years to include

    The loader populates:
    - DimIndustry: NAICS industries with class composition
    - DimOwnership: Ownership types (private/government)
    - DimTime: Temporal dimension (shared with other loaders)
    - FactQcewAnnual: Annual employment/wage observations
    """

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimIndustry, DimOwnership, DimTime]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactQcewAnnual]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load QCEW data into 3NF schema.

        Args:
            session: SQLAlchemy session for normalized database.
            reset: If True, clear existing QCEW data before loading.
            verbose: If True, log progress messages.
            **kwargs: Additional options including:
                data_path: Path to QCEW CSV directory (default: data/qcew).

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="qcew")
        data_path = kwargs.get("data_path")
        csv_dir = Path(data_path) if isinstance(data_path, (str, Path)) else DEFAULT_QCEW_PATH

        if not csv_dir.exists():
            stats.errors.append(f"QCEW data directory not found: {csv_dir}")
            logger.error(f"QCEW data directory not found: {csv_dir}")
            return stats

        if reset:
            self._clear_qcew_tables(session, verbose)

        # Load data source dimension
        self._load_data_source(session, verbose)

        # Discover CSV files
        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            stats.errors.append(f"No CSV files found in {csv_dir}")
            logger.error(f"No CSV files found in {csv_dir}")
            return stats

        stats.files_processed = len(csv_files)

        if verbose:
            logger.info(f"Found {len(csv_files)} QCEW CSV files to process")

        # Filter years based on config
        years_to_load = set(self.config.qcew_years)

        # Build lookup caches
        state_lookup = self._build_state_lookup(session)
        county_lookup = self._build_county_lookup(session)
        industry_lookup: dict[str, int] = {}
        ownership_lookup: dict[str, int] = {}
        time_cache: dict[int, int] = {}

        obs_count = 0

        # Process each CSV file
        for csv_file in csv_files:
            if verbose:
                logger.info(f"Processing {csv_file.name}...")

            for record in parse_qcew_csv(csv_file):
                # Filter by year
                if record.year not in years_to_load:
                    continue

                # Resolve county
                county_id = county_lookup.get(record.area_fips)
                if county_id is None:
                    # Try to create county if we have state info
                    state_fips = extract_state_fips(record.area_fips)
                    if state_fips and state_fips in state_lookup:
                        county_id = self._get_or_create_county(
                            session,
                            record.area_fips,
                            record.area_title,
                            state_lookup[state_fips],
                            county_lookup,
                        )
                    else:
                        # Skip non-county areas (national, MSA, etc.)
                        continue

                # Resolve industry
                industry_id = self._get_or_create_industry(
                    session,
                    record.industry_code,
                    record.industry_title,
                    industry_lookup,
                )

                # Resolve ownership
                ownership_id = self._get_or_create_ownership(
                    session,
                    record.own_code,
                    record.own_title,
                    ownership_lookup,
                )

                # Resolve time
                time_id = self._get_or_create_time(session, record.year, time_cache)

                # Create fact record
                fact = FactQcewAnnual(
                    county_id=county_id,
                    industry_id=industry_id,
                    ownership_id=ownership_id,
                    time_id=time_id,
                    establishments=record.establishments,
                    employment=record.employment,
                    total_wages_usd=record.total_wages,
                    avg_weekly_wage_usd=record.avg_weekly_wage,
                    avg_annual_pay_usd=record.avg_annual_pay,
                    lq_employment=record.lq_employment,
                    lq_annual_pay=record.lq_avg_annual_pay,
                    disclosure_code=record.disclosure_code or None,
                )
                session.add(fact)
                obs_count += 1

                # Batch commit to avoid memory pressure
                if obs_count % 10000 == 0:
                    session.flush()
                    if verbose:
                        logger.info(f"  Loaded {obs_count} observations...")

        session.commit()

        stats.dimensions_loaded["industries"] = len(industry_lookup)
        stats.dimensions_loaded["ownerships"] = len(ownership_lookup)
        stats.facts_loaded["qcew_annual"] = obs_count

        if verbose:
            logger.info(
                f"QCEW loading complete: "
                f"{len(industry_lookup)} industries, {obs_count} observations"
            )

        return stats

    def _clear_qcew_tables(self, session: Session, verbose: bool) -> None:
        """Clear QCEW-specific tables (not shared dimensions).

        Args:
            session: Database session.
            verbose: Log progress.
        """
        if verbose:
            logger.info("Clearing existing QCEW data...")

        # Delete facts first (foreign key constraints)
        session.execute(delete(FactQcewAnnual))

        # Don't delete DimIndustry or DimOwnership as they may be shared
        # with other data sources (productivity, FRED)

        session.flush()

    def _load_data_source(self, session: Session, verbose: bool) -> int:
        """Load or get QCEW data source dimension.

        Args:
            session: Database session.
            verbose: Log progress.

        Returns:
            Data source ID.
        """
        existing = session.query(DimDataSource).filter(DimDataSource.source_code == "QCEW").first()
        if existing:
            return existing.source_id

        source = DimDataSource(
            source_code="QCEW",
            source_name="BLS Quarterly Census of Employment and Wages",
            source_url="https://www.bls.gov/qcew/",
            description=(
                "Comprehensive establishment-level data on employment and wages "
                "by industry and county. Essential for labor aristocracy analysis "
                "and geographic class composition mapping."
            ),
        )
        session.add(source)
        session.flush()

        if verbose:
            logger.info("  Loaded QCEW data source")

        return source.source_id

    def _build_state_lookup(self, session: Session) -> dict[str, int]:
        """Build state FIPS to state_id lookup.

        Args:
            session: Database session.

        Returns:
            Mapping of state FIPS to state_id.
        """
        states = session.query(DimState).all()
        return {s.state_fips: s.state_id for s in states}

    def _build_county_lookup(self, session: Session) -> dict[str, int]:
        """Build county FIPS to county_id lookup.

        Args:
            session: Database session.

        Returns:
            Mapping of full FIPS to county_id.
        """
        counties = session.query(DimCounty).all()
        return {c.fips: c.county_id for c in counties}

    def _get_or_create_county(
        self,
        session: Session,
        fips: str,
        area_title: str,
        state_id: int,
        county_lookup: dict[str, int],
    ) -> int:
        """Get or create county dimension.

        Args:
            session: Database session.
            fips: 5-digit FIPS code.
            area_title: Area name from QCEW.
            state_id: State ID foreign key.
            county_lookup: Cache to update.

        Returns:
            County ID.
        """
        if fips in county_lookup:
            return county_lookup[fips]

        # Extract county FIPS (last 3 digits)
        county_fips = fips[2:5] if len(fips) >= 5 else fips

        county = DimCounty(
            fips=fips,
            state_id=state_id,
            county_fips=county_fips,
            county_name=area_title,
        )
        session.add(county)
        session.flush()
        county_lookup[fips] = county.county_id
        return county.county_id

    def _get_or_create_industry(
        self,
        session: Session,
        naics_code: str,
        industry_title: str,
        industry_lookup: dict[str, int],
    ) -> int:
        """Get or create industry dimension.

        Args:
            session: Database session.
            naics_code: NAICS or BLS industry code.
            industry_title: Industry description.
            industry_lookup: Cache to update.

        Returns:
            Industry ID.
        """
        if naics_code in industry_lookup:
            return industry_lookup[naics_code]

        # Check if exists in DB
        existing = session.query(DimIndustry).filter(DimIndustry.naics_code == naics_code).first()
        if existing:
            # Update has_qcew_data flag
            if not existing.has_qcew_data:
                existing.has_qcew_data = True
            industry_lookup[naics_code] = existing.industry_id
            return existing.industry_id

        # Derive metadata
        naics_level = determine_naics_level(naics_code)
        sector_code = naics_code[:2] if len(naics_code) >= 2 else None
        parent_code = naics_code[:-1] if len(naics_code) > 2 else None
        class_comp = classify_class_composition(naics_code, industry_title)

        industry = DimIndustry(
            naics_code=naics_code,
            industry_title=industry_title,
            naics_level=naics_level,
            parent_naics_code=parent_code,
            sector_code=sector_code,
            class_composition=class_comp,
            has_qcew_data=True,
            has_productivity_data=False,
            has_fred_data=False,
        )
        session.add(industry)
        session.flush()
        industry_lookup[naics_code] = industry.industry_id
        return industry.industry_id

    def _get_or_create_ownership(
        self,
        session: Session,
        own_code: str,
        own_title: str,
        ownership_lookup: dict[str, int],
    ) -> int:
        """Get or create ownership dimension.

        Args:
            session: Database session.
            own_code: Ownership code (1-9).
            own_title: Ownership description.
            ownership_lookup: Cache to update.

        Returns:
            Ownership ID.
        """
        if own_code in ownership_lookup:
            return ownership_lookup[own_code]

        existing = session.query(DimOwnership).filter(DimOwnership.own_code == own_code).first()
        if existing:
            ownership_lookup[own_code] = existing.ownership_id
            return existing.ownership_id

        # Determine government/private flags based on BLS codes
        # 1 = Federal, 2 = State, 3 = Local, 4 = International
        # 5 = Private
        # 0, 8, 9 = Total/aggregates
        is_government = own_code in ("1", "2", "3", "4")
        is_private = own_code == "5"

        ownership = DimOwnership(
            own_code=own_code,
            own_title=own_title,
            is_government=is_government,
            is_private=is_private,
        )
        session.add(ownership)
        session.flush()
        ownership_lookup[own_code] = ownership.ownership_id
        return ownership.ownership_id

    def _get_or_create_time(
        self,
        session: Session,
        year: int,
        time_cache: dict[int, int],
    ) -> int:
        """Get or create DimTime record for a year.

        Args:
            session: Database session.
            year: Calendar year.
            time_cache: Cache of year -> time_id mappings.

        Returns:
            time_id for the year.
        """
        if year in time_cache:
            return time_cache[year]

        existing = (
            session.query(DimTime)
            .filter(DimTime.year == year, DimTime.is_annual == True)  # noqa: E712
            .first()
        )
        if existing:
            time_cache[year] = existing.time_id
            return existing.time_id

        time_dim = DimTime(
            year=year,
            month=None,
            quarter=None,
            is_annual=True,
        )
        session.add(time_dim)
        session.flush()
        time_cache[year] = time_dim.time_id
        return time_dim.time_id
