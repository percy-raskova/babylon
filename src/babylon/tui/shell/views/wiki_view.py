"""The Wiki domain view — the baked-vault reader.

Wraps the existing wikilink-aware markdown renderer. The current single-document ArchiveApp body
becomes this pane; page navigation swaps the document in place (no Screen push).

**Program 24 P1 wiring note:** the document id is ``dossier`` (not a fresh ``wiki-doc``) —
:class:`~babylon.tui.app.ArchiveApp` mounts this view as its own shell's "wiki" pane, and every
existing nav/redlink/tutorial test queries ``#dossier`` directly (``app.query_one("#dossier",
BabylonMarkdown)``); ``ContentSwitcher`` hides non-current panes via CSS ``display``, not
unmounting, so the query still resolves regardless of which pane is currently switched-to. The
``parser_factory``/``statblocks``/``open_links`` constructor params let ``ArchiveApp`` thread its
own live-refreshing wikilink resolver and statblock provider through exactly as it did when it
composed ``BabylonMarkdown`` directly — zero behavior change for the dossier itself.
"""

from __future__ import annotations

from collections.abc import Callable

from markdown_it import MarkdownIt
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget

from babylon.tui.app import BabylonMarkdown
from babylon.tui.directives import StatblockProvider


class WikiView(Widget):
    """Renders one vault markdown page with wikilink resolution.

    :param id: the widget's own DOM id.
    :param page: the initially-displayed markdown page; ``None`` (the default) starts the
        dossier blank, matching ``BabylonMarkdown``'s own no-argument default — ``ArchiveApp``
        passes its own ``self._page`` so the dossier shows content from the very first render,
        exactly as it did composing ``BabylonMarkdown`` directly.
    :param parser_factory: the dossier's ``MarkdownIt`` factory (see
        ``BabylonMarkdown``'s own docstring) — defaults to ``None`` (plain parsing, no
        wikilink resolution), matching a standalone ``WikiView()``'s pre-wiring behavior.
    :param statblocks: the live statblock provider for ``{statblock}`` fences; defaults to
        ``None`` (``BabylonMarkdown`` falls back to its own sample provider).
    :param open_links: whether ``Markdown`` should auto-navigate its own internal anchors;
        ``ArchiveApp`` passes ``False`` (it handles ``LinkClicked`` itself).
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        page: str | None = None,
        parser_factory: Callable[[], MarkdownIt] | None = None,
        statblocks: StatblockProvider | None = None,
        open_links: bool = True,
    ) -> None:
        super().__init__(id=id)
        self._page = page
        self._parser_factory = parser_factory
        self._statblocks = statblocks
        self._open_links = open_links

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield BabylonMarkdown(
                self._page,
                parser_factory=self._parser_factory,
                open_links=self._open_links,
                id="dossier",
                statblocks=self._statblocks,
            )

    def load_page(self, markdown: str) -> None:
        """Replace the displayed document with ``markdown``."""
        self.query_one("#dossier", BabylonMarkdown).update(markdown)
