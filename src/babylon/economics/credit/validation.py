"""Three-tier validation for credit and financialization metrics.

Feature: 024-capital-volume-iii (Phase 12)

Validation pattern: Expected/Warning/Fail ranges per metric.
Return: ``tuple[bool, str | None]``

- ``(True, None)`` = within expected range
- ``(True, "WARNING: ...")`` = unusual but valid
- ``(False, "error")`` = invalid

See Also:
    :mod:`babylon.economics.gamma.validation`: Original validation pattern
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# FINANCIALIZATION INDEX VALIDATION RANGES
# =============================================================================
# Traceability: FRED TCMDO/GDP historical ratio
FINANCIALIZATION_EXPECTED_MIN: Final[float] = 1.5
FINANCIALIZATION_EXPECTED_MAX: Final[float] = 3.0
FINANCIALIZATION_WARNING_MIN: Final[float] = 0.5
FINANCIALIZATION_WARNING_MAX: Final[float] = 5.0
FINANCIALIZATION_FAIL_MIN: Final[float] = 0.0
FINANCIALIZATION_FAIL_MAX: Final[float] = 20.0

# =============================================================================
# INTEREST BURDEN RATIO VALIDATION RANGES
# =============================================================================
# Traceability: FRED NIPA net interest / corporate profits
INTEREST_BURDEN_EXPECTED_MIN: Final[float] = 0.05
INTEREST_BURDEN_EXPECTED_MAX: Final[float] = 0.35
INTEREST_BURDEN_WARNING_MIN: Final[float] = 0.0
INTEREST_BURDEN_WARNING_MAX: Final[float] = 0.60
INTEREST_BURDEN_FAIL_MIN: Final[float] = 0.0
INTEREST_BURDEN_FAIL_MAX: Final[float] = 1.0


def validate_financialization_index(value: float) -> tuple[bool, str | None]:
    """Validate financialization index against sanity ranges.

    Sanity Ranges:
        - Expected: [1.5, 3.0] (typical US TCMDO/GDP ratio)
        - Warning: [0.5, 5.0] (unusual but possible)
        - Fail: <0 or >20 (invalid)

    Args:
        value: Financialization index to validate.

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: Within expected range
        - valid=True, message=str: Warning (unusual value)
        - valid=False, message=str: Fail (invalid value)

    Example:
        >>> validate_financialization_index(2.0)
        (True, None)
    """
    if value < FINANCIALIZATION_FAIL_MIN or value > FINANCIALIZATION_FAIL_MAX:
        return (
            False,
            f"financialization_index={value:.3f} outside valid range "
            f"[{FINANCIALIZATION_FAIL_MIN}, {FINANCIALIZATION_FAIL_MAX}]",
        )

    if value < FINANCIALIZATION_EXPECTED_MIN or value > FINANCIALIZATION_EXPECTED_MAX:
        return (
            True,
            f"WARNING: financialization_index={value:.3f} outside expected range "
            f"[{FINANCIALIZATION_EXPECTED_MIN}, {FINANCIALIZATION_EXPECTED_MAX}]",
        )

    return (True, None)


def validate_interest_burden_ratio(value: float) -> tuple[bool, str | None]:
    """Validate interest burden ratio against sanity ranges.

    Sanity Ranges:
        - Expected: [0.05, 0.35] (typical NIPA net interest / profits)
        - Warning: [0.0, 0.60] (unusual but possible)
        - Fail: <0 or >1 (invalid)

    Args:
        value: Interest burden ratio to validate.

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: Within expected range
        - valid=True, message=str: Warning (unusual value)
        - valid=False, message=str: Fail (invalid value)

    Example:
        >>> validate_interest_burden_ratio(0.20)
        (True, None)
    """
    if value < INTEREST_BURDEN_FAIL_MIN or value > INTEREST_BURDEN_FAIL_MAX:
        return (
            False,
            f"interest_burden_ratio={value:.3f} outside valid range "
            f"[{INTEREST_BURDEN_FAIL_MIN}, {INTEREST_BURDEN_FAIL_MAX}]",
        )

    if value < INTEREST_BURDEN_EXPECTED_MIN or value > INTEREST_BURDEN_EXPECTED_MAX:
        return (
            True,
            f"WARNING: interest_burden_ratio={value:.3f} outside expected range "
            f"[{INTEREST_BURDEN_EXPECTED_MIN}, {INTEREST_BURDEN_EXPECTED_MAX}]",
        )

    return (True, None)


__all__: list[str] = [
    "validate_financialization_index",
    "validate_interest_burden_ratio",
]
