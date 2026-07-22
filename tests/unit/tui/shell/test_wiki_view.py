"""Behavioral contract for the WikiView vault-page reader (Task 3)."""

import pytest

from babylon.tui.shell.views.wiki_view import WikiView


@pytest.mark.asyncio
async def test_wiki_view_renders_a_vault_page(make_shell_harness):
    view = WikiView(id="wiki")
    async with make_shell_harness(view) as pilot:
        view.load_page("# Wayne County\n\nSee [[county/26163|Wayne]].")
        await pilot.pause()
        text = pilot.app.export_visible_text()
        assert "Wayne County" in text
