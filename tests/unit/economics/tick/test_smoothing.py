"""Tests for CoefficientSmoother.

Feature: 017-simulation-tick-dynamics
Task: T022
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.smoothing import CoefficientSmoother


class TestCoefficientSmoother:
    """Tests for CoefficientSmoother alpha-smoothing."""

    def test_default_alpha(self) -> None:
        """Verify default alpha is 0.3."""
        smoother = CoefficientSmoother()
        assert smoother.alpha == 0.3

    def test_custom_alpha(self) -> None:
        """Verify custom alpha is respected."""
        smoother = CoefficientSmoother(alpha=0.5)
        assert smoother.alpha == 0.5

    def test_alpha_validation_lower_bound(self) -> None:
        """Verify alpha must be > 0."""
        with pytest.raises(ValueError, match="alpha"):
            CoefficientSmoother(alpha=0.0)

    def test_alpha_validation_upper_bound(self) -> None:
        """Verify alpha must be <= 1."""
        with pytest.raises(ValueError, match="alpha"):
            CoefficientSmoother(alpha=1.1)

    def test_alpha_one_is_valid(self) -> None:
        """Verify alpha=1.0 is valid (no smoothing)."""
        smoother = CoefficientSmoother(alpha=1.0)
        assert smoother.alpha == 1.0

    def test_first_tick_passthrough(self) -> None:
        """Verify first tick returns raw value (no smoothing applied)."""
        smoother = CoefficientSmoother(alpha=0.3)
        result = smoother.smooth(raw=0.72, previous=0.68, is_initialized=False)
        assert result == 0.72

    def test_smoothing_formula(self) -> None:
        """Verify smoothing: value = previous + alpha * (raw - previous)."""
        smoother = CoefficientSmoother(alpha=0.3)
        # previous=0.68, raw=0.72, alpha=0.3
        # expected = 0.68 + 0.3 * (0.72 - 0.68) = 0.68 + 0.012 = 0.692
        result = smoother.smooth(raw=0.72, previous=0.68, is_initialized=True)
        assert abs(result - 0.692) < 0.0001

    def test_alpha_one_means_no_smoothing(self) -> None:
        """Verify alpha=1.0 means result equals raw."""
        smoother = CoefficientSmoother(alpha=1.0)
        result = smoother.smooth(raw=0.72, previous=0.68, is_initialized=True)
        assert abs(result - 0.72) < 0.0001

    def test_convergence(self) -> None:
        """Verify repeated smoothing converges toward raw value."""
        smoother = CoefficientSmoother(alpha=0.3)
        value = 0.50
        target = 0.80
        max_iterations = 100
        for _ in range(max_iterations):
            value = smoother.smooth(raw=target, previous=value, is_initialized=True)
        assert abs(value - target) < 0.001

    def test_decreasing_raw_converges_downward(self) -> None:
        """Verify smoothing converges downward when raw < previous."""
        smoother = CoefficientSmoother(alpha=0.3)
        # previous=0.80, raw=0.60
        result = smoother.smooth(raw=0.60, previous=0.80, is_initialized=True)
        # expected = 0.80 + 0.3 * (0.60 - 0.80) = 0.80 - 0.06 = 0.74
        assert abs(result - 0.74) < 0.0001

    def test_equal_raw_and_previous(self) -> None:
        """Verify no change when raw equals previous."""
        smoother = CoefficientSmoother(alpha=0.3)
        result = smoother.smooth(raw=0.68, previous=0.68, is_initialized=True)
        assert abs(result - 0.68) < 0.0001

    def test_small_alpha_slow_convergence(self) -> None:
        """Verify small alpha means slow convergence."""
        slow = CoefficientSmoother(alpha=0.1)
        fast = CoefficientSmoother(alpha=0.9)

        slow_result = slow.smooth(raw=1.0, previous=0.0, is_initialized=True)
        fast_result = fast.smooth(raw=1.0, previous=0.0, is_initialized=True)

        # Slow should be closer to previous (0.0)
        assert slow_result < fast_result
        assert abs(slow_result - 0.1) < 0.0001
        assert abs(fast_result - 0.9) < 0.0001
