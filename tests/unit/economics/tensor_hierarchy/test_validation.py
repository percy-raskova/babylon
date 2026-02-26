"""Unit tests for tensor hierarchy validation functions.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (validation is implemented)
"""

from __future__ import annotations

import numpy as np

from babylon.economics.tensor_hierarchy.validation import (
    validate_g33,
    validate_g_productive,
    validate_io_column_sums,
    validate_leontief_properties,
    validate_rent_conservation,
    validate_transition_matrix,
)

# =============================================================================
# validate_io_column_sums
# =============================================================================


class TestValidateIOColumnSums:
    """Tests for I-O column sum validation."""

    def test_expected_range(self) -> None:
        """Typical productive economy passes with no warning."""
        mat = np.array([[0.1, 0.2], [0.15, 0.05]])
        valid, msg = validate_io_column_sums(mat)
        assert valid is True
        assert msg is None

    def test_near_singular_warns(self) -> None:
        """Column sum near 1.0 produces warning."""
        mat = np.array([[0.50, 0.20], [0.49, 0.30]])  # col 0 sums to 0.99
        valid, msg = validate_io_column_sums(mat)
        assert valid is True
        assert msg is not None
        assert "WARNING" in msg

    def test_column_sum_gte_one_fails(self) -> None:
        """Column sum >= 1.0 fails (violates Hawkins-Simon)."""
        mat = np.array([[0.60, 0.20], [0.50, 0.30]])  # col 0 sums to 1.10
        valid, msg = validate_io_column_sums(mat)
        assert valid is False
        assert "Hawkins-Simon" in msg

    def test_exact_boundary(self) -> None:
        """Column sum exactly 1.0 fails."""
        mat = np.array([[0.50, 0.20], [0.50, 0.30]])  # col 0 sums to 1.0
        valid, msg = validate_io_column_sums(mat)
        assert valid is False


# =============================================================================
# validate_leontief_properties
# =============================================================================


class TestValidateLeontiefProperties:
    """Tests for Leontief inverse validation."""

    def test_valid_leontief(self) -> None:
        """Proper Leontief inverse passes."""
        A = np.array([[0.1, 0.2], [0.15, 0.05]])
        L = np.linalg.inv(np.eye(2) - A)
        valid, msg = validate_leontief_properties(L)
        assert valid is True
        assert msg is None

    def test_negative_element_fails(self) -> None:
        """Negative element in Leontief inverse fails."""
        bad_L = np.array([[1.2, 0.3], [-0.01, 1.1]])  # negative element
        valid, msg = validate_leontief_properties(bad_L)
        assert valid is False
        assert "negative" in msg

    def test_diagonal_less_than_one_fails(self) -> None:
        """Diagonal < 1.0 fails (total requirements must exceed direct)."""
        bad_L = np.array([[0.9, 0.3], [0.2, 1.1]])  # diag[0] < 1.0
        valid, msg = validate_leontief_properties(bad_L)
        assert valid is False
        assert "diagonal" in msg


# =============================================================================
# validate_g33
# =============================================================================


class TestValidateG33:
    """Tests for g_33 visibility validation."""

    def test_expected_range(self) -> None:
        """Typical g_33 around 0.333 passes."""
        valid, msg = validate_g33(0.333)
        assert valid is True
        assert msg is None

    def test_low_boundary_expected(self) -> None:
        """Lower end of expected range passes."""
        valid, msg = validate_g33(0.20)
        assert valid is True
        assert msg is None

    def test_above_expected_warns(self) -> None:
        """g_33 = 0.45 (above expected max 0.40) produces warning."""
        valid, msg = validate_g33(0.45)
        assert valid is True
        assert msg is not None
        assert "WARNING" in msg

    def test_very_low_warns(self) -> None:
        """g_33 = 0.15 (below expected min 0.20) produces warning."""
        valid, msg = validate_g33(0.15)
        assert valid is True
        assert msg is not None
        assert "WARNING" in msg

    def test_negative_fails(self) -> None:
        """Negative g_33 fails."""
        valid, msg = validate_g33(-0.01)
        assert valid is False
        assert msg is not None

    def test_above_one_fails(self) -> None:
        """g_33 > 1.0 fails."""
        valid, msg = validate_g33(1.01)
        assert valid is False

    def test_zero_boundary(self) -> None:
        """g_33 = 0.0 is valid (extreme: all care unwaged)."""
        valid, msg = validate_g33(0.0)
        assert valid is True  # [0, 1] is the valid range

    def test_one_boundary(self) -> None:
        """g_33 = 1.0 is valid (extreme: all care paid)."""
        valid, msg = validate_g33(1.0)
        assert valid is True


