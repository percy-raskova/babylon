"""Precision and timescale tunables.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PrecisionDefines(BaseModel):
    """Numerical precision configuration for deterministic simulation.

    Epoch 0 Physics Hardening:
    - All floating-point values snap to a 10^-n grid (default n=6)
    - This prevents drift accumulation over long simulations (100+ years)
    - ROUND_HALF_UP ensures deterministic cross-platform behavior

    The Gatekeeper Pattern: Quantization is applied at TYPE level
    (Pydantic AfterValidator), NOT inside formulas.

    Note: Increased from 5 to 6 decimal places for 100-year (5200 tick)
    Carceral Equilibrium simulations to reduce cumulative rounding errors.
    """

    model_config = ConfigDict(frozen=True)

    decimal_places: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Engineering: quantization grid precision (10^-n). Structurally determined by IEEE 754 float64 and 5200-tick simulation horizon.",
    )
    rounding_mode: str = Field(
        default="ROUND_HALF_UP",
        description="Rounding mode for quantization.",
    )
    epsilon: float = Field(
        default=1e-9,
        gt=0.0,
        le=1e-3,
        description="Engineering: division-by-zero guard. Must satisfy epsilon < 10^-decimal_places to stay below quantization grid.",
    )
    comparison_epsilon: float = Field(
        default=1e-10,
        gt=0.0,
        le=1e-6,
        description="Engineering: float equality tolerance for deterministic test assertions. Must be < epsilon to detect precision violations.",
    )


class TimescaleDefines(BaseModel):
    """Simulation timescale configuration for weekly ticks.

    Epoch 0 Physics Hardening:
    - 1 tick = 7 days (weekly resolution)
    - 52 weeks = 1 year (for annual rate conversions)

    This is critical for:
    - Economic flow rates (annual -> per-tick conversion)
    - Historical pacing (events per game year)
    - UI display (showing dates/weeks)

    All annual rates (wage_rate, extraction_efficiency) are divided by
    weeks_per_year to get per-tick rates.
    """

    model_config = ConfigDict(frozen=True)

    tick_duration_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Engineering: physical constant. 7 days/week is a calendar invariant, not a tunable parameter.",
    )
    weeks_per_year: int = Field(
        default=52,
        ge=1,
        description="Engineering: physical constant. 52 weeks/year for annual-to-tick rate conversion.",
    )

    @property
    def ticks_per_year(self) -> int:
        """Number of ticks per simulation year.

        Since 1 tick = 1 week, this equals weeks_per_year.
        """
        return self.weeks_per_year

    @property
    def days_per_year(self) -> int:
        """Days per simulation year (ticks * days_per_tick).

        With defaults: 7 * 52 = 364 days (close to actual 365-366).
        """
        return self.tick_duration_days * self.weeks_per_year


__all__ = [
    "PrecisionDefines",
    "TimescaleDefines",
]
