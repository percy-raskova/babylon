"""Reactionary-subject coefficients (spec-071).

The fascism branch of the George Jackson bifurcation (Constitution I.4): the
labor aristocracy and petty/comprador bourgeoisie turning fascist as the
imperial bribe (Φ) decays. All numerics are theory-derived tunables sourced
from ``project/03-next-spec-071.md`` — strategic-intervention parameters
(Constitution III.5), overridable via ``defines.yaml`` like every other
category. Provenance table: ``specs/071-reactionary-subject/research.md`` R-001.

Re-exported via :mod:`babylon.config.defines.__init__`; composed into
:class:`babylon.config.defines.GameDefines` in
:mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReactionaryDefines(BaseModel):
    """Tunable defaults for the spec-071 reactionary subject.

    The fascist pull, drift, chauvinism/defection, spontaneous-riot, and RLF
    gate coefficients. Frozen so a run's coefficients stay constant
    (Constitution III.7 determinism).
    """

    model_config = ConfigDict(frozen=True)

    # --- Fascist pull + drift (catalog "FascistFactionSystem") ---
    fascist_pull_threshold: float = Field(
        default=1.0,
        ge=0.0,
        description="Fascist_Pull above which a node drifts fascist this tick (catalog: '> 1.0').",
    )
    fascist_drift_step: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Per-tick increment to fascist_alignment while pull exceeds threshold (catalog: '+= 0.05').",
    )
    fascist_recruitment_threshold: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="fascist_alignment at/above which the node is captured by a fascist faction (catalog: '>= 1.0').",
    )
    solidarity_pull_epsilon: float = Field(
        default=0.1,
        gt=0.0,
        description="Additive guard in Entitlement/(Solidarity+eps); also sets the maximal unsuppressed pull (catalog: '+ 0.1').",
    )

    # --- Stance intervention (ADR051 hook; research.md R-004) ---
    stance_intervention_gain: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Scales min(pull, cap) into a signed shove on the capital_labor opposition balance (bounded so one tick nudges, not flips).",
    )
    stance_intervention_cap: float = Field(
        default=1.0,
        ge=0.0,
        description="Caps the pull magnitude fed to the balance shove so an agitation spike cannot saturate in one tick.",
    )

    # --- Chauvinism + defection (catalog "LA members of player orgs") ---
    chauvinism_base_rate: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Per-tick chauvinism accrual on an org->LA MEMBERSHIP edge (catalog: '+0.01/tick base').",
    )
    chauvinism_superwage_bonus: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Extra per-tick chauvinism when the LA member holds a positive super-wage (catalog: '+0.02 if super-waged').",
    )
    defection_default_discipline: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Discipline D in sigmoid(chauvinism - D) when an org exposes no cadre-derived discipline.",
    )
    red_brown_coup_fraction: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fraction of an org's LA members that must defect in one crisis to fire RED_BROWN_COUP (catalog: '>50%').",
    )

    # --- Spontaneous riot (catalog "Volatility integration") ---
    spontaneous_riot_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="volatility*(1-discipline) above which a LUMPENPROLETARIAT node risks SPONTANEOUS_RIOT.",
    )

    # --- Entitlement role defaults (catalog "New SocialClass fields") ---
    entitlement_default_periphery_proletariat: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Default entitlement for PERIPHERY_PROLETARIAT."
    )
    entitlement_default_labor_aristocracy: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Default entitlement for LABOR_ARISTOCRACY."
    )
    entitlement_default_comprador_bourgeoisie: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Default entitlement for COMPRADOR_BOURGEOISIE."
    )
    entitlement_default_lumpenproletariat: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Default entitlement for LUMPENPROLETARIAT."
    )

    # --- Volatility role default ---
    volatility_default_lumpenproletariat: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Default volatility for LUMPENPROLETARIAT."
    )

    # --- Entitlement effective (threat amplification) ---
    entitlement_threat_gain: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="How much a threatened stake (threat in [0,1]) raises effective entitlement above base (clamped to 1.0).",
    )

    # --- RLF simplex (ADR051 §9.4; f->r gate) ---
    fr_gate_epsilon: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="f->r flow permitted only under (proletarianization AND adjacent-r AND solidarity); else this epsilon (0.0 = forbidden).",
    )

    # --- Fascist OODA verb effects (catalog "Fascist action verbs") ---
    pogrom_repression_increment: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Repression added to a POGROM target node.",
    )
    pogrom_wealth_destruction: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Fraction of target wealth destroyed by a POGROM.",
    )
    vigilantism_repression_increment: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Local repression spike from VIGILANTISM.",
    )
    lockout_wage_attenuation: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fraction by which a LOCKOUT attenuates the target's WAGES/EMPLOYMENT value_flow.",
    )
