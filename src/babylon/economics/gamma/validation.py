"""Three-tier validation functions for gamma visibility coefficients.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

Validation follows the same pattern as ``basket_visibility.py``:
    - Expected: Normal operating range (no message)
    - Warning: Unusual but possible (returns warning message)
    - Fail: Invalid value (returns error message, valid=False)

See Also:
    :mod:`babylon.economics.melt.basket_visibility`: Original validation pattern
"""

from __future__ import annotations

# =============================================================================
# GAMMA III VALIDATION RANGES
# =============================================================================

GAMMA_III_EXPECTED_MIN: float = 0.20
GAMMA_III_EXPECTED_MAX: float = 0.40
GAMMA_III_WARNING_MIN: float = 0.10
GAMMA_III_WARNING_MAX: float = 0.50
GAMMA_III_FAIL_MIN: float = 0.0
GAMMA_III_FAIL_MAX: float = 1.0

# =============================================================================
# GAMMA IMPORT VALIDATION RANGES
# =============================================================================

GAMMA_IMPORT_EXPECTED_MIN: float = 0.40
GAMMA_IMPORT_EXPECTED_MAX: float = 0.70
GAMMA_IMPORT_WARNING_MIN: float = 0.30
GAMMA_IMPORT_WARNING_MAX: float = 0.80
GAMMA_IMPORT_FAIL_MIN: float = 0.0  # must be > 0
GAMMA_IMPORT_FAIL_MAX: float = 1.0

# =============================================================================
# GAMMA BASKET VALIDATION RANGES
# =============================================================================

GAMMA_BASKET_EXPECTED_MIN: float = 0.60
GAMMA_BASKET_EXPECTED_MAX: float = 0.85
GAMMA_BASKET_WARNING_MIN: float = 0.40
GAMMA_BASKET_WARNING_MAX: float = 0.95
GAMMA_BASKET_FAIL_MIN: float = 0.0  # must be > 0
GAMMA_BASKET_FAIL_MAX: float = 1.0


def validate_gamma_iii(value: float) -> tuple[bool, str | None]:
    """Validate gamma_III against sanity ranges.

    Sanity Ranges:
        - Expected: [0.20, 0.40] (typical US reproductive visibility)
        - Warning: [0.10, 0.50] (unusual but possible)
        - Fail: <0 or >1 (invalid)

    Args:
        value: Gamma III visibility coefficient to validate.

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: Within expected range
        - valid=True, message=str: Warning (unusual value)
        - valid=False, message=str: Fail (invalid value)

    Example:
        >>> validate_gamma_iii(0.33)
        (True, None)
        >>> validate_gamma_iii(0.15)
        (True, 'WARNING: ...')
        >>> validate_gamma_iii(-0.1)
        (False, '...')
    """
    if value < GAMMA_III_FAIL_MIN or value > GAMMA_III_FAIL_MAX:
        return (
            False,
            f"gamma_III={value:.3f} outside valid range "
            f"[{GAMMA_III_FAIL_MIN}, {GAMMA_III_FAIL_MAX}]",
        )

    if value < GAMMA_III_EXPECTED_MIN or value > GAMMA_III_EXPECTED_MAX:
        return (
            True,
            f"WARNING: gamma_III={value:.3f} outside expected range "
            f"[{GAMMA_III_EXPECTED_MIN}, {GAMMA_III_EXPECTED_MAX}]",
        )

    return (True, None)


def validate_gamma_import(value: float) -> tuple[bool, str | None]:
    """Validate gamma_import against sanity ranges.

    Sanity Ranges:
        - Expected: [0.40, 0.70] (typical US import basket visibility)
        - Warning: [0.30, 0.80] (unusual but possible)
        - Fail: <=0 or >1 (invalid)

    Args:
        value: Gamma import visibility coefficient to validate.

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_gamma_import(0.65)
        (True, None)
        >>> validate_gamma_import(0.35)
        (True, 'WARNING: ...')
        >>> validate_gamma_import(0.0)
        (False, '...')
    """
    if value <= GAMMA_IMPORT_FAIL_MIN or value > GAMMA_IMPORT_FAIL_MAX:
        return (
            False,
            f"gamma_import={value:.3f} outside valid range "
            f"({GAMMA_IMPORT_FAIL_MIN}, {GAMMA_IMPORT_FAIL_MAX}]",
        )

    if value < GAMMA_IMPORT_EXPECTED_MIN or value > GAMMA_IMPORT_EXPECTED_MAX:
        return (
            True,
            f"WARNING: gamma_import={value:.3f} outside expected range "
            f"[{GAMMA_IMPORT_EXPECTED_MIN}, {GAMMA_IMPORT_EXPECTED_MAX}]",
        )

    return (True, None)


def validate_gamma_basket(value: float) -> tuple[bool, str | None]:
    """Validate gamma_basket against sanity ranges.

    Sanity Ranges:
        - Expected: [0.60, 0.85] (typical US basket visibility)
        - Warning: [0.40, 0.95] (unusual but possible)
        - Fail: <=0 or >1 (invalid)

    Args:
        value: Gamma basket visibility coefficient to validate.

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_gamma_basket(0.74)
        (True, None)
        >>> validate_gamma_basket(0.45)
        (True, 'WARNING: ...')
        >>> validate_gamma_basket(0.0)
        (False, '...')
    """
    if value <= GAMMA_BASKET_FAIL_MIN or value > GAMMA_BASKET_FAIL_MAX:
        return (
            False,
            f"gamma_basket={value:.3f} outside valid range "
            f"({GAMMA_BASKET_FAIL_MIN}, {GAMMA_BASKET_FAIL_MAX}]",
        )

    if value < GAMMA_BASKET_EXPECTED_MIN or value > GAMMA_BASKET_EXPECTED_MAX:
        return (
            True,
            f"WARNING: gamma_basket={value:.3f} outside expected range "
            f"[{GAMMA_BASKET_EXPECTED_MIN}, {GAMMA_BASKET_EXPECTED_MAX}]",
        )

    return (True, None)


__all__ = [
    "validate_gamma_basket",
    "validate_gamma_iii",
    "validate_gamma_import",
]
