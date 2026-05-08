"""Game defines for centralized coefficient configuration.

This module provides the GameDefines model which extracts hardcoded values
from systems into a single, configurable location. This enables:
1. Easier calibration of game balance
2. Scenario-specific coefficient overrides
3. Clear documentation of magic numbers

Sprint: Paradox Refactor Phase 1
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CrisisDefines(BaseModel):
    """Crisis and Devaluation Mechanics coefficients (Feature 018).

    Configures the multi-period crisis detector, phased amplification,
    bifurcation risk assessment, and wage compression mechanics.

    See Also:
        :mod:`babylon.economics.tick.types`: CrisisPhase, CrisisState
        ``specs/018-crisis-devaluation-mechanics/spec.md``: FR-023
    """

    model_config = ConfigDict(frozen=True)

    # Crisis detection (FR-001, FR-003)
    crisis_period_ticks: int = Field(
        default=13,
        ge=1,
        le=52,
        description="Game design: ticks per crisis evaluation period (13 = quarterly, prime for desync).",
    )
    r_threshold: float = Field(
        default=0.05,
        gt=0,
        le=1,
        description="Profit rate threshold below which crisis accumulates",
    )
    n_consecutive: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Game design: consecutive below-threshold periods for crisis onset.",
    )
    m_recovery: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Game design: consecutive above-threshold periods for recovery start.",
    )
    r_cap: int = Field(
        default=8,
        ge=1,
        le=52,
        description="Game design: maximum recovery duration (periods).",
    )

    # Hysteresis and wage compression (FR-009, FR-016, FR-017)
    hysteresis_coefficient: float = Field(
        default=0.5,
        gt=0,
        lt=1,
        description="Game design: recovery hysteresis: effective = normal * (1 - h^k).",
    )
    wage_compression_rate: float = Field(
        default=0.02,
        ge=0,
        le=0.5,
        description="Game design: per-period wage compression during DEEP crisis.",
    )
    wage_compression_floor_ratio: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Game design: wage floor as fraction of subsistence (below = accumulation halt).",
    )

    # Bifurcation risk (FR-011 through FR-014)
    bifurcation_solidarity_weight: float = Field(
        default=1.0,
        ge=0,
        description="Game design: weight for solidarity density in bifurcation formula (w_s).",
    )
    bifurcation_burden_weight: float = Field(
        default=1.0,
        ge=0,
        description="Game design: weight for class burden ratio in bifurcation formula (w_b).",
    )
    class_burden_epsilon: float = Field(
        default=0.001,
        gt=0,
        le=0.1,
        description="Engineering: division-by-zero guard for class burden ratio. Must be > 0 and small relative to burden values.",
    )
    bifurcation_event_threshold: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Game design: |score| threshold for BIFURCATION_THRESHOLD event emission.",
    )

    # Dispossession cascade milestones (FR-022)
    dispossession_cascade_milestones: list[float] = Field(
        default=[0.05, 0.10, 0.15],
        description="Game design: LA share decline milestones for DISPOSSESSION_CASCADE events.",
    )
    stagnation_credit_growth: float = Field(
        default=0.01,
        ge=0.0,
        le=0.5,
        description="Credit expansion rate threshold for stagnation phase diagnosis",
    )


class EconomyDefines(BaseModel):
    """Economic system coefficients."""

    model_config = ConfigDict(frozen=True)

    # Imperial rent extraction
    extraction_efficiency: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="α = 0.8: imperial extraction capacity (Amin/Emmanuel unequal exchange theory).",
    )
    comprador_cut: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Fraction of wealth kept by comprador class (prevents Comprador Liquidation)",
    )

    # Production (Material Reality Refactor)
    base_labor_power: float = Field(
        default=1.0,
        ge=0.0,
        description="Base value produced per tick by worker with full biocapacity",
    )

    # Super-wages (PPP Model)
    super_wage_rate: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Fraction of tribute paid as super-wages",
    )
    superwage_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        description="PPP multiplier for labor aristocracy purchasing power",
    )
    superwage_ppp_impact: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much extraction translates to PPP bonus",
    )

    # Imperial rent pool (Dynamic Balance)
    initial_rent_pool: float = Field(
        default=100.0,
        ge=0.0,
        description="Starting imperial rent pool",
    )
    pool_high_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Pool ratio for prosperity mode",
    )
    pool_low_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Pool ratio for austerity mode",
    )
    pool_critical_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Pool ratio for ECONOMIC_CRISIS",
    )

    # Wage bounds
    min_wage_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Minimum super-wage rate during crisis",
    )
    max_wage_rate: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Maximum super-wage rate during prosperity",
    )

    # Client state subsidy (The Iron Lung)
    subsidy_conversion_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Rate at which wealth converts to repression",
    )
    subsidy_trigger_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="P(S|R)/P(S|A) ratio threshold for subsidy",
    )

    # Shadow labor (Department III visibility) - Sprint: Shadow Labor
    shadow_wage_hourly: float = Field(
        default=15.43,
        ge=0.0,
        description="Shadow labor hourly rate (BLS 31-1120 home health aide median, May 2023)",
    )

    # Negligible value thresholds (noise filtering)
    negligible_rent: float = Field(
        default=0.01,
        ge=0.0,
        description="Engineering: noise filter. Rent below this threshold skips event emission to prevent bus saturation.",
    )
    negligible_subsidy: float = Field(
        default=0.01,
        ge=0.0,
        description="Engineering: noise filter. Subsidy below this threshold skips processing to prevent bus saturation.",
    )

    # Entity operational costs (The Calorie Check - must be > 0 to prevent Eden Mode)
    # LINEAR burn: cost = base_subsistence * class_multiplier (not percentage!)
    # Calibrated for 20-year (1040 tick) Hump Shape dynamics:
    #   At 0.0005: C_b burns 0.01/tick, allowing growth phase before metabolic collapse
    base_subsistence: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.5,
        description="Biological floor: fixed cost per tick (LINEAR), scaled by class multiplier",
    )

    # Zombie prevention (Sprint 1.X D2: High-Fidelity State)
    death_threshold: float = Field(
        default=0.001,
        ge=0.0,
        description="Engineering: zombie prevention failsafe. Entities below this wealth threshold are removed to prevent infinite-deficit accumulation.",
    )

    # TRPF Surrogate - Tendency of the Rate of Profit to Fall (Marx, Capital Vol. 3)
    # See ai-docs/epoch2-trpf.yaml for full OCC implementation planned for Epoch 2
    trpf_coefficient: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.01,
        description="Rate at which extraction efficiency declines per tick (TRPF surrogate)",
    )
    rent_pool_decay: float = Field(
        default=0.002,
        ge=0.0,
        le=0.01,
        description="Background evaporation rate of imperial rent pool per tick",
    )

    # Bourgeoisie decision policy deltas (Dynamic Balance - Sprint 3.4.4)
    bribery_wage_delta: float = Field(
        default=0.05,
        ge=-1.0,
        le=1.0,
        description="Wage increase during prosperity (BRIBERY policy)",
    )
    austerity_wage_delta: float = Field(
        default=-0.05,
        ge=-1.0,
        le=1.0,
        description="Wage cut during low pool (AUSTERITY policy)",
    )
    iron_fist_repression_delta: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Repression increase during high tension (IRON_FIST policy)",
    )
    crisis_wage_delta: float = Field(
        default=-0.15,
        ge=-1.0,
        le=1.0,
        description="Emergency wage cut during crisis",
    )
    crisis_repression_delta: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Emergency repression spike during crisis",
    )

    # Tension thresholds for bourgeoisie decisions
    bribery_tension_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Maximum aggregate tension for bribery policy",
    )
    iron_fist_tension_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum aggregate tension for iron fist policy",
    )

    # TRPF efficiency floor
    trpf_efficiency_floor: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum extraction efficiency after TRPF decay",
    )


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


class SolidarityDefines(BaseModel):
    """Solidarity and consciousness transmission coefficients."""

    model_config = ConfigDict(frozen=True)

    scaling_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="= consciousness.sensitivity (k=0.5): solidarity transmission at same scale as material sensitivity.",
    )
    activation_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="p_c ≈ 0.3: network percolation threshold for social graphs with ⟨k⟩ ≈ 3-4.",
    )
    mass_awakening_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Game design: target consciousness for MASS_AWAKENING event.",
    )
    negligible_transmission: float = Field(
        default=0.01,
        ge=0.0,
        description="Engineering: noise filter. Transmissions below this threshold are skipped to prevent O(n^2) edge saturation.",
    )
    superwage_impact: float = Field(
        default=1.0,
        ge=0.0,
        description="Game design: how much imperial extraction affects Core wealth.",
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


class ConsciousnessDefines(BaseModel):
    """Consciousness drift coefficients."""

    model_config = ConfigDict(frozen=True)

    sensitivity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="k = λ/(1-α) = 0.1/0.2: consciousness drift ODE sensitivity. Full consciousness at full exploitation.",
    )
    decay_lambda: float = Field(
        default=0.1,
        gt=0.0,
        description="λ = ln(2)/7 ≈ 0.099: COIN political half-life of 7 weeks (FM 3-24).",
    )
    routing_scale: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="= decay_lambda: agitation→consciousness routing on same 7-week half-life timescale.",
    )
    agitation_decay_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="= decay_lambda: agitation entropy on same 7-week half-life (FM 3-24).",
    )

    # ----- Spec 043: Consciousness Value Integration -----

    exploitation_sensitivity: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Δ(s/v) → agitation conversion. How strongly exploitation rate changes generate crisis energy.",
    )
    rent_decline_sensitivity: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Δ(Φ) → agitation conversion. How strongly imperial rent decline generates crisis in core.",
    )
    reproduction_visibility_coefficient: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Δ(g₃₃) → agitation. How strongly changes in reproductive labor visibility generate crisis.",
    )
    repression_backfire: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Agitation generated from state REPRESS/EXCESSIVE_FORCE events (backfire effect).",
    )
    rent_opacity_factor: float = Field(
        default=1.0,
        ge=0.0,
        description="How much imperial rent (Φ) dampens exploitation visibility. Higher = more obscured.",
    )
    agitation_consumption_rate: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Fraction of agitation consumed per tick by ternary routing.",
    )
    liberal_drift_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Per-tick drift toward liberal (l) tendency under stable material conditions.",
    )
    educate_base_effect: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Base education_pressure increase per EDUCATE verb invocation.",
    )
    agitation_education_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Agitation level at which EDUCATE reaches full effectiveness (practice-first gate).",
    )
    education_pressure_decay: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Per-tick exponential decay of education_pressure on community hyperedges.",
    )


class TerritoryDefines(BaseModel):
    """Territory dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    heat_decay_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="= decay_lambda: heat entropy on same 7-week half-life (FM 3-24).",
    )
    high_profile_heat_gain: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="= rent_spike × heat_decay = 1.5 × 0.1: FM 3-24 clear-phase convergence in 6-8 weeks.",
    )
    eviction_heat_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="= α (extraction_efficiency): eviction triggers at full extraction capacity.",
    )
    rent_spike_multiplier: float = Field(
        default=1.5,
        gt=0.0,
        description="1.5×: Census/HUD gentrification rent premium (UCLA Urban Displacement Project).",
    )
    displacement_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Population displacement during eviction",
    )
    heat_spillover_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="= heat_decay_rate / 2: ink-spot spillover at half the decay rate.",
    )
    clarity_profile_coefficient: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Clarity bonus for HIGH_PROFILE territories",
    )
    concentration_camp_decay_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Population decay rate in CONCENTRATION_CAMP territories (elimination)",
    )

    # Displacement Priority Mode (Sprint 3.7.1: Dynamic Displacement Routing)
    # Stored as string for YAML compatibility, converted to enum at runtime
    displacement_priority_mode: str = Field(
        default="EXTRACTION",
        description="Sink routing mode: EXTRACTION (prison first), CONTAINMENT (reservation first), ELIMINATION (camp first)",
    )

    # AUTO mode thresholds (Sprint 3.7.1 - reserved for future use)
    elimination_rent_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Imperial rent ratio below which ELIMINATION mode activates",
    )
    elimination_tension_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Tension threshold above which ELIMINATION mode activates",
    )
    containment_rent_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Imperial rent ratio below which CONTAINMENT mode activates",
    )
    containment_tension_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Tension threshold above which CONTAINMENT mode activates",
    )


class TopologyDefines(BaseModel):
    """Phase transition coefficients for solidarity network analysis.

    The topology system tracks phase transitions in class solidarity:
    - Gaseous: Atomized, no collective action capacity
    - Transitional: Solidarity building, weak ties forming
    - Liquid: Mass movement (percolation but low cadre density)
    - Solid: Vanguard party (percolation with high cadre density)
    """

    model_config = ConfigDict(frozen=True)

    gaseous_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: percolation ratio below this = atomized (no collective action).",
    )
    condensation_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: percolation ratio for phase transition (gaseous→liquid/solid).",
    )
    vanguard_density_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: cadre density threshold for vanguard party (liquid→solid).",
    )
    brittle_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Game design: potential > actual * this = brittle network (fragile solidarity).",
    )
    solidarity_sympathizer_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: minimum SOLIDARITY edge strength for sympathizer classification.",
    )
    solidarity_cadre_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: minimum SOLIDARITY edge strength for cadre classification.",
    )
    resilience_removal_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of nodes removed during resilience test (default 20%).",
    )
    resilience_survival_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Game design: L_max must survive at this fraction of original after removal.",
    )


