"""Golden snapshot for the industry dossier page (Program 24 P2, WO-22).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_industry_page_renders_the_honest_absence_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The fixture-fed industry dossier page renders byte-identically to the golden SVG."""
    assert snap_compare("industry_snapshot_app.py")
