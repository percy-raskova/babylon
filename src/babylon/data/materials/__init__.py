"""USGS Mineral Commodity Summaries data module.

Provides strategic material production, trade, and dependency data
for imperial economics analysis in Babylon simulation.

This module ingests data from the USGS Mineral Commodity Summaries (MCS),
which provides annual U.S. and global statistics for ~85 mineral commodities.

Two ingestion paths are available:

1. **3NF Direct (recommended)**: Uses MaterialsLoader with DataLoader base class
   - Direct 3NF schema population (marxist-data-3NF.sqlite)
   - Parameterized via LoaderConfig (materials_start_year, materials_end_year)
   - Parses CSV files from USGS MCS data

2. **Legacy**: Uses load_materials_data
   - Writes to research.sqlite
   - Requires local CSV files in data/raw_mats/

Tables (3NF schema):
    dim_commodity: Mineral/material dimension with critical flags
    dim_commodity_metric: Measurement type dimension
    fact_commodity_observation: Annual observations

Key Marxian metric:
    NIR_pct (Net Import Reliance) = imperial vulnerability index.
    NIR >50% means the US is dependent on periphery extraction
    for strategic materials (lithium, cobalt, rare earths, etc.).

Example (3NF Direct):
    from babylon.data.materials import MaterialsLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(materials_years=list(range(2015, 2025)))
    loader = MaterialsLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} observations")

Example (Legacy):
    from pathlib import Path
    from babylon.data.materials import load_materials_data

    stats = load_materials_data(Path("data/raw_mats"), reset=True)
    print(f"Loaded {stats.observations_loaded} observations")
"""

from babylon.data.materials.loader import (
    MaterialsLoadStats,
    init_materials_tables,
    load_materials_data,
    reset_materials_tables,
)
from babylon.data.materials.loader_3nf import MaterialsLoader
from babylon.data.materials.parser import (
    CommodityRecord,
    StateRecord,
    TrendRecord,
    discover_aggregate_files,
    discover_commodity_files,
    parse_commodity_csv,
    parse_state_csv,
    parse_trends_csv,
)
from babylon.data.materials.schema import (
    CRITICAL_MINERALS,
    METRIC_CATEGORIES,
    METRIC_INTERPRETATIONS,
    Commodity,
    CommodityMetric,
    CommodityObservation,
    ImportSource,
    MaterialsState,
    MineralTrend,
    StateMineral,
)

__all__ = [
    # 3NF Loader (recommended)
    "MaterialsLoader",
    # Legacy schema models
    "Commodity",
    "CommodityMetric",
    "CommodityObservation",
    "MaterialsState",
    "StateMineral",
    "MineralTrend",
    "ImportSource",
    # Schema constants
    "CRITICAL_MINERALS",
    "METRIC_CATEGORIES",
    "METRIC_INTERPRETATIONS",
    # Parser
    "CommodityRecord",
    "StateRecord",
    "TrendRecord",
    "parse_commodity_csv",
    "parse_state_csv",
    "parse_trends_csv",
    "discover_commodity_files",
    "discover_aggregate_files",
    # Legacy loader
    "MaterialsLoadStats",
    "init_materials_tables",
    "reset_materials_tables",
    "load_materials_data",
]
