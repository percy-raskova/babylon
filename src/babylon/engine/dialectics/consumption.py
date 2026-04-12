"""ConsumptionDialectic — ProductiveConsumption ↔ IndividualConsumption (Grundrisse).

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class ProductiveConsumption(BaseModel):
    """Productive consumption: means of production consumed in production.

    Attributes:
        means_of_production_value: Value of means of production consumed.
    """

    model_config = ConfigDict(frozen=True)
    means_of_production_value: float = Field(default=0.0, ge=0.0)


class IndividualConsumption(BaseModel):
    """Individual consumption: reproduction of labor-power.

    Attributes:
        labor_power_reproduced: Value of labor-power reproduced.
    """

    model_config = ConfigDict(frozen=True)
    labor_power_reproduced: float = Field(default=0.0, ge=0.0)


class ConsumptionDialectic(Dialectic[ProductiveConsumption, IndividualConsumption]):
    """Productive ↔ Individual consumption (Grundrisse moment).

    Weight semantics:
        weight < 0 → productive consumption dominant (accumulation).
        weight > 0 → individual consumption dominant (reproduction).
    """

    type_tag: str = "ConsumptionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ConsumptionDialectic:
        """Motion law T for consumption dynamics.

        Args:
            inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            New ConsumptionDialectic with updated tick.
        """
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})


__all__ = [
    "ConsumptionDialectic",
    "IndividualConsumption",
    "ProductiveConsumption",
]
