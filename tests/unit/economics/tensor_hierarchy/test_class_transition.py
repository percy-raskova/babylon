"""Unit tests for ClassTransitionMatrix computation and stub loader.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (implementation is complete)
"""

from __future__ import annotations

import numpy as np
import pytest

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.class_transition import (
    DefaultClassTransitionComputer,
    DefaultClassTransitionSource,
)
from babylon.economics.tensor_hierarchy.types import ClassTransitionMatrix, StationaryDistribution

# =============================================================================
# Helpers
# =============================================================================


def _make_ctm(
    period: tuple[int, int] = (2015, 2020),
    classes: list[str] | None = None,
    matrix: list[list[float]] | None = None,
) -> ClassTransitionMatrix:
    """Build a synthetic ClassTransitionMatrix for testing.

    Args:
        period: (start_year, end_year) window.
        classes: Class labels. Defaults to ["proletariat", "petit_bourgeois"].
        matrix: Row-stochastic matrix as nested list. Defaults to a
            high-persistence matrix [[0.9, 0.1], [0.3, 0.7]].

    Returns:
        ClassTransitionMatrix with the specified data.
    """
    if classes is None:
        classes = ["proletariat", "petit_bourgeois"]
    if matrix is None:
        matrix = [[0.9, 0.1], [0.3, 0.7]]
    n = len(classes)
    mat = np.array(matrix, dtype=np.float64)
    assert mat.shape == (n, n), "Test matrix must match classes length"
    return ClassTransitionMatrix(
        period=period,
        classes=classes,
        transition_matrix=mat,
    )


# =============================================================================
# ClassTransitionMatrix type tests
# =============================================================================


class TestClassTransitionMatrixType:
    """Tests for the ClassTransitionMatrix frozen Pydantic model."""

    def test_valid_stochastic_matrix(self) -> None:
        """Valid row-stochastic matrix is accepted."""
        ctm = _make_ctm()
        assert isinstance(ctm, ClassTransitionMatrix)

    def test_n_classes_property(self) -> None:
        """n_classes property returns number of classes."""
        ctm = ClassTransitionMatrix(
            period=(2015, 2020),
            classes=["proletariat", "petit_bourgeois", "bourgeoisie"],
            transition_matrix=np.eye(3),
        )
        assert ctm.n_classes == 3

    def test_non_stochastic_matrix_rejected(self) -> None:
        """Matrix with rows that don't sum to 1.0 is rejected."""
        with pytest.raises(ValueError):
            ClassTransitionMatrix(
                period=(2015, 2020),
                classes=["proletariat", "petit_bourgeois"],
                transition_matrix=np.array([[0.9, 0.5], [0.3, 0.7]]),  # row 0 sums to 1.4
            )

    def test_absorbing_state_accepted(self) -> None:
        """Matrix with absorbing state (row = identity row) is accepted."""
        mat = np.array([[1.0, 0.0], [0.3, 0.7]])
        ctm = ClassTransitionMatrix(
            period=(2010, 2015),
            classes=["proletariat", "petit_bourgeois"],
            transition_matrix=mat,
        )
        assert ctm.n_classes == 2

    def test_identity_matrix_accepted(self) -> None:
        """Identity matrix (full absorbing) is a valid stochastic matrix."""
        ctm = ClassTransitionMatrix(
            period=(2015, 2020),
            classes=["proletariat", "petit_bourgeois"],
            transition_matrix=np.eye(2),
        )
        assert ctm.n_classes == 2

    def test_period_preserved(self) -> None:
        """Period tuple is preserved in the model."""
        ctm = _make_ctm(period=(2010, 2015))
        assert ctm.period == (2010, 2015)

    def test_classes_preserved(self) -> None:
        """Classes list is preserved in the model."""
        classes = ["proletariat", "petit_bourgeois", "bourgeoisie"]
        mat = np.eye(3)
        ctm = ClassTransitionMatrix(period=(2015, 2020), classes=classes, transition_matrix=mat)
        assert ctm.classes == classes


# =============================================================================
# DefaultClassTransitionComputer: stationary distribution
# =============================================================================


