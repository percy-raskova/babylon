"""rustworkx-backed graph algorithms (Amendment L seam).

Analytics modules (bifurcation resilience/analysis, organizations
topology, sparrow, curvature, topology monitor) call these helpers
instead of graph-library functions directly. Each helper runs
rustworkx-native over :class:`~babylon.topology.graph.BabylonGraph` /
:class:`~babylon.topology.graph.BabylonUGraph`; the transitional NetworkX
fallback arms retired with the Phase-6/7 fixture sweep (ADR052).
"""

from __future__ import annotations

from typing import Any

import rustworkx as rx

from babylon.topology.graph import BabylonGraph, BabylonUGraph

__all__ = [
    "articulation_point_set",
    "betweenness_centrality",
    "closeness_centrality",
    "component_count",
    "component_sets",
    "degree_centrality",
    "density",
    "is_connected",
    "min_edge_cut_edges",
    "shortest_path_length_between",
]

AnyGraph = BabylonGraph | BabylonUGraph
"""The two graph substrates (directed world graph / undirected analytics)."""


def component_sets(graph: AnyGraph) -> list[set[str]]:
    """Connected components as node-id sets (weak components if directed)."""
    return [set(component) for component in graph._component_id_sets()]


def component_count(graph: AnyGraph) -> int:
    """Number of connected components."""
    if isinstance(graph, BabylonUGraph):
        return int(rx.number_connected_components(graph.core))
    return len(rx.weakly_connected_components(graph.core))


def is_connected(graph: BabylonUGraph) -> bool:
    """True when the (undirected) graph is one component.

    Mirrors NetworkX is_connected: callers must guard the empty graph.
    """
    return bool(rx.is_connected(graph.core))


def articulation_point_set(graph: BabylonUGraph) -> set[str]:
    """Articulation points (cut vertices) of an undirected graph."""
    return {graph.id_of(index) for index in rx.articulation_points(graph.core)}


def density(graph: AnyGraph) -> float:
    """Edge density (rustworkx has no density function — inline formula)."""
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    if n < 2:
        return 0.0
    possible = n * (n - 1)
    if not isinstance(graph, BabylonGraph):
        possible //= 2
    return m / possible


def _centrality_ids(graph: BabylonUGraph, mapping: Any) -> dict[str, float]:
    return {graph.id_of(index): float(value) for index, value in mapping.items()}


def degree_centrality(graph: BabylonUGraph) -> dict[str, float]:
    """Degree centrality with NetworkX normalization (deg / (n - 1))."""
    return _centrality_ids(graph, rx.degree_centrality(graph.core))


def betweenness_centrality(graph: BabylonUGraph) -> dict[str, float]:
    """Normalized betweenness centrality."""
    return _centrality_ids(graph, rx.betweenness_centrality(graph.core))


def closeness_centrality(graph: BabylonUGraph) -> dict[str, float]:
    """Closeness centrality."""
    return _centrality_ids(graph, rx.closeness_centrality(graph.core))


def min_edge_cut_edges(graph: BabylonUGraph) -> set[tuple[str, str]]:
    """Global minimum edge cut of a connected undirected graph, as edges.

    The Babylon arm derives the crossing edges of the Stoer-Wagner
    partition (rustworkx returns ``(cut_value, partition)``); when
    multiple minimum cuts exist the chosen one may differ from
    NetworkX's, but its size is the edge connectivity either way.
    """
    result = rx.stoer_wagner_min_cut(graph.core)
    if result is None:
        return set()
    _cut_value, partition = result
    side = {graph.id_of(index) for index in partition}
    crossing: set[tuple[str, str]] = set()
    for node in sorted(side):
        for neighbor in graph.neighbors(node):
            if neighbor not in side:
                crossing.add((node, neighbor))
    return crossing


def shortest_path_length_between(
    graph: AnyGraph,
    u: str,
    v: str,
    weight_attr: str | None = None,
) -> float:
    """Shortest-path length ``u -> v``; ``inf`` when disconnected.

    ``weight_attr=None`` means hop count (unit weights). Missing weight
    attributes read as 1.0, matching NetworkX's shortest_path_length.
    """
    if u == v:
        return 0.0

    def cost(payload: dict[str, Any]) -> float:
        if weight_attr is None:
            return 1.0
        return float(payload.get(weight_attr, 1.0))

    lengths = rx.dijkstra_shortest_path_lengths(
        graph.core, graph.index_of(u), edge_cost_fn=cost, goal=graph.index_of(v)
    )
    target_index = graph.index_of(v)
    if target_index not in lengths:
        return float("inf")
    return float(lengths[target_index])
