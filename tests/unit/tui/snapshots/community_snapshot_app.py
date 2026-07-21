"""Launcher for the community/hyperedge dossier page snapshot test (WO-24).

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so the launched module must use
absolute imports. Colocating this launcher next to ``test_community_page.py``
keeps the path argument a trivial, stable relative reference.

A FRESH ``ArchiveApp`` is constructed here rather than importing any shared
module-level singleton — mirrors ``tests/unit/tui/snapshot_app.py``'s own
rationale exactly (a Textual ``App`` any earlier in-process test already ran
carries stale mounted state, an order-dependent snapshot flake). This does
NOT touch ``babylon.tui.app``'s module contents — ``ArchiveApp`` already
accepts injectable ``page``/``resolver``/``statblocks`` constructor
parameters for exactly this purpose (WO-24 is a Wave-1 WO; ``app.py`` edits
are serialized to WO-45).

The baked page is intentionally NOT the honest all-absent harvested fixture
(WO-24's committed ``tests/fixtures/projection/community_settler.json`` — no
scenario wires a ``community_memberships`` producer today, see
``babylon.projection.community``'s module docstring): this snapshot's whole
job is to pin that an ATTRIBUTED roster renders as ``[[social_class/<id>]]``
backlinks (design-canon S9 "backlinks = incidence"), so it bakes a
hand-built, fully-attributed ``CommunityView`` instead.
"""

from __future__ import annotations

from babylon.projection.vault.render_community import render_community
from babylon.projection.view_models import CommunityOverlap, CommunityView
from babylon.tui.app import ArchiveApp
from babylon.tui.directives import StatblockRow
from babylon.tui.wikilinks import known_target_resolver

_VIEW = CommunityView(
    community_id="settler",
    verified_tick=847,
    roster=("C001", "C002", "C003"),
    overlaps=(
        CommunityOverlap(community_id="patriarchal", shared_member_count=2),
        CommunityOverlap(community_id="women", shared_member_count=1),
    ),
)

_PAGE = render_community(_VIEW, verified_tick=847)

_KNOWN_ENTITIES = frozenset(
    {
        "community/settler",
        "community/patriarchal",
        "community/women",
        "social_class/C001",
        "social_class/C002",
        "social_class/C003",
    }
)


def _statblocks(subject: str) -> list[StatblockRow] | None:
    """The baked page's fence is empty — ``formation_tick`` has no producer
    (see the ``CommunityView`` docstring) — so the community's own statblock
    is legitimately empty, ``()``, distinct from ``None`` ("no projection
    exists for this subject at all")."""
    return [] if subject == "community/settler" else None


app = ArchiveApp(
    page=_PAGE,
    resolver=known_target_resolver(_KNOWN_ENTITIES),
    statblocks=_statblocks,
)

__all__ = ["app"]
