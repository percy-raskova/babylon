"""Behavioral contract for unit "peek-hover-wire" (shell-interconnect):
``ArchiveApp.on_directive_hover`` (mouse, secondary/non-load-bearing) and
``ArchiveApp.action_peek_wikilink`` (keyboard, S7 first-class) both paint the
SAME transient :class:`~babylon.tui.peek_overlay.PeekOverlay` via
:meth:`~babylon.tui.app.ArchiveApp._show_peek_for_subject` — a real projected
:func:`~babylon.tui.peek.peek` ``depth=1`` plate for a resolvable subject, or
an honest ``{absence}`` panel for one that is not (Constitution III.11).

Runs entirely against the no-``campaign_menu`` DEMO boot path
(:class:`~babylon.tui.app.ArchiveApp`'s default sample page/fixtures) —
:data:`~babylon.tui.app.SAMPLE_COUNTY_PAGE`'s own three wikilinks
(``county/26163`` — real, fixture-resolvable; ``org/tenants-un`` — a KNOWN
wikilink with no fixture-backed view; ``org/uaw-9999`` — an unknown redlink)
already exercise every resolution outcome
:meth:`~babylon.tui.app.ArchiveApp._resolve_subject_view` can produce,
without needing a live-campaign fake (mirrors ``test_nav_shell.py``'s own
``TestAppWiring`` idiom: ``ArchiveApp()`` + ``app.run_test()``/``pilot.press``,
nothing heavier).
"""

from __future__ import annotations

import pytest
from rich.panel import Panel
from rich.text import Text
from textual.widgets import ContentSwitcher, Label

from babylon.tui.app import ArchiveApp
from babylon.tui.directives import DirectiveHover
from babylon.tui.peek_overlay import PeekOverlay

pytestmark = [pytest.mark.unit]


def _overlay(app: ArchiveApp) -> PeekOverlay:
    return app.query_one(PeekOverlay)


def _status(app: ArchiveApp) -> str:
    return str(app.query_one("#status", Label).content)


