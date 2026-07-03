"""G_observed construction for attention threads (Feature 039).

Builds an observed subgraph from a thread's collected node/edge observations,
applying method-specific distortions that model real-world intelligence gaps.

See Also:
    :class:`babylon.models.entities.attention_thread.AttentionThread`: Thread model.
    :mod:`babylon.ooda.attention.sparrow`: Sparrow analysis on G_observed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx  # noqa: F401 — transitional annotation arm (Amendment L)

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph

from babylon.models.entities.attention_thread import AttentionThread
from babylon.models.enums import SurveillanceMethod


def build_g_observed(
    thread: AttentionThread,
    full_graph: nx.DiGraph[str],
) -> BabylonGraph | nx.DiGraph[str]:
    """Build the observed subgraph from thread intelligence.

    Extracts nodes and edges that the thread has observed, applying
    method-specific distortions.

    Args:
        thread: AttentionThread with observed_node_ids and observed_edge_ids.
        full_graph: The complete world graph.

    Returns:
        DiGraph containing only observed nodes/edges with potential distortions.
    """
    from babylon.engine.graph import BabylonGraph

    observed = BabylonGraph()

    # Add observed nodes with their attributes
    max_nodes = 1000
    for idx, node_id in enumerate(thread.observed_node_ids):
        if idx >= max_nodes:
            break
        if node_id in full_graph:
            attrs = dict(full_graph.nodes[node_id])
            observed.add_node(node_id, **attrs)

    # Add observed edges with method-specific distortions
    max_edges = 5000
    for idx, (src, tgt) in enumerate(thread.observed_edge_ids):
        if idx >= max_edges:
            break
        if src in observed and tgt in observed and full_graph.has_edge(src, tgt):
            edge_attrs = dict(full_graph.edges[src, tgt])
            distorted = _apply_distortions(edge_attrs, thread.surveillance_methods)
            observed.add_edge(src, tgt, **distorted)

    return observed


def compute_observation_ceiling(
    base_ceiling: float,
    compartmentalization_factor: float,
) -> float:
    """Compute effective observation ceiling for a thread.

    effective_ceiling = base_ceiling * (1 - compartmentalization_factor)

    Args:
        base_ceiling: Maximum intel_completeness without compartmentalization.
        compartmentalization_factor: Target's resistance to surveillance [0, 1].

    Returns:
        Effective ceiling, clamped to [0.0, 1.0].
    """
    ceiling = base_ceiling * (1.0 - compartmentalization_factor)
    return max(0.0, min(1.0, ceiling))


def _apply_distortions(
    edge_attrs: dict[str, Any],
    methods: list[SurveillanceMethod] | tuple[SurveillanceMethod, ...],
) -> dict[str, Any]:
    """Apply surveillance method-specific distortions to edge attributes.

    Method gaps:

    - SIGNALS: Cannot distinguish edge types (conflation).
    - FINANCIAL: Cannot see non-monetary edges (cash invisibility).
    - SOCIAL_MEDIA: Temporal flattening (sees current, not history).
    - INFORMANT: May introduce false edges (unreliability).
    - PHYSICAL: Cannot see digital/remote edges (face-to-face blindness).

    Args:
        edge_attrs: Original edge attributes from full graph.
        methods: Active surveillance methods on the thread.

    Returns:
        Potentially distorted edge attributes.
    """
    result = dict(edge_attrs)

    methods_set = set(methods)

    # SIGNALS: edge type conflation -- type becomes generic
    if SurveillanceMethod.SIGNALS in methods_set and len(methods_set) == 1:
        result["edge_type"] = "observed_connection"

    # FINANCIAL: can only observe monetary edges
    if SurveillanceMethod.FINANCIAL in methods_set and len(methods_set) == 1:
        edge_type = result.get("edge_type", "")
        monetary_types = {"wages", "tribute", "exploitation", "tenancy", "transactional"}
        if edge_type not in monetary_types:
            result["distorted"] = True
            result["confidence"] = 0.3

    return result


__all__ = ["build_g_observed", "compute_observation_ceiling"]
