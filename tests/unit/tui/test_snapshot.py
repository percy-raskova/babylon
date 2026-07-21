"""Golden snapshot for the Archive TUI shell (ADR099 snapshot lane).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_archive_app_renders_the_sample_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The sample county dossier page renders byte-identically to the golden SVG."""
    assert snap_compare("snapshot_app.py")
