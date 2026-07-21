"""Golden snapshot for the community/hyperedge dossier page (WO-24).

Pins that an attributed roster renders as ``[[social_class/<id>]]``
backlinks (design-canon S9 "backlinks = incidence") and that overlaps render
as ``[[community/<id>]]`` links to the sibling dossier.

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_community_page_renders_roster_and_overlaps_as_backlinks(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The community dossier renders roster/overlaps as wikilink backlinks.

    ``terminal_size`` is widened past the ``(80, 24)`` default: the default
    98-96 frontmatter/statblock/roster/overlaps page overflows a 24-row
    viewport, and a snapshot that clips the second overlap entry off-screen
    would silently pass while the thing this test claims to pin (every
    roster/overlap member rendering as a backlink) went unverified.
    """
    assert snap_compare("community_snapshot_app.py", terminal_size=(100, 50))
