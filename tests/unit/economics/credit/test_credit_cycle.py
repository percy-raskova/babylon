"""Tests for credit cycle phase detection (directed state machine).

Feature: 024-capital-volume-iii (US2, FR-006)
TDD Red Phase: Tests define expected credit cycle state machine transitions.

Main cycle: EXPANSION -> OVEREXTENSION -> CRISIS -> RECOVERY -> EXPANSION
Shortcuts: OVEREXTENSION -> STAGNATION, RECOVERY -> STAGNATION
STAGNATION is terminal (no exits).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.credit.credit_cycle import DefaultCreditCycleDetector
from babylon.domain.economics.credit.types import (
    OVEREXTENSION_DEFAULT_RATE,
    RECOVERY_CONSECUTIVE_PERIODS,
    STAGNATION_CREDIT_GROWTH,
    CreditCyclePhase,
)


@pytest.fixture
def detector() -> DefaultCreditCycleDetector:
    """Provide a fresh detector instance."""
    return DefaultCreditCycleDetector()


# =============================================================================
# Valid transitions
# =============================================================================


@pytest.mark.unit
class TestExpansionTransitions:
    """EXPANSION -> OVEREXTENSION when credit grows but profit falls."""

    def test_expansion_to_overextension(self, detector: DefaultCreditCycleDetector) -> None:
        """Positive credit growth + negative profit trend -> OVEREXTENSION."""
        new_phase, count = detector.evaluate(
            profit_rate=0.05,
            profit_rate_trend=-0.01,  # Falling profits
            credit_growth=0.05,  # Positive credit growth
            default_rate=0.01,
            current_phase=CreditCyclePhase.EXPANSION,
        )
        assert new_phase == CreditCyclePhase.OVEREXTENSION
        assert count == 0

    def test_expansion_stays_when_profits_rising(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Positive credit growth + positive profit trend -> stay EXPANSION."""
        new_phase, count = detector.evaluate(
            profit_rate=0.05,
            profit_rate_trend=0.01,  # Rising profits
            credit_growth=0.05,
            default_rate=0.01,
            current_phase=CreditCyclePhase.EXPANSION,
        )
        assert new_phase == CreditCyclePhase.EXPANSION

    def test_expansion_stays_when_credit_contracting(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Negative credit growth doesn't trigger overextension from expansion."""
        new_phase, count = detector.evaluate(
            profit_rate=0.05,
            profit_rate_trend=-0.01,
            credit_growth=-0.02,  # Contracting credit
            default_rate=0.01,
            current_phase=CreditCyclePhase.EXPANSION,
        )
        assert new_phase == CreditCyclePhase.EXPANSION


@pytest.mark.unit
class TestOverextensionTransitions:
    """OVEREXTENSION -> CRISIS or STAGNATION."""

    def test_overextension_to_crisis(self, detector: DefaultCreditCycleDetector) -> None:
        """Default rate exceeds threshold -> CRISIS."""
        new_phase, count = detector.evaluate(
            profit_rate=0.02,
            profit_rate_trend=-0.02,
            credit_growth=0.03,
            default_rate=OVEREXTENSION_DEFAULT_RATE + 0.01,  # Above threshold
            current_phase=CreditCyclePhase.OVEREXTENSION,
        )
        assert new_phase == CreditCyclePhase.CRISIS
        assert count == 0

    def test_overextension_to_stagnation(self, detector: DefaultCreditCycleDetector) -> None:
        """Near-zero credit growth + low default rate -> STAGNATION."""
        new_phase, count = detector.evaluate(
            profit_rate=0.02,
            profit_rate_trend=-0.005,
            credit_growth=STAGNATION_CREDIT_GROWTH / 2,  # Below threshold
            default_rate=OVEREXTENSION_DEFAULT_RATE / 2,  # Below crisis threshold
            current_phase=CreditCyclePhase.OVEREXTENSION,
        )
        assert new_phase == CreditCyclePhase.STAGNATION

    def test_overextension_stays_when_neither(self, detector: DefaultCreditCycleDetector) -> None:
        """Moderate credit growth, moderate defaults -> stay OVEREXTENSION."""
        new_phase, count = detector.evaluate(
            profit_rate=0.03,
            profit_rate_trend=-0.01,
            credit_growth=0.05,  # Above stagnation threshold
            default_rate=OVEREXTENSION_DEFAULT_RATE / 2,  # Below crisis threshold
            current_phase=CreditCyclePhase.OVEREXTENSION,
        )
        assert new_phase == CreditCyclePhase.OVEREXTENSION


@pytest.mark.unit
class TestCrisisTransitions:
    """CRISIS -> RECOVERY after consecutive periods of profit improvement."""

    def test_crisis_to_recovery_after_consecutive_periods(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Profit rate trending positive for RECOVERY_CONSECUTIVE_PERIODS -> RECOVERY."""
        phase = CreditCyclePhase.CRISIS
        count = 0

        # Simulate consecutive periods of positive profit trend
        for _i in range(RECOVERY_CONSECUTIVE_PERIODS):
            phase, count = detector.evaluate(
                profit_rate=0.03,
                profit_rate_trend=0.01,  # Positive trend
                credit_growth=-0.02,
                default_rate=0.05,
                current_phase=phase,
                consecutive_recovery=count,
            )

        assert phase == CreditCyclePhase.RECOVERY

    def test_crisis_stays_when_profit_trend_negative(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Negative profit trend resets recovery counter, stays CRISIS."""
        new_phase, count = detector.evaluate(
            profit_rate=0.01,
            profit_rate_trend=-0.02,  # Falling profits
            credit_growth=-0.05,
            default_rate=0.06,
            current_phase=CreditCyclePhase.CRISIS,
            consecutive_recovery=1,
        )
        assert new_phase == CreditCyclePhase.CRISIS
        assert count == 0  # Reset

    def test_crisis_increments_counter_but_stays_when_insufficient(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """One period of positive trend increments counter but stays CRISIS."""
        new_phase, count = detector.evaluate(
            profit_rate=0.03,
            profit_rate_trend=0.01,  # Positive
            credit_growth=-0.02,
            default_rate=0.04,
            current_phase=CreditCyclePhase.CRISIS,
            consecutive_recovery=0,
        )
        assert new_phase == CreditCyclePhase.CRISIS
        assert count == 1  # Incremented


@pytest.mark.unit
class TestRecoveryTransitions:
    """RECOVERY -> EXPANSION or STAGNATION."""

    def test_recovery_to_expansion(self, detector: DefaultCreditCycleDetector) -> None:
        """Credit growth resumes above stagnation threshold -> EXPANSION."""
        new_phase, count = detector.evaluate(
            profit_rate=0.04,
            profit_rate_trend=0.01,
            credit_growth=STAGNATION_CREDIT_GROWTH + 0.01,  # Above threshold
            default_rate=0.01,
            current_phase=CreditCyclePhase.RECOVERY,
        )
        assert new_phase == CreditCyclePhase.EXPANSION

    def test_recovery_to_stagnation(self, detector: DefaultCreditCycleDetector) -> None:
        """Credit growth stalls near zero -> STAGNATION."""
        new_phase, count = detector.evaluate(
            profit_rate=0.03,
            profit_rate_trend=0.005,
            credit_growth=STAGNATION_CREDIT_GROWTH / 2,  # Below threshold
            default_rate=0.01,
            current_phase=CreditCyclePhase.RECOVERY,
        )
        assert new_phase == CreditCyclePhase.STAGNATION

    def test_recovery_stays_with_negative_credit_growth(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Negative credit growth (but not near zero) -> stay RECOVERY."""
        new_phase, count = detector.evaluate(
            profit_rate=0.03,
            profit_rate_trend=0.005,
            credit_growth=-0.03,  # Negative but not near zero
            default_rate=0.01,
            current_phase=CreditCyclePhase.RECOVERY,
        )
        assert new_phase == CreditCyclePhase.RECOVERY


# =============================================================================
# Invalid transitions and terminal state
# =============================================================================


@pytest.mark.unit
class TestStagnationTerminal:
    """STAGNATION is terminal: no exits regardless of input."""

    def test_stagnation_stays_stagnation_with_growth(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Even with positive indicators, STAGNATION remains terminal."""
        new_phase, count = detector.evaluate(
            profit_rate=0.10,
            profit_rate_trend=0.05,
            credit_growth=0.10,
            default_rate=0.001,
            current_phase=CreditCyclePhase.STAGNATION,
        )
        assert new_phase == CreditCyclePhase.STAGNATION

    def test_stagnation_stays_stagnation_with_crisis_conditions(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """Even with crisis-level defaults, STAGNATION remains terminal."""
        new_phase, count = detector.evaluate(
            profit_rate=-0.05,
            profit_rate_trend=-0.10,
            credit_growth=-0.20,
            default_rate=0.15,
            current_phase=CreditCyclePhase.STAGNATION,
        )
        assert new_phase == CreditCyclePhase.STAGNATION

    def test_stagnation_returns_zero_count(self, detector: DefaultCreditCycleDetector) -> None:
        """STAGNATION always returns 0 for consecutive recovery count."""
        _, count = detector.evaluate(
            profit_rate=0.05,
            profit_rate_trend=0.02,
            credit_growth=0.05,
            default_rate=0.01,
            current_phase=CreditCyclePhase.STAGNATION,
            consecutive_recovery=5,
        )
        assert count == 0


@pytest.mark.unit
class TestInvalidTransitions:
    """Transitions not in VALID_CREDIT_TRANSITIONS are impossible.

    The state machine only allows transitions via evaluate() conditions.
    EXPANSION cannot skip to CRISIS directly.
    """

    def test_expansion_cannot_jump_to_crisis(self, detector: DefaultCreditCycleDetector) -> None:
        """EXPANSION with high defaults still goes EXPANSION (not CRISIS)."""
        new_phase, _ = detector.evaluate(
            profit_rate=0.01,
            profit_rate_trend=-0.05,
            credit_growth=-0.10,  # Negative credit growth prevents OVEREXTENSION
            default_rate=0.20,  # Very high defaults
            current_phase=CreditCyclePhase.EXPANSION,
        )
        # Cannot skip to CRISIS; must pass through OVEREXTENSION
        assert new_phase == CreditCyclePhase.EXPANSION

    def test_phase_unchanged_when_no_conditions_met(
        self, detector: DefaultCreditCycleDetector
    ) -> None:
        """When no transition conditions are met, phase stays the same."""
        new_phase, _ = detector.evaluate(
            profit_rate=0.05,
            profit_rate_trend=0.0,  # Flat
            credit_growth=0.02,
            default_rate=0.01,
            current_phase=CreditCyclePhase.EXPANSION,
        )
        assert new_phase == CreditCyclePhase.EXPANSION
