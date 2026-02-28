"""Topology classification and key figure identification (Feature 031, T027).

Classifies organization COMMAND subgraphs into STAR, HIERARCHY, MESH, or CELL
topologies and identifies structurally critical key figures via articulation
point analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from babylon.models.entities.organization import KeyFigure
from babylon.models.enums import EdgeType, TopologyType
from babylon.organizations.types import TopologyClassification

if TYPE_CHECKING:
    from babylon.config.defines import OrganizationDefines

# Density threshold for MESH classification
_MESH_DENSITY_THRESHOLD = 0.6


def _extract_command_subgraph(
    member_node_ids: list[str],
    G: nx.DiGraph[str],
) -> nx.Graph[str]:
    """Extract undirected projection of COMMAND edges among member nodes.

    Args:
        member_node_ids: Node IDs to include in subgraph.
        G: Full directed graph.

    Returns:
        Undirected graph of COMMAND edges among member nodes.
    """
    members = set(member_node_ids)
    undirected: nx.Graph[str] = nx.Graph()
    undirected.add_nodes_from(member_node_ids)

    for src, tgt, data in G.edges(data=True):
        if src not in members or tgt not in members:
            continue
        edge_type = data.get("edge_type")
        if isinstance(edge_type, str):
            edge_type = EdgeType(edge_type)
        if edge_type == EdgeType.COMMAND:
            undirected.add_edge(src, tgt)

    return undirected


def classify_topology(
    _org_id: str,
    member_node_ids: list[str],
    G: nx.DiGraph[str],
) -> TopologyClassification:
    """Classify an organization's COMMAND subgraph topology.

    Args:
        _org_id: Organization node ID (reserved for future logging/context).
        member_node_ids: Node IDs of key figures in this organization.
        G: Full directed graph containing COMMAND edges.

    Returns:
        TopologyClassification with type, articulation points, connectivity.
    """
    if len(member_node_ids) < 2:
        return TopologyClassification(
            topology_type=None,
            articulation_points=[],
            component_count=1 if len(member_node_ids) == 1 else 0,
            is_connected=len(member_node_ids) == 1,
        )

    subgraph = _extract_command_subgraph(member_node_ids, G)
    edge_count = subgraph.number_of_edges()

    if edge_count == 0:
        return TopologyClassification(
            topology_type=None,
            articulation_points=[],
            component_count=nx.number_connected_components(subgraph),
            is_connected=False,
        )

    n = len(member_node_ids)
    art_points = list(nx.articulation_points(subgraph))
    components = nx.number_connected_components(subgraph)
    is_connected = components == 1
    density = nx.density(subgraph)

    # Classification rules (applied in priority order):
    # 1. MESH: high edge density (> threshold), requires 3+ nodes
    #    (2-node graphs trivially have density 1.0, not meaningfully MESH)
    if n >= 3 and density > _MESH_DENSITY_THRESHOLD:
        return TopologyClassification(
            topology_type=TopologyType.MESH,
            articulation_points=art_points,
            component_count=components,
            is_connected=is_connected,
        )

    # 2. STAR: single hub with degree >= N-1 (connected to all others)
    #    Requires 3+ nodes (a 2-node dyad is a minimal HIERARCHY, not a STAR)
    if is_connected and n >= 3:
        degrees = dict(subgraph.degree())
        max_degree_node = max(degrees, key=degrees.get)  # type: ignore[arg-type]
        max_deg = degrees[max_degree_node]
        if max_deg >= n - 1:
            return TopologyClassification(
                topology_type=TopologyType.STAR,
                articulation_points=art_points,
                component_count=components,
                is_connected=is_connected,
            )

    # 3. CELL: has articulation points connecting clusters, with cycles (not a tree)
    if art_points and is_connected and edge_count > n - 1:
        return TopologyClassification(
            topology_type=TopologyType.CELL,
            articulation_points=art_points,
            component_count=components,
            is_connected=is_connected,
        )

    # 4. HIERARCHY: tree structure (N-1 edges, connected, acyclic)
    if is_connected and edge_count == n - 1:
        return TopologyClassification(
            topology_type=TopologyType.HIERARCHY,
            articulation_points=art_points,
            component_count=components,
            is_connected=is_connected,
        )

    # Fallback: connected but doesn't match any clear pattern
    # Treat sparse connected graphs as HIERARCHY
    if is_connected:
        return TopologyClassification(
            topology_type=TopologyType.HIERARCHY,
            articulation_points=art_points,
            component_count=components,
            is_connected=is_connected,
        )

    # Disconnected graph
    return TopologyClassification(
        topology_type=None,
        articulation_points=art_points,
        component_count=components,
        is_connected=False,
    )


def identify_key_figures(
    org_id: str,
    member_node_ids: list[str],
    G: nx.DiGraph[str],
) -> list[KeyFigure]:
    """Identify structurally critical key figures via articulation point analysis.

    Args:
        org_id: Organization node ID.
        member_node_ids: Node IDs of key figures in this organization.
        G: Full directed graph containing COMMAND edges.

    Returns:
        List of KeyFigure entities for each articulation point.
    """
    if len(member_node_ids) < 2:
        return []

    subgraph = _extract_command_subgraph(member_node_ids, G)
    if subgraph.number_of_edges() == 0:
        return []

    art_points = list(nx.articulation_points(subgraph))
    n = len(member_node_ids)
    key_figures: list[KeyFigure] = []

    for ap_id in art_points:
        # Compute structural importance: (components_after_removal - 1) / (n - 1)
        # Normalized to [0, 1] where 1.0 = maximum fragmentation
        test_graph: nx.Graph[str] = subgraph.copy()
        test_graph.remove_node(ap_id)
        components_after = nx.number_connected_components(test_graph)
        importance = min((components_after - 1) / (n - 1), 1.0) if n > 1 else 0.0

        # Check for structural equivalents (same degree, same neighbors)
        ap_neighbors = set(subgraph.neighbors(ap_id))
        ap_degree = subgraph.degree(ap_id)
        has_equivalent = False
        for other_id in member_node_ids:
            if other_id == ap_id:
                continue
            if subgraph.degree(other_id) == ap_degree:
                other_neighbors = set(subgraph.neighbors(other_id))
                # Same neighborhood structure (excluding each other)
                if ap_neighbors - {other_id} == other_neighbors - {ap_id}:
                    has_equivalent = True
                    break

        node_data = G.nodes.get(ap_id, {})
        kf = KeyFigure(
            id=ap_id,
            name=node_data.get("name", ap_id),
            organization_id=org_id,
            role=node_data.get("role", "key_figure"),
            structural_importance=importance,
            is_singleton=not has_equivalent,
        )
        key_figures.append(kf)

    return key_figures


def cohesion_loss_on_removal(
    current_cohesion: float,
    removed_count: int,
    defines: OrganizationDefines,
) -> float:
    """Compute new cohesion after removing key figures.

    Args:
        current_cohesion: Current organization cohesion [0, 1].
        removed_count: Number of key figures removed.
        defines: OrganizationDefines with cohesion_loss_per_key_figure and min_cohesion_threshold.

    Returns:
        New cohesion value, floored at min_cohesion_threshold.
    """
    loss = removed_count * defines.cohesion_loss_per_key_figure
    new_cohesion = current_cohesion - loss
    return max(new_cohesion, defines.min_cohesion_threshold)
