"""PrimitiveAccumulationDialectic — ColonialExpropriation ↔ SettlerFormation.

V1 Ch26-33 + Sakai (*Settlers*) / MIM(P).

The settler-colonial reframing of Marx's primitive accumulation.
Not "dispossession creates proletarians" but "dispossession of
colonized peoples creates and sustains a settler class bribed by
the spoils" (Sakai, MIM(P), Du Bois).

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
    :func:`babylon.formulas.fundamental_theorem.calculate_labor_aristocracy_ratio`
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.formulas.fundamental_theorem import (
    calculate_labor_aristocracy_ratio,
)


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
        # Using the fundamental theorem conceptually:
        imperial_rent = extraction * settler_share

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


__all__ = [
    "ColonialExpropriation",
    "PrimitiveAccumulationDialectic",
    "SettlerFormation",
]
