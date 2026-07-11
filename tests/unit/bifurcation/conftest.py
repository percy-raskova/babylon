"""Test fixtures for bifurcation topology analysis (Feature 033).

Provides graph builders, hypergraph builders, community states, and
BifurcationDefines fixtures for testing consciousness-weighted solidarity
analysis.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import (
    CommunityState,
)
from babylon.models.enums import (
    CommunityType,
    ConsciousnessTendency,
)
from babylon.topology.graph import BabylonUGraph

from .factories import make_community_state

# =============================================================================
# BifurcationDefines
# =============================================================================


@pytest.fixture
def bifurcation_defines() -> BifurcationDefines:
    """Default BifurcationDefines with standard values."""
    return BifurcationDefines()


# =============================================================================
# Community States at Varying CI Levels
# =============================================================================


@pytest.fixture
def low_ci_states() -> dict[CommunityType, CommunityState]:
    """Community states with CI=0.1 (assimilated)."""
    return {
        CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
        CommunityType.WOMEN: make_community_state(CommunityType.WOMEN, ci=0.1),
        CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.1),
        CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.1),
        CommunityType.DISABLED: make_community_state(
            CommunityType.DISABLED, ci=0.1, infrastructure=0.5
        ),
    }


@pytest.fixture
def medium_ci_states() -> dict[CommunityType, CommunityState]:
    """Community states with CI=0.4 (near midpoint)."""
    return {
        CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.4),
        CommunityType.WOMEN: make_community_state(CommunityType.WOMEN, ci=0.4),
        CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.4),
        CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.4),
        CommunityType.DISABLED: make_community_state(
            CommunityType.DISABLED, ci=0.4, infrastructure=0.5
        ),
    }


@pytest.fixture
def high_ci_states() -> dict[CommunityType, CommunityState]:
    """Community states with CI=0.7 (oppositional)."""
    return {
        CommunityType.NEW_AFRIKAN: make_community_state(
            CommunityType.NEW_AFRIKAN,
            ci=0.7,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        ),
        CommunityType.WOMEN: make_community_state(
            CommunityType.WOMEN,
            ci=0.7,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        ),
        CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
        CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.3),
        CommunityType.DISABLED: make_community_state(
            CommunityType.DISABLED,
            ci=0.7,
            infrastructure=0.5,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        ),
    }


@pytest.fixture
def very_high_ci_states() -> dict[CommunityType, CommunityState]:
    """Community states with CI=0.8 (near max oppositional)."""
    return {
        CommunityType.NEW_AFRIKAN: make_community_state(
            CommunityType.NEW_AFRIKAN,
            ci=0.8,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        ),
        CommunityType.WOMEN: make_community_state(
            CommunityType.WOMEN,
            ci=0.8,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        ),
        CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
        CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.3),
        CommunityType.DISABLED: make_community_state(
            CommunityType.DISABLED,
            ci=0.8,
            infrastructure=0.7,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        ),
    }


# =============================================================================
# Undirected Graph Fixtures (for resilience metrics)
# =============================================================================


@pytest.fixture
def empty_graph() -> nx.Graph:
    """Create an empty undirected graph (no nodes, no edges)."""
    return BabylonUGraph()


@pytest.fixture
def star_graph() -> nx.Graph:
    """Create a star graph with 1 hub and 5 spokes (6 nodes, 5 edges).

    Topology: hub connects to each spoke; spokes are not connected
    to each other. Hub is an articulation point.
    """
    G: nx.Graph = BabylonUGraph()
    G.add_node("hub")
    for i in range(5):
        spoke = f"spoke_{i}"
        G.add_node(spoke)
        G.add_edge("hub", spoke)
    return G


@pytest.fixture
def complete_k5() -> nx.Graph:
    """Create a complete graph K5 (5 nodes, 10 edges).

    Every node connects to every other node. No articulation points.
    Highly resilient topology.
    """
    G: nx.Graph = BabylonUGraph()
    nodes = [f"n{i}" for i in range(5)]
    for node in nodes:
        G.add_node(node)
    for i in range(5):
        for j in range(i + 1, 5):
            G.add_edge(nodes[i], nodes[j])
    return G


@pytest.fixture
def ring_graph() -> nx.Graph:
    """Create a ring (cycle) graph with 5 nodes.

    Topology: n0-n1-n2-n3-n4-n0. One cycle, no articulation points.
    beta_0=1, beta_1=1.
    """
    G: nx.Graph = BabylonUGraph()
    nodes = [f"n{i}" for i in range(5)]
    for node in nodes:
        G.add_node(node)
    for i in range(5):
        G.add_edge(nodes[i], nodes[(i + 1) % 5])
    return G


@pytest.fixture
def three_disconnected() -> nx.Graph:
    """Create 3 disconnected single-node components.

    beta_0=3, beta_1=0.
    """
    G: nx.Graph = BabylonUGraph()
    G.add_node("a")
    G.add_node("b")
    G.add_node("c")
    return G


@pytest.fixture
def bridge_graph() -> nx.Graph:
    """Create a graph with a bridge edge connecting two cliques.

    Topology: (a-b-c triangle) -- bridge edge (c-d) -- (d-e-f triangle).
    The bridge edge {c, d} is a minimum cut of size 1.
    """
    G: nx.Graph = BabylonUGraph()
    # Left clique
    G.add_node("a")
    G.add_node("b")
    G.add_node("c")
    G.add_edge("a", "b")
    G.add_edge("b", "c")
    G.add_edge("a", "c")
    # Right clique
    G.add_node("d")
    G.add_node("e")
    G.add_node("f")
    G.add_edge("d", "e")
    G.add_edge("e", "f")
    G.add_edge("d", "f")
    # Bridge
    G.add_edge("c", "d")
    return G
