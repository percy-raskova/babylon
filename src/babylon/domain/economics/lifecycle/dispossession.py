"""Crisis dispossession logic for wealth destruction events (Feature 038, US5).

Models crisis-driven LA -> Proletariat transitions via wealth destruction
(foreclosure, eviction). The dispossession rate is modifiable by community
membership — racialized subprime targeting is a historical input, not random.

Feature: 038-unified-class-system
Date: 2026-03-01

See Also:
    ``specs/038-unified-class-system/spec.md`` FR-010.
    :mod:`babylon.domain.economics.lifecycle.inheritance`: Inheritance severing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DispossessionResult(BaseModel):
    """Result of crisis dispossession computation for a household.

    Args:
        household_wealth: Original household wealth before crisis.
        foreclosure_rate: Base foreclosure rate applied.
        effective_rate: Actual rate after community targeting multiplier.
        wealth_destroyed: Amount of wealth destroyed by crisis.
        remaining_wealth: Household wealth after dispossession.
        class_position_change_indicated: True if remaining wealth drops
            below 50% of original (signals LA -> PROLETARIAT transition).
    """

    model_config = ConfigDict(frozen=True)

    household_wealth: float = Field(ge=0.0)
    foreclosure_rate: float = Field(ge=0.0, le=1.0)
    effective_rate: float = Field(ge=0.0, le=1.0)
    wealth_destroyed: float = Field(ge=0.0)
    remaining_wealth: float = Field(ge=0.0)
    class_position_change_indicated: bool

    @model_validator(mode="after")
    def _validate_wealth_conservation(self) -> DispossessionResult:
        """Wealth destroyed + remaining must equal original household wealth."""
        total = self.wealth_destroyed + self.remaining_wealth
        if abs(total - self.household_wealth) > 0.01:
            msg = (
                f"Wealth not conserved: destroyed ({self.wealth_destroyed}) "
                f"+ remaining ({self.remaining_wealth}) != "
                f"original ({self.household_wealth})"
            )
            raise ValueError(msg)
        return self


def compute_crisis_dispossession(
    household_wealth: float,
    foreclosure_rate: float,
    community_targeting_multiplier: float = 1.0,
) -> DispossessionResult:
    """Compute wealth destruction from crisis event.

    Args:
        household_wealth: Pre-crisis household wealth.
        foreclosure_rate: Base foreclosure rate (0.0 to 1.0).
        community_targeting_multiplier: Multiplier for racialized targeting.
            Defaults to 1.0 (no targeting). Values > 1.0 indicate
            disproportionate targeting (e.g., subprime targeting of
            Black and Latino homeowners in 2008).

    Returns:
        DispossessionResult with wealth destruction and transition signal.
    """
    # Effective rate capped at 1.0
    effective_rate = min(1.0, foreclosure_rate * community_targeting_multiplier)

    wealth_destroyed = household_wealth * effective_rate
    remaining_wealth = household_wealth - wealth_destroyed

    # Signal class position change if remaining wealth drops below 50% of original
    # (i.e., the household has lost enough to potentially fall out of LA bracket)
    change_indicated = remaining_wealth < household_wealth * 0.50

    return DispossessionResult(
        household_wealth=household_wealth,
        foreclosure_rate=foreclosure_rate,
        effective_rate=effective_rate,
        wealth_destroyed=wealth_destroyed,
        remaining_wealth=remaining_wealth,
        class_position_change_indicated=change_indicated,
    )


__all__ = ["DispossessionResult", "compute_crisis_dispossession"]
