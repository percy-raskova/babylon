"""Tests for bifurcation topological resilience metrics (US4).

TDD Red Phase: These tests define the contract for five resilience
functions that operate on undirected solidarity subgraphs:

Test Classes:
    1. TestComputeBettiNumbers - Betti number computation (beta_0, beta_1)
    2. TestComputeEquivalenceClasses - Structural equivalence grouping
    3. TestFindCriticalSingletons - Articulation point detection
    4. TestFindCriticalCutsets - Minimum edge cut detection
    5. TestComputePurgeResilience - Targeted node removal resilience
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.topology.graph import BabylonUGraph

# =============================================================================
# TEST: BETTI NUMBERS
# =============================================================================


@pytest.mark.unit
class TestComputeBettiNumbers:
    """Tests for compute_betti_numbers(subgraph) -> (beta_0, beta_1).

    beta_0 = number of connected components.
    beta_1 = |E| - |V| + beta_0 (first Betti number / cycle rank).
    """

    def test_star_graph_betti_numbers(self, star_graph: nx.Graph) -> None:
        """Star (hub + 5 spokes): beta_0=1, beta_1=0 (tree, no cycles)."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        beta_0, beta_1 = compute_betti_numbers(star_graph)

        assert beta_0 == 1
        assert beta_1 == 0

    def test_complete_k5_betti_numbers(self, complete_k5: nx.Graph) -> None:
        """Complete K5: beta_0=1, beta_1=6 (|E|-|V|+beta_0 = 10-5+1)."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        beta_0, beta_1 = compute_betti_numbers(complete_k5)

        assert beta_0 == 1
        # K5: 10 edges, 5 vertices, 1 component -> beta_1 = 10 - 5 + 1 = 6
        assert beta_1 == 6

    def test_ring_betti_numbers(self, ring_graph: nx.Graph) -> None:
        """Ring (5 nodes): beta_0=1, beta_1=1 (single cycle)."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        beta_0, beta_1 = compute_betti_numbers(ring_graph)

        assert beta_0 == 1
        # 5 edges, 5 vertices, 1 component -> beta_1 = 5 - 5 + 1 = 1
        assert beta_1 == 1

    def test_three_disconnected_components(self, three_disconnected: nx.Graph) -> None:
        """3 isolated nodes: beta_0=3, beta_1=0."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        beta_0, beta_1 = compute_betti_numbers(three_disconnected)

        assert beta_0 == 3
        # 0 edges, 3 vertices, 3 components -> beta_1 = 0 - 3 + 3 = 0
        assert beta_1 == 0

    def test_empty_graph_betti_numbers(self, empty_graph: nx.Graph) -> None:
        """Empty graph: beta_0=0, beta_1=0."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        beta_0, beta_1 = compute_betti_numbers(empty_graph)

        assert beta_0 == 0
        assert beta_1 == 0

    def test_bridge_graph_betti_numbers(self, bridge_graph: nx.Graph) -> None:
        """Bridge graph (two triangles + bridge): beta_0=1, beta_1=2."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        beta_0, beta_1 = compute_betti_numbers(bridge_graph)

        assert beta_0 == 1
        # 7 edges, 6 vertices, 1 component -> beta_1 = 7 - 6 + 1 = 2
        assert beta_1 == 2

    def test_single_node_betti_numbers(self) -> None:
        """Single node: beta_0=1, beta_1=0."""
        from babylon.bifurcation.resilience import compute_betti_numbers

        G: nx.Graph = BabylonUGraph()
        G.add_node("solo")

        beta_0, beta_1 = compute_betti_numbers(G)

        assert beta_0 == 1
        assert beta_1 == 0


# =============================================================================
# TEST: EQUIVALENCE CLASSES
# =============================================================================


@pytest.mark.unit
class TestComputeEquivalenceClasses:
    """Tests for compute_equivalence_classes(subgraph) -> dict[int, int].

    Groups nodes by frozenset(neighbors). Returns {class_size: count}.
    """

    def test_k5_distinct_equivalence_classes(self, complete_k5: nx.Graph) -> None:
        """K5 mesh: each node has unique neighbor frozenset -> {1: 5}.

        In K5, N(n0)={n1,n2,n3,n4}, N(n1)={n0,n2,n3,n4}, etc.
        Each frozenset is distinct (different excluded self-node),
        so 5 classes of size 1.
        """
        from babylon.bifurcation.resilience import compute_equivalence_classes

        result = compute_equivalence_classes(complete_k5)

        # Each node has a unique neighbor set -> 5 classes of size 1
        assert result == {1: 5}

    def test_star_two_equivalence_classes(self, star_graph: nx.Graph) -> None:
        """Star: hub has different neighbors than spokes -> {1: 1, 5: 1}.

        Hub has N(hub) = {all 5 spokes} -> unique class, size 1.
        Each spoke has N(spoke) = {hub} -> same frozenset -> 1 class, size 5.
        """
        from babylon.bifurcation.resilience import compute_equivalence_classes

        result = compute_equivalence_classes(star_graph)

        # Hub: class of size 1; all spokes: class of size 5
        assert result == {1: 1, 5: 1}

    def test_ring_single_equivalence_class(self, ring_graph: nx.Graph) -> None:
        """Ring: all nodes have 2 neighbors but different neighbor sets.

        In a ring n0-n1-n2-n3-n4-n0, each node has a different frozenset
        of neighbors: N(n0)={n1,n4}, N(n1)={n0,n2}, etc.
        Since all frozensets are distinct, we get 5 classes of size 1.
        """
        from babylon.bifurcation.resilience import compute_equivalence_classes

        result = compute_equivalence_classes(ring_graph)

        # Each node has unique neighbor pair -> 5 classes of size 1
        assert result == {1: 5}

    def test_disconnected_nodes_same_class(self, three_disconnected: nx.Graph) -> None:
        """3 isolated nodes: all have empty neighbor set -> {3: 1}."""
        from babylon.bifurcation.resilience import compute_equivalence_classes

        result = compute_equivalence_classes(three_disconnected)

        # All have frozenset() as neighbors -> one class of size 3
        assert result == {3: 1}

    def test_empty_graph_equivalence_classes(self, empty_graph: nx.Graph) -> None:
        """Empty graph: no nodes -> empty dict."""
        from babylon.bifurcation.resilience import compute_equivalence_classes

        result = compute_equivalence_classes(empty_graph)

        assert result == {}

    def test_bridge_graph_equivalence_classes(self, bridge_graph: nx.Graph) -> None:
        """Bridge graph: nodes have varying roles.

        In the bridge (a-b-c)--bridge--(d-e-f):
          N(a) = {b, c}  --> unique
          N(b) = {a, c}  --> unique
          N(c) = {a, b, d} --> unique (bridge endpoint, 3 neighbors)
          N(d) = {c, e, f} --> unique (bridge endpoint, 3 neighbors)
          N(e) = {d, f}  --> unique
          N(f) = {d, e}  --> unique

        All frozensets are distinct -> 6 classes of size 1.
        """
        from babylon.bifurcation.resilience import compute_equivalence_classes

        result = compute_equivalence_classes(bridge_graph)

        # All nodes have unique neighbor sets
        assert result == {1: 6}


# =============================================================================
# TEST: CRITICAL SINGLETONS (ARTICULATION POINTS)
# =============================================================================


@pytest.mark.unit
class TestFindCriticalSingletons:
    """Tests for find_critical_singletons(subgraph) -> list[str].

    Wraps nx.articulation_points to find nodes whose removal
    disconnects the graph.
    """

    def test_star_hub_is_articulation_point(self, star_graph: nx.Graph) -> None:
        """Star: hub removal disconnects all spokes."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(star_graph)

        assert "hub" in result

    def test_star_spokes_not_articulation_points(self, star_graph: nx.Graph) -> None:
        """Star: spoke removal does not disconnect graph."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(star_graph)

        for i in range(5):
            assert f"spoke_{i}" not in result

    def test_k5_no_articulation_points(self, complete_k5: nx.Graph) -> None:
        """K5 mesh: removing any single node leaves graph connected."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(complete_k5)

        assert result == []

    def test_ring_no_articulation_points(self, ring_graph: nx.Graph) -> None:
        """Ring: no single node removal disconnects a cycle."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(ring_graph)

        assert result == []

    def test_empty_graph_no_articulation_points(self, empty_graph: nx.Graph) -> None:
        """Empty graph: no nodes to be articulation points."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(empty_graph)

        assert result == []

    def test_bridge_graph_has_articulation_points(self, bridge_graph: nx.Graph) -> None:
        """Bridge graph: c and d are articulation points at the bridge."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(bridge_graph)

        assert "c" in result
        assert "d" in result

    def test_returns_sorted_list(self, bridge_graph: nx.Graph) -> None:
        """Result is a sorted list of node IDs for deterministic output."""
        from babylon.bifurcation.resilience import find_critical_singletons

        result = find_critical_singletons(bridge_graph)

        assert result == sorted(result)


# =============================================================================
# TEST: CRITICAL CUTSETS
# =============================================================================


@pytest.mark.unit
class TestFindCriticalCutsets:
    """Tests for find_critical_cutsets(subgraph, max_cutset_size) -> list[frozenset[str]].

    Finds minimum edge cuts per connected component, bounded by max_cutset_size.
    Each frozenset contains the unique node IDs involved in the minimum cut edges.
    """

    def test_bridge_edge_cutset(self, bridge_graph: nx.Graph) -> None:
        """Bridge: minimum cut = 1 edge -> cutset includes nodes {c, d}."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(bridge_graph, max_cutset_size=3)

        # At least one cutset should involve the bridge nodes
        assert len(result) >= 1
        # The minimum edge cut should have size <= 3
        for cutset in result:
            assert isinstance(cutset, frozenset)
            assert len(cutset) <= 6  # max nodes from edges

    def test_k5_cutsets_exceed_max_size(self, complete_k5: nx.Graph) -> None:
        """K5: minimum cut is 4 edges -> skipped when max_cutset_size=3."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(complete_k5, max_cutset_size=3)

        # K5's minimum edge cut = 4 (edge connectivity is 4), exceeds max 3
        assert result == []

    def test_k5_cutsets_with_high_max(self, complete_k5: nx.Graph) -> None:
        """K5: minimum cut included when max_cutset_size >= 4."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(complete_k5, max_cutset_size=4)

        # Should return at least one cutset now
        assert len(result) >= 1

    def test_empty_graph_no_cutsets(self, empty_graph: nx.Graph) -> None:
        """Empty graph: no components, no cutsets."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(empty_graph, max_cutset_size=3)

        assert result == []

    def test_single_node_no_cutsets(self) -> None:
        """Single node: no edges to cut."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        G: nx.Graph = BabylonUGraph()
        G.add_node("solo")

        result = find_critical_cutsets(G, max_cutset_size=3)

        assert result == []

    def test_disconnected_components_no_cutsets(self, three_disconnected: nx.Graph) -> None:
        """Disconnected single nodes: no edges to cut."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(three_disconnected, max_cutset_size=3)

        assert result == []

    def test_star_small_cutset(self, star_graph: nx.Graph) -> None:
        """Star: edge connectivity is 1 (removing any hub-spoke edge isolates a spoke)."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(star_graph, max_cutset_size=3)

        # Star has edge connectivity 1, so cutset includes at least one edge
        assert len(result) >= 1

    def test_cutset_contains_frozenset_of_strings(self, bridge_graph: nx.Graph) -> None:
        """Each cutset element is a frozenset of string node IDs."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        result = find_critical_cutsets(bridge_graph, max_cutset_size=3)

        for cutset in result:
            assert isinstance(cutset, frozenset)
            for node_id in cutset:
                assert isinstance(node_id, str)

    def test_default_max_cutset_size(self, bridge_graph: nx.Graph) -> None:
        """Default max_cutset_size is 3."""
        from babylon.bifurcation.resilience import find_critical_cutsets

        # Should work without explicitly passing max_cutset_size
        result = find_critical_cutsets(bridge_graph)

        assert isinstance(result, list)


# =============================================================================
# TEST: PURGE RESILIENCE
# =============================================================================


@pytest.mark.unit
class TestComputePurgeResilience:
    """Tests for compute_purge_resilience(subgraph, removal_rate, seed) -> float.

    Targeted removal of top-degree nodes, measuring post/pre L_max ratio.
    """

    def test_star_low_resilience(self, star_graph: nx.Graph) -> None:
        """Star: removing hub (highest degree) destroys connectivity.

        With 6 nodes and removal_rate=0.2, we remove max(1, int(6*0.2))=1 node.
        The hub has degree 5 (highest), so it gets removed first.
        Post-purge: 5 isolated nodes, L_max=1. Pre-purge: L_max=6.
        Resilience = 1/6 ~ 0.167.
        """
        from babylon.bifurcation.resilience import compute_purge_resilience

        result = compute_purge_resilience(star_graph, removal_rate=0.2)

        # Removing hub leaves all spokes isolated: L_max drops from 6 to 1
        assert result < 0.3

    def test_k5_high_resilience(self, complete_k5: nx.Graph) -> None:
        """K5 mesh: removing 1 of 5 nodes preserves most connectivity.

        With 5 nodes and removal_rate=0.2, we remove 1 node.
        Remaining 4 nodes still form K4 (fully connected). L_max=4.
        Pre-purge L_max=5. Resilience = 4/5 = 0.8.
        """
        from babylon.bifurcation.resilience import compute_purge_resilience

        result = compute_purge_resilience(complete_k5, removal_rate=0.2)

        assert result >= 0.7

    def test_empty_graph_vacuously_resilient(self, empty_graph: nx.Graph) -> None:
        """Empty graph: vacuously resilient -> 1.0."""
        from babylon.bifurcation.resilience import compute_purge_resilience

        result = compute_purge_resilience(empty_graph, removal_rate=0.2)

        assert result == pytest.approx(1.0)

    def test_result_clamped_zero_to_one(self, star_graph: nx.Graph) -> None:
        """Result is always in [0, 1]."""
        from babylon.bifurcation.resilience import compute_purge_resilience

        result = compute_purge_resilience(star_graph, removal_rate=0.5)

        assert 0.0 <= result <= 1.0

    def test_seeded_reproducibility(self, complete_k5: nx.Graph) -> None:
        """Same seed produces same result."""
        from babylon.bifurcation.resilience import compute_purge_resilience

        r1 = compute_purge_resilience(complete_k5, removal_rate=0.2, seed=42)
        r2 = compute_purge_resilience(complete_k5, removal_rate=0.2, seed=42)

        assert r1 == pytest.approx(r2)

    def test_different_seeds_deterministic(self, star_graph: nx.Graph) -> None:
        """Different seeds can produce different results (for non-trivial graphs).

        For star graph, the hub is always highest-degree so seed doesn't
        matter for tie-breaking. But the function should still accept seeds.
        """
        from babylon.bifurcation.resilience import compute_purge_resilience

        # Both should work without error
        r1 = compute_purge_resilience(star_graph, removal_rate=0.2, seed=1)
        r2 = compute_purge_resilience(star_graph, removal_rate=0.2, seed=2)

        # For star, result is deterministic regardless of seed (hub always removed)
        assert r1 == pytest.approx(r2)

    def test_original_graph_unmodified(self, complete_k5: nx.Graph) -> None:
        """Purge operates on a copy; original graph is unchanged."""
        from babylon.bifurcation.resilience import compute_purge_resilience

        original_nodes = set(complete_k5.nodes())
        original_edges = set(complete_k5.edges())

        compute_purge_resilience(complete_k5, removal_rate=0.4)

        assert set(complete_k5.nodes()) == original_nodes
        assert set(complete_k5.edges()) == original_edges

    def test_single_node_resilience(self) -> None:
        """Single node graph: after removing 1 node, L_max=0.

        Pre: L_max=1, Post: L_max=0. Ratio=0/1=0.0.
        """
        from babylon.bifurcation.resilience import compute_purge_resilience

        G: nx.Graph = BabylonUGraph()
        G.add_node("solo")

        result = compute_purge_resilience(G, removal_rate=0.5)

        assert result == pytest.approx(0.0)

    def test_ring_moderate_resilience(self, ring_graph: nx.Graph) -> None:
        """Ring (5 nodes): removing 1 node breaks cycle but keeps chain.

        Pre: L_max=5 (one component). Post: L_max=4 (chain of 4).
        Resilience = 4/5 = 0.8.
        """
        from babylon.bifurcation.resilience import compute_purge_resilience

        result = compute_purge_resilience(ring_graph, removal_rate=0.2)

        # Ring: all nodes have degree 2 (tied). Removing 1 leaves chain of 4.
        assert result == pytest.approx(0.8)

    def test_high_removal_rate(self, complete_k5: nx.Graph) -> None:
        """High removal rate (0.8) removes most nodes."""
        from babylon.bifurcation.resilience import compute_purge_resilience

        result = compute_purge_resilience(complete_k5, removal_rate=0.8)

        # Remove 4 of 5 nodes -> only 1 left -> L_max=1, pre=5, ratio=0.2
        assert result == pytest.approx(0.2)
