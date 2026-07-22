"""Behavioral contract for Program 24 P2 — the live dashboard HUD.

``DashboardView.render_economy_text`` (``tui/shell/views/dashboard_view.py``) was already pure
and complete, and P1 (``test_app_hybrid_shell.py``) already proved the pane mounts its honest
``{absence}`` fence with no live campaign at all. This unit closes the remaining gap: a LIVE
campaign's :meth:`~babylon.tui.app.CampaignHandle.dashboard_view` seam feeds a real
:class:`~babylon.projection.view_models.EconomyView` into the pane the moment the player presses
``1``, and keeps it live across ``t``/``r`` ticks — following the exact ``TestSeams``/lobby-flow
idiom ``tests/unit/tui/test_app_lobby_flow.py`` established for :class:`~babylon.tui.app.
CampaignHandle`, and ``test_t3_live_reachability.py``'s convention of building fixture
``EconomyView``\\ s through real hydration rather than hand-typed lookalikes.

The Φ tri-decomposition fields (``phi_unequal_exchange``/``phi_reproduction``/``phi_domestic``)
are left unset in every fixture below quite deliberately: they have NO producer anywhere in the
engine as of 2026-07-22 (verified tree-wide — see ``babylon.projection.economy``'s own module
docstring), so a real ``GameSession.dashboard_view()`` call always projects them ``None`` too.
This file asserts they render as loud, visible fences — never a fabricated zero.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from textual.pilot import Pilot
from textual.widgets import OptionList, Static

from babylon.projection.view_models import EconomyView
from babylon.tui.app import ArchiveApp, CampaignHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.chronicle import ChronicleEvent

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeTickOutcome:
    tick: int
    paused: bool
    chronicle: tuple[ChronicleEvent, ...] = ()


def _economy_view(*, verified_tick: int, wage_balance: float) -> EconomyView:
    """A fixture ``EconomyView`` with the Fundamental-Theorem verdict and the surplus/matter
    axes populated, but the Φ tri-decomposition left genuinely unset — mirrors a real
    ``project_economy`` call's own honest-absence shape today (no engine producer exists for
    those three fields tree-wide)."""
    return EconomyView(
        economy_id="USA",
        verified_tick=verified_tick,
        wage_balance=wage_balance,
        labor_aristocracy_verdict=wage_balance > 0,
        surplus_produced=1500.0,
        profit_of_enterprise=600.0,
        interest_burden=150.0,
        ground_rent=450.0,
        taxes_on_surplus=300.0,
        overshoot_ratio=0.9,
        total_consumption=900.0,
        total_biocapacity=1000.0,
        biocapacity_ceiling=1200.0,
    )


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_lobby_flow.py``'s own fixture,
    plus the Program 24 P2 ``dashboard_view`` seam. ``dashboard_view`` is a plain callable
    (``dashboard_factory``) rather than a fixed value so a test can observe it track ``tick``
    across ``advance_tick`` calls, the same way a real ``GameSession.dashboard_view()`` re-projects
    fresh off the live graph on every call."""

    def __init__(
        self,
        session_id: UUID,
        pages: dict[str, str],
        *,
        dashboard_factory: Callable[[int], EconomyView | None],
    ) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self._dashboard_factory = dashboard_factory
        self.dashboard_calls = 0

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        self.dashboard_calls += 1
        return self._dashboard_factory(self.tick)

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
                slug="campaign-dashboard",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


def _booted_app(campaign: _FakeCampaign) -> tuple[ArchiveApp, UUID]:
    menu, campaign_id = _seeded_menu()
    briefing_subject = f"briefing/{campaign_id}"
    campaign._pages.setdefault(briefing_subject, "# OPERATION DASHBOARD\n")
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


class TestSeams:
    def test_fake_campaign_satisfies_campaign_handle(self) -> None:
        campaign = _FakeCampaign(UUID(int=2), {}, dashboard_factory=lambda _tick: None)
        assert isinstance(campaign, CampaignHandle)


class TestPressingOneShowsTheLiveEconomyView:
    @pytest.mark.asyncio
    async def test_theorem_verdict_and_surplus_render_from_the_live_projection(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            dashboard_factory=lambda tick: _economy_view(verified_tick=tick, wage_balance=0.25),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-body", Static).render())
            assert "+0.25" in body
            assert "revolution impossible" in body.lower()
            assert "SURPLUS s=1500" in body

    @pytest.mark.asyncio
    async def test_phi_tri_decomposition_renders_as_honest_fences_not_zeros(self) -> None:
        """The three Φ components have no engine producer tree-wide today — a real
        ``project_economy`` call always resolves them ``None``; this must render as the
        renderer's own absence text, never a fabricated ``0.0`` (Constitution III.11)."""
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            dashboard_factory=lambda tick: _economy_view(verified_tick=tick, wage_balance=0.1),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-body", Static).render())
            assert "φ_UE=— absent (feed unwired)" in body
            assert "φ_repro=— absent (feed unwired)" in body
            assert "φ_dom=— absent (feed unwired)" in body
            assert "0.0" not in body


class TestDashboardStaysLiveAcrossTicks:
    @pytest.mark.asyncio
    async def test_advancing_a_tick_refreshes_the_visible_dashboard(self) -> None:
        campaign = _FakeCampaign(
            UUID(int=1),
            {},
            dashboard_factory=lambda tick: _economy_view(
                verified_tick=tick, wage_balance=0.1 * tick
            ),
        )
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)
            await pilot.press("1")
            await pilot.pause()

            before = str(app.query_one("#dashboard-body", Static).render())
            assert "+0.00" in before

            await pilot.press("t")
            await pilot.pause()

            after = str(app.query_one("#dashboard-body", Static).render())
            assert "+0.10" in after
            assert campaign.dashboard_calls >= 2


class TestHonestAbsenceWhenTheCampaignDeclinesAProjection:
    """A live, booted campaign whose composition root chose not to wire a live projection at
    all (``dashboard_view()`` returns ``None``, mirroring every OTHER existing ``CampaignHandle``
    test double in this suite) must leave the pane's existing honest-absence fence untouched —
    never a blank or crashed repaint."""

    @pytest.mark.asyncio
    async def test_pressing_one_keeps_the_absence_fence(self) -> None:
        campaign = _FakeCampaign(UUID(int=1), {}, dashboard_factory=lambda _tick: None)
        app, _campaign_id = _booted_app(campaign)
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            await pilot.press("1")
            await pilot.pause()

            body = str(app.query_one("#dashboard-body", Static).render())
            assert "no EconomyView projected yet" in body
            assert campaign.dashboard_calls >= 1
