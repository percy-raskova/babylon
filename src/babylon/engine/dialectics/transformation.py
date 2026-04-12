"""TransformationDialectic — Value → Price of Production (V3 Ch9-10).

The transformation problem: values produced in individual capitals diverge
from the prices at which commodities actually exchange. The average rate of
profit equalizes across sectors, so that equal capitals yield equal profits
regardless of their organic composition.

    price_of_production = cost_price × (1 + average_profit_rate)

This dialectic computes the economy-wide average profit rate from upstream
production data and makes it available as an observation frame for
CommodityDialectic (observation-relativity).

See Also:
    :class:`babylon.engine.dialectics.surplus_distribution.SurplusDistributionDialectic`
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView


class TransformationPole(BaseModel):
    """Average profit rate computed from aggregate production data.

    Attributes:
        average_profit_rate: Economy-wide average rate of profit r̄.
            Computed as: total_surplus / total_cost_price across all sectors.
    """

    model_config = ConfigDict(frozen=True)

    average_profit_rate: float = Field(
        default=0.0,
        ge=0.0,
        description="Economy-wide average rate of profit.",
    )


class TransformationDialectic(Dialectic[TransformationPole, EmptyPole]):
    """Value → Price of Production transformation (V3 Ch9-10).

    This dialectic mediates between the V1 world of labor-values and
    the V3 world of production prices. It reads upstream production
    dialectics to compute the economy-wide average profit rate, then
    makes that rate available as an observation frame.

    Weight semantics:
        weight < 0 → values dominate prices (low equalization).
        weight > 0 → prices of production fully equalized.

    observe() emits:
        - ``average_profit_rate``: r̄ = Σs / Σ(c+v)
    """

    type_tag: str = "TransformationDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> TransformationDialectic:
        """Motion law T: recompute average profit rate from upstream.

        Reads aggregate c, v, s from upstream production dialectics
        and computes r̄ = Σs / Σ(c+v).

        Args:
            inputs: Upstream outputs with ``rate_of_exploitation`` and ``occ``.
            world: Read-only world context.

        Returns:
            New TransformationDialectic with updated profit rate.
        """
        total_surplus = 0.0
        total_cost_price = 0.0

        # Read from upstream production data
        for obs in inputs.upstream.values():
            s = float(obs.get("s", 0.0))
            c = float(obs.get("c", 0.0))
            v = float(obs.get("v", 0.0))
            total_surplus += s
            total_cost_price += c + v

        if total_cost_price > 0:
            new_rate = total_surplus / total_cost_price
        else:
            new_rate = self.pole_a.average_profit_rate

        new_pole = self.pole_a.model_copy(update={"average_profit_rate": new_rate})

        # Weight: how far equalization has proceeded
        # Higher rate → more deviation from labor values → higher weight
        new_weight = max(-1.0, min(1.0, new_rate * 2.0 - 0.5))

        return self.model_copy(
            update={
                "pole_a": new_pole,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project transformation state.

        Returns:
            Base observation extended with ``average_profit_rate``.
        """
        obs = super().observe()
        obs.update(
            {
                "average_profit_rate": self.pole_a.average_profit_rate,
            }
        )
        return obs


__all__ = [
    "TransformationDialectic",
    "TransformationPole",
]
