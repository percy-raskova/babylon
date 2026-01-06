"""EIA energy data loader for direct 3NF schema population.

Loads energy production, consumption, prices, and emissions data from the
EIA API v2 directly into the normalized marxist-data-3NF.sqlite schema.

This loader replaces the legacy Excel-based loader (loader.py) with a
modern API-first approach that writes directly to 3NF tables.

Example:
    from babylon.data.energy import EnergyLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(energy_start_year=2000, energy_end_year=2023)
    loader = EnergyLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} energy observations")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import delete

from babylon.data.energy.api_client import (
    PRIORITY_MSN_CODES,
    EnergyAPIClient,
)
from babylon.data.exceptions import EIAAPIError
from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.normalize.schema import (
    DimDataSource,
    DimEnergySeries,
    DimEnergyTable,
    DimTime,
    FactEnergyAnnual,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EnergyLoader(DataLoader):
    """Loader for EIA energy data into 3NF schema.

    Fetches annual energy data from EIA API v2 and loads it into the
    normalized schema. Uses LoaderConfig for temporal parameterization:
    - config.energy_start_year: Start year for data range
    - config.energy_end_year: End year for data range

    The loader populates:
    - DimEnergyTable: Table groupings (overview, sector, prices, emissions)
    - DimEnergySeries: Individual series metadata
    - DimTime: Temporal dimension (shared with other loaders)
    - FactEnergyAnnual: Annual observations for each series
    """

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimEnergyTable, DimEnergySeries, DimTime]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactEnergyAnnual]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load EIA energy data into 3NF schema.

        Args:
            session: SQLAlchemy session for normalized database.
            reset: If True, clear existing energy data before loading.
            verbose: If True, log progress messages.

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="eia")

        if reset:
            self._clear_energy_tables(session, verbose)

        # Load data source dimension
        self._load_data_source(session, verbose)

        # Load energy table dimension (groupings)
        table_lookup = self._load_table_dimension(session, verbose)
        stats.dimensions_loaded["energy_tables"] = len(table_lookup)

        # Fetch and load series + observations from API
        try:
            with EnergyAPIClient() as client:
                self._load_series_and_facts(
                    session,
                    client,
                    table_lookup,
                    stats,
                    verbose,
                )
        except ValueError as e:
            # API key not configured
            stats.errors.append(str(e))
            logger.error(f"EIA API error: {e}")
            return stats

        session.commit()

        if verbose:
            logger.info(
                f"Energy loading complete: "
                f"{stats.dimensions_loaded.get('energy_series', 0)} series, "
                f"{stats.facts_loaded.get('energy_annual', 0)} observations"
            )

        return stats

    def _clear_energy_tables(self, session: Session, verbose: bool) -> None:
        """Clear energy-specific tables (not shared dimensions).

        Args:
            session: Database session.
            verbose: Log progress.
        """
        if verbose:
            logger.info("Clearing existing energy data...")

        # Delete facts first (foreign key constraints)
        session.execute(delete(FactEnergyAnnual))

        # Delete energy dimensions (not shared ones like DimTime)
        session.execute(delete(DimEnergySeries))
        session.execute(delete(DimEnergyTable))

        session.flush()

    def _load_data_source(self, session: Session, verbose: bool) -> int:
        """Load or get EIA data source dimension.

        Args:
            session: Database session.
            verbose: Log progress.

        Returns:
            Data source ID.
        """
        source_id = self._get_or_create_data_source(
            session,
            source_code="EIA",
            source_name="U.S. Energy Information Administration",
            source_url="https://www.eia.gov/",
            description=(
                "Primary source for U.S. energy production, consumption, "
                "prices, and emissions data. Monthly Energy Review provides "
                "comprehensive statistics for metabolic rift analysis."
            ),
        )

        if verbose:
            logger.info("  Loaded EIA data source")

        return source_id

    def _load_table_dimension(
        self,
        session: Session,
        verbose: bool,
    ) -> dict[str, int]:
        """Load energy table dimension from priority MSN codes.

        Creates table groupings based on the table_code field in
        PRIORITY_MSN_CODES configuration.

        Args:
            session: Database session.
            verbose: Log progress.

        Returns:
            Mapping of table_code to table_id.
        """
        # Extract unique table codes from priority series
        tables_to_create: dict[str, dict[str, str]] = {}
        for msn_config in PRIORITY_MSN_CODES.values():
            table_code = msn_config["table_code"]
            if table_code not in tables_to_create:
                # Use first series' category and marxian interpretation
                tables_to_create[table_code] = {
                    "category": msn_config["category"],
                    "marxian": msn_config["marxian"],
                }

        # Table code to title mapping
        table_titles = {
            "01.01": "Primary Energy Overview",
            "01.02": "Primary Energy Production by Source",
            "01.04a": "Primary Energy Imports by Source",
            "01.04b": "Primary Energy Exports by Source",
            "02.01a": "Residential Sector Energy Consumption",
            "02.01b": "Commercial Sector Energy Consumption",
            "02.02": "Industrial Sector Energy Consumption",
            "02.05": "Transportation Sector Energy Consumption",
            "09.01": "Crude Oil Price Summary",
            "09.04": "Motor Gasoline Retail Prices",
            "09.08": "Natural Gas Prices",
            "09.10": "Electricity End-Use Prices",
            "11.01": "CO2 Emissions from Energy Consumption",
            "11.02": "CO2 Emissions by Sector",
        }

        table_lookup: dict[str, int] = {}

        for table_code, config in tables_to_create.items():
            table = DimEnergyTable(
                table_code=table_code,
                title=table_titles.get(table_code, f"Table {table_code}"),
                category=config["category"],
                marxian_interpretation=config["marxian"],
            )
            session.add(table)
            session.flush()
            table_lookup[table_code] = table.table_id

        if verbose:
            logger.info(f"  Loaded {len(table_lookup)} energy table dimensions")

        return table_lookup

    def _load_series_and_facts(
        self,
        session: Session,
        client: EnergyAPIClient,
        table_lookup: dict[str, int],
        stats: LoadStats,
        verbose: bool,
    ) -> None:
        """Load series dimensions and fact observations from API.

        Args:
            session: Database session.
            client: EIA API client.
            table_lookup: Mapping of table_code to table_id.
            stats: Statistics to update.
            verbose: Log progress.
        """
        series_count = 0
        obs_count = 0

        start_year = self.config.energy_start_year
        end_year = self.config.energy_end_year

        if verbose:
            logger.info(f"Fetching energy data from EIA API ({start_year}-{end_year})...")

        for msn, config in PRIORITY_MSN_CODES.items():
            table_code = config["table_code"]
            table_id = table_lookup.get(table_code)

            if table_id is None:
                logger.warning(f"No table found for {table_code}, skipping {msn}")
                continue

            try:
                series_data = client.get_series(
                    msn=msn,
                    frequency="annual",
                    start=str(start_year),
                    end=str(end_year),
                )
                stats.api_calls += 1

                # Create series dimension
                series = DimEnergySeries(
                    table_id=table_id,
                    series_code=msn,
                    series_name=series_data.metadata.description or config["description"],
                    units=series_data.metadata.unit or "Unknown",
                    column_index=None,  # Not applicable for API-sourced data
                )
                session.add(series)
                session.flush()
                series_count += 1

                # Load observations as facts
                for obs in series_data.observations:
                    if obs.value is None:
                        continue

                    # Parse year from period
                    try:
                        year = int(obs.period[:4])
                    except (ValueError, TypeError):
                        continue

                    if year < start_year or year > end_year:
                        continue

                    time_id = self._get_or_create_time(session, year)

                    fact = FactEnergyAnnual(
                        series_id=series.series_id,
                        time_id=time_id,
                        value=obs.value,
                    )
                    session.add(fact)
                    obs_count += 1

                if verbose and series_count % 5 == 0:
                    logger.info(f"  Loaded {series_count} series, {obs_count} observations...")

            except EIAAPIError as e:
                stats.errors.append(f"Failed to fetch {msn}: {e.message}")
                logger.warning(f"API error for {msn}: {e.message}")
                continue

        session.flush()

        stats.dimensions_loaded["energy_series"] = series_count
        stats.facts_loaded["energy_annual"] = obs_count

        if verbose:
            logger.info(f"  Loaded {series_count} series with {obs_count} observations")
