"""The Wiki domain view — the baked-vault reader.

Wraps the existing wikilink-aware markdown renderer. The current single-document ArchiveApp body
becomes this pane; page navigation swaps the document in place (no Screen push).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget

from babylon.tui.app import BabylonMarkdown


class WikiView(Widget):
    """Renders one vault markdown page with wikilink resolution."""

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield BabylonMarkdown(id="wiki-doc")

    def load_page(self, markdown: str) -> None:
        """Replace the displayed document with ``markdown``."""
        self.query_one("#wiki-doc", BabylonMarkdown).update(markdown)
