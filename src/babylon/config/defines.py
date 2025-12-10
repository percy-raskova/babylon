"""Game defines for centralized coefficient configuration.

This module provides the GameDefines model which extracts hardcoded values
from systems into a single, configurable location. This enables:
1. Easier calibration of game balance
2. Scenario-specific coefficient overrides
3. Clear documentation of magic numbers

Sprint: Paradox Refactor Phase 1
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GameDefines(BaseModel):
    """Centralized game coefficients extracted from hardcoded values.

    GameDefines collects numerical constants that were previously scattered
    across system implementations. By centralizing them here, we can:
    - Document their purpose and valid ranges
    - Override them per-scenario for calibration
    - Test the sensitivity of outcomes to coefficient changes

    The model is frozen (immutable) to ensure defines remain constant
    throughout a simulation run.

    Attributes:
        SUPERWAGE_IMPACT: Multiplier for how imperial extraction affects Core wealth.
        SOLIDARITY_SCALING: Multiplier for graph edge weights affecting Organization.
        REPRESSION_BASE: Base resistance to revolution in P(S|R) denominator.
        REVOLUTION_THRESHOLD: The tipping point for P(S|R) formula.
        DEFAULT_ORGANIZATION: Fallback organization value when not specified.
        DEFAULT_REPRESSION_FACED: Fallback repression value when not specified.
        DEFAULT_SUBSISTENCE: Fallback subsistence threshold when not specified.
        NEGLIGIBLE_TRANSMISSION: Threshold below which transmissions are skipped.
    """

    model_config = ConfigDict(frozen=True)

    # Superwage/Economic coefficients
    SUPERWAGE_IMPACT: float = Field(
        default=1.0,
        ge=0.0,
        description="How much 1 unit of imperial extraction increases Core wealth",
    )

    # Solidarity coefficients
    SOLIDARITY_SCALING: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Multiplier for graph edge weights affecting Organization",
    )

    # Repression coefficients
    REPRESSION_BASE: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Base resistance to revolution in P(S|R) denominator",
    )

    # Revolution threshold
    REVOLUTION_THRESHOLD: float = Field(
        default=1.0,
        gt=0.0,
        description="The tipping point for P(S|R) formula",
    )

    # Default entity values (extracted from survival.py, economic.py)
    DEFAULT_ORGANIZATION: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Fallback organization value when not specified on entity",
    )

    DEFAULT_REPRESSION_FACED: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fallback repression value when not specified on entity",
    )

    DEFAULT_SUBSISTENCE: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Fallback subsistence threshold when not specified on entity",
    )

    # Transmission thresholds (extracted from solidarity.py, economic.py)
    NEGLIGIBLE_TRANSMISSION: float = Field(
        default=0.01,
        ge=0.0,
        description="Threshold below which transmissions are skipped as noise",
    )
