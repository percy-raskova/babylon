"""Behavioral contract for Program 24 P1 — the four-pane hybrid shell (WO Unit P1).

Boots the four-pane hybrid layout (docked chronicle/watchlist rails, bottom action bar, a
``ContentSwitcher`` across Dashboard/Map/Wiki/Topology) INSIDE :class:`~babylon.tui.app.ArchiveApp`
itself — the promoted shape of :class:`~babylon.tui.shell.app_shell.AppShell`'s own Task-2 layout
(``tests/unit/tui/shell/test_app_shell.py``), but composed where the lobby/briefing/pacing/tutorial
DI machinery already lives. This file exercises ONLY the new layout surface; existing nav/redlink/
pacing/tutorial behavior stays covered by its own pre-existing test files (``test_nav_shell.py``,
``test_app_lobby_flow.py``, ``test_app_pacing_driver.py``, ``test_app_tutorial_wiring.py``) — this
unit changes none of that wiring, only where the dossier lives.
"""

from __future__ import annotations

import pytest
from textual.widgets import ContentSwitcher, Static

from babylon.tui.app import ArchiveApp, BabylonMarkdown

pytestmark = pytest.mark.unit


class TestFourPaneLayoutBoots:
    @pytest.mark.asyncio
    async def test_shell_boots_with_four_domain_panes_and_both_rails(self) -> None:
        app = ArchiveApp()
        async with app.run_test():
            switcher = app.query_one("#main", ContentSwitcher)
            ids = {child.id for child in switcher.children}
            assert ids == {"dashboard", "map", "wiki", "topology"}
            assert app.query_one("#chronicle-rail") is not None
            assert app.query_one("#watchlist-rail") is not None
            assert app.query_one("#action-bar") is not None

    @pytest.mark.asyncio
    async def test_wiki_pane_is_the_initial_view(self) -> None:
        """The current campaign dossier is what a booting player should see first —
        zero behavior change from the pre-P1 single-pane boot."""
        app = ArchiveApp()
        async with app.run_test():
            assert app.query_one("#main", ContentSwitcher).current == "wiki"

    @pytest.mark.asyncio
    async def test_dossier_is_still_reachable_at_its_existing_id(self) -> None:
        """Every pre-P1 nav/redlink/tutorial test queries ``#dossier`` directly —
        ``ContentSwitcher`` hides non-current panes via CSS, it never unmounts them,
        so the query must keep resolving regardless of which pane is switched-to."""
        app = ArchiveApp()
        async with app.run_test():
            dossier = app.query_one("#dossier", BabylonMarkdown)
            assert dossier is not None


class TestNumberKeysSwitchTheMainView:
    @pytest.mark.asyncio
    async def test_each_digit_switches_to_its_own_pane(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert app.query_one("#main", ContentSwitcher).current == "map"
            await pilot.press("4")
            assert app.query_one("#main", ContentSwitcher).current == "topology"
            await pilot.press("1")
            assert app.query_one("#main", ContentSwitcher).current == "dashboard"
            await pilot.press("3")
            assert app.query_one("#main", ContentSwitcher).current == "wiki"


class TestHonestAbsenceFencesBeforeP2ThroughP6WireRealData:
    """Constitution III.11: every pane/rail without a live producer yet shows a loud,
    visible ``{absence}`` fence — never a fabricated number, never a bare placeholder
    word like ``"dashboard"``/``"chronicle"``."""

    @pytest.mark.asyncio
    async def test_chronicle_rail_reuses_the_existing_wire_is_quiet_absence(self) -> None:
        app = ArchiveApp()
        async with app.run_test():
            rail = app.query_one("#chronicle-rail", Static)
            assert "the wire is quiet" in str(rail.render())

    @pytest.mark.asyncio
    async def test_watchlist_rail_reuses_the_existing_nothing_pinned_absence(self) -> None:
        app = ArchiveApp()
        async with app.run_test():
            rail = app.query_one("#watchlist-rail", Static)
            assert "nothing pinned yet" in str(rail.render())

    @pytest.mark.asyncio
    async def test_dashboard_pane_shows_an_honest_absence_fence(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("1")
            body = str(app.query_one("#dashboard-body", Static).render())
            assert "no EconomyView projected yet" in body
            assert "0.0" not in body  # never a fabricated zero

    @pytest.mark.asyncio
    async def test_map_pane_shows_an_honest_absence_fence(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")
            body = str(app.query_one("#map-body", Static).render())
            assert "no choropleth cells wired yet" in body

    @pytest.mark.asyncio
    async def test_topology_pane_shows_an_honest_absence_fence(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("4")
            body = str(app.query_one("#topology-body", Static).render())
            assert "no live graph bound yet" in body

    @pytest.mark.asyncio
    async def test_action_bar_shows_an_honest_absence_fence_never_the_bare_word(self) -> None:
        app = ArchiveApp()
        async with app.run_test():
            bar = app.query_one("#action-bar", Static)
            rendered = str(bar.render())
            assert "no verb plate wired yet" in rendered
            assert rendered.strip() != "action bar"