class MetabolismDefines(BaseModel):
    """Metabolic rift coefficients (Slice 1.4 - Ecological Limits).

    The Metabolism System tracks the widening rift between extraction and regeneration:
    - Biocapacity regeneration and depletion
    - ECOLOGICAL_OVERSHOOT event when consumption exceeds biocapacity
    """

    model_config = ConfigDict(frozen=True)

    entropy_factor: float = Field(
        default=1.2,
        gt=1.0,
        le=3.0,
        description="Game design: extraction costs more than it yields (thermodynamic inefficiency).",
    )
    overshoot_threshold: float = Field(
        default=1.0,
        gt=0.0,
        le=2.0,
        description="Game design: consumption/biocapacity ratio triggering ECOLOGICAL_OVERSHOOT.",
    )
    max_overshoot_ratio: float = Field(
        default=999.0,
        gt=0.0,
        description="Engineering: overflow cap. Prevents division-by-near-zero when biocapacity approaches 0.",
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


class CarceralDefines(BaseModel):
    """Carceral equilibrium coefficients (Terminal Crisis Dynamics).

    The carceral system models the transition from wage suppression to
    outright incarceration as the imperial rent pool exhausts:

    1. SUPERWAGE_CRISIS: Rent pool can't sustain LA wages
    2. CLASS_DECOMPOSITION: LA splits into enforcers + prisoners
    3. CONTROL_RATIO_CRISIS: Prisoners exceed control capacity
    4. TERMINAL_DECISION: Revolution vs genocide based on organization

    Real-world staffing ratios (sources: BJS, Marshall Project 2024):
    - 1:1 = Maximum control (Massachusetts, best-staffed)
    - 4:1 = US national jail average (2022)
    - 15:1 = Federal DOJ theoretical baseline
    - 200:1 = Crisis/collapse (Georgia, 2024)

    With 70/30 decomposition, prisoner/enforcer = 2.33:1, so:
    - control_capacity <= 2: Crisis triggers immediately
    - control_capacity >= 3: No crisis (stable carceral state)
    """

    model_config = ConfigDict(frozen=True)

    control_capacity: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Game design: prisoners one enforcer can control (1:N). US average ~4, crisis >15.",
    )
    enforcer_fraction: float = Field(
        default=0.15,
        ge=0.05,
        le=0.50,
        description="Game design: after SUPERWAGE_CRISIS: % of former LA who BECOME guards/cops.",
    )
    proletariat_fraction: float = Field(
        default=0.85,
        ge=0.50,
        le=0.95,
        description="Game design: after SUPERWAGE_CRISIS: % of former LA who BECOME prisoners.",
    )
    revolution_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: average prisoner organization threshold for revolution (vs genocide).",
    )

    # Phase staggering delays (ticks) - ensures temporal separation between phases
    decomposition_delay: int = Field(
        default=52,
        ge=0,
        le=520,
        description="Game design: ticks to wait after SUPERWAGE_CRISIS before CLASS_DECOMPOSITION (1 year default).",
    )
    control_ratio_delay: int = Field(
        default=52,
        ge=0,
        le=520,
        description="Game design: ticks to wait after CLASS_DECOMPOSITION before checking control ratio (1 year default).",
    )
    terminal_decision_delay: int = Field(
        default=1,
        ge=0,
        le=52,
        description="Game design: ticks to wait after CONTROL_RATIO_CRISIS before TERMINAL_DECISION.",
    )


class EndgameDefines(BaseModel):
    """Configuration for endgame detection thresholds (Slice 1.6).

    The EndgameDetector monitors WorldState for three possible game endings:

    1. REVOLUTIONARY_VICTORY: percolation >= threshold AND consciousness > threshold
       The masses have achieved critical organization AND ideological clarity.

    2. ECOLOGICAL_COLLAPSE: overshoot_ratio > threshold for N consecutive ticks
       Sustained ecological overshoot leads to irreversible collapse.

    3. FASCIST_CONSOLIDATION: national_identity > class_consciousness for M+ nodes
       Fascist ideology has captured the majority of the population.

    Attributes:
        revolutionary_percolation_threshold: Minimum percolation ratio (0.7 = 70%
            of nodes in giant solidarity component) for revolutionary victory.
        revolutionary_consciousness_threshold: Minimum average class consciousness
            (0.8 = 80% ideological clarity) for revolutionary victory.
        ecological_overshoot_threshold: Consumption/biocapacity ratio above which
            ecological damage accumulates (2.0 = consuming 2x biocapacity).
        ecological_sustained_ticks: Number of consecutive ticks overshoot must
            persist before triggering ECOLOGICAL_COLLAPSE (5 ticks).
        fascist_majority_threshold: Minimum number of nodes where national_identity
            exceeds class_consciousness for FASCIST_CONSOLIDATION (3 nodes).
    """

    model_config = ConfigDict(frozen=True)

    revolutionary_percolation_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Game design: percolation ratio threshold for revolutionary victory (70%).",
    )
    revolutionary_consciousness_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Game design: average consciousness threshold for revolutionary victory (80%).",
    )
    ecological_overshoot_threshold: float = Field(
        default=2.0,
        gt=0.0,
        description="Game design: overshoot ratio threshold for ecological collapse tracking.",
    )
    ecological_sustained_ticks: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Game design: consecutive ticks of overshoot before collapse triggers.",
    )
    fascist_majority_threshold: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Game design: minimum nodes with national_identity > class_consciousness.",
    )


class InitialDefines(BaseModel):
    """Initial condition coefficients."""

    model_config = ConfigDict(frozen=True)

    worker_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for periphery worker",
    )
    owner_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for core owner",
    )
    default_population: int = Field(
        default=1,
        ge=1,
        description="Game design: default population for test entities. pop=1 ensures per-capita survival mechanics are tested without large denominators masking issues.",
    )


class PrecisionDefines(BaseModel):
    """Numerical precision configuration for deterministic simulation.

    Epoch 0 Physics Hardening:
    - All floating-point values snap to a 10^-n grid (default n=6)
    - This prevents drift accumulation over long simulations (100+ years)
    - ROUND_HALF_UP ensures deterministic cross-platform behavior

    The Gatekeeper Pattern: Quantization is applied at TYPE level
    (Pydantic AfterValidator), NOT inside formulas.

    Note: Increased from 5 to 6 decimal places for 100-year (5200 tick)
    Carceral Equilibrium simulations to reduce cumulative rounding errors.
    """

    model_config = ConfigDict(frozen=True)

    decimal_places: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Engineering: quantization grid precision (10^-n). Structurally determined by IEEE 754 float64 and 5200-tick simulation horizon.",
    )
    rounding_mode: str = Field(
        default="ROUND_HALF_UP",
        description="Rounding mode for quantization.",
    )
    epsilon: float = Field(
        default=1e-9,
        gt=0.0,
        le=1e-3,
        description="Engineering: division-by-zero guard. Must satisfy epsilon < 10^-decimal_places to stay below quantization grid.",
    )
    comparison_epsilon: float = Field(
        default=1e-10,
        gt=0.0,
        le=1e-6,
        description="Engineering: float equality tolerance for deterministic test assertions. Must be < epsilon to detect precision violations.",
    )


class ArcGISDefines(BaseModel):
    """ArcGIS organization and host configuration for external data sources.

    Different federal agencies host HIFLD and infrastructure data on various
    ArcGIS organizations. This configuration centralizes the organization IDs
    and hosts to allow easy updates when services migrate.

    Current organization mapping (as of 2024):
    - FEMA RAPT: Prison Boundaries, Law Enforcement (services.arcgis.com)
    - Esri US Federal: MIRTA Military Installations (services2.arcgis.com)
    - HIFLD Legacy: Some services still work (services1.arcgis.com)
    """

    model_config = ConfigDict(frozen=True)

    # FEMA RAPT (Resilience Analysis and Planning Tool) - primary HIFLD source
    fema_rapt_org: str = Field(
        default="XG15cJAlne2vxtgt",
        description="FEMA RAPT organization ID on ArcGIS",
    )
    fema_rapt_host: str = Field(
        default="services.arcgis.com",
        description="FEMA RAPT ArcGIS host domain",
    )

    # Esri US Federal Data - MIRTA military installations
    esri_federal_org: str = Field(
        default="FiaPA4ga0iQKduv3",
        description="Esri US Federal Data organization ID",
    )
    esri_federal_host: str = Field(
        default="services2.arcgis.com",
        description="Esri US Federal Data host domain",
    )

    # Legacy HIFLD organization (some services still work)
    hifld_legacy_org: str = Field(
        default="Hp6G80Pky0om7QvQ",
        description="Legacy HIFLD organization ID",
    )
    hifld_legacy_host: str = Field(
        default="services1.arcgis.com",
        description="Legacy HIFLD host domain",
    )


class ServicesDefines(BaseModel):
    """ArcGIS FeatureServer service names and layers.

    Service names can be overridden for testing or alternative data sources.
    Layer numbers are important as some services (like Prison_Boundaries)
    have data on non-default layers.
    """

    model_config = ConfigDict(frozen=True)

    # Prison Boundaries (FEMA RAPT)
    prison_boundaries: str = Field(
        default="Prison_Boundaries_RAPT",
        description="Prison Boundaries service name",
    )
    prison_boundaries_layer: int = Field(
        default=1,
        ge=0,
        description="Prison Boundaries layer (Note: Layer 1, not 0)",
    )

    # Law Enforcement (FEMA RAPT)
    law_enforcement: str = Field(
        default="Local_Law_Enforcement_Locations_RAPT",
        description="Law enforcement locations service name",
    )
    law_enforcement_layer: int = Field(
        default=0,
        ge=0,
        description="Law enforcement layer",
    )

    # MIRTA (Esri US Federal)
    mirta_polygons: str = Field(
        default="MIRTA_Polygons_A_view",
        description="MIRTA military installations service name",
    )
    mirta_layer: int = Field(
        default=0,
        ge=0,
        description="MIRTA layer",
    )

    # Electric Grid (Legacy HIFLD)
    electric_transmission: str = Field(
        default="Electric_Power_Transmission_Lines",
        description="Electric transmission lines service name",
    )
    electric_transmission_layer: int = Field(
        default=0,
        ge=0,
        description="Electric transmission layer",
    )


class ExternalDataDefines(BaseModel):
    """External data source configuration.

    Centralizes ArcGIS organization IDs, hosts, and service names for
    HIFLD and related infrastructure data sources. This enables:
    1. Easy updates when services migrate between organizations
    2. Testing with alternative data sources
    3. Clear documentation of data source provenance
    """

    model_config = ConfigDict(frozen=True)

    arcgis: ArcGISDefines = Field(default_factory=ArcGISDefines)
    services: ServicesDefines = Field(default_factory=ServicesDefines)

    def build_service_url(
        self,
        host: str,
        org: str,
        service: str,
        layer: int = 0,
    ) -> str:
        """Build a complete ArcGIS FeatureServer URL.

        Args:
            host: ArcGIS host domain (e.g., "services.arcgis.com")
            org: Organization ID (e.g., "XG15cJAlne2vxtgt")
            service: Service name (e.g., "Prison_Boundaries_RAPT")
            layer: Layer number (default 0)

        Returns:
            Complete FeatureServer URL
        """
        return f"https://{host}/{org}/arcgis/rest/services/{service}/FeatureServer/{layer}"

    def prison_boundaries_url(self) -> str:
        """Get the Prison Boundaries FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.fema_rapt_host,
            org=self.arcgis.fema_rapt_org,
            service=self.services.prison_boundaries,
            layer=self.services.prison_boundaries_layer,
        )

    def law_enforcement_url(self) -> str:
        """Get the Law Enforcement Locations FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.fema_rapt_host,
            org=self.arcgis.fema_rapt_org,
            service=self.services.law_enforcement,
            layer=self.services.law_enforcement_layer,
        )

    def mirta_url(self) -> str:
        """Get the MIRTA Military Installations FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.esri_federal_host,
            org=self.arcgis.esri_federal_org,
            service=self.services.mirta_polygons,
            layer=self.services.mirta_layer,
        )

    def electric_transmission_url(self) -> str:
        """Get the Electric Transmission Lines FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.hifld_legacy_host,
            org=self.arcgis.hifld_legacy_org,
            service=self.services.electric_transmission,
            layer=self.services.electric_transmission_layer,
        )


class TimescaleDefines(BaseModel):
    """Simulation timescale configuration for weekly ticks.

    Epoch 0 Physics Hardening:
    - 1 tick = 7 days (weekly resolution)
    - 52 weeks = 1 year (for annual rate conversions)

    This is critical for:
    - Economic flow rates (annual -> per-tick conversion)
    - Historical pacing (events per game year)
    - UI display (showing dates/weeks)

    All annual rates (wage_rate, extraction_efficiency) are divided by
    weeks_per_year to get per-tick rates.
    """

    model_config = ConfigDict(frozen=True)

    tick_duration_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Engineering: physical constant. 7 days/week is a calendar invariant, not a tunable parameter.",
    )
    weeks_per_year: int = Field(
        default=52,
        ge=1,
        description="Engineering: physical constant. 52 weeks/year for annual-to-tick rate conversion.",
    )

    @property
    def ticks_per_year(self) -> int:
        """Number of ticks per simulation year.

        Since 1 tick = 1 week, this equals weeks_per_year.
        """
        return self.weeks_per_year

    @property
    def days_per_year(self) -> int:
        """Days per simulation year (ticks * days_per_tick).

        With defaults: 7 * 52 = 364 days (close to actual 365-366).
        """
        return self.tick_duration_days * self.weeks_per_year


