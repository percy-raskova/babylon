"""Legacy re-export shim over :mod:`babylon.projection.verbs.copy`.

Relocated by Program 24 P2 WO-38 (verb read-side hoist); see
``babylon.projection.verbs.copy`` for the real table and its rationale.
Both bridges keep importing from here so player-facing text stays single-
sourced through the P4 cutover.
"""

from __future__ import annotations

from babylon.projection.verbs.copy import VERB_INELIGIBILITY_COPY

__all__ = ["VERB_INELIGIBILITY_COPY"]
