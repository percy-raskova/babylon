"""Launcher for the Chronicle salience/dedup/AMBER-autopause snapshot (WO-48).

Same rationale as ``tests/unit/tui/snapshots/chronicle_app.py``:
``pytest-textual-snapshot`` resolves a string app path relative to the
*calling test file* and executes it via ``runpy`` with no package context, so
this file uses absolute imports and builds a FRESH ``ChronicleSalienceApp``
instance at module scope rather than re-exporting a cached instance —
``runpy`` re-executes this file per snapshot run, but a module-level
singleton imported from elsewhere would carry stale mounted state across
runs (an order-dependent snapshot flake).

Renders the same Wayne-County-adjacent persona as ``chronicle_app.py``, with
one added wrinkle: a second UPRISING card for the same territory
(``t_wayne``) immediately follows the first in display order —
:func:`~babylon.tui.chronicle_salience.dedupe_consecutive` collapses that
pair to one card before the stream is grouped, so the golden shows exactly
one Wayne County uprising card, not two. UPRISING is critical-tier, so
:func:`~babylon.tui.chronicle_salience.compute_autopause_state` fires, and
the AMBER ``⏸ AUTOPAUSE`` indicator renders below the stream — the "not
wired to any widget yet" token (keel ``theme.py``) wired, at last.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from babylon.models.enums.events import EventType
from babylon.tui.chronicle import ChronicleEvent, chronicle_stream, render_chronicle
from babylon.tui.chronicle_salience import (
    compute_autopause_state,
    dedupe_consecutive,
    render_autopause_indicator,
)
from babylon.tui.theme import KSBC

_EVENTS: tuple[ChronicleEvent, ...] = (
    ChronicleEvent(
        tick=847,
        event_type=EventType.RED_BROWN_COUP,
        summary="a majority Labor Aristocracy defection captures the union hall",
        data={"org_id": "tenants-un"},
        org_names={"tenants-un": "Tenants Union"},
    ),
    ChronicleEvent(
        tick=847,
        event_type=EventType.UPRISING,
        summary="the insurrection holds Wayne County",
        data={"territory_id": "t_wayne"},
    ),
    ChronicleEvent(
        tick=846,
        event_type=EventType.UPRISING,
        summary="mass insurrection erupts in Wayne County",
        data={"territory_id": "t_wayne"},
    ),
    ChronicleEvent(
        tick=845,
        event_type=EventType.MASS_AWAKENING,
        summary="stirs to organized action",
        data={"target_id": "C001"},
    ),
)
"""Newest-display-order-first: the two adjacent UPRISING/t_wayne cards
(ticks 847, 846) are a consecutive dedup collapse; RED_BROWN_COUP and
UPRISING are both critical-tier, driving autopause."""

_DEDUPED = dedupe_consecutive(_EVENTS)
_AUTOPAUSE = compute_autopause_state(_EVENTS)


class ChronicleSalienceApp(App[None]):
    """Stacks the deduped stream above the AMBER autopause indicator."""

    CSS = """
    Screen { background: $background; color: $foreground; }
    #plates { padding: 1 2; }
    Static { margin: 0 0 1 0; width: auto; }
    """

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"

    def compose(self) -> ComposeResult:
        with Vertical(id="plates"):
            yield Static(render_chronicle(chronicle_stream(_DEDUPED)))
            indicator = render_autopause_indicator(_AUTOPAUSE)
            if indicator is not None:
                yield Static(indicator)


app = ChronicleSalienceApp()
"""Module-level instance the snapshot launcher exposes to ``snap_compare``."""

__all__ = ["app"]
