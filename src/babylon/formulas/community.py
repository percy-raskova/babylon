"""Community layer formulas (Feature 022).

Solidarity potential, threat score, infrastructure decay, and solidarity
amplification formulas for the hypergraph community system.

See Also:
    :mod:`babylon.engine.systems.community`: CommunitySystem consuming these formulas.
    :mod:`babylon.models.entities.community`: Data models for community state.
"""

from __future__ import annotations

from typing import Any


def calculate_solidarity_potential(
    base_solidarity: float,
    shared_count: int,
    rent_a: float,
    rent_b: float,
    overlap_bonus: float = 0.1,
    rent_penalty: float = 0.05,
) -> float:
    """Compute solidarity potential between two agents from community overlap.

    Shared community membership creates conditions for solidarity formation,
    penalized by imperial rent differential (material divergence impedes
    solidarity even with shared identity).

    Args:
        base_solidarity: Base class solidarity between the two agents.
        shared_count: Number of communities both agents share.
        rent_a: Imperial rent received by agent A.
        rent_b: Imperial rent received by agent B.
        overlap_bonus: Bonus per shared community membership.
        rent_penalty: Penalty per unit of rent differential.

    Returns:
        Solidarity potential score (may be negative if rent gap dominates).

    Examples:
        >>> calculate_solidarity_potential(0.3, 2, 0.0, 0.0)
        0.5
        >>> calculate_solidarity_potential(0.3, 0, 0.0, 0.0)
        0.3
    """
    community_bonus = overlap_bonus * shared_count
    rent_cost = rent_penalty * abs(rent_a - rent_b)
    return base_solidarity + community_bonus - rent_cost


def calculate_threat_score(
    memberships: list[tuple[float, float, float, float]],
) -> float:
    """Compute per-agent threat score from community memberships.

    Each membership contributes: heat * effective_visibility * role_weight
    * legal_status_multiplier. The total is the sum across all memberships.

    Args:
        memberships: List of (heat, effective_visibility, role_weight,
            legal_status_multiplier) tuples, one per community membership.

    Returns:
        Cumulative threat score for the agent.

    Examples:
        >>> round(calculate_threat_score([(0.4, 0.8, 1.0, 1.0)]), 6)
        0.32
    """
    total = 0.0
    for heat, visibility, role_weight, legal_mult in memberships:
        total += heat * visibility * role_weight * legal_mult
    return total


def calculate_infrastructure_decay(
    current: float,
    decay_alpha: float,
    core_organizer_count: int,
    maintenance_factor: float = 0.1,
) -> float:
    """Compute new infrastructure after one tick of decay.

    Infrastructure decays toward zero without maintenance. CORE_ORGANIZER
    members counteract decay proportionally.

    Formula: new = current * (1 - alpha) + maintenance * alpha
    where maintenance = min(core_organizer_count * maintenance_factor, 1.0)

    Args:
        current: Current infrastructure level [0, 1].
        decay_alpha: Decay rate per tick [0, 1].
        core_organizer_count: Number of CORE_ORGANIZER members remaining.
        maintenance_factor: Infrastructure contribution per CORE_ORGANIZER.

    Returns:
        New infrastructure level after decay and maintenance, clamped to [0, 1].

    Examples:
        >>> round(calculate_infrastructure_decay(0.5, 0.04, 0), 4)
        0.48
        >>> round(calculate_infrastructure_decay(0.5, 0.04, 2, 0.1), 4)
        0.488
    """
    maintenance = min(core_organizer_count * maintenance_factor, 1.0)
    new_value = current * (1.0 - decay_alpha) + maintenance * decay_alpha
    return max(0.0, min(1.0, new_value))


def calculate_solidarity_amplification(
    base_strength: float,
    shared_communities: list[tuple[float, float, float, float]],
) -> float:
    """Amplify solidarity_strength based on shared community infrastructure.

    For each shared community, the amplification is scaled by the community's
    infrastructure, cohesion, and both agents' membership strengths.

    Formula: amplified = base * (1 + sum(infra * cohesion * str_a * str_b))

    Args:
        base_strength: Base solidarity_strength on the SOLIDARITY edge.
        shared_communities: List of (infrastructure, cohesion, strength_a,
            strength_b) tuples, one per shared community.

    Returns:
        Amplified solidarity strength.

    Examples:
        >>> calculate_solidarity_amplification(0.5, [])
        0.5
        >>> round(calculate_solidarity_amplification(0.5, [(0.8, 0.6, 0.7, 0.4)]), 6)
        0.5672
    """
    if not shared_communities:
        return base_strength
    amplification = sum(
        infra * cohesion * str_a * str_b for infra, cohesion, str_a, str_b in shared_communities
    )
    return base_strength * (1.0 + amplification)


def compute_community_cost_modifier(
    memberships: list[Any],
    community_states: dict[Any, Any],
) -> float:
    """Compute compound reproduction cost modifier from community memberships.

    The modifier is the product of reproduction_cost_modifier across all
    communities the agent belongs to. No memberships → 1.0 (no effect).

    Args:
        memberships: Agent's community memberships.
        community_states: Dict mapping CommunityType to CommunityState.

    Returns:
        Multiplicative compound modifier (product of all community modifiers).

    Examples:
        >>> compute_community_cost_modifier([], {})
        1.0
    """
    if not memberships:
        return 1.0
    modifier = 1.0
    for mem in memberships:
        comm_type = (
            mem.community_type if hasattr(mem, "community_type") else mem.get("community_type")
        )
        state = community_states.get(comm_type)
        if state is not None:
            modifier *= state.reproduction_cost_modifier
    return modifier
