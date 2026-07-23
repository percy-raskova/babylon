"""The ``politics:`` defines namespace (Program 25, the-electoral-question.md §5.3).

Coefficients for the ambient electoral machine and the doctrine fork, with A6
tiers declared at birth (ADR127): **Θ_data** — terrain facts calibrated against
observed returns; **Θ_theory** — signs and bounds the theory fixes (the valve
suppresses, the social wage never mints value); **Θ_feel** — pacing knobs that
set *how long hope takes to die*, never whether the ceiling exists.

Every field names its consuming unit (U7–U12 of the P25 train); the U13 defines
sweep re-verifies that no field ships unread (the Vol I U8 lesson).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CLOCK_LEVELS = frozenset({"federal", "state", "local"})


class PoliticsDefines(BaseModel):
    """Ambient electoral-machine + doctrine-fork coefficients (P25/ADR127)."""

    model_config = ConfigDict(frozen=True)

    # ------------------------------------------------------------------ Θ_data
    cycle_ticks: dict[str, int] = Field(
        default={"federal": 104, "state": 104, "local": 52},
        description=(
            "Θ_data — election clock per JurisdictionLevel, in ticks "
            "(1 tick = 1 week): federal/state biennial (104), local annual "
            "(52). Consumed by ElectoralSystem's clock (U10, the "
            "congress_interval_ticks idiom). Terrain fact; per-sovereign "
            "electoral RULES (FPTP thresholds, ballot access, "
            "malapportionment) arrive with the MIT Election Lab data tier "
            "at U6/U10, not as scalars here."
        ),
    )
    base_turnout: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_data — base turnout rate before allegiance-concentration, "
            "hope, and suppression modifiers (U10 turnout law). Calibrated "
            "against VAP turnout in the IV window (~0.5-0.6 presidential)."
        ),
    )

    # ---------------------------------------------------------------- Θ_theory
    capital_tolerance: float = Field(
        default=0.15,
        gt=0.0,
        le=1.0,
        description=(
            "Θ_theory — the policy-incidence share of measured surplus "
            "beyond which the capital veto arms (investment strike via the "
            "equalization operator + bond discipline; U9 §2.4). The "
            "SHAPE (a finite tolerance exists) is theory; the value is "
            "calibrated by the mitterrand golden at U13."
        ),
    )
    phi_social_share: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_theory — the maximum slice of Φ pool inflow routable into "
            "the social wage (U9 funding identity: SW_deliverable = "
            "min(SW_promised, t_claim + phi_social_share·Φ_inflow − "
            "debt_service)). Bounded ≤ 1.0 as the anti-list row: no θ may "
            "let the social wage exceed measured surplus — reform "
            "redistributes, it never mints value (L-CEILING, T-6's premise)."
        ),
    )

    policy_agenda_rate: int = Field(
        default=1,
        ge=1,
        description=(
            "Θ_theory — maximum agenda items the LEGISLATE resolver executes "
            "per tick (U9 §2.3: the agenda is 'executed through LEGISLATE at "
            "a bounded rate'). The SHAPE (a finite legislative throughput "
            "exists) is theory; also the static loop bound on PolicySystem's "
            "agenda pass."
        ),
    )
    debt_finance_share: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_theory — share of an unfunded social-wage promise the state "
            "debt-finances instead of under-delivering (U9 §2.4 bond "
            "discipline: 'borrowing against unfunded promises opens the "
            "scissors'). The borrowed principal enters the sovereign debt "
            "stock; next tick's debt_service = endogenous rate × stock "
            "shrinks the funded ceiling — O'Connor's fiscal crisis as "
            "arithmetic. 0 = pure pay-go, 1 = full deficit finance."
        ),
    )
    bond_discipline_threshold: float = Field(
        default=0.25,
        gt=0.0,
        description=(
            "Θ_theory — the serviceability tightener (U9 §2.4 arm 2): once "
            "debt_service / t_claim exceeds this ratio, further deficit "
            "financing is refused and delivery collapses to the funded "
            "ceiling alone. The SHAPE (bond markets discipline unfunded "
            "promises) is theory; the value is calibrated by the mitterrand "
            "golden at U13."
        ),
    )
    judicial_tolerance_scale: float = Field(
        default=0.5,
        ge=0.0,
        description=(
            "Θ_theory — judicial strike-down tolerance = scale × the "
            "striking RSA_JUDICIAL institution's "
            "InternalBalanceOfForces.liberal_technocratic weight (U9 §2.4 "
            "arm 3: a liberal court tolerates more redistribution than a "
            "revanchist one). Policy incidence above the tolerance is "
            "voided (POLICY_STRUCK)."
        ),
    )
    preemption_envelope: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_theory — maximum overlay magnitude a LOWER sovereign on the "
            "ADMINISTERS DAG may enact before the higher sovereign nullifies "
            "it (U9 §2.4 arm 4, POLICY_PREEMPTED — the municipal-socialism "
            "ceiling: Seattle passes the wage; the state legislature erases "
            "it). U9 proxy for the governing platform's envelope, which "
            "replaces this scalar at U10."
        ),
    )
    recount_margin: float = Field(
        default=0.005,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_theory — the recount-grade tie window (U10): only when the "
            "top-two vote shares sit within this margin does the election "
            "resolve through ξ_t (the congress-purge III.7 precedent — one "
            "seeded draw, deterministic per tick); wider margins resolve "
            "deterministically by the count. The SHAPE (contingency enters "
            "ONLY at recount grain, Bush-v-Gore scale) is theory."
        ),
    )
    # ------------------------------------------------------------------ Θ_feel
    strike_equalization_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — α for the capital-strike application of the "
            "equalization operator Δc = α(r − r̄)c over the enacting "
            "sovereign's claimed counties (U9 §2.4 arm 1: policy incidence "
            "past capital_tolerance enters as a local profit-rate penalty; "
            "capital migrates out, ΣΔc = 0). Distinct from "
            "economy.alpha_annual (Spec 062's ambient hex-grain rate): this "
            "is the STRIKE-response rate, event-gated, county-grain."
        ),
    )
    policy_default_magnitude: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — overlay magnitude for agenda items the state AI "
            "drafts through the LEGISLATE sub-verb when no explicit "
            "magnitude is carried (U9; StateAction.parameters ships empty "
            "today). Scenario-seeded and U10 platform-drafted items carry "
            "their own magnitudes."
        ),
    )
    valve_strength: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — v in the valve law: Agitation→Organization conversion "
            "×= (1 − v·H(c)) (U8). Bounded [0,1] so hope SUPPRESSES and "
            "never amplifies organizing (the Θ_theory sign law lives in the "
            "bound); 0 disables the valve, 1 lets saturated hope halt "
            "conversion entirely. L-VALVE pins monotonicity in this knob."
        ),
    )
    hope_spike_gain: float = Field(
        default=0.3,
        ge=0.0,
        description=(
            "Θ_feel — HOPE_SPIKE event gain applied to H(c) on viable-"
            "platform emergence (U8; the Bernie-surge steepness knob)."
        ),
    )
    organizing_conversion_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — base per-tick Agitation→Organization conversion "
            "efficiency, the REAL quantity the valve throttles "
            "(U8/ADR134: organization += rate·agitation·(1−v·H), the "
            "first production increase pathway for the P(S|R) numerator; "
            "TRAP 1 ruling — never the consciousness router). Bounded "
            "[0,1]; pacing calibrated by the bernie_valve golden at U13."
        ),
    )
    allegiance_align_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — θ.align in the allegiance-drift law (U8 §2.2): "
            "per-tick pull toward parties whose platform fits the class's "
            "interest vector (material interest term)."
        ),
    )
    allegiance_contact_rate: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — θ.contact in the allegiance-drift law (U8 §2.2): "
            "per-tick organizing-contact pull along MEMBERSHIP edges "
            "(party→class base reach). The media (ISA_COMM) drift term "
            "arrives with its producer (media apparatus program); the "
            "betrayal term landed with U9's delivery-gap register "
            "(allegiance_betrayal_rate)."
        ),
    )
    allegiance_betrayal_rate: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — θ.betrayal in the allegiance-drift law (U8 §2.2, "
            "producer landed U9/ADR135): per-tick allegiance repulsion from "
            "an incumbent per unit of PRIOR-tick delivery gap (PolicySystem "
            "@17.47 writes the per-class gap register; AllegianceSystem "
            "@17.42 reads it next tick — the one-tick lag is the I-ORD "
            "grain). Betrayal outpaces alignment by default "
            "(0.04 vs 0.05·fit): delivered promises are forgiven, broken "
            "ones compound toward the U10 betrayal integral."
        ),
    )
    disillusion_window_ticks: int = Field(
        default=26,
        ge=1,
        description=(
            "Θ_feel — duration of the boosted-conversion disillusion window "
            "after loss/suspension/betrayal rupture (U10 H-collapse; T-7 "
            "routes the boost by SOLIDARITY topology). Default half a year."
        ),
    )
    disillusion_conversion_boost: float = Field(
        default=2.0,
        ge=1.0,
        description=(
            "Θ_feel — the disillusion window's conversion multiplier (U10 "
            "T-7 routing): bridges present ⟹ the Agitation→Organization "
            "valve conversion multiplies by this (the Bernie→DSA surge); "
            "bridges absent ⟹ the excess routes into fascist_alignment "
            "instead (the Obama→Trump pipeline). Bounded ≥ 1 — a window "
            "never suppresses; the topology only chooses the DIRECTION."
        ),
    )
    legitimation_refresh_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — election-day consent blend (U10 §2.5): "
            "legitimation_index moves toward turnout×competitiveness by "
            "this fraction on ELECTION_HELD. 1.0 = the ritual fully resets "
            "consent each cycle; 0.0 disables the refresh circuit."
        ),
    )
    betrayal_threshold: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "Θ_feel — the accumulated delivery-gap integral b(c) = Σ gap at "
            "which patience ruptures into a disillusion window regardless "
            "of the next cycle's promises (U10; the SYRIZA-voter curve)."
        ),
    )
    office_capture_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — per-tenure-tick drift of an org's effective line "
            "toward its officeholders' institutional median (U11 "
            "institutional_pull; Michels' iron law as a rate, resisted by "
            "cadre_level and cohesion)."
        ),
    )
    split_asset_retention: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — share of branch-specific assets retained through a "
            "line-change split at congress (U11; electeds rarely follow you "
            "out; canvass-cadre skills convert below par)."
        ),
    )
    sect_isolation_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — per-tick MASS_LINK decay while boycotting a live hope "
            "field the org's own base carries (U11 Principled Abstention "
            "stance; the sect death spiral, priced)."
        ),
    )
    boycott_conversion: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — efficiency of Campaign(Election, mode=BOYCOTT) at "
            "converting ambient H into agitation (U11; dominant only where "
            "legitimacy is already broken)."
        ),
    )
    popular_front_trigger: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — the fascist_consolidation axis_progress at which the "
            "popular-front conjuncture fires for EVERY line (U12 §3.4; "
            "Third Period vs Popular Front, forced)."
        ),
    )
    donor_platform_weight: float = Field(
        default=0.35,
        ge=0.0,
        description=(
            "Θ_feel — θ.politics.donor_platform_weight in the derived "
            "platform vector (U7 §2.1: donor funding-share pull vs base "
            "composition; the Brahmin-left capture knob)."
        ),
    )
    suppression_cost_weight: float = Field(
        default=0.2,
        ge=0.0,
        description=(
            "Θ_feel — turnout penalty per unit of REPRESSION exposure / "
            "carceral disenfranchisement pressure (U10 turnout law; the "
            "franchise is class-differential, from data)."
        ),
    )
    host_threat_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — intra-host influence share past which the host "
            "machine runs derecognition counter-play against an entryist "
            "org (U11; superdelegates as INCORPORATE, primary purges as "
            "DIVIDE)."
        ),
    )
    legitimacy_backfire_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — legitimation_index floor below which each Repress "
            "action converts to agitation at the multiplied "
            "repression_backfire rate (U10 §2.5 wiring of the existing "
            "consciousness-defines coefficient)."
        ),
    )
    solidarity_liquidation_floor: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — the SOLIDARITY_MASS practice-variable floor in the "
            "liquidationism absorbing-state trap_condition (U11 §3.1: "
            "SOLIDARITY_MASS <= @solidarity_liquidation_floor). Referenced "
            "by NAME from the doctrine-tree DSL (III.1: no magic thresholds "
            "in the data — the condition traces to this coefficient)."
        ),
    )
    co_optive_liquidation_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — the CO_OPTIVE_SHARE practice-variable trigger in the "
            "liquidationism absorbing-state trap_condition (U11 §3.1: "
            "CO_OPTIVE_SHARE >= @co_optive_liquidation_threshold). The org "
            "dissolved into the movement's left wing — measurably."
        ),
    )
    petty_bourgeois_liquidation_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — the PETTY_BOURGEOIS_DRIFT practice-variable trigger in "
            "the liquidationism absorbing-state trap_condition (U11 §3.1: "
            "PETTY_BOURGEOIS_DRIFT >= @petty_bourgeois_liquidation_threshold). "
            "Drift is a CONTINUOUS material proxy (membership-base class "
            "composition), never the discrete class_character label."
        ),
    )
    debs_solidarity_efficiency: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — η_cse: Campaign(Election, mode=RUN) converts campaign "
            "labour into SOLIDARITY edges at this fraction of the mass-work "
            "base per hour (U11 Debs/Class-Struggle stance; below base but "
            "with the electoral reach multiplier — a real recruitment engine, "
            "near-zero governance probability)."
        ),
    )
    class_analysis_veto_decay: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — CLASS_ANALYSIS decays at this rate per unit of a "
            "governing org's delivery gap (promised − delivered, from the "
            "policy_delivery register) (U11 §3.1 Unit-6b extended: theory "
            "rots when the line predicts deliveries the ceiling then vetoes; "
            "the gap is the veto's material trace)."
        ),
    )
    reformist_theory_decay: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — CLASS_ANALYSIS erosion rate under co-optive practice "
            "(CO_OPTIVE_SHARE + institutional_pull) (U11 §3.1/§3.3: the "
            "re-founded reformist trunk's tag drift comes from PRACTICE, not "
            "acquisition tag_deltas; Michels' iron law as theory-rot)."
        ),
    )
    entryism_cooptation_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — per-tick CO_OPTIVE dependency an entryist org accrues "
            "operating inside a host machine (U11 §3.2 Entryism within-fence "
            "cost: the priced drift toward the liquidationism absorbing "
            "state; host-derecognition counter-play itself is U12/state_ai)."
        ),
    )
    entryism_membership_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Θ_feel — weight of MEMBERSHIP edges an entryist org mints on an "
            "H spike (U11 §3.2 paper-membership: the surge is real, the "
            "power is not — Organization, the P(S|R) numerator, is weighted "
            "edge density, not headcount)."
        ),
    )

    @field_validator("cycle_ticks")
    @classmethod
    def _clocks_cover_levels_and_are_positive(cls, value: dict[str, int]) -> dict[str, int]:
        """Every JurisdictionLevel keyed, every clock a strictly positive tick count."""
        if set(value) != _CLOCK_LEVELS:
            raise ValueError(
                f"cycle_ticks must key exactly {sorted(_CLOCK_LEVELS)}; got {sorted(value)}"
            )
        bad = {level: ticks for level, ticks in value.items() if ticks < 1}
        if bad:
            raise ValueError(f"cycle_ticks must be >= 1 tick per level; got {bad}")
        return value
