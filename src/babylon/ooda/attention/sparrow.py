"""Sparrow network analysis for attention threads (Feature 039).

Implements structural vulnerability analysis on the observed subgraph.
Named after the FBI's historical counter-intelligence analysis methods.

See Also:
    :class:`babylon.models.entities.attention_thread.SparrowAnalysis`: Result model.
    :func:`babylon.ooda.attention.observation.build_g_observed`: G_observed builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.engine import graph_algorithms as ga
from babylon.models.entities.attention_thread import SparrowAnalysis

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph import BabylonGraph, BabylonUGraph


def analyze_network(
    thread_id: str,
    tick: int,
    g_observed: BabylonGraph | nx.DiGraph[str],
    confidence: float = 0.8,
) -> SparrowAnalysis:
    """Run Sparrow structural analysis on an observed subgraph.

    Computes centrality rankings, equivalence classes, singleton
    identification, and minimal cutsets.

    Args:
        thread_id: Owning attention thread ID.
        tick: Current simulation tick.
        g_observed: Observed subgraph (from build_g_observed).
        confidence: Analysis confidence [0, 1].

    Returns:
        SparrowAnalysis with structural intelligence.
    """
    if g_observed.number_of_nodes() == 0:
        return SparrowAnalysis(
            thread_id=thread_id,
            tick=tick,
            centrality_rankings={},
            equivalence_classes=[],
            identified_singletons=frozenset(),
            known_cutsets=[],
            confidence=confidence,
        )

    # Compute centrality metrics
    undirected = g_observed.to_undirected()
    centrality_rankings: dict[str, dict[str, float]] = {}

    # Degree centrality
    degree = ga.degree_centrality(undirected)
    centrality_rankings["degree"] = degree

    # Betweenness centrality
    if undirected.number_of_nodes() > 1:
        betweenness = ga.betweenness_centrality(undirected)
        centrality_rankings["betweenness"] = betweenness

    # Closeness centrality
    if undirected.number_of_nodes() > 1 and ga.is_connected(undirected):
        closeness = ga.closeness_centrality(undirected)
        centrality_rankings["closeness"] = closeness

    # Equivalence classes via degree signature
    equivalence_classes = _compute_equivalence_classes(undirected)

    # Singleton identification (nodes with unique structural position)
    singletons = _identify_singletons(undirected, centrality_rankings)

    # Minimal cutsets (articulation points as simple approximation)
    cutsets = _compute_cutsets(undirected)

    return SparrowAnalysis(
        thread_id=thread_id,
        tick=tick,
        centrality_rankings=centrality_rankings,
        equivalence_classes=equivalence_classes,
        identified_singletons=singletons,
        known_cutsets=cutsets,
        confidence=confidence,
    )


def _compute_equivalence_classes(graph: BabylonUGraph | nx.Graph[str]) -> list[frozenset[str]]:
    """Group nodes by structural equivalence (same degree signature).

    Two nodes are structurally equivalent if they have the same
    degree and same neighbor degree distribution.

    Args:
        graph: Undirected graph to analyze.

    Returns:
        List of frozensets, each containing structurally equivalent node IDs.
    """
    signatures: dict[tuple[int, ...], list[str]] = {}

    max_nodes = 1000
    for idx, node in enumerate(graph.nodes()):
        if idx >= max_nodes:
            break
        degree = graph.degree(node)
        neighbor_degrees = sorted(graph.degree(n) for n in graph.neighbors(node))
        sig = (degree, *neighbor_degrees)
        signatures.setdefault(sig, []).append(node)

    return [frozenset(nodes) for nodes in signatures.values()]


def _identify_singletons(
    graph: BabylonUGraph | nx.Graph[str],
    centrality_rankings: dict[str, dict[str, float]],
) -> frozenset[str]:
    """Identify nodes with uniquely high structural importance.

    A singleton is a node whose betweenness centrality exceeds
    2x the mean, indicating it is a critical hub.

    Args:
        graph: Undirected graph (unused but kept for future extensions).
        centrality_rankings: Metric name -> {node_id: score} mapping.

    Returns:
        Frozenset of node IDs identified as singletons.
    """
    if graph.number_of_nodes() == 0:
        return frozenset()

    betweenness = centrality_rankings.get("betweenness", {})
    if not betweenness:
        return frozenset()

    values = list(betweenness.values())
    if not values:
        return frozenset()

    mean_bc = sum(values) / len(values)
    threshold = mean_bc * 2.0

    singletons: set[str] = set()
    max_nodes = 1000
    for idx, (node, bc) in enumerate(betweenness.items()):
        if idx >= max_nodes:
            break
        if bc > threshold:
            singletons.add(node)

    return frozenset(singletons)


def _compute_cutsets(graph: BabylonUGraph | nx.Graph[str]) -> list[frozenset[str]]:
    """Compute minimal vertex cutsets (articulation points).

    Each articulation point forms a singleton cutset -- removing it
    disconnects the graph.

    Args:
        graph: Undirected graph to analyze.

    Returns:
        List of singleton frozensets, one per articulation point.
    """
    if graph.number_of_nodes() < 2:
        return []

    # Inputs are always undirected projections (analyze_network builds
    # them via to_undirected), so no directed-graph error arm is needed.
    art_points = sorted(ga.articulation_point_set(graph))

    return [frozenset({p}) for p in art_points]


__all__ = ["analyze_network"]
