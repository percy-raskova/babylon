"""Launcher for the verb-plate snapshot (Program 24 P2 WO-26).

Same rationale as ``tests/unit/tui/snapshot_app.py``: ``pytest-textual-snapshot``
resolves a string app path relative to the *calling test file* and executes it
via ``runpy`` with no package context, so this file uses absolute imports and
builds a FRESH ``VerbPlateApp`` at module scope rather than re-exporting a
cached instance — ``runpy`` re-executes this file per snapshot run, but a
module-level singleton imported from elsewhere would carry stale mounted
state across runs (an order-dependent snapshot flake).

Renders :func:`babylon.tui.verb_plate.render_verb_plate` for the Wayne
County (FIPS 26163) tick-0 fixture the WO specifies: every one of the nine
Article V verbs eligible via the real Occupant -> Territory TENANCY edge
(mirrors ``verb-submit.spec.ts``'s corrected tick-0 assertion), built through
the already-contract-tested :func:`babylon.projection.verbs.plate.build_verb_plate`
provider (WO-38) over a small hand-built graph — no engine, no database.

Unit "selection-unwrap" (shell-interconnect): ``render_verb_plate`` returns a
bare ``Text`` now (no more inner ``Panel``, so ``Widget.get_selection`` can
extract it) — the crimson border + gold org/tick title moved to the
``Static``'s own CSS chrome + :func:`~babylon.tui.verb_plate.verb_plate_title`,
mirroring exactly how ``ArchiveApp``'s real ``#action-bar`` paints it
(``babylon.tui.app``), so this golden keeps showing the header it always did.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.verbs.plate import build_verb_plate
from babylon.topology import BabylonGraph
from babylon.tui.theme import KSBC
from babylon.tui.verb_plate import render_verb_plate, verb_plate_title

ORG = "org-wayne-vanguard"
TERRITORY = "T26163"


def _wayne_graph() -> BabylonGraph:
    """Wayne County (FIPS 26163) tick-0: every verb eligible via TENANCY."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="Wayne County Tenants Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[TERRITORY],
    )
    graph.add_node(TERRITORY, NodeType.TERRITORY, county_fips="26163")
    graph.add_node(
        "sc-wayne-proles",
        NodeType.SOCIAL_CLASS,
        name="Wayne proletariat",
        population=1000,
    )
    graph.add_edge("sc-wayne-proles", TERRITORY, EdgeType.TENANCY)
    graph.add_node(
        "org-shop",
        NodeType.ORGANIZATION,
        name="Chamber of Commerce",
        org_type="business",
        territory_ids=[TERRITORY],
    )
    graph.add_node(
        "inst-court",
        NodeType.INSTITUTION,
        name="Wayne County Court",
        territory_ids=[TERRITORY],
    )
    return graph


_WAYNE_PLATE = build_verb_plate(_wayne_graph(), ORG, tick=0)
assert _WAYNE_PLATE is not None
"""Wayne County (26163) @ tick 0 — the WO-26 snapshot fixture persona."""


class VerbPlateApp(App[None]):
    """Renders ``render_verb_plate(_WAYNE_PLATE)``, chromed like the real action bar."""

    CSS = """
    Screen { background: $background; color: $foreground; }
    #plate { padding: 1 2; }
    #action-bar { width: auto; padding: 0 1; border: solid $primary; }
    #action-bar { border-title-color: $accent; border-title-background: $panel; border-title-style: bold; }
    """

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"
        self.query_one("#action-bar", Static).border_title = verb_plate_title(_WAYNE_PLATE)

    def compose(self) -> ComposeResult:
        with Vertical(id="plate"):
            yield Static(render_verb_plate(_WAYNE_PLATE), id="action-bar")


app = VerbPlateApp()
"""Module-level instance the snapshot launcher exposes to ``snap_compare``."""

__all__ = ["app"]
