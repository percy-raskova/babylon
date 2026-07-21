"""WO-49 contract tests: the campaign menu over the ``babylon_meta`` catalog.

Ports the CARRIED ledger row for ``n-briefing.spec.ts``'s lobby half:
rows show codename + ``Tick N`` + status; archive is the REVERSIBLE
``ABANDONED`` status, not a deletion; hard delete is arm-then-confirm
(one wrong key disarms). "New" mints a campaign through the catalog seam
— the same structural-Protocol trick as WO-37/WO-47, so
:class:`babylon.persistence.babylon_meta.BabylonMetaStore` satisfies
:class:`babylon.tui.campaign_menu.CampaignCatalog` without any
tui→persistence import. Codenames are computed on read from the campaign
UUID (``operation_codename``, spec-116 FR-116-3) — never stored.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from babylon.projection.briefing import operation_codename
from babylon.tui.campaign_menu import (
    CampaignCatalog,
    CampaignMenu,
    InMemoryCampaignCatalog,
    LobbyRow,
)

pytestmark = pytest.mark.unit


def _menu(catalog: InMemoryCampaignCatalog | None = None) -> CampaignMenu:
    return CampaignMenu(
        catalog if catalog is not None else InMemoryCampaignCatalog(),
        engine_version="0.24.0",
        defines_hash="d" * 16,
    )


class TestCatalogSeam:
    def test_in_memory_catalog_satisfies_the_protocol(self) -> None:
        assert isinstance(InMemoryCampaignCatalog(), CampaignCatalog)

    def test_babylon_meta_store_satisfies_the_protocol(self) -> None:
        """The composition root injects the real store — structurally."""
        from babylon.persistence.babylon_meta import BabylonMetaStore

        store = BabylonMetaStore.__new__(BabylonMetaStore)
        assert isinstance(store, CampaignCatalog)


class TestNewCampaign:
    def test_new_mints_a_uuid_and_appears_in_the_rows(self) -> None:
        menu = _menu()
        row = menu.new_campaign()
        assert isinstance(row.campaign_id, UUID)
        assert row.campaign_id in {r.campaign_id for r in menu.rows()}

    def test_every_new_campaign_is_distinct(self) -> None:
        menu = _menu()
        first = menu.new_campaign()
        second = menu.new_campaign()
        assert first.campaign_id != second.campaign_id

    def test_codename_is_computed_from_the_uuid_not_stored(self) -> None:
        menu = _menu()
        row = menu.new_campaign()
        assert row.codename == operation_codename(row.campaign_id)


class TestRows:
    def test_row_shows_codename_tick_and_status(self) -> None:
        menu = _menu()
        minted = menu.new_campaign()
        row = next(r for r in menu.rows() if r.campaign_id == minted.campaign_id)
        assert row.codename == operation_codename(minted.campaign_id)
        assert row.tick_label == "Tick 0"
        assert row.status == "ACTIVE"

    def test_rows_render_one_line_each(self) -> None:
        menu = _menu()
        minted = menu.new_campaign()
        row = next(r for r in menu.rows() if r.campaign_id == minted.campaign_id)
        assert row.label == f"{row.codename} · Tick 0 · ACTIVE"

    def test_empty_catalog_lists_honestly_empty(self) -> None:
        assert _menu().rows() == ()


class TestArchiveLifecycle:
    def test_archive_flips_to_abandoned_and_back(self) -> None:
        menu = _menu()
        row = menu.new_campaign()
        assert menu.toggle_archive(row.campaign_id) == "ABANDONED"
        assert menu.toggle_archive(row.campaign_id) == "ACTIVE"

    def test_archived_campaign_stays_in_the_list(self) -> None:
        """Soft-delete is reversible BECAUSE the row survives."""
        menu = _menu()
        row = menu.new_campaign()
        menu.toggle_archive(row.campaign_id)
        statuses = {r.campaign_id: r.status for r in menu.rows()}
        assert statuses[row.campaign_id] == "ABANDONED"


class TestArmThenConfirmDelete:
    def test_unarmed_confirm_deletes_nothing(self) -> None:
        menu = _menu()
        row = menu.new_campaign()
        assert menu.confirm_delete(row.campaign_id) is False
        assert menu.rows() != ()

    def test_armed_confirm_deletes_the_campaign(self) -> None:
        menu = _menu()
        row = menu.new_campaign()
        menu.arm_delete(row.campaign_id)
        assert menu.confirm_delete(row.campaign_id) is True
        assert menu.rows() == ()

    def test_confirm_for_a_different_campaign_only_disarms(self) -> None:
        menu = _menu()
        first = menu.new_campaign()
        second = menu.new_campaign()
        menu.arm_delete(first.campaign_id)
        assert menu.confirm_delete(second.campaign_id) is False
        assert menu.armed_delete is None
        assert len(menu.rows()) == 2

    def test_disarm_clears_the_armed_state(self) -> None:
        menu = _menu()
        row = menu.new_campaign()
        menu.arm_delete(row.campaign_id)
        menu.disarm()
        assert menu.armed_delete is None
        assert menu.confirm_delete(row.campaign_id) is False


def _seeded_catalog() -> InMemoryCampaignCatalog:
    from babylon.tui.campaign_menu import InMemoryCampaign

    return InMemoryCampaignCatalog(
        seed=(
            InMemoryCampaign(
                campaign_id=UUID(int=1),
                slug="campaign-one",
                engine_version="0.24.0",
                defines_hash="d" * 16,
                last_tick=7,
            ),
            InMemoryCampaign(
                campaign_id=UUID(int=2),
                slug="campaign-two",
                engine_version="0.24.0",
                defines_hash="d" * 16,
            ),
        )
    )


class _LobbyHost:
    """Builds the host app + screen pair for pilot-driven lobby tests."""

    def __init__(self) -> None:
        from textual.app import App

        menu = _menu(_seeded_catalog())
        chosen: list[UUID | None] = []

        class Host(App[None]):
            def on_mount(self) -> None:
                from babylon.tui.campaign_menu import LobbyScreen

                self.push_screen(LobbyScreen(menu), callback=chosen.append)

        self.menu = menu
        self.chosen = chosen
        self.app = Host()


class TestLobbyScreen:
    @pytest.mark.asyncio
    async def test_lists_the_catalog_as_rows(self) -> None:
        from textual.widgets import OptionList

        host = _LobbyHost()
        async with host.app.run_test() as pilot:
            await pilot.pause()
            campaigns = host.app.screen.query_one("#campaigns", OptionList)
            assert campaigns.option_count == 2
            first = campaigns.get_option_at_index(0)
            assert first.id == str(UUID(int=1))
            assert "Tick 7" in str(first.prompt)

    @pytest.mark.asyncio
    async def test_n_mints_a_new_campaign_row(self) -> None:
        from textual.widgets import OptionList

        host = _LobbyHost()
        async with host.app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("n")
            campaigns = host.app.screen.query_one("#campaigns", OptionList)
            assert campaigns.option_count == 3

    @pytest.mark.asyncio
    async def test_a_archives_then_restores_the_highlighted_row(self) -> None:
        host = _LobbyHost()
        async with host.app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            assert host.menu.rows()[0].status == "ABANDONED"
            await pilot.press("a")
            assert host.menu.rows()[0].status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_d_d_deletes_but_an_interposed_action_disarms(self) -> None:
        host = _LobbyHost()
        async with host.app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            assert len(host.menu.rows()) == 2
            await pilot.press("a")
            await pilot.press("d")
            assert len(host.menu.rows()) == 2
            await pilot.press("d")
            assert len(host.menu.rows()) == 1

    @pytest.mark.asyncio
    async def test_enter_chooses_the_highlighted_campaign(self) -> None:
        host = _LobbyHost()
        async with host.app.run_test() as pilot:
            await pilot.pause()
            host.app.screen.query_one("#campaigns").focus()
            await pilot.press("enter")
            assert host.chosen == [UUID(int=1)]

    @pytest.mark.asyncio
    async def test_escape_leaves_without_choosing(self) -> None:
        host = _LobbyHost()
        async with host.app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            assert host.chosen == [None]


class TestLobbyRowModel:
    def test_rows_are_frozen(self) -> None:
        row = LobbyRow(
            campaign_id=UUID("00000000-0000-0000-0000-000000000049"),
            codename="CRIMSON HARVEST",
            tick_label="Tick 7",
            status="ACTIVE",
        )
        with pytest.raises(Exception, match="frozen"):
            row.status = "ABANDONED"  # type: ignore[misc]
