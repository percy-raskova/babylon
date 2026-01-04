"""QCEW (Quarterly Census of Employment and Wages) data module.

Provides ingestion and access to BLS QCEW employment/wage data
for labor aristocracy analysis in the Babylon simulation.

Two ingestion paths are available:

1. **3NF Direct (recommended)**: Uses QcewLoader with DataLoader base class
   - Direct 3NF schema population (marxist-data-3NF.sqlite)
   - Parameterized via LoaderConfig (qcew_years)
   - Parses CSV files from BLS QCEW data

2. **Legacy**: Uses load_qcew_data
   - Writes to research.sqlite
   - Requires local CSV files in data/qcew/

Example (3NF Direct):
    from babylon.data.qcew import QcewLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(qcew_years=[2020, 2021, 2022, 2023])
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} QCEW observations")

Example (Legacy):
    from babylon.data.qcew import load_qcew_data
    from pathlib import Path

    stats = load_qcew_data(Path("data/qcew"), reset=True)
"""

from babylon.data.qcew.loader import (
    load_qcew_data,
    load_raw_2022_data,
    print_class_composition,
)
from babylon.data.qcew.loader_3nf import QcewLoader
from babylon.data.qcew.schema import (
    QcewAnnual,
    QcewArea,
    QcewIndustry,
    QcewOwnership,
    QcewRaw2022,
)

__all__ = [
    # 3NF Loader (recommended)
    "QcewLoader",
    # Schema models (normalized)
    "QcewArea",
    "QcewIndustry",
    "QcewOwnership",
    "QcewAnnual",
    # Schema models (raw/denormalized)
    "QcewRaw2022",
    # Legacy loaders
    "load_qcew_data",
    "load_raw_2022_data",
    "print_class_composition",
]
