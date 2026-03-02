"""Unit tests for attention thread lifecycle (Feature 039, T048).

Tests thread allocation, phase transitions, stickiness, deallocation,
and pool saturation handling.
"""

from __future__ import annotations

import pytest
from tests.unit.state_ai.conftest import make_attention_thread

from babylon.config.defines import GameDefines, StateApparatusAIDefines
from babylon.models.enums import SurveillanceMethod, ThreadPhase
from babylon.ooda.attention.thread_manager import (
    advance_thread_phase,
    allocate_threads,
    update_thread_tick,
)


def _defines() -> StateApparatusAIDefines:
    return GameDefines().state_ai


class TestThreadAllocation:
    """T048: Thread allocation via meta-OODA."""

    def test_allocate_to_empty_pool(self) -> None:
        """New targets get threads when pool is empty."""
        targets = {"org_a": 0.8, "org_b": 0.5, "org_c": 0.3}
        threads = allocate_threads(
            existing_threads=[],
            target_scores=targets,
            pool_size=5,
            defines=_defines(),
        )
        assert len(threads) == 3, "Should allocate one thread per target"
        target_ids = {t.target_id for t in threads}
        assert target_ids == {"org_a", "org_b", "org_c"}

    def test_pool_saturation_keeps_highest_scored(self) -> None:
        """When pool is full, lowest-scored targets are dropped."""
        existing = [
            make_attention_thread(thread_id="t_a", target_id="org_a", ticks_active=0),
            make_attention_thread(thread_id="t_b", target_id="org_b", ticks_active=0),
        ]
        targets = {"org_a": 0.2, "org_b": 0.9, "org_c": 0.7}
        threads = allocate_threads(
            existing_threads=existing,
            target_scores=targets,
            pool_size=2,
            defines=_defines(),
        )
        assert len(threads) == 2
        target_ids = {t.target_id for t in threads}
        # org_b (0.9) and org_c (0.7 new) or org_a with stickiness should be kept
        assert "org_b" in target_ids, "Highest-scored target should be kept"

    def test_stickiness_bonus_preserves_old_threads(self) -> None:
        """Long-tracked threads get a stickiness bonus in allocation."""
        old_thread = make_attention_thread(
            thread_id="t_old",
            target_id="org_old",
            ticks_active=10,
        )
        targets = {"org_old": 0.3, "org_new": 0.35}
        threads = allocate_threads(
            existing_threads=[old_thread],
            target_scores=targets,
            pool_size=1,
            defines=_defines(),
        )
        # org_old has score 0.3 + stickiness(10*0.1=1.0 capped) = 1.3
        # org_new has score 0.35
        assert len(threads) == 1
        assert threads[0].target_id == "org_old", "Stickiness should preserve old thread"


class TestThreadPhaseTransition:
    """T048: Phase transitions driven by intel_completeness."""

    def test_dormant_to_monitoring(self) -> None:
        """Thread advances from DORMANT to MONITORING at threshold."""
        thread = make_attention_thread(
            phase=ThreadPhase.DORMANT,
            intel_completeness=0.15,
            intensity=0.0,
            surveillance_methods=[],
        )
        defines = _defines()
        advanced = advance_thread_phase(thread, defines)
        assert advanced.phase == ThreadPhase.MONITORING
        assert SurveillanceMethod.SIGNALS in advanced.surveillance_methods

    def test_monitoring_to_active(self) -> None:
        """Thread advances from MONITORING to ACTIVE_INVESTIGATION."""
        thread = make_attention_thread(
            phase=ThreadPhase.MONITORING,
            intel_completeness=0.45,
        )
        defines = _defines()
        advanced = advance_thread_phase(thread, defines)
        assert advanced.phase == ThreadPhase.ACTIVE_INVESTIGATION

    def test_active_to_disruption(self) -> None:
        """Thread advances from ACTIVE_INVESTIGATION to DISRUPTION."""
        thread = make_attention_thread(
            phase=ThreadPhase.ACTIVE_INVESTIGATION,
            intel_completeness=0.75,
        )
        defines = _defines()
        advanced = advance_thread_phase(thread, defines)
        assert advanced.phase == ThreadPhase.DISRUPTION

    def test_no_regression(self) -> None:
        """Thread phase never regresses during active tracking."""
        thread = make_attention_thread(
            phase=ThreadPhase.ACTIVE_INVESTIGATION,
            intel_completeness=0.05,  # Below monitoring threshold
        )
        defines = _defines()
        result = advance_thread_phase(thread, defines)
        assert result.phase == ThreadPhase.ACTIVE_INVESTIGATION, "Phase must not regress"

    def test_dormant_stays_dormant_below_threshold(self) -> None:
        """Thread stays DORMANT when intel is below all thresholds."""
        thread = make_attention_thread(
            phase=ThreadPhase.DORMANT,
            intel_completeness=0.05,
            intensity=0.0,
            surveillance_methods=[],
        )
        defines = _defines()
        result = advance_thread_phase(thread, defines)
        assert result.phase == ThreadPhase.DORMANT


class TestThreadTickUpdate:
    """T048: Per-tick thread updates."""

    def test_intel_gains_accumulate(self) -> None:
        """Intel completeness grows with each tick."""
        thread = make_attention_thread(intel_completeness=0.2)
        updated = update_thread_tick(thread, intel_gain=0.1, observation_ceiling=1.0)
        assert updated.intel_completeness == pytest.approx(0.3)
        assert updated.ticks_active == thread.ticks_active + 1

    def test_intel_capped_at_ceiling(self) -> None:
        """Intel cannot exceed observation ceiling."""
        thread = make_attention_thread(intel_completeness=0.5)
        updated = update_thread_tick(thread, intel_gain=0.3, observation_ceiling=0.6)
        assert updated.intel_completeness == pytest.approx(0.6)

    def test_intel_capped_at_one(self) -> None:
        """Intel cannot exceed 1.0."""
        thread = make_attention_thread(intel_completeness=0.9)
        updated = update_thread_tick(thread, intel_gain=0.5, observation_ceiling=1.0)
        assert updated.intel_completeness == 1.0
