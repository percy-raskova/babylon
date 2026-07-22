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

    # ------------------------------------------------------------------ Θ_feel
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
            "(party→class base reach). The media (ISA_COMM) and betrayal "
            "(delivery-gap) drift terms arrive with their producers "
            "(media apparatus program; U9 PolicySystem)."
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
