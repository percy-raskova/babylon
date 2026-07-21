"""Unit tests for babylon.tui.directives: fenced-directive dispatch."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from babylon.tui.app import SAMPLE_COUNTY_PAGE, BabylonMarkdown
from babylon.tui.directives import DIRECTIVE_RE, BabylonFence, parse_paoh_body, render_paoh


class _DossierHost(App[None]):
    """Bare app hosting the sample dossier page for fence introspection."""

    def compose(self) -> ComposeResult:
        yield BabylonMarkdown(SAMPLE_COUNTY_PAGE, open_links=False)


class _FenceHost(App[None]):
    """Bare app hosting an arbitrary markdown fragment."""

    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown

    def compose(self) -> ComposeResult:
        yield BabylonMarkdown(self._markdown, open_links=False)


class TestDirectiveRegex:
    def test_it_matches_a_bare_directive_with_no_argument(self) -> None:
        match = DIRECTIVE_RE.match("{absence}")
        assert match is not None
        assert match.group(1) == "absence"
        assert match.group(2) == ""

    def test_it_matches_a_directive_with_an_argument(self) -> None:
        match = DIRECTIVE_RE.match("{statblock} county/26163")
        assert match is not None
        assert match.group(1) == "statblock"
        assert match.group(2) == "county/26163"

    def test_it_does_not_match_an_ordinary_language_fence(self) -> None:
        assert DIRECTIVE_RE.match("python") is None


class TestPaohParsing:
    def test_it_parses_nodes_and_tick_ordered_edges(self) -> None:
        body = "nodes: a, b, c\n9: b, c\n3: a, b\n"
        nodes, edges = parse_paoh_body(body)
        assert nodes == ("a", "b", "c")
        assert edges == ((3, frozenset({"a", "b"})), (9, frozenset({"b", "c"})))

    def test_it_rejects_a_body_with_no_nodes_line(self) -> None:
        with pytest.raises(ValueError, match="nodes:"):
            parse_paoh_body("3: a, b\n")

    def test_it_rejects_an_edge_naming_an_undeclared_node(self) -> None:
        with pytest.raises(ValueError, match="undeclared"):
            parse_paoh_body("nodes: a, b\n3: a, z\n")

    def test_it_renders_deterministic_text_for_a_known_matrix(self) -> None:
        nodes, edges = parse_paoh_body("nodes: a, b\n3: a, b\n")
        assert render_paoh(nodes, edges) == render_paoh(nodes, edges)


class TestBabylonFenceDispatch:
    @pytest.mark.asyncio
    async def test_it_renders_a_known_statblock_directive(self) -> None:
        app = _DossierHost()
        async with app.run_test():
            fences = list(app.query(BabylonFence))
            statblock_fence = next(
                f for f in fences if f._directive() == ("statblock", "county/26163")
            )
            labels = list(statblock_fence.query(Label))
            assert labels
            assert "population" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_refuses_to_render_an_unknown_directive_loudly(self) -> None:
        app = _DossierHost()
        async with app.run_test():
            fences = list(app.query(BabylonFence))
            unknown_fence = next(f for f in fences if f._directive() == ("nonsense", "arg"))
            labels = list(unknown_fence.query(Label))
            assert len(labels) == 1
            assert "UNKNOWN DIRECTIVE" in labels[0].content
            assert "nonsense" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_renders_a_narrative_directive(self) -> None:
        app = _DossierHost()
        async with app.run_test():
            fences = list(app.query(BabylonFence))
            narrative_fence = next(
                f for f in fences if f._directive() is not None and f._directive()[0] == "narrative"
            )
            labels = list(narrative_fence.query(Label))
            assert labels

    @pytest.mark.asyncio
    async def test_it_falls_through_to_highlighting_for_an_ordinary_fence(self) -> None:
        app = _FenceHost("```python\nx = 1\n```")
        async with app.run_test():
            fences = list(app.query(BabylonFence))
            assert len(fences) == 1
            assert fences[0]._directive() is None

    @pytest.mark.asyncio
    async def test_it_renders_an_absence_directive(self) -> None:
        app = _FenceHost("```{absence} county/48999\nno record filed\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "ABSENT" in labels[0].content
            assert "no record filed" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_renders_a_known_paoh_directive(self) -> None:
        app = _FenceHost("```{paoh}\nnodes: a, b\n3: a, b\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "t3" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_renders_a_malformed_paoh_directive_as_a_loud_absence(self) -> None:
        app = _FenceHost("```{paoh}\n3: a, b\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "ABSENT" in labels[0].content
            assert "nodes:" in labels[0].content
