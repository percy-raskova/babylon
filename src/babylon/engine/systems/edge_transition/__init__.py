"""Edge transition system package — Spec 059 US5 / ADR-006.4.

Replaces the historical 856-LOC ``engine/systems/edge_transition.py`` single
file with a package whose ``__init__.py`` re-exports the public surface
unchanged. The original implementation lives at ``_legacy.py`` while the
content split into ``predicates.py`` (the 3 Pydantic predicate models) +
``system.py`` (the System class) per data-model.md §2.5 is deferred to a
follow-up — preserving byte-equality and import equivalence trumps SC-002's
LOC budget for this commit.

EdgeTransitionSystem inherits from SystemBase (Spec 059 US3 / ADR-003) — the
hard ordering documented in research.md D5 holds: ADR-003 is committed
(15a6bda6 + de1d8b4b + 17c65460) before this US5/T072 lands.

Import equivalence (FR-003 / contracts/import-equivalence.md C7): every
existing ``from babylon.engine.systems.edge_transition import X`` resolves
unchanged via this re-export.
"""

from __future__ import annotations

from babylon.engine.systems.edge_transition._legacy import (
    _VALID_TRANSITIONS,
    CompoundPredicate,
    EdgeModeTransition,
    EdgeTransitionSystem,
    PredicateCondition,
)

__all__ = [
    "_VALID_TRANSITIONS",
    "CompoundPredicate",
    "EdgeModeTransition",
    "EdgeTransitionSystem",
    "PredicateCondition",
]
