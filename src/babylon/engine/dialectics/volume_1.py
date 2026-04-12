"""Capital Volume I dialectics.

This module contains the concrete Dialectic subclasses derived from
Marx's *Capital*, Volume I. Each class cites the chapter(s) that justify
its motion law.

Dialectics defined:
    CommodityDialectic (V1 Ch1): UseValue ↔ ExchangeValue.
    LaborProcessDialectic (V1 Ch7§1): ConcreteLabor ↔ AbstractLabor.
    ProductionDialectic (V1 Ch7§2, Ch8, Ch9): LaborProcess ↔ Valorization.
    WageDialectic (V1 Ch19-22): ValueOfLaborPower ↔ PriceOfLaborPower.
    AccumulationDialectic (V1 Ch23-25): ConcentrationOfCapital ↔ ReserveArmyExpansion.
    PrimitiveAccumulationDialectic (V1 Ch26-33 + Sakai/MIM(P)):
        ColonialExpropriation ↔ SettlerFormation.

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator
from babylon.economics.tensor import DepartmentRow
from babylon.economics.value import AbstractLabor, ConcreteLabor, ExchangeValue, UseValue
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView
from babylon.formulas.fundamental_theorem import (
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
)

# ===========================================================================
# CommodityDialectic
# ===========================================================================


# ===========================================================================
# CommodityDialectic
# ===========================================================================


class CommodityDialectic(Dialectic[UseValue, ExchangeValue]):
    """The use-value ↔ exchange-value contradiction (V1 Ch1).

    Weight reflects whether the commodity is currently being held for
    use (``weight < 0``, A dominant) or for exchange (``weight > 0``,
    B dominant). Zero is equilibrium.

    Motion law:
        - **Production** events shift weight toward exchange (increase, toward B).
        - **Consumption** events shift weight toward use (decrease, toward A).

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

        Production events shift weight toward exchange (pole B, positive);
        consumption events shift toward use (pole A, negative).

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
                # Production shifts toward exchange (B): weight increases
                delta = intensity
            elif event == "consumption":
                # Consumption shifts toward use (A): weight decreases
                delta = -intensity

        new_weight = max(-1.0, min(1.0, self.weight + delta))

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


# ===========================================================================
# LaborProcessDialectic (V1 Ch7§1) — ConcreteLabor ↔ AbstractLabor
# ===========================================================================


class LaborProcessDialectic(Dialectic[ConcreteLabor, AbstractLabor]):
    """The concrete ↔ abstract labor contradiction (V1 Ch1§2, Ch7§1).

    Every act of labor has a dual character: it is simultaneously concrete
    (producing specific use-values) and abstract (creating value as
    expenditure of human labor-power in general).

    Weight semantics:
        weight < 0 → concrete labor dominant (A): craft production,
                      skill matters, qualitative differences prominent.
        weight > 0 → abstract labor dominant (B): factory production,
                      labor is homogenized, only quantity matters.

    Motion law:
        Competitive pressure (from upstream) pushes weight positive
        (toward abstraction). Absent pressure, weight is stable.
    """

    type_tag: str = "LaborProcessDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> LaborProcessDialectic:
        """Motion law T for the labor process.

        Args:
            inputs: Upstream outputs. Looks for ``competitive_pressure``.
            world: Read-only world context.

        Returns:
            New LaborProcessDialectic with updated weight and tick.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            pressure = float(own_input.get("competitive_pressure", 0.0))
            delta = pressure * 0.1

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project labor process state.

        Returns:
            Base observation + labor-specific fields.
        """
        obs = super().observe()
        obs.update(
            {
                "skill": self.pole_a.skill,
                "intensity": self.pole_a.intensity,
                "hours": self.pole_a.hours,
                "labor_type": self.pole_a.labor_type,
                "snlt": self.pole_b.snlt,
                "productivity": self.pole_b.productivity,
            }
        )
        return obs


# ===========================================================================
# ProductionDialectic (V1 Ch7§2, Ch8, Ch9) — LaborProcess ↔ Valorization
# ===========================================================================


