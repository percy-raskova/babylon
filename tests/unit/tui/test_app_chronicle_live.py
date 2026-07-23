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

Unit "selection-unwrap" (shell-interconnect): ``render_chronicle`` used to return a
``rich.console.Group`` of per-bulletin ``Panel``\\ s; it now returns ONE bare ``Text`` (a
``Panel``/``Group`` is opaque to ``Widget.get_selection`` — only ``Text``/``Content`` qualify), with
each bulletin's own tick number as an inline header line rather than a Panel ``title``.

Unit "chronicle-row-nav-salience" (shell-interconnect): ``#chronicle-rail`` is a row-addressable
``textual.widgets.OptionList`` now (was a plain ``Static``) — mirrors ``test_app_watchlist_live.py``'s
own ``_rail_text`` helper, adapted to gather every option's own prompt instead of one
``Static.content``. This file also newly covers: row-open via Enter/click
(``ArchiveApp.on_option_list_option_selected`` -> ``_navigate``, shared with the watchlist rail), a
non-navigable row's honest disabled no-op, the salience layer (dedupe/volume-floor) actually being
applied before grouping, and the AMBER autopause indicator row.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import ContentSwitcher, OptionList

from babylon.models.enums.events import EventType
from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView, ProjectionRecord
from babylon.tui.app import ArchiveApp, CampaignHandle, PacedDriverHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.theme import AMBER, CRIMSON

pytestmark = pytest.mark.unit


def _event(tick: int, event_type: EventType, *, summary: str, **data: Any) -> ChronicleEvent:
    """Build a :class:`ChronicleEvent` with terser call sites (mirrors ``test_chronicle.py``)."""
    return ChronicleEvent(tick=tick, event_type=event_type, summary=summary, data=data)


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

    def endgame_status(self) -> EndgameStatus | None:
        """No live endgame-progress projection wired for this double — unrelated to this
        unit's own concern (Program 24 P4's ``CampaignHandle.endgame_status`` seam)."""
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        """No live verb plate wired for this double — unrelated to this unit's own
        concern (Program 24 P5's ``CampaignHandle.verb_plate_view`` seam)."""
        return None

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """No live per-subject projection wired for this double — unrelated to this
        unit's own concern (unit "live-subject-view", shell-interconnect's own
        ``CampaignHandle.subject_view`` seam)."""
        return None

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by these tests
        raise AssertionError("issue_verb should not be called by these chronicle tests")

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
    campaign._pages.setdefault("social_class/C001", "# Periphery Proletariat\n")
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


def _rail_text(app: ArchiveApp) -> str:
    """The left rail's plain text — every option's own prompt, joined.

    Unit "chronicle-row-nav-salience" (shell-interconnect): ``#chronicle-rail``
    is a row-addressable :class:`~textual.widgets.OptionList` now (was a plain
    ``Static``), so there is no single ``.content``/``.render()`` to read —
    mirrors ``test_app_watchlist_live.py``'s own ``_rail_text``.
    """
    widget = app.query_one("#chronicle-rail", OptionList)
    rows: list[str] = []
    for index in range(widget.option_count):
        prompt = widget.get_option_at_index(index).prompt
        assert isinstance(prompt, Text)
        rows.append(prompt.plain)
    return "\n".join(rows)


def _row_index(app: ArchiveApp, subject: str) -> int:
    """The option index whose own ``id`` is exactly ``subject`` — asserts exactly one match."""
    widget = app.query_one("#chronicle-rail", OptionList)
    matches = [
        index
        for index in range(widget.option_count)
        if widget.get_option_at_index(index).id == subject
    ]
    assert len(matches) == 1, f"expected exactly one row with id={subject!r}, found {matches}"
    return matches[0]


