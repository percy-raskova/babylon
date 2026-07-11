"""Credit cycle phase detection via directed state machine.

Models the credit cycle as a 5-phase state machine with directed transitions.
The main cycle follows: EXPANSION -> OVEREXTENSION -> CRISIS -> RECOVERY -> EXPANSION.
Shortcut paths lead to STAGNATION, which is terminal.

Feature: 024-capital-volume-iii (US2, FR-006)

See Also:
    :class:`CreditCyclePhase`: The 5-phase StrEnum.
    :data:`VALID_CREDIT_TRANSITIONS`: Allowed phase transitions.
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.credit.types import (
    OVEREXTENSION_DEFAULT_RATE,
    RECOVERY_CONSECUTIVE_PERIODS,
    STAGNATION_CREDIT_GROWTH,
    CreditCyclePhase,
)


class CreditCycleDetector(Protocol):
    """Protocol for credit cycle phase evaluation."""

    def evaluate(
        self,
        profit_rate: float,
        profit_rate_trend: float,
        credit_growth: float,
        default_rate: float,
        current_phase: CreditCyclePhase,
        consecutive_recovery: int = 0,
    ) -> tuple[CreditCyclePhase, int]:
        """Evaluate whether a phase transition should occur.

        Args:
            profit_rate: Current profit rate (r = s/C).
            profit_rate_trend: Change in profit rate from prior period.
            credit_growth: YoY credit expansion rate.
            default_rate: Loan default fraction.
            current_phase: Current credit cycle phase.
            consecutive_recovery: Periods of positive profit trend in CRISIS.

        Returns:
            Tuple of (new_phase, updated_consecutive_recovery_count).
        """
        ...


class DefaultCreditCycleDetector:
    """Directed state machine for credit cycle phase transitions.

    Main cycle: EXPANSION -> OVEREXTENSION -> CRISIS -> RECOVERY -> EXPANSION
    Shortcuts: OVEREXTENSION -> STAGNATION, RECOVERY -> STAGNATION
    STAGNATION is terminal (no exits).

    Transition conditions:

    - EXPANSION -> OVEREXTENSION: credit_growth > 0 AND profit_rate_trend < 0
    - OVEREXTENSION -> CRISIS: default_rate > OVEREXTENSION_DEFAULT_RATE
    - OVEREXTENSION -> STAGNATION: abs(credit_growth) < STAGNATION_CREDIT_GROWTH
    - CRISIS -> RECOVERY: profit_rate_trend > 0 for RECOVERY_CONSECUTIVE_PERIODS
    - RECOVERY -> EXPANSION: credit_growth > STAGNATION_CREDIT_GROWTH
    - RECOVERY -> STAGNATION: abs(credit_growth) < STAGNATION_CREDIT_GROWTH
    """

    def evaluate(
        self,
        profit_rate: float,  # noqa: ARG002 - Protocol requires; future phases may use
        profit_rate_trend: float,
        credit_growth: float,
        default_rate: float,
        current_phase: CreditCyclePhase,
        consecutive_recovery: int = 0,
    ) -> tuple[CreditCyclePhase, int]:
        """Evaluate credit cycle phase transition.

        Args:
            profit_rate: Current profit rate (r = s/C).
            profit_rate_trend: Change in profit rate from prior period.
            credit_growth: YoY credit expansion rate.
            default_rate: Loan default fraction.
            current_phase: Current credit cycle phase.
            consecutive_recovery: Periods of positive profit trend in CRISIS.

        Returns:
            Tuple of (new_phase, updated_consecutive_recovery_count).
        """
        # Terminal state: STAGNATION has no exits
        if current_phase == CreditCyclePhase.STAGNATION:
            return (CreditCyclePhase.STAGNATION, 0)

        if current_phase == CreditCyclePhase.EXPANSION:
            return self._evaluate_expansion(credit_growth, profit_rate_trend)

        if current_phase == CreditCyclePhase.OVEREXTENSION:
            return self._evaluate_overextension(credit_growth, default_rate)

        if current_phase == CreditCyclePhase.CRISIS:
            return self._evaluate_crisis(profit_rate_trend, consecutive_recovery)

        if current_phase == CreditCyclePhase.RECOVERY:
            return self._evaluate_recovery(credit_growth)

        # Unreachable: all 5 phases covered above
        return (current_phase, consecutive_recovery)

    def _evaluate_expansion(
        self, credit_growth: float, profit_rate_trend: float
    ) -> tuple[CreditCyclePhase, int]:
        """EXPANSION -> OVEREXTENSION when credit grows but profit falls."""
        if credit_growth > 0 and profit_rate_trend < 0:
            return (CreditCyclePhase.OVEREXTENSION, 0)
        return (CreditCyclePhase.EXPANSION, 0)

    def _evaluate_overextension(
        self, credit_growth: float, default_rate: float
    ) -> tuple[CreditCyclePhase, int]:
        """OVEREXTENSION -> CRISIS (high defaults) or STAGNATION (low growth)."""
        if default_rate > OVEREXTENSION_DEFAULT_RATE:
            return (CreditCyclePhase.CRISIS, 0)
        if abs(credit_growth) < STAGNATION_CREDIT_GROWTH:
            return (CreditCyclePhase.STAGNATION, 0)
        return (CreditCyclePhase.OVEREXTENSION, 0)

    def _evaluate_crisis(
        self, profit_rate_trend: float, consecutive_recovery: int
    ) -> tuple[CreditCyclePhase, int]:
        """CRISIS -> RECOVERY after consecutive periods of profit improvement."""
        if profit_rate_trend > 0:
            new_count = consecutive_recovery + 1
            if new_count >= RECOVERY_CONSECUTIVE_PERIODS:
                return (CreditCyclePhase.RECOVERY, 0)
            return (CreditCyclePhase.CRISIS, new_count)
        return (CreditCyclePhase.CRISIS, 0)

    def _evaluate_recovery(self, credit_growth: float) -> tuple[CreditCyclePhase, int]:
        """RECOVERY -> EXPANSION (credit resumes) or STAGNATION (stalls)."""
        if credit_growth > STAGNATION_CREDIT_GROWTH:
            return (CreditCyclePhase.EXPANSION, 0)
        if abs(credit_growth) < STAGNATION_CREDIT_GROWTH:
            return (CreditCyclePhase.STAGNATION, 0)
        return (CreditCyclePhase.RECOVERY, 0)
