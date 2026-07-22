"""``ArchiveApp``'s paced-driver seam (Program v1.0.0 Unit T4-core/C3).

Drives :class:`~babylon.tui.app.ArchiveApp`'s ``t``/``r``/``a`` bindings
through a fake :class:`~babylon.tui.app.PacedDriverHandle`
(:class:`_FakeDriver`) — no real engine, Postgres, or Textual worker thread
required beyond what Textual's own test harness already provides. Follows
the exact ``TestSeams``/lobby-flow idiom
``tests/unit/tui/test_app_lobby_flow.py`` already established for
:class:`~babylon.tui.app.CampaignHandle`.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest
from textual.widgets import Label, OptionList

from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView
from babylon.tui.app import ArchiveApp, CampaignHandle, PacedDriverHandle, TickOutcome
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_lobby_flow.
    py``'s own fixture."""

    def __init__(self, session_id: UUID, pages: dict[str, str]) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        """No live projection wired for this double — honest ``None``
        (Program 24 P2's ``CampaignHandle.dashboard_view`` seam)."""
        return None

    def endgame_status(self) -> EndgameStatus | None:
        """No live endgame-progress projection wired for this double — honest ``None``
        (Program 24 P4's ``CampaignHandle.endgame_status`` seam)."""
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        """No live verb plate wired for this double — honest ``None``
        (Program 24 P5's ``CampaignHandle.verb_plate_view`` seam)."""
        return None

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by these tests
        raise AssertionError("issue_verb should not be called by these pacing-driver tests")

    def advance_tick(self) -> _FakeTickOutcome:  # pragma: no cover - unused once a driver is wired
        raise AssertionError("campaign.advance_tick() called directly while a driver was wired")


class _FakeDriver:
    """A scripted ``PacedDriverHandle`` double.

    ``script`` is a list of ``_FakeTickOutcome``\\ s consumed one at a time
    by :meth:`advance_once`; :meth:`run_until_paused` consumes the REST of
    the script in one call (mirroring the real driver's "advance until
    paused/locked/exhausted" semantics closely enough for these seam
    tests, which never exercise :mod:`babylon.game.pacing` itself — that
    lives in ``tests/unit/game/test_pacing.py``).
    """

    def __init__(self, script: list[_FakeTickOutcome]) -> None:
        self._script = script
        self.locked = False
        self.lock_reason: str | None = None
        self.awaiting_ack = False
        self.busy = False
        self.pause_summary: str | None = None
        self.advance_calls = 0
        self.run_calls = 0
        self.acknowledge_calls = 0

    def advance_once(self) -> _FakeTickOutcome:
        self.advance_calls += 1
        result = self._script.pop(0)
        if result.paused:
            self.awaiting_ack = True
            self.pause_summary = f"tick {result.tick}: some critical event"
        return result

    def run_until_paused(self) -> list[_FakeTickOutcome]:
        self.run_calls += 1
        results = []
        while self._script:
            result = self._script.pop(0)
            results.append(result)
            if result.paused:
                self.awaiting_ack = True
                self.pause_summary = f"tick {result.tick}: some critical event"
                break
        return results

    def acknowledge_pause(self) -> None:
        self.acknowledge_calls += 1
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
                slug="campaign-one",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


async def _boot_into_campaign_shell(pilot: object, app: ArchiveApp) -> None:
    """Walk the lobby -> briefing -> shell flow (mirrors ``test_app_lobby_
    flow.py``'s own repeated sequence)."""
    await pilot.pause()  # type: ignore[attr-defined]
    app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # type: ignore[attr-defined]
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.press("enter")  # type: ignore[attr-defined]
    await pilot.pause()  # type: ignore[attr-defined]


class TestSeams:
    def test_fake_driver_satisfies_paced_driver_handle(self) -> None:
        assert isinstance(_FakeDriver([]), PacedDriverHandle)


class TestConstructorValidation:
    def test_driver_factory_without_a_campaign_loader_raises(self) -> None:
        with pytest.raises(ValueError, match="driver_factory"):
            ArchiveApp(driver_factory=lambda _c: _FakeDriver([]))

    def test_no_driver_factory_is_the_pre_c3_default(self) -> None:
        app = ArchiveApp()
        assert app.driver is None


