"""Verb projections — the read side of the nine Article V player verbs.

Transport-neutral ports of the legacy web bridge's verb read-models
(Program 24 P2, WO-38): the canonical verb -> engine ``ActionType``
mapping, the resolver-parity consciousness preview (preview == resolution,
spec-116 FR-4.4), the per-verb preview estimates, and the verb-plate view
(eligibility + affordability + copy) the TUI verb plate renders.

Write-side verb submission is deliberately NOT here — it lands with
WO-39; nothing in this package mutates the graph (Ruling R4: structured
verbs only, the engine adjudicates).
"""

from babylon.projection.verbs.copy import VERB_INELIGIBILITY_COPY
from babylon.projection.verbs.plate import build_verb_plate
from babylon.projection.verbs.preview import (
    CANONICAL_VERBS,
    VERB_TO_ACTION_TYPE,
    preview_consciousness_delta,
    preview_verb,
)
from babylon.projection.verbs.view_models import VerbPlateView, VerbPreview, VerbRow

__all__ = [
    "CANONICAL_VERBS",
    "VERB_INELIGIBILITY_COPY",
    "VERB_TO_ACTION_TYPE",
    "VerbPlateView",
    "VerbPreview",
    "VerbRow",
    "build_verb_plate",
    "preview_consciousness_delta",
    "preview_verb",
]
