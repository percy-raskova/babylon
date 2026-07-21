"""The Archive TUI shell: boots into the campaign lobby, or a sample page.

Demonstrates the WO-5 shell wired together — the ksbc theme, the fenced
directive dispatch, the wikilink content spans, and the ``babylon://``
router — on a small sample page rather than any live projection data (that
wiring is WO-3/WO-7). Headless-runnable via ``App.run_test()``.

Program v1.0.0 Unit C2 adds the Screen-mode boot flow: lobby -> briefing ->
campaign shell. ``ArchiveApp(campaign_menu=..., campaign_loader=...)`` pushes
:class:`~babylon.tui.campaign_menu.LobbyScreen` on mount; once it dismisses
with a chosen campaign UUID, ``campaign_loader`` (the structural
``CampaignLoader`` seam, fulfilled for real by
:mod:`babylon.game.session`'s composition-root factories) boots or resumes
that exact campaign, :class:`BriefingScreen` shows its vault-baked Scenario
Briefing, and dismissing THAT reveals the campaign shell — the very same
dossier/breadcrumbs/status widgets ``compose()`` always mounts, now reading
the live campaign's own vault instead of the built-in demo page. With no
``campaign_menu`` given (the default), none of this runs: ``ArchiveApp()``
boots straight into the sample dossier exactly as before — every existing
caller/test is unaffected.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, Protocol, runtime_checkable
from uuid import UUID, uuid4

from markdown_it import MarkdownIt
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label, Markdown

from babylon.tui.campaign_menu import CampaignMenu, LobbyScreen
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


@runtime_checkable
class TickOutcome(Protocol):
    """Structural shape of one :meth:`CampaignHandle.advance_tick` result.

    :class:`~babylon.game.session.TickAdvanceResult` satisfies this
    structurally (it also carries ``world``/``events``/
    ``determinism_hash``, which this seam doesn't need) — the WO-37 trick,
    no import in either direction.
    """

    @property
    def tick(self) -> int:
        """The committed tick just reached."""
        ...

    @property
    def paused(self) -> bool:
        """Whether the pacing driver's pause predicate fired this tick."""
        ...


@runtime_checkable
class CampaignHandle(Protocol):
    """Structural seam: one booted/resumed live campaign (Program v1.0.0 Unit C2).

    :class:`~babylon.game.session.GameSession` satisfies this without
    either module importing the other: ``babylon.tui`` never imports
    ``babylon.game``/``babylon.engine``/``babylon.persistence`` (the
    import-linter contract); the composition root hands :class:`ArchiveApp`
    a real ``GameSession`` where this seam expects one.
    """

    @property
    def session_id(self) -> UUID:
        """The campaign's identity — the same UUID the lobby chose."""
        ...

    @property
    def tick(self) -> int:
        """The last committed tick."""
        ...

    def read_page(self, subject: str) -> str | None:
        """Read one baked vault page for this campaign (see :data:`PageSource`)."""
        ...

    def advance_tick(self) -> TickOutcome:
        """Resolve exactly one further tick."""
        ...


CampaignLoader = Callable[[UUID], CampaignHandle]
"""The lobby's boot-or-resume seam: a chosen campaign UUID -> a live
:class:`CampaignHandle`. Fulfilled for real by :mod:`babylon.game.session`'s
composition-root factories (:func:`~babylon.game.session.
create_new_campaign` / :func:`~babylon.game.session.resume_campaign`) in
the ``babylon play`` composition root — ``babylon.tui`` calls only through
this seam, never those factories directly."""

#: The sample page's own subject — the nav shell's seed position, and
#: (Unit C2) the live campaign's own home dossier subject too: Wayne County
#: is the only scenario wired today (ruling 3, "Wayne stays in lobby").
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


class BriefingScreen(Screen[bool]):
    """The freshly-booted campaign's Scenario Briefing dossier (Unit C2).

    Renders the vault-baked briefing page
    (:func:`~babylon.projection.vault.render_briefing.render_briefing`,
    baked via ``VaultMaterializer.bake_briefing`` — WO-35's previously-
    orphaned renderer, wired by the composition root at boot/resume time)
    through the same :class:`BabylonMarkdown` dialect every other dossier
    page uses. The briefing's own ``{statblock}`` fence carries its numbers
    baked directly into the fence body (Constitution III.13), so this
    screen needs no live statblock provider. Dismisses ``True`` when the
    player presses "Begin Operation" — there is no separate decline action
    short of leaving the lobby entirely (its own ``escape`` binding),
    matching design canon's no-dead-ends principle.

    :param markdown: the briefing page's rendered markdown, or its honest
        absence page if the composition root has not baked one yet
        (Constitution III.11).
    """

    BINDINGS = [Binding("enter", "begin", "Begin Operation")]

    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="briefing-page"):
            yield BabylonMarkdown(self._markdown, open_links=False, id="briefing-dossier")
        yield Label("press enter to begin the operation", id="briefing-status")
        yield Footer()

    def action_begin(self) -> None:
        """``enter``: dismiss with ``True`` — the operation begins."""
        self.dismiss(True)


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
        to the sample-only source. Ignored once a live campaign boots
        (Unit C2): :attr:`_pages` is then replaced by the booted
        :class:`CampaignHandle`'s own :meth:`~CampaignHandle.read_page`.
    :param nav: The navigation shell; defaults to a fresh in-memory one
        (state dies with the process — the honest no-database default).
    :param campaign_menu: The lobby's controller over the campaign catalog
        seam (Unit C2); when given, :meth:`on_mount` pushes
        :class:`~babylon.tui.campaign_menu.LobbyScreen` first instead of
        going straight to the sample/live dossier. ``None`` (the default)
        preserves the pre-Unit-C2 single-page boot exactly.
    :param campaign_loader: The boot-or-resume seam (:data:`CampaignLoader`)
        consuming the lobby's chosen campaign UUID; REQUIRED whenever
        ``campaign_menu`` is given (a lobby with no way to boot its choice
        is a broken wiring, not a valid configuration — raised loudly).
    """

    COMMANDS = App.COMMANDS | {EntityNavigatorProvider}

    BINDINGS = [
        Binding("ctrl+o", "jump_back", "Back"),
        Binding("ctrl+i", "jump_forward", "Forward"),
        # show=False: keeps the golden dossier-shell snapshot's Footer row
        # byte-identical (layout churn is a merge-time ceremony, not this
        # unit's) — the key is fully live, just not advertised in chrome.
        Binding("t", "advance_tick", "Advance Tick", show=False),
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
        campaign_menu: CampaignMenu | None = None,
        campaign_loader: CampaignLoader | None = None,
    ) -> None:
        super().__init__()
        if campaign_menu is not None and campaign_loader is None:
            msg = (
                "ArchiveApp: campaign_menu was given but no campaign_loader — "
                "the lobby would have no way to boot the campaign it chooses"
            )
            raise ValueError(msg)
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
        self._campaign_menu = campaign_menu
        self._campaign_loader = campaign_loader
        self.campaign: CampaignHandle | None = None
        """The live, booted campaign (Unit C2) — ``None`` until the lobby
        dismisses and :func:`CampaignLoader` returns one; stays ``None``
        forever in the no-``campaign_menu`` boot path."""

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"
        if self._campaign_menu is not None:
            self.push_screen(LobbyScreen(self._campaign_menu), callback=self._on_campaign_chosen)
            return
        if self._page == SAMPLE_COUNTY_PAGE and self.nav.current is None:
            # Seed the jumplist with the sample page's own subject so the
            # first outbound jump has somewhere to Ctrl-O back to.
            self.nav.visit(_SAMPLE_SUBJECT)
            self._refresh_breadcrumbs()

    async def _on_campaign_chosen(self, campaign_id: UUID | None) -> None:
        """``LobbyScreen`` dismissed: boot/resume the chosen campaign.

        :param campaign_id: the campaign the lobby dismissed with, or
            ``None`` if the player left without choosing (escape) — there
            is no campaign shell to show, so the app exits rather than
            revealing an empty/stale default screen.
        """
        if campaign_id is None:
            self.exit()
            return
        if self._campaign_loader is None:
            # Unreachable via any public constructor path — __init__ raises
            # first whenever campaign_menu is given without a loader — but
            # never silently swallow a violated invariant (Constitution
            # III.11).
            msg = "ArchiveApp: a campaign was chosen but no campaign_loader is wired"
            raise RuntimeError(msg)
        campaign = self._campaign_loader(campaign_id)
        self.campaign = campaign
        self._pages = campaign.read_page
        briefing_subject = f"briefing/{campaign_id}"
        page = self._pages(briefing_subject)
        markdown = page if page is not None else _absence_page(briefing_subject)
        self.push_screen(BriefingScreen(markdown), callback=self._on_briefing_dismissed)

    async def _on_briefing_dismissed(self, _began: bool | None) -> None:
        """``BriefingScreen`` dismissed: reveal the campaign shell.

        Navigates to the live campaign's own home dossier subject — Wayne
        County's (ruling 3: "Wayne stays in lobby", the only scenario wired
        today) — sourced from the campaign's own vault via :attr:`_pages`,
        already reassigned by :meth:`_on_campaign_chosen`.

        :param _began: always ``True`` in practice (``BriefingScreen`` only
            ever dismisses via its "Begin Operation" action); typed
            ``bool | None`` to match ``Screen.dismiss``'s own generic
            signature (unused either way — there is no decline branch).
        """
        await self._navigate(_SAMPLE_SUBJECT)

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

    async def action_advance_tick(self) -> None:
        """``t``: advance the live campaign one tick (Program v1.0.0 Unit C2).

        Emits the intent through :attr:`campaign`'s ``advance_tick`` seam
        (fulfilled for real by
        :meth:`~babylon.game.session.GameSession.advance_tick`); a loud
        status note, never a silent no-op, when no live campaign is
        attached yet (Constitution III.11).
        """
        status = self.query_one("#status", Label)
        if self.campaign is None:
            status.update("status: no live campaign attached — nothing to advance")
            return
        result = self.campaign.advance_tick()
        subject = self.nav.current
        if subject is not None:
            await self._navigate(subject, record=False)
        paused_marker = " [PAUSED]" if result.paused else ""
        status.update(f"status: tick {result.tick}{paused_marker}")

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
