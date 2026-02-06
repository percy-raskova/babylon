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
- melt: MELT and basket visibility for Labor Aristocracy thresholds (Feature 013)
- throughput: Throughput position and domestic value geography (Feature 014)
- gamma: Gamma visibility tensor for shadow subsidies (Feature 015)

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
    >>> from babylon.economics import (
    ...     ClassPosition,
    ...     NationalParameters,
    ...     DefaultMELTCalculator,
    ...     DefaultBasketVisibilityCalculator,
    ...     DefaultClassPositionClassifier,
    ...     DefaultImperialRentCalculator as TVTImperialRentCalculator,
    ... )

See Also:
    :mod:`babylon.models.types`: Currency and other constrained types.
    :mod:`babylon.economics.reproduction`: Imperial rent calculation details.
    :mod:`babylon.economics.shadow_labor`: Shadow labor visibility details.
    :mod:`babylon.economics.capital_stock`: Capital stock computation details.
    :mod:`babylon.economics.melt`: MELT and basket visibility details (Feature 013).
    :mod:`babylon.economics.throughput`: Throughput position details (Feature 014).
    :mod:`babylon.economics.gamma`: Gamma visibility tensor details (Feature 015).
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

# Gamma Visibility Tensor (Feature 015)
from babylon.economics.gamma import (
    DefaultGammaBasketCalculator,
    DefaultGammaIIICalculator,
    DefaultGammaImportCalculator,
    DefaultShadowSubsidyCalculator,
    GammaBasket,
    GammaBasketCalculator,
    GammaIII,
    GammaIIICalculator,
    GammaImport,
    GammaImportCalculator,
    ShadowSubsidy,
    ShadowSubsidyCalculator,
)

# Hydrator
from babylon.economics.hydrator import MarxianHydrator

# MELT and Basket Visibility (Feature 013)
from babylon.economics.melt import (
    BasketVisibilityCalculator,
    ClassPosition,
    ClassPositionClassifier,
    DefaultBasketVisibilityCalculator,
    DefaultClassPositionClassifier,
    DefaultMELTCalculator,
    MELTCalculator,
    NationalParameters,
)
from babylon.economics.melt import (
    DefaultImperialRentCalculator as TVTImperialRentCalculator,
)
from babylon.economics.melt import (
    ImperialRentCalculator as TVTImperialRentCalculatorProtocol,
)

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

# Throughput Position and Domestic Value Geography (Feature 014)
from babylon.economics.throughput import (
    NAICS_2DIGIT_SECTORS,
    NAICS_DEPTH_MAPPING,
    BEACountyGDPSource,
    DefaultSupplyChainAnalyzer,
    DefaultThroughputCalculator,
    QCEWCountyNAICSSource,
    SQLiteBEACountyGDPSource,
    SQLiteQCEWCountyNAICSSource,
    SupplyChainAnalyzer,
    ThroughputCalculator,
    ThroughputMetrics,
    WageShareEstimate,
    get_depth,
    validate_depth,
)

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
    # MELT and Basket Visibility (Feature 013)
    "ClassPosition",
    "NationalParameters",
    "MELTCalculator",
    "BasketVisibilityCalculator",
    "ClassPositionClassifier",
    "TVTImperialRentCalculatorProtocol",
    "DefaultMELTCalculator",
    "DefaultBasketVisibilityCalculator",
    "DefaultClassPositionClassifier",
    "TVTImperialRentCalculator",
    # Throughput Position and Domestic Value Geography (Feature 014)
    "ThroughputMetrics",
    "WageShareEstimate",
    "NAICS_DEPTH_MAPPING",
    "NAICS_2DIGIT_SECTORS",
    "get_depth",
    "validate_depth",
    "BEACountyGDPSource",
    "QCEWCountyNAICSSource",
    "ThroughputCalculator",
    "SupplyChainAnalyzer",
    "DefaultThroughputCalculator",
    "DefaultSupplyChainAnalyzer",
    "SQLiteBEACountyGDPSource",
    "SQLiteQCEWCountyNAICSSource",
    # Gamma Visibility Tensor (Feature 015)
    "GammaIII",
    "GammaImport",
    "GammaBasket",
    "ShadowSubsidy",
    "GammaIIICalculator",
    "GammaImportCalculator",
    "GammaBasketCalculator",
    "ShadowSubsidyCalculator",
    "DefaultGammaIIICalculator",
    "DefaultGammaImportCalculator",
    "DefaultGammaBasketCalculator",
    "DefaultShadowSubsidyCalculator",
]
