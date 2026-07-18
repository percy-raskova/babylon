"""Endgame detection thresholds and initial conditions.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EndgameDefines(BaseModel):
    """Configuration for endgame detection thresholds (Slice 1.6).

    The EndgameDetector monitors WorldState for three possible game endings:

    1. REVOLUTIONARY_VICTORY: percolation >= threshold AND consciousness > threshold
       The masses have achieved critical organization AND ideological clarity.

    2. ECOLOGICAL_COLLAPSE: overshoot_ratio > threshold for N consecutive ticks
       Sustained ecological overshoot leads to irreversible collapse.

    3. FASCIST_CONSOLIDATION: fraction of ideology-bearing nodes with
       national_identity > class_consciousness reaches fascist_majority_fraction.
       Fascist ideology has captured the majority of the population.

    Attributes:
        revolutionary_percolation_threshold: Minimum percolation ratio (0.7 = 70%
            of nodes in giant solidarity component) for revolutionary victory.
        revolutionary_consciousness_threshold: Minimum average class consciousness
            (0.8 = 80% ideological clarity) for revolutionary victory.
        ecological_overshoot_threshold: Consumption/biocapacity ratio above which
            ecological damage accumulates (2.0 = consuming 2x biocapacity).
        ecological_sustained_ticks: Number of consecutive ticks overshoot must
            persist before triggering ECOLOGICAL_COLLAPSE (5 ticks).
        fascist_majority_fraction: Minimum fraction of ideology-bearing nodes where
            national_identity exceeds class_consciousness for FASCIST_CONSOLIDATION
            (0.9 = 90%; replaces the scenario-size-degenerate absolute count).
            Spec-116 Task 6 pacing calibration (2026-07-17) raised this from the
            original 0.75: imperial-circuit-derived scenarios (including ``us``,
            spec-116 gate 1's null-play scenario) reuse only 6 archetypal
            SocialClass entities regardless of territory count, so the fraction
            is quantized in 1/6 increments. At 0.75, the ``us`` scenario's tick-0
            fraction (4/6 = 0.667) sits a single entity's ideology flip away from
            5/6 = 0.833 > 0.75 — an instant false-positive lock. 0.9 requires all
            6 entities to flip before matching, restoring the intended "total
            ideological capture" semantics and keeping ``first_recognition`` past
            the no-pattern-before-tick-520 gate under null play (see
            ``reports/pacing-calibration-2026-07-17.md``).
    """

    model_config = ConfigDict(frozen=True)

    revolutionary_percolation_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Game design: percolation ratio threshold for revolutionary victory (70%).",
    )
    revolutionary_consciousness_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Game design: average consciousness threshold for revolutionary victory (80%).",
    )
    ecological_overshoot_threshold: float = Field(
        default=2.0,
        gt=0.0,
        description="Game design: overshoot ratio threshold for ecological collapse tracking.",
    )
    ecological_sustained_ticks: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Game design: consecutive ticks of overshoot before collapse triggers.",
    )
    campaign_horizon_years: int = Field(
        default=100,
        ge=1,
        le=1000,
        description=(
            "Game design: fixed campaign horizon in in-game years. The game ends "
            "only when tick >= horizon_years * timescale.weeks_per_year (owner "
            "ruling 2026-07-17: outcomes are recognized patterns, never terminators)."
        ),
    )
    pattern_lock_ticks: int = Field(
        default=26,
        ge=1,
        le=520,
        description=(
            "Game design: consecutive ticks a recognized outcome pattern must hold "
            "before it is 'locked' and the Council may accept the outcome early."
        ),
    )
    fascist_majority_fraction: float = Field(
        default=0.9,
        ge=0.5,
        le=1.0,
        description=(
            "Game design: fraction of social-class nodes with national_identity > "
            "class_consciousness required to recognize FASCIST_CONSOLIDATION "
            "(replaces the scenario-size-degenerate absolute count). Spec-116 "
            "Task 6 (2026-07-17): raised from 0.75 to 0.9 — with only 6 "
            "archetypal ideology-bearing entities, a single entity's ideology "
            "flip moves the fraction from 4/6=0.667 to 5/6=0.833, so 0.75 "
            "locked FASCIST_CONSOLIDATION almost immediately under null play; "
            "0.9 requires all 6 entities to flip."
        ),
    )


class InitialDefines(BaseModel):
    """Initial condition coefficients."""

    model_config = ConfigDict(frozen=True)

    worker_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for periphery worker",
    )
    owner_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for core owner",
    )
    default_population: int = Field(
        default=1,
        ge=1,
        description="Game design: default population for test entities. pop=1 ensures per-capita survival mechanics are tested without large denominators masking issues.",
    )


__all__ = [
    "EndgameDefines",
    "InitialDefines",
]
