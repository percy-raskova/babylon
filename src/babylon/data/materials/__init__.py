"""USGS Mineral Commodity Summaries data module.

Provides strategic material production, trade, and dependency data
for imperial economics analysis in Babylon simulation.

Uses MaterialsLoader with DataLoader base class for direct 3NF schema
population (marxist-data-3NF.sqlite). Parameterized via LoaderConfig.

Tables (3NF schema):
    dim_commodity: Mineral/material dimension with critical flags
    dim_commodity_metric: Measurement type dimension
    fact_commodity_observation: Annual observations

Key Marxian metric:
    NIR_pct (Net Import Reliance) = imperial vulnerability index.
    NIR >50% means the US is dependent on periphery extraction
    for strategic materials (lithium, cobalt, rare earths, etc.).

Usage:
    from babylon.data.materials import MaterialsLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(materials_years=list(range(2015, 2025)))
    loader = MaterialsLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} observations")
"""

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
    # Schema models
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
]
