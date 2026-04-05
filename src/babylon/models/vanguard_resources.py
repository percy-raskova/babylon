"""Vanguard Economy resource model (Wayne County MVP).

The Vanguard Economy represents the player's organizational capacity through
three resource types that map to real organizer work:

- **Cadre Labor (CL)**: Hours available from committed members. Derived from
  ``cadre_level * budget``. Spent on high-skill actions (educate, investigate).

- **Sympathizer Labor (SL)**: Hours available from supporters and contacts.
  Derived from ``cohesion * territory_count``. Spent on mass actions (mobilize,
  campaign).

- **Reputation (REP)**: Social capital accumulated through successful actions.
  Grows from successful actions, decays from failures and heat. Unlocks
  advanced verbs and alliance possibilities.

Design Note
-----------
These resources are *derived* from the existing Organization model fields, not
stored separately. This avoids schema changes while making the economy legible
to the player. The ``VanguardResources`` model computes current values each tick.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from babylon.models.types import Currency, Probability


class VanguardResources(BaseModel):
    """Computed resource snapshot for a player organization.

    All fields are derived from Organization attributes at the current tick.
    This model is for display and action cost checking — it does not persist.

    Attributes:
        cadre_labor: Available cadre work hours [0, inf).
        sympathizer_labor: Available sympathizer work hours [0, inf).
        reputation: Social capital [0, 1].
        budget: Cash on hand (passed through from Organization).
        heat: State attention (passed through from Organization).
        max_cadre_labor: Maximum CL this tick.
        max_sympathizer_labor: Maximum SL this tick.
    """

    cadre_labor: Currency = Field(
        default=0.0,
        description="Available cadre work hours this tick",
    )
    sympathizer_labor: Currency = Field(
        default=0.0,
        description="Available sympathizer work hours this tick",
    )
    reputation: Probability = Field(
        default=0.0,
        description="Social capital / community trust [0, 1]",
    )
    budget: Currency = Field(
        default=0.0,
        description="Cash on hand",
    )
    heat: Probability = Field(
        default=0.0,
        description="State attention level [0, 1]",
    )
    max_cadre_labor: Currency = Field(
        default=0.0,
        description="Maximum cadre labor available this tick",
    )
    max_sympathizer_labor: Currency = Field(
        default=0.0,
        description="Maximum sympathizer labor available this tick",
    )

    @classmethod
    def from_organization(
        cls,
        *,
        cadre_level: float,
        cohesion: float,
        budget: float,
        heat: float,
        territory_count: int,
        reputation: float = 0.0,
    ) -> VanguardResources:
        """Compute vanguard resources from organization attributes.

        Formulas:
            CL_max = cadre_level * 10 * (1 - heat * 0.5)
            SL_max = cohesion * territory_count * 5 * (1 - heat * 0.3)
            CL = min(CL_max, budget / 2)  -- cadre need to be paid
            SL = CL * 0.5 + territory_count  -- sympathizers follow cadre

        Args:
            cadre_level: Organization cadre quality [0, 1].
            cohesion: Internal unity [0, 1].
            budget: Cash on hand.
            heat: State attention [0, 1].
            territory_count: Number of territories org operates in.
            reputation: Existing reputation (carried from previous tick).

        Returns:
            VanguardResources snapshot.
        """
        # Heat suppresses capacity — being targeted makes work harder
        heat_penalty_cl = 1.0 - heat * 0.5
        heat_penalty_sl = 1.0 - heat * 0.3

        # Maximum cadre labor: skilled organizers, scaled by cadre quality
        max_cl = cadre_level * 10.0 * heat_penalty_cl

        # Maximum sympathizer labor: mass support, scaled by territory presence
        max_sl = cohesion * max(territory_count, 1) * 5.0 * heat_penalty_sl

        # Actual CL is capped by budget (cadre need stipends)
        cl = min(max_cl, budget / 2.0)

        # Actual SL follows cadre presence + organic territory support
        sl = min(max_sl, cl * 2.0 + territory_count * 1.0)

        return cls(
            cadre_labor=round(cl, 2),
            sympathizer_labor=round(sl, 2),
            reputation=reputation,
            budget=budget,
            heat=heat,
            max_cadre_labor=round(max_cl, 2),
            max_sympathizer_labor=round(max_sl, 2),
        )


# ---------------------------------------------------------------------------
# Action cost table
# ---------------------------------------------------------------------------

#: Cost of each player verb in (CL, SL, Budget).
#: These are baseline costs; actual cost depends on target and context.
ACTION_COSTS: dict[str, tuple[float, float, float]] = {
    # Build verbs (CL-heavy)
    "educate": (2.0, 0.5, 5.0),
    "reproduce": (1.5, 1.0, 10.0),
    "investigate": (3.0, 0.0, 2.0),
    # Project verbs (SL-heavy)
    "attack": (1.0, 3.0, 15.0),
    "mobilize": (0.5, 4.0, 8.0),
    "campaign": (1.0, 3.0, 20.0),
    # Manage verbs (Budget-heavy)
    "aid": (0.5, 1.0, 25.0),
    "move": (1.0, 0.5, 5.0),
    "negotiate": (2.0, 0.0, 10.0),
}


def check_can_afford(
    resources: VanguardResources,
    verb: str,
) -> tuple[bool, str]:
    """Check whether the player org can afford an action.

    Args:
        resources: Current vanguard resource snapshot.
        verb: Player verb string.

    Returns:
        Tuple of (can_afford, reason). If can_afford is False,
        reason explains which resource is insufficient.
    """
    costs = ACTION_COSTS.get(verb)
    if costs is None:
        return False, f"Unknown verb: {verb}"

    cl_cost, sl_cost, budget_cost = costs

    if resources.cadre_labor < cl_cost:
        return False, f"Need {cl_cost} CL, have {resources.cadre_labor:.1f}"
    if resources.sympathizer_labor < sl_cost:
        return False, f"Need {sl_cost} SL, have {resources.sympathizer_labor:.1f}"
    if resources.budget < budget_cost:
        return False, f"Need ${budget_cost}, have ${resources.budget:.1f}"

    return True, "OK"
