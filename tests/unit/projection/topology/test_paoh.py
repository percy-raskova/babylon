"""Contract tests for :mod:`babylon.projection.topology.paoh` (WO-30).

Fixture-fed, hand-constructed :class:`~babylon.projection.view_models.CommunityView`
dossiers (mirrors ``tests/unit/tui/snapshots/community_snapshot_app.py``'s own
rationale: ``formation_tick`` has no producer in any real game today, so a
dossier exercising it must be hand-built, not harvested) — no engine, no
graph, no database.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import CommunityType
from babylon.projection.topology.paoh import PaohEdge, format_paoh_fence_body, paoh_ordering
from babylon.projection.view_models import CommunityView


def _view(
    community_id: CommunityType,
    *,
    tick: int = 100,
    roster: tuple[str, ...] | None = None,
    formation_tick: int | None = None,
) -> CommunityView:
    return CommunityView(
        community_id=community_id,
        verified_tick=tick,
        roster=roster,
        formation_tick=formation_tick,
    )


class TestPaohOrderingNodes:
    """Node ordering: the sorted union of every attributed roster."""

    def test_nodes_are_the_sorted_union_of_all_rosters(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C002", "C001"), formation_tick=3),
            _view(CommunityType.WOMEN, roster=("C003",), formation_tick=5),
        ]
        nodes, _edges = paoh_ordering(views)
        assert nodes == ("C001", "C002", "C003")

    def test_overlapping_rosters_deduplicate(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C001", "C002"), formation_tick=1),
            _view(CommunityType.PATRIARCHAL, roster=("C002", "C003"), formation_tick=2),
        ]
        nodes, _edges = paoh_ordering(views)
        assert nodes == ("C001", "C002", "C003")

    def test_node_order_is_independent_of_input_order(self) -> None:
        forward = [
            _view(CommunityType.SETTLER, roster=("C002", "C001"), formation_tick=3),
            _view(CommunityType.WOMEN, roster=("C003",), formation_tick=5),
        ]
        reversed_views = list(reversed(forward))
        assert paoh_ordering(forward)[0] == paoh_ordering(reversed_views)[0]

    def test_unattributed_community_contributes_no_nodes(self) -> None:
        views = [_view(CommunityType.SETTLER, roster=None)]
        nodes, edges = paoh_ordering(views)
        assert nodes == ()
        assert edges == ()

    def test_empty_roster_tuple_contributes_no_nodes(self) -> None:
        """An explicit ``()`` roster (never produced by ``project_community``,
        but not forbidden by the model) is treated the same as ``None`` —
        zero members is not a hyperedge either way."""
        views = [_view(CommunityType.SETTLER, roster=())]
        nodes, edges = paoh_ordering(views)
        assert nodes == ()
        assert edges == ()

    def test_no_views_yields_empty_ordering(self) -> None:
        assert paoh_ordering([]) == ((), ())


class TestPaohOrderingEdges:
    """Edge ordering: ascending by formation_tick, None last, ties by community_id."""

    def test_edges_sorted_ascending_by_formation_tick(self) -> None:
        views = [
            _view(CommunityType.WOMEN, roster=("C003",), formation_tick=9),
            _view(CommunityType.SETTLER, roster=("C001",), formation_tick=3),
            _view(CommunityType.PATRIARCHAL, roster=("C002",), formation_tick=6),
        ]
        _nodes, edges = paoh_ordering(views)
        assert [edge.formation_tick for edge in edges] == [3, 6, 9]
        assert [edge.community_id for edge in edges] == [
            CommunityType.SETTLER,
            CommunityType.PATRIARCHAL,
            CommunityType.WOMEN,
        ]

    def test_edge_order_is_independent_of_input_order(self) -> None:
        forward = [
            _view(CommunityType.WOMEN, roster=("C003",), formation_tick=9),
            _view(CommunityType.SETTLER, roster=("C001",), formation_tick=3),
        ]
        reversed_views = list(reversed(forward))
        assert paoh_ordering(forward)[1] == paoh_ordering(reversed_views)[1]

    def test_ties_at_the_same_tick_break_by_community_id(self) -> None:
        views = [
            _view(CommunityType.WOMEN, roster=("C003",), formation_tick=5),
            _view(CommunityType.SETTLER, roster=("C001",), formation_tick=5),
        ]
        _nodes, edges = paoh_ordering(views)
        assert [edge.community_id for edge in edges] == [
            CommunityType.SETTLER,
            CommunityType.WOMEN,
        ]

    def test_edges_without_a_formation_tick_sort_after_every_ticked_edge(self) -> None:
        views = [
            _view(CommunityType.SETTLER, roster=("C001",), formation_tick=None),
            _view(CommunityType.WOMEN, roster=("C002",), formation_tick=100),
        ]
        _nodes, edges = paoh_ordering(views)
        assert [edge.community_id for edge in edges] == [
            CommunityType.WOMEN,
            CommunityType.SETTLER,
        ]

    def test_multiple_untimed_edges_break_ties_by_community_id_too(self) -> None:
        """No producer sets ``formation_tick`` today, so every real dossier
        lands in this branch — the ordering must still be total and
        deterministic across an all-``None`` input, not just the ticked
        case (III.13 — explicit ordering, never accidental)."""
        views = [
            _view(CommunityType.WOMEN, roster=("C003",), formation_tick=None),
            _view(CommunityType.SETTLER, roster=("C001",), formation_tick=None),
            _view(CommunityType.PATRIARCHAL, roster=("C002",), formation_tick=None),
        ]
        _nodes, edges = paoh_ordering(views)
        assert [edge.community_id for edge in edges] == [
            CommunityType.PATRIARCHAL,
            CommunityType.SETTLER,
            CommunityType.WOMEN,
        ]

    def test_edge_carries_the_rosters_members_as_a_frozenset(self) -> None:
        views = [_view(CommunityType.SETTLER, roster=("C001", "C002"), formation_tick=1)]
        _nodes, edges = paoh_ordering(views)
        assert edges[0].members == frozenset({"C001", "C002"})


class TestPaohEdgeModel:
    """Frozen, extra-forbid view-model — matches the keel's CommunityView discipline."""

    def test_is_frozen(self) -> None:
        edge = PaohEdge(
            community_id=CommunityType.SETTLER, formation_tick=1, members=frozenset({"C001"})
        )
        with pytest.raises(ValidationError):
            edge.formation_tick = 2  # type: ignore[misc]

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            PaohEdge(  # type: ignore[call-arg]
                community_id=CommunityType.SETTLER,
                formation_tick=1,
                members=frozenset({"C001"}),
                bogus=1,
            )

    def test_rejects_zero_members(self) -> None:
        with pytest.raises(ValidationError):
            PaohEdge(community_id=CommunityType.SETTLER, formation_tick=1, members=frozenset())


