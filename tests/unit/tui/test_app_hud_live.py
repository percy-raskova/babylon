"""Behavioral contract for Program 24 P4 — the live HUD strip.

``DashboardView.render_hud``/``render_hud_text`` (``tui/shell/views/dashboard_view.py``) are
already pure and complete (their own unit tests live in ``tests/unit/tui/shell/
test_dashboard_view.py``), and P1 (``test_app_hybrid_shell.py``) already proved the dashboard
pane mounts an honest ``{absence}`` fence with no live campaign at all. This unit closes the
remaining gap: a LIVE campaign's :meth:`~babylon.tui.app.CampaignHandle.endgame_status` seam
feeds a real :class:`~babylon.projection.endgame.EndgameStatus` into the HUD strip the moment
the player presses ``1``, keeps it live across ``t`` ticks, and reflects the paced driver's real
lock/pause state — following the exact ``TestSeams``/``_booted_app``/``_boot_into_campaign_shell``
idiom ``test_app_dashboard_live.py`` established for Program 24 P2's own dashboard-body seam.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from textual.pilot import Pilot
from textual.widgets import OptionList, Static

from babylon.config.defines import GameDefines
from babylon.models.enums.events import GameOutcome
from babylon.projection.endgame import EndgameStatus, endgame_status
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView
from babylon.tui.app import ArchiveApp, CampaignHandle, PacedDriverHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


def _status(*, tick: int, axes: dict[str, float]) -> EndgameStatus:
    """A real, freshly-folded ``EndgameStatus`` — the same fold ``GameSession.
    endgame_status`` uses live, over the default ``GameDefines``."""
    return endgame_status(
        tick=tick, pattern=None, since_tick=None, defines=GameDefines(), axes=axes
    )


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_dashboard_live.py``'s own
    fixture, with an ``endgame_factory`` standing in for a real ``GameSession.
    endgame_status()``'s own fresh-every-call fold (Program 24 P4)."""

    def __init__(
        self,
        session_id: UUID,
        pages: dict[str, str],
        *,
        endgame_factory: Callable[[int], EndgameStatus | None],
    ) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self._endgame_factory = endgame_factory
        self.endgame_calls = 0

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        """No live economy projection wired for this double — unrelated to this unit's
        own concern (Program 24 P2's own seam)."""
        return None

    def endgame_status(self) -> EndgameStatus | None:
        self.endgame_calls += 1
        return self._endgame_factory(self.tick)

    def verb_plate_view(self) -> VerbPlateView | None:
        """No live verb plate wired for this double — unrelated to this unit's own
        concern (Program 24 P5's ``CampaignHandle.verb_plate_view`` seam)."""
        return None

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by these tests
        raise AssertionError("issue_verb should not be called by these HUD tests")

    def advance_tick(self) -> _FakeTickOutcome:
        self.tick += 1
        return _FakeTickOutcome(tick=self.tick, paused=False)


class _FakeDriver:
    """A minimal ``PacedDriverHandle`` double — settable lock/pause state, and
    ``advance_once`` that advances the SAME ``_FakeCampaign`` it wraps (mirrors
    ``test_app_pacing_driver.py``'s own ``_FakeDriver`` shape, trimmed to what this
    unit's own tests need)."""

    def __init__(
        self,
        campaign: _FakeCampaign,
        *,
        locked: bool = False,
        lock_reason: str | None = None,
        awaiting_ack: bool = False,
        busy: bool = False,
        pause_summary: str | None = None,
    ) -> None:
        self._campaign = campaign
        self.locked = locked
        self.lock_reason = lock_reason
        self.awaiting_ack = awaiting_ack
        self.busy = busy
        self.pause_summary = pause_summary

    def advance_once(self) -> _FakeTickOutcome:
        return self._campaign.advance_tick()

    def run_until_paused(self) -> list[_FakeTickOutcome]:
        return [self._campaign.advance_tick()]

    def acknowledge_pause(self) -> None:
        self.awaiting_ack = False
        self.pause_summary = None


class _FakeLoader:
    def __init__(self, campaign: _FakeCampaign) -> None:
        self._campaign = campaign

    def __call__(self, campaign_id: UUID) -> _FakeCampaign:
        return self._campaign


