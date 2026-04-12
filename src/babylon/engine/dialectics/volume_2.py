"""Capital Volume II dialectics.

This module contains concrete Dialectic subclasses derived from Marx's
*Capital*, Volume II, handling the macro dynamics of circulation and reproduction.
We aggressively utilize the pure domain functions in `babylon.economics.circulation`
to maintain separation of concerns.

Dialectics defined:
    CirculationDialectic (V2 Ch1-4): CircuitState ↔ EmptyPole
    TurnoverDialectic (V2 Part 2): TurnoverProfile ↔ EmptyPole
    ReproductionDialectic (V2 Ch20-21): DepartmentRow(I) ↔ DepartmentRow(II)
    DistributionDialectic (Grundrisse): Wages ↔ SurplusShares
    ConsumptionDialectic (Grundrisse): ProductiveConsumption ↔ IndividualConsumption
    RealizationCrisisDialectic (Derived crisis)
    DisproportionalityCrisisDialectic (Derived crisis)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.circulation.circuit import advance_circuit
from babylon.economics.circulation.reproduction import (
    check_simple_reproduction,
)
from babylon.economics.circulation.turnover import compute_annual_surplus_value
from babylon.economics.circulation.types import (
    COMMODITY_OVERHANG_CRISIS,
    AnnualSurplusValue,
    CircuitState,
    TurnoverProfile,
)
from babylon.economics.tensor import DepartmentRow
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView
from babylon.models.types import Currency

# ===========================================================================
# RealizationCrisisDialectic
# ===========================================================================


class RealizationCrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Triggered when CirculationDialectic sublates due to realization failure."""

    type_tag: str = "RealizationCrisisDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> RealizationCrisisDialectic:
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})


class CirculationDialectic(Dialectic[CircuitState, EmptyPole]):
    """Circuit of capital dialectic.

    Pole A holds the `CircuitState` tracking Money, Productive, and Commodity capital.
    Motion law feeds inputs through `advance_circuit`.
    """

    type_tag: str = "CirculationDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> CirculationDialectic:
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
        # Sublate to Realization Crisis if commodity_overhang exceeds acceptable bounds
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


# ===========================================================================
# TurnoverDialectic
# ===========================================================================


class TurnoverDialectic(Dialectic[TurnoverProfile, AnnualSurplusValue]):
    """Turnover cycle dialectic.

    Pole A is TurnoverProfile (durations).
    Pole B is AnnualSurplusValue (computed turnover-adjusted rates).
    """

    type_tag: str = "TurnoverDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> TurnoverDialectic:
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
        obs = super().observe()
        obs.update(
            {
                "annual_surplus_value": float(self.pole_b.annual_surplus_value),
                "annual_rate_of_surplus_value": float(self.pole_b.annual_rate_of_surplus_value),
            }
        )
        return obs


# ===========================================================================
# ReproductionDialectic
# ===========================================================================


class DisproportionalityCrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    type_tag: str = "DisproportionalityCrisisDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> DisproportionalityCrisisDialectic:
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})


class ReproductionDialectic(Dialectic[DepartmentRow, DepartmentRow]):
    """Department I ↔ Department II contradiction.

    Pole A handles Dept I (Means of Production).
    Pole B handles Dept II (Means of Consumption).
    Weight maps to the gap returned by `check_simple_reproduction`.
    """

    type_tag: str = "ReproductionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ReproductionDialectic:
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


# ===========================================================================
# DistributionDialectic
# ===========================================================================


class Wages(BaseModel):
    model_config = ConfigDict(frozen=True)
    wages_paid: float = Field(default=0.0, ge=0.0)


class SurplusShares(BaseModel):
    model_config = ConfigDict(frozen=True)
    profit_distributed: float = Field(default=0.0, ge=0.0)
    interest_paid: float = Field(default=0.0, ge=0.0)
    rent_paid: float = Field(default=0.0, ge=0.0)


class DistributionDialectic(Dialectic[Wages, SurplusShares]):
    type_tag: str = "DistributionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> DistributionDialectic:
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input and own_input.get("event") == "profit_squeeze":
            delta = float(own_input.get("intensity", 0.0))
        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})


# ===========================================================================
# ConsumptionDialectic
# ===========================================================================


class ProductiveConsumption(BaseModel):
    model_config = ConfigDict(frozen=True)
    means_of_production_value: float = Field(default=0.0, ge=0.0)


class IndividualConsumption(BaseModel):
    model_config = ConfigDict(frozen=True)
    labor_power_reproduced: float = Field(default=0.0, ge=0.0)


class ConsumptionDialectic(Dialectic[ProductiveConsumption, IndividualConsumption]):
    type_tag: str = "ConsumptionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ConsumptionDialectic:
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})