class TestDriverWiring:
    @pytest.mark.asyncio
    async def test_beginning_the_operation_wires_the_driver_over_the_booted_campaign(
        self,
    ) -> None:
        menu, campaign_id = _seeded_menu()
        briefing_subject = f"briefing/{campaign_id}"
        campaign = _FakeCampaign(
            campaign_id, {briefing_subject: "# OPERATION TEST\n", "county/26163": "# Wayne\n"}
        )
        loader = _FakeLoader(campaign)
        seen_campaigns: list[CampaignHandle] = []

        def factory(booted: CampaignHandle) -> PacedDriverHandle:
            seen_campaigns.append(booted)
            return _FakeDriver([])

        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader, driver_factory=factory)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            assert app.driver is not None
            assert seen_campaigns == [campaign]

    @pytest.mark.asyncio
    async def test_no_driver_factory_leaves_driver_none_even_with_a_live_campaign(self) -> None:
        menu, campaign_id = _seeded_menu()
        briefing_subject = f"briefing/{campaign_id}"
        campaign = _FakeCampaign(
            campaign_id, {briefing_subject: "# OPERATION TEST\n", "county/26163": "# Wayne\n"}
        )
        loader = _FakeLoader(campaign)
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            assert app.campaign is campaign
            assert app.driver is None


def _wired_app(
    driver: _FakeDriver, *, pages: dict[str, str] | None = None
) -> tuple[ArchiveApp, _FakeCampaign, UUID]:
    menu, campaign_id = _seeded_menu()
    briefing_subject = f"briefing/{campaign_id}"
    base_pages = {briefing_subject: "# OPERATION TEST\n", "county/26163": "# Wayne\n"}
    if pages:
        base_pages.update(pages)
    campaign = _FakeCampaign(campaign_id, base_pages)
    loader = _FakeLoader(campaign)
    app = ArchiveApp(campaign_menu=menu, campaign_loader=loader, driver_factory=lambda _c: driver)
    return app, campaign, campaign_id


class TestExplicitAdvanceThroughTheDriver:
    @pytest.mark.asyncio
    async def test_t_advances_through_the_driver_not_the_campaign_directly(self) -> None:
        driver = _FakeDriver([_FakeTickOutcome(tick=1, paused=False)])
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("t")
            await pilot.pause()

            assert driver.advance_calls == 1
            status = app.query_one("#status", Label)
            assert "tick 1" in str(status.content)

    @pytest.mark.asyncio
    async def test_t_reports_a_loud_status_when_the_driver_is_locked(self) -> None:
        driver = _FakeDriver([])
        driver.locked = True
        driver.lock_reason = "red_ogv"
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("t")
            await pilot.pause()

            assert driver.advance_calls == 0
            status = app.query_one("#status", Label)
            assert "campaign ended" in str(status.content)
            assert "red_ogv" in str(status.content)

    @pytest.mark.asyncio
    async def test_t_reports_a_loud_status_when_awaiting_ack(self) -> None:
        driver = _FakeDriver([])
        driver.awaiting_ack = True
        driver.pause_summary = "tick 3: ENDGAME_REACHED"
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("t")
            await pilot.pause()

            assert driver.advance_calls == 0
            status = app.query_one("#status", Label)
            assert "autopause pending" in str(status.content)
            assert "ENDGAME_REACHED" in str(status.content)

    @pytest.mark.asyncio
    async def test_t_reports_a_loud_status_when_the_driver_is_busy(self) -> None:
        """A background ``r`` worker still in flight must not let ``t``
        race a second concurrent advance against it (the Re-entrancy
        note)."""
        driver = _FakeDriver([_FakeTickOutcome(tick=1, paused=False)])
        driver.busy = True
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("t")
            await pilot.pause()

            assert driver.advance_calls == 0
            status = app.query_one("#status", Label)
            assert "already in progress" in str(status.content)


