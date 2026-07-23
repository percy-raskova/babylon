"""Behavioral contract for Program 24 P6 — the right rail's pinned watchlist.

``watchlist.py``'s ``WatchlistState``/``render_watchlist`` and ``peek.py``'s ``peek`` were already
pure and complete (P1 wired the rail's honest ``"nothing pinned yet"`` absence at boot —
``test_app_hybrid_shell.py``). This file closes the remaining gap:
``ArchiveApp.action_toggle_pin`` (bound to ``p``) pins/unpins the dossier's current subject,
``ArchiveApp._refresh_watchlist`` stacks a live ``peek(view, depth=0)`` stat plate per pin
(resolved through ``ArchiveApp._resolve_subject_view`` -> ``CampaignHandle.subject_view`` — unit
"live-subject-view", shell-interconnect; the pre-that-unit fixture-fed default,
:func:`babylon.tui.dispatch.fixture_subject_views`, now serves only the no-``campaign_menu`` demo
boot path this file never exercises), and ``WatchlistPersistence`` (the ``babylon_meta``-backed
store, structurally satisfied here by a fake) keeps the pin order across a resumed campaign —
following the exact ``_booted_app``/``_boot_into_campaign_shell`` idiom
``test_app_dashboard_live.py``/``test_app_chronicle_live.py`` established.

Unit "live-subject-view": ``_FakeCampaign.subject_view`` resolves against a caller-supplied
``subject_views`` dict (the ``_booted_app`` kwarg of the same name, threaded into the FAKE
CAMPAIGN now rather than ``ArchiveApp`` itself) — mirroring ``test_app_post_tick_fanout.py``'s own
"stores the exact dict object, never copied" idiom for proving fresh-every-call resolution.
Defaults to a real ``CountyView`` for ``_HOME_SUBJECT`` (not empty) so the happy-path pin tests
below still exercise a genuinely resolvable live row, not merely the honest-absence path.

Unit "selection-unwrap" (shell-interconnect): ``render_watchlist`` used to return a
``rich.panel.Panel`` with the pin count as its ``title``; it now returns a bare ``Text``
(a ``Panel`` is opaque to ``Widget.get_selection``), with the pin count moved to
:func:`~babylon.tui.watchlist.watchlist_title`, assigned to the rail's own
``border_title`` by ``ArchiveApp._refresh_watchlist``. ``_rail_text`` below reads both
(content + ``border_title``) and joins them the same way the old combined string did, so
every pre-existing assertion here (``"Watchlist (N pinned)" in rail``) keeps working
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

import pytest
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import ContentSwitcher, Label, OptionList

from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import CountyView, EconomyView, ProjectionRecord
from babylon.tui.app import ArchiveApp
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.watchlist import InMemoryWatchlistPersistence, WatchlistPersistence

pytestmark = pytest.mark.unit

#: The demo campaign shell always lands on Wayne County first (ruling 3) — the same
#: subject :func:`babylon.tui.dispatch.fixture_subject_views`'s default map resolves.
_HOME_SUBJECT = "county/26163"

#: ``_FakeCampaign``'s default ``subject_view`` resolution for ``_HOME_SUBJECT`` when a test
#: hands in no explicit ``subject_views`` override — a real ``CountyView``, so the happy-path
#: pin tests below prove a genuinely live-resolved row, not merely the honest-absence path.
_DEFAULT_HOME_VIEW: Final = CountyView(county_fips="26163", verified_tick=0, population=1000)


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_dashboard_live.py``'s own
    fixture, plus unit "live-subject-view"'s own ``subject_view`` seam: resolves against a
    caller-supplied ``subject_views`` dict, stored as-is (never copied — the SAME
    "mutate the dict a test handed in, see it on the very next call" idiom
    ``test_app_post_tick_fanout.py`` already established for freshness), defaulting to
    ``{_HOME_SUBJECT: _DEFAULT_HOME_VIEW}`` rather than empty so a test that hands in no
    override still exercises a genuinely resolvable live row."""

    def __init__(
        self,
        session_id: UUID,
        pages: dict[str, str],
        *,
        subject_views: dict[str, ProjectionRecord] | None = None,
    ) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self._subject_views: dict[str, ProjectionRecord] = (
            subject_views if subject_views is not None else {_HOME_SUBJECT: _DEFAULT_HOME_VIEW}
        )

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        return None

    def endgame_status(self) -> EndgameStatus | None:
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        return None

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """Live per-subject resolution, fresh every call — this unit's own concern."""
        return self._subject_views.get(subject_id)

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by these tests
        raise AssertionError("issue_verb should not be called by these watchlist tests")

    def advance_tick(self) -> _FakeTickOutcome:
        self.tick += 1
        return _FakeTickOutcome(tick=self.tick, paused=False)