# =============================================================================
# validate_g_productive
# =============================================================================


class TestValidateGProductive:
    """Tests for productive department visibility validation."""

    def test_typical_value(self) -> None:
        """g_11 = 1.0 (fully visible) passes."""
        valid, msg = validate_g_productive("g_11", 1.0)
        assert valid is True
        assert msg is None

    def test_near_one(self) -> None:
        """g_11 = 0.95 passes (within expected range)."""
        valid, msg = validate_g_productive("g_11", 0.95)
        assert valid is True
        assert msg is None

    def test_below_expected_warns(self) -> None:
        """g_11 = 0.80 warns (below expected min 0.90)."""
        valid, msg = validate_g_productive("g_11", 0.80)
        assert valid is True
        assert "WARNING" in msg

    def test_very_low_warns(self) -> None:
        """g_11 = 0.75 warns (below warning min 0.70)... actually expected to warn."""
        valid, msg = validate_g_productive("g_22a", 0.75)
        assert valid is True
        assert msg is not None

    def test_negative_fails(self) -> None:
        """Negative visibility fails."""
        valid, msg = validate_g_productive("g_11", -0.01)
        assert valid is False

    def test_above_one_fails(self) -> None:
        """Visibility > 1.0 fails."""
        valid, msg = validate_g_productive("g_22b", 1.01)
        assert valid is False


# =============================================================================
# validate_rent_conservation
# =============================================================================


class TestValidateRentConservation:
    """Tests for imperial rent conservation validation."""

    def test_perfectly_balanced(self) -> None:
        """Exactly balanced phi (sum = 0) passes."""
        phi = np.array([50.0, -50.0])
        F = np.array([[100.0, 50.0], [30.0, 200.0]])
        valid, msg = validate_rent_conservation(phi, F)
        assert valid is True
        assert msg is None

    def test_small_imbalance_passes(self) -> None:
        """Tiny floating-point imbalance within expected threshold."""
        phi = np.array([50.001, -50.0])  # 0.001M imbalance, total flow ~380M => 0.0003%
        F = np.array([[100.0, 50.0], [30.0, 200.0]])
        valid, msg = validate_rent_conservation(phi, F)
        assert valid is True

    def test_large_imbalance_fails(self) -> None:
        """Large imbalance (> 1% of total flow) fails."""
        phi = np.array([100.0, 0.0])  # all extraction, none donated
        F = np.array([[100.0, 50.0], [30.0, 200.0]])
        valid, msg = validate_rent_conservation(phi, F)
        assert valid is False

    def test_empty_flow_matrix(self) -> None:
        """Empty flow matrix is treated as OK (nothing to conserve)."""
        phi = np.array([0.0, 0.0])
        F = np.zeros((2, 2))
        valid, msg = validate_rent_conservation(phi, F)
        assert valid is True


# =============================================================================
# validate_transition_matrix
# =============================================================================


class TestValidateTransitionMatrix:
    """Tests for class transition matrix validation."""

    def test_valid_stochastic_matrix(self) -> None:
        """Properly stochastic matrix passes."""
        P = np.array([[0.9, 0.1], [0.3, 0.7]])
        valid, msg = validate_transition_matrix(P)
        assert valid is True
        assert msg is None

    def test_identity_passes(self) -> None:
        """Identity matrix (no class mobility) is valid."""
        valid, msg = validate_transition_matrix(np.eye(3))
        assert valid is True

    def test_negative_element_fails(self) -> None:
        """Negative probability fails."""
        P = np.array([[1.1, -0.1], [0.3, 0.7]])
        valid, msg = validate_transition_matrix(P)
        assert valid is False
        assert "negative" in msg

    def test_row_sum_deviation_fails(self) -> None:
        """Row sum significantly off from 1.0 fails."""
        P = np.array([[0.9, 0.2], [0.3, 0.7]])  # row 0 sums to 1.1
        valid, msg = validate_transition_matrix(P)
        assert valid is False
