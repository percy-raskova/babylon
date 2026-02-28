"""Consciousness effect calculator (Feature 031, T021-T022).

Implements the five-factor consciousness effect formula and aggregation
for concurrent organizational effects on communities.
"""

from __future__ import annotations

from babylon.config.defines import OrganizationDefines
from babylon.models.entities.organization import (
    Business,
    CivilSocietyOrg,
    Organization,
    PoliticalFaction,
    StateApparatus,
)
from babylon.models.enums import ConsciousnessTendency, LegalStanding
from babylon.organizations.types import AggregatedEffect, ConsciousnessDelta


def derive_credibility(
    org: Organization,
    defines: OrganizationDefines,
    community_workforce: int | None = None,
) -> float:
    """Derive credibility factor by organization subtype.

    Args:
        org: Organization instance (any subtype).
        defines: OrganizationDefines with tunable parameters.
        community_workforce: Total workforce in target community (Business only).

    Returns:
        Credibility value in [0, 1].
    """
    if isinstance(org, CivilSocietyOrg):
        return float(org.legitimacy)

    if isinstance(org, PoliticalFaction):
        return defines.credibility_default_faction

    if isinstance(org, StateApparatus):
        if org.legal_standing == LegalStanding.SOVEREIGN:
            return defines.credibility_sovereign
        if org.legal_standing == LegalStanding.CHARTERED:
            return defines.credibility_chartered
        return 0.5

    if isinstance(org, Business):
        if community_workforce is None or community_workforce <= 0:
            return 0.0
        share = org.employment_count / community_workforce
        return min(share, 1.0)

    return 0.0


def _tendency_modifier(
    tendency: ConsciousnessTendency,
    defines: OrganizationDefines,
) -> float:
    """Resolve tendency modifier from defines."""
    modifier_map = {
        ConsciousnessTendency.REVOLUTIONARY: defines.tendency_modifier_revolutionary,
        ConsciousnessTendency.LIBERAL: defines.tendency_modifier_liberal,
        ConsciousnessTendency.FASCIST: defines.tendency_modifier_fascist,
    }
    return modifier_map[tendency]


def consciousness_effect(
    org: Organization,
    defines: OrganizationDefines,
    community_workforce: int | None = None,
) -> ConsciousnessDelta:
    """Compute a single organization's consciousness effect on a community.

    Five-factor product formula:
    ``consciousness_delta = tendency_modifier * cadre_level * cohesion * credibility``

    Args:
        org: Organization instance (any subtype).
        defines: OrganizationDefines with tunable parameters.
        community_workforce: Total workforce in target community (Business only).

    Returns:
        ConsciousnessDelta with CI change and tendency pressure.
    """
    credibility = derive_credibility(org, defines, community_workforce)

    # Short-circuit: zero product → zero effect
    if org.cohesion == 0.0 or org.cadre_level == 0.0 or credibility == 0.0:
        return ConsciousnessDelta(
            collective_identity_delta=0.0,
            tendency_pressure=org.consciousness_tendency,
            tendency_magnitude=0.0,
            source_org_id=org.id,
        )

    modifier = _tendency_modifier(org.consciousness_tendency, defines)
    raw_product = modifier * float(org.cadre_level) * float(org.cohesion) * credibility

    if org.consciousness_tendency == ConsciousnessTendency.FASCIST:
        # FASCIST: zero CI delta, non-zero tendency pressure
        return ConsciousnessDelta(
            collective_identity_delta=0.0,
            tendency_pressure=ConsciousnessTendency.FASCIST,
            tendency_magnitude=abs(raw_product),
            source_org_id=org.id,
        )

    # REVOLUTIONARY or LIBERAL: CI delta = raw product
    return ConsciousnessDelta(
        collective_identity_delta=raw_product,
        tendency_pressure=org.consciousness_tendency,
        tendency_magnitude=abs(raw_product),
        source_org_id=org.id,
    )


def aggregate_consciousness_effects(
    deltas: list[ConsciousnessDelta],
    current_ci: float,
) -> AggregatedEffect:
    """Aggregate multiple organization consciousness effects.

    CI deltas are summed. Tendency pressures compete — strongest weighted
    tendency wins. Result CI is clamped to [0, 1].

    Args:
        deltas: List of ConsciousnessDelta from individual orgs.
        current_ci: Current community collective identity [0, 1].

    Returns:
        AggregatedEffect with total CI change and dominant tendency.
    """
    if not deltas:
        return AggregatedEffect(
            total_ci_delta=0.0,
            dominant_tendency=None,
            tendency_weights={},
            new_ci=current_ci,
        )

    total_ci_delta = sum(d.collective_identity_delta for d in deltas)

    # Group by tendency, sum magnitudes
    tendency_weights: dict[ConsciousnessTendency, float] = {}
    for d in deltas:
        tendency_weights[d.tendency_pressure] = (
            tendency_weights.get(d.tendency_pressure, 0.0) + d.tendency_magnitude
        )

    # Dominant tendency = highest total weight
    dominant_tendency: ConsciousnessTendency | None = None
    max_weight = 0.0
    for tendency, weight in tendency_weights.items():
        if weight > max_weight:
            max_weight = weight
            dominant_tendency = tendency

    new_ci = max(0.0, min(1.0, current_ci + total_ci_delta))

    return AggregatedEffect(
        total_ci_delta=total_ci_delta,
        dominant_tendency=dominant_tendency,
        tendency_weights=tendency_weights,
        new_ci=new_ci,
    )