class _FakeLoader:
    def __init__(self, campaign: _FakeCampaign) -> None:
        self._campaign = campaign

    def __call__(self, campaign_id: UUID) -> _FakeCampaign:
        return self._campaign


def _seeded_menu(campaign_id: UUID) -> CampaignMenu:
    catalog = InMemoryCampaignCatalog(
        seed=(
            InMemoryCampaign(
                campaign_id=campaign_id,
                slug="campaign-watchlist",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16)


def _booted_app(
    campaign_id: UUID,
    *,
    watchlist_persistence: WatchlistPersistence | None = None,
    subject_views: dict[str, ProjectionRecord] | None = None,
) -> ArchiveApp:
    menu = _seeded_menu(campaign_id)
    campaign = _FakeCampaign(
        campaign_id,
        {
            f"briefing/{campaign_id}": "# OPERATION WATCHLIST\n",
            _HOME_SUBJECT: "# Wayne\n",
        },
        subject_views=subject_views,
    )
    loader = _FakeLoader(campaign)
    return ArchiveApp(
        campaign_menu=menu,
        campaign_loader=loader,
        watchlist_persistence=watchlist_persistence,
    )


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _rail_text(app: ArchiveApp) -> str:
    """The right rail's plain text — every option's own prompt, joined.

    Unit "watchlist-row-nav" (shell-interconnect): ``#watchlist-rail`` is a
    row-addressable :class:`~textual.widgets.OptionList` now (was a plain
    ``Static``), so there is no single ``.content``/``.render()`` to read —
    each :class:`~textual.widgets.option_list.Option`'s own ``prompt`` is
    the exact bare :class:`~rich.text.Text`
    :meth:`~babylon.tui.app.ArchiveApp._populate_watchlist_options` stamped
    it with (the same shape :func:`~babylon.tui.watchlist.watchlist_rows`
    itself returns), for both the absence-placeholder row and every real
    pinned row. The rail's ``border_title``
    (:func:`~babylon.tui.watchlist.watchlist_title`, the pin count that used
    to live in the old Panel's own ``title=``) is joined in front, so every
    pre-existing ``"Watchlist (N pinned)" in rail`` assertion below keeps
    working unchanged."""
    widget = app.query_one("#watchlist-rail", OptionList)
    rows: list[str] = []
    for index in range(widget.option_count):
        prompt = widget.get_option_at_index(index).prompt
        assert isinstance(prompt, Text)
        rows.append(prompt.plain)
    title = widget.border_title or ""
    return f"{title}\n" + "\n".join(rows)


class TestEmptyWatchlistShowsTheHonestAbsenceOnBoot:
    @pytest.mark.asyncio
    async def test_a_freshly_booted_campaign_shows_nothing_pinned(self) -> None:
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            assert "nothing pinned yet" in _rail_text(app)


class TestPinningAddsAStatPlateRow:
    @pytest.mark.asyncio
    async def test_pressing_p_pins_the_current_subject_and_paints_its_peek_row(self) -> None:
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            assert app.nav.current == _HOME_SUBJECT

            await pilot.press("p")
            await pilot.pause()

            assert app.watchlist.pinned_ids == (_HOME_SUBJECT,)
            rail = _rail_text(app)
            assert "Watchlist (1 pinned)" in rail
            assert _HOME_SUBJECT in rail
            assert "nothing pinned yet" not in rail
            # Unit "live-subject-view": a genuinely resolved row (real
            # ``_DEFAULT_HOME_VIEW`` content), never the "no longer
            # resolvable" absence line — proves the row reached
            # ``CampaignHandle.subject_view``, not a silent absence that
            # happens to also mention the id.
            assert "no longer resolvable" not in rail
            assert "population=1000" in rail

    @pytest.mark.asyncio
    async def test_the_status_line_names_the_pinned_subject(self) -> None:
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()

            status = str(app.query_one("#status", Label).render())
            assert f"pinned {_HOME_SUBJECT}" in status


class TestUnpinningRemovesTheRow:
    @pytest.mark.asyncio
    async def test_pressing_p_twice_pins_then_unpins(self) -> None:
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()
            assert app.watchlist.pinned_ids == (_HOME_SUBJECT,)

            await pilot.press("p")
            await pilot.pause()

            assert app.watchlist.pinned_ids == ()
            assert "nothing pinned yet" in _rail_text(app)
            status = str(app.query_one("#status", Label).render())
            assert f"unpinned {_HOME_SUBJECT}" in status


class TestAPinWithNoResolvableViewRendersHonestAbsence:
    @pytest.mark.asyncio
    async def test_a_pin_outside_subject_views_shows_the_named_absence_row(self) -> None:
        """Constitution III.11: a pinned subject this composition root has no
        view-model for renders ``render_watchlist``'s own named absence line,
        never a crash or a silently dropped pin."""
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id, subject_views={})
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()

            rail = _rail_text(app)
            assert _HOME_SUBJECT in rail
            assert "no longer resolvable" in rail


class TestLiveCampaignSubjectViewSupersedesTheAppLevelFixture:
    """Unit "live-subject-view" (shell-interconnect): pins the retirement itself — a
    booted campaign's own ``CampaignHandle.subject_view`` must be consulted, never the
    ``ArchiveApp``-level ``subject_views``/``_default_subject_views`` fixture map (which now
    serves ONLY the no-``campaign_menu`` demo boot path)."""

    @pytest.mark.asyncio
    async def test_the_live_campaigns_own_view_wins_over_an_explicit_app_level_fixture(
        self,
    ) -> None:
        campaign_id = UUID(int=1)
        menu = _seeded_menu(campaign_id)
        live_view = CountyView(county_fips="26163", verified_tick=0, population=42)
        campaign = _FakeCampaign(
            campaign_id,
            {
                f"briefing/{campaign_id}": "# OPERATION WATCHLIST\n",
                _HOME_SUBJECT: "# Wayne\n",
            },
            subject_views={_HOME_SUBJECT: live_view},
        )
        loader = _FakeLoader(campaign)
        stale_app_level_view = CountyView(county_fips="26163", verified_tick=0, population=999999)
        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=loader,
            subject_views={_HOME_SUBJECT: stale_app_level_view},
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()

            rail = _rail_text(app)
            assert "population=42" in rail
            assert "population=999999" not in rail


class TestNoCurrentSubjectToPin:
    @pytest.mark.asyncio
    async def test_pinning_with_no_navigation_history_is_a_named_no_op(self) -> None:
        """The plain (no-``campaign_menu``) boot path with a non-sample page never
        seeds ``nav``, so there is no "current subject" to pin yet."""
        app = ArchiveApp(page="# Standalone Page\n")
        async with app.run_test() as pilot:
            assert app.nav.current is None

            await pilot.press("p")
            await pilot.pause()

            assert app.watchlist.pinned_ids == ()
            status = str(app.query_one("#status", Label).render())
            assert "no current subject to pin" in status


class TestPinPersistsThroughTheHandle:
    @pytest.mark.asyncio
    async def test_a_pin_survives_a_resume_through_the_same_persistence(self) -> None:
        campaign_id = UUID(int=1)
        store = InMemoryWatchlistPersistence()

        first = _booted_app(campaign_id, watchlist_persistence=store)
        async with first.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()
            assert first.watchlist.pinned_ids == (_HOME_SUBJECT,)

        # A fresh ArchiveApp, same campaign id, same persistence handle — the
        # resumed-campaign path (Program 24 P3's charter batch ruling 3).
        second = _booted_app(campaign_id, watchlist_persistence=store)
        async with second.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            assert second.watchlist.pinned_ids == (_HOME_SUBJECT,)
            rail = _rail_text(second)
            assert "Watchlist (1 pinned)" in rail
            assert _HOME_SUBJECT in rail

    @pytest.mark.asyncio
    async def test_a_fake_satisfies_the_watchlist_persistence_protocol(self) -> None:
        """The same structural-Protocol proof every sibling seam test carries —
        ``BabylonMetaStore`` satisfies this identically without importing it here."""
        assert isinstance(InMemoryWatchlistPersistence(), WatchlistPersistence)


#: A subject with no baked page of its own — navigating to it still updates
#: ``nav.current`` (``ArchiveApp._navigate``'s own honest-absence path), which
#: is all these tests need: somewhere real to have left FROM before opening
#: the pinned row brings the dossier back.
_ELSEWHERE_SUBJECT = "county/00000"


class TestRowAddressableWatchlistOpensTheHighlightedRow:
    """Unit "watchlist-row-nav" (shell-interconnect): ``#watchlist-rail`` is a
    row-addressable ``textual.widgets.OptionList`` — Enter (keyboard) and a
    mouse click both resolve to the same
    ``ArchiveApp.on_option_list_option_selected`` -> ``_navigate`` path (R3:
    mouse and keyboard both first-class)."""

    @pytest.mark.asyncio
    async def test_enter_on_the_highlighted_row_reopens_the_pinned_subject(self) -> None:
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")  # pin _HOME_SUBJECT
            await pilot.pause()
            assert app.watchlist.pinned_ids == (_HOME_SUBJECT,)

            # Leave the pinned subject — a genuine transition, so opening it
            # back via the watchlist is provably NOT a no-op (white-box
            # _navigate call, the same pattern test_app_focus_model.py's own
            # TestNavigateMovesFocusOnlyWhenRevealed uses to set up state no
            # player-facing binding reaches yet in this fixture).
            await app._navigate(_ELSEWHERE_SUBJECT)  # noqa: SLF001 - white-box setup
            await pilot.pause()
            assert app.nav.current == _ELSEWHERE_SUBJECT

            rail = app.query_one("#watchlist-rail", OptionList)
            rail.focus()
            await pilot.pause()
            assert rail.highlighted == 0, "the one pinned row should already be highlighted"

            await pilot.press("enter")
            await pilot.pause()

            assert app.nav.current == _HOME_SUBJECT
            assert app.query_one("#main", ContentSwitcher).current == "wiki"

    @pytest.mark.asyncio
    async def test_a_mouse_click_resolves_through_the_same_option_selected_path_as_enter(
        self,
    ) -> None:
        """Proves the CLICK path reaches the exact same handler Enter does —
        without pixel-coordinate hit-testing (Textual's own responsibility,
        already covered by its own test suite): ``OptionList._on_click``'s
        entire body is ``self.highlighted = clicked_option;
        self.action_select()``, so driving those two calls directly IS the
        click path, not a stand-in for it."""
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()
            await app._navigate(_ELSEWHERE_SUBJECT)  # noqa: SLF001 - white-box setup
            await pilot.pause()
            assert app.nav.current == _ELSEWHERE_SUBJECT

            rail = app.query_one("#watchlist-rail", OptionList)
            rail.highlighted = 0
            rail.action_select()
            await pilot.pause()

            assert app.nav.current == _HOME_SUBJECT

    @pytest.mark.asyncio
    async def test_enter_on_the_empty_watchlists_placeholder_row_is_a_named_no_op(self) -> None:
        """The lone absence-placeholder row is ``disabled=True`` —
        ``OptionList.action_select`` itself refuses to post ``OptionSelected``
        for a disabled option, so Enter here never navigates anywhere
        (Constitution III.11: the fence text itself already names the
        absence, so this is honest, not a hidden failure)."""
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            before = app.nav.current
            assert app.watchlist.pinned_ids == ()

            rail = app.query_one("#watchlist-rail", OptionList)
            rail.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert app.nav.current == before

    @pytest.mark.asyncio
    async def test_opening_an_unresolvable_pin_still_reaches_its_real_or_absence_page(
        self,
    ) -> None:
        """A pin outside ``_subject_views`` renders its own "no longer
        resolvable" row (the peek-plate gap) but is still fully openable —
        ``pinned_ids`` is already the exact subject-id form ``_navigate``
        consumes, independent of whether a peek view-model exists."""
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id, subject_views={})
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()
            await app._navigate(_ELSEWHERE_SUBJECT)  # noqa: SLF001 - white-box setup
            await pilot.pause()

            rail = app.query_one("#watchlist-rail", OptionList)
            rail.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert app.nav.current == _HOME_SUBJECT

    @pytest.mark.asyncio
    async def test_the_highlighted_row_survives_a_live_repaint(self) -> None:
        """``_refresh_watchlist`` clears and rebuilds every option on every
        repaint (a tick, a pin/unpin) — the previously-highlighted index must
        survive that rebuild (mirrors
        ``babylon.tui.campaign_menu.LobbyScreen._reload``'s own highlight-
        preservation idiom), or a player mid-Tab-then-arrow-key row-pick
        would be silently reset to nothing on every live update."""
        campaign_id = UUID(int=1)
        app = _booted_app(campaign_id)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")  # pin _HOME_SUBJECT
            await pilot.pause()

            # A second pin needs a second navigable subject — _navigate to
            # one (white-box, same pattern as the tests above) then pin it.
            await app._navigate(_ELSEWHERE_SUBJECT)  # noqa: SLF001 - white-box setup
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            assert app.watchlist.pinned_ids == (_HOME_SUBJECT, _ELSEWHERE_SUBJECT)

            rail = app.query_one("#watchlist-rail", OptionList)
            rail.highlighted = 1  # the just-added second row
            app._refresh_watchlist()  # noqa: SLF001 - white-box repaint trigger

            assert rail.highlighted == 1
