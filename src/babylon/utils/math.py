"""Mathematical utilities for simulation precision.

Gatekeeper Pattern: Quantization at TYPE level (Pydantic validators),
not inside formulas. All values snap to 10^-6 grid (default).

Uses ROUND_HALF_UP (symmetric rounding - ties away from zero).

Note: Increased from 5 to 6 decimal places for 100-year (5200 tick)
Carceral Equilibrium simulations to reduce cumulative rounding errors.
"""

from __future__ import annotations

import math

_PRECISION: int = 6
_GRID: int = 10**6


def get_precision() -> int:
    """Current decimal places for quantization (default 6)."""
    return _PRECISION


def set_precision(decimal_places: int) -> None:
    """Set quantization precision (1-10 decimal places).

    Args:
        decimal_places: 1=coarse (0.1), 6=default (0.000001), 10=ultra.

    Raises:
        ValueError: If not in range [1, 10].
    """
    if decimal_places < 1 or decimal_places > 10:
        raise ValueError(f"Precision must be 1-10, got {decimal_places}")
    global _PRECISION, _GRID
    _PRECISION = decimal_places
    _GRID = 10**decimal_places


def quantize(value: float) -> float:
    """Snap float to precision grid (ROUND_HALF_UP).

    Args:
        value: Float to quantize (None treated as 0.0).

    Returns:
        Value on 10^-precision grid.

    Examples:
        >>> quantize(0.123456789)
        0.123457
        >>> quantize(-0.123456789)
        -0.123457
    """
    if value is None or value == 0.0:
        return 0.0

    if value > 0:
        return math.floor(value * _GRID + 0.5) / _GRID
    return -math.floor(-value * _GRID + 0.5) / _GRID
