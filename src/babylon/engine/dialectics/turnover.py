"""TurnoverDialectic — Turnover Cycle (V2 Part 2).

Pole A is TurnoverProfile (durations).
Pole B is AnnualSurplusValue (computed turnover-adjusted rates).

See Also:
    :mod:`babylon.economics.circulation.turnover`: Pure turnover computation.
    :mod:`babylon.economics.circulation.types`: TurnoverProfile, AnnualSurplusValue.
"""

from __future__ import annotations

from typing import Any

from babylon.economics.circulation.turnover import compute_annual_surplus_value
from babylon.economics.circulation.types import (
    AnnualSurplusValue,
    TurnoverProfile,
)
from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.models.types import Currency


class TurnoverDialectic(Dialectic[TurnoverProfile, AnnualSurplusValue]):
    """Turnover cycle dialectic.

    Pole A is TurnoverProfile (durations).
    Pole B is AnnualSurplusValue (computed turnover-adjusted rates).
    """

    type_tag: str = "TurnoverDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> TurnoverDialectic:
        """Motion law T for turnover dynamics.

        Args:
            inputs: Upstream outputs with ``v`` and ``s`` values.
            world: Read-only world context.

        Returns:
            New TurnoverDialectic with updated annual surplus value.
        """
        v = 0.0
        s = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input:
            v = float(own_input.get("v", 0.0))
            s = float(own_input.get("s", 0.0))

        annual_sv = compute_annual_surplus_value(
            variable_capital=Currency(v),
            surplus_per_cycle=Currency(s),
            turnover_time_days=max(1, self.pole_a.turnover_time),
        )

        return self.model_copy(update={"pole_b": annual_sv, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project turnover state.

        Returns:
            Base observation + annual surplus value metrics.
        """
        obs = super().observe()
        obs.update(
            {
                "annual_surplus_value": float(self.pole_b.annual_surplus_value),
                "annual_rate_of_surplus_value": float(self.pole_b.annual_rate_of_surplus_value),
            }
        )
        return obs


__all__ = [
    "TurnoverDialectic",
]
