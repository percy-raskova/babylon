"""Computed types for organization calculators (Feature 031, T004).

Frozen Pydantic models representing calculator results. These are NOT
stored on Organization entities — they are produced by composition,
consciousness, and topology calculators.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import ConsciousnessTendency, TopologyType


class ConsciousnessDelta(BaseModel):
    """Result of a single organization's consciousness effect on a community.

    Historically produced by the Feature-031 ``consciousness_effect()``
    calculator (retired, fork ledger F7); kept as the typed vocabulary for
    consciousness deltas.

    Attributes:
        collective_identity_delta: Change to target community's CI.
        tendency_pressure: Direction of ideological pressure.
        tendency_magnitude: Strength of tendency pressure (non-negative).
        source_org_id: Which organization caused this.
    """

    model_config = ConfigDict(frozen=True)

    collective_identity_delta: float = Field(
        description="Change to target community's collective identity",
    )
    tendency_pressure: ConsciousnessTendency = Field(
        description="Direction of ideological pressure",
    )
    tendency_magnitude: float = Field(
        ge=0.0,
        description="Strength of tendency pressure",
    )
    source_org_id: str = Field(
        description="ID of the organization producing this effect",
    )


class AggregatedEffect(BaseModel):
    """Result of aggregating multiple organization consciousness effects.

    Historically produced by the Feature-031 ``aggregate_consciousness_effects()``
    calculator (retired, fork ledger F7).

    Attributes:
        total_ci_delta: Sum of all organization CI deltas.
        dominant_tendency: Tendency with strongest weighted presence.
        tendency_weights: Magnitude per tendency for tie analysis.
        new_ci: Clamped [0, 1] result after applying total_ci_delta.
    """

    model_config = ConfigDict(frozen=True)

    total_ci_delta: float = Field(
        description="Sum of all organization CI deltas",
    )
    dominant_tendency: ConsciousnessTendency | None = Field(
        description="Tendency with strongest weighted presence (None if no effects)",
    )
    tendency_weights: dict[ConsciousnessTendency, float] = Field(
        default_factory=dict,
        description="Magnitude per tendency for tie analysis",
    )
    new_ci: float = Field(
        ge=0.0,
        le=1.0,
        description="Clamped [0, 1] result after applying total_ci_delta",
    )


class CompositionResult(BaseModel):
    """Result of a composition analysis (class, community, or lifecycle).

    Produced by ``class_composition()``, ``community_composition()``,
    or ``lifecycle_composition()`` calculators.

    Attributes:
        distribution: Proportional breakdown (key depends on axis).
        total_members: Total membership count.
        axis: Which analysis axis ("class", "community", or "lifecycle").
    """

    model_config = ConfigDict(frozen=True)

    distribution: dict[str, float] = Field(
        description="Proportional breakdown (key depends on axis)",
    )
    total_members: float = Field(
        ge=0.0,
        description="Total membership count",
    )
    axis: str = Field(
        description='Analysis axis: "class", "community", or "lifecycle"',
    )


class TopologyClassification(BaseModel):
    """Result of topology classification for an organization's COMMAND subgraph.

    Produced by ``classify_topology()`` calculator.

    Attributes:
        topology_type: Classified topology (STAR/HIERARCHY/MESH/CELL) or None.
        articulation_points: Node IDs that are articulation points.
        component_count: Number of connected components.
        is_connected: Whether the COMMAND subgraph is connected.
    """

    model_config = ConfigDict(frozen=True)

    topology_type: TopologyType | None = Field(
        description="Classified topology type (None if unclassifiable)",
    )
    articulation_points: list[str] = Field(
        default_factory=list,
        description="Node IDs that are articulation points",
    )
    component_count: int = Field(
        ge=0,
        description="Number of connected components in COMMAND subgraph",
    )
    is_connected: bool = Field(
        description="Whether the COMMAND subgraph is connected",
    )