class TestChronicleRailStaysQuietWithNoEvents:
    @pytest.mark.asyncio
    async def test_a_tick_with_no_events_leaves_the_honest_quiet_state(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, chronicle_factory=lambda _tick: ())
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            assert "the wire is quiet" in _rail_text(app)


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

            widget = app.query_one("#chronicle-rail", OptionList)
            found_styles: list[str] = []
            for index in range(widget.option_count):
                prompt = widget.get_option_at_index(index).prompt
                assert isinstance(prompt, Text)
                if "mass insurrection" in prompt.plain:
                    found_styles.extend(span.style for span in prompt.spans)
            assert f"bold {CRIMSON}" in found_styles

    @pytest.mark.asyncio
    async def test_ticks_accumulate_newest_tick_first(self) -> None:
        # Different node_id per tick: distinct dedup_key's (event_type, subject)
        # pair — otherwise dedupe_consecutive (this unit's own salience wiring)
        # would honestly collapse two adjacent same-key UPRISING events into
        # the first one's row alone, which is not what this test is pinning.
        events_by_tick = {
            1: (_event(1, EventType.UPRISING, summary="first tick", node_id="C001"),),
            2: (_event(2, EventType.UPRISING, summary="second tick", node_id="C002"),),
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

            plain = _rail_text(app)
            assert plain.index("second tick") < plain.index("first tick")  # newest tick first

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

            plain = _rail_text(app)
            assert "only tick with an event" in plain
            assert plain.count("T0001") == 1  # only tick 1 ever produced a bulletin/header
            assert "T0002" not in plain  # tick 2 was genuinely quiet: no bulletin at all


class TestChronicleRailStaysLiveThroughThePacedDriver:
    @pytest.mark.asyncio
    async def test_run_until_paused_plumbs_every_ticks_chronicle_in_order(self) -> None:
        script = [
            _FakeTickOutcome(
                tick=1,
                paused=False,
                chronicle=(_event(1, EventType.UPRISING, summary="run one", node_id="C001"),),
            ),
            _FakeTickOutcome(
                tick=2,
                paused=True,
                chronicle=(_event(2, EventType.UPRISING, summary="run two", node_id="C002"),),
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

            plain = _rail_text(app)
            assert plain.index("run two") < plain.index("run one")  # newest tick first


class TestEmptyChronicleShowsTheHonestAbsenceOnBoot:
    """Unit "chronicle-row-nav-salience": the lone boot-time option IS the
    absence placeholder, disabled and carrying the honest fence text —
    mirrors the watchlist rail's own equivalent boot-time contract."""

    @pytest.mark.asyncio
    async def test_a_freshly_booted_campaign_shows_the_wire_is_quiet(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, chronicle_factory=lambda _tick: ())
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            rail = app.query_one("#chronicle-rail", OptionList)
            assert rail.option_count == 1
            option = rail.get_option_at_index(0)
            assert option.disabled is True
            assert option.id is None
            assert isinstance(option.prompt, Text)
            assert "the wire is quiet" in option.prompt.plain


class TestRowAddressableChronicleOpensTheHighlightedRow:
    """Unit "chronicle-row-nav-salience": Enter (keyboard) and a mouse click
    both resolve to the same ``ArchiveApp.on_option_list_option_selected`` ->
    ``_navigate`` path the watchlist rail already established (R3: mouse and
    keyboard both first-class)."""

    @pytest.mark.asyncio
    async def test_enter_on_a_navigable_row_opens_its_subject(self) -> None:
        event = _event(1, EventType.MASS_AWAKENING, summary="stirs to action", target_id="C001")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            rail = app.query_one("#chronicle-rail", OptionList)
            rail.highlighted = _row_index(app, "social_class/C001")
            rail.focus()
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            assert app.nav.current == "social_class/C001"
            assert app.query_one("#main", ContentSwitcher).current == "wiki"

    @pytest.mark.asyncio
    async def test_a_mouse_click_resolves_through_the_same_option_selected_path_as_enter(
        self,
    ) -> None:
        """Mirrors ``test_app_watchlist_live.py``'s own click-path proof:
        ``OptionList._on_click``'s entire body is ``self.highlighted =
        clicked_option; self.action_select()``, so driving those two calls
        directly IS the click path."""
        event = _event(1, EventType.MASS_AWAKENING, summary="stirs to action", target_id="C001")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            rail = app.query_one("#chronicle-rail", OptionList)
            rail.highlighted = _row_index(app, "social_class/C001")
            rail.action_select()
            await pilot.pause()

            assert app.nav.current == "social_class/C001"

    @pytest.mark.asyncio
    async def test_a_non_navigable_events_row_is_disabled_and_enter_is_a_named_no_op(self) -> None:
        """UPRISING with no anchor carries no dispatchable subject
        (``resolve_navigable_subject`` returns ``None``) — the row stays
        VISIBLE (never dropped) but disabled: ``OptionList.action_select``
        itself refuses to post ``OptionSelected`` for a disabled option, so
        Enter here never navigates anywhere (Constitution III.11: a visible
        row is the honest fence, not a hidden failure)."""
        event = _event(1, EventType.UPRISING, summary="mass insurrection")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()
            before = app.nav.current

            rail = app.query_one("#chronicle-rail", OptionList)
            event_row_index = next(
                index
                for index in range(rail.option_count)
                if "mass insurrection" in rail.get_option_at_index(index).prompt.plain  # type: ignore[union-attr]
            )
            option = rail.get_option_at_index(event_row_index)
            assert option.disabled is True
            assert option.id is None

            rail.highlighted = event_row_index
            rail.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert app.nav.current == before

    @pytest.mark.asyncio
    async def test_the_highlighted_row_survives_a_live_repaint(self) -> None:
        """``_refresh_chronicle`` clears and rebuilds every option on every
        repaint — the previously-highlighted index must survive that rebuild
        (mirrors the watchlist rail's own highlight-preservation contract),
        or a player mid-row-pick would be silently reset on every tick."""
        event = _event(1, EventType.MASS_AWAKENING, summary="stirs", target_id="C001")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            rail = app.query_one("#chronicle-rail", OptionList)
            target_index = _row_index(app, "social_class/C001")
            rail.highlighted = target_index

            app._refresh_chronicle(())  # noqa: SLF001 - white-box repaint trigger, no new events

            assert rail.highlighted == target_index


class TestChronicleSalienceComposition:
    """Unit "chronicle-row-nav-salience": ``_refresh_chronicle`` composes
    ``chronicle_salience.apply_volume_floors``/``dedupe_consecutive`` BEFORE
    grouping into bulletins — these had zero callers before this unit."""

    @pytest.mark.asyncio
    async def test_consecutive_identical_events_collapse_into_one_row(self) -> None:
        """``dedupe_consecutive``: two SURPLUS_EXTRACTION events sharing the
        same ``(event_type, subject)`` key, back to back, collapse to the
        FIRST one's own row only."""
        events = (
            _event(
                1,
                EventType.SURPLUS_EXTRACTION,
                summary="first surplus line",
                source_id="C001",
                target_id="C003",
            ),
            _event(
                1,
                EventType.SURPLUS_EXTRACTION,
                summary="second surplus line",
                source_id="C001",
                target_id="C003",
            ),
        )
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: events if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            plain = _rail_text(app)
            assert "first surplus line" in plain
            assert "second surplus line" not in plain

    @pytest.mark.asyncio
    async def test_informational_events_are_capped_per_tick(self) -> None:
        """``apply_volume_floors``' ``cap_narrative_events``: at most ONE
        informational-tier (SURPLUS_EXTRACTION) row renders per tick — a
        DIFFERENT subject each time, so dedup alone would not collapse them."""
        events = tuple(
            _event(
                1,
                EventType.SURPLUS_EXTRACTION,
                summary=f"surplus line {n}",
                source_id=f"C00{n}",
                target_id="C003",
            )
            for n in range(1, 4)
        )
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: events if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            plain = _rail_text(app)
            assert "surplus line 1" in plain
            assert "surplus line 2" not in plain
            assert "surplus line 3" not in plain


class TestChronicleAutopauseIndicator:
    """Unit "chronicle-row-nav-salience": the AMBER
    ``chronicle_salience.render_autopause_indicator`` cue, wired as its own
    disabled row — had zero callers before this unit."""

    @pytest.mark.asyncio
    async def test_a_critical_tier_event_shows_the_amber_indicator_row(self) -> None:
        event = _event(1, EventType.UPRISING, summary="mass insurrection")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            rail = app.query_one("#chronicle-rail", OptionList)
            option = rail.get_option_at_index(0)
            assert option.disabled is True
            assert isinstance(option.prompt, Text)
            assert "AUTOPAUSE" in option.prompt.plain
            # render_autopause_indicator sets the WHOLE Text's own .style
            # (not a per-span style) — see its own implementation.
            assert option.prompt.style == f"bold {AMBER}"

    @pytest.mark.asyncio
    async def test_no_critical_tier_event_shows_no_indicator_row(self) -> None:
        event = _event(1, EventType.SURPLUS_EXTRACTION, summary="value flows")
        campaign = _FakeCampaign(
            UUID(int=1), {}, chronicle_factory=lambda tick: (event,) if tick == 1 else ()
        )
        app, _cid = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("t")
            await pilot.pause()

            assert "AUTOPAUSE" not in _rail_text(app)
