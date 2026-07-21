"""Unit tests for babylon.tui.palette: the command palette Provider."""

from __future__ import annotations

from typing import Final

import pytest
from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit
from textual.widgets import Label

from babylon.tui.palette import EntityNavigated, EntityNavigatorProvider
from babylon.tui.router import parse_babylon_uri

KNOWN: Final = frozenset({"county/26163", "county/48999", "org/tenants-un", "org/uaw-9999"})
"""Fixture known-entity set: two counties, two orgs — enough to distinguish
"matches this kind" from "matches that kind" in the fuzzy-search tests."""


class _PaletteHost(App[None]):
    """Bare app exposing a known-entity set and recording posted navigations.

    :param known_entities: if given, exposed as ``self.known_entities`` (the
        :class:`~babylon.tui.palette._KnownEntityHost` structural attribute);
        if omitted, the attribute is never set at all, exercising the
        provider's honest-absence path.
    """

    def __init__(self, known_entities: frozenset[str] | None = None) -> None:
        super().__init__()
        if known_entities is not None:
            self.known_entities = known_entities
        self.navigated: list[EntityNavigated] = []

    def compose(self) -> ComposeResult:
        yield Label("host")

    def on_entity_navigated(self, message: EntityNavigated) -> None:
        self.navigated.append(message)


class TestSearch:
    @pytest.mark.asyncio
    async def test_it_ranks_matching_known_entities(self) -> None:
        app = _PaletteHost(KNOWN)
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.search("county")]
            assert {hit.text for hit in hits} == {"county/26163", "county/48999"}
            assert all(isinstance(hit, Hit) for hit in hits)
            assert all(hit.score > 0 for hit in hits)

    @pytest.mark.asyncio
    async def test_it_excludes_non_matching_known_entities(self) -> None:
        app = _PaletteHost(KNOWN)
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.search("tenants")]
            assert {hit.text for hit in hits} == {"org/tenants-un"}

    @pytest.mark.asyncio
    async def test_it_ranks_a_tighter_match_above_a_looser_one(self) -> None:
        app = _PaletteHost(KNOWN)
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            exact_hits = [hit async for hit in provider.search("county/26163")]
            loose_hits = [hit async for hit in provider.search("c26163")]
            exact = next(h for h in exact_hits if h.text == "county/26163")
            loose = next(h for h in loose_hits if h.text == "county/26163")
            assert exact.score > loose.score

    @pytest.mark.asyncio
    async def test_it_is_honestly_empty_absent_a_known_entity_set(self) -> None:
        app = _PaletteHost()
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.search("county")]
            assert hits == []


class TestDiscover:
    @pytest.mark.asyncio
    async def test_it_lists_every_known_entity_as_a_command(self) -> None:
        app = _PaletteHost(KNOWN)
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            assert {hit.text for hit in hits} == KNOWN
            assert all(isinstance(hit, DiscoveryHit) for hit in hits)

    @pytest.mark.asyncio
    async def test_it_lists_in_deterministic_sorted_order(self) -> None:
        app = _PaletteHost(KNOWN)
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            assert [hit.text for hit in hits] == sorted(KNOWN)

    @pytest.mark.asyncio
    async def test_it_never_exceeds_the_known_entity_set_no_verb_commands(self) -> None:
        """No verb commands in the palette (R4): the command set is exactly
        the known-entity set, never wider (e.g. never Article V's verbs)."""
        app = _PaletteHost(KNOWN)
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            assert len(hits) == len(KNOWN)

    @pytest.mark.asyncio
    async def test_it_is_honestly_empty_absent_a_known_entity_set(self) -> None:
        app = _PaletteHost()
        async with app.run_test():
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            assert hits == []


class TestChosenCommand:
    @pytest.mark.asyncio
    async def test_choosing_a_hit_posts_entity_navigated_with_the_parsed_target(self) -> None:
        app = _PaletteHost(KNOWN)
        async with app.run_test() as pilot:
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            hit = next(h for h in hits if h.text == "county/26163")
            hit.command()
            await pilot.pause()
            assert len(app.navigated) == 1
            assert app.navigated[0].target == parse_babylon_uri("babylon://county/26163")

    @pytest.mark.asyncio
    async def test_choosing_a_bare_id_hit_parses_the_wikilink_bare_form(self) -> None:
        app = _PaletteHost(frozenset({"wiki-home"}))
        async with app.run_test() as pilot:
            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            hit = next(iter(hits))
            hit.command()
            await pilot.pause()
            assert len(app.navigated) == 1
            assert app.navigated[0].target.kind == "wikilink"
            assert app.navigated[0].target.entity_id == "wiki-home"
