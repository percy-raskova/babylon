"""Golden snapshot for the PAOH topology surface, wired from projection data
(WO-30, Lane T).

Pins that a ``{paoh}`` fence body **produced by**
``babylon.projection.topology.paoh.paoh_ordering`` +
``format_paoh_fence_body`` (not hand-typed) renders correctly through the
keel's already-shipped ``_directive_paoh`` — a real end-to-end proof of the
"ordering provider -> fence body -> matrix" seam the WO names, on top of the
plain unit coverage in ``tests/unit/projection/topology/test_paoh.py``.

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``test_community_page.py``).
"""

from __future__ import annotations


def test_paoh_page_renders_the_matrix_produced_from_projection_data(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The {paoh} fence body built from paoh_ordering() renders as a PAOH matrix."""
    assert snap_compare("paoh_snapshot_app.py", terminal_size=(100, 30))
