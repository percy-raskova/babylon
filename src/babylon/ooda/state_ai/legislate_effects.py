"""LEGISLATE consumption: compute effective capabilities from active laws (Feature 039 Phase 10C).

Provides :func:`consume_legal_framework_effects` which pre-computes an
"effective capabilities" dict from all active :class:`LegalFramework` records.
Downstream resolution functions read capabilities from this dict instead of
checking individual frameworks, keeping framework logic centralized.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B09.
    :mod:`babylon.ooda.state_ai.administer_effects`: Capacity builders.
"""

from __future__ import annotations

import math
from typing import Any

from babylon.config.defines import StateApparatusAIDefines


def consume_legal_framework_effects(
    active_frameworks: list[dict[str, Any]],
    baseline: dict[str, Any],
    defines: StateApparatusAIDefines,
) -> dict[str, Any]:
    """Compute effective capabilities from all active legal frameworks.

    Iterates active :class:`LegalFramework` records and applies their
    ``law_type`` effects to *baseline* capabilities. Each law type applies
    at most once (idempotent) even if multiple frameworks share the same type.

    Args:
        active_frameworks: List of LegalFramework record dicts with ``law_type``.
        baseline: Dict of baseline capabilities to modify. Must include at
            least ``thread_pool_max`` (int), ``liquidate_in_core`` (bool),
            ``intel_bonus`` (float).
        defines: Game defines for effect magnitudes.

    Returns:
        New dict with computed capabilities. Does not mutate inputs.
    """
    result = dict(baseline)

    # Collect unique law types for idempotent application
    seen_types: set[str] = set()

    max_frameworks = len(active_frameworks)
    for i in range(max_frameworks):
        framework = active_frameworks[i]
        law_type: str = framework.get("law_type", "")

        if law_type in seen_types:
            continue
        seen_types.add(law_type)

        if law_type == "EMERGENCY_POWERS":
            pool_max: int = result.get("thread_pool_max", 8)
            result["thread_pool_max"] = math.floor(
                pool_max * defines.emergency_powers_thread_multiplier
            )
            if defines.emergency_powers_liquidate_in_core:
                result["liquidate_in_core"] = True

        elif law_type == "SURVEILLANCE_EXPANSION":
            bonus: float = result.get("intel_bonus", 0.0)
            result["intel_bonus"] = bonus + defines.surveillance_expansion_intel_bonus

        # Other law_types: pass-through (extensible)

    return result


__all__ = [
    "consume_legal_framework_effects",
]