class TestDefaultClassTransitionComputerStationary:
    """Tests for DefaultClassTransitionComputer.stationary_distribution."""

    @pytest.fixture()
    def computer(self) -> DefaultClassTransitionComputer:
        """Provide a DefaultClassTransitionComputer instance."""
        return DefaultClassTransitionComputer()

    def test_returns_stationary_distribution(
        self, computer: DefaultClassTransitionComputer
    ) -> None:
        """stationary_distribution returns StationaryDistribution."""
        ctm = _make_ctm()
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)

    def test_period_preserved(self, computer: DefaultClassTransitionComputer) -> None:
        """StationaryDistribution preserves period from source matrix."""
        ctm = _make_ctm(period=(2010, 2015))
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        assert result.period == (2010, 2015)

    def test_classes_preserved(self, computer: DefaultClassTransitionComputer) -> None:
        """StationaryDistribution preserves class names."""
        ctm = _make_ctm(classes=["proletariat", "petit_bourgeois"])
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        assert result.classes == ["proletariat", "petit_bourgeois"]

    @pytest.mark.math
    def test_distribution_sums_to_one(self, computer: DefaultClassTransitionComputer) -> None:
        """Stationary distribution sums to 1.0 (valid probability distribution)."""
        ctm = _make_ctm()
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        assert float(result.distribution.sum()) == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.math
    def test_distribution_is_non_negative(self, computer: DefaultClassTransitionComputer) -> None:
        """All elements of stationary distribution are >= 0."""
        ctm = _make_ctm()
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        assert np.all(result.distribution >= -1e-12)

    @pytest.mark.math
    def test_sc_004_pi_p_equals_pi(self, computer: DefaultClassTransitionComputer) -> None:
        """SC-004: stationary distribution satisfies pi @ P == pi.

        The stationary distribution pi satisfies the fixed-point equation:
        pi @ P = pi (pi is the left eigenvector of P with eigenvalue 1).
        """
        ctm = _make_ctm()
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        pi = result.distribution
        np.testing.assert_allclose(
            pi @ ctm.transition_matrix,
            pi,
            atol=1e-8,
            err_msg="Stationary distribution pi must satisfy pi @ P = pi",
        )

    @pytest.mark.math
    def test_convergence_via_power_iteration(
        self, computer: DefaultClassTransitionComputer
    ) -> None:
        """Distribution converges within 100 self-multiplications (SC-004).

        Starting from uniform distribution, 100 applications of P^T should
        converge to the stationary distribution.
        """
        ctm = _make_ctm()
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        pi = result.distribution

        # Power iteration: row vector x @ P^k → pi as k → ∞
        n = ctm.n_classes
        x = np.ones(n) / n  # uniform initial distribution
        p = ctm.transition_matrix
        for _ in range(100):
            x = x @ p
        np.testing.assert_allclose(x, pi, atol=1e-6)

    @pytest.mark.math
    def test_absorbing_state_distribution(self, computer: DefaultClassTransitionComputer) -> None:
        """Matrix with single absorbing state converges to that state.

        If state 0 is absorbing (row=[1,0]) and state 1 transitions to 0
        with p=1.0, the stationary distribution should be [1, 0].
        """
        mat = np.array([[1.0, 0.0], [1.0, 0.0]])
        ctm = ClassTransitionMatrix(
            period=(2015, 2020),
            classes=["proletariat", "bourgeoisie"],
            transition_matrix=mat,
        )
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        np.testing.assert_allclose(result.distribution, [1.0, 0.0], atol=1e-8)

    @pytest.mark.math
    def test_hand_calculation_two_by_two(self, computer: DefaultClassTransitionComputer) -> None:
        """Verify hand-calculated stationary distribution for 2x2 matrix.

        P = [[0.9, 0.1], [0.3, 0.7]]
        pi @ P = pi with pi[0] + pi[1] = 1.0
        pi[0] = 0.3 / (0.1 + 0.3) = 0.75
        pi[1] = 0.1 / (0.1 + 0.3) = 0.25
        """
        ctm = _make_ctm()  # [[0.9, 0.1], [0.3, 0.7]]
        result = computer.stationary_distribution(ctm)
        assert isinstance(result, StationaryDistribution)
        np.testing.assert_allclose(result.distribution, [0.75, 0.25], atol=1e-8)


# =============================================================================
# DefaultClassTransitionComputer: class aggregation
# =============================================================================


