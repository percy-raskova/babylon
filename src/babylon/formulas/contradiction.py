"""Contradiction intensity formulas for the Babylon simulation.

These formulas calculate the intensity of contradictions by combining
node-level scalar divergence (e.g. wealth, ideology) with structural
network properties (e.g. node centrality).
"""

from __future__ import annotations


def calculate_contradiction_intensity(
    divergence: float,
    centrality_a: float,
    centrality_b: float,
    sensitivity: float = 1.0,
) -> float:
    """Calculate the emergent intensity of a contradiction edge.

    Combines raw dialectical divergence (e.g. wealth gap, ideological distance)
    with the topological importance of the entities involved, scaling the
    divergence magnitude by their hypergraph centrality or degree.

    Formula:
        intensity = divergence * (1 + sqrt(Centrality_a * Centrality_b)) * sensitivity
        Bound to [0.0, 1.0]

    Args:
        divergence: Raw difference between node states (typically [0, 1]).
        centrality_a: Network/Hypergraph centrality of node A (typically [0, 1]).
        centrality_b: Network/Hypergraph centrality of node B (typically [0, 1]).
        sensitivity: System or definition-level scaling factor.

    Returns:
        Intensity scalar bounded [0.0, 1.0].

    Example:
        >>> calculate_contradiction_intensity(0.5, 0.8, 0.2, 1.0)
        0.7...
    """
    if divergence < 0.0:
        msg = "divergence must be non-negative"
        raise ValueError(msg)
    if centrality_a < 0.0 or centrality_b < 0.0:
        msg = "centralities must be non-negative"
        raise ValueError(msg)
    if sensitivity < 0.0:
        msg = "sensitivity must be non-negative"
        raise ValueError(msg)

    scale_factor = 1.0 + (centrality_a * centrality_b) ** 0.5
    raw_intensity = divergence * scale_factor * sensitivity

    return min(1.0, max(0.0, float(raw_intensity)))
