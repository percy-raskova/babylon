"""Golden snapshot for the campaign lobby (Program 24 P3 WO-49).

Mirrors ``tests/unit/tui/test_snapshot.py`` exactly. Regenerate deliberately
with ``--snapshot-update`` after a rendering change, then re-run plainly to
confirm the regenerated SVG is stable; both the SVG and this test are
committed together (``__snapshots__/`` is not gitignored for this package).
"""

from __future__ import annotations


def test_lobby_renders_the_campaign_catalog(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The seeded lobby renders byte-identically: codename · Tick N · status rows."""
    assert snap_compare("lobby_snapshot_app.py")
