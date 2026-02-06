"""Tests for crisis detectors.

Feature: 017-simulation-tick-dynamics (ThresholdCrisisDetector)
Feature: 018-crisis-devaluation-mechanics (MultiPeriodCrisisDetector)
Tasks: T014, T033
"""

from __future__ import annotations

from babylon.economics.tick.crisis_detector import (
    MultiPeriodCrisisDetector,
    ThresholdCrisisDetector,
)
from babylon.economics.tick.types import CrisisPhase, CrisisState


class TestThresholdCrisisDetector:
    """Tests for ThresholdCrisisDetector crisis detection."""

    def test_normal_conditions_no_crisis(self) -> None:
        """Verify no crisis under normal economic conditions."""
        detector = ThresholdCrisisDetector()
        assert (
            detector.is_crisis(
                unemployment_rate=0.05,
                current_profit_rate=0.15,
                previous_profit_rate=0.16,
            )
            is False
        )

    def test_high_unemployment_triggers_crisis(self) -> None:
        """Verify crisis when unemployment exceeds threshold (default 0.08)."""
        detector = ThresholdCrisisDetector()
        assert (
            detector.is_crisis(
                unemployment_rate=0.09,
                current_profit_rate=0.15,
                previous_profit_rate=0.15,
            )
            is True
        )

    def test_unemployment_at_threshold_no_crisis(self) -> None:
        """Verify unemployment exactly at threshold is not a crisis."""
        detector = ThresholdCrisisDetector()
        assert (
            detector.is_crisis(
                unemployment_rate=0.08,
                current_profit_rate=0.15,
                previous_profit_rate=0.15,
            )
            is False
        )

    def test_profit_rate_decline_triggers_crisis(self) -> None:
        """Verify crisis when profit rate declines more than threshold (default 0.15)."""
        detector = ThresholdCrisisDetector()
        # previous=0.20, current=0.16 -> decline = (0.20-0.16)/0.20 = 0.20 > 0.15
        assert (
            detector.is_crisis(
                unemployment_rate=0.05,
                current_profit_rate=0.16,
                previous_profit_rate=0.20,
            )
            is True
        )

    def test_profit_rate_decline_below_threshold_no_crisis(self) -> None:
        """Verify profit rate decline below threshold is not crisis."""
        detector = ThresholdCrisisDetector()
        # previous=1.0, current=0.86 -> decline = 0.14/1.0 = 0.14 < 0.15
        assert (
            detector.is_crisis(
                unemployment_rate=0.05,
                current_profit_rate=0.86,
                previous_profit_rate=1.0,
            )
            is False
        )

    def test_zero_previous_profit_rate_no_crash(self) -> None:
        """Verify no crash when previous_profit_rate is zero (division by zero)."""
        detector = ThresholdCrisisDetector()
        # Zero previous profit rate -> can't compute decline fraction -> no crisis from profit
        result = detector.is_crisis(
            unemployment_rate=0.05,
            current_profit_rate=0.10,
            previous_profit_rate=0.0,
        )
        assert result is False

    def test_none_profit_rates_handled(self) -> None:
        """Verify None profit rates are handled gracefully."""
        detector = ThresholdCrisisDetector()
        # No profit rate data -> only unemployment matters
        assert (
            detector.is_crisis(
                unemployment_rate=0.05,
                current_profit_rate=None,
                previous_profit_rate=None,
            )
            is False
        )

        assert (
            detector.is_crisis(
                unemployment_rate=0.09,
                current_profit_rate=None,
                previous_profit_rate=None,
            )
            is True
        )

    def test_custom_unemployment_threshold(self) -> None:
        """Verify custom unemployment threshold is respected."""
        detector = ThresholdCrisisDetector(unemployment_threshold=0.10)
        # 0.09 < 0.10 -> no crisis
        assert (
            detector.is_crisis(
                unemployment_rate=0.09,
                current_profit_rate=0.15,
                previous_profit_rate=0.15,
            )
            is False
        )

        # 0.11 > 0.10 -> crisis
        assert (
            detector.is_crisis(
                unemployment_rate=0.11,
                current_profit_rate=0.15,
                previous_profit_rate=0.15,
            )
            is True
        )

    def test_custom_profit_decline_threshold(self) -> None:
        """Verify custom profit rate decline threshold is respected."""
        detector = ThresholdCrisisDetector(profit_decline_threshold=0.10)
        # previous=0.20, current=0.17 -> decline = 0.15 > 0.10 -> crisis
        assert (
            detector.is_crisis(
                unemployment_rate=0.05,
                current_profit_rate=0.17,
                previous_profit_rate=0.20,
            )
            is True
        )

    def test_both_conditions_met(self) -> None:
        """Verify crisis when both conditions are met."""
        detector = ThresholdCrisisDetector()
        assert (
            detector.is_crisis(
                unemployment_rate=0.12,
                current_profit_rate=0.05,
                previous_profit_rate=0.20,
            )
            is True
        )


class TestMultiPeriodCrisisDetectorBasic:
    """Basic tests for MultiPeriodCrisisDetector interface (T033).

    Detailed lifecycle tests are in test_multi_period_detector.py.
    This class verifies the public API and constructor defaults.
    """

    def test_default_constructor(self) -> None:
        """Verify default constructor uses CrisisDefines defaults."""
        detector = MultiPeriodCrisisDetector()
        state = CrisisState.normal()

        # Should not crash with None profit rate
        result = detector.evaluate(None, state)
        assert result.phase == CrisisPhase.NORMAL

    def test_evaluate_returns_crisis_state(self) -> None:
        """Verify evaluate returns CrisisState."""
        detector = MultiPeriodCrisisDetector(r_threshold=0.10)
        state = CrisisState.normal()

        result = detector.evaluate(0.05, state)
        assert isinstance(result, CrisisState)

    def test_configurable_parameters(self) -> None:
        """Verify constructor accepts all CrisisDefines parameters."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.08,
            n_consecutive=5,
            m_recovery=3,
            r_cap=10,
        )
        state = CrisisState.normal()

        # 4 below threshold should not trigger (need 5)
        for _ in range(4):
            state = detector.evaluate(0.05, state)
        assert state.phase == CrisisPhase.NORMAL

        # 5th triggers
        state = detector.evaluate(0.05, state)
        assert state.phase == CrisisPhase.ONSET

    def test_exports_from_module(self) -> None:
        """Verify both detectors are exported from crisis_detector module."""
        from babylon.economics.tick import crisis_detector

        assert hasattr(crisis_detector, "ThresholdCrisisDetector")
        assert hasattr(crisis_detector, "MultiPeriodCrisisDetector")
