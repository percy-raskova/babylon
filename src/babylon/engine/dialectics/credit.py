"""CreditDialectic — Real Capital ↔ Fictitious Capital (V3 Ch21-33).

Pole A holds the real capital stock and industrial profit rate.
Pole B holds the accumulated fictitious capital claims.

See Also:
    :mod:`babylon.economics.credit`: Credit cycle and fictitious capital.
    :class:`babylon.engine.dialectics.crises.FinancialCrisisDialectic`
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.credit.types import (
    FINANCIALIZATION_BUBBLE,
    FictitiousCapitalStock,
)
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView


class CreditPole(BaseModel):
    """Pole A for the Credit dialectic — real capital side.

    Attributes:
        total_real_capital: Accumulated real capital stock K.
        profit_rate: Industrial profit rate.
        gdp: Real GDP for financialization ratio computation.
    """

    model_config = ConfigDict(frozen=True)

    total_real_capital: float = Field(..., ge=0.0, description="Real capital stock K.")
    profit_rate: float = Field(default=0.0, description="Industrial profit rate.")
    gdp: float = Field(..., gt=0.0, description="Real GDP.")


class CreditDialectic(Dialectic[CreditPole, FictitiousCapitalStock]):
    """Real Capital ↔ Fictitious Capital.

    Pole A holds the real capital stock and industrial profit rate.
    Pole B holds the accumulated fictitious capital claims via the
    ``FictitiousCapitalStock`` from ``economics.credit.types``.

    Weight semantics:
        < 0: Real capital dominates (healthy production).
        > 0: Fictitious capital dominates (financialization).

    Motion law:
        Reads upstream credit growth and default rates.
        Weight tracks the financialization index mapped to [-1, 1].

    Sublation:
        When financialization index exceeds ``FINANCIALIZATION_BUBBLE`` (3.5),
        sublates to :class:`FinancialCrisisDialectic`.
    """

    type_tag: str = "CreditDialectic"

    def _financialization_index(self) -> float:
        """Compute financialization index = total_claims / gdp."""
        return self.pole_b.ratio_to_real(self.pole_a.gdp)

    def step(self, inputs: TickInputs, world: WorldView) -> CreditDialectic:
        """Motion law T for credit dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``credit_growth``, ``default_rate``.
            world: Read-only world context.

        Returns:
            New CreditDialectic with updated fictitious capital and weight.
        """
        own = inputs.upstream.get(self.id, {})
        credit_growth = float(own.get("credit_growth", 0.0))

        # Fictitious capital grows with credit expansion
        growth_factor = 1.0 + credit_growth
        new_fict = self.pole_b.model_copy(
            update={
                "government_debt": self.pole_b.government_debt * growth_factor,
                "corporate_equity": self.pole_b.corporate_equity * growth_factor,
                "corporate_debt": self.pole_b.corporate_debt * growth_factor,
                "household_debt": self.pole_b.household_debt * growth_factor,
            }
        )

        # Weight = financialization index normalized to [-1, 1]
        # Map: ratio 0 → -1, ratio BUBBLE_THRESHOLD → 0, ratio 2*BUBBLE → +1
        fin_index = new_fict.ratio_to_real(self.pole_a.gdp)
        normalized = (fin_index / FINANCIALIZATION_BUBBLE) - 1.0
        new_weight = max(-1.0, min(1.0, normalized))

        return self.model_copy(
            update={
                "pole_b": new_fict,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Sublate to financial crisis when overaccumulation exceeds threshold.

        Returns:
            FinancialCrisisDialectic if financialization > BUBBLE threshold.
        """
        from babylon.engine.dialectics.crises import FinancialCrisisDialectic

        if self._financialization_index() > FINANCIALIZATION_BUBBLE:
            return FinancialCrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=self.id,
                tick_created=self.tick_updated,
                tick_updated=self.tick_updated,
            )
        return None

    def observe(self) -> dict[str, Any]:
        """Project credit system state.

        Returns:
            Observation dict with financialization index, total claims, profit rate.
        """
        obs = super().observe()
        obs.update(
            {
                "financialization_index": self._financialization_index(),
                "total_claims": self.pole_b.total_claims,
                "total_real_capital": self.pole_a.total_real_capital,
                "profit_rate": self.pole_a.profit_rate,
                "gdp": self.pole_a.gdp,
            }
        )
        return obs


__all__ = [
    "CreditDialectic",
    "CreditPole",
]
