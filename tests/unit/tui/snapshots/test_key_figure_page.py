"""Golden snapshot for the key-figure honest-absence dossier page (WO-21).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package — mirrors ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_key_figure_dossier_renders_the_honest_absence_page(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The baked kf-001 dossier renders byte-identically to the golden SVG."""
    assert snap_compare("key_figure_snapshot_app.py")
