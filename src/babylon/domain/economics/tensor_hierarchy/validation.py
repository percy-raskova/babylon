"""Three-tier validation for tensor hierarchy types.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Follows the same three-tier pattern as gamma/validation.py:
    - Expected: Normal operating range (returns True, None)
    - Warning: Unusual but valid (returns True, warning_str)
    - Fail: Invalid value (returns False, error_str)

See Also:
    :mod:`babylon.domain.economics.gamma.validation`: Original pattern from Feature 015.
"""

from __future__ import annotations

import numpy as np

# =============================================================================
# INTER-INDUSTRY FLOW VALIDATION RANGES
# =============================================================================

# Column sums of the direct requirements matrix A
IO_COL_SUM_EXPECTED_MAX: float = 0.90  # Typical productive economy
IO_COL_SUM_WARNING_MAX: float = 0.99  # Near-singular, unusual
IO_COL_SUM_FAIL_MAX: float = 1.0  # Violates Hawkins-Simon (not productive)

# Individual coefficient values
IO_COEFF_EXPECTED_MAX: float = 0.60  # Any single industry dominance
IO_COEFF_WARNING_MAX: float = 0.85  # Very concentrated
IO_COEFF_FAIL_MIN: float = 0.0  # Must be non-negative
IO_COEFF_FAIL_MAX: float = 1.0  # Must be < 1.0 for direct requirements

# =============================================================================
# VISIBILITY METRIC VALIDATION RANGES (per data-model.md)
# =============================================================================

# g_33 (Dept III reproductive care)
G33_EXPECTED_MIN: float = 0.20
G33_EXPECTED_MAX: float = 0.40
G33_WARNING_MIN: float = 0.10
G33_WARNING_MAX: float = 0.50
G33_FAIL_MIN: float = 0.0
G33_FAIL_MAX: float = 1.0

# g_11, g_22a, g_22b (productive departments, expected near 1.0)
G_PRODUCTIVE_EXPECTED_MIN: float = 0.90
G_PRODUCTIVE_EXPECTED_MAX: float = 1.0
G_PRODUCTIVE_WARNING_MIN: float = 0.70
G_PRODUCTIVE_WARNING_MAX: float = 1.0
G_PRODUCTIVE_FAIL_MIN: float = 0.0
G_PRODUCTIVE_FAIL_MAX: float = 1.0

# =============================================================================
# GEOGRAPHIC FLOW VALIDATION RANGES
# =============================================================================

# Imperial rent conservation: |sum(phi)| / total_flow
RENT_CONSERVATION_EXPECTED_MAX: float = 0.0001  # < 0.01% of total flow
RENT_CONSERVATION_WARNING_MAX: float = 0.001  # < 0.1% of total flow
RENT_CONSERVATION_FAIL_MAX: float = 0.01  # > 1% violates conservation

# =============================================================================
# CLASS TRANSITION VALIDATION RANGES
# =============================================================================

# Row sum deviation from 1.0 (stochastic matrix)
TRANSITION_ROW_SUM_TOLERANCE: float = 1e-6  # Expected: exactly 1.0
TRANSITION_ROW_SUM_WARNING: float = 1e-4  # Warning: near 1.0

