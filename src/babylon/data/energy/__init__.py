"""EIA Monthly Energy Review data module.

Provides annual energy production, consumption, prices, and emissions
for metabolic rift analysis in Babylon simulation.

This module ingests data from the U.S. Energy Information Administration's
Monthly Energy Review (MER), which provides comprehensive U.S. energy
statistics dating back to 1949.

Tables:
    energy_tables: EIA table dimension (grouped series, ~20 priority tables)
    energy_series: Individual time series dimension (~200 series)
    energy_annual: Annual observations (1949-2024, ~15,000 rows)

Join keys:
    year: For temporal joins with Census, QCEW, FRED, Trade, Productivity data

Marxian interpretations:
    - Production series: Metabolic throughput (extraction from biosphere)
    - Import series: Imperial energy dependency on periphery
    - Emissions series: Metabolic rift accumulation (waste externality)
    - Sector consumption: Class-based energy metabolism

Example:
    from pathlib import Path
    from babylon.data.energy import load_energy_data

    stats = load_energy_data(Path("data/energy"), reset=True)
    print(f"Loaded {stats.observations_loaded} observations")
"""

from babylon.data.energy.loader import (
    EnergyLoadStats,
    init_energy_tables,
    load_energy_data,
    reset_energy_tables,
)
from babylon.data.energy.parser import (
    EnergyRecord,
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

__all__ = [
    # Schema models
    "EnergyTable",
    "EnergySeries",
    "EnergyAnnual",
    "EIA_PRIORITY_TABLES",
    # Parser
    "EnergyRecord",
    "EnergyTableData",
    "parse_energy_excel",
    "discover_energy_files",
    # Loader
    "EnergyLoadStats",
    "init_energy_tables",
    "reset_energy_tables",
    "load_energy_data",
]
