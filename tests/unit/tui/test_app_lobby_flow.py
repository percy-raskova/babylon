"""Program v1.0.0 Unit C2: ``ArchiveApp``'s lobby -> briefing -> campaign-shell
Screen-mode boot flow, driven with fake seams.

``LobbyScreen`` (``tui/campaign_menu.py``) was built (WO-49) but never
pushed by ``ArchiveApp`` — this unit wires it in: ``on_mount`` pushes the
lobby when a ``campaign_menu`` is given; the lobby's chosen campaign UUID
goes through the ``CampaignLoader`` seam (fulfilled for real by
``babylon.game.session`` in the composition root, here by
:class:`_FakeLoader`); the booted :class:`~babylon.tui.app.CampaignHandle`
(here :class:`_FakeCampaign`) backs :class:`~babylon.tui.app.BriefingScreen`
and then the campaign shell's own page source. No new snapshot goldens —
these are Screen-mode NAVIGATION tests, following the existing
``TestAppWiring``/``TestLobbyScreen`` idiom (``tests/unit/tui/
test_nav_shell.py`` / ``test_campaign_menu.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from textual.widgets import Label, OptionList

from babylon.tui.app import ArchiveApp, BabylonMarkdown, CampaignHandle, TickOutcome
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeTickOutcome:
    """A minimal ``TickOutcome`` double."""

    tick: int
    paused: bool


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — no engine, no Postgres."""

    def __init__(self, session_id: UUID, pages: dict[str, str]) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages
        self.advance_calls = 0

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def advance_tick(self) -> _FakeTickOutcome:
        self.advance_calls += 1
        self.tick += 1
        return _FakeTickOutcome(tick=self.tick, paused=False)


class _FakeLoader:
    """The ``CampaignLoader`` double — records every id it was asked to boot."""

    def __init__(self, campaign: _FakeCampaign) -> None:
        self._campaign = campaign
        self.calls: list[UUID] = []

    def __call__(self, campaign_id: UUID) -> _FakeCampaign:
        self.calls.append(campaign_id)
        return self._campaign


def _seeded_menu() -> tuple[CampaignMenu, UUID]:
    """One seeded ACTIVE campaign, ready for the lobby to list/choose."""
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


class TestSeams:
    def test_fake_campaign_satisfies_campaign_handle(self) -> None:
        assert isinstance(_FakeCampaign(uuid4(), {}), CampaignHandle)

    def test_fake_tick_outcome_satisfies_tick_outcome(self) -> None:
        assert isinstance(_FakeTickOutcome(tick=1, paused=False), TickOutcome)


class TestConstructorValidation:
    def test_campaign_menu_without_a_loader_raises(self) -> None:
        menu, _ = _seeded_menu()
        with pytest.raises(ValueError, match="campaign_loader"):
            ArchiveApp(campaign_menu=menu)

    def test_no_campaign_menu_is_the_pre_c2_default(self) -> None:
        """Backward compat: no lobby, no loader required, no live campaign."""
        app = ArchiveApp()
        assert app.campaign is None


class TestLobbyToCampaignShellFlow:
    @pytest.mark.asyncio
    async def test_lobby_appears_first_when_a_campaign_menu_is_given(self) -> None:
        menu, _campaign_id = _seeded_menu()
        loader = _FakeLoader(_FakeCampaign(uuid4(), {}))
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await pilot.pause()
            campaigns = app.screen.query_one("#campaigns", OptionList)
            assert campaigns.option_count == 1
            assert loader.calls == []  # nothing chosen yet

    @pytest.mark.asyncio
    async def test_choosing_a_campaign_boots_it_and_shows_the_briefing(self) -> None:
        menu, campaign_id = _seeded_menu()
        briefing_subject = f"briefing/{campaign_id}"
        campaign = _FakeCampaign(campaign_id, {briefing_subject: "# OPERATION TEST\n"})
        loader = _FakeLoader(campaign)
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen.query_one("#campaigns", OptionList).focus()
            await pilot.press("enter")
            await pilot.pause()

            assert loader.calls == [campaign_id]
            assert app.campaign is campaign
            assert app.screen.query_one("#briefing-dossier", BabylonMarkdown) is not None

    @pytest.mark.asyncio
    async def test_a_campaign_with_no_baked_briefing_shows_an_honest_absence(self) -> None:
        """Constitution III.11: never fabricate what the vault hasn't baked."""
        menu, campaign_id = _seeded_menu()
        campaign = _FakeCampaign(campaign_id, {})  # nothing baked
        loader = _FakeLoader(campaign)
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen.query_one("#campaigns", OptionList).focus()
            await pilot.press("enter")
            await pilot.pause()

            status = app.screen.query_one("#briefing-status", Label)
            assert "begin the operation" in str(status.content)

    @pytest.mark.asyncio
    async def test_beginning_the_operation_reveals_the_live_campaign_shell(self) -> None:
        menu, campaign_id = _seeded_menu()
        briefing_subject = f"briefing/{campaign_id}"
        campaign = _FakeCampaign(
            campaign_id,
            {
                briefing_subject: "# OPERATION TEST\n",
                "county/26163": "# county/26163 — LIVE CAMPAIGN\n",
            },
        )
        loader = _FakeLoader(campaign)
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen.query_one("#campaigns", OptionList).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")  # "Begin Operation" on the briefing
            await pilot.pause()

            assert app.nav.current == "county/26163"
            status = app.query_one("#status", Label)
            assert "county/26163" in str(status.content)
            assert "[ABSENT]" not in str(status.content)

    @pytest.mark.asyncio
    async def test_advance_tick_calls_the_seam_and_updates_status(self) -> None:
        menu, campaign_id = _seeded_menu()
        briefing_subject = f"briefing/{campaign_id}"
        campaign = _FakeCampaign(
            campaign_id,
            {briefing_subject: "# OPERATION TEST\n", "county/26163": "# Wayne\n"},
        )
        loader = _FakeLoader(campaign)
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen.query_one("#campaigns", OptionList).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            await pilot.press("t")
            await pilot.pause()

            assert campaign.advance_calls == 1
            status = app.query_one("#status", Label)
            assert "tick 1" in str(status.content)

    @pytest.mark.asyncio
    async def test_advance_tick_is_a_loud_noop_with_no_live_campaign(self) -> None:
        """No ``campaign_menu`` at all — the pre-C2 default boot."""
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("t")
            await pilot.pause()
            status = app.query_one("#status", Label)
            assert "no live campaign" in str(status.content)

    @pytest.mark.asyncio
    async def test_escape_at_the_lobby_with_no_choice_exits_the_app(self) -> None:
        menu, _campaign_id = _seeded_menu()
        loader = _FakeLoader(_FakeCampaign(uuid4(), {}))
        app = ArchiveApp(campaign_menu=menu, campaign_loader=loader)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            assert app._exit is True
            assert loader.calls == []
