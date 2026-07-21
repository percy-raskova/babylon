"""Golden snapshot for the map room's cell-art floor (WO-33, Lane T).

Pins "cell-art at the EA/state tiers, capability flag OFF, no raster"
(charter P0 batch tier ruling) — the county-tier/TGP-raster path is
deliberately NOT snapshot-gated (kitty-protocol bytes are a manual, real-Kitty
eyes-on check, not an SVG-golden concern; see
``tests/unit/tui/test_map_room_directive.py::TestRenderMapRoom`` for its
structural, non-snapshot coverage).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``test_snapshot.py``).
"""

from __future__ import annotations


def test_map_room_renders_the_cell_art_floor(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The {maproom} state-tier fixture renders byte-identically to the golden SVG."""
    assert snap_compare("map_room_snapshot_app.py")
