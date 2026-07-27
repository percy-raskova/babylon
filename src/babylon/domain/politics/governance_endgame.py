"""The governance endgame — the SYRIZA fork and the Allende limit (P25 U12, ADR139).

Pure standing math for the-electoral-question.md §3.5: first ceiling contact
in office (the veto gauntlet fires against a governing party's agenda) opens
a fork whose arm and geometry are deterministic functions of quantities the
engine already measures. Nothing here adjudicates an outcome — the endgame
detector only recognizes patterns (I.11); these functions name trajectories.

Aleksandrov traces (III.8):

- :func:`resolve_governance_arm` — a governing party without organs of dual
  power administers the veto (SYRIZA 2015: no organs, capitulation was the
  standing math); a party captured by its own office administers it too
  (Michels — the ``institutional_pull`` accumulator, U11 E2). Rupture is
  reachable only where organs exist AND the party is still its base's.
- :func:`rupture_geometry` — on the rupture arm, the synthesis window
  ("office and organs compound", the united-front thesis earned in physics)
  requires SOLIDARITY bridges and a Φ-starved state; anything less is the
  Allende geometry (Chile 1973: organs partial, the state's rent circuits
  and RSA intact).
- :func:`phi_share` — the rent cushion as a share of measured surplus; one
  measure serving both the Φ-starved-state predicate here and the periphery
  mirror (§4: in low-Φ sovereigns the ceiling arrives immediately).
- :func:`dual_power_live` — the same structural predicate SovereigntySystem
  @17.5 emits ``DUAL_POWER_ACTIVE`` for (>= 2 active claimants on one
  territory), read live over claim rows rather than replayed from event
  history: organs either stand on the terrain at rupture time or they don't.
- :func:`betrayal_crossed` — ``b(c) = Σ gap`` against ``betrayal_threshold``
  (the SYRIZA-voter curve): patience is an integral, not a per-cycle reset.

Determinism (III.7): pure functions of their arguments; no RNG, no clock.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping


class GovernanceArm(StrEnum):
    """The fork's two arms (§3.5) — both are standing math, neither is a verb."""

    CAPITULATE = "capitulate"
    RUPTURE = "rupture"


class RuptureGeometry(StrEnum):
    """What the rupture arm meets: the coup geometry or the synthesis window."""

    ALLENDE = "allende"
    SYNTHESIS = "synthesis"


def phi_share(phi_inflow: float, total_surplus: float) -> float:
    """Φ-inflow as a share of measured surplus.

    :param phi_inflow: the sovereign's imperial-rent inflow over its claimed
        territories (the ``FiscalTerrain`` sum).
    :param total_surplus: total measured surplus over the same set.
    :returns: the plain ratio; ``0.0`` when no surplus is measured — a
        sovereign with no measured surplus has no rent cushion (honest
        absence, III.11), never a fabricated ratio.
    """
    return phi_inflow / total_surplus if total_surplus > 0.0 else 0.0


def betrayal_crossed(integral: float, threshold: float) -> bool:
    """Whether the accumulated delivery-gap integral has crossed the threshold.

    :param integral: ``b(c) = Σ gap`` (the ``policy_delivery`` row's
        ``integral`` field, accumulated by PolicySystem since U9).
    :param threshold: ``politics.betrayal_threshold``; a non-positive value
        disables the curve (a mod switch, never an always-fire).
    """
    return threshold > 0.0 and integral >= threshold


def dual_power_live(
    claims_by_territory: Mapping[str, tuple[tuple[str, float], ...]],
) -> bool:
    """Whether organs of dual power stand anywhere on the given terrain.

    The same structural predicate SovereigntySystem @17.5 emits
    ``DUAL_POWER_ACTIVE`` for: at least two claimants with positive control
    on a single territory.

    :param claims_by_territory: territory id → claim rows
        ``(sovereign_id, control)`` — the caller scopes the mapping (the
        fork reads the governing sovereign's claimed set).
    """
    return any(
        sum(1 for _, control in rows if control > 0.0) >= 2 for rows in claims_by_territory.values()
    )


def resolve_governance_arm(
    *,
    institutional_pull: float,
    capture_threshold: float,
    organs_live: bool,
) -> GovernanceArm:
    """Which arm a governing party takes at first ceiling contact.

    Rupture requires BOTH the organs (``organs_live`` — dual power standing
    on the party's terrain) and an uncaptured party
    (``institutional_pull`` strictly below ``capture_threshold``; at the
    threshold the Michels drift has done its work). Everything else
    administers the veto — including the organ-less honest reformer, which
    is the SYRIZA case, not a special one.
    """
    if organs_live and institutional_pull < capture_threshold:
        return GovernanceArm.RUPTURE
    return GovernanceArm.CAPITULATE


def rupture_geometry(*, bridges_present: bool, phi_starved: bool) -> RuptureGeometry:
    """What the rupture arm meets (organs already live by construction).

    The synthesis window — office and organs compounding — opens only with
    SOLIDARITY bridges AND a Φ-starved state; a state still fed by imperial
    rent can afford its own repression, and a base without bridges cannot
    hold what the office defies (both roads end in the Allende geometry).
    """
    if bridges_present and phi_starved:
        return RuptureGeometry.SYNTHESIS
    return RuptureGeometry.ALLENDE


__all__ = [
    "GovernanceArm",
    "RuptureGeometry",
    "betrayal_crossed",
    "dual_power_live",
    "phi_share",
    "resolve_governance_arm",
    "rupture_geometry",
]
