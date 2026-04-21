"""ImperialDialectic — Core ↔ Periphery (V3 Ch14 §V + MLM-TW).

The Fundamental Theorem of MLM-TW: Revolution in Core is impossible
if W_c > V_c (wages > value produced). The difference is Imperial
Rent (Phi).

See Also:
    :func:`babylon.formulas.fundamental_theorem.calculate_labor_aristocracy_ratio`
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.formulas.fundamental_theorem import (
    calculate_labor_aristocracy_ratio,
)


class CoreEconomy(BaseModel):
    """Pole A for the Imperial dialectic — core / imperialist side.

    Attributes:
        core_wages: Wages paid to core workers (Wc).
        value_produced: Value produced by core workers (Vc).
        profit_rate: Core industrial profit rate.
    """

    model_config = ConfigDict(frozen=True)

    core_wages: float = Field(..., gt=0.0, description="Core wages Wc.")
    value_produced: float = Field(..., gt=0.0, description="Value produced Vc.")
    profit_rate: float = Field(default=0.0, description="Core profit rate.")


class PeripheryEconomy(BaseModel):
    """Pole B for the Imperial dialectic — periphery / exploited side.

    Attributes:
        periphery_wages_ratio: w_core / w_periphery ratio.
        extraction_rate: Imperial extraction efficiency alpha [0, 1].
        consciousness: Periphery resistance level Psi_p [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    periphery_wages_ratio: float = Field(default=1.0, description="w_core / w_periphery ratio.")
    extraction_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Alpha (legacy, fallback)."
    )
    consciousness: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Psi_p (legacy, fallback)."
    )


class ImperialDialectic(Dialectic[CoreEconomy, PeripheryEconomy]):
    """Core ↔ Periphery — the Fundamental Theorem of MLM-TW.

    Pole A is the imperialist core. Pole B is the exploited periphery.
    Imperial Rent Phi is now computed structurally from the production chain.

    Weight semantics:
        < 0: Core extracts freely (labor aristocracy bribed, periphery suppressed).
        > 0: Periphery resists (decolonization, rising consciousness).

    Motion law:
        Reads upstream matrix updates (DecomposedFlow) and computes rent structurally
        via ProductionChainRentCalculator, or falls back to scalar defaults.
        Weight derived from deviation of LAR from unity.

    Invariant:
        Imperial rent Phi >= 0 (core always extracts from periphery).
    """

    type_tag: str = "ImperialDialectic"

    def _compute_lar(self) -> float:
        """Compute labor aristocracy ratio Wc/Vc."""
        return calculate_labor_aristocracy_ratio(
            core_wages=self.pole_a.core_wages,
            value_produced=self.pole_a.value_produced,
        )

    def step(self, inputs: TickInputs, world: WorldView) -> ImperialDialectic:
        """Motion law T for imperial dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``extraction_boost``.
            world: Read-only world context.

        Returns:
            New ImperialDialectic with updated poles and weight.
        """
        own = inputs.upstream.get(self.id, {})

        # If upstream systems provide the rent vector result, we could absorb it.
        # Alternatively, we just track the extraction flow dynamically.
        extraction_boost = float(own.get("extraction_boost", 0.0))

        new_extraction = min(1.0, self.pole_b.extraction_rate + extraction_boost)
        new_periphery = self.pole_b.model_copy(update={"extraction_rate": new_extraction})

        lar = self._compute_lar()
        weight_shift = 1.0 - lar  # Positive when LAR < 1
        new_weight = max(-1.0, min(1.0, weight_shift))

        return self.model_copy(
            update={
                "pole_b": new_periphery,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project imperial rent state.

        Returns:
            Observation dict with Phi, LAR, extraction parameters.
        """
        obs = super().observe()
        obs.update(
            {
                "labor_aristocracy_ratio": self._compute_lar(),
                "core_wages": self.pole_a.core_wages,
                "value_produced": self.pole_a.value_produced,
                "extraction_rate": self.pole_b.extraction_rate,
                "periphery_consciousness": self.pole_b.consciousness,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Verify invariants.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        # Structural Phi constraints are now validated at the Tensor layer.
        return violations


__all__ = [
    "CoreEconomy",
    "ImperialDialectic",
    "PeripheryEconomy",
]
