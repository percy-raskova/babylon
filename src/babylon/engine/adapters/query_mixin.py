"""QueryMixin for graph query operations.

Extracted from inmemory_adapter to reduce class size.
Provides node and edge querying and counting functionality.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import networkx as nx

from babylon.models.graph import GraphEdge, GraphNode


class QueryMixin:
    """Mixin providing query operations for graph adapters.

    Requires the class using this mixin to have a `_graph` attribute
    that is a NetworkX DiGraph.

    Example:
        >>> class MyAdapter(QueryMixin):
        ...     def __init__(self, graph):
        ...         self._graph = graph
        >>> # adapter.query_nodes(node_type="social_class")
    """

    _graph: nx.DiGraph[str]

    def query_nodes(
        self,
        node_type: str | None = None,
        predicate: Callable[[GraphNode], bool] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[GraphNode]:
        """Query nodes with optional filtering.

        Args:
            node_type: Filter by node type (None = all types).
            predicate: Python callable for complex filtering.
            attributes: Attribute equality filter.

        Yields:
            Matching GraphNode models.
        """
        for node_id in self._graph.nodes:
            data = dict(self._graph.nodes[node_id])
            n_type = data.pop("_node_type", "unknown")

            # Type filter
            if node_type and n_type != node_type:
                continue

            # Attribute filter
            if attributes and not all(data.get(k) == v for k, v in attributes.items()):
                continue

            node = GraphNode(id=node_id, node_type=n_type, attributes=data)

            # Predicate filter
            if predicate and not predicate(node):
                continue

            yield node

    def query_edges(
        self,
        edge_type: str | None = None,
        predicate: Callable[[GraphEdge], bool] | None = None,
        min_weight: float | None = None,
        max_weight: float | None = None,
    ) -> Iterator[GraphEdge]:
        """Query edges with optional filtering.

        Args:
            edge_type: Filter by edge type.
            predicate: Python callable for complex filtering.
            min_weight: Minimum weight threshold.
            max_weight: Maximum weight threshold.

        Yields:
            Matching GraphEdge models.
        """
        for source, target, data in self._graph.edges(data=True):
            data_copy = dict(data)
            e_type = data_copy.pop("_edge_type", "unknown")
            weight = data_copy.pop("weight", 1.0)

            # Type filter
            if edge_type and e_type != edge_type:
                continue

            # Weight filters
            if min_weight is not None and weight < min_weight:
                continue
            if max_weight is not None and weight > max_weight:
                continue

            edge = GraphEdge(
                source_id=source,
                target_id=target,
                edge_type=e_type,
                weight=weight,
                attributes=data_copy,
            )

            # Predicate filter
            if predicate and not predicate(edge):
                continue

            yield edge

    def count_nodes(self, node_type: str | None = None) -> int:
        """Count nodes, optionally by type.

        Args:
            node_type: Filter by node type (None = count all).

        Returns:
            Number of matching nodes.
        """
        if node_type is None:
            return self._graph.number_of_nodes()
        return sum(
            1 for n in self._graph.nodes if self._graph.nodes[n].get("_node_type") == node_type
        )

    def count_edges(self, edge_type: str | None = None) -> int:
        """Count edges, optionally by type.

        Args:
            edge_type: Filter by edge type (None = count all).

        Returns:
            Number of matching edges.
        """
        if edge_type is None:
            return self._graph.number_of_edges()
        return sum(
            1 for _, _, data in self._graph.edges(data=True) if data.get("_edge_type") == edge_type
        )
