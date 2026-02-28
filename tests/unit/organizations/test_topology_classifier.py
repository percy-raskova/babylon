"""Tests for topology classification (Feature 031, T025).

Tests classify_topology() detecting STAR, HIERARCHY, MESH, CELL topologies
from COMMAND edge subgraphs.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.models.enums import EdgeType, TopologyType
from babylon.organizations.topology import classify_topology


class TestClassifyTopologyStar:
    """STAR: one hub connected to all other nodes."""

    @pytest.mark.math
    def test_star_three_leaves(self) -> None:
        """Hub connected to 3 leaves = STAR."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-hub", "kf-a", "kf-b", "kf-c"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        G.add_edge("kf-hub", "kf-a", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-hub", "kf-b", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-hub", "kf-c", edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", nodes, G)
        assert result.topology_type == TopologyType.STAR
        assert result.is_connected is True
        assert result.component_count == 1
        assert "kf-hub" in result.articulation_points

    @pytest.mark.math
    def test_star_five_leaves(self) -> None:
        """Hub connected to 5 leaves = STAR."""
        G: nx.DiGraph[str] = nx.DiGraph()
        hub = "kf-hub"
        leaves = [f"kf-{i}" for i in range(5)]
        all_nodes = [hub, *leaves]
        for n in all_nodes:
            G.add_node(n, _node_type="key_figure")
        for leaf in leaves:
            G.add_edge(hub, leaf, edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", all_nodes, G)
        assert result.topology_type == TopologyType.STAR


class TestClassifyTopologyHierarchy:
    """HIERARCHY: tree structure, N-1 edges, acyclic."""

    @pytest.mark.math
    def test_hierarchy_chain(self) -> None:
        """Linear chain: A->B->C->D = HIERARCHY (tree with N-1 edges)."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-a", "kf-b", "kf-c", "kf-d"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        G.add_edge("kf-a", "kf-b", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-b", "kf-c", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-c", "kf-d", edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", nodes, G)
        assert result.topology_type == TopologyType.HIERARCHY
        assert result.is_connected is True

    @pytest.mark.math
    def test_hierarchy_tree(self) -> None:
        """Branching tree: root->left, root->right, left->ll, left->lr."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-root", "kf-left", "kf-right", "kf-ll", "kf-lr"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        G.add_edge("kf-root", "kf-left", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-root", "kf-right", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-left", "kf-ll", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-left", "kf-lr", edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", nodes, G)
        assert result.topology_type == TopologyType.HIERARCHY
        assert result.is_connected is True
        assert result.component_count == 1


class TestClassifyTopologyMesh:
    """MESH: near-complete graph with high edge density."""

    @pytest.mark.math
    def test_mesh_complete_graph(self) -> None:
        """Complete graph (all pairs connected) = MESH."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-a", "kf-b", "kf-c", "kf-d"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        # Add COMMAND edges for all pairs (both directions)
        for i, src in enumerate(nodes):
            for j, tgt in enumerate(nodes):
                if i != j:
                    G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", nodes, G)
        assert result.topology_type == TopologyType.MESH
        assert result.is_connected is True

    @pytest.mark.math
    def test_mesh_high_density(self) -> None:
        """Dense graph (>0.6 density) = MESH."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-a", "kf-b", "kf-c", "kf-d", "kf-e"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        # Create enough edges for >0.6 density on undirected projection
        # 5 nodes = 10 possible undirected edges, need >6
        pairs = [
            ("kf-a", "kf-b"),
            ("kf-a", "kf-c"),
            ("kf-a", "kf-d"),
            ("kf-b", "kf-c"),
            ("kf-b", "kf-d"),
            ("kf-c", "kf-d"),
            ("kf-d", "kf-e"),
        ]
        for src, tgt in pairs:
            G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", nodes, G)
        assert result.topology_type == TopologyType.MESH


class TestClassifyTopologyCell:
    """CELL: multiple components linked by bridges/cutouts."""

    @pytest.mark.math
    def test_cell_two_groups_one_bridge(self) -> None:
        """Two cliques connected by one bridge node = CELL."""
        G: nx.DiGraph[str] = nx.DiGraph()
        # Cell 1: a-b-c fully connected
        cell1 = ["kf-a", "kf-b", "kf-c"]
        # Cell 2: d-e-f fully connected
        cell2 = ["kf-d", "kf-e", "kf-f"]
        # Bridge: c -> d
        bridge_node = "kf-bridge"
        all_nodes = [*cell1, *cell2, bridge_node]
        for n in all_nodes:
            G.add_node(n, _node_type="key_figure")

        # Internal cell 1 connections
        for i, src in enumerate(cell1):
            for j, tgt in enumerate(cell1):
                if i != j:
                    G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)
        # Internal cell 2 connections
        for i, src in enumerate(cell2):
            for j, tgt in enumerate(cell2):
                if i != j:
                    G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)
        # Bridge connections
        G.add_edge("kf-c", bridge_node, edge_type=EdgeType.COMMAND)
        G.add_edge(bridge_node, "kf-d", edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", all_nodes, G)
        assert result.topology_type == TopologyType.CELL
        assert result.is_connected is True
        assert bridge_node in result.articulation_points


class TestClassifyTopologyEdgeCases:
    """Edge cases: empty, single node, no COMMAND edges."""

    @pytest.mark.math
    def test_empty_org_no_members(self) -> None:
        """No member nodes → None topology."""
        G: nx.DiGraph[str] = nx.DiGraph()
        result = classify_topology("org-001", [], G)
        assert result.topology_type is None
        assert result.component_count == 0

    @pytest.mark.math
    def test_single_node(self) -> None:
        """Single node → None topology."""
        G: nx.DiGraph[str] = nx.DiGraph()
        G.add_node("kf-a", _node_type="key_figure")
        result = classify_topology("org-001", ["kf-a"], G)
        assert result.topology_type is None

    @pytest.mark.math
    def test_no_command_edges(self) -> None:
        """Multiple nodes but no COMMAND edges → None topology."""
        G: nx.DiGraph[str] = nx.DiGraph()
        G.add_node("kf-a", _node_type="key_figure")
        G.add_node("kf-b", _node_type="key_figure")
        G.add_edge("kf-a", "kf-b", edge_type=EdgeType.MEMBERSHIP)

        result = classify_topology("org-001", ["kf-a", "kf-b"], G)
        assert result.topology_type is None

    @pytest.mark.math
    def test_two_nodes_one_edge(self) -> None:
        """Two nodes, one COMMAND edge = HIERARCHY (minimal tree)."""
        G: nx.DiGraph[str] = nx.DiGraph()
        G.add_node("kf-a", _node_type="key_figure")
        G.add_node("kf-b", _node_type="key_figure")
        G.add_edge("kf-a", "kf-b", edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", ["kf-a", "kf-b"], G)
        assert result.topology_type == TopologyType.HIERARCHY

    @pytest.mark.math
    def test_ignores_non_command_edges(self) -> None:
        """Only COMMAND edges are considered for topology."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-a", "kf-b", "kf-c"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        # MEMBERSHIP edges (should be ignored)
        G.add_edge("kf-a", "kf-b", edge_type=EdgeType.MEMBERSHIP)
        G.add_edge("kf-b", "kf-c", edge_type=EdgeType.MEMBERSHIP)
        # Only one COMMAND edge
        G.add_edge("kf-a", "kf-b", edge_type=EdgeType.COMMAND)

        result = classify_topology("org-001", nodes, G)
        # Two nodes connected, one isolated → disconnected
        assert result.is_connected is False
