"""Community hypergraph system (Feature 022).

Manages the XGI hypergraph layer for n-ary community membership.
Provides builder, query, and overlap matrix operations used by
the CommunitySystem tick handler.

See Also:
    :mod:`babylon.models.entities.community`: Data models.
    :mod:`babylon.formulas.community`: Community formulas.
    Constitution II.7: Edges vs Hyperedges (NetworkX + XGI).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import networkx as nx
import xgi  # type: ignore[import-untyped,import-not-found,unused-ignore]

from babylon.models.entities.community import (
    LEGAL_STATUS_MULTIPLIERS,
    ROLE_STRENGTH_WEIGHTS,
    CommunityMembership,
    CommunityState,
)
from babylon.models.enums import CommunityType

logger = logging.getLogger(__name__)


def build_community_hypergraph(
    memberships: list[CommunityMembership],
    community_states: dict[CommunityType, CommunityState],
) -> xgi.Hypergraph:
    """Build XGI hypergraph where communities are hyperedges.

    Each community with at least one member becomes a hyperedge connecting
    all its member agent IDs. Community state attributes are stored as
    hyperedge attributes.

    Args:
        memberships: All community memberships across all agents.
        community_states: State dict keyed by community type.

    Returns:
        XGI Hypergraph with agents as nodes and communities as hyperedges.
    """
    H = xgi.Hypergraph()

    # Collect members per community
    community_members: dict[CommunityType, list[str]] = defaultdict(list)
    for membership in memberships:
        community_members[membership.community_type].append(membership.agent_id)
        # Ensure agent node exists
        if membership.agent_id not in H.nodes:
            H.add_node(membership.agent_id)

    # Communities become hyperedges with state attributes
    for comm_type, members in community_members.items():
        if len(members) == 0:
            continue
        state = community_states.get(
            comm_type,
            CommunityState(community_type=comm_type),
        )
        # Use idx= (not id=) per XGI 0.10 API
        H.add_edge(
            members,
            idx=comm_type.value,
            heat=float(state.heat),
            cohesion=float(state.cohesion),
            infrastructure=float(state.infrastructure),
            visibility=float(state.visibility),
            legal_status=state.legal_status.value,
            reproduction_cost_modifier=state.reproduction_cost_modifier,
            rent_access_modifier=float(state.rent_access_modifier),
        )

    return H


def shared_communities(
    H: xgi.Hypergraph,
    agent_a: str,
    agent_b: str,
) -> set[Any]:
    """Return community IDs (hyperedge IDs) shared by both agents.

    Args:
        H: Community hypergraph.
        agent_a: First agent ID.
        agent_b: Second agent ID.

    Returns:
        Set of community type value strings shared by both agents.
    """
    if agent_a not in H.nodes or agent_b not in H.nodes:
        return set()
    memberships_a: set[Any] = H.nodes.memberships(agent_a)
    memberships_b: set[Any] = H.nodes.memberships(agent_b)
    return memberships_a & memberships_b


def community_overlap_matrix(
    H: xgi.Hypergraph,
) -> tuple[Any, dict[str, int]]:
    """Compute pairwise community overlap matrix for all agents.

    O[i,j] = number of communities containing both agent_i and agent_j.
    O[i,i] = degree of agent_i (number of communities they belong to).

    Args:
        H: Community hypergraph.

    Returns:
        Tuple of (overlap_matrix as dense ndarray, node_index mapping
        agent_id → matrix row/column index).
    """
    I_matrix, rowdict, _coldict = xgi.incidence_matrix(
        H,
        sparse=False,
        index=True,
    )
    # rowdict maps matrix_row_index → node_id
    # Invert to node_id → matrix_row_index
    node_index: dict[str, int] = {node_id: row_idx for row_idx, node_id in rowdict.items()}
    # O = I @ I^T: (n_nodes x n_nodes) co-membership count matrix
    overlap = I_matrix @ I_matrix.T
    return overlap, node_index


def legal_status_escalate(state: CommunityState) -> CommunityState:
    """Escalate legal status by one step (one-way ratchet).

    Args:
        state: Current community state.

    Returns:
        New CommunityState with legal_status advanced one step.
        Returns unchanged if already at CRIMINALIZED.
    """
    from babylon.models.entities.community import LEGAL_STATUS_ORDER

    current_idx = LEGAL_STATUS_ORDER.index(state.legal_status)
    max_idx = len(LEGAL_STATUS_ORDER) - 1
    if current_idx >= max_idx:
        return state
    new_status = LEGAL_STATUS_ORDER[current_idx + 1]
    return state.model_copy(update={"legal_status": new_status})


def designate_community(
    state: CommunityState,
    heat_increase: float = 0.3,
) -> CommunityState:
    """State designates community — escalates legal status and raises heat.

    Args:
        state: Current community state.
        heat_increase: Amount to add to heat.

    Returns:
        New CommunityState with escalated legal status and increased heat.
    """
    escalated = legal_status_escalate(state)
    new_heat = min(1.0, float(escalated.heat) + heat_increase)
    return escalated.model_copy(update={"heat": new_heat})


def infiltrate_community(
    state: CommunityState,
    cohesion_reduction: float = 0.2,
) -> CommunityState:
    """State infiltrates community — reduces cohesion.

    Args:
        state: Current community state.
        cohesion_reduction: Amount to subtract from cohesion.

    Returns:
        New CommunityState with reduced cohesion.
    """
    new_cohesion = max(0.0, float(state.cohesion) - cohesion_reduction)
    return state.model_copy(update={"cohesion": new_cohesion})


def disrupt_infrastructure(
    state: CommunityState,
    infrastructure_reduction: float = 0.4,
) -> CommunityState:
    """State disrupts community infrastructure.

    Args:
        state: Current community state.
        infrastructure_reduction: Amount to subtract from infrastructure.

    Returns:
        New CommunityState with reduced infrastructure.
    """
    new_infra = max(0.0, float(state.infrastructure) - infrastructure_reduction)
    return state.model_copy(update={"infrastructure": new_infra})


def _extract_memberships_from_node(node_data: dict[str, Any]) -> list[CommunityMembership]:
    """Extract CommunityMembership objects from a graph node's attributes."""
    raw = node_data.get("community_memberships", [])
    if not raw:
        return []
    result: list[CommunityMembership] = []
    for item in raw:
        if isinstance(item, CommunityMembership):
            result.append(item)
        elif isinstance(item, dict):
            result.append(CommunityMembership(**item))
    return result


