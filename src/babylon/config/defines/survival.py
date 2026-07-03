"""Survival calculus (P(S|A), P(S|R)) and Agency-Layer struggle dynamics.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SurvivalDefines(BaseModel):
    """Survival calculus coefficients."""

    model_config = ConfigDict(frozen=True)

    # Acquiescence probability P(S|A)
    steepness_k: float = Field(
        default=10.0,
        gt=0.0,
        description="Game design: sigmoid sharpness in acquiescence probability.",
    )
    default_subsistence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Game design: minimum wealth for survival through compliance.",
    )

    # Revolution probability P(S|R)
    default_organization: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: fallback organization value.",
    )
    default_repression: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: fallback repression value.",
    )
    revolution_threshold: float = Field(
        default=1.0,
        gt=0.0,
        description="Game design: tipping point for P(S|R) formula.",
    )
    repression_base: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: base resistance to revolution in denominator.",
    )


class VitalityDefines(BaseModel):
    """Mortality coefficients for Mass Line population dynamics.

    The Grinding Attrition Formula models probabilistic mortality based on
    intra-class inequality:
    - Even with sufficient average wealth, high inequality kills marginal workers
    - Deaths reduce population → per-capita wealth increases → equilibrium

    Formula:
        effective_wealth_per_capita = wealth / population
        marginal_wealth = effective_wealth_per_capita × (1 - inequality × inequality_impact)
        mortality_rate = max(0, (consumption_needs - marginal_wealth) / consumption_needs)
        deaths = floor(population × mortality_rate × base_mortality_factor)

    Malthusian Correction: Population decline increases per-capita wealth,
    reducing future mortality rates and creating equilibrium dynamics.
    """

    model_config = ConfigDict(frozen=True)

    base_mortality_factor: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of at-risk population that dies per tick.",
    )
    inequality_impact: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Game design: how strongly inequality affects marginal wealth (1.0=full effect).",
    )
    attrition_base_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Base multiplier in grinding attrition: deficit * (factor + inequality)",
    )


class BehavioralDefines(BaseModel):
    """Behavioral economics coefficients."""

    model_config = ConfigDict(frozen=True)

    loss_aversion_lambda: float = Field(
        default=2.25,
        gt=0.0,
        description="Game design: Kahneman-Tversky loss aversion coefficient (empirical ~2.25).",
    )


class TensionDefines(BaseModel):
    """Tension dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    accumulation_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Game design: rate at which tension accumulates from wealth gaps.",
    )
    aspect_flip_threshold: float = Field(
        default=1.0,
        ge=0.0,
        description="Threshold of aspect_balance to trigger an aspect flip.",
    )
    antagonistic_intensity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Intensity threshold where a contradiction becomes antagonistic.",
    )
    resolution_intensity_threshold: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Maximum intensity indicating rupture/resolution.",
    )

    # Lawverian dialectics (Phase C): OppositionRegistry knobs. Kept here on
    # TensionDefines (rather than a new category) because they govern the same
    # contradiction machinery this model already configures.
    rupture_gap_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description=(
            "Principal-opposition gap above which — AND while rising — a RUPTURE "
            "fires. 0.9 keeps the pacified bridged decade (empirical capital_labor "
            "gap band ~[0.03, 0.67]) rupture-free (hegemony holds per project/02 "
            "§3); genuine extreme asymmetry (gap > 0.9) still ruptures. The "
            "rising-gate replaces the old fire-on-hitting-1.0 ceiling."
        ),
    )
    principal_rate_weight: float = Field(
        default=10.0,
        ge=0.0,
        description=(
            "Weight of |rate| in the principal-contradiction score "
            "gap*(1 + rate_weight*|rate|) (Mao: the fast-developing contradiction "
            "leads). Passed to OppositionRegistry; default matches its own."
        ),
    )


class StruggleDefines(BaseModel):
    """Struggle dynamics coefficients (Agency Layer - "George Floyd" Dynamic).

    The Struggle System gives political agency to oppressed classes by modeling:
    - The Spark: State violence (EXCESSIVE_FORCE) triggers insurrection
    - The Combustion: Spark + High Agitation + Low P(S|A) = UPRISING
    - The Result: Uprisings destroy wealth but build solidarity infrastructure

    George Jackson Bifurcation (Power Vacuum):
    When the Comprador becomes insolvent, a power vacuum occurs. The outcome
    depends on the Periphery Proletariat's revolutionary capacity:
    - capacity >= jackson_threshold: Revolutionary Offensive
    - capacity < jackson_threshold: Fascist Revanchism
    """

    model_config = ConfigDict(frozen=True)

    spark_probability_scale: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: base 10% chance scaled by repression_faced for EXCESSIVE_FORCE.",
    )
    resistance_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: minimum agitation level for uprising to trigger.",
    )
    wealth_destruction_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of wealth destroyed during uprising (riot damage).",
    )
    solidarity_gain_per_uprising: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="ΔS = 0.2: Pew Research 2020 George Floyd solidarity shift (20pp white BLM support).",
    )
    consciousness_solidarity_boost: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fraction of solidarity gain that converts to consciousness boost",
    )

    # George Jackson Bifurcation parameters
    jackson_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Game design: revolutionary capacity threshold (org * consciousness) for organized response.",
    )
    revolutionary_agitation_boost: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Game design: agitation boost for periphery proletariat during revolutionary offensive.",
    )
    fascist_identity_boost: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Game design: national identity boost for core workers during fascist turn.",
    )
    fascist_acquiescence_boost: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Game design: acquiescence boost for core workers during fascist turn.",
    )


class AidDefines(BaseModel):
    """AID verb coefficients."""

    aid_efficiency: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of transferred resources that reach the target. "
            "< 1.0 accounts for logistics overhead. "
            "Game Design Knob."
        ),
    )
    aid_cl_cost: float = Field(
        default=0.0,
        description="CL cost for AID. Zero — aid is logistically simple.",
    )
    aid_solidarity_increment: float = Field(
        default=0.15,
        ge=0.0,
        description=(
            "Solidarity accumulated per AID action on the org→target edge. "
            "Accumulates toward solidaristic_threshold. "
            "Game Design Knob."
        ),
    )
    solidaristic_threshold: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Solidarity accumulation required for TRANSACTIONAL → SOLIDARISTIC "
            "transition. At 1.0 with increment 0.15, takes ~7 AID actions. "
            "But also requires education_threshold_for_solidarity to be met."
        ),
    )
    education_threshold_for_solidarity: float = Field(
        default=0.15,
        ge=0.0,
        description=(
            "Minimum education_pressure on a shared community for "
            "TRANSACTIONAL → SOLIDARISTIC transition. "
            "Enforces the 'AID alone is not solidarity' principle. "
            "Without education, the edge stays transactional forever."
        ),
    )
    agitation_relief_per_unit: float = Field(
        default=0.05,
        ge=0.0,
        description=(
            "Agitation reduction per unit of consumption gap closed by AID. "
            "Higher = AID reduces agitation faster = stronger economism risk. "
            "Calibrate: closing 1.0 consumption gap should reduce agitation "
            "by ~0.05 (noticeable but not overwhelming)."
        ),
    )
    economism_warning_threshold: float = Field(
        default=0.1,
        ge=0.0,
        description=(
            "Agitation reduction above which the feedforward displays "
            "an economism warning if education_pressure is below "
            "education_threshold_for_solidarity."
        ),
    )


__all__ = [
    "AidDefines",
    "BehavioralDefines",
    "StruggleDefines",
    "SurvivalDefines",
    "TensionDefines",
    "VitalityDefines",
]
