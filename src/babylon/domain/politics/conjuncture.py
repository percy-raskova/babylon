"""The popular-front conjuncture — one consolidation-pressure measure (P25 U12, ADR139).

the-electoral-question.md §3.4: when the ``fascist_consolidation`` axis progress
crosses ``politics.popular_front_trigger``, the ambient system poses a forced
choice to EVERY line, abstentionists included — commit org labor and credibility
to the defense of the liberal state, or hold autonomy and trust the independent
SOLIDARITY topology. Third Period vs Popular Front, live, under conditions the
player did not choose.

:func:`consolidation_pressure` is the SINGLE measure of that consolidation
pressure, computed from the same material signals
``EndgameDetector._axis_fascist_consolidation`` reads:

* the **false-consciousness route** (spec-116): the fraction of ideology-bearing
  entities whose ``national_identity`` exceeds their ``class_consciousness``,
  gated against ``endgame.fascist_majority_fraction``;
* the **political-violence route** (spec-070 FR-031): an UPHOLD-aligned
  Sovereign claims majority, an INTENSIFY extraction majority, and
  ``state_violence_index`` at its max — three binary gates, averaged.

The axis's overall pressure is the better of the two routes. One math, two
adapters: the detector delegates its gate inputs to this function (its
pre-U12 semantics preserved EXACTLY — ``matched`` collapses onto
``pressure == 1.0`` because every gate is clamped to [0, 1], so the either-route
OR and the max-of-routes progress saturate together) and ``ElectoralSystem``
@17.45 calls it for the trigger. This module is pure: the adapters gather
terrain, the arithmetic never touches the graph.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

#: Stances whose practice is already INSIDE the liberal state's machinery —
#: entryism (operating within a host machine) and the governance road
#: (contesting for state power itself). In the §3.4 forced choice these commit
#: to the defense; every other line holds autonomy. A delegated-judgment
#: modeling ruling (BD delegated judgment at charter, ADR127 precedent),
#: documented in ADR139: it is the SIMPLEST stance-keyed deterministic rule,
#: and it keeps the conjuncture a reading of what the org already IS rather
#: than a second doctrine verdict.
_APPARATUS_ENTANGLED_STANCES: Final[frozenset[str]] = frozenset({"entryism", "governance_road"})


class PopularFrontArm(StrEnum):
    """The two arms of the §3.4 forced choice."""

    COMMIT = "commit"
    AUTONOMY = "autonomy"


def consolidation_pressure(
    ideologies: tuple[tuple[float, float] | None, ...],
    *,
    uphold_stance_majority: bool,
    intensify_extraction_majority: bool,
    state_violence_index: float,
    state_violence_index_max: float,
    fascist_majority_fraction: float,
) -> float:
    """The fascist-consolidation pressure of the current terrain, in [0, 1].

    Reproduces ``EndgameDetector._axis_fascist_consolidation``'s gate
    arithmetic verbatim (same operand order, so float reductions match
    bit-for-bit):

    * false-consciousness route — ``fascist_count / max(1, ideology_bearing)``
      where an entity counts as fascist iff ``national_identity >
      class_consciousness`` (a ``None`` entry — no ideology object — is
      neither bearing nor fascist, the detector's ``0.0 > 0.0`` edge), the
      fraction gated by ``_gate_reach`` against ``fascist_majority_fraction``;
    * political-violence route — the mean of the three binary gates (stance
      majority, extraction majority, violence index at max);
    * the pressure is the maximum of the two route progresses.

    :param ideologies: ``(national_identity, class_consciousness)`` per
        entity, or ``None`` for entities with no ideology object.
    :param uphold_stance_majority: Whether UPHOLD-aligned Sovereigns hold a
        majority of CLAIMS edges.
    :param intensify_extraction_majority: Whether INTENSIFY Sovereigns hold a
        majority of CLAIMS edges.
    :param state_violence_index: The spec-039 graph attr (0.0 when absent).
    :param state_violence_index_max: Its max (1.0 when absent).
    :param fascist_majority_fraction: ``endgame.fascist_majority_fraction``.
    :returns: The axis progress in [0, 1]; saturation (== 1.0) is exactly the
        detector's matched condition.
    """
    ideology_bearing = 0
    fascist_count = 0
    for pair in ideologies:
        if pair is None:
            continue
        ideology_bearing += 1
        national_identity, class_consciousness = pair
        if national_identity > class_consciousness:
            fascist_count += 1
    fascist_fraction = fascist_count / max(1, ideology_bearing)
    if fascist_majority_fraction <= 0.0:
        false_consciousness = 1.0 if fascist_fraction >= fascist_majority_fraction else 0.0
    else:
        false_consciousness = max(0.0, min(1.0, fascist_fraction / fascist_majority_fraction))

    stance_gate = 1.0 if uphold_stance_majority else 0.0
    extraction_gate = 1.0 if intensify_extraction_majority else 0.0
    violence_gate = 1.0 if state_violence_index >= state_violence_index_max else 0.0
    violence_route = (stance_gate + extraction_gate + violence_gate) / 3

    return max(false_consciousness, violence_route)


def resolve_popular_front_arm(stances: tuple[str, ...]) -> PopularFrontArm:
    """Resolve the §3.4 forced choice for one org from its doctrine stances.

    The arm is a reading of what the org already IS (delegated-judgment
    ruling, ADR139): an org holding ANY apparatus-entangled stance — entryism
    or the governance road — defends the liberal state whose machinery its
    practice already runs inside (COMMIT); every other org holds AUTONOMY,
    including abstentionists and orgs that never took the electoral question.
    Entanglement dominates a mixed portfolio: an org that is inside the
    machine by any line is inside it.

    :param stances: The org's acquired doctrine node ids.
    :returns: The resolved arm.
    """
    if any(stance in _APPARATUS_ENTANGLED_STANCES for stance in stances):
        return PopularFrontArm.COMMIT
    return PopularFrontArm.AUTONOMY


__all__ = [
    "PopularFrontArm",
    "consolidation_pressure",
    "resolve_popular_front_arm",
]
