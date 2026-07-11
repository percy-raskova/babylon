"""Infrastructure topology layer for the Babylon simulation (Feature 036).

Provides terrain classification, typed infrastructure on H3 mesh edges and
vertices, biocapacity extraction, nonlocal edges for airports/shipping lanes,
internet consciousness field operations, weighted Laplacian integration, and
R8 geographic substrate generation/aggregation.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: Feature specification.
    ``specs/036-infrastructure-topology/plan.md``: Implementation plan.
"""

from babylon.domain.geography.capacity import DefaultEdgeCapacityCalculator
from babylon.domain.geography.internet import (
    DefaultInternetAccessManager,
    DefaultInternetFieldOperator,
)
from babylon.domain.geography.inventory import DefaultInfrastructureInventory
from babylon.domain.geography.nonlocal_edges import (
    generate_airport_edges,
    generate_shipping_edges,
)
from babylon.domain.geography.protocols import (
    BiocapacityStore,
    EdgeCapacityCalculator,
    InfrastructureInventory,
    InternetAccessManager,
    InternetFieldOperator,
    SpatialSnapper,
    TerrainClassifier,
)

# R8 Geographic Substrate (Feature 036-R8)
from babylon.domain.geography.r8_pipeline import R8SubstrateResult, build_r8_substrate
from babylon.domain.geography.r8_types import HexR8State, R8FeatureType, R8LinearFeature
from babylon.domain.geography.terrain import (
    DefaultBiocapacityStore,
    DefaultTerrainClassifier,
)
from babylon.domain.geography.types import (
    BiocapacityStockState,
    EdgeCapacityResult,
    ExtractionResult,
    InfrastructureLinkState,
    InternetAccessState,
    InternetResponseResult,
    JunctionState,
    NonlocalEdgeState,
    OpsecResult,
    SurveillanceResult,
    TerrainClassification,
    VertexState,
)

__all__: list[str] = [
    # DTOs
    "BiocapacityStockState",
    "EdgeCapacityResult",
    "ExtractionResult",
    "InfrastructureLinkState",
    "InternetAccessState",
    "InternetResponseResult",
    "JunctionState",
    "NonlocalEdgeState",
    "OpsecResult",
    "SurveillanceResult",
    "TerrainClassification",
    "VertexState",
    # R8 Substrate DTOs
    "HexR8State",
    "R8FeatureType",
    "R8LinearFeature",
    "R8SubstrateResult",
    # Protocols
    "BiocapacityStore",
    "EdgeCapacityCalculator",
    "InfrastructureInventory",
    "InternetAccessManager",
    "InternetFieldOperator",
    "SpatialSnapper",
    "TerrainClassifier",
    # Implementations
    "DefaultBiocapacityStore",
    "DefaultEdgeCapacityCalculator",
    "DefaultInternetAccessManager",
    "DefaultInternetFieldOperator",
    "DefaultInfrastructureInventory",
    "DefaultTerrainClassifier",
    # Nonlocal edge generators
    "generate_airport_edges",
    "generate_shipping_edges",
    # R8 Pipeline
    "build_r8_substrate",
]
