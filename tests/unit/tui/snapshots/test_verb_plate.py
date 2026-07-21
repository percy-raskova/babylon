"""Golden snapshot for the verb plate (WO-26).

Regenerate deliberately with ``--snapshot-update`` after a rendering change,
then re-run plainly to confirm the regenerated SVG is stable; both the SVG
and this test are committed together (``__snapshots__/`` is not gitignored
for this package).
"""

from __future__ import annotations


def test_verb_plate_renders_wayne_county_tick_zero_all_nine_eligible(snap_compare) -> None:  # type: ignore[no-untyped-def]
    """Wayne (26163) tick-0, all nine verbs eligible via TENANCY, renders identically.

    ``terminal_size`` is generous (not the 80x24 default): the plate carries
    nine verbs, three of them (INVESTIGATE's sub-verbs) rendered as separate
    lines, each with a two-line body (label+status, then the consequence
    preview) — around 24 content rows, so an under-sized terminal would
    silently crop the plate's tail rather than fail loud.
    """
    assert snap_compare("verb_plate_app.py", terminal_size=(100, 40))
