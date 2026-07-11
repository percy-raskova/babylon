"""Unit tests for Sparrow network analysis (Feature 039, T047).

Tests centrality computation, equivalence class grouping, singleton
identification, and cutset detection on known graph structures.
"""

from __future__ import annotations

from babylon.ooda.attention.sparrow import analyze_network
from babylon.topology.graph import BabylonGraph
from tests.unit.state_ai.conftest import (
    make_directed_complete,
    make_directed_cycle,
    make_directed_path,
    make_directed_star,
)


class TestSparrowAnalysisCentrality:
    """T047: Centrality computation on known structures."""

    def test_star_hub_has_highest_degree_centrality(self) -> None:
        """In a star graph, the hub has degree centrality = 1.0."""
        g = make_directed_star(5)

        analysis = analyze_network("t1", 1, g)
        degree = analysis.centrality_rankings.get("degree", {})
        assert degree, "Degree centrality should be computed"
        hub = "node_0"
        assert degree[hub] == max(degree.values()), "Hub should have highest degree centrality"

    def test_star_hub_has_highest_betweenness(self) -> None:
        """In a star graph, the hub has the highest betweenness centrality."""
        g = make_directed_star(5)

        analysis = analyze_network("t1", 1, g)
        betweenness = analysis.centrality_rankings.get("betweenness", {})
        assert betweenness, "Betweenness centrality should be computed"
        hub = "node_0"
        assert betweenness[hub] == max(betweenness.values())

    def test_empty_graph_produces_empty_analysis(self) -> None:
        """Empty graph produces analysis with no rankings."""
        g = BabylonGraph()
        analysis = analyze_network("t1", 1, g)
        assert analysis.centrality_rankings == {}
        assert analysis.equivalence_classes == []
        assert analysis.identified_singletons == frozenset()

    def test_single_node_graph(self) -> None:
        """Single node produces analysis with degree centrality entry."""
        g = BabylonGraph()
        g.add_node("sole_node")
        analysis = analyze_network("t1", 1, g)
        assert "degree" in analysis.centrality_rankings
        # NetworkX returns 1.0 for single-node graphs by convention (0/0 -> 1.0)
        assert "sole_node" in analysis.centrality_rankings["degree"]


class TestSparrowEquivalenceClasses:
    """T047: Equivalence class computation."""

    def test_star_leaves_form_equivalence_class(self) -> None:
        """In a star graph, all leaves are structurally equivalent."""
        g = make_directed_star(4)

        analysis = analyze_network("t1", 1, g)
        # Find the equivalence class containing a leaf
        leaf_class = None
        for ec in analysis.equivalence_classes:
            if "node_1" in ec:
                leaf_class = ec
                break
        assert leaf_class is not None, "Leaf node should be in an equivalence class"
        # All leaves (1-4) should be in the same class
        expected_leaves = frozenset(f"node_{i}" for i in range(1, 5))
        assert leaf_class == expected_leaves

    def test_cycle_all_equivalent(self) -> None:
        """In a cycle graph, all nodes are structurally equivalent."""
        g = make_directed_cycle(5)

        analysis = analyze_network("t1", 1, g)
        # All 5 nodes should be in one equivalence class
        assert len(analysis.equivalence_classes) == 1
        assert len(analysis.equivalence_classes[0]) == 5


class TestSparrowSingletonIdentification:
    """T047: Singleton (critical hub) identification."""

    def test_star_hub_is_singleton(self) -> None:
        """In a star graph, the hub is identified as a singleton."""
        g = make_directed_star(5)

        analysis = analyze_network("t1", 1, g)
        assert "node_0" in analysis.identified_singletons

    def test_cycle_has_no_singletons(self) -> None:
        """In a cycle graph, no node is a singleton (all equivalent)."""
        g = make_directed_cycle(6)

        analysis = analyze_network("t1", 1, g)
        assert len(analysis.identified_singletons) == 0


class TestSparrowCutsets:
    """T047: Minimal cutset detection."""

    def test_star_hub_is_cutset(self) -> None:
        """In a star graph, the hub is an articulation point (cutset)."""
        g = make_directed_star(4)

        analysis = analyze_network("t1", 1, g)
        hub_in_cutset = any("node_0" in cs for cs in analysis.known_cutsets)
        assert hub_in_cutset, "Hub should appear in at least one cutset"

    def test_complete_graph_no_cutsets(self) -> None:
        """In a complete graph, there are no articulation points."""
        g = make_directed_complete(5)

        analysis = analyze_network("t1", 1, g)
        assert analysis.known_cutsets == [], "Complete graph should have no cutsets"

    def test_path_graph_inner_nodes_are_cutsets(self) -> None:
        """In a path graph, inner nodes are articulation points."""
        g = make_directed_path(5)

        analysis = analyze_network("t1", 1, g)
        # Nodes 1, 2, 3 are articulation points in path 0-1-2-3-4
        inner_nodes = {"node_1", "node_2", "node_3"}
        cutset_nodes: set[str] = set()
        for cs in analysis.known_cutsets:
            cutset_nodes.update(cs)
        assert inner_nodes == cutset_nodes
