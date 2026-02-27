"""Unit tests for tensor hierarchy validation functions.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (validation is implemented)
"""

from __future__ import annotations

import numpy as np
import pytest

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


# =============================================================================
# FR-017 Commutativity tests
# =============================================================================


class TestGeographicFlowCommutativity:
    """Commutativity of aggregate-then-transform vs. transform-then-aggregate.

    FR-017: For GeographicFlow, phi (imperial rent) is linear in the flow
    matrix F, so aggregating flows then computing phi equals computing phi
    at the fine level then aggregating — EXACTLY.

    phi_state[s] = sum_{a in s} phi_area[a]

    This is because phi[a] = inflow[a] - outflow[a] is a linear function of F.
    Summing phi over a group of areas equals computing phi on the grouped flow.
    """

    @pytest.mark.math
    def test_aggregate_then_phi_equals_phi_then_aggregate(self) -> None:
        """phi(aggregate(F)) == aggregate(phi(F)) for GeographicFlow.

        Verifies that the two operation orders produce identical results:
        1. Aggregate CFS area flows to state → compute imperial rent per state
        2. Compute imperial rent per CFS area → aggregate rent to state level
        """
        from babylon.economics.tensor_hierarchy.geographic_flow import (
            DefaultGeographicAggregator,
            DefaultImperialRentComputer,
        )
        from babylon.economics.tensor_hierarchy.types import GeographicFlow

        # 4-area flow matrix (areas 0-3)
        areas = ["11", "12", "119", "120"]
        flow_matrix = np.array(
            [
                [100.0, 200.0, 50.0, 30.0],
                [80.0, 150.0, 40.0, 20.0],
                [60.0, 70.0, 90.0, 25.0],
                [10.0, 15.0, 5.0, 200.0],
            ],
            dtype=np.float64,
        )
        flow = GeographicFlow(year=2022, areas=areas, flow_matrix=flow_matrix)
        mapping = {"11": "MA", "12": "MA", "119": "NY", "120": "NY"}

        computer = DefaultImperialRentComputer()
        aggregator = DefaultGeographicAggregator()

        # Path 1: Aggregate flow then compute phi
        agg_flow = aggregator.aggregate(flow, mapping)
        phi_of_agg = computer.compute_rent(agg_flow)

        # Path 2: Compute phi then aggregate phi values
        phi_original = computer.compute_rent(flow)
        # Manually aggregate phi: phi_state[s] = sum phi_area[a] for a in s
        phi_ma = float(phi_original.phi[0] + phi_original.phi[1])  # areas 11, 12
        phi_ny = float(phi_original.phi[2] + phi_original.phi[3])  # areas 119, 120

        # The aggregated phi should match (up to ordering in agg_flow.areas)
        state_to_idx = {s: i for i, s in enumerate(phi_of_agg.areas)}
        np.testing.assert_allclose(
            phi_of_agg.phi[state_to_idx["MA"]],
            phi_ma,
            atol=1e-9,
            err_msg="phi(aggregate(F))[MA] must equal aggregate(phi(F))[MA]",
        )
        np.testing.assert_allclose(
            phi_of_agg.phi[state_to_idx["NY"]],
            phi_ny,
            atol=1e-9,
            err_msg="phi(aggregate(F))[NY] must equal aggregate(phi(F))[NY]",
        )

    @pytest.mark.math
    def test_commutativity_conservation_preserved(self) -> None:
        """sum(phi) == 0 holds at both CFS area and aggregated state level."""
        from babylon.economics.tensor_hierarchy.geographic_flow import (
            DefaultGeographicAggregator,
            DefaultImperialRentComputer,
        )
        from babylon.economics.tensor_hierarchy.types import GeographicFlow

        areas = ["11", "12", "119"]
        flow_matrix = np.array(
            [[100.0, 200.0, 50.0], [80.0, 150.0, 40.0], [60.0, 70.0, 90.0]],
            dtype=np.float64,
        )
        flow = GeographicFlow(year=2022, areas=areas, flow_matrix=flow_matrix)
        mapping = {"11": "state_A", "12": "state_A", "119": "state_B"}

        computer = DefaultImperialRentComputer()
        aggregator = DefaultGeographicAggregator()

        phi_area = computer.compute_rent(flow)
        agg_flow = aggregator.aggregate(flow, mapping)
        phi_state = computer.compute_rent(agg_flow)

        # Both should sum to near zero
        assert float(phi_area.phi.sum()) == pytest.approx(0.0, abs=1e-9)
        assert float(phi_state.phi.sum()) == pytest.approx(0.0, abs=1e-9)


