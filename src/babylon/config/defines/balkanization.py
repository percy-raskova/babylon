"""Spec-070 Balkanization tunable defaults (FR-007 + R-001).

Theoretical defaults from ``balkanization-spec.yaml`` v1.2.0
(research.md R-001 documents provenance). All multipliers and
thresholds flow through this model so no magic numbers appear in
the system layer (Constitution III.1).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_EXTRACTION_MODIFIER: dict[str, float] = {
    "uphold": 1.5,
    "ignore": 0.8,
    "abolish": 0.0,
}
_DEFAULT_VIOLENCE_MODIFIER: dict[str, float] = {
    "uphold": 2.0,
    "ignore": 0.5,
    "abolish": 0.3,
}
_DEFAULT_CLASS_REDUCTION: dict[str, float] = {
    "uphold": 0.0,
    "ignore": 0.7,
    "abolish": 0.5,
}
_DEFAULT_METABOLIC_REDUCTION: dict[str, float] = {
    "uphold": -0.5,
    "ignore": 0.0,
    "abolish": 0.8,
}


class BalkanizationDefines(BaseModel):
    """Tunable defaults for the spec-070 political-topology subsystem.

    All fields have theoretical defaults from balkanization-spec.yaml
    v1.2.0; values are overridable via game-config Pydantic loading
    (see :class:`babylon.config.defines.GameDefines`).
    """

    model_config = ConfigDict(frozen=True)

    # Per-tick habitability change by ExtractionPolicy (FR-004).
    metabolic_impact_intensify: float = Field(
        default=-0.02,
        description="FR-004 INTENSIFY metabolic_impact per tick.",
    )
    metabolic_impact_continue: float = Field(
        default=-0.005,
        description="FR-004 CONTINUE metabolic_impact per tick.",
    )
    metabolic_impact_cease: float = Field(
        default=0.01,
        description="FR-004 CEASE metabolic_impact per tick.",
    )

    # Faction mechanical multipliers by ColonialStance (FR-007).
    stance_extraction_modifier: dict[str, float] = Field(
        default_factory=lambda: dict(_DEFAULT_EXTRACTION_MODIFIER),
        description="Faction extraction_modifier default by colonial_stance.",
    )
    stance_violence_modifier: dict[str, float] = Field(
        default_factory=lambda: dict(_DEFAULT_VIOLENCE_MODIFIER),
        description="Faction violence_modifier default by colonial_stance.",
    )
    stance_class_reduction: dict[str, float] = Field(
        default_factory=lambda: dict(_DEFAULT_CLASS_REDUCTION),
        description="Faction class_reduction default by colonial_stance.",
    )
    stance_metabolic_reduction: dict[str, float] = Field(
        default_factory=lambda: dict(_DEFAULT_METABOLIC_REDUCTION),
        description="Faction metabolic_reduction default by colonial_stance.",
    )

    # Secession / contiguity gating (FR-029a/b/c + R-004).
    secession_influence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="FR-029a (2) per-hex influence_level floor.",
    )
    secession_hysteresis_ticks: int = Field(
        default=3,
        ge=1,
        description="FR-029c consecutive-ticks hysteresis window.",
    )
    min_contiguous_hex_count: int = Field(
        default=12,
        ge=1,
        description="FR-029b minimum H3 res-7 hex count for a sub-region.",
    )

    # RED_OGV endgame (FR-032).
    red_ogv_class_tension_floor: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="FR-032 class_tension upper bound.",
    )
    red_ogv_habitability_floor: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="FR-032 aggregate_habitability upper bound.",
    )
    red_ogv_slope_window_ticks: int = Field(
        default=10,
        ge=1,
        description="FR-032 rolling window for habitability slope.",
    )

    # FRAGMENTED_COLLAPSE endgame (FR-032a).
    fragmented_collapse_min_sovereigns: int = Field(
        default=3,
        ge=2,
        description="FR-032a minimum surviving Sovereign count.",
    )
    fragmented_collapse_min_duration_ticks: int = Field(
        default=10,
        ge=1,
        description="FR-032a configuration persistence duration.",
    )

    # FACTION_VICTORY (FR-026).
    faction_victory_supermajority_threshold: float = Field(
        default=0.66,
        ge=0.5,
        le=1.0,
        description="FR-026 aggregate influence share threshold.",
    )

    # Post-collapse partition (FR-024 step 4).
    initial_post_collapse_control_level: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="FR-024 step 4 starting control_level for new Sovereigns.",
    )

    # Red Settler Trap diagnostic (FR-034).
    red_settler_trap_class_reduction_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="FR-034 class_reduction floor that, combined with UPHOLD/IGNORE stance, fires the diagnostic event.",
    )

    # Remediation: cross-divide solidarity gate (C5 / FR-031a / SC-016).
    revolutionary_victory_min_cross_divide_solidarity_edges: int = Field(
        default=5,
        ge=0,
        description=(
            "FR-031a minimum active SOLIDARITY edges between settler and "
            "non-settler entities required for REVOLUTIONARY_VICTORY. "
            "Below this count, an ABOLISH-majority + extraction-stopped + "
            "habitability-stabilizing run routes to RED_OGV (I.4 George "
            "Jackson Bifurcation)."
        ),
    )

    # Remediation: initial INFLUENCES seeding (C1 / FR-039).
    liberal_imperial_influence_cap: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="FR-039 cap on FAC_LIBERAL_IMPERIAL initial per-hex influence.",
    )

    # Remediation: observability projections (C3 / FR-051).
    projected_habitability_horizon_ticks: int = Field(
        default=20,
        ge=1,
        description="FR-051 default horizon for SovereignProjection.projected_habitability.",
    )
