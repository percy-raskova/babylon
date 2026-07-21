"""Launcher for the watchlist-page snapshot (Program 24 P2b WO-37).

Same rationale as ``tests/unit/tui/snapshots/peek_plate_app.py``:
``pytest-textual-snapshot`` resolves a string app path relative to the
*calling test file* and executes it via ``runpy`` with no package context,
so this file uses absolute imports and builds a FRESH ``WatchlistApp`` at
module scope rather than re-exporting a cached instance.

Renders :func:`babylon.tui.watchlist.render_watchlist` for a three-pin
watchlist: Wayne County (fully attributed), Oakland County (lightly
attributed), and one pinned id with no resolvable view at all — one golden
covers the populated row, the honest-absence row, and the page chrome
(title, pin count, border) in a single committed SVG.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from babylon.projection.view_models import ClassComposition, ConsciousnessSimplex, CountyView
from babylon.tui.theme import KSBC
from babylon.tui.watchlist import render_watchlist

WAYNE_847 = CountyView(
    county_fips="26163",
    verified_tick=847,
    population=1_749_343,
    class_composition=ClassComposition(
        bourgeoisie=0.01,
        petit_bourgeoisie=0.09,
        labor_aristocracy=0.4,
        proletariat=0.35,
        lumpenproletariat=0.15,
    ),
    median_wage=19.85,
    imperial_rent_phi=412.7,
    consciousness=ConsciousnessSimplex(
        revolutionary=0.148785,
        liberal=0.4375,
        fascist=0.413715,
    ),
    legitimacy=0.71,
    p_acquiescence=0.61,
    p_revolution=0.44,
    bifurcation_score=-0.32,
    sovereign_id="SOV_USA",
)
"""Wayne County @ T0847, wages 19.85 — the shared WO-25 fixture persona."""

OAKLAND_847 = CountyView(county_fips="26125", verified_tick=847, population=1_270_432)
"""Oakland County — lightly attributed, for a second populated row."""

_PINNED_IDS = ("county/26163", "county/26125", "county/99999")
"""Wayne, Oakland, then an unresolvable id — pin order the golden pins."""

_VIEWS_BY_ID = {"county/26163": WAYNE_847, "county/26125": OAKLAND_847}
"""Deliberately omits ``county/99999`` — exercises the honest absence row."""


class WatchlistApp(App[None]):
    """Renders one ``render_watchlist(...)`` page."""

    CSS = """
    Screen { background: $background; color: $foreground; }
    #page { padding: 1 2; }
    Static { width: auto; }
    """

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"

    def compose(self) -> ComposeResult:
        with Vertical(id="page"):
            yield Static(render_watchlist(_PINNED_IDS, _VIEWS_BY_ID))


app = WatchlistApp()
"""Module-level instance the snapshot launcher exposes to ``snap_compare``."""

__all__ = ["app"]
