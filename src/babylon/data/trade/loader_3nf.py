"""Trade data loader for direct 3NF schema population.

Loads UN trade data from Excel files directly into the normalized
marxist-data-3NF.sqlite schema.

This loader replaces the legacy loader (loader.py) with a direct
3NF approach using LoaderConfig for parameterization.

Example:
    from babylon.data.trade import TradeLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(trade_years=[2020, 2021, 2022, 2023])
    loader = TradeLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, data_path=Path("data/imperial_rent"))
        print(f"Loaded {stats.facts_loaded} trade observations")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.normalize.classifications import classify_world_system_tier
from babylon.data.normalize.schema import (
    DimCountry,
    DimDataSource,
    DimTime,
    FactTradeMonthly,
)
from babylon.data.trade.parser import (
    TradeCountryData,
    TradeRowData,
    parse_trade_excel,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data path for trade Excel files
DEFAULT_TRADE_PATH = Path("data/imperial_rent/country.xlsx")


class TradeLoader(DataLoader):
    """Loader for UN trade data into 3NF schema.

    Parses Excel files from UN trade data and loads directly into
    the normalized schema. Uses LoaderConfig for temporal filtering:
    - config.trade_years: List of years to include

    The loader populates:
    - DimCountry: Trade partners with world-system classification
    - DimTime: Temporal dimension (shared with other loaders)
    - FactTradeMonthly: Monthly import/export values
    """

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimCountry, DimTime]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactTradeMonthly]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load UN trade data into 3NF schema.

        Args:
            session: SQLAlchemy session for normalized database.
            reset: If True, clear existing trade data before loading.
            verbose: If True, log progress messages.
            **kwargs: Additional options including:
                data_path: Path to trade Excel file (default: data/imperial_rent/country.xlsx).

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="trade")
        data_path = kwargs.get("data_path")
        xlsx_path = Path(data_path) if isinstance(data_path, (str, Path)) else DEFAULT_TRADE_PATH

        if not xlsx_path.exists():
            stats.errors.append(f"Trade data file not found: {xlsx_path}")
            logger.error(f"Trade data file not found: {xlsx_path}")
            return stats

        try:
            if reset:
                self._clear_trade_tables(session, verbose)

            # Load data source dimension
            self._load_data_source(session, verbose)

            # Parse Excel file
            if verbose:
                logger.info(f"Parsing trade data from {xlsx_path}...")

            trade_data = parse_trade_excel(xlsx_path)
            stats.files_processed = 1

            # Load country dimension
            country_lookup = self._load_country_dimension(session, trade_data.countries, verbose)
            stats.dimensions_loaded["countries"] = len(country_lookup)

            # Filter years based on config
            years_to_load = set(self.config.trade_years)

            # Load monthly trade facts
            obs_count = self._load_trade_facts(
                session, trade_data.rows, country_lookup, years_to_load, verbose
            )
            stats.facts_loaded["trade_monthly"] = obs_count
            stats.record_ingest("trade:countries", len(country_lookup))
            stats.record_ingest("trade:trade_monthly", obs_count)

            session.commit()

            if verbose:
                logger.info(
                    f"Trade loading complete: {len(country_lookup)} countries, {obs_count} observations"
                )
        except Exception as e:
            stats.record_api_error(e, context="trade:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _clear_trade_tables(self, session: Session, verbose: bool) -> None:
        """Clear trade-specific tables (not shared dimensions).

        Args:
            session: Database session.
            verbose: Log progress.
        """
        if verbose:
            logger.info("Clearing existing trade data...")

        # Delete facts first (foreign key constraints)
        session.execute(delete(FactTradeMonthly))

        # Delete trade-specific dimensions (not shared DimTime)
        session.execute(delete(DimCountry))

        session.flush()

    def _load_data_source(self, session: Session, verbose: bool) -> int:
        """Load or get trade data source dimension.

        Args:
            session: Database session.
            verbose: Log progress.

        Returns:
            Data source ID.
        """
        source_id = self._get_or_create_data_source(
            session,
            source_code="TRADE",
            source_name="UN Trade Statistics",
            source_url="https://comtrade.un.org/",
            description=(
                "United Nations trade statistics for bilateral trade flows. "
                "Used for unequal exchange and imperial rent analysis."
            ),
        )

        if verbose:
            logger.info("  Loaded TRADE data source")

        return source_id

    def _load_country_dimension(
        self,
        session: Session,
        countries: list[TradeCountryData],
        verbose: bool,
    ) -> dict[str, int]:
        """Load country dimension with world-system classification.

        Args:
            session: Database session.
            countries: List of TradeCountryData objects.
            verbose: Log progress.

        Returns:
            Mapping of cty_code to country_id.
        """
        country_lookup: dict[str, int] = {}

        for country_data in countries:
            # Classify into world-system tier (core/semi-periphery/periphery)
            tier = None
            if not country_data.is_region:
                tier = classify_world_system_tier(country_data.name)

            country = DimCountry(
                cty_code=country_data.cty_code,
                country_name=country_data.name,
                is_region=country_data.is_region,
                world_system_tier=tier,
            )
            session.add(country)
            session.flush()
            country_lookup[country_data.cty_code] = country.country_id

        if verbose:
            logger.info(f"  Loaded {len(country_lookup)} country dimensions")

        return country_lookup

    def _load_trade_facts(
        self,
        session: Session,
        rows: list[TradeRowData],
        country_lookup: dict[str, int],
        years_to_load: set[int],
        verbose: bool,
    ) -> int:
        """Load monthly trade facts from parsed data.

        Args:
            session: Database session.
            rows: List of TradeRowData objects.
            country_lookup: Mapping of cty_code to country_id.
            years_to_load: Set of years to include.
            verbose: Log progress.

        Returns:
            Number of facts loaded.
        """
        obs_count = 0

        for row in rows:
            # Filter by year
            if row.year not in years_to_load:
                continue

            country_id = country_lookup.get(row.cty_code)
            if country_id is None:
                continue

            # Load each month's data
            for month_idx, (imports, exports) in enumerate(
                zip(row.monthly_imports, row.monthly_exports, strict=True)
            ):
                month = month_idx + 1  # 1-indexed

                # Skip if no data for this month
                if imports is None and exports is None:
                    continue

                # Uses base class method (auto-calculates quarter from month)
                time_id = self._get_or_create_time(session, row.year, month=month)

                fact = FactTradeMonthly(
                    country_id=country_id,
                    time_id=time_id,
                    imports_usd_millions=imports,
                    exports_usd_millions=exports,
                )
                session.add(fact)
                obs_count += 1

        session.flush()

        if verbose:
            logger.info(f"  Loaded {obs_count} monthly trade observations")

        return obs_count
