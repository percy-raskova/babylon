"""Golden snapshot for the ``{matrix}`` incidence/adjacency cell-art grid (WO-32, Lane T).

Pins the deterministic cell-art rendering of both matrix kinds in one page —
an incidence grid (node x hyperedge) and an adjacency grid (node x node) —
including the centrality-hub and singleton legibility Constitution I.21
names (a hub node with a fully filled row/column, an isolated node with
none).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``test_map_room_cellart.py``).
"""

from __future__ import annotations


def test_matrix_renders_incidence_and_adjacency_cell_art(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The {matrix} fixture page renders byte-identically to the golden SVG."""
    assert snap_compare("matrix_snapshot_app.py")
