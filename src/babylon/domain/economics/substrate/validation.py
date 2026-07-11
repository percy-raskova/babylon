"""Three-tier validation for substrate economic values.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Follows the same three-tier pattern as tensor_hierarchy/validation.py:
    - Expected: Normal operating range (returns True, None)
    - Warning: Unusual but valid (returns True, warning_str)
    - Fail: Invalid value (returns False, error_str)

See Also:
    :mod:`babylon.domain.economics.tensor_hierarchy.validation`: Original pattern.
    :mod:`babylon.domain.economics.substrate.types`: Substrate type definitions.
"""

from __future__ import annotations

# =============================================================================
# PROFIT RATE VALIDATION RANGES
# =============================================================================

PROFIT_RATE_EXPECTED_MAX: float = 0.5
PROFIT_RATE_WARNING_MAX: float = 2.0

# =============================================================================
# EXPLOITATION RATE VALIDATION RANGES
# =============================================================================

EXPLOITATION_RATE_EXPECTED_MAX: float = 2.0
EXPLOITATION_RATE_WARNING_MAX: float = 10.0

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_profit_rate(rate: float) -> tuple[bool, str | None]:
    """Validate profit rate s/(c+v) against sanity ranges.

    Expected range [0, 0.5] for typical US counties.

    Args:
        rate: Profit rate value.

    Returns:
        Tuple of (valid, message):
        - (True, None): Within expected range.
        - (True, warning): Outside expected but within warning range.
        - (False, error): Outside all valid ranges.

    Example:
        >>> validate_profit_rate(0.15)
        (True, None)
        >>> validate_profit_rate(1.5)
        (True, 'WARNING: ...')
    """
    if rate < 0.0:
        return (
            False,
            f"Profit rate {rate:.4f} is negative (invalid)",
        )

    if rate > PROFIT_RATE_WARNING_MAX:
        return (
            False,
            f"Profit rate {rate:.4f} exceeds fail threshold {PROFIT_RATE_WARNING_MAX}",
        )

    if rate > PROFIT_RATE_EXPECTED_MAX:
        return (
            True,
            f"WARNING: Profit rate {rate:.4f} exceeds expected max {PROFIT_RATE_EXPECTED_MAX}",
        )

    return (True, None)


def validate_exploitation_rate(rate: float) -> tuple[bool, str | None]:
    """Validate exploitation rate s/v against sanity ranges.

    Expected range [0, 2.0] for typical US counties.

    Args:
        rate: Exploitation rate value.

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_exploitation_rate(1.0)
        (True, None)
        >>> validate_exploitation_rate(5.0)
        (True, 'WARNING: ...')
    """
    if rate < 0.0:
        return (
            False,
            f"Exploitation rate {rate:.4f} is negative (invalid)",
        )

    if rate > EXPLOITATION_RATE_WARNING_MAX:
        return (
            False,
            f"Exploitation rate {rate:.4f} exceeds fail threshold {EXPLOITATION_RATE_WARNING_MAX}",
        )

    if rate > EXPLOITATION_RATE_EXPECTED_MAX:
        return (
            True,
            f"WARNING: Exploitation rate {rate:.4f} exceeds expected max "
            f"{EXPLOITATION_RATE_EXPECTED_MAX}",
        )

    return (True, None)


def validate_dept_shares(
    shares: tuple[float, ...],
) -> tuple[bool, str | None]:
    """Validate department shares sum to 1.0 and are non-negative.

    Args:
        shares: Tuple of department employment fractions (I, IIa, IIb, III).

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_dept_shares((0.25, 0.25, 0.25, 0.25))
        (True, None)
    """
    for i, s in enumerate(shares):
        if s < 0.0:
            return (
                False,
                f"Department share[{i}]={s:.4f} is negative",
            )

    share_sum = sum(shares)
    if abs(share_sum - 1.0) > 1e-10:
        return (
            False,
            f"Department shares sum={share_sum:.10f} deviates from 1.0 "
            f"by {abs(share_sum - 1.0):.2e}",
        )

    return (True, None)


def validate_capital_values(c: float, v: float, s: float) -> tuple[bool, str | None]:
    """Validate capital values are non-negative.

    Args:
        c: Constant capital.
        v: Variable capital.
        s: Surplus value.

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_capital_values(100.0, 50.0, 30.0)
        (True, None)
    """
    if c < 0.0:
        return (False, f"Constant capital c={c:.4f} is negative")
    if v < 0.0:
        return (False, f"Variable capital v={v:.4f} is negative")
    if s < 0.0:
        return (False, f"Surplus value s={s:.4f} is negative")

    return (True, None)


__all__ = [
    "EXPLOITATION_RATE_EXPECTED_MAX",
    "EXPLOITATION_RATE_WARNING_MAX",
    "PROFIT_RATE_EXPECTED_MAX",
    "PROFIT_RATE_WARNING_MAX",
    "validate_capital_values",
    "validate_dept_shares",
    "validate_exploitation_rate",
    "validate_profit_rate",
]
