"""Policy-space vocabulary for the ambient electoral machine (P25 U9, ADR135).

The six overlay axes of the-electoral-question.md §2.4: compact, typed,
runtime overlays in the Ledger — never ``defines.yaml`` mutations (defines
are Θ, the world's physics; policy is state, the world's politics). Each
axis names its overlay target and its material read-side; consumers arrive
with their owning units (``social_wage`` and ``border_regime`` read-sides
landed with U9, the rest are typed open wiring rows).
"""

from __future__ import annotations

from enum import StrEnum


class PolicyAxis(StrEnum):
    """The compact policy space LEGISLATE writes overlays into (§2.4).

    :cvar WAGE_FLOOR: clamps WAGES edge flow minima (read-side:
        Production/TickDynamics wage steps).
    :cvar SOCIAL_WAGE: transfer into class subsistence coverage (read-side:
        the survival calculus ``P(S|A)`` input — landed U9).
    :cvar LABOR_LAW: organizing cost/legality regime (read-side: mass-work
        verb efficiency, repression-targeting legality).
    :cvar POLICE_BUDGET: repression capacity per territory (read-side: the
        state AI's Repress ladder capacity).
    :cvar BORDER_REGIME: reserve-army inflow valve (read-side:
        ReserveArmySystem — landed U9).
    :cvar WAR_POSTURE: Φ maintenance spending (read-side: ImperialRent pool
        upkeep and ``t``-claim competition).
    """

    WAGE_FLOOR = "wage_floor"
    SOCIAL_WAGE = "social_wage"
    LABOR_LAW = "labor_law"
    POLICE_BUDGET = "police_budget"
    BORDER_REGIME = "border_regime"
    WAR_POSTURE = "war_posture"