def _get_community_states_from_services(
    services: Any,
) -> dict[CommunityType, CommunityState]:
    """Extract community_states from the services container."""
    hypergraph_config = services.community_hypergraph
    if hypergraph_config is None:
        return {}
    if isinstance(hypergraph_config, dict):
        result: dict[CommunityType, CommunityState] = hypergraph_config.get("community_states", {})
        return result
    return {}


class CommunitySystem:
    """Hypergraph community system (Feature 022).

    Manages alpha-smoothed community state decay, solidarity potential
    computation from community overlap, threat score aggregation, and
    reproduction cost modification. Runs before SolidaritySystem in the
    engine pipeline (position 6).
    """

    name = "community"

    def step(
        self,
        graph: nx.DiGraph[str] | Any,
        services: Any,
        _context: Any,
    ) -> None:
        """Execute community system for one tick."""
        # Auto-wrap guard
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        community_states = _get_community_states_from_services(services)
        if not community_states:
            return

        all_memberships, agent_memberships = _collect_memberships(graph)
        if not all_memberships:
            return

        hypergraph = build_community_hypergraph(all_memberships, community_states)

        _amplify_solidarity_edges(
            graph,
            hypergraph,
            agent_memberships,
            community_states,
            services,
        )
        _compute_threat_scores(
            graph,
            agent_memberships,
            community_states,
            services,
        )
        _compute_cost_modifiers(
            graph,
            agent_memberships,
            community_states,
        )


