"""Organization model, lifecycle, and atomic action verbs.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    expand_presence_split: float = Field(
        default=0.30,
        description="Fraction of the org's presence allocated to the new territory when MOVE runs in 'expand' mode (spec-049).",
    )
    minimum_reception: float = Field(
        default=0.05,
        description="Floor on the community-reception score used to modulate presence establishment in a destination territory (spec-049).",
    )
    relocation_withdrawal_ticks: int = Field(
        default=3,
        description="Number of ticks over which origin-territory presence phases down to zero during a 'relocate' MOVE (spec-049).",
    )
    expansion_edge_strain: float = Field(
        default=0.1,
        description="Maintenance strain added to origin-territory edges when MOVE expands into an additional territory (spec-049).",
    )
    evasion_base_probability: float = Field(
        default=0.40,
        description="Base surveillance-evasion probability before heat scaling (evasion = base * (1 - heat), spec-049).",
    )
    reacquire_ticks: int = Field(
        default=2,
        description="Ticks of operational freedom before state attention threads reacquire the org after a successful MOVE evasion (spec-049).",
    )
    distance_ap_surcharge: int = Field(
        default=1,
        description="Action-point surcharge per hex hop beyond an adjacent territory when moving (spec-049).",
    )


class NegotiateDefines(BaseModel):
    """NEGOTIATE verb coefficients."""

    interest_weight: float = Field(
        default=0.6,
        description="Weight on interest alignment in the NEGOTIATE success-probability blend (spec-050).",
    )
    leverage_weight: float = Field(
        default=0.4,
        description="Weight on org leverage in the NEGOTIATE success-probability blend for non-institutional targets (spec-050).",
    )
    institutional_leverage_weight: float = Field(
        default=0.8,
        description="Leverage weight substituted for institutional targets, which respond to power over shared values (spec-050).",
    )
    negotiate_solidarity_increment: float = Field(
        default=0.05,
        description="Amount solidarity accumulation increments when a successful NEGOTIATE strengthens an existing TRANSACTIONAL edge (spec-050).",
    )
    betrayal_base_rate: float = Field(
        default=0.05,
        description="Base rate at which a formed alliance degrades or is betrayed (spec-050 betrayal-risk baseline).",
    )
    leverage_threshold_for_institutions: float = Field(
        default=0.50,
        description="Minimum org leverage below which the institutional-target leverage check warns (non-blocking, spec-050 / Constitution I.11).",
    )


__all__ = [
    "CommunityDefines",
    "LifecycleDefines",
    "MobilizeDefines",
    "MoveDefines",
    "NegotiateDefines",
    "OrganizationDefines",
]
