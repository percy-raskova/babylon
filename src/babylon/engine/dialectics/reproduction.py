"""ReproductionDialectic — Department I ↔ Department II (V2 Ch20-21).

Pole A handles Dept I (Means of Production).
Pole B handles Dept II (Means of Consumption).
Weight maps to the gap returned by ``check_simple_reproduction``.

See Also:
    :mod:`babylon.economics.circulation.reproduction`: Reproduction balance check.
    :mod:`babylon.economics.tensor`: DepartmentRow pole model.
    :class:`babylon.engine.dialectics.crises.DisproportionalityCrisisDialectic`
"""

from __future__ import annotations

from typing import Any

from babylon.economics.circulation.reproduction import (
    check_simple_reproduction,
)
from babylon.economics.tensor import DepartmentRow
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView


class ReproductionDialectic(Dialectic[DepartmentRow, DepartmentRow]):
    """Department I ↔ Department II contradiction.

    Pole A handles Dept I (Means of Production).
    Pole B handles Dept II (Means of Consumption).
    Weight maps to the gap returned by `check_simple_reproduction`.
    """

    type_tag: str = "ReproductionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ReproductionDialectic:
        """Motion law T for reproduction balance.

        Args:
            inputs: Upstream outputs (currently unused — poles hold totals).
            world: Read-only world context.

        Returns:
            New ReproductionDialectic with updated weight.
        """
        _ = inputs
        # In a real game tick, inputs.upstream would fetch values emitted by
        # multiple local ProductionDialectics and aggregate them into Dept I and II.
        # For pure mechanics testing, we assume poles already hold the updated totals.

        balance = check_simple_reproduction(self.pole_a, self.pole_b)

        # We scale the gap to a -1.0 to 1.0 weight.
        # Gap > 0 = Overproduction Dept I (shifts negative, toward pole A constraint)
        # Gap < 0 = Underproduction Dept I (shifts positive, toward pole B constraints)
        total_value = float(
            self.pole_a.c
            + self.pole_a.v
            + self.pole_a.s
            + self.pole_b.c
            + self.pole_b.v
            + self.pole_b.s
        )

        delta = balance.gap / total_value if total_value > 0 else 0.0

        new_weight = max(-1.0, min(1.0, -delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Sublate to DisproportionalityCrisis when imbalance is extreme.

        Returns:
            DisproportionalityCrisisDialectic if |weight| >= 0.8, else None.
        """
        from babylon.engine.dialectics.crises import DisproportionalityCrisisDialectic

        if abs(self.weight) >= 0.8:
            return DisproportionalityCrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=self.id,
                tick_created=self.tick_updated,
                tick_updated=self.tick_updated,
            )
        return None


__all__ = [
    "ReproductionDialectic",
]