class ProductionDialectic(Dialectic[DepartmentRow, EmptyPole]):
    """The labor process ↔ valorization process contradiction (V1 Ch7§2).

    Ch7§2: "The production of surplus-value is the differentia specifica
    of capitalist production." The labor process (creating use-values)
    is subordinated to the valorization process (creating surplus-value).

    Weight semantics:
        weight < 0 → labor process dominant (A): production for use.
        weight > 0 → valorization dominant (B): production for profit.

    observe() returns the **value tensor** [l, c, v, s, r]:
        l = v + s (living labor / new value added)
        c = constant capital transferred
        v = variable capital (value of labor-power)
        s = surplus-value
        r = s/v (rate of exploitation)
    """

    type_tag: str = "ProductionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ProductionDialectic:
        """Motion law T for the production contradiction.

        Higher exploitation rates push weight positive (toward valorization).
        Uses upstream input if available, otherwise falls back to internal state.

        Args:
            inputs: Upstream outputs. Looks for ``rate_of_exploitation``.
            world: Read-only world context.

        Returns:
            New ProductionDialectic with updated weight and tick.
        """
        delta = 0.0
        e = self.pole_a.exploitation_rate

        # Check for upstream input (from LaborProcessDialectic)
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            e = float(own_input.get("rate_of_exploitation", e))

        # Exploitation above 1.0 pushes toward valorization dominance
        if e > 0:
            delta = (e - 1.0) * 0.05

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project the value tensor [l, c, v, s, r] + labor pool.

        Ch8: Total value = c + v + s = c + l, where l = v + s.

        Returns:
            Value tensor components, OCC, and labor pool contribution.
        """
        c = float(self.pole_a.c)
        v = float(self.pole_a.v)
        s = float(self.pole_a.s)
        e = self.pole_a.exploitation_rate

        obs = super().observe()
        obs.update(
            {
                "c": c,
                "v": v,
                "s": s,
                "l": v + s,  # Living labor = new value
                "r": e,  # Rate of exploitation alias
                "rate_of_exploitation": e,
                "occ": self.pole_a.organic_composition,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Production-specific invariants.

        Checks:
            - Surplus value ≥ 0.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        if self.pole_a.s < 0:
            violations.append(f"ProductionDialectic {self.id}: s is negative")
        return violations


# ===========================================================================
# WageDialectic (V1 Ch19-22) — ValueOfLaborPower ↔ PriceOfLaborPower
# ===========================================================================


class ValueOfLaborPower(BaseModel):
    """Value of labor-power: cost to reproduce the worker (V1 Ch6).

    Ch6: "The value of labour-power is determined by the value of the
    necessaries of life habitually required by the average labourer."

    Attributes:
        reproduction_cost: Total value needed to reproduce labor-power.
        subsistence_hours: Labor-hours of the necessaries of life.
        historical_moral_element: The "historical and moral element"
            that varies by country and epoch (Ch6). ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    reproduction_cost: float = Field(default=0.0, ge=0.0)
    subsistence_hours: float = Field(default=0.0, ge=0.0)
    historical_moral_element: float = Field(default=0.0, ge=0.0, le=1.0)


