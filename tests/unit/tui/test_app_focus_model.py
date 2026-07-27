"""Behavioral contract for the cross-pane/rail focus ring (shell-interconnect,
unit "focus-model").

Before this unit, the ONLY focusable widget anywhere in :class:`~babylon.tui.
app.ArchiveApp`'s tree was the Wiki pane's bare ``VerticalScroll``
(:mod:`~babylon.tui.shell.views.wiki_view`) — every rail and the other three
domain panes (Dashboard/Map/Topology) were plain non-focusable ``Static``/
``Widget`` content. Textual's own ``AUTO_FOCUS = "*"`` (the ``App`` default;
``ArchiveApp`` never overrides it) therefore always auto-focused that one
widget at boot regardless of which pane was actually showing, and Tab/
Shift-Tab traversal had nowhere else to go. This file pins:

* the rails and the three Static-only domain panes are now real focus
  targets (:meth:`~babylon.tui.app.ArchiveApp.compose`);
* :meth:`~babylon.tui.app.ArchiveApp.action_switch_view` moves focus onto
  whichever pane it just switched to;
* :meth:`~babylon.tui.app.ArchiveApp._navigate` moves focus onto the Wiki
  pane's scroll region only when it also reveals it (``reveal=True``) —
  never on an in-place ``reveal=False`` tick refresh;
* the resulting AUTO_FOCUS boot-time landing spot (a regression test per
  this unit's own known-risk note); and
* Tab/Shift-Tab (framework ``focus_next``/``focus_previous`` — no new
  ``Binding`` of ours) walk a ring of exactly the three rails plus whichever
  ONE pane is current, never a hidden pane's target.

The TutorialOverlay's own deliberate focus-grab is covered separately —
``tests/unit/tui/test_app_tutorial_wiring.py``'s
``TestFocusModelDoesNotFightTheOverlaysGrab`` — since exercising it needs
that file's own lobby/briefing/campaign-boot fixtures.
"""

from __future__ import annotations

import pytest
from textual.containers import VerticalScroll

from babylon.tui.app import ArchiveApp
from babylon.tui.shell.views.dashboard_view import DashboardView
from babylon.tui.shell.views.map_view import MapView
from babylon.tui.shell.views.topology_view import TopologyView

pytestmark = pytest.mark.unit


def _wiki_scroll(app: ArchiveApp) -> VerticalScroll:
    """The Wiki pane's own pre-existing focus target (no id of its own)."""
    return app.query_one("#wiki").query_one(VerticalScroll)


class TestRailsAndPanesAreFocusable:
    """Every rail and every domain pane is now a real focus target."""

    @pytest.mark.asyncio
    async def test_the_three_rails_are_focusable(self) -> None:
        app = ArchiveApp()
        async with app.run_test():
            assert app.query_one("#chronicle-rail").can_focus is True
            assert app.query_one("#watchlist-rail").can_focus is True
            assert app.query_one("#action-bar").can_focus is True

    @pytest.mark.asyncio
    async def test_the_three_static_only_panes_are_focusable(self) -> None:
        app = ArchiveApp()
        async with app.run_test():
            assert app.query_one(DashboardView).can_focus is True
            assert app.query_one(MapView).can_focus is True
            assert app.query_one(TopologyView).can_focus is True

    @pytest.mark.asyncio
    async def test_the_wiki_pane_container_stays_non_focusable(self) -> None:
        """Wiki keeps its pre-existing ``VerticalScroll`` as its own focus
        target instead of gaining a second, redundant stop on the
        ``WikiView`` container itself."""
        app = ArchiveApp()
        async with app.run_test():
            assert app.query_one("#wiki").can_focus is False
            assert _wiki_scroll(app).can_focus is True


class TestAutoFocusBootRegression:
    """Known risk (unit spec): AUTO_FOCUS's own screen-activation behavior
    changes now that more than one widget in the tree is focusable — pinned
    here as an explicit regression rather than left implicit."""

    @pytest.mark.asyncio
    async def test_boot_focuses_the_first_focusable_rail_in_dom_order(self) -> None:
        """``AUTO_FOCUS = "*"`` (the framework default) lands on the FIRST
        focusable widget in DOM/focus-chain order — the left-docked
        chronicle rail, composed before the ``ContentSwitcher`` and its
        panes. This is a real, always-visible widget (unlike the pre-unit
        landing on the Wiki pane's scroll region regardless of which pane
        was showing), so the boot-time focus border is always honest."""
        app = ArchiveApp()
        async with app.run_test():
            assert app.focused is app.query_one("#chronicle-rail")


