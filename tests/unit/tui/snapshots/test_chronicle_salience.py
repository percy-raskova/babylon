"""Golden snapshot for the Chronicle salience/dedup/AMBER-autopause layer (WO-48).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_chronicle_salience_renders_the_deduped_stream_and_amber_autopause(
    snap_compare,  # type: ignore[no-untyped-def]
) -> None:
    """The consecutive-deduped stream plus the AMBER autopause indicator render byte-identically."""
    assert snap_compare("chronicle_salience_app.py", terminal_size=(100, 40))
