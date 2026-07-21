"""Verb projections — the read side of the nine Article V player verbs.

Transport-neutral ports of the legacy web bridge's verb read-models
(Program 24 P2, WO-38): the canonical verb -> engine ``ActionType``
mapping, the resolver-parity consciousness preview (preview == resolution,
spec-116 FR-4.4), the per-verb preview estimates, and the verb-plate view
(eligibility + affordability + copy) the TUI verb plate renders.

The write side (WO-39) owns exactly ONE write: a structured row in the
runtime action queue via :func:`submit_verb` — nothing in this package
mutates the graph (Ruling R4: structured verbs only, the engine
adjudicates via OODASystem next tick).
"""

from babylon.projection.verbs.copy import VERB_INELIGIBILITY_COPY
from babylon.projection.verbs.plate import build_verb_plate
from babylon.projection.verbs.preview import (
    CANONICAL_VERBS,
    VERB_TO_ACTION_TYPE,
    preview_consciousness_delta,
    preview_verb,
)
from babylon.projection.verbs.submit import TurnSink, build_player_actions, submit_verb
from babylon.projection.verbs.view_models import VerbPlateView, VerbPreview, VerbRow

__all__ = [
    "CANONICAL_VERBS",
    "VERB_INELIGIBILITY_COPY",
    "VERB_TO_ACTION_TYPE",
    "TurnSink",
    "VerbPlateView",
    "VerbPreview",
    "VerbRow",
    "build_player_actions",
    "build_verb_plate",
    "preview_consciousness_delta",
    "preview_verb",
    "submit_verb",
]
