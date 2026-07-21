"""Golden snapshot for the UNRESOLVED epilogue page shell (WO-34).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package — mirrors ``tests/unit/tui/test_snapshot.py``).

``unresolved`` is the representative outcome pinned here (of the six WO-34
ships) because it is also the one contract-tested byte-for-byte against
``first-session.spec.ts`` in
``tests/unit/projection/vault/test_epilogues.py`` — the same page, both a
content contract and a visual one.
"""

from __future__ import annotations


def test_unresolved_epilogue_page_renders(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The UNRESOLVED epilogue page renders byte-identically to the golden SVG."""
    assert snap_compare("epilogue_snapshot_app.py")
