"""Mathematical utilities for simulation precision.

The Gatekeeper Pattern: Quantization is applied at the TYPE level
(when values enter Pydantic models), NOT inside formula calculations.
This ensures:
1. All values entering the simulation are on a fixed grid
2. Formula internals remain pure mathematical operations
3. No hidden precision loss during calculations

Epoch 0 Physics Hardening:
- All floating-point values in the simulation snap to a 10^-5 grid
- This prevents drift accumulation over long simulations
- Quantization uses ROUND_HALF_UP (round half away from zero)
"""

from __future__ import annotations

import math

# Module-level state for precision configuration
_PRECISION: int = 5
_GRID: int = 10**5


def get_precision() -> int:
    """Get current quantization precision (decimal places).

    Returns:
        Number of decimal places used for quantization.
        Default is 5 (10^-5 grid = 0.00001 resolution).
    """
    return _PRECISION


def set_precision(decimal_places: int) -> None:
    """Configure quantization precision.

    This affects all subsequent calls to quantize().
    Use this for testing or scenario-specific precision needs.

    Args:
        decimal_places: Number of decimal places (1-10).
            1 = 0.1 grid (coarse)
            5 = 0.00001 grid (default, sub-penny)
            10 = 0.0000000001 grid (ultra-precise)

    Raises:
        ValueError: If decimal_places not in valid range [1, 10].

    Example:
        >>> set_precision(3)
        >>> quantize(0.1234)
        0.123
        >>> set_precision(5)  # Restore default
    """
    if decimal_places < 1 or decimal_places > 10:
        raise ValueError(f"Precision decimal_places must be 1-10, got {decimal_places}")
    global _PRECISION, _GRID
    _PRECISION = decimal_places
    _GRID = 10**decimal_places


def quantize(value: float) -> float:
    """Snap a float to the configured precision grid.

    Uses symmetric rounding (ROUND_HALF_UP - round half away from zero):
    - Positive ties round up: 0.000005 -> 0.00001
    - Negative ties round down (away from zero): -0.000005 -> -0.00001

    This is the standard banker's rounding variant that ensures
    deterministic behavior across different platforms.

    Args:
        value: The float to quantize. None is treated as 0.0.

    Returns:
        Value snapped to 10^-precision grid.

    Examples:
        >>> quantize(0.123456789)  # precision=5
        0.12346
        >>> quantize(0.0)
        0.0
        >>> quantize(-0.123456789)
        -0.12346
        >>> quantize(0.000005)  # Exactly at midpoint
        0.00001
        >>> quantize(0.000001)  # Below midpoint
        0.0
    """
    # Handle None gracefully (defensive programming)
    if value is None:
        return 0.0

    # Zero is a fixed point of quantization
    if value == 0.0:
        return 0.0

    # Symmetric rounding (ROUND_HALF_UP): round ties away from zero
    # For positive: floor(x * GRID + 0.5) / GRID
    # For negative: -floor(-x * GRID + 0.5) / GRID = ceil(x * GRID - 0.5) / GRID
    if value > 0:
        return math.floor(value * _GRID + 0.5) / _GRID
    else:
        # For negative values, round away from zero (more negative)
        return -math.floor(-value * _GRID + 0.5) / _GRID
