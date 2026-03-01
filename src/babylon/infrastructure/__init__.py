"""Infrastructure topology layer for the Babylon simulation (Feature 036).

Provides terrain classification, typed infrastructure on H3 mesh edges and
vertices, biocapacity extraction, nonlocal edges for airports/shipping lanes,
internet consciousness field operations, and weighted Laplacian integration.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: Feature specification.
    ``specs/036-infrastructure-topology/plan.md``: Implementation plan.
"""

from babylon.infrastructure.capacity import DefaultEdgeCapacityCalculator
from babylon.infrastructure.internet import (
    DefaultInternetAccessManager,
    DefaultInternetFieldOperator,
)
from babylon.infrastructure.inventory import DefaultInfrastructureInventory
from babylon.infrastructure.nonlocal_edges import (
    generate_airport_edges,
    generate_shipping_edges,
)
from babylon.infrastructure.protocols import (
    BiocapacityStore,
    EdgeCapacityCalculator,
    InfrastructureInventory,
    InternetAccessManager,
    InternetFieldOperator,
    SpatialSnapper,
    TerrainClassifier,
)
from babylon.infrastructure.terrain import (
    DefaultBiocapacityStore,
    DefaultTerrainClassifier,
)
from babylon.infrastructure.types import (
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
]
