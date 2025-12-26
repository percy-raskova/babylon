"""Revolutionary finance model for revolutionary organizations.

This module defines the RevolutionaryFinance model which tracks the financial
state of revolutionary organizations in the Babylon simulation.

Epoch 1 (The Ledger) - Political Economy of Liquidity specification.

The RevolutionaryFinance model represents the fiscal capacity of revolutionary actors:

- war_chest: available liquid funds for revolutionary activity
- operational_burn: minimum cost to maintain organization per tick
- Income streams: dues (members), expropriation (direct action), donors (liberal funding)
- Strategic concerns: heat (state attention), reformist_drift (ideological corruption)

Key insight: Revolutionary organizations face a fundamental tension:

- Donor income is easiest but causes reformist_drift (ideological corruption)
- Expropriation income is most revolutionary but generates heat (state attention)
- Dues income is sustainable but requires organizational capacity
"""

from pydantic import BaseModel, ConfigDict

from babylon.models.types import Currency, Ideology, Intensity


class RevolutionaryFinance(BaseModel):
    """Financial state of a revolutionary organization.

    Tracks war chest, operational costs, and corruption metrics (heat, drift).
    Part of the Political Economy of Liquidity (Epoch 1: The Ledger).

    Attributes:
        war_chest: Available liquid funds for revolutionary activity. Defaults to 5.0.
        operational_burn: Minimum cost to maintain organization per tick. Defaults to 2.0.
        dues_income: Member contributions per tick. Defaults to 1.0.
        expropriation_income: Income from direct action. Defaults to 0.0.
        donor_income: Liberal funding income. Defaults to 0.0.
        heat: State attention level [0, 1]. Higher = more surveillance. Defaults to 0.0.
        reformist_drift: Ideological corruption [-1, 1]. Positive = reformist. Defaults to 0.0.

    Example:
        >>> finance = RevolutionaryFinance(war_chest=50.0, heat=0.7)
        >>> finance.heat >= 0.8  # Check if in danger zone
        False
    """

    model_config = ConfigDict(frozen=True)

    war_chest: Currency = 5.0
    operational_burn: Currency = 2.0
    dues_income: Currency = 1.0
    expropriation_income: Currency = 0.0
    donor_income: Currency = 0.0
    heat: Intensity = 0.0
    reformist_drift: Ideology = 0.0
