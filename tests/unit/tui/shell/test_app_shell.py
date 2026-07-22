"""Behavioral contract for the AppShell hybrid layout (Task 2)."""

import pytest
from textual.widgets import ContentSwitcher

from babylon.tui.shell.app_shell import AppShell


@pytest.mark.asyncio
async def test_shell_boots_with_four_domain_panes():
    app = AppShell()
    async with app.run_test():
        switcher = app.query_one("#main", ContentSwitcher)
        ids = {child.id for child in switcher.children}
        assert ids == {"dashboard", "map", "wiki", "topology"}
        assert app.query_one("#chronicle-rail") is not None
        assert app.query_one("#watchlist-rail") is not None
        assert app.query_one("#action-bar") is not None


@pytest.mark.asyncio
async def test_number_keys_switch_the_main_view():
    app = AppShell()
    async with app.run_test() as pilot:
        await pilot.press("2")
        assert app.query_one("#main", ContentSwitcher).current == "map"
        await pilot.press("3")
        assert app.query_one("#main", ContentSwitcher).current == "wiki"
