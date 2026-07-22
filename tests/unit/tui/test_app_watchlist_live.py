"""Behavioral contract for Program 24 P6 — the right rail's pinned watchlist.

``watchlist.py``'s ``WatchlistState``/``render_watchlist`` and ``peek.py``'s ``peek`` were already
pure and complete (P1 wired the rail's honest ``"nothing pinned yet"`` absence at boot —
``test_app_hybrid_shell.py``). This file closes the remaining gap:
``ArchiveApp.action_toggle_pin`` (bound to ``p``) pins/unpins the dossier's current subject,
``ArchiveApp._refresh_watchlist`` stacks a live ``peek(view, depth=0)`` stat plate per pin
(resolved against ``ArchiveApp._subject_views``, fixture-fed by default —
:func:`babylon.tui.dispatch.fixture_subject_views`), and
``WatchlistPersistence`` (the ``babylon_meta``-backed store, structurally satisfied here by a
fake) keeps the pin order across a resumed campaign — following the exact
``_booted_app``/``_boot_into_campaign_shell`` idiom ``test_app_dashboard_live.py``/
``test_app_chronicle_live.py`` established.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest
from rich.panel import Panel
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import Label, OptionList, Static

from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView
from babylon.tui.app import ArchiveApp
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.watchlist import InMemoryWatchlistPersistence, WatchlistPersistence

pytestmark = pytest.mark.unit

#: The demo campaign shell always lands on Wayne County first (ruling 3) — the same
#: subject :func:`babylon.tui.dispatch.fixture_subject_views`'s default map resolves.
_HOME_SUBJECT = "county/26163"


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_dashboard_live.py``'s own
    fixture. This unit adds no new ``CampaignHandle`` member (watchlist wiring lives entirely
    at the ``ArchiveApp`` composition-root level), so this double is unchanged in shape from
    every sibling live-wiring test file's own fake."""

    def __init__(self, session_id: UUID, pages: dict[str, str]) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages

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
    subject_views: dict[str, object] | None = None,
) -> ArchiveApp:
    menu = _seeded_menu(campaign_id)
    campaign = _FakeCampaign(
        campaign_id,
        {
            f"briefing/{campaign_id}": "# OPERATION WATCHLIST\n",
            _HOME_SUBJECT: "# Wayne\n",
        },
    )
    loader = _FakeLoader(campaign)
    return ArchiveApp(
        campaign_menu=menu,
        campaign_loader=loader,
        watchlist_persistence=watchlist_persistence,
        subject_views=subject_views,
    )


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _rail_text(app: ArchiveApp) -> str:
    """The right rail's plain text — mirrors ``test_app_chronicle_live.py``'s own
    ``_rail_content``: ``Static.content`` (not ``.render()``, which wraps the
    renderable in a ``Visual``) hands back the exact object
    :meth:`~babylon.tui.app.ArchiveApp._refresh_watchlist` passed to ``.update()``
    (a bare :class:`~rich.text.Text` for the absence fence, a
    :class:`~rich.panel.Panel` once something is pinned — same shape
    :func:`~babylon.tui.watchlist.render_watchlist` itself returns)."""
    content = app.query_one("#watchlist-rail", Static).content
    if isinstance(content, Panel):
        title = content.title
        title_plain = title.plain if isinstance(title, Text) else str(title)
        body = content.renderable
        body_plain = body.plain if isinstance(body, Text) else str(body)
        return f"{title_plain}\n{body_plain}"
    if isinstance(content, Text):
        return content.plain
    return str(content)  # pragma: no cover - render_watchlist only ever returns the above two


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