# Diagonal (self-transition probability) - class mobility
TRANSITION_DIAGONAL_EXPECTED_MIN: float = 0.50  # Most stay in class
TRANSITION_DIAGONAL_WARNING_MIN: float = 0.20  # High mobility
TRANSITION_DIAGONAL_FAIL_MIN: float = 0.0  # Must be non-negative


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_io_column_sums(
    coefficients: np.ndarray,
) -> tuple[bool, str | None]:
    """Validate that I-O column sums satisfy Hawkins-Simon condition.

    For a productive economy, all column sums of A must be < 1.0
    (otherwise the industry consumes more than it produces).

    Args:
        coefficients: Direct requirements matrix A, shape (n, n).

    Returns:
        Tuple of (valid, message):
        - valid=True, message=None: Column sums in expected range.
        - valid=True, message=str: Warning (near singular).
        - valid=False, message=str: Fail (column sum >= 1.0).

    Example:
        >>> import numpy as np
        >>> mat = np.array([[0.1, 0.2], [0.15, 0.05]])
        >>> validate_io_column_sums(mat)
        (True, None)
    """
    col_sums = coefficients.sum(axis=0)
    max_col_sum = float(col_sums.max())

    if max_col_sum >= IO_COL_SUM_FAIL_MAX:
        return (
            False,
            f"I-O column sum {max_col_sum:.4f} >= {IO_COL_SUM_FAIL_MAX} "
            f"(violates Hawkins-Simon productive economy condition)",
        )

    if max_col_sum >= IO_COL_SUM_WARNING_MAX:
        return (
            True,
            f"WARNING: I-O max column sum {max_col_sum:.4f} >= {IO_COL_SUM_WARNING_MAX} "
            f"(near-singular matrix, check for data quality issues)",
        )

    return (True, None)


def validate_leontief_properties(
    inverse_matrix: np.ndarray,
) -> tuple[bool, str | None]:
    """Validate Leontief inverse matrix properties.

    The Leontief inverse L = (I - A)^{-1} must have:
    - All elements >= 0 (productive economy produces non-negative outputs)
    - Diagonal elements >= 1.0 (own total requirements >= direct)

    Args:
        inverse_matrix: Leontief inverse matrix, shape (n, n).

    Returns:
        Tuple of (valid, message).

    Example:
        >>> import numpy as np
        >>> L = np.array([[1.15, 0.25], [0.18, 1.08]])
        >>> validate_leontief_properties(L)
        (True, None)
    """
    min_val = float(inverse_matrix.min())
    if min_val < -1e-10:
        return (
            False,
            f"Leontief inverse has negative element {min_val:.6f} "
            f"(violates non-negativity for productive economy)",
        )

    min_diag = float(np.diag(inverse_matrix).min())
    if min_diag < 1.0 - 1e-10:
        return (
            False,
            f"Leontief inverse diagonal min {min_diag:.6f} < 1.0 "
            f"(total requirements must exceed direct requirements)",
        )

    return (True, None)


def validate_g33(value: float) -> tuple[bool, str | None]:
    """Validate g_33 (Dept III visibility) against sanity ranges.

    Expected range [0.20, 0.40] based on ATUS data showing ~1/3 of
    care work is commodified in the US.

    Args:
        value: g_33 visibility coefficient.

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_g33(0.333)
        (True, None)
        >>> validate_g33(0.05)
        (True, 'WARNING: ...')
        >>> validate_g33(-0.1)
        (False, '...')
    """
    if value < G33_FAIL_MIN or value > G33_FAIL_MAX:
        return (
            False,
            f"g_33={value:.3f} outside valid range [{G33_FAIL_MIN}, {G33_FAIL_MAX}]",
        )

    if value < G33_EXPECTED_MIN or value > G33_EXPECTED_MAX:
        return (
            True,
            f"WARNING: g_33={value:.3f} outside expected range "
            f"[{G33_EXPECTED_MIN}, {G33_EXPECTED_MAX}]",
        )

    return (True, None)


