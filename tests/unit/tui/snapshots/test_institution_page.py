"""Golden snapshot for the institution dossier page (Program 24 P2 WO-19).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package, matching ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_institution_page_renders_the_doj_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The baked institution/doj dossier page renders byte-identically to the golden SVG."""
    assert snap_compare("institution_snapshot_app.py")
