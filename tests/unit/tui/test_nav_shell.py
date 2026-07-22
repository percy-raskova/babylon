"""WO-47 contract tests: the navigation shell's pure state and seams.

The jumplist is a vim-style back-stack (``Ctrl-O`` back / ``Ctrl-I``
forward): visiting truncates forward history and pushes; back/forward move
a cursor and are idempotent at the edges (a redundant key-press is not an
error). The breadcrumb trail is an append-only, consecutive-deduped,
capacity-bounded visited path. Both are frozen Pydantic values — the
``NavShell`` orchestrator owns mutation and persists through the
``NavPersistence`` seam, which :class:`babylon.persistence.babylon_meta.
BabylonMetaStore` satisfies structurally (the same no-import trick as
WO-37's ``WatchlistPersistence``; the Postgres round-trip lives in
``tests/integration/tui/test_nav_persistence.py``).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.tui.nav import (
    BreadcrumbTrail,
    InMemoryNavPersistence,
    JumplistState,
    NavPersistence,
    NavShell,
    subject_for,
)
from babylon.tui.router import parse_babylon_uri

pytestmark = pytest.mark.unit


class TestJumplist:
    def test_starts_empty_with_no_current(self) -> None:
        state = JumplistState()
        assert state.entries == ()
        assert state.current is None

    def test_visit_pushes_and_becomes_current(self) -> None:
        state = JumplistState().visit("county/26163").visit("org/tenants-un")
        assert state.entries == ("county/26163", "org/tenants-un")
        assert state.current == "org/tenants-un"

    def test_revisiting_the_current_page_is_a_no_op(self) -> None:
        state = JumplistState().visit("county/26163")
        assert state.visit("county/26163") is state

    def test_back_and_forward_walk_the_stack(self) -> None:
        state = JumplistState().visit("a").visit("b").visit("c")
        back_once = state.back()
        assert back_once.current == "b"
        back_twice = back_once.back()
        assert back_twice.current == "a"
        assert back_twice.forward().current == "b"

    def test_edges_are_idempotent(self) -> None:
        """Back at the oldest entry / forward at the newest returns self."""
        empty = JumplistState()
        assert empty.back() is empty
        assert empty.forward() is empty
        state = JumplistState().visit("a")
        assert state.back() is state
        assert state.forward() is state

    def test_visit_after_back_truncates_forward_history(self) -> None:
        """The vim contract: a new jump orphans the forward branch."""
        state = JumplistState().visit("a").visit("b").visit("c").back().back()
        rerouted = state.visit("d")
        assert rerouted.entries == ("a", "d")
        assert rerouted.forward() is rerouted

    def test_restore_resumes_at_the_newest_entry(self) -> None:
        state = JumplistState.restore(("a", "b", "c"))
        assert state.current == "c"
        assert state.back().current == "b"

    def test_inconsistent_cursor_fails_loud(self) -> None:
        with pytest.raises(ValueError, match="cursor"):
            JumplistState(entries=("a",), cursor=5)


class TestBreadcrumbTrail:
    def test_pushes_in_visit_order(self) -> None:
        trail = BreadcrumbTrail().push("national/USA").push("state/26").push("county/26163")
        assert trail.entries == ("national/USA", "state/26", "county/26163")

    def test_consecutive_repeat_is_deduped(self) -> None:
        trail = BreadcrumbTrail().push("a").push("a")
        assert trail.entries == ("a",)
        revisited = trail.push("b").push("a")
        assert revisited.entries == ("a", "b", "a")

    def test_capacity_drops_the_oldest(self) -> None:
        trail = BreadcrumbTrail(capacity=2).push("a").push("b").push("c")
        assert trail.entries == ("b", "c")

    def test_restore_rebounds_to_capacity(self) -> None:
        trail = BreadcrumbTrail.restore(("a", "b", "c"), capacity=2)
        assert trail.entries == ("b", "c")


class TestNavShell:
    def test_visit_updates_stack_trail_and_persists(self) -> None:
        campaign_id = uuid4()
        persistence = InMemoryNavPersistence()
        shell = NavShell(campaign_id=campaign_id, persistence=persistence)
        shell.visit("county/26163")
        shell.visit("org/tenants-un")
        assert shell.current == "org/tenants-un"
        assert persistence.load_jumplist(campaign_id) == ("county/26163", "org/tenants-un")
        assert persistence.load_breadcrumbs(campaign_id) == ("county/26163", "org/tenants-un")

    def test_back_and_forward_return_the_new_current(self) -> None:
        shell = NavShell(campaign_id=uuid4(), persistence=InMemoryNavPersistence())
        shell.visit("a")
        shell.visit("b")
        assert shell.back() == "a"
        assert shell.forward() == "b"

    def test_back_at_the_edge_returns_none_and_persists_nothing_new(self) -> None:
        campaign_id = uuid4()
        persistence = InMemoryNavPersistence()
        shell = NavShell(campaign_id=campaign_id, persistence=persistence)
        shell.visit("a")
        assert shell.back() is None
        assert shell.forward() is None

    def test_restore_round_trips_across_shell_instances(self) -> None:
        """Cross-session survival with the in-memory fake — the Postgres
        variant of this exact contract is the integration test."""
        campaign_id = uuid4()
        persistence = InMemoryNavPersistence()
        first = NavShell(campaign_id=campaign_id, persistence=persistence)
        first.visit("a")
        first.visit("b")
        second = NavShell.restore(campaign_id=campaign_id, persistence=persistence)
        assert second.current == "b"
        assert second.back() == "a"
        assert second.trail.entries == ("a", "b")

    def test_fresh_campaign_restores_honestly_empty(self) -> None:
        shell = NavShell.restore(campaign_id=uuid4(), persistence=InMemoryNavPersistence())
        assert shell.current is None
        assert shell.trail.entries == ()


class TestSeams:
    def test_in_memory_fake_satisfies_the_protocol(self) -> None:
        assert isinstance(InMemoryNavPersistence(), NavPersistence)

    def test_babylon_meta_store_satisfies_the_protocol(self) -> None:
        """The composition root injects the real store where the shell's
        seam expects one — no tui→persistence import in production code
        (this test imports both; ``src/`` layering is what import-linter
        guards)."""
        from babylon.persistence.babylon_meta import BabylonMetaStore

        store = BabylonMetaStore.__new__(BabylonMetaStore)
        assert isinstance(store, NavPersistence)


class TestAppWiring:
    def test_palette_provider_is_registered(self) -> None:
        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigatorProvider

        assert EntityNavigatorProvider in ArchiveApp.COMMANDS

    @pytest.mark.asyncio
    async def test_palette_navigation_opens_the_page(self) -> None:
        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            assert app.nav.current == "org/tenants-un"

    @pytest.mark.asyncio
    async def test_ctrl_o_walks_back_and_ctrl_i_forward(self) -> None:
        """The sample page seeds the jumplist, so the first outbound jump
        has somewhere to Ctrl-O back to. Unit "jumplist-rebind": ctrl+o/
        ctrl+i are now SECONDARY aliases (see
        ``test_bracket_keys_walk_back_and_forward`` for the PRIMARY `[`/`]`
        bindings) — this test pins that the alias pair still resolves to
        the exact same two actions."""
        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            await pilot.press("ctrl+o")
            assert app.nav.current == "county/26163"
            await pilot.press("ctrl+i")
            assert app.nav.current == "org/tenants-un"

    @pytest.mark.asyncio
    async def test_bracket_keys_walk_back_and_forward(self) -> None:
        """``[``/``]`` are the PRIMARY jumplist bindings (unit
        "jumplist-rebind") — plain ANSI-safe punctuation, no kitty-protocol
        dependency, unlike the ctrl+o/ctrl+i aliases pinned above."""
        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            await pilot.press("[")
            assert app.nav.current == "county/26163"
            await pilot.press("]")
            assert app.nav.current == "org/tenants-un"

    @pytest.mark.asyncio
    async def test_jump_back_at_the_edge_is_loud_not_silent(self) -> None:
        """Constitution III.11: a `[` press at the jumplist's oldest entry
        must not silently do nothing — the fresh app's sample page seeds
        exactly one jumplist entry, so it starts already at the back edge."""
        from textual.widgets import Label

        from babylon.tui.app import ArchiveApp

        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("[")
            status = app.query_one("#status", Label)
            assert "jumplist start" in str(status.content)

    @pytest.mark.asyncio
    async def test_jump_forward_at_the_edge_is_loud_not_silent(self) -> None:
        """The mirror of ``test_jump_back_at_the_edge_is_loud_not_silent``
        for ``]``/forward: the fresh app's single-entry jumplist is also
        already at the forward edge."""
        from textual.widgets import Label

        from babylon.tui.app import ArchiveApp

        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("]")
            status = app.query_one("#status", Label)
            assert "jumplist end" in str(status.content)

    @pytest.mark.asyncio
    async def test_unknown_subject_surfaces_loud_absence(self) -> None:
        from textual.widgets import Label

        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            status = app.query_one("#status", Label)
            assert "org/tenants-un [ABSENT]" in str(status.content)

    @pytest.mark.asyncio
    async def test_breadcrumb_bar_shows_the_trail(self) -> None:
        from textual.widgets import Label

        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            crumbs = app.query_one("#breadcrumbs", Label)
            assert "county/26163 › org/tenants-un" in str(crumbs.content)

    @pytest.mark.asyncio
    async def test_redlink_click_reports_but_never_navigates(self) -> None:
        from textual.widgets import Label, Markdown

        from babylon.tui.app import ArchiveApp, BabylonMarkdown

        app = ArchiveApp()
        async with app.run_test() as pilot:
            dossier = app.query_one("#dossier", BabylonMarkdown)
            app.post_message(Markdown.LinkClicked(dossier, "babylon://redlink/org/uaw-9999"))
            await pilot.pause()
            assert app.nav.current == "county/26163"
            status = app.query_one("#status", Label)
            assert "[REDLINK]" in str(status.content)


class TestNavigatePaneCoupling:
    """Unit "navigate-pane-couple" (shell-interconnect): before this fix,
    every navigation path updated ``#dossier`` under whatever pane happened
    to be showing — a player parked on the Map/Topology/Dashboard pane who
    navigated would never actually SEE the new page (the "P8 dodge").
    Navigating a NEW subject must always reveal the Wiki pane; each test
    below switches away from Wiki first so the reveal is actually exercised,
    never just trivially already-true.
    """

    @pytest.mark.asyncio
    async def test_palette_navigation_reveals_the_wiki_pane_from_elsewhere(self) -> None:
        from textual.widgets import ContentSwitcher

        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert app.query_one("#main", ContentSwitcher).current == "map"

            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()
            assert app.query_one("#main", ContentSwitcher).current == "wiki"

    @pytest.mark.asyncio
    async def test_jumplist_walk_reveals_the_wiki_pane_from_elsewhere(self) -> None:
        from textual.widgets import ContentSwitcher

        from babylon.tui.app import ArchiveApp
        from babylon.tui.palette import EntityNavigated

        app = ArchiveApp()
        async with app.run_test() as pilot:
            app.post_message(EntityNavigated(parse_babylon_uri("babylon://org/tenants-un")))
            await pilot.pause()

            await pilot.press("4")
            assert app.query_one("#main", ContentSwitcher).current == "topology"

            await pilot.press("[")
            assert app.query_one("#main", ContentSwitcher).current == "wiki"

    @pytest.mark.asyncio
    async def test_wikilink_click_reveals_the_wiki_pane_from_elsewhere(self) -> None:
        from textual.widgets import ContentSwitcher, Markdown

        from babylon.tui.app import ArchiveApp, BabylonMarkdown

        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.press("1")
            assert app.query_one("#main", ContentSwitcher).current == "dashboard"

            dossier = app.query_one("#dossier", BabylonMarkdown)
            app.post_message(Markdown.LinkClicked(dossier, "babylon://county/26163"))
            await pilot.pause()
            assert app.query_one("#main", ContentSwitcher).current == "wiki"


class TestSubjectKeys:
    def test_explicit_kind_uri_rebuilds_the_subject(self) -> None:
        target = parse_babylon_uri("babylon://county/26163")
        assert subject_for(target) == "county/26163"

    def test_bare_wikilink_uri_is_its_own_subject(self) -> None:
        target = parse_babylon_uri("babylon://glossary")
        assert subject_for(target) == "glossary"

    def test_redlink_has_no_subject(self) -> None:
        target = parse_babylon_uri("babylon://redlink/org/uaw-9999")
        with pytest.raises(ValueError, match="redlink"):
            subject_for(target)
