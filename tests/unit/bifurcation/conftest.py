"""Test fixtures for bifurcation topology analysis (Feature 033).

Provides graph builders, hypergraph builders, community states, and
BifurcationDefines fixtures for testing consciousness-weighted solidarity
analysis.
"""

from __future__ import annotations

from collections import defaultdict

import networkx as nx
import pytest
import xgi

from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import (
    CommunityConsciousness,
    CommunityState,
)
from babylon.models.enums import (
    CommunityType,
    ConsciousnessTendency,
    EdgeType,
)
from babylon.models.types import Probability

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


def make_community_state(
    community_type: CommunityType,
    ci: float = 0.3,
    tendency: ConsciousnessTendency = ConsciousnessTendency.LIBERAL,
    infrastructure: float = 0.3,
    cohesion: float = 0.5,
) -> CommunityState:
    """Create a CommunityState with specified consciousness level.

    Args:
        community_type: Which community.
        ci: Collective identity [0, 1].
        tendency: Dominant ideological tendency.
        infrastructure: Organizational capacity [0, 1].
        cohesion: Internal trust [0, 1].

    Returns:
        Frozen CommunityState with given parameters.
    """
    return CommunityState(
        community_type=community_type,
        consciousness=CommunityConsciousness(
            collective_identity=Probability(ci),
            dominant_tendency=tendency,
        ),
        infrastructure=Probability(infrastructure),
        cohesion=Probability(cohesion),
    )


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
# Graph Builders
# =============================================================================


def build_star_graph(
    num_spokes: int = 5,
    edge_type: EdgeType = EdgeType.SOLIDARITY,
    strength: float = 0.8,
) -> nx.DiGraph:
    """Build a star topology (fragile — hub is single point of failure).

    Args:
        num_spokes: Number of leaf nodes.
        edge_type: Edge type for connections.
        strength: solidarity_strength value.

    Returns:
        DiGraph with hub C_HUB connected to C000..C00N.
    """
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("C_HUB", _node_type="social_class", wealth=50.0)
    for i in range(num_spokes):
        node_id = f"C{i:03d}"
        G.add_node(node_id, _node_type="social_class", wealth=20.0)
        G.add_edge("C_HUB", node_id, edge_type=edge_type, solidarity_strength=strength)
    return G


def build_mesh_graph(
    num_nodes: int = 5,
    edge_type: EdgeType = EdgeType.SOLIDARITY,
    strength: float = 0.8,
) -> nx.DiGraph:
    """Build a fully-connected mesh topology (resilient).

    Args:
        num_nodes: Number of nodes.
        edge_type: Edge type for connections.
        strength: solidarity_strength value.

    Returns:
        DiGraph with all-to-all SOLIDARITY connections.
    """
    G: nx.DiGraph = nx.DiGraph()
    node_ids = [f"C{i:03d}" for i in range(num_nodes)]
    for node_id in node_ids:
        G.add_node(node_id, _node_type="social_class", wealth=30.0)
    for i, src in enumerate(node_ids):
        for tgt in node_ids[i + 1 :]:
            G.add_edge(src, tgt, edge_type=edge_type, solidarity_strength=strength)
    return G


def build_disconnected_graph(
    component_sizes: list[int] | None = None,
) -> nx.DiGraph:
    """Build a graph with disconnected components.

    Args:
        component_sizes: List of sizes for each component.
            Default: [3, 2, 1] (3 components).

    Returns:
        DiGraph with disconnected solidarity components.
    """
    if component_sizes is None:
        component_sizes = [3, 2, 1]
    G: nx.DiGraph = nx.DiGraph()
    node_counter = 0
    for comp_size in component_sizes:
        comp_nodes = []
        for _ in range(comp_size):
            node_id = f"C{node_counter:03d}"
            G.add_node(node_id, _node_type="social_class", wealth=25.0)
            comp_nodes.append(node_id)
            node_counter += 1
        # Connect nodes within component
        for i in range(len(comp_nodes) - 1):
            G.add_edge(
                comp_nodes[i],
                comp_nodes[i + 1],
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.8,
            )
    return G


# =============================================================================
# Hypergraph Builders
# =============================================================================


def build_test_hypergraph(
    agent_memberships: dict[str, set[CommunityType]],
    community_states: dict[CommunityType, CommunityState],
) -> xgi.Hypergraph:
    """Build XGI hypergraph from agent memberships and community states.

    Mirrors the structure of ``build_community_hypergraph()`` from
    CommunitySystem but works from test data directly.

    Args:
        agent_memberships: Agent ID to set of CommunityType memberships.
        community_states: Community type to state mapping.

    Returns:
        XGI Hypergraph with communities as hyperedges.
    """
    H: xgi.Hypergraph = xgi.Hypergraph()

    # Collect members per community
    community_members: dict[CommunityType, list[str]] = defaultdict(list)
    for agent_id, communities in agent_memberships.items():
        if agent_id not in H.nodes:
            H.add_node(agent_id)
        for comm in communities:
            community_members[comm].append(agent_id)

    # Create hyperedges
    for comm_type, members in community_members.items():
        if not members:
            continue
        state = community_states.get(
            comm_type,
            CommunityState(community_type=comm_type),
        )
        H.add_edge(
            members,
            idx=comm_type.value,
            category=state.category.value,
            consciousness_ci=float(state.consciousness.collective_identity),
            infrastructure=float(state.infrastructure),
        )

    return H


def collect_agent_memberships(
    graph: nx.DiGraph,
) -> dict[str, set[CommunityType]]:
    """Extract agent community memberships from graph node attributes.

    Args:
        graph: Simulation graph with community_memberships on social_class nodes.

    Returns:
        Agent ID to set of CommunityType memberships.
    """
    memberships: dict[str, set[CommunityType]] = {}
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") != "social_class":
            continue
        raw = data.get("community_memberships", [])
        if isinstance(raw, set):
            memberships[node_id] = raw
        elif isinstance(raw, list):
            memberships[node_id] = {CommunityType(c) if isinstance(c, str) else c for c in raw}
        else:
            memberships[node_id] = set()
    return memberships


def assign_communities_to_graph(
    graph: nx.DiGraph,
    agent_memberships: dict[str, set[CommunityType]],
) -> None:
    """Set community_memberships attribute on graph nodes.

    Args:
        graph: Simulation graph to modify.
        agent_memberships: Agent ID to community set.
    """
    for node_id, communities in agent_memberships.items():
        if node_id in graph.nodes:
            graph.nodes[node_id]["community_memberships"] = communities
