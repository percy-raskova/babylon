"""Launcher for the ``peek()`` stat-plate snapshot (Program 24 P2 WO-25).

Same rationale as ``tests/unit/tui/snapshot_app.py``: ``pytest-textual-snapshot``
resolves a string app path relative to the *calling test file* and executes it
via ``runpy`` with no package context, so this file uses absolute imports and
builds a FRESH ``PeekPlateApp`` at module scope rather than re-exporting a
cached instance — ``runpy`` re-executes this file per snapshot run, but a
module-level singleton imported from elsewhere would carry stale mounted
state across runs (an order-dependent snapshot flake).

Renders :func:`babylon.tui.peek.peek` at all four depths, stacked, for the
Wayne County (FIPS 26163) @ T0847 fixture the WO specifies — one golden
covers the full depth range in a single committed SVG.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from babylon.projection.view_models import ClassComposition, ConsciousnessSimplex, CountyView
from babylon.tui.peek import peek
from babylon.tui.theme import KSBC

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
"""Wayne County @ T0847, wages 19.85 — the WO-25 snapshot fixture persona."""


class PeekPlateApp(App[None]):
    """Stacks ``peek(WAYNE_847, depth)`` for every depth 0..3."""

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
            for depth in range(4):
                yield Static(peek(WAYNE_847, depth))


app = PeekPlateApp()
"""Module-level instance the snapshot launcher exposes to ``snap_compare``."""

__all__ = ["app"]
