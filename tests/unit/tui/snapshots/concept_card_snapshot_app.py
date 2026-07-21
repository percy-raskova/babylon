"""Launcher for the concept-card ``ArchiveApp`` snapshot test (WO-36).

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so the launched module must use
absolute imports. A FRESH ``ArchiveApp`` is built here rather than importing
a shared instance, matching ``tests/unit/tui/snapshot_app.py``'s rationale:
``runpy`` re-executes this file per snapshot run, but importing a
module-level singleton would hand back an already-mounted, stale instance —
an order-dependent snapshot flake.

Renders the Fundamental Theorem concept card — the one card exercising
every optional section (formula fence, statblock, implementation, see-also
wikilinks) in one page.
"""

from babylon.projection.vault.concept_cards import CONCEPT_CARDS, render_concept_card
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_CARD = CONCEPT_CARDS["fundamental-theorem"]

#: Every shipped concept slug resolves as a known wikilink target, so the
#: card's ``[[concept/survival-calculus]]`` see-also link renders as a
#: genuine wikilink rather than a redlink.
_KNOWN_ENTITIES = frozenset(f"concept/{slug}" for slug in CONCEPT_CARDS)

app = ArchiveApp(
    page=render_concept_card(_CARD),
    resolver=known_target_resolver(_KNOWN_ENTITIES),
)

__all__ = ["app"]
