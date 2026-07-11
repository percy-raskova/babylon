"""Material solidarity ceiling computation (US6 -- Feature 033).

Computes the maximum possible solidarity between two agents based on
material conditions: wage gap ratio, shared exploitation sources,
shared community memberships, and geographic proximity.

The core insight from MLM-TW theory: solidarity between classes with
qualitatively different material conditions (e.g., 10x wage gap) is
structurally limited regardless of subjective intent. Shared oppression
(common exploiter, marginalized community) can raise this ceiling.

See Also:
    :class:`babylon.bifurcation.types.SolidarityCeiling`: Result type.
    :class:`babylon.config.defines.BifurcationDefines`: Tunable coefficients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.bifurcation.types import SolidarityCeiling
from babylon.config.defines import BifurcationDefines
from babylon.models.enums import CommunityType, EdgeType

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph

# Bonus per shared marginalized community membership
_COMMUNITY_BONUS_PER_SHARED: float = 0.05

# Division guard for wealth ratio (prevents divide-by-zero)
_WEALTH_EPSILON: float = 0.001


def compute_solidarity_ceiling(
    node_a_id: str,
    node_b_id: str,
    graph: BabylonGraph,
    agent_memberships: dict[str, set[CommunityType]],
    defines: BifurcationDefines,
) -> SolidarityCeiling:
    """Compute material solidarity ceiling between two agents.

    The ceiling represents the maximum solidarity strength achievable
    given material conditions. Actual solidarity may be lower, but
    cannot exceed this ceiling.

    Args:
        node_a_id: Graph node ID of first agent.
        node_b_id: Graph node ID of second agent.
        graph: Simulation graph with wealth attributes and edge types.
        agent_memberships: Agent ID to set of CommunityType memberships.
        defines: Bifurcation coefficient configuration.

    Returns:
        Frozen SolidarityCeiling with all computed components.
    """
    # Step 1: Get wealth for both nodes
    wealth_a: float = graph.nodes[node_a_id].get("wealth", 0.0)
    wealth_b: float = graph.nodes[node_b_id].get("wealth", 0.0)

    # Step 2: Compute wage gap ratio (guarded against division by zero)
    max_wealth = max(wealth_a, wealth_b)
    min_wealth = max(min(wealth_a, wealth_b), _WEALTH_EPSILON)
    wage_gap_ratio = max_wealth / min_wealth

    # Step 3: Base ceiling via linear interpolation
    base_ceiling = _interpolate_base_ceiling(wage_gap_ratio, defines)

    # Step 4: Exploitation bonus (shared exploiter)
    exploitation_bonus = _compute_exploitation_bonus(node_a_id, node_b_id, graph, defines)

    # Step 5: Community bonus (shared marginalized memberships)
    community_bonus = _compute_community_bonus(node_a_id, node_b_id, agent_memberships)

    # Step 6: Geographic proximity
    geographically_proximate = _check_geographic_proximity(node_a_id, node_b_id, graph)

    # Step 7: Effective ceiling clamped to [0, 1]
    effective_ceiling = min(1.0, max(0.0, base_ceiling + exploitation_bonus + community_bonus))

    return SolidarityCeiling(
        base_ceiling=base_ceiling,
        exploitation_bonus=exploitation_bonus,
        community_bonus=community_bonus,
        effective_ceiling=effective_ceiling,
        wage_gap_ratio=wage_gap_ratio,
        geographically_proximate=geographically_proximate,
    )


def _interpolate_base_ceiling(
    wage_gap_ratio: float,
    defines: BifurcationDefines,
) -> float:
    """Linear interpolation of base ceiling from wage gap ratio.

    Args:
        wage_gap_ratio: max(w_a, w_b) / max(min(w_a, w_b), epsilon).
        defines: Coefficients for threshold and ceiling bounds.

    Returns:
        Base ceiling in [wage_ceiling_min, wage_ceiling_max].
    """
    low_ratio = defines.wage_ceiling_low_ratio
    high_ratio = defines.wage_ceiling_high_ratio
    ceiling_min = defines.wage_ceiling_min
    ceiling_max = defines.wage_ceiling_max

    if wage_gap_ratio >= high_ratio:
        return ceiling_min
    if wage_gap_ratio <= low_ratio:
        return ceiling_max

    # Linear interpolation: as ratio goes from low to high,
    # ceiling goes from max to min
    t = (wage_gap_ratio - low_ratio) / (high_ratio - low_ratio)
    return ceiling_max - t * (ceiling_max - ceiling_min)


def _compute_exploitation_bonus(
    node_a_id: str,
    node_b_id: str,
    graph: BabylonGraph,
    defines: BifurcationDefines,
) -> float:
    """Check if both nodes share an exploitation source.

    Two agents exploited by the SAME capitalist have a material basis
    for solidarity: they share a common enemy.

    Args:
        node_a_id: First agent node ID.
        node_b_id: Second agent node ID.
        graph: Simulation graph with EXPLOITATION edges.
        defines: Contains shared_exploitation_bonus value.

    Returns:
        shared_exploitation_bonus if shared source found, else 0.0.
    """
    exploiters_a = _get_exploitation_predecessors(node_a_id, graph)
    exploiters_b = _get_exploitation_predecessors(node_b_id, graph)

    shared_exploiters = exploiters_a & exploiters_b
    if shared_exploiters:
        return defines.shared_exploitation_bonus
    return 0.0


def _get_exploitation_predecessors(
    node_id: str,
    graph: BabylonGraph,
) -> set[str]:
    """Get set of nodes that have EXPLOITATION edges pointing to this node.

    Args:
        node_id: Target node ID.
        graph: Simulation graph.

    Returns:
        Set of predecessor node IDs with EXPLOITATION edge_type.
    """
    predecessors: set[str] = set()
    for pred in graph.predecessors(node_id):
        edge_data = graph.edges[pred, node_id]
        edge_type_raw = edge_data.get("edge_type", "")
        if isinstance(edge_type_raw, EdgeType):
            if edge_type_raw == EdgeType.EXPLOITATION:
                predecessors.add(pred)
        elif str(edge_type_raw) == EdgeType.EXPLOITATION.value:
            predecessors.add(pred)
    return predecessors


def _compute_community_bonus(
    node_a_id: str,
    node_b_id: str,
    agent_memberships: dict[str, set[CommunityType]],
) -> float:
    """Compute bonus from shared marginalized community memberships.

    Each shared community type adds a small solidarity bonus,
    reflecting the material basis of shared oppression.

    Args:
        node_a_id: First agent node ID.
        node_b_id: Second agent node ID.
        agent_memberships: Mapping of agent IDs to community memberships.

    Returns:
        Bonus = 0.05 * number_of_shared_communities.
    """
    communities_a = agent_memberships.get(node_a_id, set())
    communities_b = agent_memberships.get(node_b_id, set())
    shared_count = len(communities_a & communities_b)
    return _COMMUNITY_BONUS_PER_SHARED * shared_count


def _check_geographic_proximity(
    node_a_id: str,
    node_b_id: str,
    graph: BabylonGraph,
) -> bool:
    """Check if agents share ADJACENCY-linked territories.

    Two agents are geographically proximate if they have TENANCY edges
    to territories that are connected by ADJACENCY edges.

    Args:
        node_a_id: First agent node ID.
        node_b_id: Second agent node ID.
        graph: Simulation graph with TENANCY and ADJACENCY edges.

    Returns:
        True if agents share adjacency-linked territories.
    """
    territories_a = _get_tenancy_targets(node_a_id, graph)
    territories_b = _get_tenancy_targets(node_b_id, graph)

    # Check if any territory of A is adjacent to any territory of B
    for terr_a in territories_a:
        for terr_b in territories_b:
            if terr_a == terr_b:
                return True
            # Check ADJACENCY in either direction
            if graph.has_edge(terr_a, terr_b):
                edge_data = graph.edges[terr_a, terr_b]
                edge_type_raw = edge_data.get("edge_type", "")
                if _is_adjacency_edge(edge_type_raw):
                    return True
            if graph.has_edge(terr_b, terr_a):
                edge_data = graph.edges[terr_b, terr_a]
                edge_type_raw = edge_data.get("edge_type", "")
                if _is_adjacency_edge(edge_type_raw):
                    return True
    return False


def _get_tenancy_targets(
    node_id: str,
    graph: BabylonGraph,
) -> set[str]:
    """Get territory nodes this agent has TENANCY edges to.

    Args:
        node_id: Agent node ID.
        graph: Simulation graph.

    Returns:
        Set of territory node IDs connected by TENANCY edges.
    """
    territories: set[str] = set()
    for successor in graph.successors(node_id):
        edge_data = graph.edges[node_id, successor]
        edge_type_raw = edge_data.get("edge_type", "")
        if isinstance(edge_type_raw, EdgeType):
            if edge_type_raw == EdgeType.TENANCY:
                territories.add(successor)
        elif str(edge_type_raw) == EdgeType.TENANCY.value:
            territories.add(successor)
    return territories


def _is_adjacency_edge(edge_type_raw: object) -> bool:
    """Check if an edge type value represents ADJACENCY.

    Args:
        edge_type_raw: Edge type from graph edge data (may be str or EdgeType).

    Returns:
        True if the edge is an ADJACENCY edge.
    """
    if isinstance(edge_type_raw, EdgeType):
        return edge_type_raw == EdgeType.ADJACENCY
    return str(edge_type_raw) == EdgeType.ADJACENCY.value
