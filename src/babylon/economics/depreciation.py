"""Depreciation configuration for capital stock computation.

This module provides the DepreciationConfig dataclass for configuring capital
depreciation rates used in the perpetual inventory method. The depreciation rate
(δ) determines how much of the capital stock is consumed each period.

Theoretical Foundation:
    Capital stock evolves according to the perpetual inventory method with
    TSSI (Temporal Single-System Interpretation) historical cost valuation.
    Per TVT Axiom B2, capital is valued at historical cost (what was actually
    paid), not current replacement cost.

    Formula: K[t+1] = K[t] × (1 - δ) + I[t]

    Where:
        K[t] = Capital stock at time t
        δ = Depreciation rate (annual fraction consumed)
        I[t] = Gross investment (total_c from ValueTensor4x3)

Depreciation Rate Sources:
    Default rate of 0.07 (7%) based on BEA Fixed Asset Tables average
    depreciation across industries. Valid range [0.01, 0.20] encompasses:
    - Slow: δ = 0.05 (structures, long-lived equipment)
    - Default: δ = 0.07 (BEA aggregate average)
    - Fast: δ = 0.10 (technology, short-lived equipment)

Example:
    >>> from babylon.economics.depreciation import DepreciationConfig
    >>> config = DepreciationConfig()  # Default δ = 0.07
    >>> config.rate
    0.07
    >>> config.steady_state_K(70.0)  # K = I/δ = 70/0.07
    1000.0

See Also:
    :class:`babylon.economics.capital_stock.CapitalStockCalculator`: Uses config for K computation.
    :mod:`babylon.economics.tensor`: ValueTensor4x3 provides total_c (investment).
    BEA Fixed Asset Tables: https://www.bea.gov/data/special-topics/fixed-assets
    TVT Section 5.2: Capital Stock Evolution formula.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "DEFAULT_DEPRECIATION_RATE",
    "DepreciationConfig",
    "FAST_DEPRECIATION_RATE",
    "MAX_DEPRECIATION_RATE",
    "MIN_DEPRECIATION_RATE",
    "SLOW_DEPRECIATION_RATE",
]

# BEA-derived depreciation rate defaults
DEFAULT_DEPRECIATION_RATE: Final[float] = 0.07
"""Default depreciation rate (7%) based on BEA aggregate average."""

MIN_DEPRECIATION_RATE: Final[float] = 0.01
"""Minimum valid depreciation rate (1%)."""

MAX_DEPRECIATION_RATE: Final[float] = 0.20
"""Maximum valid depreciation rate (20%)."""

# Sensitivity analysis presets
SLOW_DEPRECIATION_RATE: Final[float] = 0.05
"""Slow depreciation rate (5%) for long-lived capital (structures)."""

FAST_DEPRECIATION_RATE: Final[float] = 0.10
"""Fast depreciation rate (10%) for short-lived capital (technology)."""


@dataclass(frozen=True)
class DepreciationConfig:
    """Configuration for capital depreciation rate (δ).

    The depreciation rate determines how much of the capital stock
    is consumed each period. Based on BEA fixed asset tables.

    Attributes:
        rate: Annual depreciation rate. Default 0.07 (7%) based on
            BEA fixed asset tables average. Valid range: [0.01, 0.20].

    Raises:
        ValueError: If rate is outside valid range [0.01, 0.20].

    Example:
        >>> config = DepreciationConfig(rate=0.07)
        >>> config.rate
        0.07

        >>> # Factory methods for common configurations
        >>> DepreciationConfig.slow().rate
        0.05
        >>> DepreciationConfig.fast().rate
        0.10
    """

    rate: float = DEFAULT_DEPRECIATION_RATE

    def __post_init__(self) -> None:
        """Validate depreciation rate is in valid range.

        Raises:
            ValueError: If rate is outside [0.01, 0.20].
        """
        if not MIN_DEPRECIATION_RATE <= self.rate <= MAX_DEPRECIATION_RATE:
            msg = (
                f"Depreciation rate must be in [{MIN_DEPRECIATION_RATE}, "
                f"{MAX_DEPRECIATION_RATE}], got {self.rate}"
            )
            raise ValueError(msg)

    @classmethod
    def default(cls) -> DepreciationConfig:
        """Create default configuration (δ = 0.07).

        Returns:
            DepreciationConfig with BEA average depreciation rate.
        """
        return cls(rate=DEFAULT_DEPRECIATION_RATE)

    @classmethod
    def slow(cls) -> DepreciationConfig:
        """Create slow depreciation configuration (δ = 0.05).

        Use for sensitivity analysis to test robustness of TRPF
        conclusions with lower depreciation assumption.

        Returns:
            DepreciationConfig with slow depreciation rate.
        """
        return cls(rate=SLOW_DEPRECIATION_RATE)

    @classmethod
    def fast(cls) -> DepreciationConfig:
        """Create fast depreciation configuration (δ = 0.10).

        Use for sensitivity analysis to test robustness of TRPF
        conclusions with higher depreciation assumption.

        Returns:
            DepreciationConfig with fast depreciation rate.
        """
        return cls(rate=FAST_DEPRECIATION_RATE)

    def steady_state_K(self, annual_investment: float) -> float:
        """Compute steady-state capital stock for given investment.

        At steady state, depreciation equals investment::

            δK = I
            K = I/δ

        This is used to initialize K_0 when no prior capital stock
        history is available (TVT Section 5.2).

        Args:
            annual_investment: Annual gross investment (total_c).

        Returns:
            Steady-state capital stock K_0.

        Example:
            >>> config = DepreciationConfig(rate=0.07)
            >>> config.steady_state_K(70.0)
            1000.0
        """
        return annual_investment / self.rate

    def next_K(self, current_K: float, investment: float) -> float:
        """Compute next period capital stock using perpetual inventory method.

        Applies the formula::

            K[t+1] = K[t] × (1 - δ) + I[t]

        Args:
            current_K: Current capital stock K[t].
            investment: Current period investment I[t] (total_c).

        Returns:
            Next period capital stock K[t+1], clamped to >= 0.

        Example:
            >>> config = DepreciationConfig(rate=0.07)
            >>> config.next_K(1000.0, 70.0)  # Steady state maintained
            1000.0
            >>> config.next_K(1000.0, 100.0)  # Growing capital
            1030.0
        """
        next_value = current_K * (1 - self.rate) + investment
        return max(0.0, next_value)  # Clamp to non-negative
