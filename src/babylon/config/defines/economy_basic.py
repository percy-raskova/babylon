"""Top-level economic mechanics: crisis detection and imperial rent.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "CrisisDefines",
    "EconomyDefines",
]
