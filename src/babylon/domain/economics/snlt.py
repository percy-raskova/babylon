"""SNLT (Socially Necessary Labor Time) configuration for labor-hour conversion.

This module provides configuration for converting monetary values to labor-hours
using year-specific SNLT conversion factors. The conversion follows Marx's
labor theory of value, where all economic quantities are ultimately reducible
to labor-time.

Until SNLT conversion is fully calibrated, tensor values represent
**wage-proportional labor-time proxies**. This means:
- Derived ratios (r, e, OCC) are **exact** (units cancel)
- Absolute magnitudes require SNLT calibration

Example:
    >>> from babylon.domain.economics.snlt import SNLTConfig
    >>> # Default configuration (wage-proportional proxy)
    >>> config = SNLTConfig()
    >>> config.get_factor(2020)
    1.0
    >>>
    >>> # Year-specific factors (productivity improvements)
    >>> config = SNLTConfig(
    ...     factors={2015: 1.0, 2020: 0.95, 2025: 0.90},
    ...     default_factor=1.0,
    ... )
    >>> config.get_factor(2020)  # 5% productivity increase
    0.95

See Also:
    :mod:`babylon.domain.economics.tensor`: Uses SNLT conversion for labor-hour values.
    :mod:`babylon.domain.economics.tensor_registry`: Applies SNLT during hydration.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SNLTConfig(BaseModel):
    """Configuration for year-specific SNLT conversion factors.

    The SNLT (Socially Necessary Labor Time) conversion factor transforms
    monetary wages into labor-hours. The factor represents productivity:

    - factor = 1.0: No conversion (wage-proportional proxy)
    - factor < 1.0: Higher productivity (fewer hours per dollar)
    - factor > 1.0: Lower productivity (more hours per dollar)

    Conversion formula: labor_hours = wages * snlt_factor

    Args:
        factors: Mapping of year to SNLT factor. Years not in the mapping
            will use the default_factor.
        default_factor: Factor to use when year is not in the factors mapping.
            Must be > 0.0 to prevent division by zero.

    Example:
        >>> config = SNLTConfig(
        ...     factors={2015: 1.0, 2020: 0.95, 2025: 0.90},
        ...     default_factor=1.0,
        ... )
        >>> # 2020 uses explicit factor
        >>> config.get_factor(2020)
        0.95
        >>> # 2018 falls back to default
        >>> config.get_factor(2018)
        1.0
    """

    model_config = ConfigDict(frozen=True)

    factors: dict[int, float] = Field(
        default_factory=dict,
        description="Year-specific SNLT factors (year -> factor)",
    )
    default_factor: float = Field(
        default=1.0,
        gt=0.0,
        description="Default SNLT factor for years not in factors mapping",
    )

    @field_validator("factors")
    @classmethod
    def validate_factors_positive(cls, v: dict[int, float]) -> dict[int, float]:
        """Validate all SNLT factors are positive (prevent division by zero).

        Args:
            v: The factors dictionary to validate.

        Returns:
            The validated factors dictionary.

        Raises:
            ValueError: If any factor is <= 0.0.
        """
        for year, factor in v.items():
            if factor <= 0.0:
                msg = f"SNLT factor for year {year} must be > 0.0, got {factor}"
                raise ValueError(msg)
        return v

    def get_factor(self, year: int) -> float:
        """Get SNLT conversion factor for a specific year.

        Args:
            year: Calendar year to get factor for.

        Returns:
            SNLT factor for the year. If year is not in the factors mapping,
            returns the default_factor.

        Example:
            >>> config = SNLTConfig(factors={2020: 0.95})
            >>> config.get_factor(2020)
            0.95
            >>> config.get_factor(2021)  # Not in mapping, uses default
            1.0
        """
        return self.factors.get(year, self.default_factor)


# Default configuration: wage-proportional proxy (no conversion)
DEFAULT_SNLT_CONFIG: Final[SNLTConfig] = SNLTConfig()
"""Default SNLT configuration with factor 1.0 (wage-proportional proxy).

Use this when SNLT calibration data is not available. Derived ratios
(profit rate, exploitation rate, OCC) will be exact; only absolute
magnitudes require SNLT calibration.
"""


__all__ = [
    "DEFAULT_SNLT_CONFIG",
    "SNLTConfig",
]
