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

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = ["EpistemicHorizonDefines"]
