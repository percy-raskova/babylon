"""Infrastructure inventory and edge capacity contracts.

Defines the Protocol interfaces for infrastructure links on edges and vertices,
edge capacity computation, nonlocal edge generation, and the spatial snapping
pipeline that maps Natural Earth features to the H3 mesh.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-009 through FR-022
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations (as string literals for contract-level specification)
# ---------------------------------------------------------------------------

INFRASTRUCTURE_TYPES = (
    "HIGHWAY",
    "ARTERIAL",
    "LOCAL_ROAD",
    "RAIL",
    "PIPELINE",
    "TRANSMISSION",
    "SHIPPING_LANE",
    "AIR_LINK",
)

FLOW_CATEGORIES = (
    "FREIGHT",
    "COMMUTER",
    "VALUE",
    "ENERGY",
    "CONSCIOUSNESS",
)

JUNCTION_TYPES = (
    "INTERCHANGE",
    "SUBSTATION",
    "RAIL_JUNCTION",
    "PORT",
    "AIRPORT",
)

LOCALITY_CLASSES = (
    "LOCAL",
    "SEMI_LOCAL",
    "NONLOCAL",
)


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------


class InfrastructureLinkState(BaseModel):
    """State of a single infrastructure link on an edge or vertex.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-009, FR-010
    """

    model_config = ConfigDict(frozen=True)

    link_id: str = Field(description="Unique identifier for this link")
    infra_type: str = Field(description="InfrastructureType value")
    capacity: dict[str, float] = Field(
        description="Capacity per FlowCategory (keys are FlowCategory values)",
    )
    condition: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Health/degradation scalar [0.0=destroyed, 1.0=pristine]",
    )
    owner_org_id: str | None = Field(
        default=None,
        description="Owning organization node ID",
    )
    ne_source_id: str | None = Field(
        default=None,
        description="Natural Earth feature ID for provenance",
    )

    def effective_capacity(self, category: str) -> float:
        """Effective capacity for a flow category: capacity * condition.

        Args:
            category: FlowCategory value.

        Returns:
            Effective capacity, or 0.0 if category not served.
        """
        return self.capacity.get(category, 0.0) * self.condition


class EdgeCapacityResult(BaseModel):
    """Aggregate capacity computation result for an edge.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-012, FR-013, FR-014
    """

    model_config = ConfigDict(frozen=True)

    source_h3: str = Field(description="Source hex H3 index")
    target_h3: str = Field(description="Target hex H3 index")
    aggregate_capacity: dict[str, float] = Field(
        description="Sum of effective link capacities per FlowCategory",
    )
    natural_capacity: dict[str, float] = Field(
        description="Minimal natural capacity for LAND-LAND edges (commuter, consciousness)",
    )
    total_capacity: dict[str, float] = Field(
        description="aggregate + natural per FlowCategory, used as edge weight",
    )


class JunctionState(BaseModel):
    """State of junction infrastructure at a vertex.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-016, FR-017
    """

    model_config = ConfigDict(frozen=True)

    junction_type: str = Field(description="JunctionType value")
    capacity_contribution: float = Field(
        ge=0.0,
        description="Capacity added to adjacent edges",
    )
    condition: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Health/degradation scalar",
    )
    owner_org_id: str | None = Field(
        default=None,
        description="Owning organization node ID",
    )
    ne_source_id: str | None = Field(
        default=None,
        description="Natural Earth feature ID for provenance",
    )


class VertexState(BaseModel):
    """State of a vertex (triple junction) in the hex mesh.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-015, FR-016
    """

    model_config = ConfigDict(frozen=True)

    vertex_id: str = Field(description="Canonical ID (sorted triple hash)")
    adjacent_h3: tuple[str, str, str] = Field(
        description="Three adjacent hex H3 indices (ordered)",
    )
    lat: float = Field(description="Latitude (centroid of 3 hex centroids)")
    lon: float = Field(description="Longitude (centroid of 3 hex centroids)")
    junctions: list[JunctionState] = Field(
        default_factory=list,
        description="Junction infrastructure inventory",
    )


class NonlocalEdgeState(BaseModel):
    """State of a nonlocal edge connecting non-adjacent vertices.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-019 through FR-022
    """

    model_config = ConfigDict(frozen=True)

    source_vertex_id: str = Field(description="Origin vertex ID")
    target_vertex_id: str = Field(description="Destination vertex ID")
    link: InfrastructureLinkState = Field(
        description="The infrastructure creating this edge",
    )
    distance_km: float = Field(
        gt=0.0,
        description="Great-circle distance between vertices",
    )
    locality_class: str = Field(description="LOCAL, SEMI_LOCAL, or NONLOCAL")
    origin_feature: str = Field(
        description="NE feature that generated this edge",
    )


# ---------------------------------------------------------------------------
# Protocols
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

        Used by BUILD_INFRASTRUCTURE action (Feature 032).

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

        Used by ATTACK_INFRASTRUCTURE action (Feature 032).

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

        Per FR-018, degradation cascades to all 3 adjacent edges.

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

        Aggregate capacity = sum of link effective capacities.
        Natural capacity = population-derived minimal capacity (LAND-LAND only,
        commuter and consciousness categories only, per FR-014).
        Total capacity = aggregate + natural.

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
        ``specs/036-infrastructure-topology/research.md``: R7
    """

    def snap_linear_features(
        self,
        edges: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], list[InfrastructureLinkState]]:
        """Snap Natural Earth linear features (roads, railroads) to H3 edges.

        Performs spatial intersection of NE linear geometries with buffered
        H3 edge boundary segments.

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
        """Snap Natural Earth point features (airports, ports) to H3 vertices.

        Performs nearest-neighbor assignment within tolerance radius.

        Args:
            vertices: List of vertex states with positions.

        Returns:
            Dict mapping vertex_id to lists of snapped junction states.
        """
        ...
