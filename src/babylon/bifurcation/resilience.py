"""Topological resilience metrics for solidarity subgraph analysis (US4).

Provides five core functions for measuring the structural resilience of
an undirected solidarity subgraph:

1. **Betti numbers**: Connected components (beta_0) and cycle rank (beta_1)
2. **Equivalence classes**: Structural role grouping by neighbor sets
3. **Critical singletons**: Articulation points whose removal disconnects
4. **Critical cutsets**: Minimum edge cuts bounded by configurable size
5. **Purge resilience**: Targeted removal of high-degree nodes

All functions operate on ``nx.Graph`` (undirected), which is the output
of :func:`babylon.engine.topology_monitor.extract_solidarity_subgraph`.

See Also:
    :mod:`babylon.engine.topology_monitor`: Solidarity subgraph extraction
    :mod:`babylon.models.topology_metrics`: Snapshot data models
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from babylon.engine.graph_algorithms import (
    articulation_point_set,
    component_count,
    component_sets,
    min_edge_cut_edges,
)

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph import BabylonUGraph


def compute_betti_numbers(subgraph: BabylonUGraph | nx.Graph[str]) -> tuple[int, int]:
    """Compute Betti numbers for an undirected graph.

    Args:
        subgraph: Undirected solidarity subgraph to analyze.

    Returns:
        Tuple of (beta_0, beta_1) where:
        - beta_0: Number of connected components
        - beta_1: Cycle rank = |E| - |V| + beta_0

    Example:
        >>> import networkx as nx
        >>> G = nx.cycle_graph(4)
        >>> compute_betti_numbers(G)
        (1, 1)
    """
    num_nodes: int = subgraph.number_of_nodes()
    num_edges: int = subgraph.number_of_edges()

    if num_nodes == 0:
        return (0, 0)

    beta_0: int = component_count(subgraph)
    beta_1: int = num_edges - num_nodes + beta_0

    return (beta_0, beta_1)


def compute_equivalence_classes(subgraph: BabylonUGraph | nx.Graph[str]) -> dict[int, int]:
    """Group nodes by structural equivalence (identical neighbor sets).

    Two nodes are structurally equivalent if they have the exact same
    set of neighbors (as a frozenset). Nodes are grouped by this key,
    and the result maps class_size to count of classes with that size.

    Args:
        subgraph: Undirected solidarity subgraph to analyze.

    Returns:
        Dictionary mapping class_size -> count. For example, {5: 1}
        means one equivalence class containing 5 nodes.

    Example:
        >>> import networkx as nx
        >>> G = nx.complete_graph(3)
        >>> compute_equivalence_classes(G)
        {3: 1}
    """
    if subgraph.number_of_nodes() == 0:
        return {}

    # Group nodes by their neighbor sets
    neighbor_groups: dict[frozenset[str], list[str]] = {}
    for node in subgraph.nodes():
        neighbors: frozenset[str] = frozenset(subgraph.neighbors(node))
        if neighbors not in neighbor_groups:
            neighbor_groups[neighbors] = []
        neighbor_groups[neighbors].append(str(node))

    # Convert to size -> count mapping
    sizes: list[int] = [len(group) for group in neighbor_groups.values()]
    size_counts: Counter[int] = Counter(sizes)

    return dict(size_counts)


def find_critical_singletons(subgraph: BabylonUGraph | nx.Graph[str]) -> list[str]:
    """Find articulation points whose removal disconnects the graph.

    Wraps :func:`networkx.articulation_points` and returns a sorted
    list for deterministic output.

    Args:
        subgraph: Undirected solidarity subgraph to analyze.

    Returns:
        Sorted list of node IDs that are articulation points.

    Example:
        >>> import networkx as nx
        >>> G = nx.path_graph(3)
        >>> find_critical_singletons(G)
        ['1']
    """
    if subgraph.number_of_nodes() == 0:
        return []

    points: list[str] = sorted(str(n) for n in articulation_point_set(subgraph))
    return points


def find_critical_cutsets(
    subgraph: BabylonUGraph | nx.Graph[str],
    max_cutset_size: int = 3,
) -> list[frozenset[str]]:
    """Find minimum edge cuts per connected component, bounded by size.

    For each connected component with >= 2 nodes, computes the minimum
    edge cut via :func:`networkx.minimum_edge_cut`. If the cut size
    is <= ``max_cutset_size``, the unique node IDs from the cut edges
    are collected into a frozenset and included in the result.

    Args:
        subgraph: Undirected solidarity subgraph to analyze.
        max_cutset_size: Maximum cut size to include. Components with
            edge connectivity > max_cutset_size are skipped. Default 3.

    Returns:
        List of frozensets, each containing the unique node IDs
        involved in the minimum edge cut of a component.

    Example:
        >>> import networkx as nx
        >>> G = nx.path_graph(3)
        >>> cutsets = find_critical_cutsets(G, max_cutset_size=3)
        >>> len(cutsets) >= 1
        True
    """
    result: list[frozenset[str]] = []

    for component_nodes in component_sets(subgraph):
        if len(component_nodes) < 2:
            continue

        component = subgraph.subgraph(component_nodes).copy()
        cut_edges: set[tuple[str, str]] = min_edge_cut_edges(component)

        if len(cut_edges) > max_cutset_size:
            continue

        # Flatten edge tuples to unique node IDs
        node_ids: set[str] = set()
        for u, v in cut_edges:
            node_ids.add(str(u))
            node_ids.add(str(v))

        result.append(frozenset(node_ids))

    return result


def compute_purge_resilience(
    subgraph: BabylonUGraph | nx.Graph[str],
    removal_rate: float,
    seed: int | None = None,
) -> float:
    """Measure resilience to targeted removal of high-degree nodes.

    Removes the top-degree nodes (sorted descending by degree) at the
    given removal rate and compares post-purge largest component size
    to pre-purge largest component size.

    Args:
        subgraph: Undirected solidarity subgraph to analyze.
        removal_rate: Fraction of nodes to remove (0.0 to 1.0).
        seed: RNG seed for tie-breaking when nodes have equal degree.
            Default None (non-deterministic tie-breaking).

    Returns:
        Ratio of post-purge L_max to pre-purge L_max, clamped to [0, 1].
        Returns 1.0 for empty graphs (vacuously resilient).

    Example:
        >>> import networkx as nx
        >>> G = nx.complete_graph(5)
        >>> compute_purge_resilience(G, removal_rate=0.2, seed=42)
        0.8
    """
    import random

    num_nodes: int = subgraph.number_of_nodes()

    if num_nodes == 0:
        return 1.0

    # Pre-purge L_max
    pre_components: list[set[str]] = component_sets(subgraph)
    pre_l_max: int = max(len(c) for c in pre_components)

    # Sort nodes by degree (descending), use RNG for tie-breaking
    rng = random.Random(seed)
    nodes_by_degree: list[tuple[str, int]] = [
        (str(node), degree) for node, degree in subgraph.degree()
    ]
    # Shuffle first for randomized tie-breaking, then stable-sort by degree desc
    rng.shuffle(nodes_by_degree)
    nodes_by_degree.sort(key=lambda x: x[1], reverse=True)

    # Determine removal count
    num_to_remove: int = max(1, int(num_nodes * removal_rate))
    num_to_remove = min(num_to_remove, num_nodes)

    nodes_to_remove: list[str] = [node for node, _deg in nodes_by_degree[:num_to_remove]]

    # Create copy and remove targeted nodes
    purged = subgraph.copy()
    purged.remove_nodes_from(nodes_to_remove)

    # Post-purge L_max
    if purged.number_of_nodes() == 0:
        post_l_max = 0
    else:
        post_components: list[set[str]] = component_sets(purged)
        post_l_max = max(len(c) for c in post_components)

    # Compute ratio, clamped to [0, 1]
    ratio: float = post_l_max / pre_l_max
    return max(0.0, min(1.0, ratio))
