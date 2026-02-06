"""Integration test for full crisis lifecycle.

Feature: 018-crisis-devaluation-mechanics
Task: T029

Tests the complete crisis lifecycle:
NORMAL -> ONSET -> EARLY -> DEEP -> RECOVERY -> NORMAL
via synthetic profit rate sequence.
"""

from __future__ import annotations

import pytest

from babylon.economics.tick.crisis_detector import MultiPeriodCrisisDetector
from babylon.economics.tick.types import CrisisPhase, CrisisState


@pytest.mark.unit
class TestFullCrisisLifecycle:
    """Full lifecycle integration: NORMAL through all phases back to NORMAL.

    Uses default crisis parameters (N=3, M=2, R_cap=8) to drive a county
    through the complete crisis lifecycle.
    """

    def test_complete_lifecycle(self) -> None:
        """Drive a county through NORMAL -> ONSET -> EARLY -> DEEP -> RECOVERY -> NORMAL."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=8,
        )
        state = CrisisState.normal()

        # === Phase 1: NORMAL ===
        # Healthy profit rates -- should stay NORMAL
        for r in [0.15, 0.12, 0.11]:
            state = detector.evaluate(r, state)
        assert state.phase == CrisisPhase.NORMAL

        # === Phase 2: Approaching crisis ===
        # 2 consecutive below threshold -- not enough for N=3
        state = detector.evaluate(0.09, state)
        state = detector.evaluate(0.08, state)
        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 2

        # === Phase 3: ONSET ===
        # 3rd consecutive below threshold -> ONSET
        state = detector.evaluate(0.07, state)
        assert state.phase == CrisisPhase.ONSET
        assert state.crisis_duration >= 1

        # === Phase 4: EARLY ===
        # Next evaluation advances to EARLY
        state = detector.evaluate(0.06, state)
        assert state.phase == CrisisPhase.EARLY

        # EARLY persists for 3 more evaluations (4 total EARLY periods)
        state = detector.evaluate(0.05, state)
        assert state.phase == CrisisPhase.EARLY
        state = detector.evaluate(0.04, state)
        assert state.phase == CrisisPhase.EARLY
        state = detector.evaluate(0.03, state)
        assert state.phase == CrisisPhase.EARLY

        # === Phase 5: DEEP ===
        # Next evaluation transitions to DEEP
        state = detector.evaluate(0.02, state)
        assert state.phase == CrisisPhase.DEEP

        # Stay in DEEP for a few more periods
        state = detector.evaluate(0.03, state)
        assert state.phase == CrisisPhase.DEEP
        state = detector.evaluate(0.04, state)
        assert state.phase == CrisisPhase.DEEP

        # === Phase 6: Begin recovery ===
        # 1 above threshold -> still DEEP (need M=2)
        state = detector.evaluate(0.12, state)
        assert state.phase == CrisisPhase.DEEP

        # 2nd above threshold -> RECOVERY
        state = detector.evaluate(0.13, state)
        assert state.phase == CrisisPhase.RECOVERY

        # === Phase 7: RECOVERY persists for hysteresis window ===
        recovery_counter = 0
        max_recovery = 20  # Safety bound
        while state.phase == CrisisPhase.RECOVERY and recovery_counter < max_recovery:
            state = detector.evaluate(0.15, state)
            recovery_counter += 1

        # === Phase 8: Back to NORMAL ===
        assert state.phase == CrisisPhase.NORMAL
        assert recovery_counter > 0  # Recovery took some periods
        assert recovery_counter <= 8  # Bounded by R_cap

        # Verify all counters are reset
        assert state.consecutive_below == 0
        assert state.consecutive_recovery == 0
        assert state.crisis_start_period is None
        assert state.crisis_duration == 0
        assert state.peak_severity is None
        assert state.cumulative_wage_compression == 0.0

    def test_lifecycle_with_none_periods(self) -> None:
        """Lifecycle with intermittent None profit rates.

        None periods should not interrupt the lifecycle progression.
        """
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=4,
        )
        state = CrisisState.normal()

        # 2 below, None (no effect), 1 below -> should trigger at 3
        state = detector.evaluate(0.09, state)
        state = detector.evaluate(0.08, state)
        state = detector.evaluate(None, state)  # No effect
        state = detector.evaluate(0.07, state)  # 3rd consecutive

        assert state.phase == CrisisPhase.ONSET

    def test_lifecycle_with_interrupted_recovery(self) -> None:
        """Lifecycle where recovery is interrupted then eventually succeeds."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=4,
        )
        state = CrisisState.normal()

        # Drive to DEEP
        # 3 below -> ONSET, +1 -> EARLY, +3 -> still EARLY, +1 -> DEEP
        for r in [0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02]:
            state = detector.evaluate(r, state)

        assert state.phase == CrisisPhase.DEEP

        # Enter RECOVERY
        state = detector.evaluate(0.12, state)
        state = detector.evaluate(0.11, state)
        assert state.phase == CrisisPhase.RECOVERY

        # Rate drops -> back to DEEP
        state = detector.evaluate(0.08, state)
        assert state.phase == CrisisPhase.DEEP

        # Try recovery again
        state = detector.evaluate(0.12, state)
        state = detector.evaluate(0.13, state)
        assert state.phase == CrisisPhase.RECOVERY

        # This time complete recovery
        for _ in range(20):
            state = detector.evaluate(0.15, state)
            if state.phase == CrisisPhase.NORMAL:
                break

        assert state.phase == CrisisPhase.NORMAL

    def test_multiple_crisis_episodes(self) -> None:
        """County can go through multiple complete crisis-recovery cycles."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=3,
        )
        state = CrisisState.normal()

        for _episode in range(2):
            # Drive into crisis: 3 below -> ONSET
            for _ in range(3):
                state = detector.evaluate(0.05, state)
            assert state.phase != CrisisPhase.NORMAL

            # Drive through to DEEP
            for _ in range(10):
                state = detector.evaluate(0.03, state)
                if state.phase == CrisisPhase.DEEP:
                    break
            assert state.phase == CrisisPhase.DEEP

            # Recover: M=2 above threshold -> RECOVERY
            state = detector.evaluate(0.15, state)
            state = detector.evaluate(0.15, state)
            assert state.phase == CrisisPhase.RECOVERY

            # Push through recovery to NORMAL
            for _ in range(20):
                state = detector.evaluate(0.15, state)
                if state.phase == CrisisPhase.NORMAL:
                    break

            assert state.phase == CrisisPhase.NORMAL
