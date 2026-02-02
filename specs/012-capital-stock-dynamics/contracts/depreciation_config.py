"""Contract: DepreciationConfig.

This module defines the contract for depreciation rate configuration.

Feature: 012-capital-stock-dynamics
Phase: 1 - Contracts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


# BEA-derived depreciation rate defaults
DEFAULT_DEPRECIATION_RATE: Final[float] = 0.07
MIN_DEPRECIATION_RATE: Final[float] = 0.01
MAX_DEPRECIATION_RATE: Final[float] = 0.20

# Sensitivity analysis presets
SLOW_DEPRECIATION_RATE: Final[float] = 0.05
FAST_DEPRECIATION_RATE: Final[float] = 0.10


@dataclass(frozen=True)
class DepreciationConfigContract:
    """Contract for depreciation rate configuration.

    The depreciation rate (δ) determines how much of the capital stock
    is consumed each period. This follows the perpetual inventory method
    with TSSI (Temporal Single-System Interpretation) historical cost
    valuation.

    Attributes:
        rate: Annual depreciation rate. Default 0.07 (7%) based on
            BEA fixed asset tables average. Valid range: [0.01, 0.20].

    Validation:
        - rate must be in range [0.01, 0.20]
        - Raises ValueError if out of range

    Example:
        >>> config = DepreciationConfig(rate=0.07)
        >>> config.rate
        0.07

        >>> # Validation error
        >>> DepreciationConfig(rate=0.5)  # Raises ValueError

    Factory Methods:
        - default() -> DepreciationConfig with rate=0.07
        - slow() -> DepreciationConfig with rate=0.05
        - fast() -> DepreciationConfig with rate=0.10

    See Also:
        - BEA Fixed Asset Tables: https://www.bea.gov/data/special-topics/fixed-assets
        - TVT Section 5.2 for capital stock evolution formula
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
    def default(cls) -> DepreciationConfigContract:
        """Create default configuration (δ = 0.07).

        Returns:
            DepreciationConfig with BEA average depreciation rate.
        """
        return cls(rate=DEFAULT_DEPRECIATION_RATE)

    @classmethod
    def slow(cls) -> DepreciationConfigContract:
        """Create slow depreciation configuration (δ = 0.05).

        Use for sensitivity analysis to test robustness of TRPF
        conclusions with lower depreciation assumption.

        Returns:
            DepreciationConfig with slow depreciation rate.
        """
        return cls(rate=SLOW_DEPRECIATION_RATE)

    @classmethod
    def fast(cls) -> DepreciationConfigContract:
        """Create fast depreciation configuration (δ = 0.10).

        Use for sensitivity analysis to test robustness of TRPF
        conclusions with higher depreciation assumption.

        Returns:
            DepreciationConfig with fast depreciation rate.
        """
        return cls(rate=FAST_DEPRECIATION_RATE)

    def steady_state_K(self, annual_investment: float) -> float:
        """Compute steady-state capital stock for given investment.

        At steady state, depreciation equals investment:
            δK = I
            K = I/δ

        Args:
            annual_investment: Annual gross investment (total_c).

        Returns:
            Steady-state capital stock.

        Example:
            >>> config = DepreciationConfig(rate=0.07)
            >>> config.steady_state_K(70.0)
            1000.0
        """
        return annual_investment / self.rate

    def next_K(self, current_K: float, investment: float) -> float:
        """Compute next period capital stock.

        Applies perpetual inventory method:
            K[t+1] = K[t] × (1 - δ) + I[t]

        Args:
            current_K: Current capital stock K[t].
            investment: Current period investment I[t] (total_c).

        Returns:
            Next period capital stock K[t+1], clamped to >= 0.

        Example:
            >>> config = DepreciationConfig(rate=0.07)
            >>> config.next_K(1000.0, 70.0)
            1000.0  # Steady state maintained

            >>> config.next_K(1000.0, 100.0)
            1030.0  # Growing capital
        """
        next_value = current_K * (1 - self.rate) + investment
        return max(0.0, next_value)  # Clamp to non-negative