class ContradictionFieldDefines(BaseModel):
    """Contradiction field topology coefficients (Feature 002).

    Configures normalization bounds, history window depth, and transition
    thresholds for the dialectical field topology systems.

    See Also:
        ``specs/002-dialectical-field-topology/spec.md``: FR-001 through FR-019
    """

    model_config = ConfigDict(frozen=True)

    # Normalization bounds (FR-001, EC-007)
    field_min: float = Field(
        default=0.0,
        ge=0.0,
        description="Game design: minimum normalized field value.",
    )
    field_max: float = Field(
        default=10.0,
        gt=0.0,
        description="Game design: maximum normalized field value.",
    )

    # History window for temporal derivatives (FR-006)
    history_window: int = Field(
        default=3,
        ge=2,
        le=10,
        description="Game design: rolling tick window for temporal derivative computation.",
    )

    # Curvature parameters (FR-005, R-004)
    curvature_alpha: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Self-loop weight for Ollivier-Ricci probability measures",
    )

    # CO-OPTIVE mechanics (FR-014 through FR-017)
    co_optive_suppression_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of df/dt suppressed by CO-OPTIVE edges.",
    )
    latent_release_multiplier: float = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
        description="Game design: multiplier applied to released latent contradictions.",
    )

    # Transition thresholds (FR-010)
    default_transition_priority: int = Field(
        default=0,
        ge=0,
        description="Game design: default priority for transitions without explicit priority.",
    )


class ReserveArmyDefines(BaseModel):
    """Reserve army of labor coefficients (Feature 021, FR-001/FR-002).

    Configures the bounded sigmoid that maps reserve_ratio to wage pressure.
    Higher reserve ratios produce stronger downward pressure on wages.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-001, FR-002, FR-003
    """

    model_config = ConfigDict(frozen=True)

    # Sigmoid parameters for wage pressure function
    sigmoid_k: float = Field(
        default=20.0,
        gt=0.0,
        le=100.0,
        description="Sigmoid steepness for reserve_ratio -> wage_pressure mapping",
    )
    sigmoid_r0: float = Field(
        default=0.08,
        gt=0.0,
        le=1.0,
        description="Reserve ratio at sigmoid midpoint (inflection point)",
    )

    # Saturation ceiling for wage pressure
    wage_pressure_ceiling: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Maximum wage pressure coefficient (prevents total wage elimination)",
    )

    # Flow clamping
    min_employed_fraction: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Minimum fraction of labor force that must remain employed",
    )


class DispossessionDefines(BaseModel):
    """Dispossession event intensity weights (Feature 021, FR-004/FR-005).

    Configures the relative weight of each dispossession type when computing
    aggregate territory-level dispossession intensity.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-004, FR-005, FR-006
    """

    model_config = ConfigDict(frozen=True)

    # Intensity weights per dispossession type (must sum to ~1.0)
    weight_foreclosure: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Game design: weight for foreclosure events."
    )
    weight_eviction: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Game design: weight for eviction events."
    )
    weight_displacement: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Game design: weight for gentrification displacement events.",
    )
    weight_tax_sale: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Game design: weight for tax sale events."
    )
    weight_eminent_domain: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Game design: weight for eminent domain events.",
    )
    weight_wage_theft: float = Field(
        default=0.03, ge=0.0, le=1.0, description="Game design: weight for wage theft events."
    )
    weight_incarceration_seizure: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="Game design: weight for incarceration-related seizure events.",
    )
    weight_pension_default: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Game design: weight for pension default events.",
    )

    # Deadweight loss fraction for value transfers
    deadweight_loss_fraction: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of transferred value lost as deadweight (not received by anyone).",
    )
    transfer_scale: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Scale factor for wealth transfer amount: territory_wealth * intensity * scale",
    )


class WorkingDayDefines(BaseModel):
    """Working day characterization thresholds (Feature 021, FR-007/FR-008).

    Configures the threshold values for classifying territory-sector pairs
    by their dominant mode of surplus value extraction.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-007, FR-008, FR-011
    """

    model_config = ConfigDict(frozen=True)

    # Hours thresholds for exploitation mode classification
    absolute_hours_threshold: float = Field(
        default=45.0,
        gt=0.0,
        le=168.0,
        description="Game design: weekly hours above which exploitation is ABSOLUTE_DOMINANT.",
    )
    relative_hours_threshold: float = Field(
        default=40.0,
        gt=0.0,
        le=168.0,
        description="Game design: weekly hours at or below which exploitation may be RELATIVE_DOMINANT.",
    )

    # Intensity thresholds for exploitation mode classification
    intensity_threshold_high: float = Field(
        default=1.2,
        gt=0.0,
        description="Game design: labor intensity above which exploitation is RELATIVE_DOMINANT (with low hours).",
    )
    intensity_threshold_low: float = Field(
        default=1.1,
        gt=0.0,
        description="Game design: labor intensity below which exploitation is ABSOLUTE_DOMINANT (with high hours).",
    )

    # Visibility modifiers for consciousness dynamics
    absolute_visibility: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Game design: consciousness visibility modifier for ABSOLUTE exploitation.",
    )
    relative_visibility: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Game design: consciousness visibility modifier for RELATIVE exploitation.",
    )


class CommunityDefines(BaseModel):
    """Hypergraph community layer coefficients (Feature 022).

    Controls alpha-smoothing decay rates for community state,
    solidarity potential computation bonuses and penalties,
    and infrastructure maintenance parameters.
    """

    model_config = ConfigDict(frozen=True)

    # Alpha-smoothing decay rates (per tick)
    heat_decay_alpha: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Game design: rate at which community heat decays toward 0 without provocation.",
    )
    cohesion_decay_alpha: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="Game design: rate at which cohesion decays without organizing work.",
    )
    infrastructure_decay_alpha: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="Game design: rate at which infrastructure decays without maintenance.",
    )

    # Solidarity potential coefficients
    community_overlap_bonus: float = Field(
        default=0.1,
        ge=0.0,
        description="Game design: solidarity potential bonus per shared community membership.",
    )
    rent_differential_penalty: float = Field(
        default=0.05,
        ge=0.0,
        description="Game design: solidarity potential penalty per unit of imperial rent differential.",
    )

    # Infrastructure maintenance
    core_organizer_maintenance_factor: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: infrastructure maintenance contribution per CORE_ORGANIZER member.",
    )


class ClassDynamicsDefines(BaseModel):
    """Class dynamics coefficients (FRED DFA-derived, Feature 016).

    Parameters fitted to FRED Distributional Financial Accounts (2015-2025)
    for class wealth flow dynamics.
    """

    model_config = ConfigDict(frozen=True)

    alpha_21: float = Field(
        default=0.0006,
        ge=0.0,
        le=0.01,
        description="Extraction rate from petty bourgeoisie to bourgeoisie (quarterly)",
    )
    gamma_3: float = Field(
        default=0.0057,
        ge=0.0,
        le=0.1,
        description="Imperial rent formation rate — superwages to core workers (quarterly)",
    )
    equilibrium_w1: float = Field(
        default=0.305,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 1 (bourgeoisie)",
    )
    equilibrium_w2: float = Field(
        default=0.382,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 2 (petty bourgeoisie)",
    )
    equilibrium_w3: float = Field(
        default=0.294,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 3 (proletariat)",
    )
    equilibrium_w4: float = Field(
        default=0.020,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 4 (lumpenproletariat)",
    )

    # --- Extraction rates (FRED DFA-fitted, per quarter) ---
    alpha_41: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: proletariat -> bourgeoisie extraction rate (quarterly)",
    )
    alpha_31: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: labor aristocracy -> bourgeoisie extraction rate (quarterly)",
    )
    alpha_32: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: labor aristocracy -> petty bourgeoisie extraction rate (quarterly)",
    )
    alpha_42: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: proletariat -> petty bourgeoisie extraction rate (quarterly)",
    )
    alpha_43: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: proletariat -> labor aristocracy extraction rate (quarterly)",
    )

    # --- Redistribution rates (FRED DFA-fitted) ---
    delta_1: float = Field(
        default=0.0010,
        ge=0.0,
        le=0.1,
        description="FRED DFA-fitted: redistribution from bourgeoisie (taxation, quarterly)",
    )
    delta_2: float = Field(
        default=0.0020,
        ge=0.0,
        le=0.1,
        description="FRED DFA-fitted: redistribution from petty bourgeoisie (quarterly)",
    )
    delta_3: float = Field(
        default=0.0010,
        ge=0.0,
        le=0.1,
        description="FRED DFA-fitted: redistribution from labor aristocracy (quarterly)",
    )

    # --- Damping coefficients (game design, negative = mean-reverting) ---
    beta_1: float = Field(
        default=-0.10,
        ge=-1.0,
        le=0.0,
        description="Game design: bourgeoisie damping coefficient",
    )
    beta_2: float = Field(
        default=-0.15,
        ge=-1.0,
        le=0.0,
        description="Game design: petty bourgeoisie damping coefficient",
    )
    beta_3: float = Field(
        default=-0.10,
        ge=-1.0,
        le=0.0,
        description="Game design: labor aristocracy damping coefficient",
    )
    beta_4: float = Field(
        default=-0.05,
        ge=-1.0,
        le=0.0,
        description="Game design: proletariat damping coefficient",
    )

    # --- Oscillation frequencies (game design, strictly positive) ---
    omega_1: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="Game design: bourgeoisie oscillation frequency",
    )
    omega_2: float = Field(
        default=0.08,
        gt=0.0,
        le=1.0,
        description="Game design: petty bourgeoisie oscillation frequency",
    )
    omega_3: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="Game design: labor aristocracy oscillation frequency",
    )
    omega_4: float = Field(
        default=0.03,
        gt=0.0,
        le=1.0,
        description="Game design: proletariat oscillation frequency",
    )


class LifecycleDefines(BaseModel):
    """D-P-D' Lifecycle Circuit coefficients (Feature 030).

    36 tunable parameters for intergenerational class reproduction.
    All defaults have documented provenance (CDC, Census, Chetty, etc.).

    The legitimation weight ranking is a design invariant reflecting
    authorial political judgment; individual values are tunable but the
    ordinal ranking is not.

    See Also:
        ``specs/030-dpd-lifecycle-circuit/data-model.md``: Full provenance table.
    """

    model_config = ConfigDict(frozen=True)

    # --- Population rates (CDC NVSS, Census) ---
    birth_rate: float = Field(
        default=0.0107,
        ge=0.0,
        le=1.0,
        description="CDC NVSS 2023: births per P-phase person per tick.",
    )
    rate_d_to_p: float = Field(
        default=0.0556,
        ge=0.0,
        le=1.0,
        description="Census: 1/18 years average D-to-P transition.",
    )
    rate_p_to_d_prime: float = Field(
        default=0.0213,
        ge=0.0,
        le=1.0,
        description="Census: 1/47 years average P-to-D' transition.",
    )
    rate_d_prime_to_death: float = Field(
        default=0.039,
        ge=0.0,
        le=1.0,
        description="CDC WONDER + Census 2023: D' annual mortality.",
    )

    # --- Initial population fractions (Census 2024) ---
    initial_pop_d_frac: float = Field(
        default=0.215,
        ge=0.0,
        le=1.0,
        description="Census 2024: initial D phase fraction.",
    )
    initial_pop_p_frac: float = Field(
        default=0.605,
        ge=0.0,
        le=1.0,
        description="Census 2024: initial P phase fraction.",
    )
    initial_pop_d_prime_frac: float = Field(
        default=0.180,
        ge=0.0,
        le=1.0,
        description="Census 2024: initial D' phase fraction.",
    )

    # --- Legitimation component defaults ---
    pension_coverage_rate: float = Field(
        default=0.73,
        ge=0.0,
        le=1.0,
        description="BLS NCS 2024: fraction of P-phase with pension access.",
    )
    home_ownership_rate: float = Field(
        default=0.656,
        ge=0.0,
        le=1.0,
        description="Census 2024: P-phase home ownership rate.",
    )
    ss_replacement_rate: float = Field(
        default=0.426,
        ge=0.0,
        le=1.0,
        description="SSA 2024: Social Security replacement ratio.",
    )
    healthcare_security: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Estimated composite: fraction with secure D' healthcare.",
    )
    retirement_confidence: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="EBRI RCS survey: subjective D' security assessment.",
    )

    # --- Legitimation weights (political judgment, rank-ordered) ---
    legit_w_home_ownership: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Political judgment (rank 1): home ownership weight.",
    )
    legit_w_healthcare_security: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Political judgment (rank 2): healthcare security weight.",
    )
    legit_w_retirement_confidence: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Political judgment (rank 3): retirement confidence weight.",
    )
    legit_w_pension_coverage: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Political judgment (rank 4): pension coverage weight.",
    )
    legit_w_ss_replacement: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Political judgment (rank 5): SS replacement weight.",
    )

    # --- Legitimation thresholds ---
    legitimation_blend_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Structural vs agitation blend weight for bifurcation feed.",
    )
    legitimation_crisis_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="FR-006: legitimation index below this is CRISIS.",
    )
    legitimation_unstable_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="FR-006: legitimation index below this is UNSTABLE.",
    )

    # --- Inheritance parameters ---
    pareto_alpha: float = Field(
        default=1.5,
        gt=0.0,
        le=10.0,
        description="Fed SCF: Pareto shape parameter for wealth distribution.",
    )
    care_cost_fraction: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Fraction of D' wealth consumed by end-of-life care.",
    )

    # --- Chetty Opportunity Atlas mobility parameters ---
    mobility_base_rate: float = Field(
        default=0.445,
        ge=0.0,
        le=1.0,
        description="Chetty KFR pooled at P25.",
    )
    mobility_base_rate_p75: float = Field(
        default=0.580,
        ge=0.0,
        le=1.0,
        description="Chetty KFR pooled at P75.",
    )
    mobility_racial_gap: float = Field(
        default=0.134,
        ge=0.0,
        le=1.0,
        description="Chetty Black-White KFR gap at P25.",
    )
    # These exceed [0,1] — use float with explicit bounds
    carceral_transition_modifier: float = Field(
        default=2.8,
        ge=0.0,
        le=10.0,
        description="Chetty: incarceration rate multiplier on P→D' transition.",
    )
    early_mortality_modifier: float = Field(
        default=1.24,
        ge=0.0,
        le=10.0,
        description="Chetty: premature death multiplier on P→D' transition.",
    )

    # --- Chetty Table 8 covariate defaults ---
    baseline_gini: float = Field(
        default=0.485,
        ge=0.0,
        le=1.0,
        description="Chetty Table 8: national median Gini.",
    )
    poverty_share: float = Field(
        default=0.126,
        ge=0.0,
        le=1.0,
        description="Chetty Table 8: national average poverty share.",
    )
    employment_rate: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Chetty Table 8: national average employment rate.",
    )
    single_parent_fraction: float = Field(
        default=0.234,
        ge=0.0,
        le=1.0,
        description="Chetty Table 8: national average single-parent fraction.",
    )
    college_rate: float = Field(
        default=0.33,
        ge=0.0,
        le=1.0,
        description="Chetty Table 8: national average college graduation rate.",
    )

    # --- Ideology transmission ---
    ideology_caregiver_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="FR-009: caregiver influence weight in D→P ideology transmission.",
    )
    ideology_institutional_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="FR-009: institutional hegemony weight in D→P ideology transmission.",
    )
    ideology_regression_coefficient: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="FR-009: regression toward mean strength for ideology.",
    )

    # --- Dual circuit interference ---
    sandwich_squeeze_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=10.0,
        description="FR-022: dependency ratio threshold for sandwich squeeze.",
    )

    @model_validator(mode="after")
    def _validate_invariants(self) -> LifecycleDefines:
        """Validate sum constraints, weight ranking, and threshold ordering."""
        # Population fractions sum to ~1.0
        pop_sum = self.initial_pop_d_frac + self.initial_pop_p_frac + self.initial_pop_d_prime_frac
        if abs(pop_sum - 1.0) > 0.01:
            msg = f"Initial population fractions must sum to 1.0 (got {pop_sum:.4f})"
            raise ValueError(msg)

        # Legitimation weights sum to ~1.0
        weight_sum = (
            self.legit_w_home_ownership
            + self.legit_w_healthcare_security
            + self.legit_w_retirement_confidence
            + self.legit_w_pension_coverage
            + self.legit_w_ss_replacement
        )
        if abs(weight_sum - 1.0) > 0.01:
            msg = f"Legitimation weights must sum to 1.0 (got {weight_sum:.4f})"
            raise ValueError(msg)

        # Legitimation weight ranking invariant (political judgment)
        if not (
            self.legit_w_home_ownership
            >= self.legit_w_healthcare_security
            >= self.legit_w_retirement_confidence
            >= self.legit_w_pension_coverage
            >= self.legit_w_ss_replacement
        ):
            msg = (
                "Legitimation weight ranking violated: "
                "home_ownership >= healthcare >= retirement_confidence >= pension >= ss_replacement"
            )
            raise ValueError(msg)

        # Ideology weights sum to ~1.0
        ideology_sum = self.ideology_caregiver_weight + self.ideology_institutional_weight
        if abs(ideology_sum - 1.0) > 0.01:
            msg = f"Ideology weights must sum to 1.0 (got {ideology_sum:.4f})"
            raise ValueError(msg)

        # Crisis threshold < unstable threshold
        if self.legitimation_crisis_threshold >= self.legitimation_unstable_threshold:
            msg = (
                f"Crisis threshold ({self.legitimation_crisis_threshold}) must be < "
                f"unstable threshold ({self.legitimation_unstable_threshold})"
            )
            raise ValueError(msg)

        # Mobility P25 <= P75
        if self.mobility_base_rate > self.mobility_base_rate_p75 + 0.001:
            msg = (
                f"mobility_base_rate ({self.mobility_base_rate}) > "
                f"mobility_base_rate_p75 ({self.mobility_base_rate_p75})"
            )
            raise ValueError(msg)

        return self


