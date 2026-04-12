"""CirculationDialectic — Circuit of Capital (V2 Ch1-4).

Pole A holds the ``CircuitState`` tracking Money, Productive, and Commodity
capital. Motion law feeds inputs through ``advance_circuit``.

See Also:
    :mod:`babylon.economics.circulation.circuit`: Pure circuit advancement.
    :mod:`babylon.economics.circulation.types`: CircuitState, TurnoverProfile.
    :class:`babylon.engine.dialectics.crises.RealizationCrisisDialectic`
"""

from __future__ import annotations

from typing import Any

from babylon.economics.circulation.circuit import advance_circuit
from babylon.economics.circulation.types import (
    COMMODITY_OVERHANG_CRISIS,
    CircuitState,
    TurnoverProfile,
)
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView
from babylon.models.types import Currency


class CirculationDialectic(Dialectic[CircuitState, EmptyPole]):
    """Circuit of capital dialectic.

    Pole A holds the `CircuitState` tracking Money, Productive, and Commodity capital.
    Motion law feeds inputs through `advance_circuit`.
    """

    type_tag: str = "CirculationDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> CirculationDialectic:
        """Motion law T for the circuit of capital.

        Args:
            inputs: Upstream outputs with ``elapsed_days``, ``surplus_value``,
                    and optional ``profile_dict``.
            world: Read-only world context.

        Returns:
            New CirculationDialectic with updated circuit state.
        """
        # Default fallback values
        elapsed_days = 0
        surplus_value = Currency(0.0)
        profile = TurnoverProfile(
            naics_code="DEFAULT",
            working_period_days=1,
            non_working_production_days=0,
            purchase_time_days=0,
            sale_time_days=0,
            fixed_capital_ratio=0.0,
        )

        own_input = inputs.upstream.get(self.id)
        if own_input:
            elapsed_days = int(own_input.get("elapsed_days", 0))
            surplus_value = Currency(float(own_input.get("surplus_value", 0.0)))
            if "profile_dict" in own_input:
                profile = TurnoverProfile(**own_input["profile_dict"])

        new_circuit_state = advance_circuit(
            state=self.pole_a,
            turnover=profile,
            surplus_value=surplus_value,
            elapsed_days=elapsed_days,
        )

        # Determine weight dynamically based on commodity overhang
        overhang = new_circuit_state.commodity_overhang
        # We map an overhang above CRISIS threshold to negative weight (-1.0)
        delta_overhang = overhang - (COMMODITY_OVERHANG_CRISIS / 2.0)
        new_weight = max(-1.0, min(1.0, -delta_overhang * 2.0))

        return self.model_copy(
            update={"pole_a": new_circuit_state, "weight": new_weight, "tick_updated": world.tick}
        )

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Sublate to Realization Crisis if commodity overhang exceeds threshold.

        Returns:
            RealizationCrisisDialectic if overhanging, else None.
        """
        from babylon.engine.dialectics.crises import RealizationCrisisDialectic

        if (
            self.pole_a.total_capital > 0
            and self.pole_a.commodity_overhang > COMMODITY_OVERHANG_CRISIS
        ):
            return RealizationCrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=self.id,
                tick_created=self.tick_updated,
                tick_updated=self.tick_updated,
            )
        return None


__all__ = [
    "CirculationDialectic",
]
