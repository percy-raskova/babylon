"""Behavioral contract for the shell-interconnect "post-tick-fanout" unit (issue #281).

Both ``ArchiveApp.action_advance_tick``/``action_run_until_paused`` used to inline the same
five-call post-tick refresh sequence (known entities, dashboard, action bar, chronicle, then
the currently-shown subject's dossier) — duplicated verbatim between the two methods, with the
right rail (``ArchiveApp._refresh_watchlist``, wired to ``action_toggle_pin`` at Program 24 P6)
never called from EITHER tick path, so a pinned subject's stat-plate row went stale across
every ``t``/``r``. This file pins two things:

1. The extracted ``_refresh_after_tick`` helper actually repaints the watchlist from BOTH tick
   paths (``TestWatchlistRepaintsAcrossTicks`` below) — mirroring
   ``test_app_dashboard_live.py::TestDashboardStaysLiveAcrossTicks``'s own "stays live across
   ticks" idiom, adapted for the watchlist's own now-live content (unit "live-subject-view",
   shell-interconnect): ``_FakeCampaign`` stores its ``subject_views`` dict as-is at
   construction (never copied), so mutating the SAME dict object a test hands in is a faithful
   proxy for "the live per-subject projector (``GameSession.subject_view``) handed back a fresh
   view this tick" — ``ArchiveApp._resolve_subject_view`` calls ``CampaignHandle.subject_view``
   fresh on every ``_refresh_watchlist``, never a cached snapshot.
2. The shared call order — known entities -> dashboard -> action bar -> chronicle -> watchlist ->
   dossier — survives the extraction identically from both call sites
   (``TestPostTickRefreshOrderIsPreserved`` below).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import OptionList

from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import CountyView, EconomyView, ProjectionRecord
from babylon.tui.app import ArchiveApp, PacedDriverHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent

pytestmark = pytest.mark.unit

#: The demo campaign shell always lands on Wayne County first (ruling 3) — the same
#: subject ``test_app_watchlist_live.py``'s own fixture pins.
_HOME_SUBJECT = "county/26163"


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_watchlist_live.py``'s own
    fixture, including its unit "live-subject-view" ``subject_view`` seam: resolves against
    the caller-supplied ``subject_views`` dict, stored as-is (never copied), so mutating that
    SAME dict object between pilot presses is observable on the very next call."""

    def __init__(
        self,
        session_id: UUID,
        pages: dict[str, str],
        *,
        subject_views: dict[str, ProjectionRecord],
    ) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self._subject_views = subject_views

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
        return self._subject_views.get(subject_id)

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by these tests
        raise AssertionError("issue_verb should not be called by these post-tick-fanout tests")

    def advance_tick(self) -> _FakeTickOutcome:
        self.tick += 1
        return _FakeTickOutcome(tick=self.tick, paused=False)


class _FakeDriver:
    """A scripted ``PacedDriverHandle`` double — mirrors ``test_app_pacing_driver.py``'s own
    fixture."""

    def __init__(self, script: list[_FakeTickOutcome]) -> None:
        self._script = script
        self.locked = False
        self.lock_reason: str | None = None
        self.awaiting_ack = False
        self.busy = False
        self.pause_summary: str | None = None

    def advance_once(self) -> _FakeTickOutcome:
        result = self._script.pop(0)
        if result.paused:
            self.awaiting_ack = True
            self.pause_summary = f"tick {result.tick}: some critical event"
        return result

    def run_until_paused(self) -> list[_FakeTickOutcome]:
        results: list[_FakeTickOutcome] = []
        while self._script:
            result = self._script.pop(0)
            results.append(result)
            if result.paused:
                self.awaiting_ack = True
                self.pause_summary = f"tick {result.tick}: some critical event"
                break
        return results

    def acknowledge_pause(self) -> None:
        self.awaiting_ack = False
        self.pause_summary = None


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
                slug="campaign-post-tick-fanout",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16)


def _booted_app(
    campaign_id: UUID,
    *,
    subject_views: dict[str, ProjectionRecord],
    driver_factory: Callable[[Any], PacedDriverHandle] | None = None,
) -> ArchiveApp:
    menu = _seeded_menu(campaign_id)
    campaign = _FakeCampaign(
        campaign_id,
        {
            f"briefing/{campaign_id}": "# OPERATION POST-TICK\n",
            _HOME_SUBJECT: "# Wayne\n",
        },
        subject_views=subject_views,
    )
    loader = _FakeLoader(campaign)
    return ArchiveApp(
        campaign_menu=menu,
        campaign_loader=loader,
        driver_factory=driver_factory,
    )


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _rail_text(app: ArchiveApp) -> str:
    """The right rail's plain text — mirrors ``test_app_watchlist_live.py``'s own
    ``_rail_text`` (unit "watchlist-row-nav": ``#watchlist-rail`` is a
    row-addressable ``OptionList`` now, so this gathers every option's own
    prompt rather than reading a single ``.content``)."""
    widget = app.query_one("#watchlist-rail", OptionList)
    rows: list[str] = []
    for index in range(widget.option_count):
        prompt = widget.get_option_at_index(index).prompt
        assert isinstance(prompt, Text)
        rows.append(prompt.plain)
    title = widget.border_title or ""
    return f"{title}\n" + "\n".join(rows)


