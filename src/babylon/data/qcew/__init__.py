"""QCEW (Quarterly Census of Employment and Wages) data module.

Provides ingestion and access to BLS QCEW employment/wage data
for labor aristocracy analysis in the Babylon simulation.

Uses QcewLoader with DataLoader base class for direct 3NF schema
population (marxist-data-3NF.sqlite). Parameterized via LoaderConfig.

Usage:
    from babylon.data.qcew import QcewLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(qcew_years=[2020, 2021, 2022, 2023])
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} QCEW observations")
"""

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
]
