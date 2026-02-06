"""Crisis detection for the tick dynamics pipeline.

Feature: 017-simulation-tick-dynamics (ThresholdCrisisDetector)
Feature: 018-crisis-devaluation-mechanics (MultiPeriodCrisisDetector)

ThresholdCrisisDetector: Legacy single-period detector (Feature 017).
MultiPeriodCrisisDetector: Multi-period lifecycle detector (Feature 018).

See Also:
    :mod:`babylon.economics.tick.system`: Pipeline orchestration
    :mod:`babylon.economics.tick.types`: CrisisState, CrisisPhase
"""

from __future__ import annotations

from babylon.economics.tick.types import CrisisPhase, CrisisState

# Number of EARLY periods before transitioning to DEEP.
# ONSET = 1 period, EARLY = 4 periods, so DEEP starts at crisis_duration > 5.
_EARLY_DURATION = 4


class ThresholdCrisisDetector:
    """Detect economic crisis via threshold comparison (legacy).

    Args:
        unemployment_threshold: Unemployment rate above which crisis is
            triggered. Default 0.08 (8%).
        profit_decline_threshold: Fractional decline in profit rate above
            which crisis is triggered. Default 0.15 (15%).

    Example:
        >>> detector = ThresholdCrisisDetector()
        >>> detector.is_crisis(0.09, 0.10, 0.15)
        True
    """

    def __init__(
        self,
        unemployment_threshold: float = 0.08,
        profit_decline_threshold: float = 0.15,
    ) -> None:
        self.unemployment_threshold = unemployment_threshold
        self.profit_decline_threshold = profit_decline_threshold

    def is_crisis(
        self,
        unemployment_rate: float,
        current_profit_rate: float | None,
        previous_profit_rate: float | None,
    ) -> bool:
        """Determine if economic conditions indicate crisis.

        Args:
            unemployment_rate: Current county unemployment rate.
            current_profit_rate: Current profit rate (None if unavailable).
            previous_profit_rate: Previous profit rate (None if unavailable).

        Returns:
            True if any crisis threshold is exceeded.
        """
        if unemployment_rate > self.unemployment_threshold:
            return True

        if (
            current_profit_rate is not None
            and previous_profit_rate is not None
            and previous_profit_rate > 0
        ):
            decline = (previous_profit_rate - current_profit_rate) / previous_profit_rate
            if decline > self.profit_decline_threshold:
                return True

        return False


