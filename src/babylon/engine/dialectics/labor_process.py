"""LaborProcessDialectic — ConcreteLabor ↔ AbstractLabor (V1 Ch7§1).

Every act of labor has a dual character: it is simultaneously concrete
(producing specific use-values) and abstract (creating value as
expenditure of human labor-power in general).

See Also:
    :mod:`babylon.economics.value`: ConcreteLabor and AbstractLabor pole models.
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from babylon.economics.value import AbstractLabor, ConcreteLabor
from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class LaborProcessDialectic(Dialectic[ConcreteLabor, AbstractLabor]):
    """The concrete ↔ abstract labor contradiction (V1 Ch1§2, Ch7§1).

    Every act of labor has a dual character: it is simultaneously concrete
    (producing specific use-values) and abstract (creating value as
    expenditure of human labor-power in general).

    Weight semantics:
        weight < 0 → concrete labor dominant (A): craft production,
                      skill matters, qualitative differences prominent.
        weight > 0 → abstract labor dominant (B): factory production,
                      labor is homogenized, only quantity matters.

    Motion law:
        Competitive pressure (from upstream) pushes weight positive
        (toward abstraction). Absent pressure, weight is stable.
    """

    type_tag: str = "LaborProcessDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> LaborProcessDialectic:
        """Motion law T for the labor process.

        Args:
            inputs: Upstream outputs. Looks for ``competitive_pressure``.
            world: Read-only world context.

        Returns:
            New LaborProcessDialectic with updated weight and tick.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            pressure = float(own_input.get("competitive_pressure", 0.0))
            delta = pressure * 0.1

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project labor process state.

        Returns:
            Base observation + labor-specific fields.
        """
        obs = super().observe()
        obs.update(
            {
                "skill": self.pole_a.skill,
                "intensity": self.pole_a.intensity,
                "hours": self.pole_a.hours,
                "labor_type": self.pole_a.labor_type,
                "snlt": self.pole_b.snlt,
                "productivity": self.pole_b.productivity,
            }
        )
        return obs


__all__ = [
    "LaborProcessDialectic",
]
