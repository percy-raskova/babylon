"""Golden snapshot for the baked sovereign dossier page (WO-20).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together.
"""

from __future__ import annotations


def test_sovereign_page_renders_the_baked_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """A fully-attributed sovereign dossier (statblock + Claims links) renders byte-identically."""
    assert snap_compare("snapshot_sovereign_app.py")
