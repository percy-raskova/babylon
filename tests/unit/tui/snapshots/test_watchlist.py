"""Golden snapshot for the watchlist page (WO-37).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_watchlist_page_renders_three_pins_including_one_absence(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """Wayne + Oakland (populated rows) + one unresolvable pin, one page.

    ``terminal_size`` is generous (not the 80x24 default): the page chrome
    (title + border) plus three stacked rows need a bit more width than the
    default to avoid wrapping a county id mid-line.
    """
    assert snap_compare("watchlist_app.py", terminal_size=(100, 24))
