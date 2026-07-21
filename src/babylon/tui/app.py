"""Minimal Archive TUI shell: boots, renders a sample county dossier page.

Demonstrates the WO-5 shell wired together — the ksbc theme, the fenced
directive dispatch, the wikilink content spans, and the ``babylon://``
router — on a small sample page rather than any live projection data (that
wiring is WO-3/WO-7). Headless-runnable via ``App.run_test()``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final
from uuid import uuid4

from markdown_it import MarkdownIt
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Footer, Label, Markdown

from babylon.tui.directives import BabylonFence, StatblockProvider
from babylon.tui.dispatch import (
    fixture_known_entities,
    fixture_statblock_providers,
    kind_dispatch_statblocks,
)
from babylon.tui.nav import InMemoryNavPersistence, NavShell, subject_for
from babylon.tui.palette import EntityNavigated, EntityNavigatorProvider
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


PageSource = Callable[[str], "str | None"]
"""The page-content seam (WO-47): subject id → markdown page, or ``None``
for a subject with no baked dossier. WO-49/WO-50 wire a vault-backed
source; the default below serves only the built-in sample."""

#: The sample page's own subject — the nav shell's seed position.
_SAMPLE_SUBJECT: Final = "county/26163"

#: How many trail entries the breadcrumb bar displays (newest last).
_BREADCRUMB_DISPLAY: Final = 5


def _sample_page_source(subject: str) -> str | None:
    """Serve the built-in sample dossier and nothing else — honestly.

    :param subject: the requested subject id.
    :returns: the sample page for its own subject, else ``None``.
    """
    return SAMPLE_COUNTY_PAGE if subject == _SAMPLE_SUBJECT else None


def _absence_page(subject: str) -> str:
    """A loud, visible page for a subject with no baked dossier.

    Constitution III.11: absence renders as absence — never a blank pane,
    never fabricated content.

    :param subject: the subject id that has no page.
    :returns: the absence page markdown.
    """
    return f"# {subject}\n\n> **ABSENT** — no dossier exists for `{subject}` yet.\n"


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
    """The Archive TUI shell: renders dossier pages with a nav shell.

    WO-47 wires navigation onto the keel: ``Ctrl-O``/``Ctrl-I`` walk the
    jumplist, a breadcrumb bar shows the trail, the command palette's
    fuzzy switcher (WO-28's :class:`~babylon.tui.palette.
    EntityNavigatorProvider`) opens pages, and following a known wikilink
    navigates instead of only reporting. Navigation state persists through
    the :class:`~babylon.tui.nav.NavShell`'s seam — in-memory by default,
    ``babylon_meta``-backed when the composition root injects the store.

    :param page: The markdown page to render; defaults to the built-in
        sample. Baked vault pages (WO-4/WO-7) hand their content in here.
    :param resolver: The wikilink known-target resolver; defaults to the
        sample page's known entities.
    :param statblocks: The live statblock provider for pages whose
        ``{statblock}`` fences carry no baked body; defaults to the sample
        provider.
    :param known_entities: The palette/redlink known-entity set; defaults
        to the sample set (:data:`KNOWN_ENTITIES`).
    :param pages: The page-content source navigation reads from; defaults
        to the sample-only source.
    :param nav: The navigation shell; defaults to a fresh in-memory one
        (state dies with the process — the honest no-database default).
    """

    COMMANDS = App.COMMANDS | {EntityNavigatorProvider}

    BINDINGS = [
        Binding("ctrl+o", "jump_back", "Back"),
        Binding("ctrl+i", "jump_forward", "Forward"),
    ]

    CSS = """
    Screen { background: $background; color: $foreground; }
    #page { padding: 1 4; }

    #breadcrumbs { dock: top; height: 1; background: $panel; color: $foreground; padding: 0 1; }

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
        known_entities: frozenset[str] | None = None,
        pages: PageSource | None = None,
        nav: NavShell | None = None,
    ) -> None:
        super().__init__()
        self._page = page if page is not None else SAMPLE_COUNTY_PAGE
        self.known_entities: frozenset[str] = (
            known_entities if known_entities is not None else KNOWN_ENTITIES
        )
        self._resolver = resolver or known_target_resolver(self.known_entities)
        self._statblocks = statblocks or _default_statblocks()
        self._pages: PageSource = pages or _sample_page_source
        self.nav: NavShell = nav or NavShell(
            campaign_id=uuid4(), persistence=InMemoryNavPersistence()
        )

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"
        if self._page == SAMPLE_COUNTY_PAGE and self.nav.current is None:
            # Seed the jumplist with the sample page's own subject so the
            # first outbound jump has somewhere to Ctrl-O back to.
            self.nav.visit(_SAMPLE_SUBJECT)
            self._refresh_breadcrumbs()

    def compose(self) -> ComposeResult:
        yield Label("", id="breadcrumbs")
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

    def _refresh_breadcrumbs(self) -> None:
        """Render the trail's newest entries into the breadcrumb bar."""
        crumbs = self.nav.trail.entries[-_BREADCRUMB_DISPLAY:]
        self.query_one("#breadcrumbs", Label).update(" › ".join(crumbs))

    async def _navigate(self, subject: str, *, record: bool = True) -> None:
        """Show ``subject``'s page (or its loud absence page).

        :param subject: the subject id to open.
        :param record: whether this is a new jump (recorded in the
            jumplist and trail) or a jumplist walk (already recorded).
        """
        page = self._pages(subject)
        document = page if page is not None else _absence_page(subject)
        await self.query_one("#dossier", BabylonMarkdown).update(document)
        if record:
            self.nav.visit(subject)
        self._refresh_breadcrumbs()
        marker = " [ABSENT]" if page is None else ""
        self.query_one("#status", Label).update(f"status: {subject}{marker}")

    async def action_jump_back(self) -> None:
        """``Ctrl-O``: walk back one jumplist step, if there is one."""
        subject = self.nav.back()
        if subject is not None:
            await self._navigate(subject, record=False)

    async def action_jump_forward(self) -> None:
        """``Ctrl-I``: walk forward one jumplist step, if there is one."""
        subject = self.nav.forward()
        if subject is not None:
            await self._navigate(subject, record=False)

    async def on_entity_navigated(self, event: EntityNavigated) -> None:
        """Open the page a palette hit chose.

        :param event: the palette's navigation request.
        """
        await self._navigate(subject_for(event.target))

    async def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Follow a clicked link: navigate if known, report if not.

        :param event: the ``LinkClicked`` message.
        """
        status = self.query_one("#status", Label)
        try:
            target = parse_babylon_uri(event.href)
        except InvalidBabylonUri as exc:
            status.update(f"status: invalid link — {exc}")
            return
        if target.redlink:
            status.update(f"status: {target.entity_id} [REDLINK]")
            return
        await self._navigate(subject_for(target))


app = ArchiveApp()
"""Module-level instance — ``pytest-textual-snapshot`` resolves the app path
relative to the test file, so the launcher fixture imports this directly."""

if __name__ == "__main__":
    app.run()
