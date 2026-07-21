"""Minimal Archive TUI shell: boots, renders a sample county dossier page.

Demonstrates the WO-5 shell wired together — the ksbc theme, the fenced
directive dispatch, the wikilink content spans, and the ``babylon://``
router — on a small sample page rather than any live projection data (that
wiring is WO-3/WO-7). Headless-runnable via ``App.run_test()``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from markdown_it import MarkdownIt
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Label, Markdown

from babylon.tui.directives import BabylonFence, StatblockProvider
from babylon.tui.dispatch import (
    fixture_known_entities,
    fixture_statblock_providers,
    kind_dispatch_statblocks,
)
from babylon.tui.router import InvalidBabylonUri, parse_babylon_uri
from babylon.tui.theme import KSBC
from babylon.tui.wikilinks import (
    BabylonH1,
    BabylonH2,
    BabylonH3,
    BabylonH4,
    BabylonH5,
    BabylonH6,
    BabylonParagraph,
    BabylonTableDataCell,
    BabylonTableHeaderCell,
    WikilinkResolver,
    known_target_resolver,
    make_parser_factory,
)

KNOWN_ENTITIES: Final = fixture_known_entities() | frozenset({"org/tenants-un"})
"""The demo resolver's known-set: every committed Lane P fixture subject
(WO-45 kind-dispatch composition) plus the sample page's demo org. A live
session replaces this with
:func:`babylon.projection.epistemic_search.known_entity_ids` — the
``reach ∪ intel`` epistemic set, never a global oracle (WO-43)."""

SAMPLE_COUNTY_PAGE: Final = """\
# county/26163 — Wayne

Solidarity runs through [[county/26163|Wayne County]] and its neighbor
[[org/tenants-un]], but [[org/uaw-9999]] has no dossier yet.

```{statblock} county/26163
```

```{narrative} the Narrator
The picket line held through the second shift change.
```

```{nonsense} arg
```
"""
"""A sample dossier page: a known wikilink, a redlink, a statblock, a
narrative aside, and an unknown directive (to exercise the loud-refusal path)."""


def _default_statblocks() -> StatblockProvider:
    """The app's default provider: kind-dispatch over every Lane P kind.

    WO-45: replaces the keel's literal ``county/26163`` sample branch with
    :func:`~babylon.tui.dispatch.kind_dispatch_statblocks` composed over
    the committed-fixture providers. P3 swaps the composition input to
    live per-tick projections; the dispatch seam itself is unchanged.

    :returns: the composed provider.
    """
    return kind_dispatch_statblocks(fixture_statblock_providers())


class BabylonMarkdown(Markdown):
    """The Archive's markdown dialect: fenced directives + wikilink spans.

    :param statblocks: the statblock provider fences in this document defer
        to (``BabylonFence`` reads it off the parent widget); defaults to
        the sample page's fixture provider.
    """

    BLOCKS = {
        **Markdown.BLOCKS,
        "fence": BabylonFence,
        "code_block": BabylonFence,
        "paragraph_open": BabylonParagraph,
        "h1": BabylonH1,
        "h2": BabylonH2,
        "h3": BabylonH3,
        "h4": BabylonH4,
        "h5": BabylonH5,
        "h6": BabylonH6,
        "th_open": BabylonTableHeaderCell,
        "td_open": BabylonTableDataCell,
    }

    def __init__(
        self,
        markdown: str | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        parser_factory: Callable[[], MarkdownIt] | None = None,
        open_links: bool = True,
        statblocks: StatblockProvider | None = None,
    ) -> None:
        super().__init__(
            markdown,
            name=name,
            id=id,
            classes=classes,
            parser_factory=parser_factory,
            open_links=open_links,
        )
        self.statblocks: StatblockProvider = statblocks or _default_statblocks()


class ArchiveApp(App[None]):
    """Minimal Archive TUI shell: renders a dossier page.

    :param page: The markdown page to render; defaults to the built-in
        sample. Baked vault pages (WO-4/WO-7) hand their content in here.
    :param resolver: The wikilink known-target resolver; defaults to the
        sample page's known entities.
    :param statblocks: The live statblock provider for pages whose
        ``{statblock}`` fences carry no baked body; defaults to the sample
        provider.
    """

    CSS = """
    Screen { background: $background; color: $foreground; }
    #page { padding: 1 4; }

    .statblock {
        border: double $primary; padding: 0 2; margin: 1 0;
        background: $panel; width: auto;
    }
    .absence {
        border: heavy $error; color: $error; padding: 0 1; margin: 1 0;
        text-style: bold; width: auto;
    }
    .narrative {
        border-left: thick $accent; padding: 0 2; margin: 1 0;
        background: $panel; width: auto;
    }
    .paoh { border: round $panel; padding: 0 1; margin: 1 0; width: auto; }

    #status { dock: bottom; height: 1; background: $panel; color: $accent; padding: 0 1; }
    """

    def __init__(
        self,
        *,
        page: str | None = None,
        resolver: WikilinkResolver | None = None,
        statblocks: StatblockProvider | None = None,
    ) -> None:
        super().__init__()
        self._page = page if page is not None else SAMPLE_COUNTY_PAGE
        self._resolver = resolver or known_target_resolver(KNOWN_ENTITIES)
        self._statblocks = statblocks or _default_statblocks()

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="page"):
            yield BabylonMarkdown(
                self._page,
                parser_factory=make_parser_factory(self._resolver),
                open_links=False,
                id="dossier",
                statblocks=self._statblocks,
            )
        yield Label("status: — (click a link)", id="status")
        yield Footer()

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Route a clicked link's href through the ``babylon://`` router.

        :param event: the ``LinkClicked`` message.
        """
        status = self.query_one("#status", Label)
        try:
            target = parse_babylon_uri(event.href)
        except InvalidBabylonUri as exc:
            status.update(f"status: invalid link — {exc}")
            return
        marker = "REDLINK" if target.redlink else target.kind
        status.update(f"status: {target.entity_id} [{marker}]")


app = ArchiveApp()
"""Module-level instance — ``pytest-textual-snapshot`` resolves the app path
relative to the test file, so the launcher fixture imports this directly."""

if __name__ == "__main__":
    app.run()
