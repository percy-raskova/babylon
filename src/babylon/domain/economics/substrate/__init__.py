"""Tri-county economic substrate module.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Integrates Capital Volumes I (Production), II (Circulation), and III
(Equalization) onto an H3 resolution 7 spatial mesh covering Wayne (26163),
Oakland (26125), and Macomb (26099) counties.

See Also:
    :mod:`babylon.domain.economics.tensor_hierarchy`: Level 1/2 tensor infrastructure.
    :mod:`babylon.domain.economics.tensor`: Level 0 ValueTensor4x3 primitive.
"""

from __future__ import annotations

from babylon.domain.economics.substrate.aggregation import DefaultResolutionAggregator
from babylon.domain.economics.substrate.circulation import DefaultHexCirculationComputer
from babylon.domain.economics.substrate.conservation import (
    CONSERVATION_TOLERANCE,
    DefaultConservationChecker,
)
from babylon.domain.economics.substrate.equalization import DefaultHexEqualizationComputer
from babylon.domain.economics.substrate.ground_rent import GroundRentResult, compute_ground_rent
from babylon.domain.economics.substrate.hydrator import hydrate_hex_grid
from babylon.domain.economics.substrate.production import DefaultHexProductionComputer
from babylon.domain.economics.substrate.protocols import (
    CommuterFlowSource,
    ConservationChecker,
    HexCirculationComputer,
    HexEqualizationComputer,
    HexProductionComputer,
    ResolutionAggregator,
    SpatialSubstrateSource,
    TractDemographicSource,
)
from babylon.domain.economics.substrate.spatial import (
    DefaultSpatialSubstrateSource,
    generate_tri_county_mesh,
)
from babylon.domain.economics.substrate.types import (
    TRI_COUNTY_FIPS,
    BoundaryFlowRegister,
    HexEconomicState,
    HexGrid,
    HexTenureComposition,
    SubstrateConfig,
    TractWeight,
)

__all__ = [
    # Constants
    "CONSERVATION_TOLERANCE",
    "TRI_COUNTY_FIPS",
    # Types
    "BoundaryFlowRegister",
    "HexEconomicState",
    "HexGrid",
    "HexTenureComposition",
    "SubstrateConfig",
    "TractWeight",
    # Ground rent (Feature 043)
    "GroundRentResult",
    "compute_ground_rent",
    # Protocols
    "CommuterFlowSource",
    "ConservationChecker",
    "HexCirculationComputer",
    "HexEqualizationComputer",
    "HexProductionComputer",
    "ResolutionAggregator",
    "SpatialSubstrateSource",
    "TractDemographicSource",
    # Default implementations
    "DefaultConservationChecker",
    "DefaultHexCirculationComputer",
    "DefaultHexEqualizationComputer",
    "DefaultHexProductionComputer",
    "DefaultResolutionAggregator",
    "DefaultSpatialSubstrateSource",
    # Convenience functions
    "generate_tri_county_mesh",
    "hydrate_hex_grid",
]
