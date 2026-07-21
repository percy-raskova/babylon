"""Unit tests for the ``{matrix}`` directive + ``babylon.tui.topology.matrix`` (WO-32).

Deliberately a *separate* test file from ``tests/unit/tui/test_directives.py``
(mirrors ``test_map_room_directive.py``'s own rationale): that file is not one
of Lane T's shared-file zipper points (only ``view_models.py``,
``registry.py``, and ``directives.py`` itself are), and several Lane T work
orders add their own directive simultaneously — keeping each WO's directive
tests in its own file avoids gratuitous merge collisions in a file nobody
declared shared.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.widgets import Label

from babylon.models.enums import CommunityType
from babylon.projection.topology.incidence import AdjacencyMatrix, IncidenceMatrix
from babylon.tui.directives import BabylonFence, parse_matrix_body
from babylon.tui.topology.matrix import render_adjacency_matrix, render_incidence_matrix


class _FenceHost(App[None]):
    """Bare app hosting an arbitrary markdown fragment (mirrors test_directives.py)."""

    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown

    def compose(self) -> ComposeResult:
        from babylon.tui.app import BabylonMarkdown

        yield BabylonMarkdown(self._markdown, open_links=False)


class TestParseMatrixBodyIncidence:
    def test_parses_nodes_edges_and_membership(self) -> None:
        body = "kind: incidence\nnodes: alpha, beta\nedges: settler, women\nalpha: settler\nbeta: settler, women\n"
        matrix = parse_matrix_body(body)
        assert isinstance(matrix, IncidenceMatrix)
        assert matrix.nodes == ("alpha", "beta")
        assert matrix.hyperedges == (CommunityType.SETTLER, CommunityType.WOMEN)
        assert matrix.cells == ((True, False), (True, True))

    def test_a_node_with_no_row_has_no_memberships(self) -> None:
        body = "kind: incidence\nnodes: alpha, beta\nedges: settler\nalpha: settler\n"
        matrix = parse_matrix_body(body)
        assert isinstance(matrix, IncidenceMatrix)
        assert matrix.cells == ((True,), (False,))

    def test_rejects_missing_edges_line(self) -> None:
        with pytest.raises(ValueError, match="edges:"):
            parse_matrix_body("kind: incidence\nnodes: alpha\n")

    def test_rejects_an_edge_that_is_not_a_real_community_type(self) -> None:
        with pytest.raises(ValueError):
            parse_matrix_body(
                "kind: incidence\nnodes: alpha\nedges: not_a_real_type\nalpha: not_a_real_type\n"
            )

    def test_rejects_a_row_referencing_an_undeclared_edge(self) -> None:
        with pytest.raises(ValueError, match="undeclared edge"):
            parse_matrix_body("kind: incidence\nnodes: alpha\nedges: settler\nalpha: women\n")


class TestParseMatrixBodyAdjacency:
    def test_parses_symmetric_adjacency(self) -> None:
        body = "kind: adjacency\nnodes: a, b, c\na: b\nb: a, c\nc: b\n"
        matrix = parse_matrix_body(body)
        assert isinstance(matrix, AdjacencyMatrix)
        assert matrix.nodes == ("a", "b", "c")
        assert matrix.cells == (
            (False, True, False),
            (True, False, True),
            (False, True, False),
        )

    def test_a_node_with_no_row_is_isolated(self) -> None:
        body = "kind: adjacency\nnodes: a, b\na: \n"
        matrix = parse_matrix_body(body)
        assert isinstance(matrix, AdjacencyMatrix)
        assert matrix.cells == ((False, False), (False, False))

    def test_rejects_a_one_sided_declaration(self) -> None:
        with pytest.raises(ValueError, match="symmetrically"):
            parse_matrix_body("kind: adjacency\nnodes: a, b\na: b\n")

    def test_rejects_an_edges_line_on_an_adjacency_body(self) -> None:
        with pytest.raises(ValueError, match="must not declare"):
            parse_matrix_body("kind: adjacency\nnodes: a, b\nedges: settler\n")

    def test_rejects_a_row_referencing_an_undeclared_node(self) -> None:
        with pytest.raises(ValueError, match="undeclared node"):
            parse_matrix_body("kind: adjacency\nnodes: a, b\na: z\nz: a\n")


class TestParseMatrixBodyShared:
    def test_rejects_a_missing_kind_line(self) -> None:
        with pytest.raises(ValueError, match="kind:"):
            parse_matrix_body("nodes: a, b\n")

    def test_rejects_an_unrecognized_kind(self) -> None:
        with pytest.raises(ValueError, match="incidence/adjacency"):
            parse_matrix_body("kind: bogus\nnodes: a\n")

    def test_rejects_a_missing_nodes_line(self) -> None:
        with pytest.raises(ValueError, match="nodes:"):
            parse_matrix_body("kind: adjacency\na: b\n")

    def test_rejects_a_line_with_no_separator(self) -> None:
        with pytest.raises(ValueError, match="':'"):
            parse_matrix_body("kind: adjacency\nnodes: a\nbogus line\n")

    def test_rejects_a_row_naming_an_undeclared_node(self) -> None:
        with pytest.raises(ValueError, match="undeclared node"):
            parse_matrix_body("kind: adjacency\nnodes: a\nz: a\n")


class TestDirectiveMatrixDispatch:
    @pytest.mark.asyncio
    async def test_it_renders_a_known_incidence_matrix(self) -> None:
        app = _FenceHost(
            "```{matrix}\nkind: incidence\nnodes: alpha, beta\nedges: settler\nalpha: settler\n```"
        )
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "settler" in labels[0].content
            assert "alpha" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_renders_a_known_adjacency_matrix(self) -> None:
        app = _FenceHost("```{matrix}\nkind: adjacency\nnodes: a, b\na: b\nb: a\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "a" in labels[0].content
            assert "b" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_refuses_a_malformed_body_loudly(self) -> None:
        app = _FenceHost("```{matrix}\nbogus\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "ABSENT" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_renders_absence_for_a_kind_with_no_nodes(self) -> None:
        """A syntactically well-formed but data-empty matrix (no producer
        attributed yet, mirrors community.py's honest-absence reality) is
        never rendered as a blank/fabricated grid."""
        app = _FenceHost("```{matrix}\nkind: adjacency\nnodes: \n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "no incidence/adjacency data" in labels[0].content


class TestRenderIncidenceMatrix:
    def test_header_names_every_hyperedge(self) -> None:
        matrix = IncidenceMatrix(
            nodes=("alpha", "beta"),
            hyperedges=(CommunityType.SETTLER, CommunityType.WOMEN),
            cells=((True, False), (False, True)),
        )
        text = render_incidence_matrix(matrix)
        assert "settler" in text
        assert "women" in text
        assert "alpha" in text
        assert "beta" in text

    def test_is_deterministic(self) -> None:
        matrix = IncidenceMatrix(
            nodes=("alpha",), hyperedges=(CommunityType.SETTLER,), cells=((True,),)
        )
        assert render_incidence_matrix(matrix) == render_incidence_matrix(matrix)

    def test_empty_matrix_says_so_rather_than_rendering_a_blank_grid(self) -> None:
        matrix = IncidenceMatrix(nodes=(), hyperedges=(), cells=())
        assert "no incidence data" in render_incidence_matrix(matrix)


class TestRenderAdjacencyMatrix:
    def test_diagonal_is_never_a_false_not_adjacent_dot(self) -> None:
        matrix = AdjacencyMatrix(nodes=("a", "b"), cells=((False, True), (True, False)))
        text = render_adjacency_matrix(matrix)
        assert "—" in text

    def test_is_deterministic(self) -> None:
        matrix = AdjacencyMatrix(nodes=("a", "b"), cells=((False, True), (True, False)))
        assert render_adjacency_matrix(matrix) == render_adjacency_matrix(matrix)

    def test_empty_matrix_says_so_rather_than_rendering_a_blank_grid(self) -> None:
        matrix = AdjacencyMatrix(nodes=(), cells=())
        assert "no adjacency data" in render_adjacency_matrix(matrix)


class TestValidationErrorsSurfaceThroughDirective:
    """Sanity check: a body that parses but fails Pydantic shape validation
    (should be unreachable via parse_matrix_body's own construction, but
    proves the directive doesn't crash the app on a ValidationError either
    — it only explicitly catches ValueError, and pydantic's ValidationError
    IS a ValueError subclass, so the same except clause covers it)."""

    def test_validation_error_is_a_value_error(self) -> None:
        with pytest.raises(ValidationError):
            IncidenceMatrix(nodes=("a", "b"), hyperedges=(), cells=((True,),))
        try:
            IncidenceMatrix(nodes=("a", "b"), hyperedges=(), cells=((True,),))
        except ValueError:
            pass
        else:
            pytest.fail("ValidationError must be catchable as ValueError")
