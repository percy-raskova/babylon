"""Economics package for the Babylon simulation engine.

This package provides the Marxian value transformation layer:

- tensor: ValueTensor4x3, DepartmentRow Pydantic models
- department_mapper: NAICS to Marxian department mapping
- hydrator: MarxianHydrator for county-level transformation
- adapters: Data source protocols for QCEW and BEA data
- reproduction: Imperial rent calculation (Emmanuel-Amin framework)
- shadow_labor: Shadow labor visibility calculations (Department III)

Example:
    >>> from babylon.economics import MarxianHydrator, DepartmentMapper
    >>> from babylon.economics import ValueTensor4x3, DepartmentRow
    >>> from babylon.economics import (
    ...     PeripheryReproductionBasket,
    ...     ImperialRentCalculator,
    ...     ImperialRentResult,
    ... )
    >>> from babylon.economics import (
    ...     ShadowLaborConfig,
    ...     ShadowLaborResult,
    ...     ShadowLaborService,
    ... )

See Also:
    :mod:`babylon.models.types`: Currency and other constrained types.
    :mod:`babylon.economics.reproduction`: Imperial rent calculation details.
    :mod:`babylon.economics.shadow_labor`: Shadow labor visibility details.
"""

# Adapters (protocols and implementations)
from babylon.economics.adapters import BEADataSource, QCEWDataSource, SQLiteQCEWSource

# Department mapping
from babylon.economics.department_mapper import (
    DefaultRatios,
    Department,
    DepartmentAllocation,
    DepartmentMapper,
    get_default_mapper,
    map_sector_value,
)

# Hydrator
from babylon.economics.hydrator import MarxianHydrator

# Imperial rent (Emmanuel-Amin framework)
from babylon.economics.reproduction import (
    ImperialRentCalculator,
    ImperialRentResult,
    PeripheryReproductionBasket,
    RentStructure,
)

# Shadow labor (Department III visibility)
from babylon.economics.shadow_labor import (
    ShadowLaborConfig,
    ShadowLaborResult,
    ShadowLaborService,
)

# Tensor models
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3

__all__ = [
    # Protocols and implementations
    "BEADataSource",
    "QCEWDataSource",
    "SQLiteQCEWSource",
    # Department mapping
    "DefaultRatios",
    "Department",
    "DepartmentAllocation",
    "DepartmentMapper",
    "get_default_mapper",
    "map_sector_value",
    # Hydrator
    "MarxianHydrator",
    # Imperial rent (Emmanuel-Amin framework)
    "ImperialRentCalculator",
    "ImperialRentResult",
    "PeripheryReproductionBasket",
    "RentStructure",
    # Shadow labor (Department III visibility)
    "ShadowLaborConfig",
    "ShadowLaborResult",
    "ShadowLaborService",
    # Tensor models
    "DepartmentRow",
    "ValueTensor4x3",
]
