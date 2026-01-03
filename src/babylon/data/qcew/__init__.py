"""QCEW (Quarterly Census of Employment and Wages) data module.

Provides ingestion and access to BLS QCEW employment/wage data
for labor aristocracy analysis in the Babylon simulation.

Usage:
    from babylon.data.qcew import QcewArea, QcewIndustry, QcewAnnual
    from babylon.data.qcew import load_qcew_data

    # Raw 2022 data (denormalized for class composition analysis)
    from babylon.data.qcew import QcewRaw2022, LaborHours2022
    from babylon.data.qcew import load_raw_2022_data, load_labor_hours_data
    from babylon.data.qcew import print_class_composition
"""

from babylon.data.qcew.loader import (
    load_labor_hours_data,
    load_qcew_data,
    load_raw_2022_data,
    print_class_composition,
)
from babylon.data.qcew.schema import (
    LaborHours2022,
    QcewAnnual,
    QcewArea,
    QcewIndustry,
    QcewOwnership,
    QcewRaw2022,
)

__all__ = [
    # Schema models (normalized)
    "QcewArea",
    "QcewIndustry",
    "QcewOwnership",
    "QcewAnnual",
    # Schema models (raw/denormalized)
    "QcewRaw2022",
    "LaborHours2022",
    # Loaders
    "load_qcew_data",
    "load_raw_2022_data",
    "load_labor_hours_data",
    "print_class_composition",
]
