"""EIA Energy data module.

Provides annual energy production, consumption, prices, and emissions
for metabolic rift analysis in Babylon simulation.

This module ingests data from the U.S. Energy Information Administration
via the EIA API v2, providing comprehensive U.S. energy statistics
dating back to 1949.

Tables (3NF schema):
    dim_energy_table: EIA table dimension (grouped series)
    dim_energy_series: Individual time series dimension
    fact_energy_annual: Annual observations

Join keys:
    dim_time.year: For temporal joins with Census, QCEW, FRED, Trade data

Marxian interpretations:
    - Production series: Metabolic throughput (extraction from biosphere)
    - Import series: Imperial energy dependency on periphery
    - Emissions series: Metabolic rift accumulation (waste externality)
    - Sector consumption: Class-based energy metabolism

Usage:
    from babylon.data.energy import EnergyLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(energy_start_year=2000, energy_end_year=2023)
    loader = EnergyLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} observations")
"""

from babylon.data.energy.api_client import (
    MSN_BY_CATEGORY,
    PRIORITY_MSN_CODES,
    EIAAPIError,
    EnergyAPIClient,
    EnergyObservation,
    EnergySeriesData,
    EnergySeriesMetadata,
)
from babylon.data.energy.loader_3nf import EnergyLoader
from babylon.data.energy.schema import (
    EIA_PRIORITY_TABLES,
    EnergyAnnual,
    EnergySeries,
    EnergyTable,
)

__all__ = [
    # API Client (EIA v2)
    "EnergyAPIClient",
    "EIAAPIError",
    "EnergySeriesMetadata",
    "EnergySeriesData",
    "EnergyObservation",
    "PRIORITY_MSN_CODES",
    "MSN_BY_CATEGORY",
    # Loaders
    "EnergyLoader",  # 3NF direct loader (recommended)
    # Schema models
    "EnergyTable",
    "EnergySeries",
    "EnergyAnnual",
    "EIA_PRIORITY_TABLES",
]
