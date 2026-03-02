"""Player observability layer for state apparatus AI (Feature 039, T084).

Surfaces state behavior through indirect signals rather than exposing
internal decision-making. Players observe:
- Verb selections as EventBus events with public-facing metadata
- Territory-level effects via graph attributes
- Deeper internals via COUNTER_INTEL action proportional to intel success

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-D11, FR-D12.
    :class:`babylon.ooda.state_ai.decision.RuleBasedStateAI`: Decision system.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.state_apparatus_ai import FactionBalance, StateAction

# -------------------------------------------------------------------------
# Public-facing action metadata (what players see)
# -------------------------------------------------------------------------


def create_observable_action(
    action: StateAction,
    territory_heat: float,
) -> dict[str, Any]:
    """Create public-facing metadata for a state action.

    Players see the WHAT (verb, territory, visible intensity) but not
    the WHY (faction scoring, budget trade-offs, thread intelligence).

    Args:
        action: The state action taken.
        territory_heat: Current heat in target territory [0.0, 1.0].

    Returns:
        Dict of publicly observable information.
    """
    return {
        "verb": str(action.verb),
        "sub_verb": str(action.sub_verb),
        "target_id": action.target_id,
        "visible_intensity": _compute_visible_intensity(action, territory_heat),
        "territory_heat": territory_heat,
    }


def create_territory_observables(
    territory: dict[str, Any],
) -> dict[str, Any]:
    """Extract publicly visible territory attributes.

    Players can observe territory-level effects (property values,
    infrastructure quality, heat) without seeing internal state AI
    decision scoring.

    Args:
        territory: Full territory dict with all attributes.

    Returns:
        Dict of publicly visible territory attributes only.
    """
    return {
        "property_value_proxy": territory.get("property_value_proxy", 0.0),
        "infrastructure_quality": territory.get("infrastructure_quality", 0.0),
        "heat": territory.get("heat", 0.0),
        "population": territory.get("population", 0),
        "collective_identity": territory.get("collective_identity", 0.0),
    }


# -------------------------------------------------------------------------
# COUNTER_INTEL — deeper observability proportional to intel success
# -------------------------------------------------------------------------


def resolve_counter_intel(
    intel_success: float,
    faction_balance: FactionBalance,
    last_actions: list[StateAction],
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """Reveal state internals proportional to COUNTER_INTEL success.

    Higher intel_success reveals more detailed information:
    - 0.0-0.3: Only verb types visible (already public)
    - 0.3-0.6: Faction balance weights revealed
    - 0.6-0.8: Budget allocations and thread targets revealed
    - 0.8-1.0: Full internal state (equivalent to God Mode)

    Args:
        intel_success: Intelligence success level [0.0, 1.0].
        faction_balance: Current faction balance.
        last_actions: Recent state actions.
        defines: State AI configuration.

    Returns:
        Dict of revealed state internals (depth varies by intel_success).
    """
    # defines reserved for configurable intel thresholds (future)
    _ = defines

    revealed: dict[str, Any] = {
        "intel_level": intel_success,
    }

    # Level 1: Basic (always visible)
    revealed["visible_actions"] = [
        {"verb": str(a.verb), "target_id": a.target_id} for a in last_actions
    ]

    # Level 2: Faction balance (intel >= 0.3)
    if intel_success >= 0.3:
        revealed["faction_balance"] = {
            "finance_capital": round(faction_balance.finance_capital, 2),
            "security_state": round(faction_balance.security_state, 2),
            "settler_populist": round(faction_balance.settler_populist, 2),
        }

    # Level 3: Action details (intel >= 0.6)
    if intel_success >= 0.6:
        revealed["action_details"] = [
            {
                "verb": str(a.verb),
                "sub_verb": str(a.sub_verb),
                "target_id": a.target_id,
                "budget_cost": a.budget_cost,
                "faction_alignment": str(a.faction_alignment),
            }
            for a in last_actions
        ]

    # Level 4: Full state (intel >= 0.8)
    if intel_success >= 0.8:
        revealed["full_state"] = {
            "dominant_faction": str(faction_balance.dominant_faction),
            "stability": faction_balance.stability,
            "legitimacy": faction_balance.legitimacy,
        }

    return revealed


# -------------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------------


def _compute_visible_intensity(
    action: StateAction,
    territory_heat: float,
) -> float:
    """Compute publicly visible intensity of a state action.

    Intensity combines budget cost magnitude with territory heat.
    Higher cost actions and hotter territories are more visible.

    Args:
        action: The state action.
        territory_heat: Current territory heat [0.0, 1.0].

    Returns:
        Visible intensity in [0.0, 1.0].
    """
    # Normalize budget cost to [0, 1] using a reasonable max
    budget_factor = min(1.0, action.budget_cost / 20.0) if action.budget_cost > 0 else 0.0
    heat_factor = territory_heat * 0.3
    return max(0.0, min(1.0, budget_factor * 0.7 + heat_factor))


__all__ = [
    "create_observable_action",
    "create_territory_observables",
    "resolve_counter_intel",
]
