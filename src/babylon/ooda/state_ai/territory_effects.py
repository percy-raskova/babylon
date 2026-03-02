"""Territory effects for state apparatus verbs (Feature 039 Phase 6).

Implements INVEST, NEGLECT, DISPLACE, STRATEGIC_WITHDRAWAL, SCORCHED_EARTH
territory mutations and PROPAGANDIZE consciousness effects.

Each function operates on a simple dict representing territory state,
keeping territory_effects pure and testable without graph dependency.
Functions take territory data and return new territory data (no mutation).

See Also:
    ``specs/039-state-apparatus-ai/contracts/territory-effects.md``: TE-01 through TE-07.
    :class:`babylon.config.defines.StateApparatusAIDefines`: All thresholds.
    :mod:`babylon.ooda.state_ai.faction_dynamics`: Similar pure-function pattern.
"""

from __future__ import annotations

import math
from typing import Any

from babylon.config.defines import StateApparatusAIDefines

# -------------------------------------------------------------------------
# TE-01: INVEST increases property_value_proxy and rent_level
# -------------------------------------------------------------------------


def resolve_invest(
    territory: dict[str, Any],
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """INVEST: Increase property_value_proxy and rent_level.

    TE-01: property_value_proxy += develop_infrastructure_boost.
    rent_level increases proportionally to the property value change.
    INVEST never decreases economic value (monotonically non-decreasing).

    Args:
        territory: Dict of territory node attributes.
        defines: State AI configuration with ``develop_infrastructure_boost``.

    Returns:
        New territory dict with updated property_value_proxy and rent_level.
    """
    result = dict(territory)
    delta = defines.develop_infrastructure_boost

    old_pvp: float = result.get("property_value_proxy", 0.0)
    new_pvp = old_pvp + delta
    result["property_value_proxy"] = new_pvp

    # rent_level increases proportionally to property value change
    old_rent: float = result.get("rent_level", 0.0)
    # Scale rent increase by the relative property value change
    rent_delta = old_rent * (delta / old_pvp) if old_pvp > 0 else delta * 0.1
    result["rent_level"] = old_rent + rent_delta

    return result


# -------------------------------------------------------------------------
# TE-02: NEGLECT degrades infrastructure with exponential decay and floor
# -------------------------------------------------------------------------


def resolve_neglect(
    territory: dict[str, Any],
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """NEGLECT: Exponential infrastructure_quality decay with floor.

    TE-02: quality *= (1.0 - neglect_infrastructure_decay).
    quality = max(quality, neglect_quality_floor).

    Args:
        territory: Dict of territory node attributes.
        defines: State AI configuration with ``neglect_infrastructure_decay``
            and ``neglect_quality_floor``.

    Returns:
        New territory dict with decayed infrastructure_quality.
    """
    result = dict(territory)

    old_quality: float = result.get("infrastructure_quality", 1.0)
    decayed = old_quality * (1.0 - defines.neglect_infrastructure_decay)
    result["infrastructure_quality"] = max(decayed, defines.neglect_quality_floor)

    return result


# -------------------------------------------------------------------------
# TE-03: DISPLACE removes population fraction and reduces community metrics
# -------------------------------------------------------------------------


def resolve_displace(
    territory: dict[str, Any],
    defines: StateApparatusAIDefines,
) -> tuple[dict[str, Any], int]:
    """DISPLACE: Remove population fraction, reduce community metrics.

    TE-03: displaced = floor(population * displace_population_fraction).
    Reduces collective_identity and community_infrastructure_quality.

    Args:
        territory: Dict of territory node attributes.
        defines: State AI configuration with ``displace_population_fraction``,
            ``displace_ci_reduction``, and ``displace_community_infra_reduction``.

    Returns:
        Tuple of (updated_territory, displaced_count).
    """
    result = dict(territory)

    population: int = result.get("population", 0)
    displaced_count = math.floor(population * defines.displace_population_fraction)
    result["population"] = population - displaced_count

    # Reduce collective_identity (consciousness disruption)
    old_ci: float = result.get("collective_identity", 0.0)
    new_ci = max(0.0, old_ci - defines.displace_ci_reduction)
    result["collective_identity"] = new_ci

    # Reduce community infrastructure quality
    old_ciq: float = result.get("community_infrastructure_quality", 0.0)
    new_ciq = max(0.0, old_ciq - defines.displace_community_infra_reduction)
    result["community_infrastructure_quality"] = new_ciq

    return result, displaced_count


# -------------------------------------------------------------------------
# TE-04: STRATEGIC_WITHDRAWAL removes state investment, accelerates decay
# -------------------------------------------------------------------------


def resolve_strategic_withdrawal(
    territory: dict[str, Any],
    defines: StateApparatusAIDefines,
    asset_extraction: bool = False,
) -> tuple[dict[str, Any], float]:
    """STRATEGIC_WITHDRAWAL: Remove state investment, accelerate decay.

    TE-04: state_investment=0, accelerated infrastructure degradation.
    When asset_extraction=True, recovers a fraction of prior investment.

    Args:
        territory: Dict of territory node attributes.
        defines: State AI configuration with ``strategic_withdrawal_decay_multiplier``,
            ``neglect_infrastructure_decay``, ``neglect_quality_floor``,
            and ``strategic_withdrawal_asset_recovery``.
        asset_extraction: If True, recover budget from prior investment.

    Returns:
        Tuple of (updated_territory, budget_recovered).
    """
    result = dict(territory)

    # Recover budget from state investment if extracting assets
    old_investment: float = result.get("state_investment", 0.0)
    budget_recovered = 0.0
    if asset_extraction:
        budget_recovered = old_investment * defines.strategic_withdrawal_asset_recovery

    # Zero out state investment
    result["state_investment"] = 0.0

    # Accelerated infrastructure decay (multiplied neglect)
    old_quality: float = result.get("infrastructure_quality", 1.0)
    accelerated_decay_rate = (
        defines.neglect_infrastructure_decay * defines.strategic_withdrawal_decay_multiplier
    )
    # Clamp decay rate to [0, 1] to prevent negative quality
    clamped_decay_rate = min(1.0, accelerated_decay_rate)
    decayed = old_quality * (1.0 - clamped_decay_rate)
    result["infrastructure_quality"] = max(decayed, defines.neglect_quality_floor)

    return result, budget_recovered


# -------------------------------------------------------------------------
# TE-05: SCORCHED_EARTH destroys infrastructure immediately
# -------------------------------------------------------------------------


def resolve_scorched_earth(
    territory: dict[str, Any],
    defines: StateApparatusAIDefines,
) -> tuple[dict[str, Any], float]:
    """SCORCHED_EARTH: Immediate infrastructure destruction.

    TE-05: infrastructure_quality -> neglect_quality_floor.
    Legitimacy cost scales by territory visibility (CORE vs PERIPHERY).

    Args:
        territory: Dict of territory node attributes.
        defines: State AI configuration with ``neglect_quality_floor``,
            ``scorched_earth_legitimacy_core``, and
            ``scorched_earth_legitimacy_periphery``.

    Returns:
        Tuple of (updated_territory, legitimacy_cost).
    """
    result = dict(territory)

    # Destroy infrastructure to floor
    result["infrastructure_quality"] = defines.neglect_quality_floor

    # Destroy community infrastructure
    result["community_infrastructure_quality"] = 0.0

    # Zero state investment (same as strategic withdrawal)
    result["state_investment"] = 0.0

    # Compute legitimacy cost based on territory type
    territory_type: str = result.get("territory_type", "PERIPHERY")
    legitimacy_cost = compute_scorched_earth_legitimacy(territory_type, defines)

    return result, legitimacy_cost


# -------------------------------------------------------------------------
# TE-06: PRESENCE edge operational profile drives heat accumulation
# -------------------------------------------------------------------------


def compute_heat_accumulation(
    current_heat: float,
    high_profile_count: int,
    low_profile_count: int,
    defines: StateApparatusAIDefines,
) -> float:
    """Compute heat from PRESENCE edges by operational profile.

    TE-06: heat += high_profile_count * high_profile_heat_rate
                 + low_profile_count * low_profile_heat_rate.
    Bounded to [0.0, 1.0].

    Args:
        current_heat: Current heat level on the territory.
        high_profile_count: Number of HIGH_PROFILE PRESENCE edges.
        low_profile_count: Number of LOW_PROFILE PRESENCE edges.
        defines: State AI configuration with ``high_profile_heat_rate``
            and ``low_profile_heat_rate``.

    Returns:
        Updated heat value, bounded to [0.0, 1.0].
    """
    heat_delta = (
        high_profile_count * defines.high_profile_heat_rate
        + low_profile_count * defines.low_profile_heat_rate
    )
    new_heat = current_heat + heat_delta
    return max(0.0, min(1.0, new_heat))


# -------------------------------------------------------------------------
# TE-07: PROPAGANDIZE consciousness resistance
# -------------------------------------------------------------------------


def compute_propagandize_effect(
    collective_identity: float,
    base_delta: float,
    defines: StateApparatusAIDefines,
) -> float:
    """PROPAGANDIZE effect modulated by consciousness.

    TE-07: effective_delta = base_delta * (1 - CI * consciousness_resistance_factor).
    High-CI territories resist better.

    The returned value is the effective reduction in collective_identity,
    bounded so that CI does not go below 0.0.

    Args:
        collective_identity: Current collective_identity in [0.0, 1.0].
        base_delta: Base CI reduction attempted by PROPAGANDIZE (positive value).
        defines: State AI configuration with ``consciousness_resistance_factor``.

    Returns:
        Effective CI reduction (positive value), bounded so CI >= 0.0 after application.
    """
    resistance = collective_identity * defines.consciousness_resistance_factor
    effective_delta = base_delta * (1.0 - resistance)

    # Floor: propagandize cannot increase CI, and cannot reduce below 0
    effective_delta = max(0.0, effective_delta)
    effective_delta = min(effective_delta, collective_identity)

    return effective_delta


# -------------------------------------------------------------------------
# Legitimacy cost for SCORCHED_EARTH
# -------------------------------------------------------------------------


def compute_scorched_earth_legitimacy(
    territory_type: str,
    defines: StateApparatusAIDefines,
) -> float:
    """Compute legitimacy cost for SCORCHED_EARTH based on visibility.

    CORE = extreme cost (high media presence).
    PERIPHERY = minimal cost (low international visibility).

    Args:
        territory_type: Territory classification ("CORE" or "PERIPHERY").
        defines: State AI configuration with ``scorched_earth_legitimacy_core``
            and ``scorched_earth_legitimacy_periphery``.

    Returns:
        Legitimacy cost (positive value, higher = more costly to state).
    """
    if territory_type == "CORE":
        return defines.scorched_earth_legitimacy_core
    return defines.scorched_earth_legitimacy_periphery


# -------------------------------------------------------------------------
# Heat decay (T066)
# -------------------------------------------------------------------------


def compute_heat_decay(
    current_heat: float,
    has_presence: bool,
    defines: StateApparatusAIDefines,
) -> float:
    """Decay heat when no PRESENCE edges remain.

    When an organization loses all PRESENCE edges in a territory,
    heat decays by heat_decay_rate per tick. If PRESENCE exists,
    no decay occurs (heat is driven by accumulation instead).

    Args:
        current_heat: Current heat level on the territory [0.0, 1.0].
        has_presence: Whether any PRESENCE edges exist in this territory.
        defines: State AI configuration with ``heat_decay_rate``.

    Returns:
        Updated heat value, bounded to [0.0, 1.0].
    """
    if has_presence:
        return current_heat
    new_heat = current_heat - defines.heat_decay_rate
    return max(0.0, min(1.0, new_heat))


# -------------------------------------------------------------------------
# Territorial PRESENCE requirement for RECRUIT (T067)
# -------------------------------------------------------------------------


def check_recruit_effectiveness(
    has_presence: bool,
    base_effectiveness: float,
    defines: StateApparatusAIDefines,
) -> float:
    """Compute recruitment effectiveness based on territorial PRESENCE.

    Organizations without PRESENCE in a territory have severely
    reduced recruitment effectiveness (recruit_no_presence_penalty).

    Args:
        has_presence: Whether the recruiting org has PRESENCE in the territory.
        base_effectiveness: Base recruitment effectiveness [0.0, 1.0].
        defines: State AI configuration with ``recruit_no_presence_penalty``.

    Returns:
        Effective recruitment rate, penalized if no PRESENCE.
    """
    if has_presence:
        return base_effectiveness
    penalty = defines.recruit_no_presence_penalty
    return base_effectiveness * (1.0 - penalty)


# -------------------------------------------------------------------------
# Consciousness geography — territory threat assessment (T068)
# -------------------------------------------------------------------------


def assess_territory_threat(
    territory_ci: float,
    territory_heat: float,
    defines: StateApparatusAIDefines,
) -> float:
    """Assess state threat level for a specific territory.

    Threat = weighted combination of local collective_identity and heat.
    Territories with high CI AND high heat are priority targets for
    state intervention. This enables consciousness geography --- the state
    sees threat at territory granularity, not org-level.

    Args:
        territory_ci: Local collective_identity [0.0, 1.0].
        territory_heat: Current heat level [0.0, 1.0].
        defines: State AI configuration with ``heat_escalation_threshold``.

    Returns:
        Threat score in [0.0, 1.0]. Higher = more threatening to state.
    """
    # Weight CI and heat equally, with bonus for heat above threshold
    ci_component = territory_ci * 0.5
    heat_component = territory_heat * 0.5

    # Bonus threat for heat exceeding escalation threshold
    if territory_heat > defines.heat_escalation_threshold:
        overshoot = territory_heat - defines.heat_escalation_threshold
        heat_component += overshoot * 0.3

    return max(0.0, min(1.0, ci_component + heat_component))


# -------------------------------------------------------------------------
# Eviction cascade — DISPLACE scatter effects (T069)
# -------------------------------------------------------------------------


def resolve_eviction_cascade(
    source_territory: dict[str, Any],
    neighbor_territories: list[dict[str, Any]],
    displaced_count: int,
    defines: StateApparatusAIDefines,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Resolve eviction cascade from DISPLACE action.

    Scattered population is distributed across neighboring territories.
    Each receiving territory gains population but loses collective_identity
    (organized community is scattered, diluting consciousness).
    Community infrastructure in the source territory is severed.

    Args:
        source_territory: Dict of territory that was displaced.
        neighbor_territories: List of neighboring territory dicts.
        displaced_count: Number of people displaced (from resolve_displace).
        defines: State AI configuration with ``eviction_scatter_ci_loss``.

    Returns:
        Tuple of (updated_source, list_of_updated_neighbors).
    """
    updated_source = dict(source_territory)

    # Sever community infrastructure in source (TENANCY edges broken)
    old_ciq: float = updated_source.get("community_infrastructure_quality", 0.0)
    updated_source["community_infrastructure_quality"] = max(
        0.0, old_ciq - defines.displace_community_infra_reduction
    )

    if not neighbor_territories or displaced_count <= 0:
        return updated_source, []

    # Distribute displaced population evenly across neighbors
    per_neighbor = displaced_count // len(neighbor_territories)
    remainder = displaced_count % len(neighbor_territories)

    updated_neighbors: list[dict[str, Any]] = []
    max_neighbors = len(neighbor_territories)
    for idx in range(max_neighbors):
        neighbor = dict(neighbor_territories[idx])
        # Allocate population (first neighbor gets remainder)
        allocation = per_neighbor + (1 if idx < remainder else 0)
        old_pop: int = neighbor.get("population", 0)
        neighbor["population"] = old_pop + allocation

        # CI dilution: scattered arrivals reduce local consciousness
        old_ci: float = neighbor.get("collective_identity", 0.0)
        new_ci = max(0.0, old_ci - defines.eviction_scatter_ci_loss)
        neighbor["collective_identity"] = new_ci

        updated_neighbors.append(neighbor)

    return updated_source, updated_neighbors


__all__ = [
    "assess_territory_threat",
    "check_recruit_effectiveness",
    "compute_heat_accumulation",
    "compute_heat_decay",
    "compute_propagandize_effect",
    "compute_scorched_earth_legitimacy",
    "resolve_displace",
    "resolve_eviction_cascade",
    "resolve_invest",
    "resolve_neglect",
    "resolve_scorched_earth",
    "resolve_strategic_withdrawal",
]
