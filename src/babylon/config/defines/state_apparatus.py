"""State Apparatus AI and Institution Base Model (Features 039 + 040).

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "InstitutionDefines",
    "StateApparatusAIDefines",
]
