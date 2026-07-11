"""Data transfer objects for the infrastructure topology layer (Feature 036).

Frozen Pydantic models representing terrain classifications, biocapacity
stocks, infrastructure links, edge capacities, vertex/junction states,
nonlocal edges, and internet access states.

All models use ``ConfigDict(frozen=True)`` for immutability.

See Also:
    ``specs/036-infrastructure-topology/contracts/``: Canonical protocol specs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Terrain & Biocapacity DTOs (US1)
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
    depletion_history: list[float] = Field(
        default_factory=list,
        description="Extraction amounts per tick",
    )
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
# Infrastructure Link & Edge Capacity DTOs (US2)
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


# ---------------------------------------------------------------------------
# Vertex & Junction DTOs (US3)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Nonlocal Edge DTOs (US4)
# ---------------------------------------------------------------------------


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
# Internet DTOs (US5)
# ---------------------------------------------------------------------------


class InternetAccessState(BaseModel):
    """Per-hex internet connectivity state.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-023, FR-024
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell identifier")
    internet_access: bool = Field(
        default=False,
        description="Whether broadband is available at this hex",
    )
    internet_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Coverage quality scalar derived from FCC data",
    )
    surveillance_coupling: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of consciousness flow visible to the state",
    )
    response_mode: str = Field(
        default="PERMIT",
        description="State apparatus control mode: PERMIT, THROTTLE, or SEVER",
    )


class SurveillanceResult(BaseModel):
    """Result of surveillance intelligence generation for a tick.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-027
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell where surveillance occurred")
    flow_magnitude: float = Field(
        ge=0.0,
        description="Consciousness flow magnitude through this hex",
    )
    surveillance_coupling: float = Field(
        ge=0.0,
        le=1.0,
        description="Current coupling value at this hex",
    )
    intelligence_generated: float = Field(
        ge=0.0,
        description="Intelligence added to state observation graph",
    )
    org_ids_observed: list[str] = Field(
        default_factory=list,
        description="Organization node IDs observed at this hex",
    )


class OpsecResult(BaseModel):
    """Result of COUNTER_INTEL action on internet surveillance coupling.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-028
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell where OPSEC was applied")
    org_id: str = Field(description="Organization that invested in OPSEC")
    coupling_before: float = Field(
        ge=0.0,
        le=1.0,
        description="Surveillance coupling before OPSEC",
    )
    coupling_after: float = Field(
        ge=0.0,
        le=1.0,
        description="Surveillance coupling after OPSEC",
    )
    throughput_reduction: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction of consciousness throughput lost",
    )


class InternetResponseResult(BaseModel):
    """Result of state apparatus internet response mode change.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-029
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell targeted")
    previous_mode: str = Field(description="Previous response mode")
    new_mode: str = Field(description="New response mode")
    throughput_effect: float = Field(
        ge=0.0,
        le=1.0,
        description="Remaining throughput fraction (1.0=full, 0.0=severed)",
    )
    surveillance_effect: float = Field(
        ge=0.0,
        le=1.0,
        description="Remaining surveillance fraction",
    )
    visibility: bool = Field(
        description="Whether the mode change is visible to target community",
    )
    backfire_magnitude: float = Field(
        ge=0.0,
        description="Consciousness backfire effect (signals state fear)",
    )
