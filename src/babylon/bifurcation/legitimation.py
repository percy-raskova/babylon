"""Legitimation crisis amplifier for bifurcation topology (US7, Feature 033).

Computes a population-weighted legitimation amplifier that scales crisis
intensity inversely with territorial legitimation. When the state loses
legitimacy, crises amplify — Gramsci's "interregnum" where the old order
cannot be maintained but the new order cannot yet be born.

Formula:
    amplifier = 1.0 + (1.0 - mean_legitimation) * (scale - 1.0)

Where:
    mean_legitimation = population-weighted mean of territory legitimation_index
    scale = BifurcationDefines.legitimation_amplifier_scale

See Also:
    :class:`babylon.config.defines.BifurcationDefines`: Configuration for ``legitimation_amplifier_scale``.
    :mod:`babylon.bifurcation.types`: ``BifurcationResult.legitimation_index`` field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.config.defines import BifurcationDefines

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph

_DEFAULT_LEGITIMATION: float = 0.5
"""Default legitimation_index when missing from territory node data."""

_DEFAULT_POPULATION: int = 1
"""Default population when missing from territory node data."""


def compute_legitimation_amplifier(
    graph: BabylonGraph,
    defines: BifurcationDefines,
) -> float:
    """Compute crisis amplifier from population-weighted mean legitimation.

    Iterates all territory nodes in the graph, computes the population-weighted
    mean legitimation index, and returns a multiplier that scales crisis
    intensity. High legitimation (near 1.0) yields amplifier near 1.0.
    Low legitimation (near 0.0) yields amplifier approaching
    ``defines.legitimation_amplifier_scale``.

    Args:
        graph: Simulation graph with territory nodes carrying
            ``legitimation_index`` and ``population`` attributes.
        defines: Bifurcation configuration providing
            ``legitimation_amplifier_scale``.

    Returns:
        Crisis amplifier in range [1.0, legitimation_amplifier_scale].
        Returns 1.0 if no territory nodes are found (graceful degradation).

    Example:
        >>> from babylon.config.defines import BifurcationDefines
        >>> from babylon.topology.graph import BabylonGraph
        >>> G = BabylonGraph()
        >>> G.add_node("T1", _node_type="territory", legitimation_index=0.5, population=100)
        >>> compute_legitimation_amplifier(G, BifurcationDefines())
        1.5
    """
    total_weighted_legitimation: float = 0.0
    total_population: int = 0

    for _node_id, data in graph.nodes(data=True):
        if data.get("_node_type") != "territory":
            continue

        legitimation: float = data.get("legitimation_index", _DEFAULT_LEGITIMATION)
        population: int = data.get("population", _DEFAULT_POPULATION)

        total_weighted_legitimation += population * legitimation
        total_population += population

    if total_population == 0:
        return 1.0

    mean_legitimation: float = total_weighted_legitimation / total_population
    scale: float = defines.legitimation_amplifier_scale
    amplifier: float = 1.0 + (1.0 - mean_legitimation) * (scale - 1.0)

    return amplifier