class TestActionSwitchViewMovesFocus:
    """Every explicit ``1``-``4`` pane switch moves focus onto the pane it
    just switched to."""

    @pytest.mark.asyncio
    async def test_switching_to_map_focuses_the_map_pane(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert app.focused is app.query_one("#map")

    @pytest.mark.asyncio
    async def test_switching_to_dashboard_focuses_the_dashboard_pane(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("1")
            assert app.focused is app.query_one("#dashboard")

    @pytest.mark.asyncio
    async def test_switching_to_topology_focuses_the_topology_pane(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("4")
            assert app.focused is app.query_one("#topology")

    @pytest.mark.asyncio
    async def test_switching_to_wiki_focuses_its_pre_existing_scroll_region(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")  # leave the initial wiki pane first
            await pilot.press("3")
            assert app.focused is _wiki_scroll(app)


class TestNavigateMovesFocusOnlyWhenRevealed:
    """:meth:`~babylon.tui.app.ArchiveApp._navigate`'s own ``reveal`` split:
    a deliberate navigation moves focus to the Wiki pane it reveals; an
    in-place (``reveal=False``) tick refresh never yanks focus off whatever
    pane the player is actually parked on."""

    @pytest.mark.asyncio
    async def test_a_revealing_navigation_focuses_the_wiki_scroll_from_another_pane(
        self,
    ) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")  # park on the Map pane
            assert app.focused is app.query_one("#map")
            await app._navigate("county/26163")  # noqa: SLF001 - white-box wiring check
            await pilot.pause()
            assert app.query_one("#main").current == "wiki"
            assert app.focused is _wiki_scroll(app)

    @pytest.mark.asyncio
    async def test_a_non_revealing_navigation_never_steals_focus_from_the_current_pane(
        self,
    ) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")  # park on the Map pane
            assert app.focused is app.query_one("#map")
            await app._navigate(  # noqa: SLF001 - white-box wiring check
                "county/26163", record=False, reveal=False
            )
            await pilot.pause()
            assert app.query_one("#main").current == "map"
            assert app.focused is app.query_one("#map")


class TestTabTraversalIsMeaningfulAcrossPanesAndRails:
    """Framework ``Tab``/``Shift-Tab`` (no new ``Binding`` of ours) now walk
    a real ring: the three rails plus whichever ONE pane is current — never
    a hidden pane's own focus target (``ContentSwitcher`` hides non-current
    panes via ``display: none``, and Textual's own focus chain already
    excludes non-displayed widgets)."""

    @pytest.mark.asyncio
    async def test_tab_from_the_current_panes_target_reaches_a_rail(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("3")  # land explicitly on the wiki pane's scroll
            assert app.focused is _wiki_scroll(app)
            await pilot.press("tab")
            assert app.focused in (
                app.query_one("#chronicle-rail"),
                app.query_one("#watchlist-rail"),
                app.query_one("#action-bar"),
            )

    @pytest.mark.asyncio
    async def test_shift_tab_from_a_rail_walks_back_to_the_current_pane(self) -> None:
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("3")
            focused_before = app.focused
            await pilot.press("tab")
            assert app.focused is not focused_before
            await pilot.press("shift+tab")
            assert app.focused is focused_before

    @pytest.mark.asyncio
    async def test_hidden_panes_never_appear_in_the_tab_ring_while_wiki_is_current(
        self,
    ) -> None:
        """Dashboard/Map/Topology are each focusable, but hidden (``display:
        none``) while Wiki is current — Tab must never land on one of them
        until the player actually switches to it."""
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("3")
            seen = {app.focused}
            for _ in range(6):  # loop bound: comfortably exceeds the 4-stop ring
                await pilot.press("tab")
                seen.add(app.focused)
            assert app.query_one("#dashboard") not in seen
            assert app.query_one("#map") not in seen
            assert app.query_one("#topology") not in seen
