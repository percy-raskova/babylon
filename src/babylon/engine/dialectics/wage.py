"""WageDialectic — ValueOfLaborPower ↔ PriceOfLaborPower (V1 Ch19-22).

Ch19: The daily price of labour-power does not coincide with its
daily value. The wage mystifies the relation by concealing the
division between necessary and surplus labor.

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class ValueOfLaborPower(BaseModel):
    """Value of labor-power: cost to reproduce the worker (V1 Ch6).

    Ch6: "The value of labour-power is determined by the value of the
    necessaries of life habitually required by the average labourer."

    Attributes:
        reproduction_cost: Total value needed to reproduce labor-power.
        subsistence_hours: Labor-hours of the necessaries of life.
        historical_moral_element: The "historical and moral element"
            that varies by country and epoch (Ch6). ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    reproduction_cost: float = Field(default=0.0, ge=0.0)
    subsistence_hours: float = Field(default=0.0, ge=0.0)
    historical_moral_element: float = Field(default=0.0, ge=0.0, le=1.0)


class PriceOfLaborPower(BaseModel):
    """Price of labor-power: the wage actually paid (V1 Ch19).

    Ch19: "What the labourer sells is not directly his labour, but his
    labour-power." The price (wage) may differ from the value.

    Attributes:
        nominal_wage: Money wage paid.
        real_wage: Wage in terms of purchasing power.
        relative_wage: Share of total product going to labor ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    nominal_wage: float = Field(default=0.0, ge=0.0)
    real_wage: float = Field(default=0.0, ge=0.0)
    relative_wage: float = Field(default=0.0, ge=0.0, le=1.0)


class WageDialectic(Dialectic[ValueOfLaborPower, PriceOfLaborPower]):
    """The value ↔ price of labor-power contradiction (V1 Ch19-22).

    Ch19: The daily price of labour-power does not coincide with its
    daily value. The wage mystifies the relation by concealing the
    division between necessary and surplus labor.

    Weight semantics:
        weight < 0 → tight labor market ("buy" market for labor-power).
                      Workers have bargaining power, W approaches V.
        weight > 0 → loose labor market ("sell" market for labor-power).
                      Reserve army is large, W falls below V.
    """

    type_tag: str = "WageDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> WageDialectic:
        """Motion law T for the wage contradiction.

        Reserve army pressure (from AccumulationDialectic) pushes weight
        positive (toward sell market / depressed wages).

        Args:
            inputs: Upstream outputs. Looks for ``reserve_army_pressure``.
            world: Read-only world context.

        Returns:
            New WageDialectic with updated weight and tick.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            pressure = float(own_input.get("reserve_army_pressure", 0.0))
            delta = pressure * 0.1

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project wage state for downstream consumption.

        Returns:
            Base observation + wage-specific fields.
        """
        obs = super().observe()
        obs.update(
            {
                "reproduction_cost": self.pole_a.reproduction_cost,
                "subsistence_hours": self.pole_a.subsistence_hours,
                "nominal_wage": self.pole_b.nominal_wage,
                "real_wage": self.pole_b.real_wage,
                "relative_wage": self.pole_b.relative_wage,
            }
        )
        return obs


__all__ = [
    "PriceOfLaborPower",
    "ValueOfLaborPower",
    "WageDialectic",
]
