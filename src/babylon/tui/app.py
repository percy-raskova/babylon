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

Unit C3 adds the paced tick driver's own structural seam
(:class:`PacedDriverHandle`) alongside :class:`CampaignHandle`: when the
composition root also supplies ``driver_factory``, the campaign shell's
``t``/``r``/``a`` bindings route through
:mod:`~babylon.game.pacing`'s :class:`~babylon.game.pacing.PacedTickDriver`
(explicit single-tick advance, run-until-paused auto-play, and the
autopause-ack flow) instead of calling :attr:`ArchiveApp.campaign` directly
— never a hard import of ``babylon.game``, only this module's own Protocol.
With no ``driver_factory`` given (the default), :attr:`ArchiveApp.driver`
stays ``None`` and ``t`` behaves exactly as it did before this unit —
existing callers/tests are unaffected.

Program v1.0.0 Unit U1 (live-campaign navigation) closes the gap left by
Unit C2's own ``known_entities``/``_resolver`` docstrings: booting a live
campaign used to swap :attr:`ArchiveApp._pages` but never the demo
:data:`KNOWN_ENTITIES` fixture set, so wikilink classification and the
command palette (:class:`~babylon.tui.palette.EntityNavigatorProvider`)
kept speaking the demo entities on every real ``babylon play`` boot —
real baked pages were unreachable except by direct ``Ctrl-O``/``Ctrl-I``
jumplist replay. :meth:`CampaignHandle.known_subjects` is the new
enumeration seam; :meth:`ArchiveApp._on_campaign_chosen` rebuilds
``known_entities``/``_resolver`` from it right after swapping ``_pages``,
and every successful ``t``/``r`` tick advance re-scans it again (cheap
frozenset compare, skipped when unchanged) so pages baked mid-campaign
become navigable immediately. The demo (no-``campaign_menu``) boot path is
completely unaffected.

