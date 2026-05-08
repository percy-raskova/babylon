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

    3. FASCIST_CONSOLIDATION: national_identity > class_consciousness for M+ nodes
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
        fascist_majority_threshold: Minimum number of nodes where national_identity
            exceeds class_consciousness for FASCIST_CONSOLIDATION (3 nodes).
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
    fascist_majority_threshold: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Game design: minimum nodes with national_identity > class_consciousness.",
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
