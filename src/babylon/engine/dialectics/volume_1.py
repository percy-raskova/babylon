"""Capital Volume I dialectics.

This module contains the concrete Dialectic subclasses derived from
Marx's *Capital*, Volume I. Each class cites the chapter(s) that justify
its motion law.

Dialectics defined:
    CommodityDialectic (V1 Ch1): UseValue ↔ ExchangeValue.

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView

# ===========================================================================
# Pole types
# ===========================================================================


class UseValue(BaseModel):
    """Properties of a commodity as use-value (V1 Ch1).

    Attributes:
        utility: How useful the commodity is to its possessor, ∈ [0, 1].
        demand: Aggregate demand (labor-hours or units).
    """

    model_config = ConfigDict(frozen=True)

    utility: float = Field(default=0.5, ge=0.0, le=1.0)
    demand: float = Field(default=0.0, ge=0.0)


class ExchangeValue(BaseModel):
    """Properties of a commodity as exchange-value (V1 Ch1).

    Attributes:
        price: Monetary price of the commodity.
        snlt: Socially Necessary Labour Time embodied.
    """

    model_config = ConfigDict(frozen=True)

    price: float = Field(default=0.0, ge=0.0)
    snlt: float = Field(default=0.0, ge=0.0)


# ===========================================================================
# CommodityDialectic
# ===========================================================================


class CommodityDialectic(Dialectic[UseValue, ExchangeValue]):
    """The use-value ↔ exchange-value contradiction (V1 Ch1).

    Weight reflects whether the commodity is currently being held for
    use (``weight → 1``) or for exchange (``weight → 0``).

    Motion law:
        - **Production** events shift weight toward exchange (decrease).
        - **Consumption** events shift weight toward use (increase).

    The input convention is an upstream dict with keys:
        - ``event``: ``"production"`` or ``"consumption"``
        - ``intensity``: float ∈ [0, 1] controlling shift magnitude

    Sublation: None in Phase 1 (commodities persist).

    Invariants:
        - SNLT ≥ 0 (enforced by pole validation)
    """

    type_tag: str = "CommodityDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> CommodityDialectic:
        """Motion law T for the commodity contradiction.

        Production events shift weight toward exchange (pole B);
        consumption events shift toward use (pole A).

        Args:
            inputs: Upstream outputs. Looks for own id's entry with
                    ``event`` and ``intensity`` keys.
            world: Read-only world context (unused in Phase 1).

        Returns:
            New CommodityDialectic with updated weight and tick.
        """
        # Default: no shift
        delta = 0.0

        # Check own upstream input
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            event = own_input.get("event", "")
            intensity = float(own_input.get("intensity", 0.0))

            if event == "production":
                # Production shifts toward exchange: weight decreases
                delta = -intensity
            elif event == "consumption":
                # Consumption shifts toward use: weight increases
                delta = intensity

        new_weight = max(0.0, min(1.0, self.weight + delta))

        return self.model_copy(
            update={
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project commodity state for frontend rendering.

        Returns:
            Base observation dict extended with commodity-specific fields:
            utility, demand, price, snlt.
        """
        obs = super().observe()
        obs.update(
            {
                "utility": self.pole_a.utility,
                "demand": self.pole_a.demand,
                "price": self.pole_b.price,
                "snlt": self.pole_b.snlt,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Commodity-specific invariants.

        Checks:
            - SNLT ≥ 0 (should be guaranteed by pole validation, but
              we double-check as a runtime safety net).

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        if self.pole_b.snlt < 0:
            violations.append(
                f"CommodityDialectic {self.id}: SNLT is negative ({self.pole_b.snlt})"
            )
        return violations