class MultiPeriodCrisisDetector:
    """Multi-period crisis detector with 5-phase lifecycle management.

    Tracks the tendency of the rate of profit to fall across consecutive
    crisis periods, managing phase transitions through the full lifecycle:
    NORMAL -> ONSET -> EARLY -> DEEP -> RECOVERY -> NORMAL.

    Args:
        r_threshold: Profit rate below which crisis accumulates (default: 0.05).
        n_consecutive: Consecutive below-threshold periods to trigger crisis (default: 3).
        m_recovery: Consecutive above-threshold periods in DEEP to enter RECOVERY (default: 2).
        r_cap: Maximum recovery duration in periods (default: 8).

    See Also:
        :class:`babylon.economics.tick.types.CrisisState`: State tracked by this detector.
        :class:`babylon.economics.tick.types.CrisisPhase`: Phase enumeration.
    """

    def __init__(
        self,
        r_threshold: float = 0.05,
        n_consecutive: int = 3,
        m_recovery: int = 2,
        r_cap: int = 8,
    ) -> None:
        self._r_threshold = r_threshold
        self._n_consecutive = n_consecutive
        self._m_recovery = m_recovery
        self._r_cap = r_cap

    def evaluate(
        self,
        profit_rate: float | None,
        current_state: CrisisState,
    ) -> CrisisState:
        """Evaluate one crisis period and return the updated state.

        FR-005: None profit_rate is a no-op (neither counts toward
        nor resets the consecutive-period accumulator).

        Args:
            profit_rate: Current flow-based profit rate, or None if unavailable.
            current_state: The county's current crisis state.

        Returns:
            Updated CrisisState after this evaluation period.
        """
        if profit_rate is None:
            return current_state

        phase = current_state.phase

        if phase == CrisisPhase.NORMAL:
            return self._evaluate_normal(profit_rate, current_state)
        if phase == CrisisPhase.ONSET:
            return self._evaluate_onset(profit_rate, current_state)
        if phase == CrisisPhase.EARLY:
            return self._evaluate_early(profit_rate, current_state)
        if phase == CrisisPhase.DEEP:
            return self._evaluate_deep(profit_rate, current_state)
        # RECOVERY
        return self._evaluate_recovery(profit_rate, current_state)

    def _evaluate_normal(
        self,
        profit_rate: float,
        state: CrisisState,
    ) -> CrisisState:
        """Evaluate in NORMAL phase.

        Accumulates consecutive_below when r < r_threshold.
        Resets on r >= r_threshold. Transitions to ONSET when
        consecutive_below reaches n_consecutive.
        """
        if profit_rate >= self._r_threshold:
            # Reset accumulator
            return state.model_copy(update={"consecutive_below": 0})

        # Below threshold: increment counter
        new_below = state.consecutive_below + 1

        if new_below >= self._n_consecutive:
            # Trigger ONSET
            return CrisisState(
                phase=CrisisPhase.ONSET,
                consecutive_below=new_below,
                consecutive_recovery=0,
                crisis_start_period=new_below,
                crisis_duration=1,
                peak_severity=profit_rate,
                cumulative_wage_compression=0.0,
            )

        return state.model_copy(update={"consecutive_below": new_below})

    def _evaluate_onset(
        self,
        profit_rate: float,
        state: CrisisState,
    ) -> CrisisState:
        """Evaluate in ONSET phase.

        FR-003: Automatic transition to EARLY on next evaluation.
        Phase progression is strictly linear regardless of profit rate.
        """
        new_severity = self._update_severity(profit_rate, state.peak_severity)

        return CrisisState(
            phase=CrisisPhase.EARLY,
            consecutive_below=state.consecutive_below
            + (1 if profit_rate < self._r_threshold else 0),
            consecutive_recovery=0,
            crisis_start_period=state.crisis_start_period,
            crisis_duration=state.crisis_duration + 1,
            peak_severity=new_severity,
            cumulative_wage_compression=state.cumulative_wage_compression,
        )

    def _evaluate_early(
        self,
        profit_rate: float,
        state: CrisisState,
    ) -> CrisisState:
        """Evaluate in EARLY phase.

        FR-003: Strictly linear progression, duration-based, not r-based.
        EARLY lasts 4 periods (crisis_duration from 2 to 5).
        At crisis_duration > 5 (i.e. after ONSET(1) + EARLY(4)), transition to DEEP.
        """
        new_duration = state.crisis_duration + 1
        new_severity = self._update_severity(profit_rate, state.peak_severity)

        # ONSET is 1 period, EARLY is 4 periods -> DEEP at duration > 5
        new_phase = CrisisPhase.DEEP if new_duration > 1 + _EARLY_DURATION else CrisisPhase.EARLY

        return CrisisState(
            phase=new_phase,
            consecutive_below=state.consecutive_below
            + (1 if profit_rate < self._r_threshold else 0),
            consecutive_recovery=0,
            crisis_start_period=state.crisis_start_period,
            crisis_duration=new_duration,
            peak_severity=new_severity,
            cumulative_wage_compression=state.cumulative_wage_compression,
        )

    def _evaluate_deep(
        self,
        profit_rate: float,
        state: CrisisState,
    ) -> CrisisState:
        """Evaluate in DEEP phase.

        Tracks consecutive_recovery when r >= r_threshold.
        Resets consecutive_recovery on r < r_threshold.
        Transitions to RECOVERY when consecutive_recovery reaches m_recovery.
        """
        new_duration = state.crisis_duration + 1
        new_severity = self._update_severity(profit_rate, state.peak_severity)

        if profit_rate >= self._r_threshold:
            new_recovery = state.consecutive_recovery + 1
            if new_recovery >= self._m_recovery:
                # Enter RECOVERY
                return CrisisState(
                    phase=CrisisPhase.RECOVERY,
                    consecutive_below=state.consecutive_below,
                    consecutive_recovery=new_recovery,
                    crisis_start_period=state.crisis_start_period,
                    crisis_duration=new_duration,
                    peak_severity=new_severity,
                    cumulative_wage_compression=state.cumulative_wage_compression,
                )
            # Still DEEP, accumulating recovery
            return CrisisState(
                phase=CrisisPhase.DEEP,
                consecutive_below=state.consecutive_below,
                consecutive_recovery=new_recovery,
                crisis_start_period=state.crisis_start_period,
                crisis_duration=new_duration,
                peak_severity=new_severity,
                cumulative_wage_compression=state.cumulative_wage_compression,
            )

        # Below threshold: reset recovery counter
        return CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=state.consecutive_below + 1,
            consecutive_recovery=0,
            crisis_start_period=state.crisis_start_period,
            crisis_duration=new_duration,
            peak_severity=new_severity,
            cumulative_wage_compression=state.cumulative_wage_compression,
        )

    def _evaluate_recovery(
        self,
        profit_rate: float,
        state: CrisisState,
    ) -> CrisisState:
        """Evaluate in RECOVERY phase.

        Recovery duration = min(crisis_duration, R_cap).
        If r < r_threshold, interrupted -> back to DEEP.
        On completion -> NORMAL (all counters reset).
        """
        if profit_rate < self._r_threshold:
            # Interrupted recovery -> back to DEEP
            new_severity = self._update_severity(profit_rate, state.peak_severity)
            return CrisisState(
                phase=CrisisPhase.DEEP,
                consecutive_below=1,
                consecutive_recovery=0,
                crisis_start_period=state.crisis_start_period,
                crisis_duration=state.crisis_duration + 1,
                peak_severity=new_severity,
                cumulative_wage_compression=state.cumulative_wage_compression,
            )

        # Decrement recovery remaining
        new_recovery = state.consecutive_recovery + 1
        recovery_target = min(state.crisis_duration, self._r_cap)

        if new_recovery >= recovery_target + self._m_recovery:
            # Recovery complete -> NORMAL
            return CrisisState.normal()

        return CrisisState(
            phase=CrisisPhase.RECOVERY,
            consecutive_below=state.consecutive_below,
            consecutive_recovery=new_recovery,
            crisis_start_period=state.crisis_start_period,
            crisis_duration=state.crisis_duration,
            peak_severity=state.peak_severity,
            cumulative_wage_compression=state.cumulative_wage_compression,
        )

    @staticmethod
    def _update_severity(
        profit_rate: float,
        current_peak: float | None,
    ) -> float:
        """Update peak_severity (lowest profit rate during crisis).

        Args:
            profit_rate: Current profit rate.
            current_peak: Current peak severity (lowest rate seen).

        Returns:
            Updated peak severity.
        """
        if current_peak is None:
            return profit_rate
        return min(current_peak, profit_rate)


__all__ = ["MultiPeriodCrisisDetector", "ThresholdCrisisDetector"]