class TestWatchlistRepaintsAcrossTicks:
    """Issue #281: a pinned subject's row must repaint on EVERY committed tick, not only when
    ``action_toggle_pin`` itself runs."""

    @pytest.mark.asyncio
    async def test_advancing_a_tick_with_no_driver_repaints_the_pinned_row(self) -> None:
        campaign_id = UUID(int=1)
        subject_views: dict[str, ProjectionRecord] = {
            _HOME_SUBJECT: CountyView(county_fips="26163", verified_tick=0, population=1000),
        }
        app = _booted_app(campaign_id, subject_views=subject_views)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            assert app.nav.current == _HOME_SUBJECT

            await pilot.press("p")
            await pilot.pause()
            before = _rail_text(app)
            assert "T0000" in before
            assert "population=1000" in before

            # Simulate a live per-subject projector handing back a fresh view this
            # tick — ``ArchiveApp`` stores the exact ``dict`` object given at
            # construction (never copied), so mutating it here is observable on the
            # NEXT ``_refresh_watchlist`` call the same way a real live feed would be.
            subject_views[_HOME_SUBJECT] = CountyView(
                county_fips="26163", verified_tick=1, population=2000
            )

            await pilot.press("t")
            await pilot.pause()

            after = _rail_text(app)
            assert "T0001" in after
            assert "population=2000" in after
            assert "T0000" not in after

    @pytest.mark.asyncio
    async def test_running_until_paused_through_the_driver_repaints_the_pinned_row(self) -> None:
        campaign_id = UUID(int=1)
        subject_views: dict[str, ProjectionRecord] = {
            _HOME_SUBJECT: CountyView(county_fips="26163", verified_tick=0, population=1000),
        }
        driver = _FakeDriver(
            [
                _FakeTickOutcome(tick=1, paused=False),
                _FakeTickOutcome(tick=2, paused=True),
            ]
        )
        app = _booted_app(
            campaign_id, subject_views=subject_views, driver_factory=lambda _c: driver
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("p")
            await pilot.pause()
            assert "T0000" in _rail_text(app)

            subject_views[_HOME_SUBJECT] = CountyView(
                county_fips="26163", verified_tick=2, population=3000
            )

            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            after = _rail_text(app)
            assert "T0002" in after
            assert "population=3000" in after


class TestPostTickRefreshOrderIsPreserved:
    """Guards the exact call order both former inline sequences shared — known entities ->
    dashboard -> action bar -> chronicle -> watchlist -> dossier — against the extraction
    accidentally reshuffling it (a Known Risk the unit spec calls out explicitly)."""

    @staticmethod
    def _track(app: ArchiveApp, monkeypatch: pytest.MonkeyPatch, order: list[str]) -> None:
        def _make_tracked(label: str, original: Callable[..., object]) -> Callable[..., object]:
            def _tracked(*args: object, **kwargs: object) -> object:
                order.append(label)
                return original(*args, **kwargs)

            return _tracked

        for name, label in (
            ("_refresh_known_entities", "known_entities"),
            ("_refresh_dashboard", "dashboard"),
            ("_refresh_action_bar", "action_bar"),
            ("_refresh_chronicle", "chronicle"),
            ("_refresh_watchlist", "watchlist"),
        ):
            original = getattr(app, name)
            monkeypatch.setattr(app, name, _make_tracked(label, original))

        original_navigate = app._navigate

        async def _tracked_navigate(*args: object, **kwargs: object) -> None:
            order.append("dossier")
            await original_navigate(*args, **kwargs)

        monkeypatch.setattr(app, "_navigate", _tracked_navigate)

    @pytest.mark.asyncio
    async def test_advance_tick_refreshes_in_the_documented_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        campaign_id = UUID(int=1)
        subject_views: dict[str, ProjectionRecord] = {
            _HOME_SUBJECT: CountyView(county_fips="26163", verified_tick=0),
        }
        app = _booted_app(campaign_id, subject_views=subject_views)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            order: list[str] = []
            self._track(app, monkeypatch, order)

            await pilot.press("t")
            await pilot.pause()

            assert order == [
                "known_entities",
                "dashboard",
                "action_bar",
                "chronicle",
                "watchlist",
                "dossier",
            ]

    @pytest.mark.asyncio
    async def test_run_until_paused_refreshes_in_the_documented_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        campaign_id = UUID(int=1)
        subject_views: dict[str, ProjectionRecord] = {
            _HOME_SUBJECT: CountyView(county_fips="26163", verified_tick=0),
        }
        driver = _FakeDriver([_FakeTickOutcome(tick=1, paused=True)])
        app = _booted_app(
            campaign_id, subject_views=subject_views, driver_factory=lambda _c: driver
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            order: list[str] = []
            self._track(app, monkeypatch, order)

            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert order == [
                "known_entities",
                "dashboard",
                "action_bar",
                "chronicle",
                "watchlist",
                "dossier",
            ]
