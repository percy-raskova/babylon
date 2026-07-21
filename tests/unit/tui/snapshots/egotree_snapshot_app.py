"""Launcher for the ``{egotree}`` Levi/bipartite ego-tree snapshot test (WO-31).

Mirrors ``tests/unit/tui/snapshots/map_room_snapshot_app.py``'s launcher
discipline exactly: a FRESH ``ArchiveApp`` instance is built here (rather
than importing a shared module-level singleton) because
``pytest-textual-snapshot`` ``runpy``-executes this file per snapshot run —
a cached, already-mounted App instance from an earlier in-process test would
render with stale state, an order-dependent flake.

Fixture rooted at a community (``settler``) with two members, one of whom
also shares ``patriarchal`` — exercises both the depth-1 (roster) and
depth-2 (cross-community neighbor) fan-out in one golden.
"""

from babylon.tui.app import ArchiveApp

_EGOTREE_PAGE = """\
# Ego-tree — settler

```{egotree}
root: settler
side: community
C001: patriarchal
C002:
```
"""

app = ArchiveApp(page=_EGOTREE_PAGE)

__all__ = ["app"]
