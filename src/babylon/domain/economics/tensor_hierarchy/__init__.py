"""Tensor hierarchy module for multi-level economic tensor computation.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Implements Level 1 tensors from federal data sources and Level 2 derived tensors
on top of the existing ValueTensor4x3 (Level 0) primitive.

Level 1 tensors (from federal data):
    - InterIndustryFlow: BEA I-O coefficient matrix (~70 industries)
    - VisibilityMetric: Gamma visibility diagonal (wraps Feature 015)
    - GeographicFlow: BTS FAF commodity flow O-D matrix
    - ReproductionRequirements: CEX + ATUS consumption/labor requirements
    - ClassTransitionMatrix: PSID-based class mobility matrix

Level 2 tensors (derived):
    - LeontiefInverse: (I - A)^{-1} from InterIndustryFlow
    - ImperialRentField: Net value extraction per CFS area
    - ShadowSubsidy: Dept III value × (1 - g_33)
    - StationaryDistribution: Long-run class distribution eigenvector

See Also:
    :mod:`babylon.domain.economics.tensor`: Level 0 ValueTensor4x3 primitive.
    :mod:`babylon.domain.economics.gamma`: Feature 015 gamma visibility module.
"""

from __future__ import annotations

from babylon.domain.economics.tensor_hierarchy.class_transition import (
    DefaultClassTransitionComputer,
    DefaultClassTransitionSource,
)
from babylon.domain.economics.tensor_hierarchy.geographic_flow import (
    DefaultGeographicAggregator,
    DefaultGeographicFlowSource,
    DefaultImperialRentComputer,
)
from babylon.domain.economics.tensor_hierarchy.inter_industry import (
    DefaultDepartmentAggregator,
    DefaultInterIndustryFlowSource,
    DefaultLeontiefComputer,
)
from babylon.domain.economics.tensor_hierarchy.protocols import (
    ClassTransitionSource,
    DepartmentAggregator,
    GeographicFlowSource,
    ImperialRentComputer,
    InterIndustryFlowSource,
    LeontiefComputer,
    ReproductionSource,
    VisibilitySource,
)
from babylon.domain.economics.tensor_hierarchy.reproduction import (
    DefaultReproductionRequirementsComputer,
    DefaultReproductionSource,
)
from babylon.domain.economics.tensor_hierarchy.types import (
    ClassTransitionMatrix,
    Department,
    GeographicFlow,
    ImperialRentField,
    InterIndustryFlow,
    IOTableType,
    LeontiefInverse,
    ReproductionRequirements,
    ShadowSubsidyTensor,
    StationaryDistribution,
    VisibilityMetric,
)
from babylon.domain.economics.tensor_hierarchy.visibility import DefaultVisibilitySource

__all__ = [
    # Types (Level 1)
    "ClassTransitionMatrix",
    "Department",
    "GeographicFlow",
    "InterIndustryFlow",
    "IOTableType",
    "ReproductionRequirements",
    "VisibilityMetric",
    # Types (Level 2)
    "ImperialRentField",
    "LeontiefInverse",
    "ShadowSubsidyTensor",
    "StationaryDistribution",
    # Protocols
    "ClassTransitionSource",
    "DepartmentAggregator",
    "GeographicFlowSource",
    "ImperialRentComputer",
    "InterIndustryFlowSource",
    "LeontiefComputer",
    "ReproductionSource",
    "VisibilitySource",
    # Default implementations
    "DefaultClassTransitionComputer",
    "DefaultClassTransitionSource",
    "DefaultDepartmentAggregator",
    "DefaultGeographicAggregator",
    "DefaultGeographicFlowSource",
    "DefaultImperialRentComputer",
    "DefaultInterIndustryFlowSource",
    "DefaultLeontiefComputer",
    "DefaultReproductionRequirementsComputer",
    "DefaultReproductionSource",
    "DefaultVisibilitySource",
]
