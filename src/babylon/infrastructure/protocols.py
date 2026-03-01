"""Protocol interfaces for the infrastructure topology layer (Feature 036).

Seven ``@runtime_checkable`` Protocols defining the API surface for terrain
classification, biocapacity management, infrastructure inventory, edge
capacity computation, spatial snapping, internet access management, and
internet consciousness field operations.

See Also:
    ``specs/036-infrastructure-topology/contracts/``: Canonical contract specs.
    :mod:`babylon.infrastructure.types`: DTO definitions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

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

# ---------------------------------------------------------------------------
# Terrain & Biocapacity (US1)
# ---------------------------------------------------------------------------


@runtime_checkable
class TerrainClassifier(Protocol):
    """Classifies hex cells by terrain type from NE geographic data.

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

        Args:
            source_h3: Resource hex (WATER/RESOURCE).
            target_h3: Extracting LAND hex.
            stock_type: BiocapacityType value.
            infrastructure_capacity: Max extraction from edge infrastructure.
            depletion_rate: Per-tick depletion rate from GameDefines.

        Returns:
            ExtractionResult with amount extracted and remaining stock.
        """
        ...


# ---------------------------------------------------------------------------
# Infrastructure Inventory & Edge Capacity (US2, US3)
# ---------------------------------------------------------------------------


@runtime_checkable
class InfrastructureInventory(Protocol):
    """Manages infrastructure links on edges and junctions on vertices.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-009 through FR-018
    """

    def get_edge_links(
        self,
        source_h3: str,
        target_h3: str,
    ) -> list[InfrastructureLinkState]:
        """Get all infrastructure links on an edge.

        Args:
            source_h3: Source hex H3 index.
            target_h3: Target hex H3 index.

        Returns:
            List of infrastructure links on the edge.
        """
        ...

    def add_edge_link(
        self,
        source_h3: str,
        target_h3: str,
        link: InfrastructureLinkState,
    ) -> None:
        """Add an infrastructure link to an edge.

        Args:
            source_h3: Source hex H3 index.
            target_h3: Target hex H3 index.
            link: The infrastructure link to add.
        """
        ...

    def degrade_link(
        self,
        link_id: str,
        condition_delta: float,
    ) -> InfrastructureLinkState:
        """Degrade an infrastructure link's condition.

        Args:
            link_id: Unique identifier of the link to degrade.
            condition_delta: Amount to reduce condition by (positive value).

        Returns:
            Updated link state after degradation.
        """
        ...

    def get_vertex(self, vertex_id: str) -> VertexState | None:
        """Get vertex state by ID.

        Args:
            vertex_id: Canonical vertex identifier.

        Returns:
            Vertex state, or None if vertex not found.
        """
        ...

    def degrade_junction(
        self,
        vertex_id: str,
        junction_type: str,
        condition_delta: float,
    ) -> list[tuple[str, str]]:
        """Degrade a junction's condition, cascading to adjacent edges.

        Args:
            vertex_id: Vertex containing the junction.
            junction_type: Type of junction to degrade.
            condition_delta: Amount to reduce condition by.

        Returns:
            List of (source_h3, target_h3) edge pairs affected by cascade.
        """
        ...

    def get_nonlocal_edges(self) -> list[NonlocalEdgeState]:
        """Get all nonlocal edges in the mesh.

        Returns:
            List of nonlocal edge states.
        """
        ...


@runtime_checkable
class EdgeCapacityCalculator(Protocol):
    """Computes aggregate edge capacity from infrastructure inventory.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-012 through FR-014
    """

    def compute_edge_capacity(
        self,
        source_h3: str,
        target_h3: str,
        source_terrain: str,
        target_terrain: str,
        links: Sequence[InfrastructureLinkState],
        population_density: float,
    ) -> EdgeCapacityResult:
        """Compute total capacity for an edge.

        Args:
            source_h3: Source hex H3 index.
            target_h3: Target hex H3 index.
            source_terrain: TerrainType of source hex.
            target_terrain: TerrainType of target hex.
            links: Infrastructure links on this edge.
            population_density: Average population density of adjacent hexes.

        Returns:
            EdgeCapacityResult with per-category capacity breakdown.
        """
        ...

    def compute_mesh_weights(
        self,
        inventory: InfrastructureInventory,
        terrain_map: dict[str, str],
        population_map: dict[str, float],
        edges: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], dict[str, float]]:
        """Compute total capacity for all edges in the mesh.

        Args:
            inventory: Infrastructure inventory to query.
            terrain_map: Mapping of h3_index to TerrainType.
            population_map: Mapping of h3_index to population density.
            edges: List of (source_h3, target_h3) edge pairs.

        Returns:
            Dict mapping edge pair to total capacity per FlowCategory.
        """
        ...


@runtime_checkable
class SpatialSnapper(Protocol):
    """Snaps Natural Earth features to H3 mesh edges and vertices.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-011, FR-017
    """

    def snap_linear_features(
        self,
        edges: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], list[InfrastructureLinkState]]:
        """Snap NE linear features (roads, railroads) to H3 edges.

        Args:
            edges: List of (source_h3, target_h3) edge pairs.

        Returns:
            Dict mapping edge pairs to lists of snapped infrastructure links.
        """
        ...

    def snap_point_features(
        self,
        vertices: Sequence[VertexState],
    ) -> dict[str, list[JunctionState]]:
        """Snap NE point features (airports, ports) to H3 vertices.

        Args:
            vertices: List of vertex states with positions.

        Returns:
            Dict mapping vertex_id to lists of snapped junction states.
        """
        ...


# ---------------------------------------------------------------------------
# Internet & Consciousness Field (US5)
# ---------------------------------------------------------------------------


@runtime_checkable
class InternetAccessManager(Protocol):
    """Manages per-hex internet access state and mutations.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-023 through FR-029
    """

    def get_state(self, h3_index: str) -> InternetAccessState | None:
        """Get internet state for a hex.

        Args:
            h3_index: H3 cell identifier.

        Returns:
            Internet access state, or None if not initialized.
        """
        ...

    def set_state(self, state: InternetAccessState) -> None:
        """Set internet state for a hex.

        Args:
            state: Internet access state to store.
        """
        ...

    def get_all_states(self) -> dict[str, InternetAccessState]:
        """Get all internet states.

        Returns:
            Dict mapping h3_index to InternetAccessState.
        """
        ...

    def initialize_from_broadband(
        self,
        broadband: dict[str, float],
        hex_to_county: dict[str, str],
        quality_data: dict[str, float] | None,
        water_hexes: set[str] | None,
    ) -> None:
        """Initialize internet access from FCC broadband data.

        Args:
            broadband: County FIPS → penetration fraction [0.0, 1.0].
            hex_to_county: H3 index → county FIPS mapping.
            quality_data: County FIPS → high-speed fraction.
            water_hexes: Set of H3 indices classified as WATER (EC-009).
        """
        ...

    def apply_opsec(
        self,
        h3_index: str,
        org_id: str,
        opsec_investment: float,
        infra_defines: object,
    ) -> OpsecResult:
        """Apply OPSEC to reduce surveillance coupling at a hex.

        Args:
            h3_index: Target hex.
            org_id: Organization investing in OPSEC.
            opsec_investment: Investment magnitude [0.0, 1.0].
            infra_defines: InfrastructureDefines for opsec_tradeoff_ratio.

        Returns:
            OpsecResult with before/after coupling and throughput reduction.
        """
        ...

    def set_response_mode(
        self,
        h3_index: str,
        mode: str,
        infra_defines: object,
    ) -> InternetResponseResult:
        """Set state apparatus internet response mode for a hex.

        Args:
            h3_index: Target hex.
            mode: InternetResponseMode value.
            infra_defines: InfrastructureDefines for throttle parameters.

        Returns:
            InternetResponseResult with effects.
        """
        ...


@runtime_checkable
class InternetFieldOperator(Protocol):
    """Manages internet consciousness field diffusion operations.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-025, FR-027
    """

    def get_connected_component(self) -> set[str]:
        """Get the set of internet-enabled hex indices forming the component.

        Returns:
            Set of H3 indices in the internet-connected component.
        """
        ...

    def propagate_consciousness(
        self,
        field_values: dict[str, float],
        diffusion_rate: float,
    ) -> dict[str, float]:
        """Run consciousness field diffusion on the internet-connected component.

        Args:
            field_values: Current consciousness field values per h3_index.
            diffusion_rate: Base diffusion rate from GameDefines.

        Returns:
            Updated consciousness field values after propagation.
        """
        ...

    def generate_surveillance(
        self,
        flow_magnitudes: dict[str, float],
        analytical_capacity: float,
    ) -> list[SurveillanceResult]:
        """Generate surveillance intelligence from consciousness flow.

        Args:
            flow_magnitudes: H3 index → consciousness flow magnitude.
            analytical_capacity: State apparatus analytical capacity [0.0, 1.0].

        Returns:
            List of SurveillanceResult for each hex with surveillance.
        """
        ...
