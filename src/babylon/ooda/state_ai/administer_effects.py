"""ADMINISTER verb resolution: FUND, STAFF, AUDIT (Feature 039 Phase 10B).

Pure functions that resolve ADMINISTER sub-verb effects on state apparatus
capacity. FUND increases capacity ratings, STAFF grows the attention thread
pool, and AUDIT detects enemy infiltrations within the apparatus.

All functions follow the same pattern as :mod:`territory_effects`: take dicts
and a :class:`~babylon.config.defines.StateApparatusAIDefines`, return new
dicts without mutating inputs.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B02.
    :mod:`babylon.ooda.state_ai.territory_effects`: Analogous pattern.
"""

from __future__ import annotations

import random
from typing import Any

from babylon.config.defines import StateApparatusAIDefines

_VALID_CAPACITY_TYPES = frozenset({"violence", "surveillance", "service"})

_CAPACITY_FIELD_MAP: dict[str, str] = {
    "violence": "violence_capacity",
    "surveillance": "surveillance_capacity",
    "service": "service_delivery",
}

_VALID_AUDIT_DEPTHS = frozenset({"ROUTINE", "THOROUGH", "DEEP"})


def resolve_fund(
    apparatus: dict[str, Any],
    capacity_type: str,
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """Increment a state apparatus capacity via FUND action.

    Args:
        apparatus: State apparatus dict with capacity fields.
        capacity_type: One of ``"violence"``, ``"surveillance"``, ``"service"``.
        defines: Game defines for increment value.

    Returns:
        New apparatus dict with incremented capacity (capped at 1.0).

    Raises:
        ValueError: If *capacity_type* is not recognized.
    """
    if capacity_type not in _VALID_CAPACITY_TYPES:
        msg = f"Invalid capacity_type {capacity_type!r}; expected one of {sorted(_VALID_CAPACITY_TYPES)}"
        raise ValueError(msg)

    result = dict(apparatus)
    field = _CAPACITY_FIELD_MAP[capacity_type]
    current: float = result.get(field, 0.0)
    result[field] = min(1.0, current + defines.fund_capacity_increment)
    return result


def resolve_staff(
    apparatus: dict[str, Any],
    current_pool_size: int,
    count: int,
    defines: StateApparatusAIDefines,
) -> tuple[dict[str, Any], int]:
    """Grow the attention thread pool via STAFF action.

    Pool growth requires ``surveillance_capacity > 0``. The actual increase
    is capped by :attr:`staff_max_per_tick` and :attr:`thread_pool_max`.

    Args:
        apparatus: State apparatus dict with ``surveillance_capacity``.
        current_pool_size: Current number of thread slots.
        count: Requested number of new threads.
        defines: Game defines for caps.

    Returns:
        Tuple of (updated apparatus dict, new pool size).
    """
    result = dict(apparatus)
    surv_cap: float = result.get("surveillance_capacity", 0.0)

    if surv_cap <= 0.0 or count <= 0:
        return result, current_pool_size

    effective_count = min(count, defines.staff_max_per_tick)
    room = defines.thread_pool_max - current_pool_size
    effective_count = max(0, min(effective_count, room))

    new_pool = current_pool_size + effective_count
    return result, new_pool


def resolve_audit(
    apparatus: dict[str, Any],
    active_infiltrations: list[dict[str, Any]],
    depth: str,
    defines: StateApparatusAIDefines,
    rng_seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Check for enemy infiltrations via AUDIT action.

    Each active infiltration is tested against the detection chance for the
    given audit *depth*. Detection is deterministic for a given *rng_seed*.

    Args:
        apparatus: State apparatus dict.
        active_infiltrations: List of infiltration record dicts.
        depth: One of ``"ROUTINE"``, ``"THOROUGH"``, ``"DEEP"``.
        defines: Game defines for detection chances.
        rng_seed: Seed for deterministic RNG.

    Returns:
        Tuple of (updated apparatus dict, list of detected infiltrations).

    Raises:
        ValueError: If *depth* is not recognized.
    """
    if depth not in _VALID_AUDIT_DEPTHS:
        msg = f"Invalid audit depth {depth!r}; expected one of {sorted(_VALID_AUDIT_DEPTHS)}"
        raise ValueError(msg)

    detection_chances: dict[str, float] = {
        "ROUTINE": defines.audit_routine_detection_chance,
        "THOROUGH": defines.audit_thorough_detection_chance,
        "DEEP": defines.audit_deep_detection_chance,
    }
    detection_chance = detection_chances[depth]

    result = dict(apparatus)
    detected: list[dict[str, Any]] = []

    max_infil = len(active_infiltrations)
    for i in range(max_infil):
        rng = random.Random(rng_seed + i)
        if rng.random() < detection_chance:
            detected.append(dict(active_infiltrations[i]))

    # Track counter-intel score based on detections
    counter_intel: float = result.get("counter_intel_score", 0.0)
    if max_infil > 0:
        counter_intel = min(1.0, counter_intel + len(detected) / max_infil * 0.1)
    result["counter_intel_score"] = counter_intel

    return result, detected


__all__ = [
    "resolve_audit",
    "resolve_fund",
    "resolve_staff",
]
