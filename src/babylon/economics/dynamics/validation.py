"""Three-tier validation for transition rates and class shares.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

Validation follows the same pattern as ``gamma/validation.py``:
    - Expected: Normal operating range (no message)
    - Warning: Unusual but possible (returns warning message)
    - Fail: Invalid value (returns error message, valid=False)

Ranges from ``specs/016-class-dynamics-engine/research.md`` Section 7.

See Also:
    :mod:`babylon.economics.gamma.validation`: Original three-tier pattern
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.economics.dynamics.types import TransitionRates

# =============================================================================
# TRANSITION RATE VALIDATION RANGES (research.md §7)
# =============================================================================

# Dispossession (LA -> Proletariat)
DISPOSSESSION_EXPECTED_MIN: float = 0.001
DISPOSSESSION_EXPECTED_MAX: float = 0.05
DISPOSSESSION_WARNING_MIN: float = 0.0001
DISPOSSESSION_WARNING_MAX: float = 0.10
DISPOSSESSION_FAIL_MAX: float = 0.20

# Accumulation (Proletariat -> LA)
ACCUMULATION_EXPECTED_MIN: float = 0.001
ACCUMULATION_EXPECTED_MAX: float = 0.03
ACCUMULATION_WARNING_MIN: float = 0.0001
ACCUMULATION_WARNING_MAX: float = 0.08
ACCUMULATION_FAIL_MAX: float = 0.15

# Precaritization (Proletariat -> Lumpen)
PRECARITIZATION_EXPECTED_MIN: float = 0.005
PRECARITIZATION_EXPECTED_MAX: float = 0.08
PRECARITIZATION_WARNING_MIN: float = 0.001
PRECARITIZATION_WARNING_MAX: float = 0.15
PRECARITIZATION_FAIL_MAX: float = 0.25

# Stabilization (Lumpen -> Proletariat)
STABILIZATION_EXPECTED_MIN: float = 0.01
STABILIZATION_EXPECTED_MAX: float = 0.15
STABILIZATION_WARNING_MIN: float = 0.005
STABILIZATION_WARNING_MAX: float = 0.20
STABILIZATION_FAIL_MAX: float = 0.30

# =============================================================================
# CLASS SHARE VALIDATION RANGES (research.md §7)
# =============================================================================

LA_SHARE_EXPECTED_MIN: float = 0.30
LA_SHARE_EXPECTED_MAX: float = 0.50
LA_SHARE_WARNING_MIN: float = 0.20
LA_SHARE_WARNING_MAX: float = 0.60

PROLETARIAT_SHARE_EXPECTED_MIN: float = 0.25
PROLETARIAT_SHARE_EXPECTED_MAX: float = 0.45
PROLETARIAT_SHARE_WARNING_MIN: float = 0.15
PROLETARIAT_SHARE_WARNING_MAX: float = 0.55

LUMPEN_SHARE_EXPECTED_MIN: float = 0.10
LUMPEN_SHARE_EXPECTED_MAX: float = 0.25
LUMPEN_SHARE_WARNING_MIN: float = 0.05
LUMPEN_SHARE_WARNING_MAX: float = 0.35


def _check_rate(
    name: str,
    value: float,
    expected_min: float,
    expected_max: float,
    warning_min: float,
    warning_max: float,
    fail_max: float,
) -> tuple[bool, str | None]:
    """Check a single rate against three-tier ranges.

    Args:
        name: Rate name for error messages.
        value: Rate value to validate.
        expected_min: Lower bound of expected range.
        expected_max: Upper bound of expected range.
        warning_min: Lower bound of warning range.
        warning_max: Upper bound of warning range.
        fail_max: Upper bound of fail range (lower is 0).

    Returns:
        Tuple of (valid, message).
    """
    if value < 0.0 or value > fail_max:
        return (
            False,
            f"{name}={value:.4f} outside valid range [0.0, {fail_max}]",
        )

    if value < warning_min or value > warning_max:
        return (
            True,
            f"WARNING: {name}={value:.4f} outside warning range [{warning_min}, {warning_max}]",
        )

    if value < expected_min or value > expected_max:
        return (
            True,
            f"WARNING: {name}={value:.4f} outside expected range [{expected_min}, {expected_max}]",
        )

    return (True, None)


def validate_transition_rates(rates: TransitionRates) -> tuple[bool, str | None]:
    """Validate transition rates against three-tier ranges.

    Checks each of the four transition rates against Expected/Warning/Fail
    boundaries from research.md Section 7.

    Args:
        rates: TransitionRates to validate.

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: All rates in expected range
        - valid=True, message=str: Warning (unusual value)
        - valid=False, message=str: Fail (invalid value)

    Example:
        >>> from babylon.economics.dynamics.types import TransitionRates
        >>> rates = TransitionRates(fips="00000", year=2015,
        ...     dispossession=0.01, accumulation=0.01,
        ...     precaritization=0.02, stabilization=0.05)
        >>> validate_transition_rates(rates)
        (True, None)
    """
    checks = [
        _check_rate(
            "dispossession",
            rates.dispossession,
            DISPOSSESSION_EXPECTED_MIN,
            DISPOSSESSION_EXPECTED_MAX,
            DISPOSSESSION_WARNING_MIN,
            DISPOSSESSION_WARNING_MAX,
            DISPOSSESSION_FAIL_MAX,
        ),
        _check_rate(
            "accumulation",
            rates.accumulation,
            ACCUMULATION_EXPECTED_MIN,
            ACCUMULATION_EXPECTED_MAX,
            ACCUMULATION_WARNING_MIN,
            ACCUMULATION_WARNING_MAX,
            ACCUMULATION_FAIL_MAX,
        ),
        _check_rate(
            "precaritization",
            rates.precaritization,
            PRECARITIZATION_EXPECTED_MIN,
            PRECARITIZATION_EXPECTED_MAX,
            PRECARITIZATION_WARNING_MIN,
            PRECARITIZATION_WARNING_MAX,
            PRECARITIZATION_FAIL_MAX,
        ),
        _check_rate(
            "stabilization",
            rates.stabilization,
            STABILIZATION_EXPECTED_MIN,
            STABILIZATION_EXPECTED_MAX,
            STABILIZATION_WARNING_MIN,
            STABILIZATION_WARNING_MAX,
            STABILIZATION_FAIL_MAX,
        ),
    ]

    # Return first failure, or first warning, or (True, None)
    for valid, message in checks:
        if not valid:
            return (valid, message)

    for valid, message in checks:
        if message is not None:
            return (valid, message)

    return (True, None)


def _check_share(
    name: str,
    value: float,
    expected_min: float,
    expected_max: float,
    warning_min: float,
    warning_max: float,
) -> tuple[bool, str | None]:
    """Check a single class share against three-tier ranges.

    Args:
        name: Share name for error messages.
        value: Share value to validate.
        expected_min: Lower bound of expected range.
        expected_max: Upper bound of expected range.
        warning_min: Lower bound of warning range.
        warning_max: Upper bound of warning range.

    Returns:
        Tuple of (valid, message).
    """
    if value < 0.0 or value > 1.0:
        return (
            False,
            f"{name}={value:.4f} outside valid range [0.0, 1.0]",
        )

    if value < warning_min or value > warning_max:
        return (
            True,
            f"WARNING: {name}={value:.4f} outside warning range [{warning_min}, {warning_max}]",
        )

    if value < expected_min or value > expected_max:
        return (
            True,
            f"WARNING: {name}={value:.4f} outside expected range [{expected_min}, {expected_max}]",
        )

    return (True, None)


def validate_class_shares(
    la_share: float,
    proletariat_share: float,
    lumpen_share: float,
) -> tuple[bool, str | None]:
    """Validate class shares against three-tier ranges.

    Args:
        la_share: Labor aristocracy share.
        proletariat_share: Proletariat share.
        lumpen_share: Lumpenproletariat share.

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: All shares in expected range
        - valid=True, message=str: Warning (unusual value)
        - valid=False, message=str: Fail (invalid value)

    Example:
        >>> validate_class_shares(0.40, 0.35, 0.15)
        (True, None)
    """
    checks = [
        _check_share(
            "la_share",
            la_share,
            LA_SHARE_EXPECTED_MIN,
            LA_SHARE_EXPECTED_MAX,
            LA_SHARE_WARNING_MIN,
            LA_SHARE_WARNING_MAX,
        ),
        _check_share(
            "proletariat_share",
            proletariat_share,
            PROLETARIAT_SHARE_EXPECTED_MIN,
            PROLETARIAT_SHARE_EXPECTED_MAX,
            PROLETARIAT_SHARE_WARNING_MIN,
            PROLETARIAT_SHARE_WARNING_MAX,
        ),
        _check_share(
            "lumpen_share",
            lumpen_share,
            LUMPEN_SHARE_EXPECTED_MIN,
            LUMPEN_SHARE_EXPECTED_MAX,
            LUMPEN_SHARE_WARNING_MIN,
            LUMPEN_SHARE_WARNING_MAX,
        ),
    ]

    # Return first failure, or first warning, or (True, None)
    for valid, message in checks:
        if not valid:
            return (valid, message)

    for valid, message in checks:
        if message is not None:
            return (valid, message)

    return (True, None)


__all__ = [
    "validate_class_shares",
    "validate_transition_rates",
]
