"""Result types for bifurcation topology analysis (Feature 033).

All types are frozen Pydantic models representing analysis snapshots.
No mutable state — each computation produces a new instance.

See Also:
    :mod:`babylon.bifurcation.analysis`: Produces ``BifurcationResult``.
    ``specs/033-bifurcation-topology/data-model.md``: Full field specs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import CommunityType


class AxisTendency(BaseModel):
    """Per-contradiction-axis analysis result.

    Args:
        axis_id: Matches Contradiction.id (e.g. "colonial", "patriarchal").
        cross_solidarity_weighted: Sum of consciousness-weighted cross-line solidarity.
        lateral_antagonism_weighted: Sum of antagonistic edge weights on same side.
        tendency_ratio: cross / (lateral + epsilon); >1.0 = solidarity-dominant.
        cross_edge_count: Raw count of cross-line solidarity edges.
        lateral_edge_count: Raw count of lateral antagonism edges.
        upward_edge_count: Raw count of upward antagonism edges.
    """

    model_config = ConfigDict(frozen=True)

    axis_id: str
    cross_solidarity_weighted: float = Field(ge=0.0)
    lateral_antagonism_weighted: float = Field(ge=0.0)
    tendency_ratio: float = Field(ge=0.0)
    cross_edge_count: int = Field(ge=0)
    lateral_edge_count: int = Field(ge=0)
    upward_edge_count: int = Field(ge=0)


class BridgeInfo(BaseModel):
    """A community spanning a contradiction axis with weighted potential.

    Args:
        community_type: Which community (e.g. DISABLED, INCARCERATED).
        axes_spanned: Contradiction IDs this community bridges.
        collective_identity: Raw CI from CommunityConsciousness.
        sigmoid_ci: Sigmoid-transformed CI (breakage cliff applied).
        infrastructure: Community infrastructure from CommunityState.
        weighted_potential: infrastructure * sigmoid_ci.
        member_count: Number of agents in this community.
    """

    model_config = ConfigDict(frozen=True)

    community_type: CommunityType
    axes_spanned: list[str] = Field(min_length=1)
    collective_identity: float = Field(ge=0.0, le=1.0)
    sigmoid_ci: float = Field(ge=0.0, le=1.0)
    infrastructure: float = Field(ge=0.0, le=1.0)
    weighted_potential: float = Field(ge=0.0)
    member_count: int = Field(ge=0)


class SolidarityCeiling(BaseModel):
    """Material constraints on solidarity formation between two agents.

    Args:
        base_ceiling: From wage gap ratio interpolation.
        exploitation_bonus: +0.2 if shared exploitation source.
        community_bonus: Bonus from shared community membership.
        effective_ceiling: Clamped sum of all components.
        wage_gap_ratio: max(w_a, w_b) / min(w_a, w_b).
        geographically_proximate: Whether agents share ADJACENCY-linked territories.
    """

    model_config = ConfigDict(frozen=True)

    base_ceiling: float = Field(ge=0.0, le=1.0)
    exploitation_bonus: float = Field(ge=0.0, le=0.2)
    community_bonus: float = Field(ge=0.0)
    effective_ceiling: float = Field(ge=0.0, le=1.0)
    wage_gap_ratio: float = Field(ge=0.0)
    geographically_proximate: bool


class WeightedSolidarityResult(BaseModel):
    """Result of consciousness-weighted solidarity computation (Feature 034).

    Extends the original float return with a crisis-fragile marker:
    solidarity edges where both endpoints have r < crisis_fragile_threshold
    are marked as crisis-fragile (assimilation trap indicator).

    Args:
        weight: Consciousness-weighted solidarity value [0, 1].
        crisis_fragile: True if effective CI < crisis-fragile threshold.
    """

    model_config = ConfigDict(frozen=True)

    weight: float = Field(ge=0.0)
    crisis_fragile: bool = False


class BifurcationResult(BaseModel):
    """Complete output of a single bifurcation analysis computation.

    Produced by ``bifurcation_tendency()`` — one per tick.

    Args:
        overall_tendency: Weakest-link classification.
        per_axis_tendency: Axis ID to tendency ratio (>1.0 = solidarity-dominant).
        cross_line_solidarity_count: Raw SOLIDARITY edges crossing any axis.
        within_line_solidarity_count: Raw SOLIDARITY edges within same side.
        lateral_antagonism_count: Antagonistic edges within same side.
        upward_antagonism_count: Edges from marginalized toward hegemonic.
        consciousness_weighted_cross_solidarity: Consciousness-weighted sum.
        mean_collective_identity_marginalized: Mean CI across marginalized.
        dominant_tendency_distribution: ConsciousnessTendency fractions.
        community_bridge_count: Communities spanning axes.
        bridge_potential_weighted: Sum of infrastructure * sigmoid(CI).
        legitimation_index: Population-weighted mean legitimation.
        raw_beta_0: Connected components (all SOLIDARITY edges).
        raw_beta_1: Independent cycles (all SOLIDARITY edges).
        filtered_beta_0: Components (consciousness-filtered only).
        filtered_beta_1: Cycles (consciousness-filtered only).
        resilience_under_targeted_purge: Post-purge L_max / pre-purge L_max.
        equivalence_class_distribution: Class size to count.
        critical_singletons: Articulation point node IDs.
        critical_cutsets: Minimal disconnecting edge sets.
        mean_assimilation_ratio_marginalized: Mean f/(l+f) across marginalized.
        crisis_fragile_edge_count: Solidarity edges marked crisis-fragile.
    """

    model_config = ConfigDict(frozen=True)

    overall_tendency: Literal["revolutionary", "fascist", "indeterminate"]
    per_axis_tendency: dict[str, float]
    cross_line_solidarity_count: int = Field(ge=0)
    within_line_solidarity_count: int = Field(ge=0)
    lateral_antagonism_count: int = Field(ge=0)
    upward_antagonism_count: int = Field(ge=0)
    consciousness_weighted_cross_solidarity: float = Field(ge=0.0)
    mean_collective_identity_marginalized: float = Field(ge=0.0, le=1.0)
    dominant_tendency_distribution: dict[str, float]
    community_bridge_count: int = Field(ge=0)
    bridge_potential_weighted: float = Field(ge=0.0)
    legitimation_index: float = Field(ge=0.0, le=1.0)
    raw_beta_0: int = Field(ge=0)
    raw_beta_1: int = Field(ge=0)
    filtered_beta_0: int = Field(ge=0)
    filtered_beta_1: int = Field(ge=0)
    resilience_under_targeted_purge: float = Field(ge=0.0, le=1.0)
    equivalence_class_distribution: dict[int, int]
    critical_singletons: list[str]
    critical_cutsets: list[frozenset[str]]
    mean_assimilation_ratio_marginalized: float = Field(default=0.0, ge=0.0, le=1.0)
    crisis_fragile_edge_count: int = Field(default=0, ge=0)


class BifurcationSnapshot(BaseModel):
    """Wraps BifurcationResult with tick metadata.

    Stored in ``BifurcationMonitor._bifurcation_history``.

    Args:
        tick: Simulation tick when computed.
        result: The full analysis result.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(ge=0)
    result: BifurcationResult
