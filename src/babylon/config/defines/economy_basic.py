"""Top-level economic mechanics: crisis detection and imperial rent.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from babylon.config.defines.cross_scale import (
    CoefficientLookupPolicy,
    LookupPolicy,
)


def _default_lookup_policies() -> dict[str, CoefficientLookupPolicy]:
    """Build the 11-entry default registry per data-model.md §2.5.

    Spec 062, T041. Used by ``EconomyDefines.coefficient_lookup_policies``
    via ``default_factory`` so the registry is populated for every fresh
    :class:`GameDefines` instance.
    """
    policies = [
        ("bea_io_intermediate", LookupPolicy.SLOWLY_VARYING, "BEA Make-Use 2010-2024"),
        ("bea_io_imports", LookupPolicy.SLOWLY_VARYING, "BEA Imports Matrix 2010-2024"),
        ("melt_tau", LookupPolicy.SLOWLY_VARYING, "MELT τ annual aggregate"),
        ("basket_gamma", LookupPolicy.SLOWLY_VARYING, "Basket visibility γ"),
        ("erdi_ratio", LookupPolicy.SLOWLY_VARYING, "ERDI productivity ratios"),
        ("hickel_drain", LookupPolicy.SLOWLY_VARYING, "Hickel et al. Φ_year"),
        ("qcew_wages", LookupPolicy.SLOWLY_VARYING, "BLS QCEW annual wages"),
        ("bea_reis_rent", LookupPolicy.SLOWLY_VARYING, "BEA REIS rent series"),
        ("fred_fed_funds_rate", LookupPolicy.EVENT_DISCRETE, "FRED FEDFUNDS"),
        ("regulatory_regime", LookupPolicy.EVENT_DISCRETE, "Federal regulatory regime"),
        ("datacenter_came_online", LookupPolicy.EVENT_DISCRETE, "Datacenter commission events"),
    ]
    return {
        series_id: CoefficientLookupPolicy(
            series_id=series_id, policy=policy, canonical_reference=ref
        )
        for series_id, policy, ref in policies
    }


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

    # Tension thresholds for bourgeoisie decisions.
    #
    # Lawverian recalibration (Phase C1.5): the bourgeoisie now reads the
    # capital_labor OPPOSITION GAP (scale-free wealth asymmetry in [0, 1],
    # ImperialRentSystem._calculate_aggregate_tension) instead of the old
    # add-only mean edge tension. The gap has a different range, so the
    # thresholds are recalibrated against measured worlds:
    #
    #   Bridged labor-aristocracy (county 26163, 45-tick engine probe): the
    #   capital_labor gap peaks at 0.667 (t1, worker≈2 vs bourgeois≈10) and
    #   settles ~0.42-0.44 as the income circuit lifts the worker. It never
    #   exceeds 0.7 while the rent pool is high.
    #
    #   Canonical super-exploited periphery: worker wealth ~0.8-2, bourgeois
    #   ~10-35 → gap = |b-w|/(b+w) ≈ 0.67 (w=2,b=10) up to 0.94 (w=1,b=35),
    #   typically ~0.85-0.95.
    #
    # bribery=0.70 sits just above the bridged aristocracy's 0.667 peak (so
    # BRIBERY holds whenever the pool is high — hegemony per project/02 §3)
    # and below the periphery's ~0.85 floor (so the super-exploited are never
    # bribed — only the aristocracy is, per Cope/Amin).
    bribery_tension_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Maximum capital_labor opposition gap for bribery policy (C1.5).",
    )
    # iron_fist stays 0.5: when the pool collapses (pool < low), the bridged
    # aristocracy (gap 0.42-0.667 > 0.5) draws IRON_FIST = repression, NOT
    # AUSTERITY = wage cuts — the historically correct response to core-worker
    # unrest and the one that preserves the income keeping them alive
    # (liveness gate). The canonical periphery (gap ~0.85-0.95 > 0.5) also
    # draws IRON_FIST when the pool collapses.
    iron_fist_tension_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum capital_labor opposition gap for iron fist policy (C1.5).",
    )

    # TRPF efficiency floor
    trpf_efficiency_floor: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum extraction efficiency after TRPF decay",
    )

    # Spec 057 — Leontief imperial-rent pipeline tunables
    leontief_rent: LeontiefRentDefines = Field(
        default_factory=lambda: LeontiefRentDefines(),
        description="Tunables for the Leontief imperial-rent integration (Spec 057)",
    )

    # Spec 062 — Cross-scale integration tunables (FR-029, FR-029a, FR-046, FR-004a)
    alpha_annual: float = Field(
        default=0.01,
        ge=0.0,
        lt=1.0,
        description=(
            "Annual capital-equalization rate alpha (Spec 062, FR-029). "
            "Geometric weekly form derived via alpha_weekly(alpha_annual). "
            "Default 0.01 matches HexEqualizationComputer's prior calibration."
        ),
    )
    epsilon_conservation: float = Field(
        default=1e-10,
        gt=0.0,
        le=1e-3,
        description=(
            "Conservation-residual tolerance epsilon (Spec 062, FR-046 / SC-002). "
            "Audit rows with |residual| <= epsilon receive severity='ok'."
        ),
    )
    scenario_length_years: int = Field(
        default=15,
        ge=1,
        le=200,
        description=(
            "Immutable scenario length in years (Spec 062, FR-004a). "
            "Reference-series copy spans [start_year, start_year + scenario_length_years]."
        ),
    )
    coefficient_lookup_policies: dict[str, CoefficientLookupPolicy] = Field(
        default_factory=lambda: _default_lookup_policies(),
        description=(
            "Per-series lookup policies for the immutable_reference_* family "
            "(Spec 062, FR-011 / data-model.md §2.5). The default registry "
            "covers the 11 canonical series enumerated in data-model.md §2.5."
        ),
    )

    # Spec 063 closure — hex hydration uniform allocation defaults (2026-05-14)
    initial_c_to_v_ratio: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description=(
            "Initial organic composition of capital used by the hex hydrator: "
            "per-hex c = v * initial_c_to_v_ratio. Default 2.0 is a mid-range "
            "Marxist OCC; downstream specs can re-calibrate empirically."
        ),
    )
    initial_k_to_v_ratio: float = Field(
        default=10.0,
        ge=0.0,
        le=50.0,
        description=(
            "Initial capital-stock to variable-capital ratio used by the hex "
            "hydrator: per-hex K = v * initial_k_to_v_ratio. Default 10.0 "
            "approximates a ~10-year accumulated K relative to annual wages."
        ),
    )

    # Spec 063 — Vol II Circulation System with LODES OD (FR-031..FR-036)
    border_commute_share: float = Field(
        default=0.50,
        gt=0.0,
        le=1.0,
        description=(
            "Spec 063, FR-034 — fraction of Detroit-Windsor personal-vehicle "
            "crossings attributable to commuters (vs tourists/shoppers). "
            "Default 0.50 traces to Workforce WindsorEssex 2017 Cross-Border "
            "Employment Report: ~6,120 commuters / ~12K daily personal-vehicle "
            "crossings. Constitution III.1: cited, not magic."
        ),
    )
    enable_border_commute_synthesis: bool = Field(
        default=False,
        description=(
            "Spec 063, FR-031 — opt-in flag for the Option B border-commute "
            "synthesis loader (BTS + StatCan + WWE share anchor). When True, "
            "session init reads BTS Border Crossing CSV from "
            "data-trove/border_crossings/ and merges synthesized weekly "
            "Canadian-bound aggregate rows into the LODES year matrix. When "
            "False, behavior is identical to the LODES-only path."
        ),
    )

    @property
    def alpha_weekly(self) -> float:
        """Geometric weekly equalization rate derived from alpha_annual.

        Implements ``alpha_weekly = 1 - (1 - alpha_annual)^(1/52)`` so that
        compounding 52 weekly applications reproduces the annual rate.
        Required to satisfy FR-029a startup invariant ``alpha_weekly < 1/52``.
        """
        from babylon.economics.geometric_depreciation import alpha_weekly

        return alpha_weekly(self.alpha_annual)


class LeontiefRentDefines(BaseModel):
    """Tunables for the Spec 057 Leontief imperial-rent pipeline.

    Lifted to GameDefines per Constitution III.1 (No Magic Constants):
    every numeric tunable in the new ``imperial_rent.compute()`` pipeline
    must trace to a configured constant rather than a literal in code.

    See ``specs/057-leontief-rent-integration/data-model.md`` for the
    field-level rationale.
    """

    model_config = ConfigDict(frozen=True)

    qcew_carry_forward_max_years: Annotated[int, Field(ge=0, le=20)] = 5
    """Maximum look-back window (in years) for QCEW carry-forward fallback in
    :class:`babylon.economics.tensor_hierarchy.leontief_rent.industry_to_county_allocator.IndustryToCountyAllocator`
    (per Spec 057 / FR-004 + Clarifications 2026-05-08). ``0`` disables
    carry-forward (strict no-data semantics).
    """

    phi_hour_outlier_threshold_low: float = Field(
        default=-1000.0,
        description=(
            "Per-county phi_hour values below this trigger a "
            "PhiHourOutlierEvent via EventBus (Spec 057 / FR-008). "
            "Pre-clamp negative values cannot reach phi_hour because of the "
            "two-layer axiom enforcement (research.md §R5); this threshold "
            "is defense-in-depth and validation only."
        ),
    )

    phi_hour_outlier_threshold_high: float = Field(
        default=1000.0,
        description=(
            "Per-county phi_hour values above this trigger a "
            "PhiHourOutlierEvent via EventBus (Spec 057 / FR-008)."
        ),
    )


__all__ = [
    "CrisisDefines",
    "EconomyDefines",
    "LeontiefRentDefines",
]
