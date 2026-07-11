"""Hegemonic fraction OODA effects for institutions (Feature 040).

Computes orientation modifier hints based on the hegemonic ruling-class
fraction within an institution.  The caller (OODA resolution layer)
interprets the returned dict; this function never modifies OODAProfile
directly.

See Also:
    ``specs/040-institution-base-model/spec.md``: FR-008, SC-009.
"""

from __future__ import annotations

from typing import Any

from babylon.models.enums import ActionType, RulingClassFraction


def hegemonic_fraction_effect(
    fraction: RulingClassFraction,
) -> dict[str, Any]:
    """Compute OODA modifier hints based on hegemonic fraction.

    Args:
        fraction: The currently hegemonic ruling-class fraction.

    Returns:
        Dict with keys ``preferred_actions`` (list of ActionType values)
        and ``escalation_reluctance`` (float in [0, 1]).

    Raises:
        ValueError: If *fraction* is not a valid RulingClassFraction member.
    """
    if fraction == RulingClassFraction.LIBERAL_TECHNOCRATIC:
        return {
            "preferred_actions": [ActionType.ASSIMILATE],
            "escalation_reluctance": 0.7,
        }

    if fraction == RulingClassFraction.REVANCHIST_FASCIST:
        return {
            "preferred_actions": [ActionType.REPRESS],
            "escalation_reluctance": 0.2,
        }

    if fraction == RulingClassFraction.INSTITUTIONALIST_BONAPARTIST:
        return {
            "preferred_actions": [ActionType.SURVEIL],
            "escalation_reluctance": 0.5,
        }

    msg = f"Unknown RulingClassFraction: {fraction!r}"
    raise ValueError(msg)