class OrganizationDefines(BaseModel):
    """Organization system tunable coefficients (Feature 031).

    14 parameters controlling consciousness effects, intelligence methodology
    ceilings, cohesion mechanics, credibility defaults, and capacity factors.

    See Also:
        ``specs/031-organization-base-model/data-model.md``: Full provenance table.
    """

    model_config = ConfigDict(frozen=True)

    # --- Lifecycle capacity ---
    elder_capacity_factor: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="BLS 65+ LFPR: D'-phase capacity scalar.",
    )

    # --- Consciousness tendency modifiers ---
    tendency_modifier_revolutionary: float = Field(
        default=0.15,
        ge=-1.0,
        le=1.0,
        description="Game design: CI delta multiplier for REVOLUTIONARY tendency.",
    )
    tendency_modifier_liberal: float = Field(
        default=-0.05,
        ge=-1.0,
        le=1.0,
        description="Game design: CI delta multiplier for LIBERAL tendency.",
    )
    tendency_modifier_fascist: float = Field(
        default=0.10,
        ge=-1.0,
        le=1.0,
        description="Game design: tendency pressure multiplier for FASCIST tendency.",
    )

    # --- Intelligence observation ceilings (Sparrow calibration) ---
    observation_ceiling_local_pd: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Sparrow calibration: Local PD observation ceiling.",
    )
    observation_ceiling_fusion: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Sparrow calibration: Fusion center observation ceiling.",
    )
    observation_ceiling_fbi: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Sparrow calibration: FBI observation ceiling.",
    )

    # --- Cohesion mechanics ---
    cohesion_loss_per_key_figure: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Game design: cohesion drop per key figure removal.",
    )
    min_cohesion_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Game design: floor cohesion (never reaches zero).",
    )

    # --- Credibility defaults ---
    credibility_default_faction: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: default PoliticalFaction credibility.",
    )
    credibility_sovereign: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Game design: SOVEREIGN legal standing credibility.",
    )
    credibility_chartered: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Game design: CHARTERED legal standing credibility.",
    )
    credibility_default_state: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: StateApparatus fallthrough credibility (non-SOVEREIGN, non-CHARTERED).",
    )

    # --- Capacity defaults (pending Phase 2/3 attention threads) ---
    violence_capacity_default: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: default StateApparatus violence capacity.",
    )
    surveillance_capacity_default: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Game design: default StateApparatus surveillance capacity.",
    )


class EdgeTransitionDefines(BaseModel):
    """Edge mode transition threshold values (Feature 002, FR-010).

    Configures the threshold values used in predicate conditions
    that determine when edges transition between modes (EXTRACTIVE,
    TRANSACTIONAL, CO-OPTIVE, etc.).
    """

    model_config = ConfigDict(frozen=True)

    extraction_contested_threshold: float = Field(
        default=5.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation tension threshold for EXTRACTIVE -> CONTESTED.",
    )
    extraction_broken_threshold: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold for CONTESTED -> BROKEN.",
    )
    concessions_exploitation_threshold: float = Field(
        default=3.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold for EXTRACTIVE -> CONCESSIONS_OFFERED.",
    )
    concessions_rent_threshold: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Game design: imperial rent threshold for EXTRACTIVE -> CONCESSIONS_OFFERED.",
    )
    mutual_aid_threshold: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold (both directions) for BROKEN -> MUTUAL_AID.",
    )
    market_failure_threshold: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Game design: immiseration threshold for TRANSACTIONAL -> MUTUAL_AID.",
    )
    power_asymmetry_threshold: float = Field(
        default=5.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold for TRANSACTIONAL -> POWER_ASYMMETRY.",
    )
    co_optive_power_threshold: float = Field(
        default=3.0,
        ge=0.0,
        le=10.0,
        description="Game design: imperial rent threshold for POWER_ASYMMETRY -> CO_OPTIVE.",
    )
    solidarity_degrades_threshold: float = Field(
        default=6.0,
        ge=0.0,
        le=10.0,
        description="Game design: immiseration threshold for SOLIDARITY -> CONTESTED.",
    )
    betrayal_threshold: float = Field(
        default=3.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold for SOLIDARITY -> BROKEN.",
    )
    conflict_resolved_threshold: float = Field(
        default=3.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold (below) for CONTESTED -> TRANSACTIONAL.",
    )
    shared_enemy_threshold: float = Field(
        default=7.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold (both) for CONTESTED -> SOLIDARITY.",
    )
    reform_rent_threshold: float = Field(
        default=3.0,
        ge=0.0,
        le=10.0,
        description="Game design: imperial rent threshold for CO_OPTIVE -> CONCESSIONS_OFFERED.",
    )
    co_optation_normalizes_threshold: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold (below) for CO_OPTIVE -> TRANSACTIONAL.",
    )
    co_optive_breakdown_threshold: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Game design: exploitation threshold (below) for CO_OPTIVE -> BROKEN.",
    )
    concessions_withdrawn_threshold: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Game design: imperial rent threshold (below) for CONCESSIONS_OFFERED -> EXTRACTIVE.",
    )


