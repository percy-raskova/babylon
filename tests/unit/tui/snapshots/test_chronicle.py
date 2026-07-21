"""Golden snapshot for the Chronicle stream (Program 24 P2 WO-27).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_chronicle_renders_the_grouped_stream_and_a_quiet_tick(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The grouped event stream plus a quiet tick (T0848) render byte-identically."""
    assert snap_compare("chronicle_app.py", terminal_size=(100, 40))
