"""Launcher for the Chronicle stream snapshot (Program 24 P2 WO-27).

Same rationale as ``tests/unit/tui/snapshots/peek_plate_app.py``:
``pytest-textual-snapshot`` resolves a string app path relative to the
*calling test file* and executes it via ``runpy`` with no package context,
so this file uses absolute imports and builds a FRESH ``ChroniclePlateApp``
at module scope rather than re-exporting a cached instance — ``runpy``
re-executes this file per snapshot run, but a module-level singleton
imported from elsewhere would carry stale mounted state across runs (an
order-dependent snapshot flake).

Renders the grouped, newest-tick-first stream (:func:`~babylon.tui.chronicle.render_chronicle`
over :func:`~babylon.tui.chronicle.chronicle_stream`) for a small
Wayne-County-adjacent fixture, stacked above one quiet tick's dated page
(:func:`~babylon.tui.chronicle.render_bulletin` over
:func:`~babylon.tui.chronicle.bulletin_for_tick`) — one golden covers both
the populated-stream and honest-absence paths.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from babylon.models.enums.events import EventType
from babylon.tui.chronicle import (
    ChronicleEvent,
    bulletin_for_tick,
    chronicle_stream,
    render_bulletin,
    render_chronicle,
)
from babylon.tui.theme import KSBC

_EVENTS: tuple[ChronicleEvent, ...] = (
    ChronicleEvent(
        tick=845,
        event_type=EventType.MASS_AWAKENING,
        summary="stirs to organized action",
        data={"target_id": "C001"},
    ),
    ChronicleEvent(
        tick=847,
        event_type=EventType.UPRISING,
        summary="mass insurrection erupts in Wayne County",
        data={"territory_id": "t_wayne"},
    ),
    ChronicleEvent(
        tick=847,
        event_type=EventType.RED_BROWN_COUP,
        summary="a majority Labor Aristocracy defection captures the union hall",
        data={"org_id": "tenants-un"},
        org_names={"tenants-un": "Tenants Union"},
    ),
)
"""Wayne County (FIPS 26163)-adjacent fixture events — the WO-27 snapshot persona."""


class ChroniclePlateApp(App[None]):
    """Stacks the grouped stream above one quiet tick's dated page (T0848)."""

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
            yield Static(render_chronicle(chronicle_stream(_EVENTS)))
            yield Static(render_bulletin(bulletin_for_tick(_EVENTS, 848)))


app = ChroniclePlateApp()
"""Module-level instance the snapshot launcher exposes to ``snap_compare``."""

__all__ = ["app"]
