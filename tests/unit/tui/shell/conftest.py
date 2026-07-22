"""Shared fixtures for shell view tests.

``make_shell_harness`` mounts a single widget in a minimal harness app and yields the Pilot —
the pattern Tasks 3-6 use to exercise a view in isolation. The harness app exposes
``export_visible_text()`` (Task 10's helper) so view tests can assert on emitted screen text.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from textual.app import App, ComposeResult
from textual.widget import Widget

from babylon.tui.shell.bdd.harness import export_visible_text


class _HarnessApp(App[None]):
    """Minimal single-widget host used by view unit tests."""

    def __init__(self, widget: Widget) -> None:
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget

    def export_visible_text(self) -> str:
        return export_visible_text(self)


@pytest.fixture
def make_shell_harness():
    """Factory: ``async with make_shell_harness(view) as pilot`` mounts ``view`` alone."""

    @asynccontextmanager
    async def _harness(widget: Widget):
        app = _HarnessApp(widget)
        async with app.run_test() as pilot:
            yield pilot

    return _harness
