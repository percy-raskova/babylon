"""Unit tests for ``babylon.tui.peek_overlay`` (unit "peek-hover-wire",
shell-interconnect).

Bare-widget behavior only — no ``ArchiveApp``/campaign/engine required,
mirroring ``tests/unit/tui/test_tutorial_overlay.py``'s own bare-host-``App``
idiom: :class:`~babylon.tui.peek_overlay.PeekOverlay` is a pure sink
(``show_peek``/``hide_peek``), never itself calling
:func:`~babylon.tui.peek.peek` or resolving a subject — that wiring is
``ArchiveApp``'s own job, tested separately in
``tests/unit/tui/test_app_peek_hover_wire.py``.
"""

from __future__ import annotations

import pytest
from rich.text import Text
from textual.app import App, ComposeResult

from babylon.tui.peek_overlay import PeekOverlay

pytestmark = [pytest.mark.unit]


class _OverlayHost(App[None]):
    """Bare host mounting exactly one :class:`PeekOverlay`."""

    def compose(self) -> ComposeResult:
        yield PeekOverlay(id="peek-overlay")


def _overlay(app: _OverlayHost) -> PeekOverlay:
    return app.query_one(PeekOverlay)


class TestInitialState:
    @pytest.mark.asyncio
    async def test_hidden_by_default(self) -> None:
        app = _OverlayHost()
        async with app.run_test():
            assert _overlay(app).display is False


class TestShowPeek:
    @pytest.mark.asyncio
    async def test_reveals_the_overlay(self) -> None:
        app = _OverlayHost()
        async with app.run_test():
            _overlay(app).show_peek(Text("county/26163"))
            assert _overlay(app).display is True

    @pytest.mark.asyncio
    async def test_paints_the_given_content(self) -> None:
        app = _OverlayHost()
        async with app.run_test():
            _overlay(app).show_peek(Text("county/26163 population=2"))
            content = _overlay(app).content
            assert isinstance(content, Text)
            assert content.plain == "county/26163 population=2"

    @pytest.mark.asyncio
    async def test_a_second_show_replaces_the_first_content(self) -> None:
        app = _OverlayHost()
        async with app.run_test():
            overlay = _overlay(app)
            overlay.show_peek(Text("first subject"))
            overlay.show_peek(Text("second subject"))
            content = overlay.content
            assert isinstance(content, Text)
            assert content.plain == "second subject"


class TestHidePeek:
    @pytest.mark.asyncio
    async def test_hides_a_shown_overlay(self) -> None:
        app = _OverlayHost()
        async with app.run_test():
            overlay = _overlay(app)
            overlay.show_peek(Text("county/26163"))
            overlay.hide_peek()
            assert overlay.display is False

    @pytest.mark.asyncio
    async def test_is_idempotent_on_an_already_hidden_overlay(self) -> None:
        """Hiding an already-hidden overlay is not an error — mirrors
        ``WatchlistState.unpin``'s own no-op-on-redundant-call idiom
        (``PeekOverlay``'s own docstring)."""
        app = _OverlayHost()
        async with app.run_test():
            overlay = _overlay(app)
            overlay.hide_peek()
            overlay.hide_peek()
            assert overlay.display is False
