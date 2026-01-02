"""QCEW (Quarterly Census of Employment and Wages) data module.

Provides ingestion and access to BLS QCEW employment/wage data
for labor aristocracy analysis in the Babylon simulation.

Usage:
    from babylon.data.qcew import QcewArea, QcewIndustry, QcewAnnual
    from babylon.data.qcew import load_qcew_data
"""

from babylon.data.qcew.loader import load_qcew_data
from babylon.data.qcew.schema import (
    QcewAnnual,
    QcewArea,
    QcewIndustry,
    QcewOwnership,
)

__all__ = [
    # Schema models
    "QcewArea",
    "QcewIndustry",
    "QcewOwnership",
    "QcewAnnual",
    # Loader
    "load_qcew_data",
]
