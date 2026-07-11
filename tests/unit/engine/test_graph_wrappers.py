"""RED phase: Tests for DyadicGraph and CommunityHypergraph wrappers.

Spec 040 Discipline 5: Dyadic edges (NetworkX) and hyperedges (XGI)
are accessed through typed wrapper services, not raw data structures.
"""

from __future__ import annotations

from babylon.engine.graph_wrappers import CommunityHypergraph, DyadicGraph
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph


class TestDyadicGraph:
    """DyadicGraph wraps NetworkX DiGraph with typed edge operations."""

    def test_wrap_creates_dyadic_graph(self) -> None:
        """Can wrap a raw NetworkX graph."""
        g = BabylonGraph()
        dg = DyadicGraph(g)
        assert dg.raw is g

    def test_add_and_query_edge(self) -> None:
        """Can add and query typed edges."""
        g = BabylonGraph()
        g.add_node("C001", _node_type="social_class")
        g.add_node("C002", _node_type="social_class")
        dg = DyadicGraph(g)
        dg.add_edge("C001", "C002", EdgeType.SOLIDARITY, solidarity_strength=0.5)

        edges = list(dg.edges_of_type(EdgeType.SOLIDARITY))
        assert len(edges) == 1
        assert edges[0] == ("C001", "C002")

    def test_edge_type_filtering(self) -> None:
        """edges_of_type only returns edges of the specified type."""
        g = BabylonGraph()
        g.add_node("C001", _node_type="social_class")
        g.add_node("C002", _node_type="social_class")
        dg = DyadicGraph(g)
        dg.add_edge("C001", "C002", EdgeType.SOLIDARITY)
        dg.add_edge("C002", "C001", EdgeType.EXPLOITATION)

        solidarity_edges = list(dg.edges_of_type(EdgeType.SOLIDARITY))
        assert len(solidarity_edges) == 1

    def test_node_count(self) -> None:
        """Reports correct node count."""
        g = BabylonGraph()
        g.add_node("C001", _node_type="social_class")
        g.add_node("T001", _node_type="territory")
        dg = DyadicGraph(g)
        assert len(dg) == 2


class TestCommunityHypergraph:
    """CommunityHypergraph wraps XGI Hypergraph with typed operations."""

    def test_empty_hypergraph(self) -> None:
        """Can create an empty community hypergraph."""
        ch = CommunityHypergraph()
        assert len(ch) == 0

    def test_add_community(self) -> None:
        """Can add a community with members."""
        ch = CommunityHypergraph()
        ch.add_community("settler", members=["C001", "C002"])
        assert len(ch) == 1
        assert "settler" in ch.community_ids

    def test_members_of(self) -> None:
        """Can retrieve members of a community."""
        ch = CommunityHypergraph()
        ch.add_community("settler", members=["C001", "C002"])
        members = ch.members_of("settler")
        assert set(members) == {"C001", "C002"}

    def test_shared_communities(self) -> None:
        """Can find shared communities between agents."""
        ch = CommunityHypergraph()
        ch.add_community("settler", members=["C001", "C002"])
        ch.add_community("youth", members=["C001", "C003"])
        shared = ch.shared_communities("C001", "C002")
        assert shared == {"settler"}
