"""Ollivier-Ricci curvature computation for contradiction field topology.

Dialectical Field Topology (Feature 002): Discrete Ricci curvature
measures how "spread out" the neighborhoods of two connected nodes are.
Positive curvature = well-connected (clustered), negative curvature =
bottleneck (bridge). This captures the topological structure of class
relationships.

Reference: FR-005 (Ollivier-Ricci curvature on edges)
Reference: R-004 (scipy LP for Wasserstein-1 distance)

Algorithm:
    For each edge (u, v):
    1. Construct probability measures mu_u, mu_v over neighborhoods
       with alpha self-loop weight
    2. Build cost matrix from shortest path distances
    3. Solve linear program for Wasserstein-1 (Earth Mover's) distance
    4. kappa(u,v) = 1 - W1/d(u,v)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import linprog  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonUGraph


def compute_ollivier_ricci(
    graph: BabylonUGraph,
    u: str,
    v: str,
    alpha: float = 0.5,
    weight_attr: str | None = None,
) -> float:
    """Compute Ollivier-Ricci curvature for a single edge (u, v).

    Args:
        graph: Undirected or directed NetworkX graph.
        u: Source node.
        v: Target node.
        alpha: Self-loop probability weight in [0, 1].
            Higher alpha = more weight on the node itself.
        weight_attr: Optional edge attribute name for weights.
            When set, probability measures distribute (1-alpha)
            proportional to edge weights instead of uniformly,
            and shortest path uses weighted distances.
            None = unweighted (backward compatible).

    Returns:
        Curvature kappa(u,v) = 1 - W1(mu_u, mu_v) / d(u,v).
        Positive = well-connected, negative = bottleneck.

    Raises:
        ValueError: If u or v is not in the graph or they are not connected.
    """
    if u not in graph or v not in graph:
        msg = f"Node {u} or {v} not in graph"
        raise ValueError(msg)

    # Graph distance between u and v
    d_uv = _graph_distance(graph, u, v, weight_attr=weight_attr)
    if d_uv == 0:
        return 0.0  # Self-loop: curvature undefined, return 0

    # Construct probability measures
    mu_u = _probability_measure(graph, u, alpha, weight_attr=weight_attr)
    mu_v = _probability_measure(graph, v, alpha, weight_attr=weight_attr)

    # Union of supports
    all_nodes = sorted(set(mu_u.keys()) | set(mu_v.keys()))
    n = len(all_nodes)

    # Build supply and demand vectors
    supply = np.array([mu_u.get(node, 0.0) for node in all_nodes])
    demand = np.array([mu_v.get(node, 0.0) for node in all_nodes])

    # Cost matrix: shortest path distances
    cost = np.zeros((n, n))
    for i, ni in enumerate(all_nodes):
        for j, nj in enumerate(all_nodes):
            if i != j:
                cost[i, j] = _graph_distance(graph, ni, nj, weight_attr=weight_attr)

    # Solve transportation problem via LP
    w1 = _wasserstein_1(supply, demand, cost)

    # Curvature
    return 1.0 - w1 / d_uv


def _probability_measure(
    graph: BabylonUGraph,
    node: str,
    alpha: float,
    weight_attr: str | None = None,
) -> dict[str, float]:
    """Construct probability measure centered at node.

    With probability alpha, stay at the node.
    With probability (1-alpha), distribute to neighbors:
    - If weight_attr is None: uniformly
    - If weight_attr is set: proportional to edge weights

    Args:
        graph: NetworkX graph.
        node: Center node.
        alpha: Self-loop weight.
        weight_attr: Optional edge attribute for proportional weighting.

    Returns:
        Dict mapping node -> probability.
    """
    neighbors = list(graph.neighbors(node))
    measure: dict[str, float] = {}

    if not neighbors:
        # Isolated node: all mass on self
        measure[node] = 1.0
        return measure

    measure[node] = alpha

    if weight_attr is not None:
        # Weighted: distribute (1-alpha) proportional to edge weights
        neighbor_weights: list[tuple[str, float]] = []
        for neighbor in neighbors:
            edge_data = graph.get_edge_data(node, neighbor)
            w = float(edge_data.get(weight_attr, 1.0)) if edge_data else 1.0
            neighbor_weights.append((neighbor, w))

        total_weight = sum(w for _, w in neighbor_weights)
        if total_weight > 0:
            for neighbor, w in neighbor_weights:
                prob = (1.0 - alpha) * (w / total_weight)
                measure[neighbor] = measure.get(neighbor, 0.0) + prob
        else:
            # All weights zero: uniform fallback
            uniform = (1.0 - alpha) / len(neighbors)
            for neighbor in neighbors:
                measure[neighbor] = measure.get(neighbor, 0.0) + uniform
    else:
        # Unweighted: uniform distribution
        neighbor_weight = (1.0 - alpha) / len(neighbors)
        for neighbor in neighbors:
            measure[neighbor] = measure.get(neighbor, 0.0) + neighbor_weight

    return measure


def _graph_distance(
    graph: BabylonUGraph,
    u: str,
    v: str,
    weight_attr: str | None = None,
) -> float:
    """Compute shortest path distance between u and v.

    Args:
        graph: Undirected analytics graph.
        u: Source node.
        v: Target node.
        weight_attr: Optional edge attribute name for weighted distance.
            None = hop count (unweighted).

    Returns:
        Shortest path length. Returns inf if disconnected.
    """
    # Function-local import: formulas are imported during babylon.models
    # init (sovereign -> balkanization); a module-level engine import here
    # closes an import cycle (models -> formulas -> engine -> ... -> models).
    from babylon.topology.graph_algorithms import shortest_path_length_between

    return shortest_path_length_between(graph, u, v, weight_attr=weight_attr)


def _wasserstein_1(
    supply: np.ndarray,
    demand: np.ndarray,
    cost: np.ndarray,
) -> float:
    """Compute Wasserstein-1 (Earth Mover's) distance via LP.

    Solves the transportation problem:
        min sum_ij cost[i,j] * x[i,j]
        s.t. sum_j x[i,j] = supply[i]  for all i
             sum_i x[i,j] = demand[j]  for all j
             x[i,j] >= 0

    Args:
        supply: Source probability distribution.
        demand: Target probability distribution.
        cost: Pairwise cost (distance) matrix.

    Returns:
        Optimal transport cost (Wasserstein-1 distance).
    """
    n = len(supply)

    # Flatten cost matrix for LP
    c = cost.flatten()

    # Equality constraints: Ax_eq = b_eq
    # Row constraints: sum_j x[i,j] = supply[i]
    # Col constraints: sum_i x[i,j] = demand[j]
    a_eq = np.zeros((2 * n, n * n))
    b_eq = np.zeros(2 * n)

    for i in range(n):
        # Row constraint: sum_j x[i,j] = supply[i]
        for j in range(n):
            a_eq[i, i * n + j] = 1.0
        b_eq[i] = supply[i]

    for j in range(n):
        # Column constraint: sum_i x[i,j] = demand[j]
        for i in range(n):
            a_eq[n + j, i * n + j] = 1.0
        b_eq[n + j] = demand[j]

    # Solve LP
    result = linprog(
        c,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=(0, None),
        method="highs",
    )

    if result.success:
        return float(result.fun)
    # Fallback: return 0 if LP fails (shouldn't happen with valid inputs)
    return 0.0
