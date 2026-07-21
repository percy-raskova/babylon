"""Golden snapshot for a baked concept-card page (Program 24 P2 WO-36).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_concept_card_page_renders_the_fundamental_theorem(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The Fundamental Theorem concept card renders byte-identically to the golden SVG."""
    assert snap_compare("concept_card_snapshot_app.py")