class TestRunUntilPaused:
    @pytest.mark.asyncio
    async def test_r_runs_the_driver_as_a_worker_until_autopause(self) -> None:
        driver = _FakeDriver(
            [
                _FakeTickOutcome(tick=1, paused=False),
                _FakeTickOutcome(tick=2, paused=False),
                _FakeTickOutcome(tick=3, paused=True),
            ]
        )
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert driver.run_calls == 1
            assert driver.awaiting_ack is True
            status = app.query_one("#status", Label)
            assert "tick 3" in str(status.content)
            assert "PAUSED" in str(status.content)

    @pytest.mark.asyncio
    async def test_r_refuses_a_second_run_while_the_driver_is_already_busy(self) -> None:
        """The second worker Task must see :attr:`busy` and refuse rather
        than the app relying on ``exclusive`` cancellation (which cannot
        actually stop the executor thread underneath — the Re-entrancy
        note)."""
        driver = _FakeDriver([_FakeTickOutcome(tick=1, paused=False)])
        driver.busy = True
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert driver.run_calls == 0
            status = app.query_one("#status", Label)
            assert "already in progress" in str(status.content)

    @pytest.mark.asyncio
    async def test_r_reports_a_loud_status_with_no_driver(self) -> None:
        menu, campaign_id = _seeded_menu()
        campaign = _FakeCampaign(campaign_id, {f"briefing/{campaign_id}": "# OP\n"})
        app = ArchiveApp(campaign_menu=menu, campaign_loader=_FakeLoader(campaign))

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            status = app.query_one("#status", Label)
            assert "no paced driver attached" in str(status.content)

    @pytest.mark.asyncio
    async def test_r_refuses_to_start_a_new_run_while_locked(self) -> None:
        driver = _FakeDriver([])
        driver.locked = True
        driver.lock_reason = "fascist_consolidation"
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert driver.run_calls == 0
            status = app.query_one("#status", Label)
            assert "campaign ended" in str(status.content)


class TestAcknowledgePause:
    @pytest.mark.asyncio
    async def test_a_acknowledges_a_pending_pause_and_permits_the_next_advance(self) -> None:
        driver = _FakeDriver([_FakeTickOutcome(tick=2, paused=False)])
        driver.awaiting_ack = True
        driver.pause_summary = "tick 1: ENDGAME_REACHED"
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("a")
            await pilot.pause()

            assert driver.acknowledge_calls == 1
            assert driver.awaiting_ack is False
            status = app.query_one("#status", Label)
            assert "acknowledged" in str(status.content)

            await pilot.press("t")
            await pilot.pause()
            assert driver.advance_calls == 1

    @pytest.mark.asyncio
    async def test_a_reports_a_loud_status_when_nothing_is_pending(self) -> None:
        driver = _FakeDriver([])
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("a")
            await pilot.pause()

            assert driver.acknowledge_calls == 0
            status = app.query_one("#status", Label)
            assert "no autopause pending" in str(status.content)

    @pytest.mark.asyncio
    async def test_a_reports_a_loud_status_with_no_driver(self) -> None:
        menu, campaign_id = _seeded_menu()
        campaign = _FakeCampaign(campaign_id, {f"briefing/{campaign_id}": "# OP\n"})
        app = ArchiveApp(campaign_menu=menu, campaign_loader=_FakeLoader(campaign))

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("a")
            await pilot.pause()

            status = app.query_one("#status", Label)
            assert "no paced driver attached" in str(status.content)


class TestAdvanceDoesNotClobberANonWikiPane:
    """Unit "navigate-pane-couple" (shell-interconnect): ``_navigate``'s new
    pane-reveal (unconditional for jumplist/palette/wikilink navigation)
    must NOT apply to the post-tick "refresh the currently-shown subject in
    place" calls here — a player deliberately parked on the Dashboard/Map/
    Topology pane watching its own live refresh must never be yanked back
    to the Wiki pane just because a tick advanced."""

    @pytest.mark.asyncio
    async def test_t_refreshes_the_dossier_without_switching_away_from_dashboard(self) -> None:
        from textual.widgets import ContentSwitcher

        driver = _FakeDriver([_FakeTickOutcome(tick=1, paused=False)])
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("1")
            assert app.query_one("#main", ContentSwitcher).current == "dashboard"

            await pilot.press("t")
            await pilot.pause()

            assert driver.advance_calls == 1
            assert app.query_one("#main", ContentSwitcher).current == "dashboard"

    @pytest.mark.asyncio
    async def test_r_refreshes_the_dossier_without_switching_away_from_topology(self) -> None:
        from textual.widgets import ContentSwitcher

        driver = _FakeDriver(
            [_FakeTickOutcome(tick=1, paused=False), _FakeTickOutcome(tick=2, paused=True)]
        )
        app, _campaign, _cid = _wired_app(driver)

        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            await pilot.press("4")
            assert app.query_one("#main", ContentSwitcher).current == "topology"

            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert driver.run_calls == 1
            assert app.query_one("#main", ContentSwitcher).current == "topology"


class TestTickOutcomeConformance:
    def test_fake_tick_outcome_satisfies_tick_outcome(self) -> None:
        assert isinstance(_FakeTickOutcome(tick=1, paused=False), TickOutcome)
