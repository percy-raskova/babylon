"""Epistemic Horizon (fog of war) coefficients — Phase 1 SHADOW ONLY.

Program: ``project/research/epistemic-horizon-program-proposal.md``. Source
formulas + the three worked ``M_r`` examples: ``ai/epochs/epoch3/fog-of-war.yaml``
lines 86-330 ("Slice 2.10: The Epistemic Horizon"). All numerics below are
theory-corpus-derived tunables, overridable via ``defines.yaml`` like every
other category (Constitution "never hardcode a coefficient").

Phase 1 scope: the :class:`~babylon.engine.systems.epistemic_horizon.EpistemicHorizonSystem`
computes ``mass_receptivity`` / ``intel_confidence`` / ``vision_state`` as
SHADOW (write-only, non-gating) territory node attrs. No masking, no reveal
gating, no Investigate wiring — that is Phase 2/3 territory per the program doc.

Re-exported via :mod:`babylon.config.defines.__init__`; composed into
:class:`babylon.config.defines.GameDefines` in
:mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EpistemicHorizonDefines(BaseModel):
    """Tunable coefficients for the Phase 1 Epistemic Horizon shadow system.

    ``class_factor_*`` maps the corpus's 4 explicitly-named class factors
    (fog-of-war.yaml:195-236: proletariat, lumpenproletariat, petty_bourgeoisie,
    labor_aristocracy) onto the real ``SocialRole`` enum members
    (``PERIPHERY_PROLETARIAT``, ``LUMPENPROLETARIAT``, ``PETTY_BOURGEOISIE``,
    ``LABOR_ARISTOCRACY``). Any ``SocialRole`` NOT in that table (e.g.
    ``CORE_BOURGEOISIE``, ``COMPRADOR_BOURGEOISIE``, ``INTERNAL_PROLETARIAT``,
    ``CARCERAL_ENFORCER``) falls through to ``class_factor_default`` — an
    explicit defines value, never a silent 1.0/0.0-by-omission (Constitution
    III.11 honest-null extends to coefficient lookups, not just missing data).
    """

    model_config = ConfigDict(frozen=True)

    base_observation: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="B_o: public baseline intel confidence, always visible without any presence (fog-of-war.yaml:106-117).",
    )
    desert_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="M_r below this is Desert vision state (fog-of-war.yaml:274).",
    )
    water_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="M_r at/above this is Water vision state (fog-of-war.yaml threshold table, ~line 322). M_r in between is Mud.",
    )
    class_factor_periphery_proletariat: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="C_f for PERIPHERY_PROLETARIAT — corpus 'proletariat' P_w (fog-of-war.yaml:203-209).",
    )
    class_factor_lumpenproletariat: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="C_f for LUMPENPROLETARIAT — corpus 'lumpenproletariat' L_u (fog-of-war.yaml:211-218).",
    )
    class_factor_petty_bourgeoisie: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="C_f for PETTY_BOURGEOISIE — corpus C_pb, hedges bets (fog-of-war.yaml:220-227).",
    )
    class_factor_labor_aristocracy: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="C_f for LABOR_ARISTOCRACY — corpus C_la, informs to protect privilege (fog-of-war.yaml:229-236).",
    )
    class_factor_default: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="C_f fallback for any SocialRole absent from the corpus's 4-entry table (explicit, never silent).",
    )
    investigate_intel_boost: float = Field(
        default=0.2,
        ge=0.05,
        le=0.5,
        description=(
            "Phase 2: I_c gained by the player org per INVESTIGATE of a territory "
            "(fog-of-war.yaml: intelligence is EARNED; Investigate is the tactical "
            "supplement, mass work the strategic base). No decay until Phase 3."
        ),
    )
    investigate_min_receptivity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Phase 2: minimum target-territory M_r for the player's INVESTIGATE "
            "to gather intel (fog-of-war.yaml:458-485 SOCIAL_INVESTIGATION — "
            "'cannot investigate if masses won't talk'; below it the action "
            "automatically fails). Cadre-presence gating is Phase 3."
        ),
    )
    organizing_reach_radius: int = Field(
        default=1,
        ge=1,
        le=5,
        description=(
            "Track 1 Task 2 (2026-07-18, spec-117 §5a): depth of the SOLIDARITY "
            "hop ONLY, in ``web.game.fog.reach.organizing_reach``. Reach is a "
            "composed, alternating traversal — org --PRESENCE--> territory "
            "--TENANCY--> class --SOLIDARITY--> class — NOT a union BFS over an "
            "edge-type set. The PRESENCE and TENANCY hops are structural facts "
            "(an org's operational footprint; a territory's occupant) and are "
            "always exactly one hop regardless of this value; only the "
            "SOLIDARITY front extends. Default 1 mirrors the design text — "
            "'visible only within organizing reach: where the org has presence "
            "or solidarity connection' — one ally deep, not a transitive chain. "
            "A union over {PRESENCE, SOLIDARITY} rooted at the org would be "
            "SILENTLY PRESENCE-ONLY: SOLIDARITY edges connect social_class to "
            "social_class and never touch an organization (verified in both "
            "shipped scenarios, ``_legacy_wayne.py:427-429`` and "
            "``_legacy.py:433-435``)."
        ),
    )
    intel_staleness_ticks: int = Field(
        default=5,
        ge=1,
        description=(
            "Track 1 Task 3 (2026-07-18): a fog-ledger entry no older than "
            "this many ticks renders EXACT. Older renders approximate "
            "(quantized), then unknown past ``intel_unknown_ticks``. Intel "
            "ages visibly — this is NOT a decay simulation, just a pure "
            "function of (ledger, current tick)."
        ),
    )
    intel_unknown_ticks: int = Field(
        default=20,
        ge=1,
        description=(
            "Track 1 Task 3 (2026-07-18): a fog-ledger entry older than this "
            "many ticks renders UNKNOWN rather than approximate. Must exceed "
            "``intel_staleness_ticks`` — enforced by "
            "``EpistemicHorizonDefines.check_intel_tick_ordering``."
        ),
    )

    @model_validator(mode="after")
    def check_intel_tick_ordering(self) -> EpistemicHorizonDefines:
        """Fail loud on a misconfigured fog-ledger tier ordering.

        ``intel_unknown_ticks`` must strictly exceed ``intel_staleness_ticks``
        — otherwise the "approximate" tier is empty or inverted, silently
        collapsing a 3-tier reveal gate into 2 (Constitution III.11: a
        misconfigured coefficient must fail loud, not degrade quietly).
        """
        if self.intel_unknown_ticks <= self.intel_staleness_ticks:
            raise ValueError(
                "intel_unknown_ticks "
                f"({self.intel_unknown_ticks}) must exceed intel_staleness_ticks "
                f"({self.intel_staleness_ticks}) or the 'approximate' fog tier "
                "is empty/inverted"
            )
        return self


__all__ = ["EpistemicHorizonDefines"]