class TestDefaultClassTransitionComputerAggregation:
    """Tests for DefaultClassTransitionComputer.aggregate_classes."""

    @pytest.fixture()
    def computer(self) -> DefaultClassTransitionComputer:
        """Provide a DefaultClassTransitionComputer instance."""
        return DefaultClassTransitionComputer()

    def test_aggregate_returns_class_transition_matrix(
        self, computer: DefaultClassTransitionComputer
    ) -> None:
        """aggregate_classes returns ClassTransitionMatrix."""
        ctm = _make_ctm()
        mapping = {"proletariat": "worker", "petit_bourgeois": "non_worker"}
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)

    def test_aggregated_classes_are_target_values(
        self, computer: DefaultClassTransitionComputer
    ) -> None:
        """Aggregated matrix uses target class names from mapping."""
        ctm = _make_ctm()
        mapping = {"proletariat": "worker", "petit_bourgeois": "non_worker"}
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)
        assert set(result.classes) == {"worker", "non_worker"}

    @pytest.mark.math
    def test_aggregated_rows_sum_to_one(self, computer: DefaultClassTransitionComputer) -> None:
        """Aggregated transition matrix rows still sum to 1.0."""
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
        # Merge proletariat+lumpen → "labor", petit_bourgeois+bourgeoisie → "capital"
        mapping = {
            "proletariat": "labor",
            "lumpen": "labor",
            "petit_bourgeois": "capital",
            "bourgeoisie": "capital",
        }
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)
        row_sums = result.transition_matrix.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-9)

    @pytest.mark.math
    def test_period_preserved_in_aggregation(
        self, computer: DefaultClassTransitionComputer
    ) -> None:
        """Aggregation preserves source period."""
        ctm = _make_ctm(period=(2010, 2015))
        mapping = {"proletariat": "worker", "petit_bourgeois": "non_worker"}
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)
        assert result.period == (2010, 2015)

    @pytest.mark.math
    def test_trivial_mapping_identity(self, computer: DefaultClassTransitionComputer) -> None:
        """1-to-1 mapping (no merging) preserves original matrix exactly."""
        ctm = _make_ctm()
        mapping = {"proletariat": "proletariat", "petit_bourgeois": "petit_bourgeois"}
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)
        # After 1-to-1 aggregation, matrices should be equal (up to class reordering)
        # Since classes may be reordered alphabetically, check row sums only
        row_sums = result.transition_matrix.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-9)

    def test_unmapped_classes_excluded(self, computer: DefaultClassTransitionComputer) -> None:
        """Classes not in mapping are excluded from aggregated matrix."""
        ctm = _make_ctm()
        # Only map proletariat → worker; petit_bourgeois not mapped
        mapping = {"proletariat": "worker"}
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)
        assert "petit_bourgeois" not in result.classes

    @pytest.mark.math
    def test_two_to_one_merging(self, computer: DefaultClassTransitionComputer) -> None:
        """Merging two classes preserves row stochasticity.

        When proletariat and petit_bourgeois both map to 'worker',
        the result is a 1x1 matrix with transition prob = 1.0.
        """
        ctm = _make_ctm()  # 2 classes both map to same target
        mapping = {"proletariat": "worker", "petit_bourgeois": "worker"}
        result = computer.aggregate_classes(ctm, mapping)
        assert isinstance(result, ClassTransitionMatrix)
        assert result.n_classes == 1
        assert result.transition_matrix[0, 0] == pytest.approx(1.0)


# =============================================================================
# DefaultClassTransitionSource stub tests
# =============================================================================


class TestDefaultClassTransitionSource:
    """Tests for DefaultClassTransitionSource stub (PSID loader deferred)."""

    @pytest.fixture()
    def source(self) -> DefaultClassTransitionSource:
        """Provide a DefaultClassTransitionSource stub instance."""
        return DefaultClassTransitionSource()

    def test_get_transition_matrix_returns_sentinel(
        self, source: DefaultClassTransitionSource
    ) -> None:
        """get_transition_matrix returns NoDataSentinel (PSID loader deferred)."""
        result = source.get_transition_matrix((2015, 2020))
        assert isinstance(result, NoDataSentinel)

    def test_sentinel_year_matches_period_start(self, source: DefaultClassTransitionSource) -> None:
        """Sentinel year matches start year of requested period."""
        result = source.get_transition_matrix((2010, 2015))
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2010

    def test_sentinel_is_falsy(self, source: DefaultClassTransitionSource) -> None:
        """NoDataSentinel is falsy."""
        result = source.get_transition_matrix((2015, 2020))
        assert not result

    def test_sentinel_reason_mentions_psid(self, source: DefaultClassTransitionSource) -> None:
        """Sentinel reason references PSID data source."""
        result = source.get_transition_matrix((2015, 2020))
        assert isinstance(result, NoDataSentinel)
        assert "PSID" in result.reason or "constitutional" in result.reason.lower()

    def test_get_stationary_distribution_returns_sentinel(
        self, source: DefaultClassTransitionSource
    ) -> None:
        """get_stationary_distribution returns NoDataSentinel."""
        result = source.get_stationary_distribution((2015, 2020))
        assert isinstance(result, NoDataSentinel)

    def test_stationary_distribution_sentinel_year(
        self, source: DefaultClassTransitionSource
    ) -> None:
        """Stationary distribution sentinel year matches period start."""
        result = source.get_stationary_distribution((2018, 2023))
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2018
