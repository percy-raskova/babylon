"""Golden snapshot for the state dossier page (Program 24 P2 WO-16).

Mirrors ``tests/unit/tui/test_snapshot.py`` exactly. Regenerate deliberately
with ``--snapshot-update`` after a rendering change, then re-run plainly to
confirm the regenerated SVG is stable; both the SVG and this test are
committed together (``__snapshots__/`` is not gitignored for this package).
"""

from __future__ import annotations


def test_state_page_renders_the_baked_michigan_dossier(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The baked Michigan state dossier page renders byte-identically to the golden SVG."""
    assert snap_compare("state_page_app.py")
