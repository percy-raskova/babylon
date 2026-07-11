"""Tests for MultiPeriodCrisisDetector.

Feature: 018-crisis-devaluation-mechanics
Tasks: T020-T028

Tests the multi-period crisis detector state machine:
- US1 acceptance scenarios (detection via consecutive periods)
- US4 acceptance scenarios (phase lifecycle management)
- Edge cases (interrupted recovery, None handling)
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.crisis_detector import MultiPeriodCrisisDetector
from babylon.domain.economics.tick.types import CrisisPhase, CrisisState

# =============================================================================
# Helpers
# =============================================================================


def _advance(
    detector: MultiPeriodCrisisDetector,
    state: CrisisState,
    profit_rates: list[float | None],
) -> CrisisState:
    """Feed a sequence of profit rates through the detector.

    Args:
        detector: The crisis detector instance.
        state: Starting crisis state.
        profit_rates: Sequence of profit rates to evaluate.

    Returns:
        The crisis state after all evaluations.
    """
    for r in profit_rates:
        state = detector.evaluate(r, state)
    return state


def _make_detector(
    r_threshold: float = 0.05,
    n_consecutive: int = 3,
    m_recovery: int = 2,
    r_cap: int = 8,
) -> MultiPeriodCrisisDetector:
    """Build a detector with explicit parameters."""
    return MultiPeriodCrisisDetector(
        r_threshold=r_threshold,
        n_consecutive=n_consecutive,
        m_recovery=m_recovery,
        r_cap=r_cap,
    )


# =============================================================================
# US1 AS1: Consecutive periods below threshold trigger crisis (T020)
# =============================================================================


@pytest.mark.unit
class TestConsecutiveBelowThreshold:
    """US1 AS1: Consecutive periods below threshold trigger crisis.

    Given a county with profit rates below r_threshold for N consecutive
    periods, the detector should transition from NORMAL to ONSET.
    """

    def test_three_consecutive_below_triggers_onset(self) -> None:
        """3 consecutive below-threshold rates trigger ONSET (N=3 default)."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # Rates: 0.09, 0.08, 0.07 -- all below 0.10
        state = _advance(detector, state, [0.09, 0.08, 0.07])

        assert state.phase == CrisisPhase.ONSET
        assert state.consecutive_below == 3

    def test_spec_example_rates(self) -> None:
        """Spec US1 AS1: rates [0.12, 0.11, 0.10, 0.09, 0.08] with threshold 0.10.

        Periods 1-2: above threshold (0.12, 0.11) -> accumulator stays 0.
        Period 3: at threshold (0.10) -> NOT below (r >= r_threshold) -> accumulator 0.
        Periods 4-5: below threshold (0.09, 0.08) -> accumulator = 2.
        Not enough for N=3 after 5 periods.

        Note: The spec says "r[t] < r_threshold" so 0.10 at threshold is NOT below.
        With the given sequence, consecutive_below reaches 2 at period 5,
        which is less than N=3. But the spec says periods 3, 4, 5 all below.
        Since 0.10 is the threshold and the check is strict less-than,
        0.10 is NOT below. So we need one more period below to trigger.
        """
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # Feed all 5 rates
        state = _advance(detector, state, [0.12, 0.11, 0.10, 0.09, 0.08])

        # 0.10 is NOT below threshold (strict <), so consecutive_below is 2
        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 2

    def test_five_below_threshold_triggers_onset_then_early(self) -> None:
        """5 consecutive below-threshold rates -> ONSET at N=3, then EARLY."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 5 rates all below 0.10
        state = _advance(detector, state, [0.09, 0.08, 0.07, 0.06, 0.05])

        # After 3: ONSET, after 4: EARLY, after 5: still EARLY
        assert state.phase == CrisisPhase.EARLY
        assert state.crisis_duration > 0


# =============================================================================
# US1 AS2: Non-consecutive dips reset accumulator (T021)
# =============================================================================


@pytest.mark.unit
class TestNonConsecutiveDipsReset:
    """US1 AS2: Non-consecutive dips below threshold reset accumulator.

    Given profit rates that dip below then rise above threshold,
    the consecutive-period counter resets.
    """

    def test_recovery_resets_consecutive_below(self) -> None:
        """Rate above threshold resets consecutive_below to 0."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 2 below, 1 above -> reset
        state = _advance(detector, state, [0.09, 0.08, 0.11])

        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 0

    def test_spec_example_non_consecutive(self) -> None:
        """Spec US1 AS2: rates [0.12, 0.09, 0.11, 0.09, 0.08] with N=3.

        Period 1: 0.12 >= 0.10 -> accumulator 0.
        Period 2: 0.09 < 0.10 -> accumulator 1.
        Period 3: 0.11 >= 0.10 -> accumulator RESETS to 0.
        Period 4: 0.09 < 0.10 -> accumulator 1.
        Period 5: 0.08 < 0.10 -> accumulator 2.
        Still NORMAL (need 3 consecutive).
        """
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        state = _advance(detector, state, [0.12, 0.09, 0.11, 0.09, 0.08])

        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 2

    def test_interrupted_accumulation_then_restart(self) -> None:
        """Accumulator restarts after reset and eventually triggers."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 2 below, 1 above (reset), 3 below (triggers)
        state = _advance(detector, state, [0.09, 0.08, 0.11, 0.09, 0.08, 0.07])

        assert state.phase == CrisisPhase.ONSET


# =============================================================================
# US1 AS3: Recovery after M consecutive above-threshold periods (T022)
# =============================================================================


@pytest.mark.unit
class TestRecoveryFromCrisis:
    """US1 AS3: Recovery after M consecutive above-threshold periods.

    Given a county in DEEP crisis, when profit rates recover above
    r_threshold for M consecutive periods, phase transitions to RECOVERY.
    """

    def test_m_above_threshold_enters_recovery(self) -> None:
        """M consecutive above-threshold periods in DEEP -> RECOVERY."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3, m_recovery=2)
        # Start in DEEP crisis
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=8,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=8,
            peak_severity=0.03,
            cumulative_wage_compression=0.0,
        )

        # 2 above-threshold evaluations
        state = _advance(detector, state, [0.12, 0.11])

        assert state.phase == CrisisPhase.RECOVERY
        assert state.consecutive_recovery >= 2

    def test_single_above_threshold_insufficient(self) -> None:
        """Single above-threshold period in DEEP is not enough for M=2."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3, m_recovery=2)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=5,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=5,
            peak_severity=0.04,
            cumulative_wage_compression=0.0,
        )

        state = _advance(detector, state, [0.12])

        assert state.phase == CrisisPhase.DEEP
        assert state.consecutive_recovery == 1


# =============================================================================
# US1 AS4: None profit rate handling (T023)
# =============================================================================


@pytest.mark.unit
class TestNoneProfitRateHandling:
    """US1 AS4: None profit rate neither counts toward nor resets accumulator.

    FR-005: Missing profit rate data is a no-op for the consecutive counter.
    """

    def test_none_does_not_increment_counter(self) -> None:
        """None profit rate does not count toward consecutive_below."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 2 below, None, 1 below -> None breaks nothing, counter still 2 after None
        state = _advance(detector, state, [0.09, 0.08])
        assert state.consecutive_below == 2

        state = detector.evaluate(None, state)
        assert state.consecutive_below == 2  # Unchanged
        assert state.phase == CrisisPhase.NORMAL

    def test_none_does_not_reset_counter(self) -> None:
        """None profit rate does not reset consecutive_below."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 2 below, None, 1 below -> should reach 3
        state = _advance(detector, state, [0.09, 0.08, None, 0.07])

        assert state.consecutive_below == 3
        assert state.phase == CrisisPhase.ONSET

    def test_none_during_deep_preserves_recovery_count(self) -> None:
        """None in DEEP does not affect consecutive_recovery counter."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=5,
            consecutive_recovery=1,
            crisis_start_period=1,
            crisis_duration=5,
            peak_severity=0.04,
            cumulative_wage_compression=0.0,
        )

        state = detector.evaluate(None, state)

        assert state.phase == CrisisPhase.DEEP
        assert state.consecutive_recovery == 1  # Unchanged


