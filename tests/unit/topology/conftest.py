"""Test fixtures for topology tests.

Provides graph construction helpers for testing solidarity network
analysis including connected components, liquidity, and resilience.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.models.enums import EdgeType


@pytest.fixture
def empty_digraph() -> nx.DiGraph:
    """Create an empty directed graph."""
    return nx.DiGraph()


@pytest.fixture
def single_node_graph() -> nx.DiGraph:
    """Create a graph with one social_class node, no edges."""
    G: nx.DiGraph = nx.DiGraph()
    G.add_node(
        "C001",
        _node_type="social_class",
        ideology={"class_consciousness": 0.5, "national_identity": 0.5, "agitation": 0.0},
    )
    return G


@pytest.fixture
def two_isolated_nodes() -> nx.DiGraph:
    """Create a graph with two isolated social_class nodes."""
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("C001", _node_type="social_class")
    G.add_node("C002", _node_type="social_class")
    return G


@pytest.fixture
def connected_pair() -> nx.DiGraph:
    """Create a graph with two nodes connected by SOLIDARITY edge."""
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("C001", _node_type="social_class")
    G.add_node("C002", _node_type="social_class")
    G.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    return G


@pytest.fixture
def mixed_edges_graph() -> nx.DiGraph:
    """Create a graph with both SOLIDARITY and non-SOLIDARITY edges."""
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("C001", _node_type="social_class")
    G.add_node("C002", _node_type="social_class")
    G.add_node("C003", _node_type="social_class")
    # SOLIDARITY edge
    G.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.6)
    # Non-SOLIDARITY edge (should be excluded)
    G.add_edge("C002", "C003", edge_type=EdgeType.EXPLOITATION, value_flow=0.5)
    return G


@pytest.fixture
def territory_mixed_graph() -> nx.DiGraph:
    """Create a graph with both social_class and territory nodes."""
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("C001", _node_type="social_class")
    G.add_node("C002", _node_type="social_class")
    G.add_node("T001", _node_type="territory")
    G.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.5)
    G.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)
    return G


@pytest.fixture
def weak_strong_edges() -> nx.DiGraph:
    """Create a graph with edges of varying solidarity_strength."""
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("C001", _node_type="social_class")
    G.add_node("C002", _node_type="social_class")
    G.add_node("C003", _node_type="social_class")
    G.add_node("C004", _node_type="social_class")
    # Weak edge (< 0.5 but > 0.1) - sympathizer
    G.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.3)
    # Strong edge (> 0.5) - cadre
    G.add_edge("C002", "C003", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.7)
    # Very weak edge (< 0.1) - should be filtered out of potential
    G.add_edge("C003", "C004", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.05)
    return G


@pytest.fixture
def star_topology() -> nx.DiGraph:
    """Create a star topology (fragile - hub is single point of failure)."""
    G: nx.DiGraph = nx.DiGraph()
    # Central hub
    G.add_node("C_HUB", _node_type="social_class")
    # Spokes
    for i in range(5):
        node_id = f"C00{i}"
        G.add_node(node_id, _node_type="social_class")
        G.add_edge("C_HUB", node_id, edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    return G


@pytest.fixture
def mesh_topology() -> nx.DiGraph:
    """Create a mesh topology (resilient - no single point of failure)."""
    G: nx.DiGraph = nx.DiGraph()
    nodes = ["C001", "C002", "C003", "C004", "C005"]
    for node_id in nodes:
        G.add_node(node_id, _node_type="social_class")
    # Create mesh connections (each node connected to multiple others)
    edges = [
        ("C001", "C002"),
        ("C001", "C003"),
        ("C002", "C003"),
        ("C002", "C004"),
        ("C003", "C004"),
        ("C003", "C005"),
        ("C004", "C005"),
    ]
    for src, tgt in edges:
        G.add_edge(src, tgt, edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    return G


@pytest.fixture
def multi_component_graph() -> nx.DiGraph:
    """Create a graph with multiple disconnected components."""
    G: nx.DiGraph = nx.DiGraph()
    # Component 1: 3 nodes
    G.add_node("C001", _node_type="social_class")
    G.add_node("C002", _node_type="social_class")
    G.add_node("C003", _node_type="social_class")
    G.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    G.add_edge("C002", "C003", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    # Component 2: 2 nodes (isolated from component 1)
    G.add_node("C004", _node_type="social_class")
    G.add_node("C005", _node_type="social_class")
    G.add_edge("C004", "C005", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    # Component 3: 1 isolated node
    G.add_node("C006", _node_type="social_class")
    return G
