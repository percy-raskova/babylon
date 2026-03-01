"""Terrain classification and biocapacity extraction contracts.

Defines the Protocol interfaces for terrain classification, biocapacity
stock management, and Natural Earth data reading. These contracts
establish the API surface for US1 (Terrain Classification) and
biocapacity extraction mechanics (FR-001 through FR-008).

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-001 through FR-008
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations (as string literals for contract-level specification)
# ---------------------------------------------------------------------------

TERRAIN_TYPES = ("LAND", "WATER", "RESOURCE")

BIOCAPACITY_TYPES = (
    "FRESHWATER",
    "FISHERY",
    "SHIPPING_ACCESS",
    "MINERAL",
    "TIMBER",
    "HYDROELECTRIC",
)

# featurecla values from ne_10m_geography_regions_polys that map to RESOURCE
RESOURCE_FEATURECLA = (
    "Range/mtn",
    "Plateau",
    "Basin",
    "Delta",
    "Wetlands",
)


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------


class TerrainClassification(BaseModel):
    """Terrain classification result for a single hex.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-001
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell identifier")
    terrain_type: str = Field(description="LAND, WATER, or RESOURCE")
    water_coverage_fraction: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of hex area covered by water polygons",
    )
    resource_coverage_fraction: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of hex area covered by resource region polygons",
    )
    source_features: list[str] = Field(
        default_factory=list,
        description="NE feature names contributing to classification",
    )


class BiocapacityStockState(BaseModel):
    """Current state of a biocapacity stock on a non-LAND hex.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-005, FR-006
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell identifier")
    stock_type: str = Field(description="BiocapacityType value")
    initial_value: float = Field(ge=0.0, description="Stock at initialization")
    current_value: float = Field(ge=0.0, description="Current stock level")
    depleted: bool = Field(
        default=False,
        description="True when current_value == 0.0",
    )


class ExtractionResult(BaseModel):
    """Result of biocapacity extraction through an edge.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-007
    """

    model_config = ConfigDict(frozen=True)

    source_h3: str = Field(description="Resource hex (WATER/RESOURCE)")
    target_h3: str = Field(description="Extracting LAND hex")
    stock_type: str = Field(description="BiocapacityType value")
    amount_extracted: float = Field(ge=0.0, description="Units extracted this tick")
    remaining_stock: float = Field(ge=0.0, description="Stock after extraction")
    infrastructure_constraint: float = Field(
        ge=0.0,
        description="Max extraction allowed by edge infrastructure",
    )


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class TerrainClassifier(Protocol):
    """Classifies hex cells by terrain type from NE geographic data.

    Implementations read Natural Earth lake, river, and geographic region
    polygons and perform spatial intersection with H3 cell boundaries to
    determine terrain type.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-001, FR-003
    """

    def classify_hex(self, h3_index: str) -> TerrainClassification:
        """Classify a single hex by terrain type.

        Args:
            h3_index: H3 cell identifier at resolution 7.

        Returns:
            TerrainClassification with terrain_type and coverage fractions.
        """
        ...

    def classify_mesh(
        self,
        h3_indices: Sequence[str],
    ) -> dict[str, TerrainClassification]:
        """Classify all hexes in a mesh.

        Args:
            h3_indices: Collection of H3 cell identifiers.

        Returns:
            Dict mapping h3_index to TerrainClassification.
        """
        ...


@runtime_checkable
class BiocapacityStore(Protocol):
    """Manages biocapacity stocks on WATER and RESOURCE hexes.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-005 through FR-008
    """

    def initialize_stocks(
        self,
        classifications: dict[str, TerrainClassification],
    ) -> dict[str, list[BiocapacityStockState]]:
        """Initialize biocapacity stocks for all non-LAND hexes.

        Args:
            classifications: Terrain classifications for the mesh.

        Returns:
            Dict mapping h3_index to list of BiocapacityStockState.
        """
        ...

    def get_stock(
        self,
        h3_index: str,
        stock_type: str,
    ) -> BiocapacityStockState | None:
        """Get current stock state for a hex and type.

        Args:
            h3_index: H3 cell identifier.
            stock_type: BiocapacityType value.

        Returns:
            Current stock state, or None if no stock of this type.
        """
        ...

    def extract(
        self,
        source_h3: str,
        target_h3: str,
        stock_type: str,
        infrastructure_capacity: float,
        depletion_rate: float,
    ) -> ExtractionResult:
        """Extract biocapacity from a resource hex through an edge.

        Extraction amount is min(infrastructure_capacity, depletion_rate *
        current_value, current_value). Updates stock in place.

        Args:
            source_h3: Resource hex (WATER/RESOURCE).
            target_h3: Extracting LAND hex.
            stock_type: BiocapacityType value.
            infrastructure_capacity: Max extraction from edge infrastructure.
            depletion_rate: Per-tick depletion rate from GameDefines.

        Returns:
            ExtractionResult with amount extracted and remaining stock.

        See Also:
            ``specs/036-infrastructure-topology/spec.md``: FR-007
        """
        ...
