"""AggregationMixin for graph aggregation operations.

Extracted from inmemory_adapter to reduce class size and unify
duplicate aggregation logic for nodes and edges.

Uses a unified _aggregate_items method instead of separate
_aggregate_nodes and _aggregate_edges implementations.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import networkx as nx


class AggregationMixin:
    """Mixin providing aggregation operations for graph adapters.

    Requires the class using this mixin to have a `_graph` attribute
    that is a NetworkX DiGraph.

    Example:
        >>> class MyAdapter(AggregationMixin):
        ...     def __init__(self, graph):
        ...         self._graph = graph
        >>> # adapter.aggregate("nodes", group_by="type", agg_func="count")
    """

    _graph: nx.DiGraph[str]

    def aggregate(
        self,
        target: Literal["nodes", "edges"],
        group_by: str | None = None,
        agg_func: Literal["count", "sum", "avg", "min", "max"] = "count",
        agg_attr: str | None = None,
    ) -> dict[str, float]:
        """Aggregate over nodes or edges.

        Args:
            target: Whether to aggregate nodes or edges.
            group_by: Attribute to group by (e.g., 'type').
            agg_func: Aggregation function to apply.
            agg_attr: Attribute to aggregate (required for sum/avg/min/max).

        Returns:
            Dict mapping group keys to aggregated values.
        """
        if target == "nodes":
            items = self._iter_node_items()
            type_key = "_node_type"
        else:
            items = self._iter_edge_items()
            type_key = "_edge_type"

        return self._aggregate_items(items, group_by, agg_func, agg_attr, type_key)

    def _iter_node_items(self) -> Iterator[dict[str, Any]]:
        """Iterate over node attribute dictionaries."""
        for node_id in self._graph.nodes:
            yield dict(self._graph.nodes[node_id])

    def _iter_edge_items(self) -> Iterator[dict[str, Any]]:
        """Iterate over edge attribute dictionaries."""
        for _, _, data in self._graph.edges(data=True):
            yield dict(data)

    def _aggregate_items(
        self,
        items: Iterator[dict[str, Any]],
        group_by: str | None,
        agg_func: str,
        agg_attr: str | None,
        type_key: str,
    ) -> dict[str, float]:
        """Unified aggregation over items (nodes or edges).

        Args:
            items: Iterator of item attribute dictionaries.
            group_by: Attribute to group by.
            agg_func: Aggregation function.
            agg_attr: Attribute to aggregate.
            type_key: Internal key for type attribute (_node_type or _edge_type).

        Returns:
            Dict mapping group keys to aggregated values.
        """
        groups: dict[str, list[float]] = defaultdict(list)

        for data in items:
            # Determine group key
            if group_by == "type":
                key = data.get(type_key, "unknown")
            elif group_by:
                key = str(data.get(group_by, "unknown"))
            else:
                key = "_all"

            # Get value to aggregate
            if agg_attr:
                val = data.get(agg_attr, 0.0)
                if isinstance(val, (int, float)):
                    groups[key].append(float(val))
            else:
                groups[key].append(1.0)  # For count

        return self._apply_agg_func(groups, agg_func)

    def _apply_agg_func(
        self,
        groups: dict[str, list[float]],
        agg_func: str,
    ) -> dict[str, float]:
        """Apply aggregation function to grouped values.

        Args:
            groups: Dict mapping group keys to lists of values.
            agg_func: Aggregation function name.

        Returns:
            Dict mapping group keys to aggregated values.
        """
        result: dict[str, float] = {}

        for key, values in groups.items():
            if not values:
                result[key] = 0.0
            elif agg_func == "count":
                result[key] = float(len(values))
            elif agg_func == "sum":
                result[key] = sum(values)
            elif agg_func == "avg":
                result[key] = sum(values) / len(values)
            elif agg_func == "min":
                result[key] = min(values)
            elif agg_func == "max":
                result[key] = max(values)
            else:
                result[key] = float(len(values))  # Default to count

        return result