class OODADefines(BaseModel):
    """OODA Loop System tunable coefficients (Feature 032).

    Controls cycle time computation, initiative scoring, action costs,
    consciousness effect multipliers, and propagation parameters.

    See Also:
        ``specs/032-ooda-loop-system/data-model.md``: Full specification.
    """

    model_config = ConfigDict(frozen=True)

    # --- Cycle time weights (OODA profile contract) ---
    base_observe_time: float = Field(
        default=1.0,
        gt=0,
        description="Base Observe phase duration.",
    )
    latency_weight: float = Field(
        default=0.5,
        ge=0,
        description="Weight of sensor_latency on Observe phase.",
    )
    base_orient_time: float = Field(
        default=2.0,
        gt=0,
        description="Base Orient phase duration.",
    )
    coherence_weight: float = Field(
        default=0.6,
        ge=0,
        le=1.0,
        description="Weight of ideological_coherence on Orient phase.",
    )
    base_act_time: float = Field(
        default=1.0,
        gt=0,
        description="Base Act phase duration (fixed).",
    )
    coord_weight: float = Field(
        default=0.3,
        ge=0,
        description="Weight of coordination on Act phase (reserved).",
    )
    depth_weight: float = Field(
        default=0.4,
        ge=0,
        description="Weight of bureaucratic_depth on Decide phase.",
    )

    # --- Decision mode base times ---
    decision_mode_base_autocratic: float = Field(
        default=1.0,
        gt=0,
        description="[C] 1 cycle: single decision-maker (COIN operational tempo).",
    )
    decision_mode_base_delegate: float = Field(
        default=2.0,
        gt=0,
        description="[C] 2 cycles: FM 3-24 mission command delegation.",
    )
    decision_mode_base_democratic: float = Field(
        default=3.0,
        gt=0,
        description="[C] 3 cycles: majority vote (ProleWiki democratic centralism).",
    )
    decision_mode_base_consensus: float = Field(
        default=5.0,
        gt=0,
        description="[C] 5 cycles: full agreement, mass line process (ProleWiki).",
    )

    # --- Initiative scoring weights ---
    initiative_weight_speed: float = Field(
        default=2.0,
        ge=0,
        description="[C] Boyd's central insight: tempo is decisive factor (RAND decomposition).",
    )
    initiative_weight_institutional: float = Field(
        default=1.0,
        ge=0,
        description="[C] Baseline: institutional power is important but static (RAND).",
    )
    initiative_weight_counterintel: float = Field(
        default=1.5,
        ge=0,
        description="[C] 1.5× institutional: degrades adversary Observe phase (Sparrow).",
    )
    initiative_weight_embeddedness: float = Field(
        default=1.0,
        ge=0,
        description="[C] = institutional: community roots compensate for state advantage (RAND).",
    )
    initiative_weight_momentum: float = Field(
        default=0.5,
        ge=0,
        description="[C] 0.5× baseline: volatile, decays 20%/tick (RAND).",
    )

    # --- Institutional bonus by jurisdiction ---
    institutional_bonus_federal: float = Field(
        default=5.0,
        ge=0,
        description="[C] 5×: COIN force density ratio, federal apparatus (FM 3-24).",
    )
    institutional_bonus_state: float = Field(
        default=3.0,
        ge=0,
        description="[C] 3×: state police force ratio, 60% federal effectiveness (RAND).",
    )
    institutional_bonus_local: float = Field(
        default=1.5,
        ge=0,
        description="[C] 1.5×: local PD baseline + Galula administrative presence premium.",
    )
    institutional_bonus_nonstate: float = Field(
        default=0.0,
        ge=0,
        description="Initiative bonus for non-state organizations.",
    )

    # --- Momentum ---
    momentum_decay: float = Field(
        default=0.8,
        ge=0,
        lt=1.0,
        description="= 1 - 2λ: momentum twice as volatile as consciousness (mass line analysis).",
    )
    momentum_success_bonus: float = Field(
        default=0.2,
        ge=0,
        description="[A] = struggle.solidarity_gain_per_uprising: organizational analog of solidarity gain.",
    )

    # --- Action cost modifiers ---
    embeddedness_discount: float = Field(
        default=0.5,
        ge=0,
        le=1.0,
        description="[B] = solidarity.scaling_factor: community roots discount action costs at solidarity scale.",
    )
    contradiction_cost_multiplier: float = Field(
        default=2.5,
        gt=1.0,
        description="[C] ≈ √4.2: geometric mean of Black/white incarceration disparity (MIM Prisons).",
    )
    outsider_cost_multiplier: float = Field(
        default=1.5,
        gt=1.0,
        description="[C] = territory.rent_spike_multiplier: Prebisch-Singer terms-of-trade penalty.",
    )
    min_cost_modifier: float = Field(
        default=0.5,
        gt=0,
        le=1.0,
        description="Floor cost modifier for embedded orgs.",
    )

    # --- Consciousness effect limits ---
    max_ci_delta_per_tick: float = Field(
        default=0.05,
        gt=0,
        le=1.0,
        description="[B] = λ/2: half the decay rate prevents single actions from overwhelming the ODE.",
    )

    # --- Action base consciousness multipliers ---
    action_base_educate: float = Field(
        default=1.2,
        ge=0,
        description="[B] = 1 + 2λ: overcomes decay plus net positive effect.",
    )
    action_base_agitate: float = Field(
        default=0.0,
        ge=0,
        description="Consciousness multiplier for AGITATE (zero = no CI effect).",
    )
    action_base_provide_service: float = Field(
        default=0.6,
        ge=0,
        description="[B] = k + routing_scale = 0.5 + 0.1: material sensitivity + routing (BPP survival programs).",
    )
    action_base_recruit: float = Field(
        default=0.3,
        ge=0,
        description="[B] = solidarity.activation_threshold: bring recruits to percolation threshold.",
    )
    action_base_organize: float = Field(
        default=0.5,
        ge=0,
        description="[B] = consciousness.sensitivity: organizing operationalizes material sensitivity k.",
    )
    action_base_propagandize: float = Field(
        default=0.8,
        ge=0,
        description="[B] = 1 - 2λ: symmetric inverse of EDUCATE (less precise than education).",
    )
    action_base_repress: float = Field(
        default=0.8,
        ge=0,
        description="[B] = α (extraction_efficiency): repression backfire proportional to extraction visibility.",
    )
    action_base_surveil: float = Field(
        default=0.2,
        ge=0,
        description="[B] = 1 - α: surveillance backfire is complement of extraction (invisible fraction).",
    )
    action_base_assimilate: float = Field(
        default=1.0,
        ge=0,
        description="Negative CI multiplier for ASSIMILATE.",
    )

    # --- Autonomy tradeoff ---
    autonomy_effectiveness_scale: float = Field(
        default=0.5,
        ge=0,
        le=1.0,
        description="[C] 0.5: democratic centralism tradeoff (ProleWiki). Vanguard = 2× coordinated impact.",
    )

    # --- Agitation -> contestation ---
    agitation_contestation_delta: float = Field(
        default=0.1,
        ge=0,
        le=1.0,
        description="[A] = consciousness.agitation_decay_rate: equilibrium requires continuous agitation.",
    )
    agitation_educate_bonus: float = Field(
        default=1.5,
        ge=1.0,
        description="[B] = territory.rent_spike_multiplier: crisis amplification factor (same as eviction premium).",
    )
    contestation_threshold: float = Field(
        default=0.3,
        ge=0,
        le=1.0,
        description="[B] = solidarity.activation_threshold: same tipping point for political engagement.",
    )

    # --- Lifecycle modifiers ---
    elder_legitimacy_multiplier: float = Field(
        default=1.3,
        ge=1.0,
        description="[C] = 1 + lifecycle.ideology_institutional_weight: elder institutional moral authority.",
    )

    # --- Counter-intelligence ---
    counter_intel_increment: float = Field(
        default=0.1,
        ge=0,
        le=1.0,
        description="[C] = λ: network disruption rate matches consciousness entropy (Sparrow).",
    )

    # --- Base action point costs ---
    base_cost_recruit: int = Field(default=2, ge=1, description="AP cost: RECRUIT")
    base_cost_organize: int = Field(default=2, ge=1, description="AP cost: ORGANIZE")
    base_cost_educate: int = Field(default=1, ge=1, description="AP cost: EDUCATE")
    base_cost_agitate: int = Field(default=1, ge=1, description="AP cost: AGITATE")
    base_cost_propagandize: int = Field(default=2, ge=1, description="AP cost: PROPAGANDIZE")
    base_cost_fundraise: int = Field(default=1, ge=1, description="AP cost: FUNDRAISE")
    base_cost_provide_service: int = Field(default=2, ge=1, description="AP cost: PROVIDE_SERVICE")
    base_cost_employ: int = Field(default=1, ge=1, description="AP cost: EMPLOY")
    base_cost_repress: int = Field(default=2, ge=1, description="AP cost: REPRESS")
    base_cost_protest: int = Field(default=2, ge=1, description="AP cost: PROTEST")
    base_cost_strike: int = Field(default=3, ge=1, description="AP cost: STRIKE")
    base_cost_expropriate: int = Field(default=3, ge=1, description="AP cost: EXPROPRIATE")
    base_cost_surveil: int = Field(default=1, ge=1, description="AP cost: SURVEIL")
    base_cost_infiltrate: int = Field(default=3, ge=1, description="AP cost: INFILTRATE")
    base_cost_counter_intel: int = Field(default=2, ge=1, description="AP cost: COUNTER_INTEL")
    base_cost_map_network: int = Field(default=1, ge=1, description="AP cost: MAP_NETWORK")
    base_cost_propose_alliance: int = Field(
        default=1, ge=1, description="AP cost: PROPOSE_ALLIANCE"
    )
    base_cost_denounce: int = Field(default=1, ge=1, description="AP cost: DENOUNCE")
    base_cost_build_infrastructure: int = Field(
        default=3, ge=1, description="AP cost: BUILD_INFRASTRUCTURE"
    )
    base_cost_attack_infrastructure: int = Field(
        default=2, ge=1, description="AP cost: ATTACK_INFRASTRUCTURE"
    )
    base_cost_assimilate: int = Field(default=2, ge=1, description="AP cost: ASSIMILATE")

    # --- Layer 3 propagation coefficients ---
    repress_heat_delta: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="[A] = territory.high_profile_heat_gain: repression IS high-profile attention.",
    )
    surveil_heat_delta: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="[A] = territory.heat_spillover_rate: passive surveillance = background state attention.",
    )
    build_infrastructure_delta: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Infrastructure increase per BUILD action"
    )
    attack_infrastructure_delta: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Infrastructure decrease per ATTACK action"
    )
    orient_time_floor: float = Field(
        default=0.1, ge=0.0, description="Minimum orient phase duration"
    )

    def validate_derivations(self, game_defines: GameDefines) -> list[str]:
        """Cross-validate OODA coefficients against source primitives.

        Checks that derived coefficients (Categories A and B) still match
        their source primitive formulas. Returns a list of drift warnings
        for any mismatches exceeding tolerance (0.001).

        Args:
            game_defines: Parent GameDefines providing source primitives.

        Returns:
            List of warning messages for any detected drift. Empty if clean.
        """
        c = game_defines.consciousness
        t = game_defines.territory
        e = game_defines.economy
        s = game_defines.solidarity
        st = game_defines.struggle
        lc = game_defines.lifecycle
        tol = 0.001
        drifts: list[str] = []

        checks: list[tuple[str, float, float]] = [
            # Category A: direct substitutions
            ("repress_heat_delta", self.repress_heat_delta, t.high_profile_heat_gain),
            ("surveil_heat_delta", self.surveil_heat_delta, t.heat_spillover_rate),
            (
                "momentum_success_bonus",
                self.momentum_success_bonus,
                st.solidarity_gain_per_uprising,
            ),
            (
                "agitation_contestation_delta",
                self.agitation_contestation_delta,
                c.agitation_decay_rate,
            ),
            # Category B: formula derivations
            ("momentum_decay", self.momentum_decay, 1 - 2 * c.agitation_decay_rate),
            ("max_ci_delta_per_tick", self.max_ci_delta_per_tick, c.decay_lambda / 2),
            ("action_base_educate", self.action_base_educate, 1 + 2 * c.decay_lambda),
            ("action_base_propagandize", self.action_base_propagandize, 1 - 2 * c.decay_lambda),
            ("action_base_repress", self.action_base_repress, e.extraction_efficiency),
            ("action_base_surveil", self.action_base_surveil, 1 - e.extraction_efficiency),
            (
                "action_base_provide_service",
                self.action_base_provide_service,
                c.sensitivity + c.routing_scale,
            ),
            ("action_base_organize", self.action_base_organize, c.sensitivity),
            ("action_base_recruit", self.action_base_recruit, s.activation_threshold),
            ("contestation_threshold", self.contestation_threshold, s.activation_threshold),
            ("agitation_educate_bonus", self.agitation_educate_bonus, t.rent_spike_multiplier),
            ("embeddedness_discount", self.embeddedness_discount, s.scaling_factor),
            # Category C: empirically grounded cross-references
            (
                "elder_legitimacy_multiplier",
                self.elder_legitimacy_multiplier,
                1 + lc.ideology_institutional_weight,
            ),
            ("counter_intel_increment", self.counter_intel_increment, c.decay_lambda),
            ("outsider_cost_multiplier", self.outsider_cost_multiplier, t.rent_spike_multiplier),
        ]

        for name, actual, expected in checks:
            if abs(actual - expected) > tol:
                msg = f"OODADefines.{name} drifted: actual={actual}, expected={expected}"
                drifts.append(msg)
                warnings.warn(msg, UserWarning, stacklevel=2)

        return drifts

    def get_base_cost(self, action_type: str) -> int:
        """Look up base AP cost for an action type.

        Args:
            action_type: ActionType value string.

        Returns:
            Base AP cost for the action.

        Raises:
            KeyError: If action_type is not recognized.
        """
        cost_map: dict[str, int] = {
            "recruit": self.base_cost_recruit,
            "organize": self.base_cost_organize,
            "educate": self.base_cost_educate,
            "agitate": self.base_cost_agitate,
            "propagandize": self.base_cost_propagandize,
            "fundraise": self.base_cost_fundraise,
            "provide_service": self.base_cost_provide_service,
            "employ": self.base_cost_employ,
            "repress": self.base_cost_repress,
            "protest": self.base_cost_protest,
            "strike": self.base_cost_strike,
            "expropriate": self.base_cost_expropriate,
            "surveil": self.base_cost_surveil,
            "infiltrate": self.base_cost_infiltrate,
            "counter_intel": self.base_cost_counter_intel,
            "map_network": self.base_cost_map_network,
            "propose_alliance": self.base_cost_propose_alliance,
            "denounce": self.base_cost_denounce,
            "build_infrastructure": self.base_cost_build_infrastructure,
            "attack_infrastructure": self.base_cost_attack_infrastructure,
            "assimilate": self.base_cost_assimilate,
        }
        if action_type not in cost_map:
            msg = f"Unknown action type: {action_type}"
            raise KeyError(msg)
        return cost_map[action_type]

    def get_action_base(self, action_type: str) -> float:
        """Look up consciousness base multiplier for an action type.

        Args:
            action_type: ActionType value string.

        Returns:
            Consciousness base multiplier (0.0 means no CI effect).
        """
        base_map: dict[str, float] = {
            "educate": self.action_base_educate,
            "agitate": self.action_base_agitate,
            "provide_service": self.action_base_provide_service,
            "recruit": self.action_base_recruit,
            "organize": self.action_base_organize,
            "propagandize": self.action_base_propagandize,
            "repress": self.action_base_repress,
            "surveil": self.action_base_surveil,
            "assimilate": self.action_base_assimilate,
        }
        return base_map.get(action_type, 0.0)


class BifurcationDefines(BaseModel):
    """Bifurcation Topology Analysis coefficients (Feature 033).

    Configures consciousness-weighted solidarity analysis that predicts
    whether crisis routes to fascism or revolution. The core innovation:
    a nonlinear sigmoid of collective_identity weights solidarity edges
    so assimilationist solidarity classifies as fragile/fascist.

    See Also:
        :mod:`babylon.bifurcation.consciousness`: Sigmoid weighting.
        :mod:`babylon.bifurcation.analysis`: Full bifurcation orchestrator.
        ``specs/033-bifurcation-topology/spec.md``: Feature specification.
    """

    model_config = ConfigDict(frozen=True)

    # Consciousness sigmoid (US1)
    consciousness_sigmoid_midpoint: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description=(
            "Behavior-tuned: CI value at sigmoid inflection. Below-center "
            "so breakage cliff catches assimilated communities (CI<0.4). "
            "Analogous to SurvivalDefines.default_subsistence=0.3."
        ),
    )
    consciousness_sigmoid_steepness: float = Field(
        default=10.0,
        gt=0.0,
        le=50.0,
        description=(
            "Codebase precedent: matches SurvivalDefines.steepness_k=10.0. "
            "Slope at inflection (higher = sharper cliff)."
        ),
    )
    consciousness_filter_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description=(
            "Derived: sigmoid(CI=0.27, midpoint=0.4, k=10)~0.21. "
            "Minimum sigmoid output to include edge in filtered subgraph."
        ),
    )

    # Classification (US5)
    indeterminate_dead_zone: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: score within [-x, +x] of threshold = indeterminate. "
            "Analogous to CrisisDefines.bifurcation_event_threshold=0.5."
        ),
    )
    axis_tendency_epsilon: float = Field(
        default=0.001,
        gt=0.0,
        le=0.1,
        description=(
            "Engineering: matches CrisisDefines.class_burden_epsilon=0.001. "
            "Division guard for cross/lateral ratio."
        ),
    )

    # Legitimation amplifier (US7)
    legitimation_amplifier_scale: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description=(
            "Behavior-tuned: at zero legitimation, crisis intensity doubles. "
            "Conservative start vs legacy _DEFAULT_CRISIS_AMPLIFIER=2.5."
        ),
    )

    # Solidarity ceiling (US6)
    wage_ceiling_high_ratio: float = Field(
        default=10.0,
        ge=1.0,
        description=(
            "Theoretical: 10x wage gap = qualitatively different material "
            "conditions (core bourgeoisie vs periphery proletariat)."
        ),
    )
    wage_ceiling_low_ratio: float = Field(
        default=2.0,
        ge=1.0,
        description=(
            "Theoretical: <2x wage gap = roughly similar material conditions "
            "(within same class fraction)."
        ),
    )
    wage_ceiling_min: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Theoretical: extreme wage gaps severely limit but don't eliminate "
            "solidarity potential."
        ),
    )
    wage_ceiling_max: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description=(
            "Theoretical: similar wages allow strong but not unlimited "
            "solidarity (other factors still matter)."
        ),
    )
    shared_exploitation_bonus: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description=(
            "Theoretical: matches _REPRO_EXTERNALIZATION_FACTOR=0.2. "
            "Shared enemy raises solidarity potential."
        ),
    )

    # Purge resilience (US4)
    purge_removal_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description=(
            "Codebase precedent: matches TopologyDefines.resilience_removal_rate=0.2. "
            "Fraction removed during bifurcation-specific purge test."
        ),
    )


