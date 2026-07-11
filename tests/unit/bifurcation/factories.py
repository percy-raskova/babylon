from __future__ import annotations

from collections import defaultdict

import networkx as nx
import xgi

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
from babylon.topology.graph import BabylonGraph


def make_community_state(
    community_type: CommunityType,
    ci: float = 0.3,
    tendency: ConsciousnessTendency = ConsciousnessTendency.LIBERAL,
    infrastructure: float = 0.3,
    cohesion: float = 0.5,
) -> CommunityState:
    """Create a CommunityState with specified consciousness level."""
    return CommunityState(
        community_type=community_type,
        consciousness=CommunityConsciousness(
            collective_identity=Probability(ci),
            dominant_tendency=tendency,
        ),
        infrastructure=Probability(infrastructure),
        cohesion=Probability(cohesion),
    )


def build_star_graph(
    num_spokes: int = 5,
    edge_type: EdgeType = EdgeType.SOLIDARITY,
    strength: float = 0.8,
) -> nx.DiGraph:
    """Build a star topology."""
    G: nx.DiGraph = BabylonGraph()
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
    """Build a fully-connected mesh topology."""
    G: nx.DiGraph = BabylonGraph()
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
    """Build a graph with disconnected components."""
    if component_sizes is None:
        component_sizes = [3, 2, 1]
    G: nx.DiGraph = BabylonGraph()
    node_counter = 0
    for comp_size in component_sizes:
        comp_nodes = []
        for _ in range(comp_size):
            node_id = f"C{node_counter:03d}"
            G.add_node(node_id, _node_type="social_class", wealth=25.0)
            comp_nodes.append(node_id)
            node_counter += 1
        for i in range(len(comp_nodes) - 1):
            G.add_edge(
                comp_nodes[i],
                comp_nodes[i + 1],
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.8,
            )
    return G


def build_test_hypergraph(
    agent_memberships: dict[str, set[CommunityType]],
    community_states: dict[CommunityType, CommunityState],
) -> xgi.Hypergraph:
    """Build XGI hypergraph from agent memberships and community states."""
    H: xgi.Hypergraph = xgi.Hypergraph()
    community_members: dict[CommunityType, list[str]] = defaultdict(list)
    for agent_id, communities in agent_memberships.items():
        if agent_id not in H.nodes:
            H.add_node(agent_id)
        for comm in communities:
            community_members[comm].append(agent_id)

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
    """Extract agent community memberships from graph node attributes."""
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
    """Set community_memberships attribute on graph nodes."""
    for node_id, communities in agent_memberships.items():
        if node_id in graph.nodes:
            graph.nodes[node_id]["community_memberships"] = communities


def build_ceiling_test_graph(
    wealth_a: float = 50.0,
    wealth_b: float = 50.0,
    shared_exploiter: bool = False,
    node_a_id: str = "worker_a",
    node_b_id: str = "worker_b",
) -> nx.DiGraph:
    """Build a minimal graph for solidarity ceiling tests."""
    graph: nx.DiGraph = BabylonGraph()
    graph.add_node(node_a_id, _node_type="social_class", wealth=wealth_a)
    graph.add_node(node_b_id, _node_type="social_class", wealth=wealth_b)

    if shared_exploiter:
        exploiter_id = "bourgeois_exploiter"
        graph.add_node(exploiter_id, _node_type="social_class", wealth=500.0)
        graph.add_edge(
            exploiter_id,
            node_a_id,
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.0,
        )
        graph.add_edge(
            exploiter_id,
            node_b_id,
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.0,
        )
    return graph
