"""Golden snapshot for the social-class dossier page (Program 24 P2 WO-23).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_social_class_page_renders_the_fixture_backed_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The fixture-backed C004 dossier renders byte-identically to the golden SVG."""
    assert snap_compare("social_class_snapshot_app.py")
