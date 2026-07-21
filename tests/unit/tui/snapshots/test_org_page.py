"""Golden snapshot for the organization dossier page (Program 24 P2 WO-18).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_organization_page_renders_the_rwp_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The RWP organization dossier renders byte-identically to the golden SVG."""
    assert snap_compare("org_page_app.py")
