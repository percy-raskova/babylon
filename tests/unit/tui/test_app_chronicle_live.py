"""Behavioral contract for Program 24 P3 — the live chronicle rail with severity color.

``chronicle.py``'s ``render_chronicle``/``_event_line`` were already pure and complete (P1 wired
the rail's honest ``"the wire is quiet"`` absence at boot — ``test_app_hybrid_shell.py``), and
``TestSeverityColoring`` (``test_chronicle.py``) already pins the per-tier coloring at the
renderer's own unit level. This file closes the remaining gap: the live
:attr:`~babylon.tui.app.TickOutcome.chronicle` seam feeds every advanced tick's real events into
the left rail — through ``t`` (direct campaign advance), ``r`` (the paced driver's
run-until-paused), and staying quiet when a tick genuinely produces nothing — following the exact
``_booted_app``/``_boot_into_campaign_shell`` idiom ``test_app_dashboard_live.py`` established for
Program 24 P2's dashboard seam.

``Static.content`` (not ``.render()``, which wraps the renderable in a ``Visual``) hands back the
exact ``Group``/``Text`` object ``ArchiveApp._refresh_chronicle`` passed to ``.update()`` — the
same object shape ``render_chronicle``/``render_bulletin`` already return, so these tests inspect
it the same way ``test_chronicle.py``'s own ``TestRendering``/``TestSeverityColoring`` do (``Text.
plain`` for content, ``Text.spans`` for the applied severity style).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import OptionList, Static

from babylon.models.enums.events import EventType
from babylon.projection.view_models import EconomyView
from babylon.tui.app import ArchiveApp, CampaignHandle, PacedDriverHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.theme import CRIMSON

pytestmark = pytest.mark.unit


def _event(tick: int, event_type: EventType, *, summary: str) -> ChronicleEvent:
    """Build a :class:`ChronicleEvent` with terser call sites (mirrors ``test_chronicle.py``)."""
    return ChronicleEvent(tick=tick, event_type=event_type, summary=summary)


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_dashboard_live.py``'s own
    fixture, with a caller-supplied ``chronicle_factory`` standing in for a real
    ``GameSession.advance_tick()``'s own ``TickAdvanceResult.chronicle`` (Program 24 P3)."""

    def __init__(
        self,
        session_id: UUID,
        pages: dict[str, str],
        *,
        chronicle_factory: Callable[[int], tuple[ChronicleEvent, ...]],
    ) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self._chronicle_factory = chronicle_factory

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        """No live projection wired for this double — unrelated to this unit's own concern."""
        return None

    def advance_tick(self) -> _FakeTickOutcome:
        self.tick += 1
        return _FakeTickOutcome(
            tick=self.tick, paused=False, chronicle=self._chronicle_factory(self.tick)
        )


class _FakeDriver:
    """A scripted ``PacedDriverHandle`` double (mirrors ``test_app_pacing_driver.py``'s own)."""

    def __init__(self, script: list[_FakeTickOutcome]) -> None:
        self._script = script
        self.locked = False
        self.lock_reason: str | None = None
        self.awaiting_ack = False
        self.busy = False
        self.pause_summary: str | None = None

    def advance_once(self) -> _FakeTickOutcome:
        return self._script.pop(0)

    def run_until_paused(self) -> list[_FakeTickOutcome]:
        results = list(self._script)
        self._script.clear()
        return results

    def acknowledge_pause(self) -> None:  # pragma: no cover - unused by these tests
        self.awaiting_ack = False


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
                slug="campaign-chronicle",
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
    campaign._pages.setdefault(briefing_subject, "# OPERATION CHRONICLE\n")
    campaign._pages.setdefault("county/26163", "# Wayne\n")
    loader = _FakeLoader(campaign)
    app = ArchiveApp(campaign_menu=menu, campaign_loader=loader, driver_factory=driver_factory)
    return app, campaign_id


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _rail_content(app: ArchiveApp) -> Group | Text:
    return app.query_one("#chronicle-rail", Static).content


class TestChronicleRailStaysQuietWithNoEvents:
    @pytest.mark.asyncio
    async def test_a_tick_with_no_events_leaves_the_honest_quiet_state(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, chronicle_factory=lambda _tick: ())
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            content = _rail_content(app)
            assert isinstance(content, Text)
            assert "the wire is quiet" in content.plain


class TestChronicleRailShowsLiveEvents:
    @pytest.mark.asyncio
    async def test_a_critical_event_renders_in_the_crimson_tier(self) -> None:
        event = _event(1, EventType.UPRISING, summary="mass insurrection")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            content = _rail_content(app)
            assert isinstance(content, Group)
            panel = content.renderables[0]
            assert isinstance(panel, Panel)
            body = panel.renderable
            assert isinstance(body, Text)
            assert "mass insurrection" in body.plain
            styles = [span.style for span in body.spans]
            assert f"bold {CRIMSON}" in styles

    @pytest.mark.asyncio
    async def test_ticks_accumulate_newest_tick_first(self) -> None:
        events_by_tick = {
            1: (_event(1, EventType.UPRISING, summary="first tick"),),
            2: (_event(2, EventType.UPRISING, summary="second tick"),),
        }
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: events_by_tick.get(tick, ())
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()
            await pilot.press("t")
            await pilot.pause()

            content = _rail_content(app)
            assert isinstance(content, Group)
            assert len(content.renderables) == 2
            first_panel, second_panel = content.renderables
            assert isinstance(first_panel, Panel)
            assert isinstance(second_panel, Panel)
            assert "second tick" in first_panel.renderable.plain  # newest tick first
            assert "first tick" in second_panel.renderable.plain

    @pytest.mark.asyncio
    async def test_a_quiet_tick_after_history_leaves_the_history_visible(self) -> None:
        event = _event(1, EventType.UPRISING, summary="only tick with an event")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()
            await pilot.press("t")  # tick 2: genuinely no events
            await pilot.pause()

            content = _rail_content(app)
            assert isinstance(content, Group)
            assert len(content.renderables) == 1  # only tick 1 ever produced a bulletin
            assert "only tick with an event" in content.renderables[0].renderable.plain


class TestChronicleRailStaysLiveThroughThePacedDriver:
    @pytest.mark.asyncio
    async def test_run_until_paused_plumbs_every_ticks_chronicle_in_order(self) -> None:
        script = [
            _FakeTickOutcome(
                tick=1, paused=False, chronicle=(_event(1, EventType.UPRISING, summary="run one"),)
            ),
            _FakeTickOutcome(
                tick=2, paused=True, chronicle=(_event(2, EventType.UPRISING, summary="run two"),)
            ),
        ]
        driver = _FakeDriver(script)
        campaign = _FakeCampaign(UUID(int=1), {}, chronicle_factory=lambda _tick: ())
        app, _cid = _booted_app(campaign, driver_factory=lambda _c: driver)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            content = _rail_content(app)
            assert isinstance(content, Group)
            assert len(content.renderables) == 2
            first_panel, second_panel = content.renderables
            assert "run two" in first_panel.renderable.plain  # newest tick first
            assert "run one" in second_panel.renderable.plain
