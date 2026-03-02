"""CO-OPT sub-verb resolution (Feature 039 Phase 8, US6).

Implements PROPAGANDIZE, INCORPORATE, DIVIDE, and BRIBE action resolution.
These are the state's first-line ideological warfare tools --- attacking
consciousness, leadership, solidarity, and material conditions.

Each function operates on simple dicts/values keeping co_opt_effects pure
and testable without graph dependency.

See Also:
    ``specs/039-state-apparatus-ai/contracts/territory-effects.md``: TE-07.
    ``specs/039-state-apparatus-ai/spec.md``: FR-B05.
    :mod:`babylon.ooda.state_ai.territory_effects`: compute_propagandize_effect.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.territory_effects import compute_propagandize_effect

# -------------------------------------------------------------------------
# PROPAGANDIZE resolution (T072)
# -------------------------------------------------------------------------

# Narrative-specific base delta multipliers
_NARRATIVE_MULTIPLIERS: dict[str, float] = {
    "we_are_all_americans": 1.0,  # Direct CI attack
    "threat_narrative": 0.5,  # Raises settler CI (different effect)
    "reform_is_working": 0.7,  # Reinforces liberal tendency
    "delegitimize_opposition": 0.3,  # Reduces org reputation (deferred)
}


def resolve_propagandize(
    territory: dict[str, Any],
    narrative: str,
    intensity: float,
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """Resolve PROPAGANDIZE action on a territory.

    Applies narrative-specific CI reduction. The core resistance formula
    from compute_propagandize_effect is used with narrative-scaled deltas.

    Narratives:
        - we_are_all_americans: Direct CI attack (multiplier 1.0).
        - threat_narrative: Raises settler CI, different from standard CI attack.
        - reform_is_working: Reinforces liberal tendency, moderate CI effect.
        - delegitimize_opposition: Weak CI effect (org reputation target deferred).

    Args:
        territory: Dict of territory node attributes (must contain collective_identity).
        narrative: Narrative type string (e.g., "we_are_all_americans").
        intensity: Action intensity [0.0, 1.0].
        defines: State AI configuration with ``propagandize_base_delta``
            and ``consciousness_resistance_factor``.

    Returns:
        New territory dict with updated collective_identity.
    """
    result = dict(territory)
    current_ci: float = result.get("collective_identity", 0.0)

    # Scale base delta by narrative multiplier and intensity
    multiplier = _NARRATIVE_MULTIPLIERS.get(narrative, 0.5)
    base_delta = defines.propagandize_base_delta * multiplier * intensity

    # Apply consciousness resistance formula
    effective_delta = compute_propagandize_effect(current_ci, base_delta, defines)

    # Special handling for threat_narrative: raises settler CI instead
    if narrative == "threat_narrative":
        settler_ci: float = result.get("settler_collective_identity", 0.0)
        result["settler_collective_identity"] = min(1.0, settler_ci + effective_delta)
        # threat_narrative doesn't reduce target CI
        return result

    # Standard CI reduction
    result["collective_identity"] = max(0.0, current_ci - effective_delta)

    return result


# -------------------------------------------------------------------------
# INCORPORATE resolution (T073)
# -------------------------------------------------------------------------


def compute_incorporate_probability(
    coherence: float,
    collective_identity: float,
    offer_attractiveness: float,
    defines: StateApparatusAIDefines,
) -> float:
    """Compute acceptance probability for INCORPORATE offer.

    Probability is inversely proportional to org Coherence and community CI.
    Higher Coherence = members more unified, less susceptible.
    Higher CI = less susceptible to individual co-option.

    Formula: p_accept = (1 - coherence) * (1 - ci) * offer_attractiveness

    Args:
        coherence: Organization coherence [0.0, 1.0].
        collective_identity: Community collective_identity [0.0, 1.0].
        offer_attractiveness: Attractiveness of the offer [0.0, 1.0].
        defines: State AI configuration (available for future tuning).

    Returns:
        Acceptance probability in [0.0, 1.0].
    """
    # Use defines.incorporate_base_attractiveness as a floor on offer attractiveness
    effective_attractiveness = max(offer_attractiveness, defines.incorporate_base_attractiveness)
    p_accept = (1.0 - coherence) * (1.0 - collective_identity) * effective_attractiveness
    return max(0.0, min(1.0, p_accept))


# -------------------------------------------------------------------------
# DIVIDE resolution (T074)
# -------------------------------------------------------------------------

# Edge degradation sequence per Constitution I.15
_EDGE_DEGRADATION: dict[str, str] = {
    "solidaristic": "transactional",
    "transactional": "antagonistic",
}


def resolve_divide(
    current_edge_type: str,
    has_prior_surveil: bool,
    defines: StateApparatusAIDefines,
) -> str:
    """Resolve DIVIDE action on an edge between organizations.

    Degrades edge type by one step:
    SOLIDARISTIC -> TRANSACTIONAL -> ANTAGONISTIC.

    Requires prior SURVEIL intelligence (precondition).

    Args:
        current_edge_type: Current edge type string.
        has_prior_surveil: Whether state has prior SURVEIL intel on target orgs.
        defines: State AI configuration with ``divide_requires_prior_surveil``.

    Returns:
        New edge type string after degradation.
        Returns current_edge_type if precondition not met or already at bottom.
    """
    # Check precondition
    if defines.divide_requires_prior_surveil and not has_prior_surveil:
        return current_edge_type

    # Apply one step of degradation
    return _EDGE_DEGRADATION.get(current_edge_type, current_edge_type)


# -------------------------------------------------------------------------
# BRIBE resolution (T075)
# -------------------------------------------------------------------------


def resolve_bribe(
    target: dict[str, Any],
    bribe_amount: float,
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """Resolve BRIBE action on a target (org or social class).

    BRIBE transfers material resources and shifts consciousness toward
    liberal assimilationism (reduces revolutionary tendency, increases
    liberal tendency).

    Args:
        target: Dict of target attributes (wealth, r_tendency, l_tendency, etc.).
        bribe_amount: Material transfer amount.
        defines: State AI configuration with ``bribe_consciousness_shift``
            and ``bribe_liberal_increase``.

    Returns:
        New target dict with updated wealth and consciousness tendencies.
    """
    result = dict(target)

    # Material transfer: increase target wealth
    old_wealth: float = result.get("wealth", 0.0)
    result["wealth"] = old_wealth + bribe_amount

    # Consciousness shift: reduce revolutionary tendency, increase liberal
    old_r: float = result.get("r_tendency", 0.0)
    old_l: float = result.get("l_tendency", 0.0)

    new_r = max(0.0, old_r - defines.bribe_consciousness_shift)
    new_l = min(1.0, old_l + defines.bribe_liberal_increase)

    result["r_tendency"] = new_r
    result["l_tendency"] = new_l

    # Mark that a TRANSACTIONAL edge should be created (caller handles graph)
    result["_state_transactional"] = True

    return result


__all__ = [
    "compute_incorporate_probability",
    "resolve_bribe",
    "resolve_divide",
    "resolve_propagandize",
]
