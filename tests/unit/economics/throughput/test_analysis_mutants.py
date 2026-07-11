"""Mutation-killing tests for CorrelationResult properties.

Tests for is_significant and meets_threshold — the only untested
algorithmic paths in analysis.py (correlation functions are pragma'd).
"""

from __future__ import annotations

from babylon.domain.economics.throughput.analysis import CorrelationResult


class TestCorrelationResultMutationKillers:
    """Mutation-killing tests for CorrelationResult properties."""

    def test_is_significant_below_threshold(self) -> None:
        """p_value < 0.05 is significant."""
        result = CorrelationResult(
            correlation=0.5,
            p_value=0.01,
            sample_size=50,
            counties_analyzed=[],
            counties_excluded=[],
        )
        assert result.is_significant is True

    def test_is_significant_above_threshold(self) -> None:
        """p_value > 0.05 is NOT significant."""
        result = CorrelationResult(
            correlation=0.5,
            p_value=0.10,
            sample_size=50,
            counties_analyzed=[],
            counties_excluded=[],
        )
        assert result.is_significant is False

    def test_is_significant_at_boundary(self) -> None:
        """p_value exactly at 0.05 is NOT significant (uses <, not <=)."""
        result = CorrelationResult(
            correlation=0.5,
            p_value=0.05,
            sample_size=50,
            counties_analyzed=[],
            counties_excluded=[],
        )
        assert result.is_significant is False

    def test_meets_threshold_above(self) -> None:
        """correlation > 0.4 meets threshold."""
        result = CorrelationResult(
            correlation=0.5,
            p_value=0.01,
            sample_size=50,
            counties_analyzed=[],
            counties_excluded=[],
        )
        assert result.meets_threshold is True

    def test_meets_threshold_below(self) -> None:
        """correlation < 0.4 does NOT meet threshold."""
        result = CorrelationResult(
            correlation=0.3,
            p_value=0.01,
            sample_size=50,
            counties_analyzed=[],
            counties_excluded=[],
        )
        assert result.meets_threshold is False

    def test_meets_threshold_at_boundary(self) -> None:
        """correlation exactly 0.4 does NOT meet threshold (uses >, not >=)."""
        result = CorrelationResult(
            correlation=0.4,
            p_value=0.01,
            sample_size=50,
            counties_analyzed=[],
            counties_excluded=[],
        )
        assert result.meets_threshold is False