class TestFormatPaohFenceBody:
    """The ``{paoh}`` fence-body serializer — the WO's "wire it into a page" seam."""

    def test_formats_the_nodes_line_and_one_line_per_ticked_edge(self) -> None:
        edges = (
            PaohEdge(
                community_id=CommunityType.SETTLER,
                formation_tick=3,
                members=frozenset({"C002", "C001"}),
            ),
        )
        body = format_paoh_fence_body(("C001", "C002"), edges)
        assert body == "nodes: C001, C002\n3: C001, C002"

    def test_members_serialize_sorted_regardless_of_frozenset_iteration_order(self) -> None:
        edges = (
            PaohEdge(
                community_id=CommunityType.SETTLER,
                formation_tick=1,
                members=frozenset({"zeta", "alpha", "mu"}),
            ),
        )
        body = format_paoh_fence_body(("alpha", "mu", "zeta"), edges)
        assert body.splitlines()[1] == "1: alpha, mu, zeta"

    def test_omits_edges_without_a_formation_tick(self) -> None:
        edges = (
            PaohEdge(
                community_id=CommunityType.SETTLER, formation_tick=None, members=frozenset({"C001"})
            ),
            PaohEdge(
                community_id=CommunityType.WOMEN, formation_tick=2, members=frozenset({"C002"})
            ),
        )
        body = format_paoh_fence_body(("C001", "C002"), edges)
        assert body == "nodes: C001, C002\n2: C002"

    def test_no_edges_still_emits_the_nodes_line(self) -> None:
        assert format_paoh_fence_body(("C001",), ()) == "nodes: C001"

    def test_round_trips_through_the_keels_own_parser(self) -> None:
        """The whole point of this module: its serialized output is exactly
        what ``babylon.tui.directives.parse_paoh_body`` (the keel's already
        shipped, already-tested parser) accepts — no new grammar invented."""
        from babylon.tui.directives import parse_paoh_body

        views = [
            CommunityView(
                community_id=CommunityType.SETTLER,
                verified_tick=847,
                roster=("C001", "C002"),
                formation_tick=3,
            ),
            CommunityView(
                community_id=CommunityType.WOMEN,
                verified_tick=847,
                roster=("C002", "C003"),
                formation_tick=9,
            ),
        ]
        nodes, edges = paoh_ordering(views)
        body = format_paoh_fence_body(nodes, edges)

        parsed_nodes, parsed_edges = parse_paoh_body(body)
        assert parsed_nodes == nodes
        assert parsed_edges == tuple((edge.formation_tick, edge.members) for edge in edges)
