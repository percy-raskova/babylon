"""Golden snapshot for the command palette Provider (WO-28).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together.
"""

from __future__ import annotations

from textual.pilot import Pilot
from textual.widgets import Input


async def _open_palette_without_cursor_blink(pilot: Pilot) -> None:
    """Open the command palette, then kill cursor blink.

    Cursor blink is a known SVG-golden flakiness source (the
    pytest-textual-snapshot README's own ``run_before`` recipe calls
    ``disable_blink_for_active_cursors`` — a helper that does not exist in
    the 1.1.0 pin, so this reimplements the equivalent directly).

    :param pilot: the running app's ``Pilot``.
    """
    await pilot.press("ctrl+p")
    await pilot.pause()
    for search_input in pilot.app.query(Input):
        search_input.cursor_blink = False
    await pilot.pause()


def test_palette_discover_lists_known_entities(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """Opening the palette with no query renders the ``discover()`` listing."""
    assert snap_compare("palette_snapshot_app.py", run_before=_open_palette_without_cursor_blink)
