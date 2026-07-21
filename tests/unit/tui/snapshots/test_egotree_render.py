"""Golden snapshot for the WO-31 ``{egotree}`` Levi/bipartite ego-tree.

Pins the depth-2 box-drawing text art for a root community with two roster
members, one of whom also shares a second community (depth-1 = roster,
depth-2 = cross-community neighbor).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``test_snapshot.py``).
"""

from __future__ import annotations


def test_egotree_renders_the_depth_two_bipartite_tree(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The {egotree} community-rooted fixture renders byte-identically to the golden SVG."""
    assert snap_compare("egotree_snapshot_app.py")
