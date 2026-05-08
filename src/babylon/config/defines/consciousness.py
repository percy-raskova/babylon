"""Consciousness, solidarity, contradiction-field and bifurcation coefficients.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "BifurcationDefines",
    "ConsciousnessDefines",
    "ContradictionFieldDefines",
    "EdgeTransitionDefines",
    "SolidarityDefines",
]
