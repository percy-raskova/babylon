"""Escalation ladder ranking and heat-to-escalation scoring (Feature 039).

Provides the mapping from sub-verbs to their position on the escalation
ladder, and a scoring function that determines how well a verb fits the
current threat level (heat).

See Also:
    ``specs/039-state-apparatus-ai/contracts/state-ai-decision.md``: D-03, D-04.
    :class:`babylon.config.defines.StateApparatusAIDefines`: Escalation ladder config.
"""

from __future__ import annotations

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.enums import StateActionType


def get_escalation_rank(
    sub_verb: StateActionType,
    defines: StateApparatusAIDefines,
) -> int:
    """Return the 0-based index of a sub-verb in the escalation ladder.

    Args:
        sub_verb: A StateActionType sub-verb to look up.
        defines: StateApparatusAIDefines containing the escalation_ladder.

    Returns:
        0-based rank if found in the ladder, -1 if not present.
    """
    ladder = defines.escalation_ladder
    max_entries = len(ladder)
    for idx in range(max_entries):
        if ladder[idx] == sub_verb.value:
            return idx
    return -1


def compute_heat_escalation_score(
    heat: float,
    escalation_rank: int,
    max_rank: int,
) -> float:
    """Score how appropriate a verb's escalation level is for current heat.

    The scoring formula creates a preference curve: at low heat, low-rank
    verbs score higher; at high heat, high-rank verbs score higher.

    The formula uses a Gaussian-like affinity:
        normalized_rank = rank / max_rank  (in [0, 1])
        affinity = 1 - |heat - normalized_rank|
        score = max(0, affinity) * BASE_SCORE

    This produces a score peak where the verb's escalation level matches
    the current heat, decaying smoothly in both directions.

    Args:
        heat: Player threat level in [0.0, 1.0].
        escalation_rank: 0-based rank of the verb on the escalation ladder.
        max_rank: Maximum rank value (len(ladder) - 1).

    Returns:
        Non-negative score in [0.0, BASE_SCORE].
    """
    base_score: float = 2.0

    if max_rank <= 0:
        return base_score

    normalized_rank = escalation_rank / max_rank
    distance = abs(heat - normalized_rank)

    # Affinity: 1.0 at perfect match, 0.0 at maximum distance
    affinity = max(0.0, 1.0 - distance)

    return affinity * base_score


__all__ = [
    "compute_heat_escalation_score",
    "get_escalation_rank",
]