class InfraTerrainDefines(BaseModel):
    """Terrain classification and biocapacity coefficients (Feature 036).

    Configures majority-coverage thresholds, initial biocapacity stock
    values, and per-tick depletion rates. Also includes internet access
    defaults.

    See Also:
        :mod:`babylon.infrastructure.terrain`: DefaultTerrainClassifier.
        ``specs/036-infrastructure-topology/spec.md``: FR-001 through FR-008.
    """

    model_config = ConfigDict(frozen=True)

    # Terrain classification (FR-001)
    majority_coverage_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Coverage fraction above which a hex is classified "
            "as WATER or RESOURCE. 0.5 = majority rule."
        ),
    )

    # Biocapacity initial stocks (FR-005, FR-006)
    # SYNTHETIC: Game-design values, no empirical source
    initial_freshwater: float = Field(
        default=100.0,
        ge=0.0,
        description="SYNTHETIC: Initial FRESHWATER stock for WATER hexes.",
    )
    initial_fishery: float = Field(
        default=80.0,
        ge=0.0,
        description="SYNTHETIC: Initial FISHERY stock for WATER hexes.",
    )
    initial_shipping_access: float = Field(
        default=50.0,
        ge=0.0,
        description="SYNTHETIC: Initial SHIPPING_ACCESS stock for WATER hexes.",
    )
    initial_mineral: float = Field(
        default=120.0,
        ge=0.0,
        description="SYNTHETIC: Initial MINERAL stock for RESOURCE hexes.",
    )
    initial_timber: float = Field(
        default=90.0,
        ge=0.0,
        description="SYNTHETIC: Initial TIMBER stock for RESOURCE hexes.",
    )
    initial_hydroelectric: float = Field(
        default=60.0,
        ge=0.0,
        description="SYNTHETIC: Initial HYDROELECTRIC stock for RESOURCE hexes.",
    )

    # Biocapacity depletion rates (FR-007)
    # SYNTHETIC: Per-tick extraction fraction of current stock
    depletion_freshwater: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for FRESHWATER.",
    )
    depletion_fishery: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for FISHERY.",
    )
    depletion_shipping_access: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for SHIPPING_ACCESS.",
    )
    depletion_mineral: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for MINERAL.",
    )
    depletion_timber: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for TIMBER.",
    )
    depletion_hydroelectric: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for HYDROELECTRIC.",
    )

    # Internet access defaults (FR-024)
    internet_access_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Minimum FCC broadband penetration percentage / 100 "
            "for internet_access=True. 0.5 = 50% coverage required."
        ),
    )
    default_surveillance_coupling: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Default fraction of consciousness flow visible "
            "to state apparatus at internet-connected hexes."
        ),
    )

    def get_initial_stock(self, stock_type: str) -> float:
        """Get initial biocapacity stock value by type.

        Args:
            stock_type: BiocapacityType value (lowercase).

        Returns:
            Initial stock value.

        Raises:
            ValueError: If stock_type is not recognized.
        """
        stock_map: dict[str, float] = {
            "freshwater": self.initial_freshwater,
            "fishery": self.initial_fishery,
            "shipping_access": self.initial_shipping_access,
            "mineral": self.initial_mineral,
            "timber": self.initial_timber,
            "hydroelectric": self.initial_hydroelectric,
        }
        if stock_type not in stock_map:
            msg = f"Unknown stock_type: {stock_type!r}"
            raise ValueError(msg)
        return stock_map[stock_type]

    def get_depletion_rate(self, stock_type: str) -> float:
        """Get per-tick depletion rate by stock type.

        Args:
            stock_type: BiocapacityType value (lowercase).

        Returns:
            Depletion rate per tick.

        Raises:
            ValueError: If stock_type is not recognized.
        """
        rate_map: dict[str, float] = {
            "freshwater": self.depletion_freshwater,
            "fishery": self.depletion_fishery,
            "shipping_access": self.depletion_shipping_access,
            "mineral": self.depletion_mineral,
            "timber": self.depletion_timber,
            "hydroelectric": self.depletion_hydroelectric,
        }
        if stock_type not in rate_map:
            msg = f"Unknown stock_type: {stock_type!r}"
            raise ValueError(msg)
        return rate_map[stock_type]


class InfrastructureDefines(BaseModel):
    """Infrastructure capacity and internet operation coefficients (Feature 036).

    Configures per-type capacity values, natural capacity defaults,
    OPSEC tradeoff ratios, and internet throttle fractions.

    See Also:
        :mod:`babylon.infrastructure.capacity`: DefaultEdgeCapacityCalculator.
        ``specs/036-infrastructure-topology/spec.md``: FR-009 through FR-029.
    """

    model_config = ConfigDict(frozen=True)

    # Per-type base capacity coefficients (FR-012)
    # Format: {infra_type}_{flow_category}
    # SYNTHETIC: Game-design values
    highway_freight: float = Field(default=1.0, ge=0.0, description="SYNTHETIC")
    highway_commuter: float = Field(default=1.0, ge=0.0, description="SYNTHETIC")
    highway_value: float = Field(default=0.5, ge=0.0, description="SYNTHETIC")
    highway_consciousness: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")

    arterial_freight: float = Field(default=0.6, ge=0.0, description="SYNTHETIC")
    arterial_commuter: float = Field(default=0.7, ge=0.0, description="SYNTHETIC")
    arterial_value: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")
    arterial_consciousness: float = Field(default=0.2, ge=0.0, description="SYNTHETIC")

    local_road_freight: float = Field(default=0.2, ge=0.0, description="SYNTHETIC")
    local_road_commuter: float = Field(default=0.4, ge=0.0, description="SYNTHETIC")
    local_road_value: float = Field(default=0.1, ge=0.0, description="SYNTHETIC")
    local_road_consciousness: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")

    rail_freight: float = Field(default=1.2, ge=0.0, description="SYNTHETIC")
    rail_commuter: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")
    rail_value: float = Field(default=0.2, ge=0.0, description="SYNTHETIC")
    rail_consciousness: float = Field(default=0.1, ge=0.0, description="SYNTHETIC")

    pipeline_energy: float = Field(default=1.5, ge=0.0, description="SYNTHETIC")

    transmission_energy: float = Field(default=1.0, ge=0.0, description="SYNTHETIC")

    shipping_lane_freight: float = Field(default=1.5, ge=0.0, description="SYNTHETIC")

    air_link_freight: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")
    air_link_commuter: float = Field(default=0.8, ge=0.0, description="SYNTHETIC")
    air_link_value: float = Field(default=0.5, ge=0.0, description="SYNTHETIC")
    air_link_consciousness: float = Field(default=0.5, ge=0.0, description="SYNTHETIC")

    # Natural capacity (FR-014)
    natural_capacity_coefficient: float = Field(
        default=0.1,
        ge=0.0,
        description=(
            "SYNTHETIC: Base natural capacity for LAND-LAND edges without "
            "infrastructure. Applied to COMMUTER and CONSCIOUSNESS only."
        ),
    )

    # Minimum capacity threshold (EC-006)
    minimum_capacity_threshold: float = Field(
        default=0.01,
        ge=0.0,
        description=(
            "SYNTHETIC: Minimum edge capacity below which flow is zero. "
            "Prevents numerical noise from near-zero weights."
        ),
    )

    # OPSEC tradeoff (FR-028)
    opsec_tradeoff_ratio: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Ratio of surveillance coupling reduction to "
            "consciousness throughput loss when applying COUNTER_INTEL."
        ),
    )

    # Throttle throughput (FR-029)
    throttle_throughput_fraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Fraction of consciousness throughput remaining "
            "when state sets THROTTLE response mode."
        ),
    )

    # Snapping tolerance (FR-011)
    snap_buffer_fraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Buffer around shared boundary as fraction of "
            "hex diameter for spatial snapping of linear features."
        ),
    )

    # Nonlocal locality thresholds (FR-020)
    local_ratio_threshold: float = Field(
        default=3.0,
        gt=0.0,
        description=(
            "SYNTHETIC: Distance/hex_diameter ratio below which edge is classified as LOCAL."
        ),
    )
    semi_local_ratio_threshold: float = Field(
        default=20.0,
        gt=0.0,
        description=(
            "SYNTHETIC: Distance/hex_diameter ratio below which edge "
            "is classified as SEMI_LOCAL. Above = NONLOCAL."
        ),
    )

    def get_capacity(self, infra_type: str, flow_category: str) -> float:
        """Get base capacity for an infrastructure type and flow category.

        Args:
            infra_type: InfrastructureType value (lowercase).
            flow_category: FlowCategory value (lowercase).

        Returns:
            Base capacity value, or 0.0 if combination not applicable.
        """
        key = f"{infra_type}_{flow_category}"
        return getattr(self, key, 0.0)


class RentCircuitDefines(BaseModel):
    """Parameters for ground rent extraction in Volume III equalization (Feature 043)."""

    model_config = ConfigDict(frozen=True)

    absolute_rent_fraction: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="Fraction of extracted volume III rent considered absolute rent.",
    )
    differential_rent_elasticity: float = Field(
        default=1.2,
        ge=0.1,
        le=5.0,
        description="Responsiveness of differential rent given local surplus intensity.",
    )


class ClassSystemDefines(BaseModel):
    """Unified class system coefficients (Feature 038).

    Centralizes all tunable coefficients for the unified class system:
    filtration parameters, home ownership proxy, and the 5x5 class-pair
    solidarity matrix.

    Args:
        trust_land_discount: Fed SCF / BIA discount on effective wealth for
            FIRST_NATIONS trust land property. 0.5 = 50% reduction.
        documentation_exclusion_factor: Discount on effective wealth for
            UNDOCUMENTED households. 0.6 = 40% reduction.
        equity_factor: Fraction of homeowners with meaningful equity.
            Calibrated: 65% ownership * 0.6 = 39% ~ 40% LA share.
        base_class_solidarity: Symmetric 5x5 class-pair base solidarity
            matrix (15 unique values in upper triangle including diagonal).
    """

    model_config = ConfigDict(frozen=True)

    trust_land_discount: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Fed SCF / BIA: discount on effective wealth for FIRST_NATIONS "
            "trust land property. 0.5 = 50% reduction in effective wealth percentile."
        ),
    )
    documentation_exclusion_factor: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: discount on effective wealth for UNDOCUMENTED households. "
            "0.6 = 40% reduction. Reflects structural exclusion from formal "
            "property/banking/labor protections."
        ),
    )
    equity_factor: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Feature 043: Absolute threshold test on equity required for LA classification. "
            "Formerly a population-level numeric scaler."
        ),
    )
    base_class_solidarity: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "BOURGEOISIE": {
                "BOURGEOISIE": 0.70,
                "PETIT_BOURGEOISIE": 0.30,
                "LABOR_ARISTOCRACY": 0.10,
                "PROLETARIAT": 0.00,
                "LUMPENPROLETARIAT": 0.00,
            },
            "PETIT_BOURGEOISIE": {
                "PETIT_BOURGEOISIE": 0.50,
                "LABOR_ARISTOCRACY": 0.40,
                "PROLETARIAT": 0.15,
                "LUMPENPROLETARIAT": 0.05,
            },
            "LABOR_ARISTOCRACY": {
                "LABOR_ARISTOCRACY": 0.60,
                "PROLETARIAT": 0.30,
                "LUMPENPROLETARIAT": 0.10,
            },
            "PROLETARIAT": {
                "PROLETARIAT": 0.80,
                "LUMPENPROLETARIAT": 0.50,
            },
            "LUMPENPROLETARIAT": {
                "LUMPENPROLETARIAT": 0.60,
            },
        },
        description=(
            "Game design: symmetric 5x5 class-pair base solidarity matrix. "
            "15 unique values (upper triangle including diagonal). "
            "Class proximity yields higher base solidarity."
        ),
    )

    @model_validator(mode="after")
    def _validate_solidarity_matrix(self) -> ClassSystemDefines:
        """Ensure all matrix entries are in [0.0, 1.0]."""
        for outer_key, inner_dict in self.base_class_solidarity.items():
            for inner_key, value in inner_dict.items():
                if not 0.0 <= value <= 1.0:
                    msg = (
                        f"base_class_solidarity[{outer_key!r}][{inner_key!r}] = {value} "
                        f"is outside [0.0, 1.0]"
                    )
                    raise ValueError(msg)
        return self

    def get_base_solidarity(self, class_a: str, class_b: str) -> float:
        """Symmetric lookup into the class-pair solidarity matrix.

        Args:
            class_a: ClassPosition name (e.g. "PROLETARIAT").
            class_b: ClassPosition name (e.g. "LABOR_ARISTOCRACY").

        Returns:
            Base solidarity value, or 0.0 for unknown pairs.
        """
        if class_a in self.base_class_solidarity:
            inner = self.base_class_solidarity[class_a]
            if class_b in inner:
                return inner[class_b]
        if class_b in self.base_class_solidarity:
            inner = self.base_class_solidarity[class_b]
            if class_a in inner:
                return inner[class_a]
        return 0.0


