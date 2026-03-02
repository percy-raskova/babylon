"""REPRESS verb resolution: INFILTRATE, RAID, PROSECUTE, LIQUIDATE (Feature 039 Phase 10D).

Pure functions that resolve REPRESS sub-verb effects on target organizations,
territories, and key figures. Implements the COINTELPRO double bind (RAID
radicalizes high-CI communities) and escalation from intelligence gathering
through prosecution to liquidation.

All functions follow the same pattern as :mod:`territory_effects`: take dicts
and a :class:`~babylon.config.defines.StateApparatusAIDefines`, return new
dicts without mutating inputs.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B06.
    :mod:`babylon.ooda.state_ai.territory_effects`: Analogous pattern.
"""

from __future__ import annotations

import random
from typing import Any

from babylon.config.defines import StateApparatusAIDefines

_VALID_AGENT_TYPES = frozenset({"INFORMANT", "PROVOCATEUR", "MOLE"})

_VALID_FORCE_LEVELS = frozenset({"POLICE", "SWAT", "MILITARY"})

_VALID_RAID_SCALES = frozenset({"TARGETED", "SWEEP", "MASS"})

_VALID_CHARGES = frozenset(
    {
        "CONSPIRACY",
        "RACKETEERING",
        "TAX",
        "CIVIL_RIGHTS_VIOLATION",
        "TERRORISM",
    }
)

_VALID_LIQUIDATE_METHODS = frozenset(
    {
        "ASSASSINATION",
        "DISAPPEARANCE",
        "RENDITION",
        "PRISON_KILLING",
    }
)

_RAID_SCALE_LEGITIMACY_MULTIPLIER: dict[str, float] = {
    "TARGETED": 1.0,
    "SWEEP": 1.5,
    "MASS": 2.5,
}

_RAID_MASS_INFRA_DAMAGE: float = 0.1


# ---------------------------------------------------------------------------
# INFILTRATE (T096)
# ---------------------------------------------------------------------------


