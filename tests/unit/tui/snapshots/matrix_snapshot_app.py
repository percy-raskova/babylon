"""Launcher for the ``{matrix}`` incidence/adjacency cell-art snapshot test (WO-32).

Mirrors ``map_room_snapshot_app.py``'s launcher discipline exactly: a FRESH
:class:`~babylon.tui.app.ArchiveApp` instance is built here (rather than
importing a shared module-level singleton) because ``pytest-textual-snapshot``
``runpy``-executes this file per snapshot run — a cached, already-mounted App
instance from an earlier in-process test would render with stale state, an
order-dependent flake.

One page, two fences: an incidence matrix (three nodes across two real
``CommunityType`` hyperedges, one node — HUB — a member of both, visibly a
centrality hub with a filled row) and an adjacency matrix derived by hand
from the same membership (HUB adjacent to everyone, LONE adjacent to
nobody — the singleton case) — pinning Constitution I.21's
centrality/singleton legibility in one golden.
"""

from babylon.tui.app import ArchiveApp

_MATRIX_PAGE = """\
# Topology — incidence / adjacency

```{matrix}
kind: incidence
nodes: hub, lone, c001
edges: settler, women
hub: settler, women
lone: settler
c001: women
```

```{matrix}
kind: adjacency
nodes: hub, lone, c001
hub: c001
c001: hub
lone:
```
"""

app = ArchiveApp(page=_MATRIX_PAGE)

__all__ = ["app"]
