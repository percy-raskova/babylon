"""The Topology domain view — the graph, text-floor first.

Glyph floor: the existing ASCII incidence/egotree/PAOH renderers. Raster polish (rustworkx /
XGI → SVG/PNG via the kitty lane) hooks in later, always over a text floor. Individuals and
coalitions are NOT production node types (KEY_FIGURE retired ADR084, PERSON fixture-only) — they
render as declared-future absence, never as fabricated nodes (design §C4).
"""

from __future__ import annotations

from typing import Final, Literal

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

TopologyKind = Literal["incidence", "egotree", "paoh"]

_ABSENT_KINDS = {
    "individual": "Individuals are not yet a production node type (design §C4).",
    "coalition": "Coalitions/alliances are not yet a production node type (design §C4).",
}

_PANE_ABSENT: Final[str] = "▌ topology: no live graph bound yet (wires in at T4-integration)."
"""Program 24 P1 honest-absence fence: :meth:`TopologyView.render_topology` is a
declared-future seam (raises ``NotImplementedError`` by design) — this is the pane's
default body until that binding lands (Constitution III.11)."""


def render_absence(node_kind: str) -> str:
    """Render a visible declared-future stub for a node kind that does not exist in production."""
    reason = _ABSENT_KINDS.get(node_kind, f"{node_kind} is not a production node type.")
    return f"▌ {node_kind}: {reason}"


class TopologyView(Widget):
    """Graph view over org/institution/sovereign/faction/class/territory nodes."""

    def compose(self) -> ComposeResult:
        yield Static(_PANE_ABSENT, id="topology-body")

    def render_topology(self, kind: TopologyKind) -> str:
        """Render the requested topology surface; bound to the live graph at T4-integration."""
        raise NotImplementedError("bound to live graph at T4-integration")
