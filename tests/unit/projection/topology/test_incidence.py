"""Contract tests for :mod:`babylon.projection.topology.incidence` (WO-32).

Fixture-fed with hand-constructed :class:`~babylon.projection.view_models.
CommunityView` instances — no engine, no graph, no ``WorldState`` (community
is never a graph node; see ``community.py``'s own contract tests for the
same discipline). Pins: deterministic lexicographic node/hyperedge ordering
(III.13), honest-absence exclusion of unattributed views, incidence-derived
adjacency sharing the identical node order, and the loud failures the two
Pydantic models + the duplicate-``community_id`` guard raise.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import CommunityType
from babylon.projection.topology.incidence import (
    AdjacencyMatrix,
    IncidenceMatrix,
    adjacency_ordering,
    incidence_ordering,
)
from babylon.projection.view_models import CommunityView


def _view(
    community_id: CommunityType, *, roster: tuple[str, ...] | None = None, tick: int = 5
) -> CommunityView:
    return CommunityView(community_id=community_id, verified_tick=tick, roster=roster)


class TestIncidenceOrdering:
    """Deterministic node/hyperedge ordering + membership cells."""

    def test_nodes_are_the_sorted_union_of_attributed_rosters(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C003", "C001")),
            _view(CommunityType.WOMEN, roster=("C002",)),
        ]
        matrix = incidence_ordering(views)
        assert matrix.nodes == ("C001", "C002", "C003")

    def test_hyperedges_are_sorted_lexicographically_by_community_id(self) -> None:
        views = [
            _view(CommunityType.WOMEN, roster=("C001",)),
            _view(CommunityType.SETTLER, roster=("C001",)),
        ]
        matrix = incidence_ordering(views)
        assert matrix.hyperedges == (CommunityType.SETTLER, CommunityType.WOMEN)

    def test_cells_are_true_exactly_for_real_membership(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C001", "C002")),
            _view(CommunityType.WOMEN, roster=("C002",)),
        ]
        matrix = incidence_ordering(views)
        assert matrix.nodes == ("C001", "C002")
        assert matrix.hyperedges == (CommunityType.SETTLER, CommunityType.WOMEN)
        assert matrix.cells == ((True, False), (True, True))

    def test_unattributed_views_are_excluded_not_zero_filled(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C001",)),
            _view(CommunityType.QUEER, roster=None),
        ]
        matrix = incidence_ordering(views)
        assert matrix.hyperedges == (CommunityType.SETTLER,)

    def test_no_attributed_views_yields_an_honestly_empty_matrix(self) -> None:
        matrix = incidence_ordering([_view(CommunityType.SETTLER, roster=None)])
        assert matrix.nodes == ()
        assert matrix.hyperedges == ()
        assert matrix.cells == ()

    def test_empty_input_yields_an_honestly_empty_matrix(self) -> None:
        matrix = incidence_ordering([])
        assert matrix == IncidenceMatrix(nodes=(), hyperedges=(), cells=())

    def test_rejects_duplicate_community_id_in_input(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C001",)),
            _view(CommunityType.SETTLER, roster=("C002",)),
        ]
        with pytest.raises(ValueError, match="duplicate community_id"):
            incidence_ordering(views)

    def test_is_deterministic_across_input_order(self) -> None:
        forward = [
            _view(CommunityType.SETTLER, roster=("C001", "C002")),
            _view(CommunityType.WOMEN, roster=("C002",)),
        ]
        backward = list(reversed(forward))
        assert incidence_ordering(forward) == incidence_ordering(backward)


class TestAdjacencyOrdering:
    """Co-membership adjacency, derived from the same incidence ordering."""

    def test_shares_identical_node_order_with_incidence(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C003", "C001")),
            _view(CommunityType.WOMEN, roster=("C002",)),
        ]
        assert adjacency_ordering(views).nodes == incidence_ordering(views).nodes

    def test_co_members_of_one_hyperedge_are_mutually_adjacent(self) -> None:
        views = [_view(CommunityType.SETTLER, roster=("C001", "C002", "C003"))]
        matrix = adjacency_ordering(views)
        assert matrix.nodes == ("C001", "C002", "C003")
        assert matrix.cells == (
            (False, True, True),
            (True, False, True),
            (True, True, False),
        )

    def test_members_of_disjoint_hyperedges_are_not_adjacent(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C001",)),
            _view(CommunityType.WOMEN, roster=("C002",)),
        ]
        matrix = adjacency_ordering(views)
        assert matrix.cells == ((False, False), (False, False))

    def test_diagonal_is_always_false(self) -> None:
        views = [_view(CommunityType.SETTLER, roster=("C001", "C002"))]
        matrix = adjacency_ordering(views)
        for index in range(len(matrix.nodes)):
            assert matrix.cells[index][index] is False

    def test_a_node_in_two_hyperedges_becomes_a_centrality_hub(self) -> None:
        """A node co-membered with disjoint groups in two different
        communities is adjacent to every other node — visually a hub, the
        legibility WO-32 exists to provide (Constitution I.21 centrality)."""
        views = [
            _view(CommunityType.SETTLER, roster=("HUB", "C001")),
            _view(CommunityType.WOMEN, roster=("HUB", "C002")),
        ]
        matrix = adjacency_ordering(views)
        hub_row = matrix.cells[matrix.nodes.index("HUB")]
        assert all(hub_row[i] for i in range(len(matrix.nodes)) if matrix.nodes[i] != "HUB")

    def test_a_lone_roster_member_is_a_visual_singleton(self) -> None:
        """A node whose only community has no other member is adjacent to
        nobody — Constitution I.21 singleton legibility."""
        views = [
            _view(CommunityType.SETTLER, roster=("LONE",)),
            _view(CommunityType.WOMEN, roster=("C001", "C002")),
        ]
        matrix = adjacency_ordering(views)
        lone_row = matrix.cells[matrix.nodes.index("LONE")]
        assert not any(lone_row)

    def test_empty_input_yields_an_honestly_empty_matrix(self) -> None:
        assert adjacency_ordering([]) == AdjacencyMatrix(nodes=(), cells=())


class TestIncidenceMatrixShapeValidation:
    def test_rejects_row_count_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="row"):
            IncidenceMatrix(nodes=("a", "b"), hyperedges=(CommunityType.SETTLER,), cells=((True,),))

    def test_rejects_row_length_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="hyperedge"):
            IncidenceMatrix(
                nodes=("a",),
                hyperedges=(CommunityType.SETTLER, CommunityType.WOMEN),
                cells=((True,),),
            )


class TestAdjacencyMatrixShapeValidation:
    def test_rejects_non_square_grid(self) -> None:
        with pytest.raises(ValidationError, match="node"):
            AdjacencyMatrix(nodes=("a", "b"), cells=((False,),))

    def test_rejects_a_true_diagonal_cell(self) -> None:
        with pytest.raises(ValidationError, match="diagonal"):
            AdjacencyMatrix(nodes=("a",), cells=((True,),))

    def test_rejects_an_asymmetric_grid(self) -> None:
        with pytest.raises(ValidationError, match="symmetric"):
            AdjacencyMatrix(
                nodes=("a", "b"),
                cells=((False, True), (False, False)),
            )
