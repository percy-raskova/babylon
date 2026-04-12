"""DistributionDialectic — Wages ↔ SurplusShares (Grundrisse moment).

This is the Grundrisse-level distribution dialectic, distinct from the
V3 SurplusDistributionDialectic which handles the decomposition of surplus
into profit, interest, rent, and taxes.

See Also:
    :class:`babylon.engine.dialectics.surplus_distribution.SurplusDistributionDialectic`
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class Wages(BaseModel):
    """Wage component of distribution.

    Attributes:
        wages_paid: Total wages paid in the distribution round.
    """

    model_config = ConfigDict(frozen=True)
    wages_paid: float = Field(default=0.0, ge=0.0)


class SurplusShares(BaseModel):
    """Surplus shares distributed among claimants.

    Attributes:
        profit_distributed: Profit of enterprise distributed.
        interest_paid: Interest on borrowed capital.
        rent_paid: Ground rent paid to landowners.
    """

    model_config = ConfigDict(frozen=True)
    profit_distributed: float = Field(default=0.0, ge=0.0)
    interest_paid: float = Field(default=0.0, ge=0.0)
    rent_paid: float = Field(default=0.0, ge=0.0)


class DistributionDialectic(Dialectic[Wages, SurplusShares]):
    """Wages ↔ SurplusShares distribution (Grundrisse moment).

    Weight semantics:
        weight < 0 → wages dominate surplus claims.
        weight > 0 → surplus claims squeeze wages (profit squeeze).
    """

    type_tag: str = "DistributionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> DistributionDialectic:
        """Motion law T for distribution dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``profit_squeeze`` events.
            world: Read-only world context.

        Returns:
            New DistributionDialectic with updated weight.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input and own_input.get("event") == "profit_squeeze":
            delta = float(own_input.get("intensity", 0.0))
        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project distribution state for downstream dialectics.

        Emits:
        - ``wages_paid``: total wages from pole A (→ Consumption)
        - ``surplus_distributed``: total surplus from pole B (→ Consumption)

        Returns:
            Base observation extended with distribution outputs.
        """
        obs = super().observe()
        obs.update(
            {
                "wages_paid": self.pole_a.wages_paid,
                "surplus_distributed": (
                    self.pole_b.profit_distributed
                    + self.pole_b.interest_paid
                    + self.pole_b.rent_paid
                ),
            }
        )
        return obs


__all__ = [
    "DistributionDialectic",
    "SurplusShares",
    "Wages",
]
