"""Behavioral contract for Program 24 P5 — the live action bar + its write path.

``render_verb_plate``/``build_verb_plate`` (WO-26/WO-38) were already pure, complete, and
independently tested (``test_verb_plate.py``), and P1 (``test_app_hybrid_shell.py``) already
proved the bottom bar mounts its honest ``{absence}`` fence with no live campaign at all. This
unit closes the remaining gap: a LIVE campaign's :meth:`~babylon.tui.app.CampaignHandle.
verb_plate_view` seam feeds a real :class:`~babylon.projection.verbs.view_models.VerbPlateView`
into the bar the moment the shell reveals (and keeps it live across ``t`` ticks), and
:meth:`~babylon.tui.app.ArchiveApp.action_issue_verb` (bound ``F1``-``F9``) is the FIRST time the
player can act on the world from this shell — following the exact ``TestSeams``/``_booted_app``/
``_boot_into_campaign_shell`` idiom ``test_app_dashboard_live.py`` established for Program 24 P2's
own dashboard-body seam.

The Wayne/barren fixture graphs mirror ``test_verb_plate.py``'s own two personas verbatim (all
nine verbs eligible vs. almost nothing eligible) so this file exercises the SAME eligibility
predicates the plate's own contract tests already pin, rather than a hand-typed lookalike.

Unit "selection-unwrap" (shell-interconnect): ``render_verb_plate`` used to return a
``rich.panel.Panel`` with the org/tick header as its ``title``; it now returns a bare ``Text``
(a ``Panel`` is opaque to ``Widget.get_selection``), with the header moved to
:func:`~babylon.tui.verb_plate.verb_plate_title`, assigned to the bar's own ``border_title`` by
``ArchiveApp._refresh_action_bar``. ``_action_bar_text`` below reads both (content +
``border_title``) and joins them the same way the old combined string did, so every
pre-existing assertion here keeps working unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import Label, OptionList, Static

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.plate import build_verb_plate
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView
from babylon.topology import BabylonGraph
from babylon.tui.app import ArchiveApp, CampaignHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent

pytestmark = pytest.mark.unit

ORG = "org-wayne-vanguard"
TERRITORY = "T26163"


def _wayne_graph() -> BabylonGraph:
    """Wayne County (FIPS 26163) tick-0: every verb eligible via TENANCY (mirrors
    ``test_verb_plate.py``'s own ``_wayne_graph`` fixture verbatim)."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="Wayne County Tenants Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[TERRITORY],
    )
    graph.add_node(TERRITORY, NodeType.TERRITORY, county_fips="26163")
    graph.add_node(
        "sc-wayne-proles",
        NodeType.SOCIAL_CLASS,
        name="Wayne proletariat",
        population=1000,
    )
    graph.add_edge("sc-wayne-proles", TERRITORY, EdgeType.TENANCY)
    graph.add_node(
        "org-shop",
        NodeType.ORGANIZATION,
        name="Chamber of Commerce",
        org_type="business",
        territory_ids=[TERRITORY],
    )
    graph.add_node(
        "inst-court",
        NodeType.INSTITUTION,
        name="Wayne County Court",
        territory_ids=[TERRITORY],
    )
    return graph