class TestKeyboardPeekCyclesTheDossiersWikilinks:
    """``K`` — S7's own "keyboard peek is first-class" path."""

    @pytest.mark.asyncio
    async def test_first_press_shows_the_first_wikilinks_real_peek_plate(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("K")
            overlay = _overlay(app)
            assert overlay.display is True
            assert isinstance(overlay.content, Panel)
            assert "county/26163" in _status(app)
            assert "(1/3)" in _status(app)

    @pytest.mark.asyncio
    async def test_repeated_presses_walk_every_target_in_document_order(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("K")
            assert "county/26163" in _status(app)
            await pilot.press("K")
            assert "org/tenants-un" in _status(app)
            assert "(2/3)" in _status(app)
            await pilot.press("K")
            assert "org/uaw-9999" in _status(app)
            assert "(3/3)" in _status(app)

    @pytest.mark.asyncio
    async def test_a_fourth_press_wraps_around_to_the_first_target_again(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            for _ in range(3):
                await pilot.press("K")
            await pilot.press("K")
            assert "county/26163" in _status(app)
            assert "(1/3)" in _status(app)

    @pytest.mark.asyncio
    async def test_a_known_wikilink_with_no_fixture_view_shows_an_honest_absence_panel(
        self,
    ) -> None:
        """``org/tenants-un`` is in ``KNOWN_ENTITIES`` (a real, non-redlink
        wikilink span) but has no entry in the demo's
        ``fixture_subject_views()`` map — ``_resolve_subject_view`` honestly
        returns ``None``, and the overlay paints the absence panel, never a
        crash or a blank plate."""
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("K")
            await pilot.press("K")
            overlay = _overlay(app)
            content = overlay.content
            assert isinstance(content, Text)
            assert "org/tenants-un" in content.plain
            assert "no peek projection available" in content.plain

    @pytest.mark.asyncio
    async def test_a_redlink_wikilink_also_shows_an_honest_absence_panel(self) -> None:
        """``org/uaw-9999`` is not even in ``KNOWN_ENTITIES`` (a redlink) —
        still resolves to the SAME absence panel, never a crash."""
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("K")
            await pilot.press("K")
            await pilot.press("K")
            content = _overlay(app).content
            assert isinstance(content, Text)
            assert "org/uaw-9999" in content.plain
            assert "no peek projection available" in content.plain


class TestKeyboardPeekRefusesLoudly:
    """Constitution III.11: never a silent no-op."""

    @pytest.mark.asyncio
    async def test_refuses_when_the_wiki_pane_is_not_current(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")  # switch to the Map pane
            assert app.query_one("#main", ContentSwitcher).current == "map"
            await pilot.press("K")
            assert "switch to the Wiki pane" in _status(app)
            assert _overlay(app).display is False

    @pytest.mark.asyncio
    async def test_refuses_when_the_current_page_has_no_wikilinks(self) -> None:
        app = ArchiveApp(page="# a page with no links at all\n", pages=lambda _s: None)
        async with app.run_test() as pilot:
            await pilot.press("K")
            assert "this page has no wikilinks to peek" in _status(app)
            assert _overlay(app).display is False


class TestEscapeDismissesThePeekOverlay:
    @pytest.mark.asyncio
    async def test_escape_hides_a_shown_overlay(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("K")
            assert _overlay(app).display is True
            await pilot.press("escape")
            assert _overlay(app).display is False

    @pytest.mark.asyncio
    async def test_escape_is_a_harmless_no_op_with_nothing_showing(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("escape")
            assert _overlay(app).display is False


class TestDirectiveHoverShowsTheSameOverlay:
    """The mouse path (secondary, never load-bearing — R3/S7): ``ArchiveApp``
    consumes ``DirectiveHover`` (before this unit, posted with ZERO
    subscribers) exactly the way the sample page's own ``{statblock}``
    fence's ``arg`` is subject-shaped."""

    @pytest.mark.asyncio
    async def test_entered_shows_the_real_peek_plate_for_a_resolvable_subject(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(DirectiveHover("statblock:county/26163", True))
            await pilot.pause()
            overlay = _overlay(app)
            assert overlay.display is True
            assert isinstance(overlay.content, Panel)

    @pytest.mark.asyncio
    async def test_leave_hides_the_overlay(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(DirectiveHover("statblock:county/26163", True))
            await pilot.pause()
            app.post_message(DirectiveHover("statblock:county/26163", False))
            await pilot.pause()
            assert _overlay(app).display is False

    @pytest.mark.asyncio
    async def test_an_unresolvable_hover_subject_shows_the_absence_panel(self) -> None:
        """A directive whose own ``arg`` is not subject-shaped (here, an
        ``{absence}`` fence's free-text detail) degrades to the SAME honest
        absence panel — never a crash, no per-directive-kind allowlist."""
        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(DirectiveHover("absence:some free-text detail", True))
            await pilot.pause()
            content = _overlay(app).content
            assert isinstance(content, Text)
            assert "no peek projection available" in content.plain


class TestNavigatingAwayResetsThePeekState:
    """A page swap must retire whatever the overlay/cursor last referred to —
    never a stale preview, never a wikilink index pointing into a DIFFERENT
    page's target list."""

    @pytest.mark.asyncio
    async def test_navigating_hides_a_shown_overlay(self) -> None:
        from babylon.tui.palette import EntityNavigated
        from babylon.tui.router import parse_babylon_uri

        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("K")
            assert _overlay(app).display is True
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            assert _overlay(app).display is False

    @pytest.mark.asyncio
    async def test_the_wikilink_cursor_restarts_at_zero_on_a_new_page(self) -> None:
        """Two custom pages, each with its OWN two wikilinks: pressing 'K'
        once on the first page, navigating to the second, then pressing 'K'
        once there must land on the SECOND page's own FIRST target — not
        continue from the first page's cursor position (which would be
        target index 1, an entirely different subject)."""
        from babylon.tui.palette import EntityNavigated
        from babylon.tui.router import parse_babylon_uri

        page_one = "# one\n\n[[county/26163|Home]] and [[org/tenants-un]].\n"
        page_two = "# two\n\n[[org/uaw-9999]] and [[county/26163|Home]].\n"

        def pages(subject: str) -> str | None:
            return {"county/26163": page_one, "org/other-page": page_two}.get(subject)

        app = ArchiveApp(page=page_one, pages=pages)
        async with app.run_test() as pilot:
            await pilot.press("K")
            assert "county/26163" in _status(app)
            assert "(1/2)" in _status(app)

            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/other-page")))
            await pilot.pause()
            assert _overlay(app).display is False  # navigating hid it

            await pilot.press("K")
            assert "org/uaw-9999" in _status(app), (
                f"expected the SECOND page's own first target, got: {_status(app)!r}"
            )
            assert "(1/2)" in _status(app)