def validate_g_productive(name: str, value: float) -> tuple[bool, str | None]:
    """Validate productive department visibility (g_11, g_22a, g_22b).

    Expected near 1.0 since productive departments are mostly paid labor.

    Args:
        name: Department name for error messages (e.g., 'g_11').
        value: Visibility coefficient.

    Returns:
        Tuple of (valid, message).

    Example:
        >>> validate_g_productive("g_11", 0.95)
        (True, None)
        >>> validate_g_productive("g_11", 0.75)
        (True, 'WARNING: ...')
    """
    if value < G_PRODUCTIVE_FAIL_MIN or value > G_PRODUCTIVE_FAIL_MAX:
        return (
            False,
            f"{name}={value:.3f} outside valid range "
            f"[{G_PRODUCTIVE_FAIL_MIN}, {G_PRODUCTIVE_FAIL_MAX}]",
        )

    if value < G_PRODUCTIVE_EXPECTED_MIN or value > G_PRODUCTIVE_EXPECTED_MAX:
        return (
            True,
            f"WARNING: {name}={value:.3f} outside expected range "
            f"[{G_PRODUCTIVE_EXPECTED_MIN}, {G_PRODUCTIVE_EXPECTED_MAX}]",
        )

    return (True, None)


def validate_rent_conservation(phi: np.ndarray, flow_matrix: np.ndarray) -> tuple[bool, str | None]:
    """Validate imperial rent field conservation (closed system).

    For a closed system sum(phi) ≈ 0 (value extracted equals value donated).
    Allows small floating-point deviations expressed as fraction of total flow.

    Args:
        phi: Net value extraction vector, shape (n_areas,).
        flow_matrix: Original O-D flow matrix, shape (n, n).

    Returns:
        Tuple of (valid, message).

    Example:
        >>> import numpy as np
        >>> phi = np.array([50.0, -50.0])
        >>> F = np.array([[100.0, 50.0], [30.0, 200.0]])
        >>> validate_rent_conservation(phi, F)
        (True, None)
    """
    total_flow = float(flow_matrix.sum())
    if total_flow < 1e-10:
        return (True, None)  # Empty flow matrix, skip conservation check

    phi_sum = abs(float(phi.sum()))
    ratio = phi_sum / total_flow

    if ratio > RENT_CONSERVATION_FAIL_MAX:
        return (
            False,
            f"Imperial rent sum imbalance {phi_sum:.2f} = {ratio * 100:.2f}% of total flow "
            f"{total_flow:.2f} exceeds {RENT_CONSERVATION_FAIL_MAX * 100:.1f}% threshold",
        )

    if ratio > RENT_CONSERVATION_WARNING_MAX:
        return (
            True,
            f"WARNING: Imperial rent sum {phi_sum:.2f} = {ratio * 100:.3f}% of total flow "
            f"exceeds {RENT_CONSERVATION_WARNING_MAX * 100:.2f}% warning threshold",
        )

    return (True, None)


def validate_transition_matrix(matrix: np.ndarray) -> tuple[bool, str | None]:
    """Validate class transition matrix is row-stochastic.

    Each row must sum to 1.0 and all elements must be in [0, 1].

    Args:
        matrix: Transition probability matrix, shape (n, n).

    Returns:
        Tuple of (valid, message).

    Example:
        >>> import numpy as np
        >>> P = np.array([[0.9, 0.1], [0.3, 0.7]])
        >>> validate_transition_matrix(P)
        (True, None)
    """
    if float(matrix.min()) < 0.0:
        return (
            False,
            f"Transition matrix has negative element {float(matrix.min()):.6f}",
        )

    row_sums = matrix.sum(axis=1)
    max_deviation = float(abs(row_sums - 1.0).max())

    if max_deviation > TRANSITION_ROW_SUM_WARNING:
        return (
            False,
            f"Transition matrix row sum deviation {max_deviation:.8f} "
            f"exceeds warning threshold {TRANSITION_ROW_SUM_WARNING}",
        )

    if max_deviation > TRANSITION_ROW_SUM_TOLERANCE:
        return (
            True,
            f"WARNING: Transition matrix row sum deviation {max_deviation:.8f} "
            f"exceeds precision tolerance {TRANSITION_ROW_SUM_TOLERANCE}",
        )

    return (True, None)


__all__ = [
    "validate_g33",
    "validate_g_productive",
    "validate_io_column_sums",
    "validate_leontief_properties",
    "validate_rent_conservation",
    "validate_transition_matrix",
]
