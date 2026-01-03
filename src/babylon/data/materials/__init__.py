"""USGS Mineral Commodity Summaries data module.

Provides strategic material production, trade, and dependency data
for imperial economics analysis in Babylon simulation.

This module ingests data from the USGS Mineral Commodity Summaries (MCS),
which provides annual U.S. and global statistics for ~85 mineral commodities.

Tables:
    commodities: Mineral/material dimension (~85 commodities)
    commodity_metrics: Measurement type dimension (~15 metrics)
    commodity_observations: Annual observations (EAV pattern, 2020-2024)
    materials_states: US state dimension for geographic joins
    state_minerals: State-level production values
    mineral_trends: Industry aggregate trends
    import_sources: Major import countries

Join keys:
    year: For temporal joins with Census, QCEW, FRED, Energy data
    fips_code: For geographic joins with Census counties via materials_states

Key Marxian metric:
    NIR_pct (Net Import Reliance) = imperial vulnerability index.
    NIR >50% means the US is dependent on periphery extraction
    for strategic materials (lithium, cobalt, rare earths, etc.).

Example:
    from pathlib import Path
    from babylon.data.materials import load_materials_data

    stats = load_materials_data(Path("data/raw_mats"), reset=True)
    print(f"Loaded {stats.observations_loaded} observations "
          f"for {stats.commodities_loaded} commodities")
"""

from babylon.data.materials.loader import (
    MaterialsLoadStats,
    init_materials_tables,
    load_materials_data,
    reset_materials_tables,
)
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
    # Loader
    "MaterialsLoadStats",
    "init_materials_tables",
    "reset_materials_tables",
    "load_materials_data",
]
