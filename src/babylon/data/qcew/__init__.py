"""BLS QCEW data loading infrastructure.

Provides loading of Quarterly Census of Employment and Wages data
from the BLS Open Data API or local CSV files using a hybrid approach:
- API for recent years (2021+): Fetches directly from BLS QCEW Open Data API
- Files for historical years (2013-2020): Reads from local CSV downloads

Usage:
    from babylon.data.qcew import QcewLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(qcew_years=list(range(2013, 2026)))
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} QCEW observations")
"""

from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAPIError,
    QcewAreaRecord,
    get_state_area_code,
)
from babylon.data.qcew.loader_3nf import QcewLoader
from babylon.data.qcew.parser import (
    QcewRecord,
    parse_all_area_files,
    parse_qcew_csv,
)
from babylon.data.qcew.schema import (
    QcewAnnual,
    QcewArea,
    QcewIndustry,
    QcewOwnership,
    QcewRaw2022,
)

__all__ = [
    # API Client
    "QcewAPIClient",
    "QcewAPIError",
    "QcewAreaRecord",
    "get_state_area_code",
    # 3NF Loader (recommended)
    "QcewLoader",
    # Parser (legacy/offline)
    "QcewRecord",
    "parse_qcew_csv",
    "parse_all_area_files",
    # Schema models (normalized)
    "QcewArea",
    "QcewIndustry",
    "QcewOwnership",
    "QcewAnnual",
    # Schema models (raw/denormalized)
    "QcewRaw2022",
]