Program v1.0.0 T6 Unit U4 (the guided opening-arc overlay — not to be
confused with the earlier, unrelated "Unit U1" above) adds
``tutorial_steps``/``tutorial_progress_factory``: when both are given,
:meth:`ArchiveApp._on_campaign_chosen` builds this campaign's
:class:`~babylon.tui.tutorial_overlay.TutorialProgress` seam, and
:meth:`ArchiveApp._on_briefing_dismissed` mounts a
:class:`~babylon.tui.tutorial_overlay.TutorialOverlay` over the freshly-
revealed campaign shell IFF that seam is not ``None`` (the composition
root's own new-vs-resumed gating — see ``babylon.cli.play``). Every
committed-tick action (``t``/``r``/``a``) and every navigation event
(``Ctrl-O``/``Ctrl-I``/palette pick/wikilink follow — all of which route
through :meth:`ArchiveApp._navigate`) re-polls the mounted overlay via
:meth:`ArchiveApp._refresh_tutorial_progress`. With no
``tutorial_progress_factory`` given (the default), nothing here runs at
all — every pre-Unit-U4 caller/test, and the demo boot path, is completely
unaffected.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Final, Protocol, runtime_checkable
from uuid import UUID, uuid4

from markdown_it import MarkdownIt
from textual import work
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
from babylon.tui.tutorial_overlay import TutorialOverlay, TutorialProgress, TutorialStepView
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

    def known_subjects(self) -> frozenset[str]:
        """Every subject id this campaign's vault has baked so far (Unit U1).

        Replaces the demo :data:`KNOWN_ENTITIES` fixture set once a live
        campaign boots — :meth:`ArchiveApp._on_campaign_chosen` reads this
        to rebuild :attr:`ArchiveApp.known_entities`/``_resolver`` against
        the REAL vault instead of the built-in fixture set, so wikilink
        classification and the command palette speak the live campaign's
        own baked pages.
        """
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


@runtime_checkable
class PacedDriverHandle(Protocol):
    """Structural seam: the paced tick driver (Program v1.0.0 Unit C3).

    :class:`~babylon.game.pacing.PacedTickDriver` satisfies this without
    ``babylon.tui`` importing ``babylon.game``/``babylon.engine`` — the
    same WO-37 trick :class:`CampaignHandle` already uses, one layer up.
    Deliberately narrow: only primitives (``bool``/``str``/``None``) cross
    this boundary, so the UI never needs
    :class:`~babylon.kernel.event_bus.Event` or
    :class:`~babylon.models.enums.events.GameOutcome` to render a status
    line (:attr:`~babylon.game.pacing.PacedTickDriver.pause_summary` /
    ``lock_reason`` already format themselves; a ``GameOutcome`` IS a
    ``str`` — it's a ``StrEnum`` — so it satisfies ``lock_reason: str |
    None`` here with no cast).
    """

    @property
    def locked(self) -> bool:
        """``True`` once the endgame lock has engaged — permanent."""
        ...

    @property
    def lock_reason(self) -> str | None:
        """The recognized terminal outcome's name, or ``None`` while unlocked."""
        ...

    @property
    def awaiting_ack(self) -> bool:
        """``True`` while a tick's autopause is unacknowledged."""
        ...

    @property
    def busy(self) -> bool:
        """``True`` while a previous advance on this SAME driver is still
        in flight — a Textual worker's cancellation cannot actually stop
        an executor thread already running underneath it (see
        :mod:`babylon.game.pacing`'s Re-entrancy note), so the UI must
        check this BEFORE starting a second overlapping advance rather
        than relying on ``@work``'s own ``exclusive`` cancellation."""
        ...

    @property
    def pause_summary(self) -> str | None:
        """The pending autopause's UI-safe one-liner, or ``None``."""
        ...

    def advance_once(self) -> TickOutcome:
        """Resolve exactly one further tick (the Unit C2 binding's seam)."""
        ...

    def run_until_paused(self) -> Sequence[TickOutcome]:
        """Advance repeatedly until an autopause or the endgame lock."""
        ...

    def acknowledge_pause(self) -> None:
        """Clear a pending autopause, permitting the next advance."""
        ...


DriverFactory = Callable[[CampaignHandle], PacedDriverHandle]
"""The booted campaign's pacing-driver seam: a live :class:`CampaignHandle`
-> a :class:`PacedDriverHandle` wrapping it. Fulfilled for real by
:func:`~babylon.game.pacing.paced_driver_for_session` in the ``babylon
play`` composition root (the SAME concrete object satisfies both
``CampaignHandle`` and whatever ``paced_driver_for_session`` actually
needs — the composition root holds the real
:class:`~babylon.game.session.GameSession`, this module only ever sees it
through the narrower seam types)."""

TutorialProgressFactory = Callable[
    [CampaignHandle, "PacedDriverHandle | None", Callable[[], "str | None"]],
    "TutorialProgress | None",
]
"""The booted campaign's tutorial-progress seam (Program v1.0.0 T6, Unit U4)
— one layer up from :data:`DriverFactory`, same shape. Takes the just-booted
:class:`CampaignHandle`, the just-built :class:`PacedDriverHandle` (or
``None`` when no ``driver_factory`` was wired), and a zero-arg callable
reading :attr:`ArchiveApp.nav`'s current subject at call time; returns
``None`` to mean "the tutorial should not show for this campaign" — the
composition root's own new-vs-resumed gating decision (see
``babylon.cli.play``'s own docstring for the honest first-session heuristic
it uses), in which case :meth:`ArchiveApp._on_briefing_dismissed` never
mounts a :class:`~babylon.tui.tutorial_overlay.TutorialOverlay` at all."""

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
        to the sample set (:data:`KNOWN_ENTITIES`). Ignored once a live
        campaign boots (Unit U1): rebuilt from the booted
        :class:`CampaignHandle`'s own :meth:`~CampaignHandle.known_subjects`
        instead, same shape as ``pages`` below.
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
    :param driver_factory: The paced-driver seam (:data:`DriverFactory`,
        Unit C3); when given, :meth:`_on_campaign_chosen` wraps the just-
        booted campaign in a :class:`PacedDriverHandle` and every
        subsequent ``t``/``r``/``a`` press routes through it instead of
        :attr:`campaign` directly. REQUIRED whenever ``campaign_loader`` is
        absent (there would be no campaign to ever wrap — raised loudly,
        same pattern as ``campaign_menu``/``campaign_loader``). ``None``
        (the default) leaves :attr:`driver` ``None`` forever — the pre-
        Unit-C3 behavior, unchanged.
    :param tutorial_steps: The guided opening-arc step sequence to render
        (Program v1.0.0 T6, Unit U4) — MUST be the exact same sequence
        ``tutorial_progress_factory`` builds its evaluator against (same
        length, same order; see :data:`TutorialProgressFactory`). ``None``
        (the default) never mounts a tutorial overlay, unchanged from every
        pre-Unit-U4 caller/test.
    :param tutorial_progress_factory: The tutorial-progress seam
        (:data:`TutorialProgressFactory`, Unit U4); when given (and
        ``tutorial_steps`` too — REQUIRED together, raised loudly otherwise,
        same pattern as ``campaign_menu``/``campaign_loader``),
        :meth:`_on_campaign_chosen` builds this campaign's
        :class:`~babylon.tui.tutorial_overlay.TutorialProgress`, and
        :meth:`_on_briefing_dismissed` mounts a
        :class:`~babylon.tui.tutorial_overlay.TutorialOverlay` over the
        campaign shell IFF the factory did not return ``None``. ``None``
        (the default) never mounts one — the pre-Unit-U4 behavior,
        unchanged.
    """

    COMMANDS = App.COMMANDS | {EntityNavigatorProvider}

    BINDINGS = [
        Binding("ctrl+o", "jump_back", "Back"),
        Binding("ctrl+i", "jump_forward", "Forward"),
        # show=False on this whole trio: keeps the golden dossier-shell
        # snapshot's Footer row byte-identical (layout churn is a merge-time
        # ceremony, not this unit's) — every key is fully live, just not
        # advertised in chrome.
        Binding("t", "advance_tick", "Advance Tick", show=False),
        Binding("r", "run_until_paused", "Run", show=False),
        Binding("a", "acknowledge_pause", "Acknowledge", show=False),
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
        driver_factory: DriverFactory | None = None,
        tutorial_steps: Sequence[TutorialStepView] | None = None,
        tutorial_progress_factory: TutorialProgressFactory | None = None,
    ) -> None:
        super().__init__()
        if campaign_menu is not None and campaign_loader is None:
            msg = (
                "ArchiveApp: campaign_menu was given but no campaign_loader — "
                "the lobby would have no way to boot the campaign it chooses"
            )
            raise ValueError(msg)
        if driver_factory is not None and campaign_loader is None:
            msg = (
                "ArchiveApp: driver_factory was given but no campaign_loader — "
                "there would never be a booted campaign to wrap in a driver"
            )
            raise ValueError(msg)
        if tutorial_progress_factory is not None and tutorial_steps is None:
            msg = (
                "ArchiveApp: tutorial_progress_factory was given but no tutorial_steps — "
                "there would be nothing for a TutorialOverlay to render"
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
        self._driver_factory = driver_factory
        self._tutorial_steps = tutorial_steps
        self._tutorial_progress_factory = tutorial_progress_factory
        self.campaign: CampaignHandle | None = None
        """The live, booted campaign (Unit C2) — ``None`` until the lobby
        dismisses and :func:`CampaignLoader` returns one; stays ``None``
        forever in the no-``campaign_menu`` boot path."""
        self.driver: PacedDriverHandle | None = None
        """The campaign's paced tick driver (Unit C3) — ``None`` until
        :attr:`campaign` boots AND a ``driver_factory`` was given; stays
        ``None`` forever in the no-``driver_factory`` boot path (``t``
        then falls back to calling :attr:`campaign` directly, unchanged
        from before this unit)."""
        self._tutorial_progress: TutorialProgress | None = None
        """This campaign's tutorial-progress seam (Unit U4) — ``None``
        until :attr:`campaign` boots AND ``tutorial_progress_factory``
        both was given AND itself returned non-``None`` (its own new-vs-
        resumed gating); stays ``None`` forever otherwise."""
        self._tutorial_overlay: TutorialOverlay | None = None
        """The mounted :class:`~babylon.tui.tutorial_overlay.TutorialOverlay`
        (Unit U4) — ``None`` until :meth:`_on_briefing_dismissed` mounts one
        (only when :attr:`_tutorial_progress` is not ``None``); stays
        ``None`` forever otherwise."""

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
        self.driver = self._driver_factory(campaign) if self._driver_factory is not None else None
        if self._tutorial_progress_factory is not None:
            self._tutorial_progress = self._tutorial_progress_factory(
                campaign, self.driver, lambda: self.nav.current
            )
        self._pages = campaign.read_page
        self._refresh_known_entities(campaign)
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
        await self._mount_tutorial_overlay_if_active()

    async def _mount_tutorial_overlay_if_active(self) -> None:
        """Mount :attr:`_tutorial_overlay` over the freshly-revealed campaign
        shell, IFF :attr:`_tutorial_progress` is not ``None`` (Unit U4).

        A no-op with no ``tutorial_progress_factory`` wired, or when the
        factory itself decided not to show the tutorial for THIS campaign
        (its own new-vs-resumed gating) — every pre-Unit-U4 caller/test is
        unaffected either way.
        """
        if self._tutorial_progress is None or self._tutorial_steps is None:
            return
        overlay = TutorialOverlay(self._tutorial_steps, self._tutorial_progress)
        self._tutorial_overlay = overlay
        await self.mount(overlay)

    def _refresh_tutorial_progress(self) -> None:
        """Re-poll the mounted overlay's current step (Unit U4) — called
        at the tail of every committed-tick action and navigation event
        (:meth:`action_advance_tick`, :meth:`action_run_until_paused`,
        :meth:`action_acknowledge_pause`, :meth:`_navigate`). A no-op with
        no overlay mounted.
        """
        if self._tutorial_overlay is not None:
            self._tutorial_overlay.check_progress()

    def compose(self) -> ComposeResult:
        yield Label("", id="breadcrumbs")
        with VerticalScroll(id="page"):
            yield BabylonMarkdown(
                self._page,
                parser_factory=self._current_parser,
                open_links=False,
                id="dossier",
                statblocks=self._statblocks,
            )
        yield Label("status: — (click a link)", id="status")
        yield Footer()

    def _current_parser(self) -> MarkdownIt:
        """The dossier's zero-arg ``parser_factory``, rebuilt fresh every call.

        ``BabylonMarkdown``/``Markdown.update()`` invokes its
        ``parser_factory`` fresh on every render (never caching the
        ``MarkdownIt`` instance), but a plain ``make_parser_factory(self.
        _resolver)`` closure captures :attr:`_resolver`'s VALUE at
        :meth:`compose` time — swapping the attribute later (Unit U1's
        live-campaign known-set refresh) would never reach an already-built
        closure. Passing this bound method instead means every render reads
        :attr:`_resolver` fresh, so the very next navigation after a swap
        classifies links against the live set — the same shape the existing
        :attr:`_pages` swap already relies on.

        :returns: a freshly configured parser.
        """
        return make_parser_factory(self._resolver)()

    def _refresh_known_entities(self, campaign: CampaignHandle) -> None:
        """Recompute :attr:`known_entities`/``_resolver`` from the live
        campaign's vault, IF the baked subject set actually changed (Unit
        U1). Pages bake once per committed tick, so most ticks contribute
        no new subjects — comparing the frozensets first skips an
        unnecessary resolver rebuild.

        :param campaign: the live campaign to re-scan.
        """
        subjects = campaign.known_subjects()
        if subjects == self.known_entities:
            return
        self.known_entities = subjects
        self._resolver = known_target_resolver(self.known_entities)

    def _refresh_breadcrumbs(self) -> None:
        """Render the trail's newest entries into the breadcrumb bar.

        Tolerant of a transient-absent breadcrumb widget. This runs from
        the briefing-dismiss ``call_next`` callback via :meth:`_navigate` —
        a window in which the campaign shell's compose can still be
        settling under concurrent load (the source of the CI-only
        ``NoMatches`` this guard closes). ``#breadcrumbs`` is yielded
        unconditionally in :meth:`compose`, so an empty query here is only
        ever a transition artifact, never a structural absence — and the
        bar is chrome (the tutorial-BDD transcript asserts semantic text,
        never chrome, per the T6 ruling), so a skipped repaint self-heals
        on the next navigation. ``#dossier``/``#status`` deliberately stay
        loud ``query_one`` calls in :meth:`_navigate`: those ARE asserted
        behavior. This never masks a real absence — only the transition
        window can empty a query on an unconditionally-composed widget.
        """
        bar = self.query("#breadcrumbs")
        if not bar:
            return
        crumbs = self.nav.trail.entries[-_BREADCRUMB_DISPLAY:]
        bar.first(Label).update(" › ".join(crumbs))

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
        self._refresh_tutorial_progress()

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
        """``t``: advance the live campaign one tick (Program v1.0.0 Unit
        C2; routed through :attr:`driver` when Unit C3 wired one).

        With no :attr:`driver` (the pre-Unit-C3 default), emits the intent
        through :attr:`campaign`'s ``advance_tick`` seam directly, exactly
        as before. With a :attr:`driver` wired, its own
        locked/awaiting-ack/busy refusals surface as a loud status note
        instead of a raised exception reaching the UI — a player mashing
        ``t`` past an autopause (or while ``r``'s worker is still running
        in the background) sees WHY nothing moved, not a crash or silence
        (Constitution III.11).

        Unit U1: also re-scans :attr:`campaign`'s vault via
        :meth:`_refresh_known_entities` after a successful advance, so a
        page baked THIS tick becomes navigable/known immediately, not only
        on the next lobby boot.
        """
        status = self.query_one("#status", Label)
        if self.campaign is None:
            status.update("status: no live campaign attached — nothing to advance")
            return
        if self.driver is not None:
            if self.driver.locked:
                status.update(f"status: campaign ended — {self.driver.lock_reason}")
                return
            if self.driver.awaiting_ack:
                status.update(
                    f"status: autopause pending ({self.driver.pause_summary}) "
                    "— press 'a' to acknowledge"
                )
                return
            if self.driver.busy:
                status.update("status: a run is already in progress — please wait")
                return
            result: TickOutcome = self.driver.advance_once()
        else:
            result = self.campaign.advance_tick()
        self._refresh_known_entities(self.campaign)
        subject = self.nav.current
        if subject is not None:
            await self._navigate(subject, record=False)
        paused_marker = " [PAUSED]" if result.paused else ""
        status.update(f"status: tick {result.tick}{paused_marker}")
        self._refresh_tutorial_progress()

    @work()
    async def action_run_until_paused(self) -> None:
        """``r``: auto-advance through uneventful ticks until an autopause
        or the endgame lock (Program v1.0.0 Unit C3).

        A Textual worker (:func:`textual.work`, deliberately NOT
        ``exclusive`` — see :attr:`~PacedDriverHandle.busy`'s own
        docstring): :meth:`~babylon.game.pacing.PacedTickDriver.
        run_until_paused` is a blocking, potentially wall-clock-paced call
        (its own ``tick_delay``/``sleep``), so it runs via
        :func:`asyncio.to_thread` — the UI keeps rendering while it works,
        and this coroutine resumes on the event loop once it returns, safe
        to touch widgets from directly. A SECOND ``r`` press while one run
        is still in flight starts a second worker Task that immediately
        sees :attr:`~PacedDriverHandle.busy` and refuses — cancelling the
        first worker instead (``exclusive=True``) would only abandon
        awaiting it; the executor thread underneath keeps running either
        way (cooperative-only cancellation), so refusing the SECOND press
        is the only choice that is actually honest about what is running.

        Unit U1: re-scans :attr:`campaign`'s vault via
        :meth:`_refresh_known_entities` once the run stops, same as ``t``.
        """
        status = self.query_one("#status", Label)
        if self.driver is None:
            status.update("status: no paced driver attached — nothing to run")
            return
        if self.driver.locked:
            status.update(f"status: campaign ended — {self.driver.lock_reason}")
            return
        if self.driver.awaiting_ack:
            status.update(
                f"status: autopause pending ({self.driver.pause_summary}) "
                "— press 'a' to acknowledge"
            )
            return
        if self.driver.busy:
            status.update("status: a run is already in progress — please wait")
            return
        results = await asyncio.to_thread(self.driver.run_until_paused)
        last = results[-1]
        if self.campaign is not None:
            self._refresh_known_entities(self.campaign)
        subject = self.nav.current
        if subject is not None:
            await self._navigate(subject, record=False)
        if self.driver.locked:
            status.update(
                f"status: ran to tick {last.tick} — campaign ended ({self.driver.lock_reason})"
            )
        elif self.driver.awaiting_ack:
            status.update(f"status: ran to tick {last.tick} [PAUSED] ({self.driver.pause_summary})")
        else:
            status.update(f"status: ran to tick {last.tick} (stopped at the run limit)")
        self._refresh_tutorial_progress()

    def action_acknowledge_pause(self) -> None:
        """``a``: acknowledge a pending autopause (Program v1.0.0 Unit C3),
        permitting the next ``t``/``r``.
        """
        status = self.query_one("#status", Label)
        if self.driver is None:
            status.update("status: no paced driver attached — nothing to acknowledge")
            return
        if not self.driver.awaiting_ack:
            status.update("status: no autopause pending to acknowledge")
            return
        self.driver.acknowledge_pause()
        status.update("status: autopause acknowledged — ready to advance")
        self._refresh_tutorial_progress()

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
