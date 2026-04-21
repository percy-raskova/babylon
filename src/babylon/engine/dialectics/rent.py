"""RentDialectic — Ground Rent extraction (V3 Ch37-47).

Three-category decomposition: agricultural, resource, urban.

See Also:
    :mod:`babylon.economics.rent`: Ground rent extraction calculations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView


class RentPole(BaseModel):
    """Pole A for the Rent dialectic — three-category decomposition.

    Reimplements the three-category rent aggregation from
    ``economics.rent.types.RentExtraction``. The formula
    ``total_rent = agri + resource + urban`` is identical.
    This is intentional: the dialectic receives pre-aggregated
    county-level data and does not perform data-source lookups.

    See Also:
        :class:`babylon.economics.rent.types.RentExtraction`

    Attributes:
        agricultural_rent: Rent from farming / rural land.
        resource_rent: Rent from extractive industries.
        urban_rent: Rent from urban / building-site monopoly.
    """

    model_config = ConfigDict(frozen=True)

    agricultural_rent: float = Field(default=0.0, ge=0.0)
    resource_rent: float = Field(default=0.0, ge=0.0)
    urban_rent: float = Field(default=0.0, ge=0.0)

    @property
    def total_rent(self) -> float:
        """Total ground rent across all categories."""
        return self.agricultural_rent + self.resource_rent + self.urban_rent


class RentDialectic(Dialectic[RentPole, EmptyPole]):
    """Ground Rent extraction — Absolute ↔ Differential.

    Pole A holds the three-category rent decomposition (agricultural,
    resource, urban) from ``economics.rent.types``.

    Weight semantics:
        < 0: Rent is a minor claims category (small rentier share).
        > 0: Rent dominates surplus distribution (rentier economy).

    Motion law:
        Reads upstream ``total_surplus`` to compute rentier share.
        Weight = 2 * (rent_share) - 1, clamped to [-1, 1].
    """

    type_tag: str = "RentDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> RentDialectic:
        """Motion law T for rent dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``total_surplus``.
            world: Read-only world context.

        Returns:
            New RentDialectic with updated weight.
        """
        own = inputs.upstream.get(self.id, {})
        total_surplus = float(own.get("total_surplus", 0.0))

        if total_surplus > 0:
            rentier_share = self.pole_a.total_rent / total_surplus
            new_weight = max(-1.0, min(1.0, (rentier_share * 2.0) - 1.0))
        else:
            new_weight = 0.0

        return self.model_copy(
            update={
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project rent extraction state.

        Returns:
            Observation dict with rent categories and total.
        """
        obs = super().observe()
        obs.update(
            {
                "total_rent": self.pole_a.total_rent,
                "agricultural_rent": self.pole_a.agricultural_rent,
                "resource_rent": self.pole_a.resource_rent,
                "urban_rent": self.pole_a.urban_rent,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Verify rent components are non-negative.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        if self.pole_a.total_rent < 0:
            violations.append(
                f"RentDialectic {self.id}: total rent is negative ({self.pole_a.total_rent})"
            )
        return violations


__all__ = [
    "RentDialectic",
    "RentPole",
]
