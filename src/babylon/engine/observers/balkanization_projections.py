"""Spec-070 observability projections (T115-T116, FR-036 / FR-037 /
FR-051).

Read-only, deterministic snapshots of Sovereign + Territory state for
downstream UI consumption (spec-042 / spec-085). The projections never
mutate the graph and never depend on the order they are called.

Per FR-051: ``SovereignProjection.projected_habitability`` extrapolates
current ``metabolic_impact`` over ``horizon_ticks`` (default 20 from
:class:`BalkanizationDefines`) assuming no policy change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.formulas.balkanization import (
    calculate_metabolic_impact,
    extrapolate_habitability,
)
from babylon.models.enums import ExtractionPolicy

if TYPE_CHECKING:  # pragma: no cover
    from babylon.engine.graph_protocol import GraphProtocol


class SovereignProjection(BaseModel):
    """Read-only snapshot of a Sovereign's state + 20-tick projection
    of its claimed-territory habitability under the current policy."""

    model_config = ConfigDict(frozen=True)

    sovereign_id: str
    name: str
    sovereignty_type: str
    legitimacy: float
    ruling_faction_id: str | None
    extraction_policy: ExtractionPolicy
    metabolic_impact: float
    claimed_territory_count: int
    projected_habitability: float = Field(
        description=(
            "Linear extrapolation of mean claimed-territory habitability "
            "over ``horizon_ticks`` (default "
            "BalkanizationDefines.projected_habitability_horizon_ticks)."
        )
    )


class TerritoryProjection(BaseModel):
    """Read-only snapshot of a Territory's claim/influence state."""

    model_config = ConfigDict(frozen=True)

    territory_id: str
    habitability: float
    effective_sovereign_id: str | None
    effective_control_level: float
    is_dual_power: bool
    claimant_count: int
    influencer_count: int


def observe_sovereign(
    graph: GraphProtocol,
    sovereign_id: str,
    horizon_ticks: int | None = None,
    defines: BalkanizationDefines | None = None,
) -> SovereignProjection | None:
    """Return a frozen projection of ``sovereign_id``'s state, or None
    when the Sovereign is absent.

    Args:
        graph: GraphProtocol exposing :meth:`get_node` +
            :meth:`query_sovereign_claims`.
        sovereign_id: Target Sovereign node ID.
        horizon_ticks: Optional override for the projection horizon.
            Defaults to
            :attr:`BalkanizationDefines.projected_habitability_horizon_ticks`.
        defines: Optional override defines.
    """

    if defines is None:
        defines = BalkanizationDefines()
    if horizon_ticks is None:
        horizon_ticks = defines.projected_habitability_horizon_ticks

    node = graph.get_node(sovereign_id)
    if node is None:
        return None
    attrs = node.attributes
    policy_raw = attrs.get("extraction_policy", "continue")
    try:
        policy = ExtractionPolicy(policy_raw)
    except (TypeError, ValueError):
        policy = ExtractionPolicy.CONTINUE
    metabolic_impact = calculate_metabolic_impact(policy, defines=defines)

    claims = graph.query_sovereign_claims(sovereign_id)
    # Mean habitability across claimed territories.
    habitability_values: list[float] = []
    for territory_id, _ctrl, _legal in claims:
        territory_node = graph.get_node(territory_id)
        if territory_node is None:
            continue
        habitability_values.append(float(territory_node.attributes.get("habitability", 1.0)))
    mean_habitability = (
        sum(habitability_values) / len(habitability_values) if habitability_values else 1.0
    )
    projected = extrapolate_habitability(mean_habitability, metabolic_impact, horizon_ticks)

    return SovereignProjection(
        sovereign_id=sovereign_id,
        name=str(attrs.get("name", sovereign_id)),
        sovereignty_type=str(attrs.get("sovereignty_type", "provisional")),
        legitimacy=float(attrs.get("legitimacy", 0.0)),
        ruling_faction_id=attrs.get("ruling_faction_id"),
        extraction_policy=policy,
        metabolic_impact=metabolic_impact,
        claimed_territory_count=len(claims),
        projected_habitability=projected,
    )


def observe_territory(
    graph: GraphProtocol,
    territory_id: str,
) -> TerritoryProjection | None:
    """Return a frozen projection of ``territory_id``'s claim state."""

    node = graph.get_node(territory_id)
    if node is None:
        return None
    attrs = node.attributes
    claims = graph.query_territory_claims(territory_id)
    influences = graph.query_faction_influence_by_territory(territory_id)
    active_claimants = [row for row in claims if row[1] > 0.0]
    effective_sov: str | None = None
    effective_ctrl = 0.0
    if claims:
        effective_sov = claims[0][0]
        effective_ctrl = float(claims[0][1])
    return TerritoryProjection(
        territory_id=territory_id,
        habitability=float(attrs.get("habitability", 1.0)),
        effective_sovereign_id=effective_sov,
        effective_control_level=effective_ctrl,
        is_dual_power=len(active_claimants) >= 2,
        claimant_count=len(claims),
        influencer_count=len(influences),
    )


__all__ = [
    "SovereignProjection",
    "TerritoryProjection",
    "observe_sovereign",
    "observe_territory",
]