# =============================================================================
# US4 AS1: Below threshold but < N stays NORMAL (T024)
# =============================================================================


@pytest.mark.unit
class TestBelowThresholdBelowN:
    """US4 AS1: Below threshold but fewer than N periods stays NORMAL."""

    def test_one_below_stays_normal(self) -> None:
        """Single below-threshold period does not trigger crisis."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        state = detector.evaluate(0.09, state)

        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 1

    def test_two_below_stays_normal_with_n3(self) -> None:
        """Two below-threshold periods stays NORMAL with N=3."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        state = _advance(detector, state, [0.09, 0.08])

        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 2


# =============================================================================
# US4 AS2: Exactly N periods triggers ONSET (T025)
# =============================================================================


@pytest.mark.unit
class TestExactlyNTriggersOnset:
    """US4 AS2: Exactly N consecutive below-threshold periods triggers ONSET."""

    def test_exactly_n_triggers_onset(self) -> None:
        """N=3 consecutive periods below threshold -> ONSET."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        state = _advance(detector, state, [0.09, 0.08, 0.07])

        assert state.phase == CrisisPhase.ONSET
        assert state.consecutive_below == 3
        assert state.crisis_start_period is not None
        assert state.crisis_duration >= 1

    def test_onset_with_n_equals_1(self) -> None:
        """N=1 means first below-threshold period immediately triggers ONSET."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=1)
        state = CrisisState.normal()

        state = detector.evaluate(0.09, state)

        assert state.phase == CrisisPhase.ONSET

    def test_onset_tracks_peak_severity(self) -> None:
        """ONSET records the lowest profit rate as peak_severity."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        state = _advance(detector, state, [0.09, 0.07, 0.08])

        assert state.phase == CrisisPhase.ONSET
        # Peak severity should be the lowest rate seen during crisis
        assert state.peak_severity is not None
        assert state.peak_severity <= 0.08


# =============================================================================
# US4 AS3: ONSET -> EARLY -> DEEP progression (T026)
# =============================================================================


@pytest.mark.unit
class TestPhaseProgression:
    """US4 AS3: ONSET -> EARLY -> DEEP phase progression with duration tracking.

    FR-003: Phase progression is strictly linear.
    ONSET is 1 period, EARLY is 4 periods (N+1 through N+4),
    DEEP is N+5 onward.
    """

    def test_onset_advances_to_early_on_next_eval(self) -> None:
        """ONSET transitions to EARLY on the next evaluation."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 3 below -> ONSET
        state = _advance(detector, state, [0.09, 0.08, 0.07])
        assert state.phase == CrisisPhase.ONSET

        # Next eval -> EARLY (regardless of profit rate per FR-003)
        state = detector.evaluate(0.06, state)
        assert state.phase == CrisisPhase.EARLY

    def test_onset_advances_to_early_even_if_rate_recovers(self) -> None:
        """ONSET -> EARLY even if profit rate recovers (FR-003: strictly linear)."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 3 below -> ONSET
        state = _advance(detector, state, [0.09, 0.08, 0.07])
        assert state.phase == CrisisPhase.ONSET

        # Rate recovers above threshold - still advances to EARLY
        state = detector.evaluate(0.15, state)
        assert state.phase == CrisisPhase.EARLY

    def test_early_persists_for_four_periods(self) -> None:
        """EARLY phase persists for 4 periods before transitioning to DEEP."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 3 below -> ONSET (period 3 = crisis_duration 1)
        state = _advance(detector, state, [0.09, 0.08, 0.07])
        assert state.phase == CrisisPhase.ONSET

        # Period 4: EARLY (crisis_duration 2)
        state = detector.evaluate(0.06, state)
        assert state.phase == CrisisPhase.EARLY

        # Periods 5-7: still EARLY (crisis_duration 3, 4, 5)
        state = detector.evaluate(0.05, state)
        assert state.phase == CrisisPhase.EARLY
        state = detector.evaluate(0.04, state)
        assert state.phase == CrisisPhase.EARLY
        state = detector.evaluate(0.03, state)
        assert state.phase == CrisisPhase.EARLY

    def test_early_transitions_to_deep(self) -> None:
        """EARLY transitions to DEEP after 4 additional periods (N+5 total)."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 3 below -> ONSET (crisis_duration=1)
        # +1 -> EARLY (crisis_duration=2)
        # +3 more -> still EARLY (crisis_duration=5)
        # +1 -> DEEP (crisis_duration=6, i.e. period N+5 onward)
        state = _advance(detector, state, [0.09, 0.08, 0.07])  # ONSET
        state = _advance(detector, state, [0.06, 0.05, 0.04, 0.03])  # EARLY x4
        state = detector.evaluate(0.02, state)  # DEEP

        assert state.phase == CrisisPhase.DEEP

    def test_crisis_duration_increments_correctly(self) -> None:
        """Crisis duration tracks total periods in crisis."""
        detector = _make_detector(r_threshold=0.10, n_consecutive=3)
        state = CrisisState.normal()

        # 3 below -> ONSET
        state = _advance(detector, state, [0.09, 0.08, 0.07])
        onset_duration = state.crisis_duration

        # 1 more -> EARLY
        state = detector.evaluate(0.06, state)
        early_duration = state.crisis_duration

        assert early_duration > onset_duration


# =============================================================================
# US4 AS4: DEEP -> RECOVERY -> NORMAL (T027)
# =============================================================================


@pytest.mark.unit
class TestDeepToRecoveryToNormal:
    """US4 AS4: DEEP -> RECOVERY -> NORMAL with hysteresis window.

    Recovery duration = min(crisis_duration, R_cap).
    After recovery_duration periods, phase returns to NORMAL.
    """

    def test_deep_to_recovery_via_m_consecutive(self) -> None:
        """DEEP transitions to RECOVERY after M consecutive above-threshold."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=10,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=10,
            peak_severity=0.02,
            cumulative_wage_compression=0.0,
        )

        # M=2 consecutive above threshold
        state = _advance(detector, state, [0.12, 0.11])

        assert state.phase == CrisisPhase.RECOVERY

    def test_recovery_eventually_returns_to_normal(self) -> None:
        """RECOVERY persists for hysteresis window then returns to NORMAL.

        Recovery duration = min(crisis_duration, R_cap).
        With crisis_duration=4 and R_cap=8, recovery lasts 4 periods.
        """
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=7,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=4,
            peak_severity=0.03,
            cumulative_wage_compression=0.0,
        )

        # Enter RECOVERY (M=2 above threshold)
        state = _advance(detector, state, [0.12, 0.11])
        assert state.phase == CrisisPhase.RECOVERY

        # Recovery lasts min(4, 8) = 4 periods
        # Feed above-threshold rates through recovery
        for _ in range(10):
            state = detector.evaluate(0.15, state)
            if state.phase == CrisisPhase.NORMAL:
                break

        assert state.phase == CrisisPhase.NORMAL

    def test_recovery_resets_all_counters_on_normal(self) -> None:
        """NORMAL state after recovery has all counters reset (invariant)."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=10,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=3,
            peak_severity=0.02,
            cumulative_wage_compression=0.04,
        )

        # Enter recovery
        state = _advance(detector, state, [0.12, 0.11])
        assert state.phase == CrisisPhase.RECOVERY

        # Push through recovery to NORMAL
        for _ in range(20):
            state = detector.evaluate(0.15, state)
            if state.phase == CrisisPhase.NORMAL:
                break

        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 0
        assert state.consecutive_recovery == 0
        assert state.crisis_start_period is None
        assert state.crisis_duration == 0
        assert state.peak_severity is None
        assert state.cumulative_wage_compression == 0.0

    def test_r_cap_limits_recovery_duration(self) -> None:
        """Recovery duration is capped at R_cap."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=3)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=20,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=20,  # Very long crisis
            peak_severity=0.01,
            cumulative_wage_compression=0.0,
        )

        # Enter recovery
        state = _advance(detector, state, [0.12, 0.11])
        assert state.phase == CrisisPhase.RECOVERY

        # Recovery should last min(20, 3) = 3 periods (R_cap)
        periods_in_recovery = 0
        for _ in range(20):
            state = detector.evaluate(0.15, state)
            periods_in_recovery += 1
            if state.phase == CrisisPhase.NORMAL:
                break

        assert state.phase == CrisisPhase.NORMAL
        assert periods_in_recovery <= 3