class PriceOfLaborPower(BaseModel):
    """Price of labor-power: the wage actually paid (V1 Ch19).

    Ch19: "What the labourer sells is not directly his labour, but his
    labour-power." The price (wage) may differ from the value.

    Attributes:
        nominal_wage: Money wage paid.
        real_wage: Wage in terms of purchasing power.
        relative_wage: Share of total product going to labor ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    nominal_wage: float = Field(default=0.0, ge=0.0)
    real_wage: float = Field(default=0.0, ge=0.0)
    relative_wage: float = Field(default=0.0, ge=0.0, le=1.0)


class WageDialectic(Dialectic[ValueOfLaborPower, PriceOfLaborPower]):
    """The value ↔ price of labor-power contradiction (V1 Ch19-22).

    Ch19: The daily price of labour-power does not coincide with its
    daily value. The wage mystifies the relation by concealing the
    division between necessary and surplus labor.

    Weight semantics:
        weight < 0 → tight labor market ("buy" market for labor-power).
                      Workers have bargaining power, W approaches V.
        weight > 0 → loose labor market ("sell" market for labor-power).
                      Reserve army is large, W falls below V.
    """

    type_tag: str = "WageDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> WageDialectic:
        """Motion law T for the wage contradiction.

        Reserve army pressure (from AccumulationDialectic) pushes weight
        positive (toward sell market / depressed wages).

        Args:
            inputs: Upstream outputs. Looks for ``reserve_army_pressure``.
            world: Read-only world context.

        Returns:
            New WageDialectic with updated weight and tick.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            pressure = float(own_input.get("reserve_army_pressure", 0.0))
            delta = pressure * 0.1

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project wage state for downstream consumption.

        Returns:
            Base observation + wage-specific fields.
        """
        obs = super().observe()
        obs.update(
            {
                "reproduction_cost": self.pole_a.reproduction_cost,
                "subsistence_hours": self.pole_a.subsistence_hours,
                "nominal_wage": self.pole_b.nominal_wage,
                "real_wage": self.pole_b.real_wage,
                "relative_wage": self.pole_b.relative_wage,
            }
        )
        return obs


# ===========================================================================
# AccumulationDialectic (V1 Ch23-25) — Concentration ↔ ReserveArmy
# ===========================================================================


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


# ===========================================================================
# PrimitiveAccumulationDialectic (V1 Ch26-33 + Sakai/MIM(P))
# ColonialExpropriation ↔ SettlerFormation
# ===========================================================================


class ColonialExpropriation(BaseModel):
    """Active process of dispossessing colonized peoples (V1 Ch26-27, Ch31).

    Ch31: "The treasures captured outside Europe by undisguised looting,
    enslavement, and murder, floated back to the mother-country and were
    there turned into capital."

    Following Sakai (*Settlers*) and MIM(P), this is not merely historical
    but an ongoing process: gentrification, mass incarceration (Ch28's
    "bloody legislation" for the 13th Amendment), ICE raids, etc.

    Attributes:
        expropriation_rate: Rate of ongoing dispossession ∈ [0, 1].
        colonial_extraction: Value extracted via extra-economic coercion.
        land_theft: Fraction of indigenous/colonized land enclosed ∈ [0, 1].
        super_exploitation_rate: Degree colonized workers are paid below
            the value of their labor-power (W_opc < V_opc).
    """

    model_config = ConfigDict(frozen=True)

    expropriation_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    colonial_extraction: float = Field(default=0.0, ge=0.0)
    land_theft: float = Field(default=0.0, ge=0.0, le=1.0)
    super_exploitation_rate: float = Field(default=0.0, ge=0.0)


class SettlerFormation(BaseModel):
    """Creation and maintenance of the settler nation (Sakai, MIM(P)).

    Sakai: The white working class is not a proletariat — it is a
    settler nation. Their material interests are tied to the colonial
    project. Du Bois/Roediger: "The wages of whiteness."

    MIM(P): First World "workers" are net exploiters when Wc/Vc > 1.

    Attributes:
        settler_share: Fraction of colonial surplus distributed as
            imperial rent (super-wages, land, state services) ∈ [0, 1].
        labor_aristocracy_ratio: Wc/Vc for settler workers. > 1.0 means
            they consume more than they produce = labor aristocracy.
        settler_identity: Degree of identification with colonial project
            vs. recognition of shared class interest ∈ [0, 1].
        immiseration_resistance: How resistant settlers are to actual
            proletarianization ∈ [0, 1]. High when bribe flows.
    """

    model_config = ConfigDict(frozen=True)

    settler_share: float = Field(default=0.0, ge=0.0, le=1.0)
    labor_aristocracy_ratio: float = Field(default=1.0, ge=0.0)
    settler_identity: float = Field(default=0.0, ge=0.0, le=1.0)
    immiseration_resistance: float = Field(default=0.0, ge=0.0, le=1.0)


class PrimitiveAccumulationDialectic(Dialectic[ColonialExpropriation, SettlerFormation]):
    """Colonial expropriation ↔ settler formation (V1 Ch26-33 + Sakai).

    The settler-colonial reframing of Marx's primitive accumulation.
    Not "dispossession creates proletarians" but "dispossession of
    colonized peoples creates and sustains a settler class bribed by
    the spoils" (Sakai, MIM(P), Du Bois).

    Weight semantics:
        weight < 0 → A dominant: raw colonial violence is primary.
                      Frontier wars, active genocide, visible extraction.
        weight > 0 → B dominant: settler formation is mature.
                      The bribe is institutionalized, violence structural.
                      "Law and order" replaces open warfare.

    Morphism outputs:
        ``colonial_extraction`` → AccumulationDialectic (capital stock).
        ``imperial_rent_generated`` → WageDialectic (super-wages).
    """

    type_tag: str = "PrimitiveAccumulationDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> PrimitiveAccumulationDialectic:
        """Motion law T for primitive accumulation.

        Extraction boost (from upstream) shifts weight.
        Without input, weight is stable.

        Args:
            inputs: Upstream outputs. Looks for ``extraction_boost``.
            world: Read-only world context.

        Returns:
            New PrimitiveAccumulationDialectic with updated weight.
        """
        delta = 0.0
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            boost = float(own_input.get("extraction_boost", 0.0))
            delta = boost * 0.1

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project settler-colonial state for downstream consumption.

        Emits ``colonial_extraction`` for AccumulationDialectic and
        ``imperial_rent_generated`` for WageDialectic.

        Returns:
            Base observation + settler-colonial fields.
        """
        extraction = self.pole_a.colonial_extraction
        settler_share = self.pole_b.settler_share

        # Imperial rent = extraction distributed to settlers
        # Using the fundamental theorem to calculate exactly how much is extracted.
        # We model settler_share as the alpha (extraction efficiency) over the periphery wages (extraction).
        imperial_rent = calculate_imperial_rent(
            alpha=settler_share,
            periphery_wages=extraction,
            periphery_consciousness=0.0,
        )

        # Derive an endogenous Wc/Vc based on the imperial rent to ground it in the theorem.
        # Assuming base wages match value produced (1.0 ratio), and they receive imperial_rent on top.
        derived_lar = self.pole_b.labor_aristocracy_ratio
        if extraction > 0:
            derived_lar = calculate_labor_aristocracy_ratio(
                core_wages=extraction + imperial_rent, value_produced=extraction
            )

        obs = super().observe()
        obs.update(
            {
                "colonial_extraction": extraction,
                "expropriation_rate": self.pole_a.expropriation_rate,
                "land_theft": self.pole_a.land_theft,
                "super_exploitation_rate": self.pole_a.super_exploitation_rate,
                "settler_share": settler_share,
                "labor_aristocracy_ratio": derived_lar,
                "settler_identity": self.pole_b.settler_identity,
                "immiseration_resistance": self.pole_b.immiseration_resistance,
                "imperial_rent_generated": imperial_rent,
            }
        )
        return obs
