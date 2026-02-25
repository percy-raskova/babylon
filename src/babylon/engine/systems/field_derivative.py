"""FieldDerivativeSystem — System #15 in materialist causality order.

Dialectical Field Topology (Feature 002): Computes spatial derivatives
(gradient on edges, Laplacian on nodes), temporal derivatives (df/dt,
d2f/dt2), principal contradiction identification, and continuity residuals.

Reference: FR-003 (gradient), FR-004 (Laplacian)
Reference: FR-006 (temporal derivatives)
Reference: FR-008 (principal contradiction)
Reference: FR-009 (continuity residuals)
Reference: R-006 (system ordering — position 15)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

logger = logging.getLogger(__name__)


class FieldDerivativeSystem:
    """Compute spatial and temporal derivatives for contradiction fields.

    Execution Order: 15 (after ContradictionFieldSystem)

    Reads contradiction_fields from nodes (written by System #14),
    computes gradients on edges, Laplacian at nodes, and temporal
    derivatives from the rolling history in persistent_data.
    """

    name = "field_derivative"

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Compute all spatial and temporal derivatives.

        Args:
            graph: Mutable graph (NetworkX or GraphProtocol).
            services: ServiceContainer with field_registry.
            context: TickContext or dict with tick and persistent_data.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        registry = services.field_registry
        if registry is None:
            return

        field_names = registry.get_field_names()
        if not field_names:
            return

        persistent_data = _get_persistent_data(context)
        history: dict[str, dict[str, list[float]]] = persistent_data.get(
            "contradiction_history", {}
        )

        # ─── Phase 1: Spatial gradients on edges ────────────────────
        _compute_edge_gradients(graph, field_names)

        # ─── Phase 2: Laplacian + temporal derivatives on nodes ─────
        _compute_node_derivatives(graph, field_names, history)

    # ─── Principal contradiction (Phase 5, added later) ─────────────
    # ─── Continuity residuals (Phase 8, added later) ────────────────


def _compute_edge_gradients(
    graph: GraphProtocol,
    field_names: list[str],
) -> None:
    """Compute gradient = f(target) - f(source) on every edge.

    Args:
        graph: Graph with contradiction_fields on nodes.
        field_names: List of field names to compute gradients for.
    """
    for edge in graph.query_edges():
        src_node = graph.get_node(edge.source_id)
        tgt_node = graph.get_node(edge.target_id)

        if src_node is None or tgt_node is None:
            continue

        src_fields: dict[str, float] = src_node.attributes.get("contradiction_fields", {})
        tgt_fields: dict[str, float] = tgt_node.attributes.get("contradiction_fields", {})

        # Skip edges where nodes don't have field data
        if not src_fields or not tgt_fields:
            continue

        gradients: dict[str, float] = {}
        for field_name in field_names:
            src_val = src_fields.get(field_name, 0.0)
            tgt_val = tgt_fields.get(field_name, 0.0)
            gradients[field_name] = tgt_val - src_val

        graph.update_edge(
            edge.source_id,
            edge.target_id,
            edge.edge_type,
            field_gradients=gradients,
        )


def _compute_node_derivatives(
    graph: GraphProtocol,
    field_names: list[str],
    history: dict[str, dict[str, list[float]]],
) -> None:
    """Compute Laplacian and temporal derivatives at each node.

    Args:
        graph: Graph with contradiction_fields on nodes.
        field_names: List of field names.
        history: contradiction_history from persistent_data.
    """
    for node in graph.query_nodes(node_type="social_class"):
        node_id = node.id
        node_fields: dict[str, float] = node.attributes.get("contradiction_fields", {})
        if not node_fields:
            continue

        node_history = history.get(node_id, {})

        # Collect neighbor field values (both in and out edges)
        neighbor_fields = _collect_neighbor_fields(graph, node_id, field_names)

        field_derivatives: dict[str, dict[str, float | None]] = {}
        for field_name in field_names:
            my_val = node_fields.get(field_name, 0.0)

            # Laplacian: sum_j(f(j) - f(i))
            neighbor_vals = neighbor_fields.get(field_name, [])
            if neighbor_vals:
                laplacian = sum(nv - my_val for nv in neighbor_vals)
            else:
                laplacian = 0.0
                if not neighbor_vals:
                    logger.debug(
                        "EC-002: Isolated node %s, Laplacian=0.0 for %s",
                        node_id,
                        field_name,
                    )

            # Temporal derivatives from history
            field_hist = node_history.get(field_name, [])
            df_dt: float | None = None
            d2f_dt2: float | None = None

            if len(field_hist) >= 2:
                # df/dt = f(t) - f(t-1)
                df_dt = field_hist[-1] - field_hist[-2]

            if len(field_hist) >= 3:
                # d2f/dt2 = f(t) - 2*f(t-1) + f(t-2)
                d2f_dt2 = field_hist[-1] - 2.0 * field_hist[-2] + field_hist[-3]

            field_derivatives[field_name] = {
                "laplacian": laplacian,
                "df_dt": df_dt,
                "d2f_dt2": d2f_dt2,
            }

        graph.update_node(node_id, field_derivatives=field_derivatives)


def _collect_neighbor_fields(
    graph: GraphProtocol,
    node_id: str,
    field_names: list[str],
) -> dict[str, list[float]]:
    """Collect field values from all neighbors of a node.

    Considers both incoming and outgoing edges to ensure full
    Laplacian computation on the undirected graph structure.

    Args:
        graph: Graph protocol instance.
        node_id: Node to collect neighbors for.
        field_names: Field names to collect.

    Returns:
        Mapping of field_name -> list of neighbor values.
    """
    result: dict[str, list[float]] = {name: [] for name in field_names}

    # Collect unique neighbor IDs from both directions
    neighbor_ids: set[str] = set()

    for edge in graph.query_edges():
        if edge.source_id == node_id:
            neighbor_ids.add(edge.target_id)
        elif edge.target_id == node_id:
            neighbor_ids.add(edge.source_id)

    for nid in neighbor_ids:
        neighbor_node = graph.get_node(nid)
        if neighbor_node is None:
            continue
        n_fields: dict[str, float] = neighbor_node.attributes.get("contradiction_fields", {})
        for field_name in field_names:
            if field_name in n_fields:
                result[field_name].append(n_fields[field_name])

    return result


def _get_persistent_data(context: ContextType) -> dict[str, Any]:
    """Extract persistent_data from context (TickContext or dict).

    Args:
        context: TickContext or dict with persistent_data key.

    Returns:
        Mutable persistent_data dict.
    """
    if hasattr(context, "persistent_data"):
        result: dict[str, Any] = context.persistent_data
        return result
    if isinstance(context, dict):
        data: dict[str, Any] = context.setdefault("persistent_data", {})
        return data
    return {}
