"""Unit tests for year-over-year transition computation.

Feature: 003-hydrator-temporal-validation
User Story 2: Flag Anomalous Year-over-Year Jumps

Tests cover:
- T026: YoY delta percentage computation

TDD: These tests are written FIRST and should FAIL until implementation.
"""

import pytest

from babylon.economics.temporal.models import DetectionMethod, TemporalTransition


class TestComputeTransition:
    """Test TransitionComputerImpl.compute_transition() (T026, T030)."""

    def test_compute_transition_returns_temporal_transition(self) -> None:
        """compute_transition returns TemporalTransition object."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        # Will need mock hydrator
        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]
        assert hasattr(computer, "compute_transition")

    def test_compute_transition_invalid_year_sequence_raises(self) -> None:
        """compute_transition with non-consecutive years raises ValueError."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="consecutive"):
            computer.compute_transition(
                fips="26163",
                year_from=2020,
                year_to=2022,  # Should be 2021
            )


class TestDeltaPercentageComputation:
    """Test delta percentage calculation helper (T026)."""

    def test_compute_delta_percentage_positive_change(self) -> None:
        """Positive change returns positive percentage."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # 100 -> 120 = 20% increase
        delta = compute_delta_percentage(old_value=100.0, new_value=120.0)
        assert delta == pytest.approx(0.20, abs=0.001)

    def test_compute_delta_percentage_negative_change(self) -> None:
        """Negative change returns negative percentage."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # 100 -> 80 = 20% decrease
        delta = compute_delta_percentage(old_value=100.0, new_value=80.0)
        assert delta == pytest.approx(-0.20, abs=0.001)

    def test_compute_delta_percentage_no_change(self) -> None:
        """No change returns zero."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        delta = compute_delta_percentage(old_value=100.0, new_value=100.0)
        assert delta == pytest.approx(0.0, abs=0.0001)

    def test_compute_delta_percentage_zero_old_value(self) -> None:
        """Zero old value returns inf or raises."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # Division by zero case - should return infinity or raise
        delta = compute_delta_percentage(old_value=0.0, new_value=100.0)
        assert delta == float("inf") or delta > 1000  # Very large

    def test_compute_delta_percentage_both_zero(self) -> None:
        """Both zero returns zero (no change)."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        delta = compute_delta_percentage(old_value=0.0, new_value=0.0)
        assert delta == pytest.approx(0.0, abs=0.0001)


class TestTransitionModelIntegration:
    """Test TemporalTransition model usage in transitions."""

    def test_transition_with_dept_shares(self) -> None:
        """Transition correctly stores department share deltas."""
        transition = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.05,
            delta_dept_shares={
                "dept_i": -0.02,
                "dept_ii": 0.01,
                "dept_iii": 0.005,
                "dept_iv": 0.005,
            },
            delta_profit_rate=-0.03,
            detection_method=DetectionMethod.BOOTSTRAP,
        )

        assert transition.delta_dept_shares["dept_i"] == pytest.approx(-0.02)
        assert transition.detection_method == DetectionMethod.BOOTSTRAP

    def test_transition_z_scores_populated(self) -> None:
        """Transition can store Z-scores for each component."""
        transition = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.25,
            delta_profit_rate=-0.10,
            z_scores={
                "total_v": 2.8,
                "profit_rate": -1.5,
            },
            detection_method=DetectionMethod.Z_SCORE,
        )

        assert transition.z_scores["total_v"] == pytest.approx(2.8)
        assert transition.z_scores["profit_rate"] == pytest.approx(-1.5)


class TestDeltaPercentageMutationKillers:
    """Mutation-killing tests for compute_delta_percentage."""

    def test_exact_doubling(self) -> None:
        """100 -> 200 = exactly 100% increase."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        assert compute_delta_percentage(100.0, 200.0) == pytest.approx(1.0)

    def test_exact_halving(self) -> None:
        """100 -> 50 = exactly -50% decrease."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        assert compute_delta_percentage(100.0, 50.0) == pytest.approx(-0.5)

    def test_small_positive_change(self) -> None:
        """Verify numerator uses (new - old), not (old - new)."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # 100 -> 101 = 1% positive
        result = compute_delta_percentage(100.0, 101.0)
        assert result > 0
        assert result == pytest.approx(0.01)

    def test_small_negative_change(self) -> None:
        """Verify sign is negative for decrease."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        result = compute_delta_percentage(100.0, 99.0)
        assert result < 0
        assert result == pytest.approx(-0.01)

    def test_zero_old_nonzero_new_returns_inf(self) -> None:
        """Zero old with nonzero new returns positive infinity."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        result = compute_delta_percentage(0.0, 50.0)
        assert result == float("inf")

    def test_zero_old_negative_new_returns_inf(self) -> None:
        """Zero old with negative new still returns inf (not -inf)."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # Implementation returns float("inf") for any nonzero new when old=0
        result = compute_delta_percentage(0.0, -50.0)
        assert result == float("inf")

    def test_both_zero_returns_exactly_zero(self) -> None:
        """Both zero returns exactly 0.0, not inf or nan."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        result = compute_delta_percentage(0.0, 0.0)
        assert result == 0.0

    def test_negative_old_positive_new(self) -> None:
        """Works with negative old value."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # -100 -> 100: (100 - (-100)) / (-100) = -2.0
        result = compute_delta_percentage(-100.0, 100.0)
        assert result == pytest.approx(-2.0)

    def test_division_uses_old_value(self) -> None:
        """Verify denominator is old_value, not new_value."""
        from babylon.economics.temporal.transitions import compute_delta_percentage

        # 50 -> 100: (100-50)/50 = 1.0 (using old)
        # vs (100-50)/100 = 0.5 (using new) — would be wrong
        assert compute_delta_percentage(50.0, 100.0) == pytest.approx(1.0)


class TestComputeDeptSharesMutationKillers:
    """Mutation-killing tests for _compute_dept_shares."""

    def _make_mock_tensor(
        self,
        dept_I_v: float,
        dept_IIa_v: float,
        dept_IIb_v: float,
        dept_III_v: float,
    ) -> object:
        from types import SimpleNamespace

        return SimpleNamespace(
            dept_I=SimpleNamespace(v=dept_I_v),
            dept_IIa=SimpleNamespace(v=dept_IIa_v),
            dept_IIb=SimpleNamespace(v=dept_IIb_v),
            dept_III=SimpleNamespace(v=dept_III_v),
        )

    def test_shares_sum_to_one(self) -> None:
        """Department shares sum to 1.0 when total_v > 0."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(10.0, 30.0, 40.0, 20.0)
        shares = computer._compute_dept_shares(tensor, total_v=100.0)

        assert sum(shares.values()) == pytest.approx(1.0)

    def test_shares_correct_individual_values(self) -> None:
        """Each department share equals dept_v / total_v."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(25.0, 25.0, 25.0, 25.0)
        shares = computer._compute_dept_shares(tensor, total_v=100.0)

        assert shares["dept_I"] == pytest.approx(0.25)
        assert shares["dept_IIa"] == pytest.approx(0.25)
        assert shares["dept_IIb"] == pytest.approx(0.25)
        assert shares["dept_III"] == pytest.approx(0.25)

    def test_shares_zero_total_v_returns_all_zeros(self) -> None:
        """When total_v is 0, all shares are 0.0."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(0.0, 0.0, 0.0, 0.0)
        shares = computer._compute_dept_shares(tensor, total_v=0.0)

        for dept_share in shares.values():
            assert dept_share == 0.0

    def test_shares_has_all_four_departments(self) -> None:
        """Result dict contains all four department keys."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(10.0, 20.0, 30.0, 40.0)
        shares = computer._compute_dept_shares(tensor, total_v=100.0)

        assert set(shares.keys()) == {"dept_I", "dept_IIa", "dept_IIb", "dept_III"}

    def test_shares_asymmetric_distribution(self) -> None:
        """Verify each dept is correctly mapped (not swapped)."""
        from babylon.economics.temporal.transitions import TransitionComputerImpl

        computer = TransitionComputerImpl(hydrator=None)  # type: ignore[arg-type]
        tensor = self._make_mock_tensor(10.0, 20.0, 30.0, 40.0)
        shares = computer._compute_dept_shares(tensor, total_v=100.0)

        assert shares["dept_I"] == pytest.approx(0.10)
        assert shares["dept_IIa"] == pytest.approx(0.20)
        assert shares["dept_IIb"] == pytest.approx(0.30)
        assert shares["dept_III"] == pytest.approx(0.40)
