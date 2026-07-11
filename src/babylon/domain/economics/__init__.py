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
- dynamics: Class dynamics engine for modeling class position transitions (Feature 016)
- tick: Simulation tick dynamics pipeline integrating Features 012-016 (Feature 017)

Example:
    >>> from babylon.domain.economics import MarxianHydrator, DepartmentMapper
    >>> from babylon.domain.economics import ValueTensor4x3, DepartmentRow
    >>> from babylon.domain.economics import ValueTensor4x3, DepartmentRow
    >>> from babylon.domain.economics import (
    ...     ShadowLaborConfig,
    ...     ShadowLaborResult,
    ...     ShadowLaborService,
    ... )
    >>> from babylon.domain.economics import (
    ...     CapitalStockCalculator,
    ...     DepreciationConfig,
    ...     DerivedTensorMetrics,
    ... )
    >>> from babylon.domain.economics import (
    ...     ClassPosition,
    ...     NationalParameters,
    ...     DefaultMELTCalculator,
    ...     DefaultBasketVisibilityCalculator,
    ...     DefaultClassPositionClassifier,
    ... )

See Also:
    :mod:`babylon.models.types`: Currency and other constrained types.
    :mod:`babylon.domain.economics.reproduction`: Imperial rent calculation details.
    :mod:`babylon.domain.economics.shadow_labor`: Shadow labor visibility details.
    :mod:`babylon.domain.economics.capital_stock`: Capital stock computation details.
    :mod:`babylon.domain.economics.melt`: MELT and basket visibility details (Feature 013).
    :mod:`babylon.domain.economics.throughput`: Throughput position details (Feature 014).
    :mod:`babylon.domain.economics.gamma`: Gamma visibility tensor details (Feature 015).
    :mod:`babylon.domain.economics.dynamics`: Class dynamics engine details (Feature 016).
    :mod:`babylon.domain.economics.tick`: Simulation tick dynamics pipeline (Feature 017).
"""

# Adapters (protocols and implementations)
from babylon.domain.economics.adapters import (
    BEADataSource,
    QCEWDataSource,
    SQLiteQCEWSource,
)

# Capital stock dynamics (Feature 012)
from babylon.domain.economics.capital_stock import CapitalStockCalculator

# Department mapping
from babylon.domain.economics.department_mapper import (
    DefaultRatios,
    Department,
    DepartmentAllocation,
    DepartmentMapper,
    get_default_mapper,
    map_sector_value,
)
from babylon.domain.economics.depreciation import DepreciationConfig
from babylon.domain.economics.derived_metrics import DerivedTensorMetrics

# Class Dynamics Engine (Feature 016)
from babylon.domain.economics.dynamics import (
    ClassDistribution,
    DefaultAccumulationCalculator,
    DefaultClassTransitionEngine,
    DefaultCrisisAmplifier,
    DefaultDispossessionCalculator,
    DefaultSavingsRateSchedule,
    EconomicConditions,
    HardcodedNationalDispossessionSource,
    TransitionRates,
)

# Exceptions
from babylon.domain.economics.exceptions import (
    TensorError,
    TensorHydrationError,
    TensorInitializationError,
)

# Gamma Visibility Tensor (Feature 015)
from babylon.domain.economics.gamma import (
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
from babylon.domain.economics.hydrator import MarxianHydrator

# MELT and Basket Visibility (Feature 013)
from babylon.domain.economics.melt import (
    BasketVisibilityCalculator,
    ClassPosition,
    ClassPositionClassifier,
    DefaultBasketVisibilityCalculator,
    DefaultClassPositionClassifier,
    DefaultMELTCalculator,
    MELTCalculator,
    NationalParameters,
)

# Shadow labor (Department III visibility)
from babylon.domain.economics.shadow_labor import (
    ShadowLaborConfig,
    ShadowLaborResult,
    ShadowLaborService,
)

# Temporal validation (Feature 003)
from babylon.domain.economics.temporal import (
    AnomalyThresholdConfig,
    DeindustrializationSignal,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
    TemporalValidatorFacade,
)

# Tensor models
from babylon.domain.economics.tensor import DepartmentRow, ValueTensor4x3

# Throughput Position and Domestic Value Geography (Feature 014)
from babylon.domain.economics.throughput import (
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

# Simulation Tick Dynamics (Feature 017)
from babylon.domain.economics.tick import (
    CoefficientSmoother,
    CountyEconomicState,
    DefaultTickInitializer,
    DerivedRateCalculator,
    DerivedRates,
    NationalTickParameters,
    PrecarityDeriver,
    SimulationTickState,
    SmoothedCoefficients,
    ThresholdCrisisDetector,
    TickDynamicsSystem,
    TickSummary,
)

__all__ = [
    # Protocols and implementations
    "BEADataSource",
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
    "DefaultMELTCalculator",
    "DefaultBasketVisibilityCalculator",
    "DefaultClassPositionClassifier",
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
    # Class Dynamics Engine (Feature 016)
    "ClassDistribution",
    "EconomicConditions",
    "TransitionRates",
    "DefaultAccumulationCalculator",
    "DefaultClassTransitionEngine",
    "DefaultCrisisAmplifier",
    "DefaultDispossessionCalculator",
    "DefaultSavingsRateSchedule",
    "HardcodedNationalDispossessionSource",
    # Simulation Tick Dynamics (Feature 017)
    "TickDynamicsSystem",
    "SimulationTickState",
    "NationalTickParameters",
    "CountyEconomicState",
    "SmoothedCoefficients",
    "TickSummary",
    "DerivedRates",
    "CoefficientSmoother",
    "DefaultTickInitializer",
    "DerivedRateCalculator",
    "PrecarityDeriver",
    "ThresholdCrisisDetector",
]
