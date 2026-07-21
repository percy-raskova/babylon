"""Launcher for the command palette Provider's snapshot test (WO-28).

See ``tests/unit/tui/snapshot_app.py`` for why this launcher constructs a
FRESH app per snapshot run rather than importing a shared module-level
instance (a Textual ``App`` any earlier in-process test already ran renders
with stale mounted state — an order-dependent snapshot flake).
"""

from __future__ import annotations

from typing import Final

from textual.app import App, ComposeResult
from textual.widgets import Footer, Label

from babylon.tui.palette import EntityNavigatorProvider
from babylon.tui.theme import KSBC

KNOWN_ENTITIES: Final = frozenset(
    {"county/26163", "county/48999", "org/tenants-un", "org/uaw-9999"}
)
"""Fixture known-entity set for the golden — matches ``test_palette.py``'s
fixture so both lanes exercise the same demo data."""


class _PaletteHost(App[None]):
    """Bare app registering the command palette Provider for a golden.

    Registers **only** :class:`EntityNavigatorProvider`, not
    ``App.COMMANDS | {...}`` — the default ``SystemCommandsProvider`` runs
    as a concurrent task feeding the same command queue, and its
    interleaving with ours is a genuine race (two independent providers'
    items land in queue-arrival order, not a stable one) that made this
    golden flake across process runs. WO-45 is where the real
    ``ArchiveApp`` composes both; this WO's golden isolates the deliverable
    under test.

    :ivar known_entities: the fixture set the palette fuzzy-matches over.
    """

    COMMANDS = {EntityNavigatorProvider}

    def __init__(self) -> None:
        super().__init__()
        self.known_entities = KNOWN_ENTITIES

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"

    def compose(self) -> ComposeResult:
        yield Label("the Archive — press ctrl+p for the command palette")
        yield Footer()


app = _PaletteHost()
"""A fresh instance per ``runpy`` execution — see module docstring."""

__all__ = ["app"]