def _barren_graph() -> BabylonGraph:
    """The org alone in an empty world — almost nothing is eligible (mirrors
    ``test_verb_plate.py``'s own ``_barren_graph`` fixture verbatim)."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="Wayne County Tenants Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[],
    )
    return graph


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_dashboard_live.py``'s own
    fixture, with a caller-supplied ``plate_factory`` standing in for a real ``GameSession.
    verb_plate_view()``'s own fresh-every-call fold (Program 24 P5), and its own
    ``issue_verb`` recording every action id it was asked to issue — a fake/recording
    handle proving the action bar's write path REACHES this seam, never a real
    ``submit_turn``/Postgres write."""

    def __init__(
        self,
        session_id: UUID,
        pages: dict[str, str],
        *,
        plate_factory: Callable[[int], VerbPlateView | None],
        issue_verb_impl: Callable[[str], int] | None = None,
    ) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self._plate_factory = plate_factory
        self._issue_verb_impl = issue_verb_impl
        self.issue_calls: list[str] = []
        self.plate_calls = 0

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        """No live economy projection wired for this double — unrelated to this unit's
        own concern (Program 24 P2's own seam)."""
        return None

    def endgame_status(self) -> EndgameStatus | None:
        """No live endgame-progress projection wired for this double — unrelated to this
        unit's own concern (Program 24 P4's own seam)."""
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        self.plate_calls += 1
        return self._plate_factory(self.tick)

    def issue_verb(self, action_id: str) -> int:
        self.issue_calls.append(action_id)
        if self._issue_verb_impl is not None:
            return self._issue_verb_impl(action_id)
        return len(self.issue_calls)

    def advance_tick(self) -> _FakeTickOutcome:
        self.tick += 1
        return _FakeTickOutcome(tick=self.tick, paused=False)


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
                slug="campaign-action-bar",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


def _booted_app(campaign: _FakeCampaign) -> tuple[ArchiveApp, UUID]:
    menu, campaign_id = _seeded_menu()
    briefing_subject = f"briefing/{campaign_id}"
    campaign._pages.setdefault(briefing_subject, "# OPERATION ACTION BAR\n")
    campaign._pages.setdefault("county/26163", "# Wayne\n")
    loader = _FakeLoader(campaign)
    return ArchiveApp(campaign_menu=menu, campaign_loader=loader), campaign_id


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _action_bar_text(app: ArchiveApp) -> str:
    """The bar's plain rendered text (title + body) — ``Static.content`` (not
    ``.render()``, which wraps a Rich renderable in an opaque ``Visual``; see this
    file's own module docstring / ``test_app_chronicle_live.py``'s identical note)
    hands back the exact object :meth:`~babylon.tui.app.ArchiveApp._refresh_action_bar`
    passed to ``.update()`` — a live bare :class:`~rich.text.Text` (``render_verb_plate``'s
    own return shape, mirroring ``test_verb_plate.py``'s own ``_lines_of`` helper) or the
    plain :data:`~babylon.tui.app._ACTION_BAR_ABSENT` string when no live plate is wired.
    The bar's ``border_title`` (:func:`~babylon.tui.verb_plate.verb_plate_title`, the
    org/tick header that used to live in the old Panel's own ``title=``) is joined in
    front, so every pre-existing tick-stamp assertion below keeps working unchanged."""
    widget = app.query_one("#action-bar", Static)
    content = widget.content
    body_plain = content.plain if isinstance(content, Text) else str(content)
    title = widget.border_title or ""
    return f"{title}\n{body_plain}"


class TestSeams:
    def test_fake_campaign_satisfies_campaign_handle(self) -> None:
        campaign = _FakeCampaign(UUID(int=2), {}, plate_factory=lambda _tick: None)
        assert isinstance(campaign, CampaignHandle)


