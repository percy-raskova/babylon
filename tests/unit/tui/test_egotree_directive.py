"""Unit tests for the ``{egotree}`` directive + ``babylon.tui.topology.egotree`` (WO-31).

Deliberately a *separate* test file from ``tests/unit/tui/test_directives.py``:
that file is not one of this WO's shared-file zipper points (only
``view_models.py``, ``registry.py``, and ``directives.py`` itself are), and
several Lane T work orders add their own directive simultaneously — keeping
each WO's directive tests in its own file avoids gratuitous merge collisions
in a file nobody declared shared (mirrors ``test_map_room_directive.py``'s
own stated rationale, WO-33).
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from babylon.projection.topology.levi import LeviEgoTree, LeviNode
from babylon.tui.directives import BabylonFence
from babylon.tui.topology.egotree import parse_egotree_body, render_egotree


class _FenceHost(App[None]):
    """Bare app hosting an arbitrary markdown fragment (mirrors test_directives.py)."""

    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown

    def compose(self) -> ComposeResult:
        from babylon.tui.app import BabylonMarkdown

        yield BabylonMarkdown(self._markdown, open_links=False)


class TestParseEgotreeBody:
    def test_parses_root_side_and_children_in_body_order(self) -> None:
        tree = parse_egotree_body("root: settler\nside: community\nC002: patriarchal\nC001: \n")
        assert tree.root_id == "settler"
        assert tree.root_side == "community"
        assert tree.children == (
            LeviNode(node_id="C002", neighbors=("patriarchal",)),
            LeviNode(node_id="C001", neighbors=()),
        )

    def test_root_and_side_may_appear_in_either_order(self) -> None:
        tree = parse_egotree_body("side: member\nroot: C001\nsettler: C002, C003\n")
        assert tree.root_id == "C001"
        assert tree.root_side == "member"
        assert tree.children == (LeviNode(node_id="settler", neighbors=("C002", "C003")),)

    def test_preserves_child_order_not_sorted(self) -> None:
        tree = parse_egotree_body("root: settler\nside: community\nC999: \nC001: \n")
        assert [child.node_id for child in tree.children] == ["C999", "C001"]

    def test_rejects_missing_root_line(self) -> None:
        with pytest.raises(ValueError, match="root:"):
            parse_egotree_body("side: community\n")

    def test_rejects_missing_side_line(self) -> None:
        with pytest.raises(ValueError, match="side:"):
            parse_egotree_body("root: settler\n")

    def test_rejects_an_invalid_side_value(self) -> None:
        with pytest.raises(ValueError, match="member.*community"):
            parse_egotree_body("root: settler\nside: hyperedge\n")

    def test_rejects_a_line_with_no_separator(self) -> None:
        with pytest.raises(ValueError, match="':'"):
            parse_egotree_body("root: settler\nside: community\nbogus line\n")

    def test_empty_root_value_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_egotree_body("root: \nside: community\n")


class TestRenderEgotree:
    def test_is_deterministic(self) -> None:
        tree = LeviEgoTree(
            root_id="settler",
            root_side="community",
            children=(LeviNode(node_id="C001", neighbors=("patriarchal",)),),
        )
        assert render_egotree(tree) == render_egotree(tree)

    def test_renders_the_root_and_every_child_and_grandchild(self) -> None:
        tree = LeviEgoTree(
            root_id="settler",
            root_side="community",
            children=(
                LeviNode(node_id="C001", neighbors=("patriarchal", "women")),
                LeviNode(node_id="C002", neighbors=()),
            ),
        )
        text = render_egotree(tree)
        assert "settler" in text
        assert "(community)" in text
        assert "C001" in text
        assert "patriarchal" in text
        assert "women" in text
        assert "C002" in text

    def test_a_root_with_no_children_renders_just_the_root_line(self) -> None:
        tree = LeviEgoTree(root_id="C001", root_side="member")
        text = render_egotree(tree)
        assert text == "[b $accent]C001[/] [$text-muted](member)[/]"


class TestDirectiveEgotreeDispatch:
    @pytest.mark.asyncio
    async def test_it_renders_a_well_formed_ego_tree(self) -> None:
        app = _FenceHost("```{egotree}\nroot: settler\nside: community\nC001: patriarchal\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "settler" in labels[0].content
            assert "C001" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_refuses_a_malformed_body_loudly(self) -> None:
        app = _FenceHost("```{egotree}\nside: community\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "ABSENT" in labels[0].content
            assert "root:" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_refuses_an_invalid_side_loudly(self) -> None:
        app = _FenceHost("```{egotree}\nroot: settler\nside: hyperedge\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "ABSENT" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_dispatches_via_the_directive_registry(self) -> None:
        """{egotree} is a known directive, not a silent UNKNOWN-DIRECTIVE refusal."""
        app = _FenceHost("```{egotree}\nroot: settler\nside: community\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert not any("UNKNOWN DIRECTIVE" in label.content for label in labels)
