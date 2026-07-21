"""Golden snapshot for ``peek()`` stat plates across all four depths (WO-25).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_peek_plate_renders_wayne_county_at_every_depth(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """Wayne County (26163) @ T0847 renders identically at depths 0..3.

    ``terminal_size`` is generous (not the 80x24 default): four stacked
    plates, capped at the WO-25 depth->row-count mapping (1/3/6/all-16 for
    this fully-attributed fixture), need ~40 rows to all sit in the visible
    viewport — the snapshot captures one frame, never a scroll, so an
    under-sized terminal would silently crop the deepest plate's tail rows
    rather than fail loud.
    """
    assert snap_compare("peek_plate_app.py", terminal_size=(100, 60))