class TestActionBarPaintsLiveOnBoot:
    @pytest.mark.asyncio
    async def test_the_shell_reveal_paints_the_real_verb_plate(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            plate_factory=lambda tick: build_verb_plate(_wayne_graph(), ORG, tick=tick),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            body = _action_bar_text(app)
            assert "Educate" in body
            assert "✓ legal" in body
            assert campaign.plate_calls >= 1


class TestEligibleVerbReachesIssueVerb:
    @pytest.mark.asyncio
    async def test_pressing_f1_issues_educate_through_the_real_seam(self) -> None:
        """Every verb is eligible on the Wayne fixture (mirrors ``test_verb_plate.py``'s own
        tick-0 assertion) — pressing F1 (``educate``, the first canonical verb) must reach
        :meth:`CampaignHandle.issue_verb`, never a silent no-op."""
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            plate_factory=lambda tick: build_verb_plate(_wayne_graph(), ORG, tick=tick),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("f1")
            await pilot.pause()

            assert campaign.issue_calls == ["educate"]
            status = str(app.query_one("#status", Label).render())
            assert "educate queued" in status
            assert "turn #1" in status

    @pytest.mark.asyncio
    async def test_a_refusal_raised_by_issue_verb_surfaces_loudly_not_a_crash(self) -> None:
        """``CampaignHandle.issue_verb`` can still refuse (e.g. the org can no longer afford
        it) even for an ELIGIBLE row — the app must show the refusal, never crash."""

        def _refuse(_action_id: str) -> int:
            raise ValueError("Cannot afford 'educate': insufficient budget")

        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            plate_factory=lambda tick: build_verb_plate(_wayne_graph(), ORG, tick=tick),
            issue_verb_impl=_refuse,
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("f1")
            await pilot.pause()

            status = str(app.query_one("#status", Label).render())
            assert "educate refused" in status
            assert "insufficient budget" in status


class TestIneligibleVerbShowsRefusalWithoutIssuing:
    @pytest.mark.asyncio
    async def test_pressing_f1_on_a_barren_world_shows_the_reason_never_calls_issue_verb(
        self,
    ) -> None:
        """``educate`` is ineligible on the barren fixture (mirrors ``test_verb_plate.py``'s own
        barren-world assertion) — the plate already computed WHY; the app must show that reason
        without ever attempting :meth:`CampaignHandle.issue_verb` (Constitution III.11: a blocked
        verb shows why, it does not silently no-op)."""
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            plate_factory=lambda tick: build_verb_plate(_barren_graph(), ORG, tick=tick),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            view = build_verb_plate(_barren_graph(), ORG, tick=0)
            assert view is not None
            expected_reason = next(row.reason for row in view.verbs if row.verb == "educate")
            assert expected_reason is not None

            await pilot.press("f1")
            await pilot.pause()

            assert campaign.issue_calls == []
            status = str(app.query_one("#status", Label).render())
            assert "educate refused" in status
            assert expected_reason in status


class TestActionBarStaysLiveAcrossTicks:
    @pytest.mark.asyncio
    async def test_advancing_a_tick_repaints_the_action_bar(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            plate_factory=lambda tick: build_verb_plate(_wayne_graph(), ORG, tick=tick),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            calls_after_boot = campaign.plate_calls
            assert calls_after_boot >= 1

            await pilot.press("t")
            await pilot.pause()

            body = _action_bar_text(app)
            assert f"T{campaign.tick:04d}" in body
            assert campaign.plate_calls > calls_after_boot


class TestHonestAbsenceWhenTheCampaignDeclinesAProjection:
    """A live, booted campaign whose composition root chose not to wire a live plate
    (``verb_plate_view()`` returns ``None``, mirroring every OTHER ``CampaignHandle`` test
    double in this suite) must leave the bar's existing honest-absence fence untouched, and
    pressing a verb key must refuse loudly rather than crash."""

    @pytest.mark.asyncio
    async def test_the_absence_fence_survives_the_shell_reveal(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, plate_factory=lambda _tick: None)
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            body = _action_bar_text(app)
            assert "no verb plate wired yet" in body
            assert campaign.plate_calls >= 1

    @pytest.mark.asyncio
    async def test_pressing_a_verb_key_with_no_plate_refuses_without_a_crash(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, plate_factory=lambda _tick: None)
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("f1")
            await pilot.pause()

            assert campaign.issue_calls == []
            status = str(app.query_one("#status", Label).render())
            assert "cannot issue an action" in status


class TestNoLiveCampaignRefusesLoudly:
    """The pre-Program-24-P5 demo boot path (no ``campaign_menu``) — pressing a verb key
    must never crash, matching every other action's ``no live campaign`` refusal."""

    @pytest.mark.asyncio
    async def test_pressing_f1_with_no_campaign_shows_a_loud_refusal(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("f1")
            await pilot.pause()

            status = str(app.query_one("#status", Label).render())
            assert "no live campaign attached" in status
