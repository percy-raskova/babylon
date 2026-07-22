"""The hybrid player shell: tabbed main region + persistent rails.

Layout (design §B): docked header · left chronicle rail · right watchlist rail · bottom action
bar · a ``ContentSwitcher`` main region across the four domains, switched by number keys. Views
are projection clients only — the shell never imports the engine (import-linter contract).
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import ContentSwitcher, Footer, Header, Static

_VIEW_ORDER = ("dashboard", "map", "wiki", "topology")


class DomainPane(Static):
    """Placeholder pane; replaced by real view widgets in Phase 3."""


class AppShell(App[None]):
    """Root player shell."""

    CSS = """
    #chronicle-rail { width: 24; dock: left; border-right: solid $panel; }
    #watchlist-rail { width: 24; dock: right; border-left: solid $panel; }
    #action-bar { height: 3; dock: bottom; border-top: solid $panel; }
    #main { height: 1fr; }
    """

    BINDINGS = [
        Binding(str(i + 1), f"switch_view({name!r})", name.capitalize())
        for i, name in enumerate(_VIEW_ORDER)
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("chronicle", id="chronicle-rail")
        yield Static("watchlist", id="watchlist-rail")
        with Vertical():
            with ContentSwitcher(initial="dashboard", id="main"):
                for name in _VIEW_ORDER:
                    yield DomainPane(name, id=name)
            yield Static("action bar", id="action-bar")
        yield Footer()

    def action_switch_view(self, view: str) -> None:
        """Switch the main region to ``view`` (one of the four domain pane ids)."""
        self.query_one("#main", ContentSwitcher).current = view
