"""Golden snapshot for the national dossier page (Program 24 P2 WO-17).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together.
"""

from __future__ import annotations


def test_archive_app_renders_the_national_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The baked USA national dossier page renders byte-identically to the golden SVG."""
    assert snap_compare("national_page_app.py")
