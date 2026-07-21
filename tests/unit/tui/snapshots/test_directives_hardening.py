"""Golden snapshot for the WO-29 directive-hardening delta.

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (mirrors ``tests/unit/tui/test_snapshot.py``).
"""

from __future__ import annotations


def test_directives_hardening_delta_renders_stably(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """The bracket-laden statblock/narrative rows and cache-keyed narrator
    byline render byte-identically to the golden SVG."""
    assert snap_compare("directives_hardening_app.py")