def _collect_memberships(
    graph: Any,
) -> tuple[list[CommunityMembership], dict[str, list[CommunityMembership]]]:
    """Collect all community memberships from active graph nodes."""
    all_memberships: list[CommunityMembership] = []
    agent_memberships: dict[str, list[CommunityMembership]] = {}

    for node in graph.query_nodes(node_type="social_class"):
        if not node.attributes.get("active", True):
            continue
        memberships = _extract_memberships_from_node(node.attributes)
        agent_memberships[node.id] = memberships
        all_memberships.extend(memberships)

    return all_memberships, agent_memberships


def _build_shared_data(
    comm_ids: set[Any],
    src_memberships: list[CommunityMembership],
    tgt_memberships: list[CommunityMembership],
    community_states: dict[CommunityType, CommunityState],
) -> list[tuple[float, float, float, float]]:
    """Build (infrastructure, cohesion, strength_a, strength_b) tuples for shared communities."""
    shared_data: list[tuple[float, float, float, float]] = []
    for comm_id in comm_ids:
        comm_type = CommunityType(comm_id)
        state = community_states.get(comm_type)
        if state is None:
            continue
        str_a = next(
            (float(m.strength) for m in src_memberships if m.community_type == comm_type),
            0.0,
        )
        str_b = next(
            (float(m.strength) for m in tgt_memberships if m.community_type == comm_type),
            0.0,
        )
        shared_data.append((float(state.infrastructure), float(state.cohesion), str_a, str_b))
    return shared_data


def _amplify_solidarity_edges(
    graph: Any,
    hypergraph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
    services: Any,
) -> None:
    """Amplify solidarity_strength on SOLIDARITY edges via community overlap."""
    from babylon.models.enums import EdgeType

    calculate_amplification = services.formulas.get("solidarity_amplification")

    for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
        src_mem = agent_memberships.get(edge.source_id, [])
        tgt_mem = agent_memberships.get(edge.target_id, [])
        if not src_mem or not tgt_mem:
            continue

        shared = shared_communities(hypergraph, edge.source_id, edge.target_id)
        if not shared:
            continue

        shared_data = _build_shared_data(shared, src_mem, tgt_mem, community_states)
        base_strength = edge.attributes.get("solidarity_strength", 0.0)
        amplified = calculate_amplification(
            base_strength=base_strength,
            shared_communities=shared_data,
        )
        graph.update_edge(
            edge.source_id,
            edge.target_id,
            EdgeType.SOLIDARITY,
            solidarity_strength=amplified,
        )


def _compute_threat_scores(
    graph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
    services: Any,
) -> None:
    """Compute per-agent threat scores and write to graph nodes."""
    calculate_threat = services.formulas.get("threat_score")

    for node_id, memberships in agent_memberships.items():
        if not memberships:
            graph.update_node(node_id, threat_score=0.0)
            continue

        threat_tuples: list[tuple[float, float, float, float]] = []
        for mem in memberships:
            comm_state = community_states.get(mem.community_type)
            if comm_state is None:
                continue
            threat_tuples.append(
                (
                    float(comm_state.heat),
                    mem.effective_visibility,
                    ROLE_STRENGTH_WEIGHTS.get(mem.role, 0.4),
                    LEGAL_STATUS_MULTIPLIERS.get(comm_state.legal_status, 0.1),
                )
            )

        score = calculate_threat(memberships=threat_tuples)
        graph.update_node(node_id, threat_score=score)


def _compute_cost_modifiers(
    graph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
) -> None:
    """Compute per-agent reproduction cost modifiers and write to graph nodes."""
    from babylon.formulas.community import compute_community_cost_modifier

    for node_id, memberships in agent_memberships.items():
        modifier = compute_community_cost_modifier(memberships, community_states)
        graph.update_node(node_id, community_cost_modifier=modifier)
