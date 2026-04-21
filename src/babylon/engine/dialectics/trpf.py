"""TRPFDialectic — Tendency of the Rate of Profit to Fall (V3 Ch13-15).

Pole A holds the tendency (profit rate trajectory). Pole B holds the
counter-tendency vector from ``economics.counter_tendencies``.

See Also:
    :mod:`babylon.economics.counter_tendencies`: Counter-tendency calculations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.counter_tendencies.types import CounterTendencyStrength
from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class ProfitRateState(BaseModel):
    """Pole A for the TRPF dialectic.

    Attributes:
        profit_rate: Current average rate of profit.
        profit_rate_trend: Year-over-year change in profit rate.
        organic_composition: c/v ratio (OCC).
    """

    model_config = ConfigDict(frozen=True)

    profit_rate: float = Field(default=0.0, description="Current r = s/(c+v).")
    profit_rate_trend: float = Field(default=0.0, description="Year-over-year change.")
    organic_composition: float = Field(default=0.0, ge=0.0, description="OCC = c/v.")


class TRPFDialectic(Dialectic[ProfitRateState, CounterTendencyStrength]):
    """Tendency of the Rate of Profit to Fall ↔ Counteracting Tendencies.

    Pole A holds the tendency (profit rate trajectory). Pole B holds the
    counter-tendency vector from ``economics.counter_tendencies``.

    Weight semantics:
        < 0: TRPF dominating (profit rate falling, counter-tendencies weak).
        > 0: Counter-tendencies dominating (profit rate sustained).

    Motion law:
        Reads upstream OCC and exploitation rate changes, delegates to
        ``CounterTendencyStrength.net_counter_tendency`` for weight.

    No sublation: TRPF is a structural tendency, not an event.
    """

    type_tag: str = "TRPFDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> TRPFDialectic:
        """Motion law T for TRPF dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``occ``, ``exploitation_rate``.
            world: Read-only world context.

        Returns:
            New TRPFDialectic with updated weight and poles.
        """
        own = inputs.upstream.get(self.id, {})
        new_occ = float(own.get("occ", self.pole_a.organic_composition))
        new_exploitation = float(own.get("exploitation_rate", 0.0))

        # Simple structural TRPF: as OCC rises, profit rate tends to fall
        # r = s/v / (c/v + 1) = exploitation_rate / (occ + 1)
        if new_occ + 1.0 > 0:
            implied_profit_rate = new_exploitation / (new_occ + 1.0)
        else:
            implied_profit_rate = self.pole_a.profit_rate

        new_trend = implied_profit_rate - self.pole_a.profit_rate

        new_pole_a = ProfitRateState(
            profit_rate=implied_profit_rate,
            profit_rate_trend=new_trend,
            organic_composition=new_occ,
        )

        # Weight = net counter-tendency mapped to [-1, 1]
        net_ct = self.pole_b.net_counter_tendency
        new_weight = max(-1.0, min(1.0, net_ct))

        return self.model_copy(
            update={
                "pole_a": new_pole_a,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project TRPF state for downstream consumers.

        Returns:
            Observation dict with profit rate, OCC, net counter-tendency.
        """
        obs = super().observe()
        obs.update(
            {
                "profit_rate": self.pole_a.profit_rate,
                "profit_rate_trend": self.pole_a.profit_rate_trend,
                "organic_composition": self.pole_a.organic_composition,
                "net_counter_tendency": self.pole_b.net_counter_tendency,
            }
        )
        return obs


__all__ = [
    "ProfitRateState",
    "TRPFDialectic",
]
