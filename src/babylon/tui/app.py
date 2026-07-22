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
:meth:`ArchiveApp._refresh_tutorial_progress` — as does, since Program 24 P8
("the tutorial learns the shell"), every pane switch (``1``-``4``,
:meth:`ArchiveApp.action_switch_view`) and every watchlist pin/unpin
(``p``, :meth:`ArchiveApp.action_toggle_pin`), the same trigger-path idiom
extended to the two new :class:`~babylon.game.tutorial.PaneShowing`/
:class:`~babylon.game.tutorial.PinnedInWatchlist` completion kinds. With no
``tutorial_progress_factory`` given (the default), nothing here runs at
all — every pre-Unit-U4 caller/test, and the demo boot path, is completely
unaffected.

Program 24 P5 (the bottom action bar) closes :data:`_ACTION_BAR_ABSENT`'s own
"feed wires in at Program 24 P2-P6" note: :meth:`ArchiveApp._refresh_action_bar`
paints the ``#action-bar`` pane with :meth:`CampaignHandle.verb_plate_view`'s
live :class:`~babylon.projection.verbs.view_models.VerbPlateView` (mirroring
:meth:`_refresh_dashboard`'s own projection-purity shape) on boot and on every
``t``/``r`` tick, and :meth:`ArchiveApp.action_issue_verb` (bound to ``F1``-``F9``,
see :data:`_VERB_ACTION_KEYS`) is the FIRST real write the player can make on
the world from this shell: an eligible verb reaches
:meth:`CampaignHandle.issue_verb`; an ineligible one shows its already-rendered
refusal without ever attempting the write. With no live :attr:`campaign` (the
demo boot path) or a composition root that declines to wire
:meth:`CampaignHandle.verb_plate_view`, the pane keeps its honest absence fence
— unaffected, same as every other pane's Program 24 P1 default.

Program 24 P6 (the right rail) wires :attr:`ArchiveApp.watchlist` — a
:class:`~babylon.tui.watchlist.WatchlistState` pin/unpin domain object,
persisted through :data:`~babylon.tui.watchlist.WatchlistPersistence` (the
``babylon_meta``-backed store the composition root already threads in as the
campaign catalog — the WO-37 structural trick) — to the ``#watchlist-rail``
pane P1 left painting its own honest "nothing pinned yet" fence.
:meth:`ArchiveApp.action_toggle_pin` (bound to ``p``) pins/unpins
:attr:`nav`'s current subject; :meth:`ArchiveApp._refresh_watchlist` stacks a
:func:`~babylon.tui.peek.peek` ``depth=0`` stat plate per pinned subject via
:func:`~babylon.tui.watchlist.render_watchlist`, resolving each id against
:attr:`ArchiveApp._subject_views` (:func:`_default_subject_views`'s
committed-fixture map by default — the same fixture-fed-until-a-live-per-
subject-projector-lands shape :func:`_default_statblocks` already carries).
A pin outside that map renders the rail's own named "no longer resolvable"
row rather than a crash or a silent drop (Constitution III.11).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from typing import Final, Protocol, runtime_checkable
from uuid import UUID, uuid4

from markdown_it import MarkdownIt
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Footer, Label, Markdown, Static

from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.preview import VERB_TO_ACTION_TYPE
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView, ProjectionRecord
from babylon.tui.campaign_menu import CampaignMenu, LobbyScreen
from babylon.tui.chronicle import (
    CHRONICLE_ROW_CEILING,
    ChronicleEvent,
    chronicle_stream,
    render_chronicle,
)
from babylon.tui.directives import BabylonFence, StatblockProvider
from babylon.tui.dispatch import (
    fixture_known_entities,
    fixture_statblock_providers,
    fixture_subject_views,
    kind_dispatch_statblocks,
)
from babylon.tui.nav import InMemoryNavPersistence, NavShell, subject_for
from babylon.tui.palette import EntityNavigated, EntityNavigatorProvider
from babylon.tui.router import InvalidBabylonUri, parse_babylon_uri
from babylon.tui.shell.views.dashboard_view import DashboardView
from babylon.tui.shell.views.map_view import MapView
from babylon.tui.shell.views.topology_view import TopologyView
from babylon.tui.theme import KSBC
from babylon.tui.tutorial_overlay import TutorialOverlay, TutorialProgress, TutorialStepView
from babylon.tui.verb_plate import render_verb_plate, verb_plate_title
from babylon.tui.watchlist import (
    InMemoryWatchlistPersistence,
    WatchlistPersistence,
    WatchlistState,
    load_watchlist,
    render_watchlist,
    save_watchlist,
    watchlist_title,
)
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


def _default_subject_views() -> Mapping[str, ProjectionRecord]:
    """The app's default peek-plate source: the committed fixtures, unwrapped.

    Program 24 P6: the right rail's watchlist stacks
    :func:`~babylon.tui.peek.peek` stat plates for its pinned subjects, which
    needs the actual :data:`ProjectionRecord` view-model, not the row form
    :func:`_default_statblocks` composes. :func:`~babylon.tui.dispatch.
    fixture_subject_views` is the sibling function that loads the SAME ten
    committed fixtures and hands back the models themselves. Fixture-fed
    today; a live campaign wires no override yet (no per-subject-id live
    projection producer exists tree-wide — the same honest gap
    :func:`_default_statblocks` already carries for the dossier's own
    statblocks in the real ``babylon play`` boot), so a pinned subject
    outside this committed set renders the watchlist's own honest "no
    longer resolvable" row (Constitution III.11) until that producer lands.

    :returns: the composed subject-id -> view-model mapping.
    """
    return fixture_subject_views()


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

    @property
    def chronicle(self) -> tuple[ChronicleEvent, ...]:
        """This tick's chronicle events, chronological (Program 24 P3).

        :attr:`~babylon.game.session.TickAdvanceResult.chronicle` satisfies this
        structurally — the same WO-37 trick this Protocol already uses for
        ``tick``/``paused``. :meth:`ArchiveApp._refresh_chronicle` appends this
        ONE tick's events onto its own running history; this seam never carries
        more than one tick's worth at a time.
        """
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

    def dashboard_view(self) -> EconomyView | None:
        """This campaign's live economy dashboard projection (Program 24 P2).

        Computed HOST-SIDE by the composition root
        (:func:`~babylon.projection.economy.project_economy`, called from
        :mod:`babylon.game.session` — never from ``babylon.tui``:
        ``project_economy`` needs the live graph/world this Protocol
        deliberately never exposes, and calling it from this module would be
        a projection-purity violation, the same import-linter contract
        :attr:`known_subjects`'s docstring already names). Handed to
        :class:`~babylon.tui.shell.views.dashboard_view.DashboardView` as a
        pure, frozen pydantic view model — the TUI only ever renders it,
        never builds it.

        :returns: the freshly-projected :class:`EconomyView`, or ``None``
            when this composition root chose not to wire a live projection
            (e.g. a test double standing in for a campaign with no vault) —
            :meth:`ArchiveApp._refresh_dashboard` then leaves the pane's
            existing honest-absence fence untouched (Constitution III.11),
            never a blank or fabricated repaint.
        """
        ...

    def endgame_status(self) -> EndgameStatus | None:
        """This campaign's live endgame-progress HUD status (Program 24 P4).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.endgame_status`, folding
        its own :class:`~babylon.engine.observers.endgame_detector.
        EndgameDetector` via :func:`~babylon.projection.endgame.
        endgame_status` — never from ``babylon.tui``: the detector needs the
        live world/graph this Protocol deliberately never exposes, the same
        projection-purity reasoning :attr:`dashboard_view`'s docstring
        already names). Handed to
        :class:`~babylon.tui.shell.views.dashboard_view.DashboardView` as a
        pure, frozen pydantic view model — the TUI only ever renders it,
        never computes it.

        :returns: the freshly-folded :class:`~babylon.projection.endgame.
            EndgameStatus`, or ``None`` when this composition root chose not
            to wire a live projection — :meth:`ArchiveApp._refresh_dashboard`
            then leaves the HUD's existing honest-absence fence untouched
            (Constitution III.11), same as :attr:`dashboard_view`.
        """
        ...

    def verb_plate_view(self) -> VerbPlateView | None:
        """This campaign's live verb-plate projection (Program 24 P5).

        Computed HOST-SIDE by the composition root
        (:func:`~babylon.projection.verbs.plate.build_verb_plate`, called from
        :meth:`~babylon.game.session.GameSession.verb_plate_view` — never
        from ``babylon.tui``: ``build_verb_plate`` needs the live graph this
        Protocol deliberately never exposes, the same projection-purity
        reasoning :attr:`dashboard_view`'s docstring already names). Handed
        to :func:`~babylon.tui.verb_plate.render_verb_plate` as a pure,
        frozen pydantic view model — the TUI only ever renders it, never
        builds it.

        :returns: the freshly-built :class:`~babylon.projection.verbs.
            view_models.VerbPlateView`, or ``None`` when this composition
            root chose not to wire a live plate (e.g. a test double, or a
            campaign whose graph carries no player-org pointer) —
            :meth:`ArchiveApp._refresh_action_bar` then leaves the bar's
            existing honest-absence fence untouched (Constitution III.11),
            never a blank or fabricated repaint.
        """
        ...

    def issue_verb(self, action_id: str) -> int:
        """Issue one player verb through the registry-gated write path (Program 24 P5).

        The action bar's real write-path seam — the FIRST time the player
        can act on the world from this shell. Computed HOST-SIDE (
        :meth:`~babylon.game.session.GameSession.issue_verb`, which composes
        :func:`~babylon.game.actions.player_driver.issue_action`'s
        agent-type/``LIVE``-status gate with :func:`~babylon.projection.
        verbs.submit.submit_verb`'s own affordability gate) — never from
        ``babylon.tui``: only primitives (``str`` in, ``int`` out, or a
        builtin exception) cross this boundary, the same deliberately narrow
        crossing :class:`PacedDriverHandle` already established, so this
        module never needs to import ``ActionNotPermitted``/``ActionNotLive``
        by name.

        :param action_id: one of the nine canonical Article V verbs.
        :raises RuntimeError: no player org to act as, the organizer may not
            issue ``action_id``, or it is a STUB with no wired effect yet.
        :raises KeyError: ``action_id`` names no registered action at all.
        :raises ValueError: a non-canonical verb, or the org cannot afford it.
        :returns: the queued turn's integer id.
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
    [
        CampaignHandle,
        "PacedDriverHandle | None",
        Callable[[], "str | None"],
        Callable[[], "str | None"],
        Callable[[str], bool],
    ],
    "TutorialProgress | None",
]
"""The booted campaign's tutorial-progress seam (Program v1.0.0 T6, Unit U4;
extended by Program 24 P8, "the tutorial learns the shell") — one layer up
from :data:`DriverFactory`, same shape. Takes the just-booted
:class:`CampaignHandle`, the just-built :class:`PacedDriverHandle` (or
``None`` when no ``driver_factory`` was wired), a zero-arg callable reading
:attr:`ArchiveApp.nav`'s current subject at call time, a zero-arg callable
reading the hybrid shell's ``ContentSwitcher`` ``.current`` pane at call time
(P8), and a one-arg callable reading whether a given subject id currently
holds a watchlist pin at call time (P8); returns ``None`` to mean "the
tutorial should not show for this campaign" — the composition root's own
new-vs-resumed gating decision (see ``babylon.cli.play``'s own docstring for
the honest first-session heuristic it uses), in which case
:meth:`ArchiveApp._on_briefing_dismissed` never mounts a
:class:`~babylon.tui.tutorial_overlay.TutorialOverlay` at all."""

#: The sample page's own subject — the nav shell's seed position, and
#: (Unit C2) the live campaign's own home dossier subject too: Wayne County
#: is the only scenario wired today (ruling 3, "Wayne stays in lobby").
_SAMPLE_SUBJECT: Final = "county/26163"

#: How many trail entries the breadcrumb bar displays (newest last).
_BREADCRUMB_DISPLAY: Final = 5

_ACTION_BAR_ABSENT: Final = (
    "▌ action bar: no verb plate wired yet (feed wires in at Program 24 P2-P6)."
)
"""Program 24 P1 honest-absence fence for the bottom action bar — the live
:class:`~babylon.projection.verbs.view_models.VerbPlateView` seam
(:func:`~babylon.projection.verbs.plate.build_verb_plate`) is not wired to any live campaign
graph yet; never fabricate a plate from no data (Constitution III.11)."""

_COPY_HINT: Final = "^c/⌘c copy · kitty: shift-drag"
"""Unit "selection-unwrap" (shell-interconnect): the static ``border_subtitle``
every un-paneled rail (:data:`_UNPANELED_RAIL_IDS`) carries — surfacing the
already-live but undiscoverable ``ctrl+c``/``super+c`` `Screen.copy_text`
binding (``screen.py:272``, ``show=False`` -> no Footer entry) now that
mouse-drag selection on these three rails actually extracts real text
(``Widget.get_selection`` needs a bare ``Text``/``Content`` body — see
:mod:`babylon.tui.chronicle`/:mod:`babylon.tui.watchlist`/
:mod:`babylon.tui.verb_plate`'s own "selection-unwrap" docstring notes). The
"kitty: shift-drag" half documents the terminal-native-selection escape
hatch for the #dashboard/#wiki panes, which stay OUTSIDE this unit's scope
(they render Markdown/HUD widgets, not a bare Text/Content body) — a real
gap, deliberately left as a documented absence rather than a code fix."""

_UNPANELED_RAIL_IDS: Final[tuple[str, ...]] = ("#chronicle-rail", "#watchlist-rail", "#action-bar")
"""The three ``Static`` ids this unit converted from an inner Rich ``Panel``
to a bare ``Text``/``Content`` body plus outer CSS chrome (border +
border-title + border-subtitle) — see :data:`_COPY_HINT` and
:meth:`ArchiveApp._apply_shell_chrome_titles`."""

_VERB_ACTION_KEYS: Final[tuple[str, ...]] = (
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
)
"""One function key per canonical Article V verb (Program 24 P5), zipped onto
:data:`~babylon.projection.verbs.preview.VERB_TO_ACTION_TYPE`'s own plate order —
educate/reproduce/attack/mobilize/campaign/aid/investigate/move/negotiate. Function keys
were chosen deliberately: every mnemonic first letter collides with an ALREADY-bound key
(``r``un vs ``r``eproduce, ``a``cknowledge vs ``a``ttack/``a``id, ``m``obilize vs ``m``ove),
so a positional F-key scheme is the only collision-free single-keypress mapping over the
existing ``t``/``r``/``a``/``1``-``4``/``ctrl+o``/``ctrl+i`` bindings."""


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
    :param subject_views: The right rail's peek-plate source (Program 24
        P6) — subject id -> its :data:`~babylon.projection.view_models.
        ProjectionRecord`, read by :meth:`_refresh_watchlist` to build each
        pinned subject's :func:`~babylon.tui.peek.peek` stat plate; defaults
        to :func:`_default_subject_views` (the committed fixtures). A pinned
        subject absent from this mapping renders
        :func:`~babylon.tui.watchlist.render_watchlist`'s own honest "no
        longer resolvable" row, never a crash or a silently dropped pin.
    :param watchlist_persistence: The watchlist's cross-session store
        (:data:`~babylon.tui.watchlist.WatchlistPersistence`, Program 24 P6);
        ``None`` (the default) uses
        :class:`~babylon.tui.watchlist.InMemoryWatchlistPersistence` (state
        dies with the process — the same honest no-database default
        :attr:`nav`'s own default persistence uses). The composition root
        threads the same ``babylon_meta``-backed
        :class:`~babylon.persistence.babylon_meta.BabylonMetaStore` in here
        it already threads as the campaign catalog (structurally satisfies
        this seam via its own ``load``/``save`` — the WO-37 trick).
    """

    COMMANDS = App.COMMANDS | {EntityNavigatorProvider}

    BINDINGS = [
        # Jumplist back/forward (unit "jumplist-rebind"): `[`/`]` are the
        # PRIMARY bindings — plain, ANSI-safe punctuation (ADR097 glyph
        # floor; verified free of collision, below), with no terminal-
        # protocol dependency. ctrl+o/ctrl+i are kept as SECONDARY aliases on
        # the SAME two actions: ctrl+o (0x0F) is fully live in every
        # terminal, but ctrl+i shares its raw byte (0x09) with Tab, so it
        # only resolves distinctly from Tab under the kitty keyboard
        # protocol's disambiguating encoding (textual.keys.KEY_ALIASES maps
        # "tab" -> ["ctrl+i"]) — inert-not-broken on a legacy terminal,
        # never a collision with Tab's own binding since ArchiveApp declares
        # none. The aliases are ``show=False`` so the Footer advertises one
        # Back/Forward pair, not a redundant duplicate.
        Binding("[", "jump_back", "Back"),
        Binding("]", "jump_forward", "Forward"),
        Binding("ctrl+o", "jump_back", "Back", show=False),
        Binding("ctrl+i", "jump_forward", "Forward", show=False),
        # show=False on this trio: not advertised in Footer chrome, but every
        # key is fully live — a pre-existing convention this unit leaves as-is
        # (the P1 layout change already regenerates the golden snapshot for
        # its own, unrelated reasons; see this unit's own commit).
        Binding("t", "advance_tick", "Advance Tick", show=False),
        Binding("r", "run_until_paused", "Run", show=False),
        Binding("a", "acknowledge_pause", "Acknowledge", show=False),
        # Program 24 P1 — the four-pane hybrid shell's domain switcher,
        # mirroring babylon.tui.shell.app_shell.AppShell's own BINDINGS.
        Binding("1", "switch_view('dashboard')", "Dashboard"),
        Binding("2", "switch_view('map')", "Map"),
        Binding("3", "switch_view('wiki')", "Wiki"),
        Binding("4", "switch_view('topology')", "Topology"),
        # Program 24 P6 — pin/unpin the current dossier subject on the right rail.
        Binding("p", "toggle_pin", "Pin/Unpin"),
        # Program 24 P5 — one F-key per canonical Article V verb (see
        # _VERB_ACTION_KEYS' own docstring for why F-keys, not mnemonic letters).
        *(
            Binding(key, f"issue_verb({verb!r})", verb.capitalize(), show=False)
            for key, verb in zip(_VERB_ACTION_KEYS, VERB_TO_ACTION_TYPE, strict=True)
        ),
    ]

    CSS = """
    Screen { background: $background; color: $foreground; }

    #breadcrumbs { dock: top; height: 1; background: $panel; color: $foreground; padding: 0 1; }

    #shell-body { height: 1fr; }

    #chronicle-rail {
        width: 24; height: 1fr; dock: left;
        background: $panel; color: $foreground; padding: 0 1;
        border: solid $primary;
    }
    #watchlist-rail {
        width: 24; height: 1fr; dock: right;
        background: $panel; color: $foreground; padding: 0 1;
        border: solid $primary;
    }
    #main { height: 1fr; }
    #action-bar {
        height: 3; dock: bottom;
        background: $panel; color: $foreground; padding: 0 1;
        border: solid $primary;
    }

    /* Unit "selection-unwrap" (shell-interconnect): the three rails' own
       Rich-rendered CONTENT used to carry a crimson Panel + gold title
       (chronicle's per-tick bulletins, the watchlist's pin-count panel, the
       verb plate's org/tick panel — Program 24 P2/P3/P5/P6). That Panel is
       gone now — render_chronicle/render_watchlist/render_verb_plate return
       a bare rich.text.Text so Widget.get_selection (widget.py:4213-4232)
       can extract it; a Panel/Group is opaque to that method, only
       Text/Content qualify — so the SAME crimson-box-plus-gold-title chrome
       moves here, onto the Static's own CSS border/border-title. Gold
       ($accent), not crimson ($primary): matches the old Rich title's own
       "bold GOLD" style; the four domain panes below use crimson ($primary)
       titles by contrast, a pre-existing, intentional difference this unit
       does not touch. border-title text is set dynamically, once per
       repaint (ArchiveApp._apply_shell_chrome_titles at boot,
       _refresh_watchlist/_refresh_action_bar on every live update —
       _refresh_chronicle never touches it: the tick number now lives
       inline in the body text itself, one header line per bulletin, so a
       single static rail-level title is enough). border-subtitle carries a
       static copy-affordance hint: the already-live but undiscoverable
       ctrl+c/super+c Screen.copy_text binding (screen.py:272, show=False)
       — mouse-drag a selection on any of these three rails, then copy it.
       Kitty's own Shift+drag (terminal-native selection, bypassing
       Textual's mouse reporting entirely) remains the escape hatch for the
       #dashboard/#wiki panes, which are NOT bare Text/Content widgets and
       so are NOT part of this unit — a documented {absence}, not a code
       fix (see ArchiveApp._apply_shell_chrome_titles' own docstring). */
    #chronicle-rail, #watchlist-rail, #action-bar {
        border-title-color: $accent;
        border-title-background: $panel;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        border-subtitle-background: $panel;
    }

    /* Program 24 P7 (KSBC aesthetic pass, DESIGN_BIBLE §9b "The Installer"):
       the four domain panes + the HUD sub-strip had NO chrome of their own
       before this pass. Each pane plate is a crimson-bordered box with its
       own title tab breaking the top border line ("┤ TITLE ├" idiom) — a
       bold crimson label chipped on a panel-tone backing. #wiki is the one
       scrollable content region among the four, so it gets the doc's
       "inner well" double border instead of the others' single plate
       border; #dashboard-hud nests inside #dashboard's own plate (ample
       width in the main content region, unlike the rails). */
    #dashboard, #map, #topology { border: solid $primary; }
    #wiki { border: double $primary; }
    #dashboard-hud { border: solid $primary; margin-bottom: 1; }

    #dashboard, #map, #wiki, #topology, #dashboard-hud {
        border-title-color: $primary;
        border-title-background: $panel;
        border-title-style: bold;
    }

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
        subject_views: Mapping[str, ProjectionRecord] | None = None,
        watchlist_persistence: WatchlistPersistence | None = None,
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
        self._chronicle_history: tuple[ChronicleEvent, ...] = ()
        """Every chronicle event advanced so far this session (Program 24 P3),
        newest-appended-last — the accumulator :meth:`_refresh_chronicle` grows
        one tick's worth at a time and :meth:`compose`'s ``#chronicle-rail``
        renders from. Bounded to :data:`~babylon.tui.chronicle.CHRONICLE_ROW_CEILING`
        (the same ceiling :func:`~babylon.tui.chronicle.chronicle_stream` applies
        to what's ever displayed — trimming the raw history to the same bound
        loses nothing a player could see, since a genuinely older event would
        never survive that same ceiling on render anyway) with the OLDEST events
        dropped first. Empty until the first tick advances; stays empty forever
        on the no-``campaign_menu`` demo boot path."""
        self._subject_views: Mapping[str, ProjectionRecord] = (
            subject_views if subject_views is not None else _default_subject_views()
        )
        self._watchlist_persistence: WatchlistPersistence = (
            watchlist_persistence or InMemoryWatchlistPersistence()
        )
        self.watchlist: WatchlistState = WatchlistState()
        """The right rail's pinned-subject set (Program 24 P6) — starts empty
        (:meth:`compose`'s ``#watchlist-rail`` paints its own honest "nothing
        pinned yet" fence) and is replaced with the persisted pin order once a
        live campaign boots (:meth:`_on_campaign_chosen`, keyed by
        :attr:`_watchlist_session_id`)."""
        self._watchlist_session_id: UUID = uuid4()
        """The watchlist's persistence key — a fresh id for the no-
        ``campaign_menu`` demo boot path (state lives exactly as long as the
        process, the same honest shape :attr:`nav`'s own in-memory default
        uses), replaced with the live campaign's own
        :attr:`~CampaignHandle.session_id` in :meth:`_on_campaign_chosen`."""

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"
        self._apply_shell_chrome_titles()
        if self._campaign_menu is not None:
            self.push_screen(LobbyScreen(self._campaign_menu), callback=self._on_campaign_chosen)
            return
        if self._page == SAMPLE_COUNTY_PAGE and self.nav.current is None:
            # Seed the jumplist with the sample page's own subject so the
            # first outbound jump has somewhere to Ctrl-O back to.
            self.nav.visit(_SAMPLE_SUBJECT)
            self._refresh_breadcrumbs()

    def _apply_shell_chrome_titles(self) -> None:
        """Stamp the Program 24 P7 KSBC title-tab label on every domain pane +
        the HUD sub-strip (DESIGN_BIBLE §9b "title tab breaks the border"
        idiom) — the four panes and the HUD had no chrome of their own
        before this pass. :meth:`compose` unconditionally mounts all five, so
        this always runs once at boot regardless of which path (lobby or
        demo) :meth:`on_mount` takes next.

        Unit "selection-unwrap" (shell-interconnect) extends this to the
        three un-paneled rails (:data:`_UNPANELED_RAIL_IDS`): each gets the
        SAME boot-time chrome stamp the four panes do, plus the static
        :data:`_COPY_HINT` ``border_subtitle`` every rail carries
        permanently (never touched again — it is not data-dependent, unlike
        ``border_title``). ``#chronicle-rail``'s own title never changes
        after this (the tick number now lives inline in the rendered body,
        one header line per bulletin, not in the title); ``#watchlist-rail``
        and ``#action-bar`` start with their own honest "nothing live yet"
        title and are overwritten with the real pin-count/org-tick string by
        :meth:`_refresh_watchlist`/:meth:`_refresh_action_bar` the moment a
        live campaign feeds them (Constitution III.11 — the boot-time title
        never claims data that is not there yet).
        """
        # Lazy import: WikiView imports BabylonMarkdown from this module — the
        # same one-way-seam trick :meth:`compose` already uses.
        from babylon.tui.shell.views.wiki_view import WikiView

        self.query_one(DashboardView).border_title = "DASHBOARD"
        self.query_one("#dashboard-hud", Static).border_title = "HUD"
        self.query_one(MapView).border_title = "MAP"
        self.query_one(WikiView).border_title = "WIKI"
        self.query_one(TopologyView).border_title = "TOPOLOGY"

        self.query_one("#chronicle-rail", Static).border_title = "CHRONICLE"
        self.query_one("#watchlist-rail", Static).border_title = watchlist_title(())
        self.query_one("#action-bar", Static).border_title = "ACTION BAR — no verb plate wired yet"
        for rail_id in _UNPANELED_RAIL_IDS:
            self.query_one(rail_id, Static).border_subtitle = _COPY_HINT

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
                campaign,
                self.driver,
                lambda: self.nav.current,
                lambda: self.query_one("#main", ContentSwitcher).current,
                lambda subject: self.watchlist.is_pinned(subject),
            )
        self._pages = campaign.read_page
        self._refresh_known_entities(campaign)
        self._watchlist_session_id = campaign.session_id
        self.watchlist = load_watchlist(self._watchlist_persistence, str(campaign.session_id))
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
        self._refresh_action_bar()
        self._refresh_watchlist()
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
        """Program 24 P1 — the four-pane hybrid shell: docked chronicle/watchlist rails,
        a bottom action bar, and a ``ContentSwitcher`` across Dashboard/Map/Wiki/Topology
        (``1``-``4`` switch panes, mirroring
        :class:`~babylon.tui.shell.app_shell.AppShell`'s own layout). The dossier that used
        to be this method's whole body now lives inside the "wiki" pane's
        :class:`~babylon.tui.shell.views.wiki_view.WikiView` — same ``#dossier`` id, same
        live wikilink resolver/statblock provider, zero behavior change for navigation.
        Dashboard/Map/Topology and both rails render their own honest ``{absence}`` fence
        until Program 24 P2-P6 wires real data through them.
        """
        # Lazy import: WikiView imports BabylonMarkdown from this module — importing it
        # here (compose() only ever runs after this module has fully loaded) keeps the
        # babylon.tui.app <-> shell.views seam one-way, the same trick
        # babylon.tui.shell.app_shell.export_visible_text already uses for its own
        # reverse reference.
        from babylon.tui.shell.views.wiki_view import WikiView

        yield Label("", id="breadcrumbs")
        # A separate arrange pass (own box, not the Screen's): the rails dock left/right
        # WITHIN #shell-body's own height, so they never fight #breadcrumbs'/#status'/
        # Footer's dock:top/dock:bottom strips for the same top-left/bottom-left corner
        # cells — each edge's dock reservation stays inside the layer that owns it.
        with Container(id="shell-body"):
            yield Static(render_chronicle(()), id="chronicle-rail")
            yield Static(render_watchlist((), {}), id="watchlist-rail")
            with Vertical():
                with ContentSwitcher(initial="wiki", id="main"):
                    yield DashboardView(id="dashboard")
                    yield MapView(id="map")
                    yield WikiView(
                        id="wiki",
                        page=self._page,
                        parser_factory=self._current_parser,
                        open_links=False,
                        statblocks=self._statblocks,
                    )
                    yield TopologyView(id="topology")
                yield Static(_ACTION_BAR_ABSENT, id="action-bar")
        yield Label("status: — (click a link)", id="status")
        yield Footer()

    def action_switch_view(self, view: str) -> None:
        """``1``-``4``: switch the main region to ``view`` (one of the four domain pane
        ids), mirroring :meth:`~babylon.tui.shell.app_shell.AppShell.action_switch_view`.

        Switching TO the dashboard pane (Program 24 P2) also re-renders it from the live
        campaign's current :meth:`CampaignHandle.dashboard_view` — a player pressing ``1``
        always sees this instant's numbers, not whatever was last painted at boot.

        Program 24 P8: also re-polls the tutorial overlay via
        :meth:`_refresh_tutorial_progress` — the same trigger-path idiom every other
        committed-tick/navigation action already follows, extended here so a
        :class:`~babylon.game.tutorial.PaneShowing` completion is actually observed the
        instant it becomes true, not only on some LATER unrelated action.

        :param view: one of ``"dashboard"``/``"map"``/``"wiki"``/``"topology"``.
        """
        self.query_one("#main", ContentSwitcher).current = view
        if view == "dashboard":
            self._refresh_dashboard()
        self._refresh_tutorial_progress()

    def _refresh_dashboard(self) -> None:
        """Render the dashboard pane's live :class:`EconomyView` (Program 24 P2)
        and its HUD strip (Program 24 P4) — the tick/horizon counter, the five
        endgame axis progress bars, and the paced driver's lock/pause state.

        Reads ONLY through :meth:`CampaignHandle.dashboard_view`/
        :meth:`CampaignHandle.endgame_status` — the host-side composition root
        (:mod:`babylon.game.session`) already did the ``project_economy``/
        ``EndgameDetector`` work; this app hands the resulting pure view models
        straight to :class:`~babylon.tui.shell.views.dashboard_view.DashboardView`,
        never touching a graph/world/detector itself (projection purity). A
        no-op with no live :attr:`campaign`; the economy body and the HUD strip
        are each independently left exactly as :meth:`compose` painted them
        (Constitution III.11: never a blank or fabricated repaint) whenever
        their own accessor returns ``None`` — one pane's absence never blocks
        the other's live repaint.
        """
        if self.campaign is None:
            return
        dashboard = self.query_one(DashboardView)
        view = self.campaign.dashboard_view()
        if view is not None:
            dashboard.render_economy(view)
        status = self.campaign.endgame_status()
        if status is not None:
            driver = self.driver
            dashboard.render_hud(
                status,
                tick=self.campaign.tick,
                driver_attached=driver is not None,
                locked=driver.locked if driver is not None else False,
                lock_reason=driver.lock_reason if driver is not None else None,
                awaiting_ack=driver.awaiting_ack if driver is not None else False,
                busy=driver.busy if driver is not None else False,
                pause_summary=driver.pause_summary if driver is not None else None,
            )

    def _refresh_action_bar(self) -> None:
        """Render the bottom action bar's live verb plate (Program 24 P5) — the
        player's first real write-path onto the world.

        Reads ONLY through :meth:`CampaignHandle.verb_plate_view` — the host-side
        composition root (:mod:`babylon.game.session`) already did the
        ``build_verb_plate`` work; this app hands the resulting pure
        :class:`~babylon.projection.verbs.view_models.VerbPlateView` straight to
        :func:`~babylon.tui.verb_plate.render_verb_plate`, never touching a graph
        itself (projection purity, the same reasoning :meth:`_refresh_dashboard`
        already documents). A no-op with no live :attr:`campaign`; leaves the
        bar's existing :data:`_ACTION_BAR_ABSENT` fence untouched when this
        composition root chose not to wire a live plate (Constitution III.11: never
        a blank or fabricated repaint), same as :meth:`_refresh_dashboard`.

        Unit "selection-unwrap": also stamps the bar's ``border_title`` with
        :func:`~babylon.tui.verb_plate.verb_plate_title` — the org/tick
        header the old ``Panel(title=...)`` used to carry, now CSS chrome
        (see :mod:`babylon.tui.app`'s own CSS comment) — so the two always
        repaint together, never one stale against the other.
        """
        if self.campaign is None:
            return
        view = self.campaign.verb_plate_view()
        if view is not None:
            bar = self.query_one("#action-bar", Static)
            bar.update(render_verb_plate(view))
            bar.border_title = verb_plate_title(view)

    def _refresh_chronicle(self, chronicle: Sequence[ChronicleEvent]) -> None:
        """Append ``chronicle``'s events to :attr:`_chronicle_history` and repaint
        the left rail (Program 24 P3) — the loudest "the world is alive" signal.

        A no-op when ``chronicle`` is empty: a genuinely quiet tick contributes no
        bulletin (:func:`~babylon.tui.chronicle.chronicle_stream`'s own documented
        behavior), so the rail is left exactly as it last rendered — either the
        boot-time honest "the wire is quiet" fence (Constitution III.11) when no
        tick has ever produced an event, or the prior history when it has. Called
        with ONE tick's events from :meth:`action_advance_tick`, and with every
        tick's events (concatenated, in order) from a ``run_until_paused`` batch.

        :param chronicle: newly-produced chronicle events, chronological.
        """
        if not chronicle:
            return
        combined = (*self._chronicle_history, *chronicle)
        self._chronicle_history = combined[-CHRONICLE_ROW_CEILING:]
        bulletins = chronicle_stream(self._chronicle_history, limit=CHRONICLE_ROW_CEILING)
        self.query_one("#chronicle-rail", Static).update(render_chronicle(bulletins))

    def _refresh_watchlist(self) -> None:
        """Repaint the right rail from :attr:`watchlist` (Program 24 P6).

        Stacks one :func:`~babylon.tui.peek.peek` ``depth=0`` stat-plate row
        per pinned subject via :func:`~babylon.tui.watchlist.render_watchlist`,
        resolving each pinned id against :attr:`_subject_views`. A pin with no
        entry there (a subject outside the committed fixture set, or a kind
        with no live producer yet) still renders its own named "no longer
        resolvable" row — never silently dropped (Constitution III.11). An
        empty :attr:`watchlist` renders the same honest "nothing pinned yet"
        fence :meth:`compose` boots with.

        Unit "selection-unwrap": also stamps the rail's ``border_title`` with
        :func:`~babylon.tui.watchlist.watchlist_title` — the pin count the
        old ``Panel(title=...)`` used to carry, now CSS chrome (see
        :mod:`babylon.tui.app`'s own CSS comment) — so the two always
        repaint together, never one stale against the other.
        """
        rail = self.query_one("#watchlist-rail", Static)
        rail.update(render_watchlist(self.watchlist.pinned_ids, self._subject_views))
        rail.border_title = watchlist_title(self.watchlist.pinned_ids)

    def _save_watchlist(self) -> None:
        """Persist :attr:`watchlist`'s current pin order (Program 24 P6).

        Keyed by :attr:`_watchlist_session_id` — the live campaign's own
        :attr:`~CampaignHandle.session_id` once one has booted, else the
        demo boot's own process-lifetime id (see that attribute's own
        docstring).
        """
        save_watchlist(self._watchlist_persistence, str(self._watchlist_session_id), self.watchlist)

    def action_toggle_pin(self) -> None:
        """``p``: pin/unpin the dossier's current subject (Program 24 P6).

        Reads :attr:`nav.current` — the subject the dossier is presently
        showing. Persists the resulting pin order via
        :meth:`_save_watchlist` and repaints the rail via
        :meth:`_refresh_watchlist` on every successful toggle. Never
        crashes or silently no-ops: with no current subject (nothing
        navigated to yet) or a pin that would exceed
        :class:`~babylon.tui.watchlist.WatchlistState`'s own capacity
        ceiling, the status line names exactly why nothing moved
        (Constitution III.11).

        Program 24 P8: also re-polls the tutorial overlay via
        :meth:`_refresh_tutorial_progress` on every successful toggle — the
        same "success path only" shape :meth:`action_advance_tick`/
        :meth:`action_run_until_paused`/:meth:`action_acknowledge_pause`
        already use, so a :class:`~babylon.game.tutorial.PinnedInWatchlist`
        completion is observed the instant the pin actually lands.
        """
        status = self.query_one("#status", Label)
        subject = self.nav.current
        if subject is None:
            status.update("status: no current subject to pin")
            return
        if self.watchlist.is_pinned(subject):
            self.watchlist = self.watchlist.unpin(subject)
            status.update(f"status: unpinned {subject}")
        else:
            try:
                self.watchlist = self.watchlist.pin(subject)
            except ValueError as exc:
                status.update(f"status: {exc}")
                return
            status.update(f"status: pinned {subject}")
        self._save_watchlist()
        self._refresh_watchlist()
        self._refresh_tutorial_progress()

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

    async def _navigate(self, subject: str, *, record: bool = True, reveal: bool = True) -> None:
        """Show ``subject``'s page (or its loud absence page).

        Unit "navigate-pane-couple" (shell-interconnect): before this fix, every
        caller updated ``#dossier`` under whatever pane happened to be showing —
        a player parked on the Map/Topology/Dashboard pane who walked the
        jumplist, picked a command-palette hit, or clicked a wikilink would
        never actually SEE the new page (the "P8 dodge"; ``#dossier`` changed,
        but ``ContentSwitcher`` was still showing something else). ``reveal``
        closes that for every DELIBERATE navigation by switching ``#main`` back
        to the Wiki pane — but stays ``False`` for the post-tick "refresh the
        CURRENTLY-shown subject in place" calls
        (:meth:`action_advance_tick`/:meth:`action_run_until_paused`), which
        must never clobber a player deliberately parked on the Dashboard/Map/
        Topology pane watching ITS OWN live refresh just because a tick
        advanced.

        :param subject: the subject id to open.
        :param record: whether this is a new jump (recorded in the
            jumplist and trail) or a jumplist walk (already recorded).
        :param reveal: whether to switch ``#main`` to the Wiki pane so this
            update is actually visible.
        """
        page = self._pages(subject)
        document = page if page is not None else _absence_page(subject)
        if reveal:
            self.query_one("#main", ContentSwitcher).current = "wiki"
        await self.query_one("#dossier", BabylonMarkdown).update(document)
        if record:
            self.nav.visit(subject)
        self._refresh_breadcrumbs()
        marker = " [ABSENT]" if page is None else ""
        self.query_one("#status", Label).update(f"status: {subject}{marker}")
        self._refresh_tutorial_progress()

    async def action_jump_back(self) -> None:
        """``[`` (alias ``Ctrl-O``): walk back one jumplist step, if there is one.

        Unit "jumplist-rebind" fix: :attr:`~babylon.tui.nav.NavShell.back`
        returns ``None`` at the jumplist's oldest entry — previously a
        silent no-op the player could not distinguish from a missed
        keypress. Now surfaces a loud status note instead (Constitution
        III.11), the same "refuse with a reason" posture
        :meth:`action_advance_tick`/:meth:`action_run_until_paused` already
        use for their own edge refusals.
        """
        subject = self.nav.back()
        if subject is not None:
            await self._navigate(subject, record=False)
        else:
            self.query_one("#status", Label).update(
                "status: at the jumplist start — nothing further back"
            )

    async def action_jump_forward(self) -> None:
        """``]`` (alias ``Ctrl-I``): walk forward one jumplist step, if there is one.

        See :meth:`action_jump_back`'s docstring for the loud-edge fix this
        mirrors.
        """
        subject = self.nav.forward()
        if subject is not None:
            await self._navigate(subject, record=False)
        else:
            self.query_one("#status", Label).update(
                "status: at the jumplist end — nothing further forward"
            )

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

        Program 24 P2: also re-renders the dashboard pane via
        :meth:`_refresh_dashboard`, so the HUD stays live across ticks even
        while a different pane is showing.

        Program 24 P3: also appends this tick's chronicle to the left rail via
        :meth:`_refresh_chronicle`.

        Program 24 P5: also re-renders the action bar's verb plate via
        :meth:`_refresh_action_bar`, so its eligibility/affordability/preview
        columns reflect this instant's graph, not the tick this pane last painted.
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
        self._refresh_dashboard()
        self._refresh_action_bar()
        self._refresh_chronicle(result.chronicle)
        subject = self.nav.current
        if subject is not None:
            # reveal=False: refresh the currently-shown subject's dossier
            # content in place — never yank a player parked on the
            # Dashboard/Map/Topology pane back to the Wiki pane just
            # because a tick advanced (``_navigate``'s own docstring).
            await self._navigate(subject, record=False, reveal=False)
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

        Program 24 P2: also re-renders the dashboard pane via
        :meth:`_refresh_dashboard`, same as ``t``.

        Program 24 P3: also appends every advanced tick's chronicle (in order)
        to the left rail via :meth:`_refresh_chronicle`, same as ``t``.

        Program 24 P5: also re-renders the action bar's verb plate via
        :meth:`_refresh_action_bar`, same as ``t``.
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
        self._refresh_dashboard()
        self._refresh_action_bar()
        self._refresh_chronicle(tuple(event for result in results for event in result.chronicle))
        subject = self.nav.current
        if subject is not None:
            # reveal=False: see action_advance_tick's own comment above —
            # a background refresh must never clobber a deliberately
            # non-wiki pane.
            await self._navigate(subject, record=False, reveal=False)
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

    def action_issue_verb(self, verb: str) -> None:
        """``F1``-``F9``: issue one Article V verb through the action bar's real
        write path (Program 24 P5) — the FIRST time the player can act on the
        world from this shell.

        Reads the ALREADY-RENDERED :class:`~babylon.projection.verbs.view_models.
        VerbPlateView` (:meth:`CampaignHandle.verb_plate_view`, the same call
        :meth:`_refresh_action_bar` just painted) to decide whether to even
        attempt the write: ``eligible`` is a target-existence predicate
        :meth:`CampaignHandle.issue_verb`'s own agent-type/``LIVE`` gate knows
        nothing about (:func:`~babylon.projection.verbs.plate.build_verb_plate`'s
        own docstring — "the UI disables on eligible only, never on
        can_afford") — so an ineligible row's reason is surfaced WITHOUT ever
        calling :meth:`CampaignHandle.issue_verb`, never a silent no-op
        (Constitution III.11). An eligible row proceeds to
        :meth:`CampaignHandle.issue_verb`; any refusal it raises (an
        institutional macro-action, the wrong agent type, an unaffordable verb,
        an unknown action id) surfaces as a loud status note too, never an
        unhandled crash — the concrete ``ActionNotPermitted``/``ActionNotLive``
        types stay inside ``babylon.game.actions.player_driver`` (both are
        ``RuntimeError`` subclasses; this module never imports them by name,
        the same primitives-only crossing :class:`PacedDriverHandle` already
        established).

        :param verb: one of the nine canonical Article V verbs (bound 1:1 to
            ``F1``-``F9`` via :data:`_VERB_ACTION_KEYS`).
        """
        status = self.query_one("#status", Label)
        if self.campaign is None:
            status.update("status: no live campaign attached — nothing to act on")
            return
        view = self.campaign.verb_plate_view()
        if view is None:
            status.update("status: no verb plate wired — cannot issue an action")
            return
        row = next((candidate for candidate in view.verbs if candidate.verb == verb), None)
        if row is None:
            status.update(f"status: {verb} — missing from plate view")
            return
        if not row.eligible:
            status.update(f"status: {verb} refused — {row.reason}")
            return
        try:
            turn_id = self.campaign.issue_verb(verb)
        except (RuntimeError, ValueError, KeyError) as exc:
            status.update(f"status: {verb} refused — {exc}")
            return
        afford_note = "" if row.can_afford else f" · {row.afford_note}"
        status.update(f"status: {verb} queued (turn #{turn_id}){afford_note}")
        self._refresh_action_bar()

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
