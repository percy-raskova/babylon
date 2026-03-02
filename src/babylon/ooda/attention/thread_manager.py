"""Attention thread management (Feature 039).

Handles thread pool allocation, phase transitions, and per-tick updates.
The meta-OODA cycle allocates threads to targets based on threat assessment.

See Also:
    :class:`babylon.models.entities.attention_thread.AttentionThread`: Thread model.
    :class:`babylon.config.defines.StateApparatusAIDefines`: Thread config.
"""

from __future__ import annotations

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.attention_thread import AttentionThread
from babylon.models.enums import SurveillanceMethod, ThreadPhase


def allocate_threads(
    existing_threads: list[AttentionThread],
    target_scores: dict[str, float],
    pool_size: int,
    defines: StateApparatusAIDefines,
) -> list[AttentionThread]:
    """Allocate attention threads to targets based on threat scores.

    Greedy allocation with stickiness bonus for long-tracked targets.
    Deallocates lowest-priority threads when pool is saturated.

    Args:
        existing_threads: Current thread list.
        target_scores: Target ID to threat score mapping.
        pool_size: Maximum threads in the pool.
        defines: Configuration for escalation thresholds.

    Returns:
        Updated list of threads (may add new, remove low-priority).
    """
    # Score existing threads with stickiness bonus
    # Use minimum_effect_floor from defines as base stickiness increment
    stickiness_bonus = defines.minimum_effect_floor * 5.0  # ~0.1 at default 0.02
    scored_existing: list[tuple[float, AttentionThread]] = []

    for idx in range(len(existing_threads)):
        thread = existing_threads[idx]
        base_score = target_scores.get(thread.target_id, 0.0)
        bonus = min(thread.ticks_active * stickiness_bonus, 1.0)
        scored_existing.append((base_score + bonus, thread))

    # Sort by score descending
    scored_existing.sort(key=lambda x: x[0], reverse=True)

    # Keep top threads within pool size
    kept: list[AttentionThread] = []
    kept_target_ids: set[str] = set()
    max_keep = pool_size
    for idx in range(len(scored_existing)):
        if len(kept) >= max_keep:
            break
        _, thread = scored_existing[idx]
        kept.append(thread)
        kept_target_ids.add(thread.target_id)

    # Allocate remaining slots to new targets
    remaining_slots = pool_size - len(kept)
    if remaining_slots > 0:
        # Sort unallocated targets by score descending
        new_targets = [
            (score, tid) for tid, score in target_scores.items() if tid not in kept_target_ids
        ]
        new_targets.sort(key=lambda x: x[0], reverse=True)

        max_new = remaining_slots
        for new_idx in range(min(len(new_targets), max_new)):
            _score, target_id = new_targets[new_idx]
            new_thread = AttentionThread(
                thread_id=f"thread_{target_id}_{len(kept) + new_idx}",
                target_type="organization",
                target_id=target_id,
                phase=ThreadPhase.DORMANT,
                intensity=0.0,
                intel_completeness=0.0,
                surveillance_methods=[],
                observed_node_ids=frozenset(),
                observed_edge_ids=frozenset(),
                stickiness=0.0,
                ticks_active=0,
                owning_apparatus_id="state_apparatus",
            )
            kept.append(new_thread)

    return kept


def advance_thread_phase(
    thread: AttentionThread,
    defines: StateApparatusAIDefines,
) -> AttentionThread:
    """Advance a thread's phase based on intel_completeness thresholds.

    Phase transitions are one-directional during active tracking
    (no regression). Thresholds from defines.thread_escalation_thresholds.

    Args:
        thread: Current thread state.
        defines: Configuration with phase thresholds.

    Returns:
        Updated thread (via model_copy) if phase changed.
    """
    thresholds = defines.thread_escalation_thresholds
    ic = thread.intel_completeness
    current_phase = thread.phase

    # Determine target phase based on thresholds (check highest first)
    target_phase = current_phase

    if ic >= thresholds.get("active_to_disruption", 0.7):
        target_phase = ThreadPhase.DISRUPTION
    elif ic >= thresholds.get("monitoring_to_active", 0.4):
        target_phase = ThreadPhase.ACTIVE_INVESTIGATION
    elif ic >= thresholds.get("dormant_to_monitoring", 0.1):
        target_phase = ThreadPhase.MONITORING

    # Only advance, never regress
    phase_order = [
        ThreadPhase.DORMANT,
        ThreadPhase.MONITORING,
        ThreadPhase.ACTIVE_INVESTIGATION,
        ThreadPhase.DISRUPTION,
    ]
    current_idx = phase_order.index(current_phase)
    target_idx = phase_order.index(target_phase)

    if target_idx > current_idx:
        # Advance phase and set appropriate surveillance methods
        new_methods = _methods_for_phase(target_phase)
        new_intensity = _intensity_for_phase(target_phase)
        return thread.model_copy(
            update={
                "phase": target_phase,
                "surveillance_methods": new_methods,
                "intensity": new_intensity,
            }
        )

    return thread


def update_thread_tick(
    thread: AttentionThread,
    intel_gain: float,
    observation_ceiling: float,
) -> AttentionThread:
    """Update a thread for one tick of surveillance activity.

    Increments ticks_active and intel_completeness (capped at ceiling).

    Args:
        thread: Current thread state.
        intel_gain: Intel gained this tick [0, 1].
        observation_ceiling: Maximum intel_completeness achievable.

    Returns:
        Updated thread via model_copy.
    """
    new_intel = min(
        observation_ceiling,
        thread.intel_completeness + intel_gain,
    )
    new_intel = max(0.0, min(1.0, new_intel))

    return thread.model_copy(
        update={
            "intel_completeness": new_intel,
            "ticks_active": thread.ticks_active + 1,
        }
    )


def _methods_for_phase(phase: ThreadPhase) -> list[SurveillanceMethod]:
    """Get default surveillance methods for a phase.

    Args:
        phase: Target thread phase.

    Returns:
        List of surveillance methods appropriate for the phase.
    """
    if phase == ThreadPhase.DORMANT:
        return []
    if phase == ThreadPhase.MONITORING:
        return [SurveillanceMethod.SIGNALS]
    if phase == ThreadPhase.ACTIVE_INVESTIGATION:
        return [SurveillanceMethod.SIGNALS, SurveillanceMethod.FINANCIAL]
    if phase == ThreadPhase.DISRUPTION:
        return [
            SurveillanceMethod.SIGNALS,
            SurveillanceMethod.FINANCIAL,
            SurveillanceMethod.INFORMANT,
        ]
    return []


def _intensity_for_phase(phase: ThreadPhase) -> float:
    """Get default intensity for a phase.

    Args:
        phase: Target thread phase.

    Returns:
        Default intensity value for the phase.
    """
    if phase == ThreadPhase.DORMANT:
        return 0.0
    if phase == ThreadPhase.MONITORING:
        return 0.3
    if phase == ThreadPhase.ACTIVE_INVESTIGATION:
        return 0.6
    if phase == ThreadPhase.DISRUPTION:
        return 0.9
    return 0.0


__all__ = [
    "advance_thread_phase",
    "allocate_threads",
    "update_thread_tick",
]
