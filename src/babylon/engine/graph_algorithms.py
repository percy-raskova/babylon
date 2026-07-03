"""Backend-dispatching graph algorithms (Amendment L seam).

Analytics modules (bifurcation resilience/analysis, organizations
topology, sparrow, curvature, topology monitor) call these helpers
instead of ``nx.*`` directly. Each helper runs rustworkx-native when
handed a :class:`~babylon.engine.graph.BabylonGraph` /
:class:`~babylon.engine.graph.BabylonUGraph` and falls back to NetworkX
for legacy nx fixtures — the fallback arms are transitional and retire
with the Phase-6 fixture sweep (ADR052).

Node ids are ``str`` on the Babylon arms; the nx arms accept whatever
hashables the fixture used (test generators produce int nodes), so the
helpers are typed over ``Any`` nodes.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import rustworkx as rx

from babylon.engine.graph import BabylonGraph, BabylonUGraph

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

AnyGraph = Any
"""Transitional carrier: BabylonUGraph | BabylonGraph | nx.Graph | nx.DiGraph."""


def component_sets(graph: AnyGraph) -> list[set[Any]]:
    """Connected components as node-id sets (weak components if directed)."""
    if isinstance(graph, (BabylonGraph, BabylonUGraph)):
        return [set(component) for component in graph._component_id_sets()]
    if graph.is_directed():
        return [set(c) for c in nx.weakly_connected_components(graph)]
    return [set(c) for c in nx.connected_components(graph)]


def component_count(graph: AnyGraph) -> int:
    """Number of connected components."""
    if isinstance(graph, BabylonUGraph):
        return int(rx.number_connected_components(graph.core))
    if isinstance(graph, BabylonGraph):
        return len(rx.weakly_connected_components(graph.core))
    return int(nx.number_connected_components(graph))


def is_connected(graph: AnyGraph) -> bool:
    """True when the (undirected) graph is one component.

    Mirrors ``nx.is_connected``: callers must guard the empty graph.
    """
    if isinstance(graph, BabylonUGraph):
        return bool(rx.is_connected(graph.core))
    return bool(nx.is_connected(graph))


def articulation_point_set(graph: AnyGraph) -> set[Any]:
    """Articulation points (cut vertices) of an undirected graph."""
    if isinstance(graph, BabylonUGraph):
        return {graph.id_of(index) for index in rx.articulation_points(graph.core)}
    return set(nx.articulation_points(graph))


def density(graph: AnyGraph) -> float:
    """Edge density (rustworkx has no density function — inline formula)."""
    if isinstance(graph, (BabylonGraph, BabylonUGraph)):
        n = graph.number_of_nodes()
        m = graph.number_of_edges()
        if n < 2:
            return 0.0
        possible = n * (n - 1)
        if not isinstance(graph, BabylonGraph):
            possible //= 2
        return m / possible
    return float(nx.density(graph))


def _centrality_ids(graph: BabylonUGraph, mapping: Any) -> dict[str, float]:
    return {graph.id_of(index): float(value) for index, value in mapping.items()}


def degree_centrality(graph: AnyGraph) -> dict[Any, float]:
    """Degree centrality with NetworkX normalization (deg / (n - 1))."""
    if isinstance(graph, BabylonUGraph):
        return _centrality_ids(graph, rx.degree_centrality(graph.core))
    return dict(nx.degree_centrality(graph))


def betweenness_centrality(graph: AnyGraph) -> dict[Any, float]:
    """Normalized betweenness centrality."""
    if isinstance(graph, BabylonUGraph):
        return _centrality_ids(graph, rx.betweenness_centrality(graph.core))
    return dict(nx.betweenness_centrality(graph))


def closeness_centrality(graph: AnyGraph) -> dict[Any, float]:
    """Closeness centrality."""
    if isinstance(graph, BabylonUGraph):
        return _centrality_ids(graph, rx.closeness_centrality(graph.core))
    return dict(nx.closeness_centrality(graph))


def min_edge_cut_edges(graph: AnyGraph) -> set[tuple[Any, Any]]:
    """Global minimum edge cut of a connected undirected graph, as edges.

    The Babylon arm derives the crossing edges of the Stoer-Wagner
    partition (rustworkx returns ``(cut_value, partition)``); when
    multiple minimum cuts exist the chosen one may differ from
    NetworkX's, but its size is the edge connectivity either way.
    """
    if isinstance(graph, BabylonUGraph):
        result = rx.stoer_wagner_min_cut(graph.core)
        if result is None:
            return set()
        _cut_value, partition = result
        side = {graph.id_of(index) for index in partition}
        crossing: set[tuple[Any, Any]] = set()
        for node in sorted(side):
            for neighbor in graph.neighbors(node):
                if neighbor not in side:
                    crossing.add((node, neighbor))
        return crossing
    return set(nx.minimum_edge_cut(graph))


def shortest_path_length_between(
    graph: AnyGraph,
    u: Any,
    v: Any,
    weight_attr: str | None = None,
) -> float:
    """Shortest-path length ``u -> v``; ``inf`` when disconnected.

    ``weight_attr=None`` means hop count (unit weights). Missing weight
    attributes read as 1.0, matching ``nx.shortest_path_length``.
    """
    if u == v:
        return 0.0
    if isinstance(graph, (BabylonGraph, BabylonUGraph)):

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
    try:
        return float(nx.shortest_path_length(graph, u, v, weight=weight_attr))
    except nx.NetworkXNoPath:
        return float("inf")