class StateApparatusAIDefines(BaseModel):
    """State Apparatus AI coefficients (Feature 039).

    Configures the state-as-adversary system: faction dynamics,
    fascist convergence detection, attention thread management,
    budget allocation, escalation ladder, and territory effect parameters.

    All thresholds are [S] SYNTHETIC unless otherwise noted.

    See Also:
        ``specs/039-state-apparatus-ai/spec.md``: Full specification.
    """

    model_config = ConfigDict(frozen=True)

    # -------------------------------------------------------------------------
    # Faction Dynamics (FR-C01 through FR-C08, R-003)
    # -------------------------------------------------------------------------
    max_faction_shift_per_tick: float = Field(
        default=0.05,
        ge=0.0,
        le=0.2,
        description="[S] Maximum per-faction weight change per tick (R-003).",
    )
    minimum_effect_floor: float = Field(
        default=0.02,
        ge=0.0,
        le=0.1,
        description="[S] Minimum detectable faction/territory effect (SC-010).",
    )
    heat_to_ss_coefficient: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[S] Heat-to-Security-State shift rate per tick.",
    )

    # -------------------------------------------------------------------------
    # Fascist Convergence (FR-C06, FR-C07, R-008)
    # -------------------------------------------------------------------------
    fascist_security_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="[S] Security-State weight threshold for convergence entry.",
    )
    fascist_settler_ci_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="[S] Settler collective_identity threshold for convergence entry.",
    )
    fascist_finance_ceiling: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="[S] Finance-Capital weight ceiling for convergence entry.",
    )
    convergence_confirmation_ticks: int = Field(
        default=2,
        ge=1,
        le=10,
        description="[S] Consecutive ticks required to confirm convergence.",
    )
    reversion_ss_threshold: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="[S] Security-State threshold for fascist reversion (FR-C07).",
    )
    reversion_ci_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="[S] Settler CI threshold for fascist reversion (FR-C07).",
    )

    # -------------------------------------------------------------------------
    # Attention Threads (FR-A01 through FR-A08)
    # -------------------------------------------------------------------------
    thread_pool_base: int = Field(
        default=5,
        ge=1,
        le=50,
        description="[S] Base thread pool size before surveillance_capacity scaling.",
    )
    thread_pool_max: int = Field(
        default=8,
        ge=1,
        le=100,
        description="[S] Maximum thread pool size.",
    )
    thread_escalation_thresholds: dict[str, float] = Field(
        default={
            "dormant_to_monitoring": 0.1,
            "monitoring_to_active": 0.4,
            "active_to_disruption": 0.7,
        },
        description="[S] Intel completeness thresholds for phase transitions.",
    )

    # -------------------------------------------------------------------------
    # Budget (FR-D05, R-004)
    # -------------------------------------------------------------------------
    detroit_2010_annual_budget: float = Field(
        default=100.0,
        ge=0.0,
        description="[S] Scaled annual budget for Detroit 2010 scenario.",
    )
    actions_per_tick: int = Field(
        default=1,
        ge=1,
        le=10,
        description="[S] Maximum state actions per tick (FR-D05).",
    )

    # -------------------------------------------------------------------------
    # Escalation Ladder (FR-D06)
    # -------------------------------------------------------------------------
    escalation_ladder: list[str] = Field(
        default=[
            "propagandize",
            "bribe",
            "incorporate",
            "surveil_state",
            "divide",
            "infiltrate_state",
            "invest",
            "rezone",
            "fund",
            "legislate",
            "raid",
            "prosecute",
            "displace",
            "strategic_withdrawal",
            "liquidate",
            "scorched_earth",
        ],
        description="[S] Ordered escalation from low-cost to high-cost verbs.",
    )

    # -------------------------------------------------------------------------
    # Territory Effects (FR-E01 through FR-E05)
    # -------------------------------------------------------------------------
    develop_infrastructure_boost: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[S] Infrastructure boost per INVEST action.",
    )
    neglect_infrastructure_decay: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="[S] Infrastructure decay per NEGLECT action.",
    )
    displace_population_fraction: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[S] Population fraction displaced per DISPLACE action.",
    )
    neglect_quality_floor: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[S] Hard lower bound on infrastructure_quality under NEGLECT (TE-02).",
    )
    consciousness_resistance_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="[S] How much collective_identity resists PROPAGANDIZE (TE-07).",
    )
    high_profile_heat_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[S] Heat per HIGH_PROFILE PRESENCE edge per tick (TE-06).",
    )
    low_profile_heat_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="[S] Heat per LOW_PROFILE PRESENCE edge per tick (TE-06).",
    )
    heat_escalation_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="[S] Heat level at which territory becomes priority target (TE-06).",
    )
    scorched_earth_legitimacy_core: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="[S] Legitimacy cost for SCORCHED_EARTH in CORE territory (TE-05).",
    )
    scorched_earth_legitimacy_periphery: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="[S] Legitimacy cost for SCORCHED_EARTH in PERIPHERY territory (TE-05).",
    )
    strategic_withdrawal_decay_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="[S] Accelerated NEGLECT factor for STRATEGIC_WITHDRAWAL (TE-04).",
    )
    strategic_withdrawal_asset_recovery: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="[S] Fraction of state_investment recovered when asset_extraction=True (TE-04).",
    )
    displace_ci_reduction: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="[S] Collective identity reduction per DISPLACE action (TE-03).",
    )
    displace_community_infra_reduction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="[S] Community infrastructure quality reduction per DISPLACE (TE-03).",
    )

    # -------------------------------------------------------------------------
    # Spatial Dynamics (FR-E01 through FR-E07)
    # -------------------------------------------------------------------------
    heat_decay_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="[S] Per-tick heat decay when no PRESENCE edges active.",
    )
    recruit_no_presence_penalty: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="[S] Effectiveness penalty for recruiting without territorial PRESENCE (0.9 = 90% reduction).",
    )
    eviction_scatter_ci_loss: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="[S] CI loss in neighboring territories receiving scattered population.",
    )

    # -------------------------------------------------------------------------
    # CO-OPT Effects (FR-B05)
    # -------------------------------------------------------------------------
    propagandize_base_delta: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="[S] Base CI reduction per PROPAGANDIZE application (FR-B05).",
    )
    incorporate_base_attractiveness: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="[S] Base offer attractiveness for INCORPORATE (FR-B05).",
    )
    bribe_consciousness_shift: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="[S] Revolutionary tendency reduction per BRIBE (FR-B05).",
    )
    bribe_liberal_increase: float = Field(
        default=0.03,
        ge=0.0,
        le=0.5,
        description="[S] Liberal tendency increase per BRIBE (FR-B05).",
    )
    divide_requires_prior_surveil: bool = Field(
        default=True,
        description="[S] Whether DIVIDE requires prior SURVEIL intelligence.",
    )
    incorporate_requires_prior_surveil: bool = Field(
        default=True,
        description="[S] Whether INCORPORATE requires prior SURVEIL intelligence.",
    )

    # -------------------------------------------------------------------------
    # ADMINISTER Effects (FR-B02)
    # -------------------------------------------------------------------------
    fund_capacity_increment: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="[S] Per-FUND capacity increase for target capacity type (FR-B02).",
    )
    staff_thread_cost: float = Field(
        default=3.0,
        ge=0.0,
        le=50.0,
        description="[S] Budget cost per new thread slot from STAFF (FR-B02).",
    )
    staff_max_per_tick: int = Field(
        default=2,
        ge=1,
        le=10,
        description="[S] Maximum threads STAFF can add per tick (FR-B02).",
    )
    audit_routine_detection_chance: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="[S] ROUTINE audit depth: P(detect infiltration) (FR-B02).",
    )
    audit_thorough_detection_chance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="[S] THOROUGH audit depth: P(detect infiltration) (FR-B02).",
    )
    audit_deep_detection_chance: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="[S] DEEP audit depth: P(detect infiltration) (FR-B02).",
    )

    # -------------------------------------------------------------------------
    # REPRESS Effects (FR-B06)
    # -------------------------------------------------------------------------
    infiltrate_informant_intel_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="[S] Per-tick intel gain from INFORMANT infiltration (FR-B06).",
    )
    infiltrate_provocateur_intel_rate: float = Field(
        default=0.03,
        ge=0.0,
        le=0.5,
        description="[S] Per-tick intel gain from PROVOCATEUR infiltration (FR-B06).",
    )
    infiltrate_mole_intel_rate: float = Field(
        default=0.08,
        ge=0.0,
        le=0.5,
        description="[S] Per-tick intel gain from MOLE infiltration (FR-B06).",
    )
    infiltrate_detection_base_chance: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[S] Base chance of infiltration detection per tick (FR-B06).",
    )
    raid_ci_radicalization_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="[S] CI above which RAID radicalizes instead of suppresses (FR-B06).",
    )
    raid_ci_radicalization_boost: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="[S] CI increase when RAID radicalizes high-CI territory (FR-B06).",
    )
    raid_ci_suppression_rate: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="[S] CI decrease when RAID suppresses low-CI territory (FR-B06).",
    )
    raid_org_coherence_damage: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="[S] Coherence reduction per RAID action (FR-B06).",
    )
    raid_key_figure_capture_base: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="[S] Base capture probability per known key figure (FR-B06).",
    )
    raid_force_multiplier_swat: float = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
        description="[S] SWAT force multiplier for RAID operations (FR-B06).",
    )
    raid_force_multiplier_military: float = Field(
        default=2.5,
        ge=1.0,
        le=10.0,
        description="[S] MILITARY force multiplier for RAID operations (FR-B06).",
    )
    prosecute_org_morale_damage: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="[S] Org coherence hit from prosecution proceedings (FR-B06).",
    )
    prosecute_key_figure_removal_chance: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="[S] P(conviction removes key figure) (FR-B06).",
    )
    prosecute_terrorism_charge_multiplier: float = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
        description="[S] Terrorism charges multiply all prosecution effects (FR-B06).",
    )
    prosecute_legitimacy_boost_success: float = Field(
        default=0.02,
        ge=0.0,
        le=0.1,
        description="[S] Legitimacy gained on successful conviction (FR-B06).",
    )
    liquidate_singleton_collapse_chance: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="[S] P(org collapses if singleton leader liquidated) (FR-B06).",
    )
    liquidate_core_legitimacy_cost: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="[S] Legitimacy cost of LIQUIDATE in core territory (FR-B06).",
    )
    liquidate_periphery_legitimacy_cost: float = Field(
        default=0.03,
        ge=0.0,
        le=0.5,
        description="[S] Legitimacy cost of LIQUIDATE in periphery territory (FR-B06).",
    )
    liquidate_deniability_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="[S] Deniability above which LIQUIDATE legitimacy cost halved (FR-B06).",
    )
    liquidate_coherence_damage: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="[S] Fixed coherence reduction from leadership liquidation (FR-B06).",
    )

    # -------------------------------------------------------------------------
    # LEGISLATE Consumption (FR-B09)
    # -------------------------------------------------------------------------
    emergency_powers_thread_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="[S] Thread pool multiplier under EMERGENCY_POWERS (FR-B09).",
    )
    emergency_powers_liquidate_in_core: bool = Field(
        default=True,
        description="[S] EMERGENCY_POWERS enables LIQUIDATE in core territories (FR-B09).",
    )
    surveillance_expansion_intel_bonus: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="[S] Per-tick intel bonus from SURVEILLANCE_EXPANSION legislation (FR-B09).",
    )

    # -------------------------------------------------------------------------
    # Debug (Phase 9)
    # -------------------------------------------------------------------------
    god_mode_enabled: bool = Field(
        default=False,
        description="When True, state AI decisions are exposed to player.",
    )


class InstitutionDefines(BaseModel):
    """Institution Base Model coefficients (Feature 040).

    Configures factional balance dynamics, Bonapartist threshold detection,
    and default structural selectivity modifiers per apparatus type.

    All thresholds are [S] SYNTHETIC unless otherwise noted.

    See Also:
        ``specs/040-institution-base-model/spec.md``: Full specification.
    """

    model_config = ConfigDict(frozen=True)

    # -------------------------------------------------------------------------
    # Balance Dynamics (FR-005)
    # -------------------------------------------------------------------------
    alpha_smoothing_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="[S] Per-call smoothing rate for factional balance shifts.",
    )
    bonapartist_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="[S] BONAPARTIST weight above which Bonapartist mode triggers.",
    )
    bonapartist_exclusion_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="[S] Other fractions must be below this for Bonapartist mode.",
    )

    # -------------------------------------------------------------------------
    # Default Structural Selectivity Modifiers (FR-007)
    # -------------------------------------------------------------------------
    # Keys: ApparatusType string values
    # Values: dict mapping ActionType string values to cost multipliers
    # < 1.0 = cheaper, > 1.0 = more expensive
    default_action_modifiers: dict[str, dict[str, float]] = Field(
        default={
            "rsa_executive": {"propagandize": 0.5, "repress": 0.8, "educate": 1.5},
            "rsa_police": {"repress": 0.6, "surveil": 0.7, "educate": 2.0},
            "rsa_judicial": {"surveil": 0.5, "repress": 1.2},
            "rsa_military": {"repress": 0.4, "attack_infrastructure": 0.5},
            "rsa_carceral": {"repress": 0.5, "educate": 2.5},
            "isa_educational": {"educate": 0.7, "recruit": 0.8, "repress": 2.0},
            "isa_religious": {"educate": 0.8, "recruit": 0.7, "repress": 2.5},
            "isa_family": {"educate": 0.9, "recruit": 1.5},
            "isa_communications": {"propagandize": 0.5, "agitate": 0.6, "repress": 2.0},
            "isa_cultural": {"educate": 0.8, "propagandize": 0.7, "repress": 2.0},
            "isa_legal": {},
            "isa_political": {},
            "economic_productive": {"employ": 0.5, "fundraise": 0.7, "repress": 1.5},
            "economic_financial": {"fundraise": 0.4, "employ": 0.8},
            "economic_extractive": {"fundraise": 0.5, "attack_infrastructure": 0.8},
        },
        description=(
            "[S] Default action cost modifiers per ApparatusType. "
            "Keys are ApparatusType values, sub-keys are ActionType values."
        ),
    )


