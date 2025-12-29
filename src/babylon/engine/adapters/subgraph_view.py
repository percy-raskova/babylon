"""SubgraphView for read-only graph iteration.

Extracted from inmemory_adapter to reduce file size and improve modularity.
Provides iteration over nodes and edges in a subgraph.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx

from babylon.models.graph import GraphEdge, GraphNode


class SubgraphView:
    """Read-only view of a subgraph.

    Provides iteration over nodes in a subgraph returned by neighborhood queries.
    Wraps the underlying NetworkX subgraph to provide GraphNode iteration.

    Attributes:
        _subgraph: The underlying NetworkX subgraph.

    Example:
        >>> from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter
        >>> adapter = NetworkXAdapter()
        >>> adapter.add_node("C001", "social_class", wealth=100.0)
        >>> adapter.add_node("C002", "social_class", wealth=50.0)
        >>> adapter.add_edge("C001", "C002", "SOLIDARITY")
        >>> view = adapter.get_neighborhood("C001")
        >>> list(view.nodes())  # doctest: +ELLIPSIS
        [GraphNode(...), GraphNode(...)]
    """

    def __init__(self, subgraph: nx.Graph[str]) -> None:
        """Initialize with a NetworkX subgraph.

        Args:
            subgraph: The NetworkX subgraph to wrap. Can be DiGraph or subgraph view.
        """
        self._subgraph = subgraph

    def nodes(self) -> Iterator[GraphNode]:
        """Iterate over nodes in the subgraph.

        Yields:
            GraphNode models for each node in the subgraph.
        """
        for node_id in self._subgraph.nodes:
            data = dict(self._subgraph.nodes[node_id])
            node_type = data.pop("_node_type", "unknown")
            yield GraphNode(id=node_id, node_type=node_type, attributes=data)

    def edges(self) -> Iterator[GraphEdge]:
        """Iterate over edges in the subgraph.

        Yields:
            GraphEdge models for each edge in the subgraph.
        """
        for source, target, data in self._subgraph.edges(data=True):
            data_copy = dict(data)
            edge_type = data_copy.pop("_edge_type", "unknown")
            weight = data_copy.pop("weight", 1.0)
            yield GraphEdge(
                source_id=source,
                target_id=target,
                edge_type=edge_type,
                weight=weight,
                attributes=data_copy,
            )
