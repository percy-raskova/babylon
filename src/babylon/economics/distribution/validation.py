"""Three-tier validation for surplus distribution metrics.

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
# RENTIER SHARE VALIDATION RANGES
# =============================================================================
# Traceability: BEA rental income / total surplus value
RENTIER_SHARE_EXPECTED_MIN: Final[float] = 0.02
RENTIER_SHARE_EXPECTED_MAX: Final[float] = 0.15
RENTIER_SHARE_WARNING_MIN: Final[float] = 0.0
RENTIER_SHARE_WARNING_MAX: Final[float] = 0.30
RENTIER_SHARE_FAIL_MIN: Final[float] = 0.0
RENTIER_SHARE_FAIL_MAX: Final[float] = 1.0


def validate_rentier_share(value: float) -> tuple[bool, str | None]:
    """Validate rentier share of surplus against sanity ranges.

    Sanity Ranges:
        - Expected: [0.02, 0.15] (typical BEA rental income / surplus)
        - Warning: [0.0, 0.30] (unusual but possible)
        - Fail: <0 or >1 (invalid)

    Args:
        value: Rentier share ratio to validate.

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: Within expected range
        - valid=True, message=str: Warning (unusual value)
        - valid=False, message=str: Fail (invalid value)

    Example:
        >>> validate_rentier_share(0.08)
        (True, None)
    """
    if value < RENTIER_SHARE_FAIL_MIN or value > RENTIER_SHARE_FAIL_MAX:
        return (
            False,
            f"rentier_share={value:.3f} outside valid range "
            f"[{RENTIER_SHARE_FAIL_MIN}, {RENTIER_SHARE_FAIL_MAX}]",
        )

    if value < RENTIER_SHARE_EXPECTED_MIN or value > RENTIER_SHARE_EXPECTED_MAX:
        return (
            True,
            f"WARNING: rentier_share={value:.3f} outside expected range "
            f"[{RENTIER_SHARE_EXPECTED_MIN}, {RENTIER_SHARE_EXPECTED_MAX}]",
        )

    return (True, None)


__all__: list[str] = [
    "validate_rentier_share",
]