def _seeded_menu() -> tuple[CampaignMenu, UUID]:
    campaign_id = UUID(int=1)
    catalog = InMemoryCampaignCatalog(
        seed=(
            InMemoryCampaign(
                campaign_id=campaign_id,
                slug="campaign-hud",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


def _booted_app(
    campaign: _FakeCampaign,
    *,
    driver_factory: Callable[[CampaignHandle], PacedDriverHandle] | None = None,
) -> tuple[ArchiveApp, UUID]:
    menu, campaign_id = _seeded_menu()
    briefing_subject = f"briefing/{campaign_id}"
    campaign._pages.setdefault(briefing_subject, "# OPERATION HUD\n")
    campaign._pages.setdefault("county/26163", "# Wayne\n")
    loader = _FakeLoader(campaign)
    return (
        ArchiveApp(campaign_menu=menu, campaign_loader=loader, driver_factory=driver_factory),
        campaign_id,
    )


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


class TestSeams:
    def test_fake_campaign_satisfies_campaign_handle(self) -> None:
        campaign = _FakeCampaign(UUID(int=2), {}, endgame_factory=lambda _tick: None)
        assert isinstance(campaign, CampaignHandle)

    def test_fake_driver_satisfies_paced_driver_handle(self) -> None:
        campaign = _FakeCampaign(UUID(int=2), {}, endgame_factory=lambda _tick: None)
        assert isinstance(_FakeDriver(campaign), PacedDriverHandle)


class TestPressingOneShowsTheLiveAxisProgress:
    @pytest.mark.asyncio
    async def test_tick_horizon_and_all_five_axes_render_from_the_live_projection(self) -> None:
        axes = {
            "revolutionary_victory": 0.3,
            "ecological_collapse": 0.0,
            "fascist_consolidation": 0.6,
            "red_ogv": 0.0,
            "fragmented_collapse": 0.1,
        }
        campaign = _FakeCampaign(
            UUID(int=1), {}, endgame_factory=lambda tick: _status(tick=tick, axes=axes)
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-hud", Static).render())
            expected_horizon = _status(tick=0, axes=axes).horizon_tick
            assert f"T+0/{expected_horizon}" in body
            assert "REVOLUTIONARY VICTORY" in body
            assert "0.30" in body
            assert "FASCIST CONSOLIDATION" in body
            assert "0.60" in body
            assert campaign.endgame_calls >= 1


class TestHudStaysLiveAcrossTicks:
    @pytest.mark.asyncio
    async def test_advancing_a_tick_refreshes_the_visible_hud_counter(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1), {}, endgame_factory=lambda tick: _status(tick=tick, axes={})
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("1")
            await pilot.pause()

            before = str(app.query_one("#dashboard-hud", Static).render())
            assert "T+0/" in before

            await pilot.press("t")
            await pilot.pause()

            after = str(app.query_one("#dashboard-hud", Static).render())
            assert "T+1/" in after
            assert campaign.endgame_calls >= 2


class TestHudShowsTheRealPacingLockState:
    @pytest.mark.asyncio
    async def test_a_locked_driver_shows_locked_and_its_reason(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1), {}, endgame_factory=lambda tick: _status(tick=tick, axes={})
        )

        def factory(booted: CampaignHandle) -> PacedDriverHandle:
            return _FakeDriver(
                booted,  # type: ignore[arg-type]
                locked=True,
                lock_reason=GameOutcome.FASCIST_CONSOLIDATION,
            )

        app, _campaign_id = _booted_app(campaign, driver_factory=factory)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-hud", Static).render())
            assert "LOCKED" in body
            assert "fascist_consolidation" in body

    @pytest.mark.asyncio
    async def test_an_awaiting_ack_driver_shows_the_pause_summary(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1), {}, endgame_factory=lambda tick: _status(tick=tick, axes={})
        )

        def factory(booted: CampaignHandle) -> PacedDriverHandle:
            return _FakeDriver(
                booted,  # type: ignore[arg-type]
                awaiting_ack=True,
                pause_summary="tick 3: some critical event",
            )

        app, _campaign_id = _booted_app(campaign, driver_factory=factory)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-hud", Static).render())
            assert "autopause pending" in body
            assert "tick 3: some critical event" in body

    @pytest.mark.asyncio
    async def test_no_driver_wired_shows_the_honest_no_driver_absence(self) -> None:
        """Pre-Unit-C3 default (no ``driver_factory``): the HUD's pacing line must
        say so honestly — never conflated with a driver that happens to be idle."""
        campaign = _FakeCampaign(
            UUID(int=1), {}, endgame_factory=lambda tick: _status(tick=tick, axes={})
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-hud", Static).render())
            assert "no paced driver attached" in body


class TestHonestAbsenceWhenTheCampaignDeclinesAProjection:
    """A live, booted campaign whose composition root chose not to wire a live endgame
    projection at all (``endgame_status()`` returns ``None``) must leave the HUD's existing
    honest-absence fence untouched — never a blank or crashed repaint."""

    @pytest.mark.asyncio
    async def test_pressing_one_keeps_the_hud_absence_fence(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, endgame_factory=lambda _tick: None)
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-hud", Static).render())
            assert "no EndgameStatus projected yet" in body
            assert campaign.endgame_calls >= 1
