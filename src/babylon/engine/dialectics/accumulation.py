"""AccumulationDialectic — ConcentrationOfCapital ↔ ReserveArmyExpansion (V1 Ch23-25).

Ch25§1: "accumulation of capital is... accompanied by... a
relatively redundant population of labourers." Rising OCC
displaces workers, while accumulation itself creates demand.

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
    :mod:`babylon.economics.reserve_army`: Wage pressure calculations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator
from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class ConcentrationOfCapital(BaseModel):
    """Concentration of capital via reinvestment of surplus (V1 Ch25§1).

    Ch24: "Accumulate, accumulate! That is Moses and the prophets!"

    Attributes:
        total_capital: Total capital stock (c + v).
        reinvestment_rate: Fraction of surplus reinvested ∈ [0, 1].
        fixed_capital: Capital tied up in instruments/machinery.
        centralization_index: Degree of capital centralization ∈ [0, 1].
            Distinct from concentration: centralization is merger
            and acquisition, concentration is growth from reinvestment.
    """

    model_config = ConfigDict(frozen=True)

    total_capital: float = Field(default=0.0, ge=0.0)
    reinvestment_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    fixed_capital: float = Field(default=0.0, ge=0.0)
    centralization_index: float = Field(default=0.0, ge=0.0, le=1.0)


class ReserveArmyExpansion(BaseModel):
    """Industrial reserve army produced by accumulation (V1 Ch25§3).

    Ch25: "The greater the social wealth... the greater is the
    industrial reserve army... The more extensive, finally, the
    lazarus-layers... the greater is official pauperism."

    Attributes:
        unemployed_fraction: Fraction of labor force unemployed ∈ [0, 1].
        wage_pressure: Downward pressure on wages from reserve army.
            Negative = tight market (upward pressure on wages).
        absorption_rate: Rate at which reserve army is absorbed.
        total_labor_pool: Total available labor-hours in the economy.
    """

    model_config = ConfigDict(frozen=True)

    unemployed_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    wage_pressure: float = Field(default=0.0)
    absorption_rate: float = Field(default=0.0, ge=0.0)
    total_labor_pool: float = Field(default=0.0, ge=0.0)


class AccumulationDialectic(Dialectic[ConcentrationOfCapital, ReserveArmyExpansion]):
    """Concentration of capital ↔ reserve army expansion (V1 Ch25).

    Ch25§1: "accumulation of capital is... accompanied by... a
    relatively redundant population of labourers." Rising OCC
    displaces workers, while accumulation itself creates demand.

    Weight semantics:
        weight < 0 → concentration dominant (A): capital expanding,
                      absorbing labor (prosperity phase).
        weight > 0 → reserve army dominant (B): labor displacement,
                      rising unemployment (crisis phase).

    Morphism inputs:
        Receives ``rate_of_exploitation``, ``occ``, ``labor_hours_contributed``
        from ProductionDialectic. Receives ``colonial_extraction`` from
        PrimitiveAccumulationDialectic.
    """

    type_tag: str = "AccumulationDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> AccumulationDialectic:
        """Motion law T for the accumulation contradiction.

        Rising OCC from upstream Production shifts weight positive
        (toward reserve army expansion).

        Args:
            inputs: Upstream outputs. Looks for ``occ``.
            world: Read-only world context.

        Returns:
            New AccumulationDialectic with updated weight and tick.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            occ = float(own_input.get("occ", 0.0))
            # Rising OCC pushes toward reserve army (B)
            if occ > 1.0:
                delta = (occ - 1.0) * 0.02

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project accumulation state for downstream consumption.

        Emits ``reserve_army_pressure`` for WageDialectic and
        ``total_labor_pool`` for macro aggregation.

        Returns:
            Base observation + accumulation-specific fields.
        """
        pressure_calc = DefaultWagePressureCalculator()
        computed_pressure = pressure_calc.compute_wage_pressure(self.pole_b.unemployed_fraction)

        obs = super().observe()
        obs.update(
            {
                "total_capital": self.pole_a.total_capital,
                "reinvestment_rate": self.pole_a.reinvestment_rate,
                "fixed_capital": self.pole_a.fixed_capital,
                "centralization_index": self.pole_a.centralization_index,
                "unemployed_fraction": self.pole_b.unemployed_fraction,
                "wage_pressure": computed_pressure,
                "absorption_rate": self.pole_b.absorption_rate,
                "total_labor_pool": self.pole_b.total_labor_pool,
                "reserve_army_pressure": computed_pressure,
            }
        )
        return obs


__all__ = [
    "AccumulationDialectic",
    "ConcentrationOfCapital",
    "ReserveArmyExpansion",
]
