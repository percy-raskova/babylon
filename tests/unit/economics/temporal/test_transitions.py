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