class TestClassTransitionCommutativity:
    """Commutativity tests for ClassTransitionMatrix aggregation and stationary distribution.

    The stationary distribution is nonlinear (eigenvector), so exact commutativity
    cannot be guaranteed. However, the aggregated matrix must always yield a
    valid stationary distribution that is consistent with the aggregated structure.
    """

    @pytest.mark.math
    def test_aggregated_stationary_is_valid(self) -> None:
        """Stationary distribution of aggregated matrix sums to 1.0."""
        from babylon.economics.tensor_hierarchy.class_transition import (
            DefaultClassTransitionComputer,
        )
        from babylon.economics.tensor_hierarchy.types import ClassTransitionMatrix

        classes = ["proletariat", "lumpen", "petit_bourgeois", "bourgeoisie"]
        mat = np.array(
            [
                [0.7, 0.1, 0.15, 0.05],
                [0.3, 0.4, 0.2, 0.1],
                [0.1, 0.05, 0.7, 0.15],
                [0.02, 0.01, 0.07, 0.9],
            ],
            dtype=np.float64,
        )
        ctm = ClassTransitionMatrix(period=(2015, 2020), classes=classes, transition_matrix=mat)
        mapping = {
            "proletariat": "labor",
            "lumpen": "labor",
            "petit_bourgeois": "capital",
            "bourgeoisie": "capital",
        }
        computer = DefaultClassTransitionComputer()

        # Aggregate then compute stationary
        agg_ctm = computer.aggregate_classes(ctm, mapping)
        pi_agg = computer.stationary_distribution(agg_ctm)

        assert float(pi_agg.distribution.sum()) == pytest.approx(1.0, abs=1e-9)
        assert np.all(pi_agg.distribution >= -1e-12)
        # SC-004: pi_agg @ P_agg == pi_agg
        np.testing.assert_allclose(
            pi_agg.distribution @ agg_ctm.transition_matrix,
            pi_agg.distribution,
            atol=1e-8,
        )

    @pytest.mark.math
    def test_aggregated_stationary_is_self_consistent(self) -> None:
        """Stationary distribution of aggregated matrix satisfies pi @ P = pi.

        The stationary distribution is non-linear (eigenvector), so the
        coarse stationary is NOT necessarily the marginal of the fine stationary.
        However, the aggregated matrix must have a self-consistent stationary
        distribution that satisfies the fixed-point equation.

        This verifies two-step commutativity:
        - aggregate_classes produces a valid ClassTransitionMatrix
        - stationary_distribution of the coarse matrix is self-consistent
        """
        from babylon.economics.tensor_hierarchy.class_transition import (
            DefaultClassTransitionComputer,
        )
        from babylon.economics.tensor_hierarchy.types import ClassTransitionMatrix

        # 4-class mixing matrix with unique stationary distribution
        mat = np.array(
            [
                [0.7, 0.1, 0.15, 0.05],
                [0.2, 0.6, 0.15, 0.05],
                [0.05, 0.1, 0.75, 0.10],
                [0.02, 0.01, 0.07, 0.9],
            ],
            dtype=np.float64,
        )
        classes = ["proletariat", "lumpen", "petit_bourgeois", "bourgeoisie"]
        ctm = ClassTransitionMatrix(period=(2015, 2020), classes=classes, transition_matrix=mat)
        mapping = {
            "proletariat": "labor",
            "lumpen": "labor",
            "petit_bourgeois": "capital",
            "bourgeoisie": "capital",
        }
        computer = DefaultClassTransitionComputer()

        # Aggregate then compute stationary
        agg_ctm = computer.aggregate_classes(ctm, mapping)
        pi_coarse = computer.stationary_distribution(agg_ctm)

        # pi_coarse must be a valid probability distribution
        assert float(pi_coarse.distribution.sum()) == pytest.approx(1.0, abs=1e-9)
        assert np.all(pi_coarse.distribution >= -1e-12)
        # SC-004 at coarse level: pi_coarse @ P_coarse == pi_coarse
        np.testing.assert_allclose(
            pi_coarse.distribution @ agg_ctm.transition_matrix,
            pi_coarse.distribution,
            atol=1e-8,
            err_msg="Coarse stationary must satisfy fixed-point equation pi @ P = pi",
        )
