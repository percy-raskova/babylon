"""Launcher for the PAOH topology-surface snapshot test (WO-30, Lane T).

Mirrors ``tests/unit/tui/snapshots/community_snapshot_app.py``'s own
rationale exactly: ``CommunityView.formation_tick`` has no producer in any
real game today (see ``babylon.projection.topology.paoh``'s module
docstring), so a dossier exercising the PAOH ordering must be hand-built,
not harvested — this is the same honesty tradeoff WO-24's own community-page
golden already made for ``roster``, applied here to ``formation_tick``.

A FRESH ``ArchiveApp`` is constructed here rather than reusing a shared
module-level singleton (mirrors ``tests/unit/tui/snapshot_app.py``'s own
rationale: a Textual ``App`` any earlier in-process test already ran carries
stale mounted state, an order-dependent snapshot flake). This does NOT touch
``babylon.tui.app`` — ``ArchiveApp`` already accepts an injectable ``page``
constructor parameter (WO-30 is a Wave-1 WO; ``app.py`` edits are serialized
to WO-45).

The whole point of this fixture: the fence BODY below is not hand-typed (as
``map_room_snapshot_app.py``'s is) — it is produced by
``paoh_ordering`` + ``format_paoh_fence_body`` from three hand-built
:class:`~babylon.projection.view_models.CommunityView` dossiers, then handed
to the keel's already-shipped ``{paoh}`` directive unchanged. Three
communities with distinct formation ticks and overlapping rosters
(``C001``/``C002``/``C003`` span all three) exercise both the tick-ascending
column order and the shared-member row spans ``render_paoh`` draws.
"""

from __future__ import annotations

from babylon.models.enums import CommunityType
from babylon.projection.topology.paoh import format_paoh_fence_body, paoh_ordering
from babylon.projection.view_models import CommunityView
from babylon.tui.app import ArchiveApp

_VIEWS = (
    CommunityView(
        community_id=CommunityType.SETTLER,
        verified_tick=847,
        roster=("C001", "C002"),
        formation_tick=12,
    ),
    CommunityView(
        community_id=CommunityType.PATRIARCHAL,
        verified_tick=847,
        roster=("C002", "C003"),
        formation_tick=30,
    ),
    CommunityView(
        community_id=CommunityType.WOMEN,
        verified_tick=847,
        roster=("C001", "C003"),
        formation_tick=5,
    ),
)

_NODES, _EDGES = paoh_ordering(_VIEWS)
_BODY = format_paoh_fence_body(_NODES, _EDGES)

_PAGE = f"""\
# Community Hypergraph — PAOH

```{{paoh}}
{_BODY}
```
"""

app = ArchiveApp(page=_PAGE)

__all__ = ["app"]