# =============================================================================
# US4 Edge Case: Interrupted recovery (T028)
# =============================================================================


@pytest.mark.unit
class TestInterruptedRecovery:
    """Edge case: RECOVERY -> DEEP when profit rate drops during recovery.

    Data-model invariant: consecutive_recovery resets to 0, crisis_duration
    and cumulative_wage_compression carry forward.
    """

    def test_recovery_interrupted_by_below_threshold(self) -> None:
        """Rate dropping below threshold during RECOVERY returns to DEEP."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=10,
            consecutive_recovery=0,
            crisis_start_period=1,
            crisis_duration=10,
            peak_severity=0.03,
            cumulative_wage_compression=0.04,
        )

        # Enter RECOVERY
        state = _advance(detector, state, [0.12, 0.11])
        assert state.phase == CrisisPhase.RECOVERY

        # Rate drops below threshold -> back to DEEP
        state = detector.evaluate(0.08, state)
        assert state.phase == CrisisPhase.DEEP

    def test_interrupted_recovery_resets_consecutive_recovery(self) -> None:
        """Interrupted recovery resets consecutive_recovery to 0."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        state = CrisisState(
            phase=CrisisPhase.RECOVERY,
            consecutive_below=10,
            consecutive_recovery=2,
            crisis_start_period=1,
            crisis_duration=10,
            peak_severity=0.03,
            cumulative_wage_compression=0.04,
        )

        # Rate drops during recovery
        state = detector.evaluate(0.08, state)

        assert state.phase == CrisisPhase.DEEP
        assert state.consecutive_recovery == 0

    def test_interrupted_recovery_preserves_crisis_duration(self) -> None:
        """Interrupted recovery preserves crisis_duration (data-model invariant)."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        original_duration = 10
        original_compression = 0.04
        state = CrisisState(
            phase=CrisisPhase.RECOVERY,
            consecutive_below=10,
            consecutive_recovery=2,
            crisis_start_period=1,
            crisis_duration=original_duration,
            peak_severity=0.03,
            cumulative_wage_compression=original_compression,
        )

        state = detector.evaluate(0.08, state)

        assert state.phase == CrisisPhase.DEEP
        assert state.crisis_duration >= original_duration
        assert state.cumulative_wage_compression >= original_compression

    def test_interrupted_recovery_updates_peak_severity(self) -> None:
        """Interrupted recovery may update peak_severity if new rate is lower."""
        detector = _make_detector(r_threshold=0.10, m_recovery=2, r_cap=8)
        state = CrisisState(
            phase=CrisisPhase.RECOVERY,
            consecutive_below=10,
            consecutive_recovery=2,
            crisis_start_period=1,
            crisis_duration=10,
            peak_severity=0.05,  # Previous low was 0.05
            cumulative_wage_compression=0.0,
        )

        # Rate drops to 0.02 (below previous peak_severity of 0.05)
        state = detector.evaluate(0.02, state)

        assert state.phase == CrisisPhase.DEEP
        assert state.peak_severity is not None
        assert state.peak_severity <= 0.02