class MobilizeDefines(BaseModel):
    """Configuration for MOBILIZE verb organizational actions."""

    model_config = ConfigDict(frozen=True)

    mobilize_cl_cost: float = Field(
        default=0.2,
        ge=0.0,
        description="[M] Consciousness Layer cost to initiate mobilization.",
    )
    min_consciousness: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="[M] Minimum target consciousness required to sustain mobilization.",
    )
    turnout_per_sl: float = Field(
        default=0.01,
        ge=0.0,
        description="[M] Percentage of population mobilized per Solidarity Level invested.",
    )
    solidarity_amplification_per_edge: float = Field(
        default=0.05,
        ge=0.0,
        description="[M] Solidarity multiplier applied per inbound solidaristic edge.",
    )
    heat_generation_per_demonstrator: float = Field(
        default=0.001,
        ge=0.0,
        description="[M] Heat generated per mobilized person.",
    )
    base_agitation_gain: float = Field(
        default=0.05,
        ge=0.0,
        description="[M] Base agitation level added to target territory on success.",
    )
    strike_value_disruption_factor: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="[M] Percentage of extracted value disrupted by strike action.",
    )
    max_demonstrators_before_backfire: int = Field(
        default=100_000,
        ge=0,
        description="[M] Maximum demonstrators before backfire dynamic engages.",
    )
    backfire_heat_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="[M] Heat penalty multiplier when mobilization backfires.",
    )
    backfire_agitation_gain: float = Field(
        default=0.15,
        ge=0.0,
        description="[M] Reverse agitation added due to backfire effect.",
    )


class MoveDefines(BaseModel):
    """MOVE verb coefficients."""

    expand_presence_split: float = Field(default=0.30)
    minimum_reception: float = Field(default=0.05)
    relocation_withdrawal_ticks: int = Field(default=3)
    expansion_edge_strain: float = Field(default=0.1)
    evasion_base_probability: float = Field(default=0.40)
    reacquire_ticks: int = Field(default=2)
    distance_ap_surcharge: int = Field(default=1)


class NegotiateDefines(BaseModel):
    """NEGOTIATE verb coefficients."""

    interest_weight: float = Field(default=0.6)
    leverage_weight: float = Field(default=0.4)
    institutional_leverage_weight: float = Field(default=0.8)
    negotiate_solidarity_increment: float = Field(default=0.05)
    betrayal_base_rate: float = Field(default=0.05)
    leverage_threshold_for_institutions: float = Field(default=0.50)


class GameDefines(BaseModel):
    """Centralized game coefficients extracted from hardcoded values.

    GameDefines collects numerical constants that were previously scattered
    across system implementations. By centralizing them here, we can:
    - Document their purpose and valid ranges
    - Override them per-scenario for calibration
    - Test the sensitivity of outcomes to coefficient changes

    The model is frozen (immutable) to ensure defines remain constant
    throughout a simulation run.

    Structure follows the YAML file organization:
    - crisis: Crisis detection and devaluation mechanics (Feature 018)
    - economy: Imperial rent extraction and value flow
    - survival: P(S|A) and P(S|R) survival calculus
    - solidarity: Consciousness transmission
    - behavioral: Behavioral economics (loss aversion)
    - tension: Tension dynamics
    - consciousness: Consciousness drift
    - territory: Territory dynamics
    - topology: Phase transition thresholds (gaseous/liquid/solid)
    - metabolism: Metabolic rift (ecological limits)
    - struggle: Struggle dynamics (Agency Layer)
    - carceral: Carceral equilibrium (Terminal Crisis Dynamics)
    - endgame: Endgame detection thresholds
    - initial: Initial conditions
    - contradiction_field: Dialectical field topology (Feature 002)
    - reserve_army: Reserve army of labor coefficients (Feature 021)
    - dispossession: Dispossession event intensity weights (Feature 021)
    - working_day: Working day characterization thresholds (Feature 021)
    - community: Hypergraph community layer coefficients (Feature 022)
    - class_dynamics: Class wealth flow dynamics (Feature 016, FRED DFA-derived)
    - edge_transition: Edge mode transition thresholds (Feature 002)
    - organization: Organization system coefficients (Feature 031)
    - ooda: OODA loop system coefficients (Feature 032)
    - class_system: Unified class system coefficients (Feature 038)
    - bifurcation: Bifurcation topology analysis coefficients (Feature 033)
    - infra_terrain: Terrain classification and biocapacity coefficients (Feature 036)
    - infrastructure: Infrastructure capacity and internet coefficients (Feature 036)
    """

    model_config = ConfigDict(frozen=True)

    crisis: CrisisDefines = Field(default_factory=CrisisDefines)
    mobilize: MobilizeDefines = Field(default_factory=MobilizeDefines)
    economy: EconomyDefines = Field(default_factory=EconomyDefines)
    survival: SurvivalDefines = Field(default_factory=SurvivalDefines)
    vitality: VitalityDefines = Field(default_factory=VitalityDefines)
    solidarity: SolidarityDefines = Field(default_factory=SolidarityDefines)
    behavioral: BehavioralDefines = Field(default_factory=BehavioralDefines)
    tension: TensionDefines = Field(default_factory=TensionDefines)
    consciousness: ConsciousnessDefines = Field(default_factory=ConsciousnessDefines)
    territory: TerritoryDefines = Field(default_factory=TerritoryDefines)
    topology: TopologyDefines = Field(default_factory=TopologyDefines)
    metabolism: MetabolismDefines = Field(default_factory=MetabolismDefines)
    struggle: StruggleDefines = Field(default_factory=StruggleDefines)
    carceral: CarceralDefines = Field(default_factory=CarceralDefines)
    endgame: EndgameDefines = Field(default_factory=EndgameDefines)
    initial: InitialDefines = Field(default_factory=InitialDefines)
    precision: PrecisionDefines = Field(default_factory=PrecisionDefines)
    timescale: TimescaleDefines = Field(default_factory=TimescaleDefines)
    external_data: ExternalDataDefines = Field(default_factory=ExternalDataDefines)
    contradiction_field: ContradictionFieldDefines = Field(
        default_factory=ContradictionFieldDefines
    )
    # Capital Volume I Production Dynamics (Feature 021)
    reserve_army: ReserveArmyDefines = Field(default_factory=ReserveArmyDefines)
    dispossession: DispossessionDefines = Field(default_factory=DispossessionDefines)
    working_day: WorkingDayDefines = Field(default_factory=WorkingDayDefines)
    # Hypergraph Community Layer (Feature 022)
    community: CommunityDefines = Field(default_factory=CommunityDefines)
    # Class Dynamics (Feature 016, FRED DFA-derived)
    class_dynamics: ClassDynamicsDefines = Field(default_factory=ClassDynamicsDefines)
    # Edge Transition Thresholds (Feature 002/028)
    edge_transition: EdgeTransitionDefines = Field(default_factory=EdgeTransitionDefines)
    # D-P-D' Lifecycle Circuit (Feature 030)
    lifecycle: LifecycleDefines = Field(default_factory=LifecycleDefines)
    # Organization Base Model (Feature 031)
    organization: OrganizationDefines = Field(default_factory=OrganizationDefines)
    # OODA Loop System (Feature 032)
    ooda: OODADefines = Field(default_factory=OODADefines)
    # Bifurcation Topology Analysis (Feature 033)
    bifurcation: BifurcationDefines = Field(default_factory=BifurcationDefines)
    # Infrastructure Topology Layer (Feature 036)
    infra_terrain: InfraTerrainDefines = Field(default_factory=InfraTerrainDefines)
    infrastructure: InfrastructureDefines = Field(default_factory=InfrastructureDefines)
    # Unified Class System (Feature 038)
    rent_circuit: RentCircuitDefines = Field(default_factory=RentCircuitDefines)
    class_system: ClassSystemDefines = Field(default_factory=ClassSystemDefines)
    # State Apparatus AI (Feature 039)
    state_ai: StateApparatusAIDefines = Field(default_factory=StateApparatusAIDefines)
    # Institution Base Model (Feature 040)
    institution: InstitutionDefines = Field(default_factory=InstitutionDefines)
    move: MoveDefines = Field(default_factory=MoveDefines)
    negotiate: NegotiateDefines = Field(default_factory=NegotiateDefines)

    # Legacy flat attributes for backward compatibility
    # These delegate to the nested structure

    @property
    def SUPERWAGE_IMPACT(self) -> float:
        """How much 1 unit of imperial extraction increases Core wealth."""
        return self.solidarity.superwage_impact

    @property
    def SOLIDARITY_SCALING(self) -> float:
        """Multiplier for graph edge weights affecting Organization."""
        return self.solidarity.scaling_factor

    @property
    def REPRESSION_BASE(self) -> float:
        """Base resistance to revolution in P(S|R) denominator."""
        return self.survival.repression_base

    @property
    def REVOLUTION_THRESHOLD(self) -> float:
        """The tipping point for P(S|R) formula."""
        return self.survival.revolution_threshold

    @property
    def DEFAULT_ORGANIZATION(self) -> float:
        """Fallback organization value when not specified on entity."""
        return self.survival.default_organization

    @property
    def DEFAULT_REPRESSION_FACED(self) -> float:
        """Fallback repression value when not specified on entity."""
        return self.survival.default_repression

    @property
    def DEFAULT_SUBSISTENCE(self) -> float:
        """Fallback subsistence threshold when not specified on entity."""
        return self.survival.default_subsistence

    @property
    def NEGLIGIBLE_TRANSMISSION(self) -> float:
        """Threshold below which transmissions are skipped as noise."""
        return self.solidarity.negligible_transmission

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> GameDefines:
        """Load GameDefines from a YAML file.

        Args:
            path: Path to the YAML file (absolute or relative)

        Returns:
            GameDefines instance populated from YAML

        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML is malformed
            pydantic.ValidationError: If values fail validation
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls._from_yaml_dict(data)

    @classmethod
    def _from_yaml_dict(cls, data: dict[str, Any]) -> GameDefines:
        """Create GameDefines from parsed YAML dictionary.

        Args:
            data: Parsed YAML data

        Returns:
            GameDefines instance
        """
        if data is None:
            data = {}

        # Parse external_data section with nested arcgis/services
        external_data_raw = data.get("external_data", {})
        external_data = ExternalDataDefines(
            arcgis=ArcGISDefines(**external_data_raw.get("arcgis", {})),
            services=ServicesDefines(**external_data_raw.get("services", {})),
        )

        return cls(
            mobilize=MobilizeDefines(**data.get("mobilize", {})),
            crisis=CrisisDefines(**data.get("crisis", {})),
            economy=EconomyDefines(**data.get("economy", {})),
            survival=SurvivalDefines(**data.get("survival", {})),
            vitality=VitalityDefines(**data.get("vitality", {})),
            solidarity=SolidarityDefines(**data.get("solidarity", {})),
            behavioral=BehavioralDefines(**data.get("behavioral", {})),
            tension=TensionDefines(**data.get("tension", {})),
            consciousness=ConsciousnessDefines(**data.get("consciousness", {})),
            territory=TerritoryDefines(**data.get("territory", {})),
            topology=TopologyDefines(**data.get("topology", {})),
            metabolism=MetabolismDefines(**data.get("metabolism", {})),
            struggle=StruggleDefines(**data.get("struggle", {})),
            carceral=CarceralDefines(**data.get("carceral", {})),
            endgame=EndgameDefines(**data.get("endgame", {})),
            initial=InitialDefines(**data.get("initial", {})),
            precision=PrecisionDefines(**data.get("precision", {})),
            timescale=TimescaleDefines(**data.get("timescale", {})),
            external_data=external_data,
            contradiction_field=ContradictionFieldDefines(**data.get("contradiction_field", {})),
            community=CommunityDefines(**data.get("community", {})),
            class_dynamics=ClassDynamicsDefines(**data.get("class_dynamics", {})),
            reserve_army=ReserveArmyDefines(**data.get("reserve_army", {})),
            dispossession=DispossessionDefines(**data.get("dispossession", {})),
            working_day=WorkingDayDefines(**data.get("working_day", {})),
            edge_transition=EdgeTransitionDefines(**data.get("edge_transition", {})),
            lifecycle=LifecycleDefines(**data.get("lifecycle", {})),
            organization=OrganizationDefines(**data.get("organization", {})),
            ooda=OODADefines(**data.get("ooda", {})),
            bifurcation=BifurcationDefines(**data.get("bifurcation", {})),
            infra_terrain=InfraTerrainDefines(**data.get("infra_terrain", {})),
            infrastructure=InfrastructureDefines(**data.get("infrastructure", {})),
            rent_circuit=RentCircuitDefines(**data.get("rent_circuit", {})),
            class_system=ClassSystemDefines(**data.get("class_system", {})),
            state_ai=StateApparatusAIDefines(**data.get("state_ai", {})),
            institution=InstitutionDefines(**data.get("institution", {})),
            move=MoveDefines(**data.get("move", {})),
            negotiate=NegotiateDefines(**data.get("negotiate", {})),
        )

    @classmethod
    def default_yaml_path(cls) -> Path:
        """Return the conventional path for an optional ``defines.yaml`` override.

        The repository does not ship a ``defines.yaml`` (the file was removed
        in commit ``4ce7c96a`` when the data layer was extracted). Callers
        may drop a YAML at this path to override the dataclass defaults
        compiled into :class:`GameDefines`; if the file is absent,
        :meth:`load_default` returns the dataclass defaults unchanged.

        Returns:
            ``Path`` pointing at ``src/babylon/data/defines.yaml`` (which
            may or may not exist on disk).
        """
        return Path(__file__).parent.parent / "data" / "defines.yaml"

    @classmethod
    def load_default(cls) -> GameDefines:
        """Load :class:`GameDefines`, preferring the optional YAML override.

        If ``src/babylon/data/defines.yaml`` exists, it is loaded as a
        full override of the dataclass defaults. Otherwise the dataclass
        defaults are returned. The repository ships without the YAML, so
        the dataclass defaults are the canonical values today.

        Returns:
            ``GameDefines`` instance — YAML-loaded if present, otherwise
            the dataclass defaults.
        """
        default_path = cls.default_yaml_path()
        if default_path.exists():
            return cls.load_from_yaml(default_path)
        return cls()