def resolve_infiltrate(
    target_org: dict[str, Any],
    thread: dict[str, Any],
    agent_type: str,
    defines: StateApparatusAIDefines,
    rng_seed: int,
    current_tick: int = 0,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Create an infiltration of a target organization.

    Args:
        target_org: Target organization dict.
        thread: Attention thread dict with ``intel_completeness``.
        agent_type: One of ``"INFORMANT"``, ``"PROVOCATEUR"``, ``"MOLE"``.
        defines: Game defines for intel rates and detection.
        rng_seed: Seed for deterministic detection roll.
        current_tick: Current simulation tick for record timestamps.

    Returns:
        Tuple of (updated thread dict, infiltration record, detected).

    Raises:
        ValueError: If *agent_type* is not recognized.
    """
    if agent_type not in _VALID_AGENT_TYPES:
        msg = f"Invalid agent_type {agent_type!r}; expected one of {sorted(_VALID_AGENT_TYPES)}"
        raise ValueError(msg)

    intel_rates: dict[str, float] = {
        "INFORMANT": defines.infiltrate_informant_intel_rate,
        "PROVOCATEUR": defines.infiltrate_provocateur_intel_rate,
        "MOLE": defines.infiltrate_mole_intel_rate,
    }

    result_thread = dict(thread)
    intel: float = result_thread.get("intel_completeness", 0.0)
    intel = min(1.0, intel + intel_rates[agent_type])
    result_thread["intel_completeness"] = intel

    # Detection roll — PROVOCATEUR has 1.5x detection chance
    detection_chance = defines.infiltrate_detection_base_chance
    if agent_type == "PROVOCATEUR":
        detection_chance = min(1.0, detection_chance * 1.5)

    rng = random.Random(rng_seed)
    detected = rng.random() < detection_chance

    record: dict[str, Any] = {
        "agent_type": agent_type,
        "target_org_id": target_org.get("id", "unknown"),
        "created_tick": current_tick,
        "detected": detected,
    }

    return result_thread, record, detected


# ---------------------------------------------------------------------------
# RAID (T097)
# ---------------------------------------------------------------------------


def compute_raid_consciousness_effect(
    ci: float,
    defines: StateApparatusAIDefines,
) -> float:
    """Compute consciousness delta from RAID action (COINTELPRO double bind).

    High-CI territories radicalize further when raided; low-CI territories
    are suppressed. This creates a strategic dilemma for the state.

    Args:
        ci: Current collective identity of the territory.
        defines: Game defines for thresholds and rates.

    Returns:
        CI delta (positive = radicalization, negative = suppression).
    """
    if ci >= defines.raid_ci_radicalization_threshold:
        return defines.raid_ci_radicalization_boost
    return -defines.raid_ci_suppression_rate


def resolve_raid(
    target_org: dict[str, Any],
    territory: dict[str, Any],
    scale: str,
    force_level: str,
    thread_intel: float,
    key_figure_ids: list[str],
    defines: StateApparatusAIDefines,
    rng_seed: int,
) -> tuple[dict[str, Any], dict[str, Any], list[str], float]:
    """Execute a RAID against a target organization.

    Args:
        target_org: Target organization dict with ``coherence``.
        territory: Territory dict with ``collective_identity``,
            ``community_infrastructure_quality``.
        scale: One of ``"TARGETED"``, ``"SWEEP"``, ``"MASS"``.
        force_level: One of ``"POLICE"``, ``"SWAT"``, ``"MILITARY"``.
        thread_intel: Intel completeness from the thread [0.0, 1.0].
        key_figure_ids: IDs of known key figures in the org.
        defines: Game defines for damage rates and multipliers.
        rng_seed: Seed for deterministic capture rolls.

    Returns:
        Tuple of (updated org dict, updated territory dict,
        captured figure IDs, legitimacy cost).

    Raises:
        ValueError: If *scale* or *force_level* is not recognized.
    """
    if scale not in _VALID_RAID_SCALES:
        msg = f"Invalid raid scale {scale!r}; expected one of {sorted(_VALID_RAID_SCALES)}"
        raise ValueError(msg)
    if force_level not in _VALID_FORCE_LEVELS:
        msg = f"Invalid force_level {force_level!r}; expected one of {sorted(_VALID_FORCE_LEVELS)}"
        raise ValueError(msg)

    # Force multiplier
    force_multiplier = 1.0
    if force_level == "SWAT":
        force_multiplier = defines.raid_force_multiplier_swat
    elif force_level == "MILITARY":
        force_multiplier = defines.raid_force_multiplier_military

    result_org = dict(target_org)
    result_territory = dict(territory)

    # Coherence damage
    coherence: float = result_org.get("coherence", 1.0)
    damage = defines.raid_org_coherence_damage * force_multiplier
    result_org["coherence"] = max(0.0, coherence - damage)

    # Key figure capture
    captured: list[str] = []
    rng = random.Random(rng_seed)
    capture_prob = defines.raid_key_figure_capture_base * force_multiplier * thread_intel
    capture_prob = min(1.0, capture_prob)

    max_figures = len(key_figure_ids)
    for i in range(max_figures):
        if rng.random() < capture_prob:
            captured.append(key_figure_ids[i])

    # Consciousness dialectic (COINTELPRO double bind)
    ci: float = result_territory.get("collective_identity", 0.0)
    ci_delta = compute_raid_consciousness_effect(ci, defines)
    result_territory["collective_identity"] = max(0.0, min(1.0, ci + ci_delta))

    # Legitimacy cost
    base_legitimacy = 0.05  # From _LEGITIMACY_COSTS[RAID]
    scale_mult = _RAID_SCALE_LEGITIMACY_MULTIPLIER[scale]
    legitimacy_cost = base_legitimacy * scale_mult

    # MASS raids damage community infrastructure
    if scale == "MASS":
        infra: float = result_territory.get("community_infrastructure_quality", 0.0)
        result_territory["community_infrastructure_quality"] = max(
            0.0, infra - _RAID_MASS_INFRA_DAMAGE
        )

    return result_org, result_territory, captured, legitimacy_cost


# ---------------------------------------------------------------------------
# PROSECUTE (T098)
# ---------------------------------------------------------------------------


def resolve_prosecute(
    target_org: dict[str, Any],
    target_key_figure_id: str | None,
    charge: str,
    defines: StateApparatusAIDefines,
    rng_seed: int,
    current_tick: int = 0,
) -> tuple[dict[str, Any], dict[str, Any], float]:
    """Execute prosecution against a target organization or key figure.

    Args:
        target_org: Target organization dict with ``coherence``.
        target_key_figure_id: ID of targeted key figure, or None.
        charge: One of ``"CONSPIRACY"``, ``"RACKETEERING"``, ``"TAX"``,
            ``"CIVIL_RIGHTS_VIOLATION"``, ``"TERRORISM"``.
        defines: Game defines for morale damage and removal chances.
        rng_seed: Seed for deterministic conviction roll.
        current_tick: Current tick for record timestamps.

    Returns:
        Tuple of (updated org dict, prosecution record, legitimacy delta).

    Raises:
        ValueError: If *charge* is not recognized.
    """
    if charge not in _VALID_CHARGES:
        msg = f"Invalid charge {charge!r}; expected one of {sorted(_VALID_CHARGES)}"
        raise ValueError(msg)

    result_org = dict(target_org)

    # Terrorism multiplier
    multiplier = 1.0
    if charge == "TERRORISM":
        multiplier = defines.prosecute_terrorism_charge_multiplier

    # Morale / coherence damage
    coherence: float = result_org.get("coherence", 1.0)
    morale_damage = defines.prosecute_org_morale_damage * multiplier
    result_org["coherence"] = max(0.0, coherence - morale_damage)

    # Conviction roll
    rng = random.Random(rng_seed)
    removal_chance = defines.prosecute_key_figure_removal_chance * multiplier
    removal_chance = min(1.0, removal_chance)
    convicted = rng.random() < removal_chance

    # Figure removal (only if convicted AND figure targeted)
    figure_removed = convicted and target_key_figure_id is not None

    # Legitimacy delta
    if convicted:
        legitimacy_delta = defines.prosecute_legitimacy_boost_success
    else:
        legitimacy_delta = -defines.prosecute_legitimacy_boost_success

    record: dict[str, Any] = {
        "target_org_id": result_org.get("id", "unknown"),
        "figure_id": target_key_figure_id,
        "charge": charge,
        "convicted": convicted,
        "figure_removed": figure_removed,
        "created_tick": current_tick,
    }

    return result_org, record, legitimacy_delta


# ---------------------------------------------------------------------------
# LIQUIDATE (T099)
# ---------------------------------------------------------------------------


def resolve_liquidate(
    target_org: dict[str, Any],
    target_key_figure_id: str,
    method: str,
    deniability: float,
    territory_type: str,
    liquidate_available_in_core: bool,
    is_singleton: bool,
    defines: StateApparatusAIDefines,
) -> tuple[dict[str, Any], float, bool]:
    """Execute liquidation of a key figure.

    Args:
        target_org: Target organization dict with ``coherence``.
        target_key_figure_id: ID of the key figure to liquidate.
        method: One of ``"ASSASSINATION"``, ``"DISAPPEARANCE"``,
            ``"RENDITION"``, ``"PRISON_KILLING"``.
        deniability: Current deniability level [0.0, 1.0].
        territory_type: ``"CORE"`` or ``"PERIPHERY"``.
        liquidate_available_in_core: Whether EMERGENCY_POWERS enables
            LIQUIDATE in core territories.
        is_singleton: Whether the figure is the org's sole leader.
        defines: Game defines for legitimacy costs and collapse chances.

    Returns:
        Tuple of (updated org dict, legitimacy cost, org collapsed).

    Raises:
        ValueError: If LIQUIDATE in core without EMERGENCY_POWERS, or
            if *method* is not recognized.
    """
    if method not in _VALID_LIQUIDATE_METHODS:
        msg = f"Invalid method {method!r}; expected one of {sorted(_VALID_LIQUIDATE_METHODS)}"
        raise ValueError(msg)

    if territory_type == "CORE" and not liquidate_available_in_core:
        msg = "LIQUIDATE in core territory requires EMERGENCY_POWERS legislation"
        raise ValueError(msg)

    result_org = dict(target_org)

    # Key figure always removed
    existing_figures: list[str] = list(result_org.get("key_figure_ids", []))
    if target_key_figure_id in existing_figures:
        existing_figures.remove(target_key_figure_id)
        result_org["key_figure_ids"] = existing_figures

    # Coherence damage (leadership crisis)
    coherence: float = result_org.get("coherence", 1.0)
    result_org["coherence"] = max(0.0, coherence - defines.liquidate_coherence_damage)

    # Legitimacy cost
    if territory_type == "CORE":
        legitimacy_cost = defines.liquidate_core_legitimacy_cost
    else:
        legitimacy_cost = defines.liquidate_periphery_legitimacy_cost

    # High deniability halves legitimacy cost
    if deniability >= defines.liquidate_deniability_threshold:
        legitimacy_cost = legitimacy_cost / 2.0

    # Singleton collapse
    org_collapsed = is_singleton

    return result_org, legitimacy_cost, org_collapsed


__all__ = [
    "compute_raid_consciousness_effect",
    "resolve_infiltrate",
    "resolve_liquidate",
    "resolve_prosecute",
    "resolve_raid",
]
