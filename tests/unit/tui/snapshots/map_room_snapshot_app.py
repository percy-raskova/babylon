"""Launcher for the map-room ``{maproom}`` cell-art snapshot test (WO-33).

Mirrors ``tests/unit/tui/snapshot_app.py``'s launcher discipline exactly: a
FRESH :class:`~babylon.tui.app.ArchiveApp` instance is built here (rather than
importing a shared module-level singleton) because ``pytest-textual-snapshot``
``runpy``-executes this file per snapshot run — a cached, already-mounted App
instance from an earlier in-process test would render with stale state, an
order-dependent flake.

The capability flag is OFF by design (``ArchiveApp``'s ``{maproom}`` fence
dispatch — ``BabylonFence._directive_maproom`` — never wires the TGP/pixel
path at all today), so this golden pins exactly the "cell-art floor,
capability flag OFF, no raster" contract the WO names: four state-tier cells
covering all four fill bands (absent, low, elevated, extreme/undefined).
"""

from babylon.tui.app import ArchiveApp

_MAPROOM_PAGE = """\
# Map Room — state tier

```{maproom}
tier: state
26: 0.250000
27: 1.500000
28: 3.000000
29:
```
"""

app = ArchiveApp(page=_MAPROOM_PAGE)

__all__ = ["app"]
