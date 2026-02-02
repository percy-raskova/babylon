"""Economics package for the Babylon simulation engine.

This package provides the Marxian value transformation layer:

- tensor: ValueTensor4x3, DepartmentRow Pydantic models
- department_mapper: NAICS to Marxian department mapping
- hydrator: MarxianHydrator for county-level transformation
- adapters: Data source protocols for QCEW and BEA data
- reproduction: Imperial rent calculation (Emmanuel-Amin framework)
- shadow_labor: Shadow labor visibility calculations (Department III)
- depreciation: DepreciationConfig for capital stock computation (Feature 012)
- capital_stock: CapitalStockCalculator for TRPF analysis (Feature 012)
- derived_metrics: DerivedTensorMetrics for stock-based profit rate (Feature 012)

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
    >>> from babylon.economics import (
    ...     CapitalStockCalculator,
    ...     DepreciationConfig,
    ...     DerivedTensorMetrics,
    ... )

See Also:
    :mod:`babylon.models.types`: Currency and other constrained types.
    :mod:`babylon.economics.reproduction`: Imperial rent calculation details.
    :mod:`babylon.economics.shadow_labor`: Shadow labor visibility details.
    :mod:`babylon.economics.capital_stock`: Capital stock computation details.
"""

# Adapters (protocols and implementations)
from babylon.economics.adapters import (
    BEADataSource,
    InterpolatingBEASource,
    QCEWDataSource,
    SQLiteQCEWSource,
)

# Capital stock dynamics (Feature 012)
from babylon.economics.capital_stock import CapitalStockCalculator

# Department mapping
from babylon.economics.department_mapper import (
    DefaultRatios,
    Department,
    DepartmentAllocation,
    DepartmentMapper,
    get_default_mapper,
    map_sector_value,
)
from babylon.economics.depreciation import DepreciationConfig
from babylon.economics.derived_metrics import DerivedTensorMetrics

# Exceptions
from babylon.economics.exceptions import (
    TensorError,
    TensorHydrationError,
    TensorInitializationError,
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

# Temporal validation (Feature 003)
from babylon.economics.temporal import (
    AnomalyThresholdConfig,
    DeindustrializationSignal,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
    TemporalValidatorFacade,
)

# Tensor models
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3

__all__ = [
    # Protocols and implementations
    "BEADataSource",
    "InterpolatingBEASource",
    "QCEWDataSource",
    "SQLiteQCEWSource",
    # Exceptions
    "TensorError",
    "TensorHydrationError",
    "TensorInitializationError",
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
    # Temporal validation (Feature 003)
    "AnomalyThresholdConfig",
    "DeindustrializationSignal",
    "SmoothedCoefficientSeries",
    "TemporalTransition",
    "TemporalValidationReport",
    "TemporalValidatorFacade",
    # Capital stock dynamics (Feature 012)
    "CapitalStockCalculator",
    "DepreciationConfig",
    "DerivedTensorMetrics",
]
