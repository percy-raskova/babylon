"""SubgraphFilterBuilder for constructing filtered subgraphs.

Extracted from inmemory_adapter._build_filtered_subgraph to reduce
cyclomatic complexity and improve testability.

Uses the Builder pattern to chain filter operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import networkx as nx

if TYPE_CHECKING:
    from babylon.models.graph import TraversalQuery


class SubgraphFilterBuilder:
    """Builds filtered subgraphs from NetworkX DiGraphs.

    Uses the Builder pattern to apply node and edge filters incrementally.
    Each filter method returns self for method chaining.

    Example:
        >>> builder = SubgraphFilterBuilder(graph)
        >>> subgraph = (
        ...     builder
        ...     .with_nodes({"C001", "C002"})
        ...     .with_node_types({"social_class"})
        ...     .with_edge_types({"SOLIDARITY"})
        ...     .build()
        ... )
    """

    def __init__(self, graph: nx.DiGraph[str]) -> None:
        """Initialize builder with source graph.

        Args:
            graph: The NetworkX DiGraph to filter.
        """
        self._graph = graph
        self._nodes: set[str] | None = None
        self._node_types: set[str] | None = None
        self._edge_types: set[str] | None = None
        self._min_weight: float | None = None
        self._max_weight: float | None = None

    def with_nodes(self, nodes: set[str] | None) -> SubgraphFilterBuilder:
        """Filter to specific node IDs.

        Args:
            nodes: Set of node IDs to include, or None for all nodes.

        Returns:
            Self for method chaining.
        """
        if nodes is not None:
            self._nodes = nodes
        return self

    def with_node_types(self, node_types: set[str] | None) -> SubgraphFilterBuilder:
        """Filter nodes by type.

        Args:
            node_types: Set of node types to include, or None for all types.

        Returns:
            Self for method chaining.
        """
        if node_types is not None:
            self._node_types = node_types
        return self

    def with_edge_types(self, edge_types: set[str] | None) -> SubgraphFilterBuilder:
        """Filter edges by type.

        Args:
            edge_types: Set of edge types to include, or None for all types.

        Returns:
            Self for method chaining.
        """
        if edge_types is not None:
            self._edge_types = edge_types
        return self

    def with_weight_range(
        self,
        min_weight: float | None = None,
        max_weight: float | None = None,
    ) -> SubgraphFilterBuilder:
        """Filter edges by weight range.

        Args:
            min_weight: Minimum edge weight (inclusive), or None for no minimum.
            max_weight: Maximum edge weight (inclusive), or None for no maximum.

        Returns:
            Self for method chaining.
        """
        self._min_weight = min_weight
        self._max_weight = max_weight
        return self

    def from_query(
        self, query: TraversalQuery, include_all_nodes: bool = False
    ) -> SubgraphFilterBuilder:
        """Configure builder from a TraversalQuery.

        Args:
            query: TraversalQuery with filters to apply.
            include_all_nodes: If True, include all nodes regardless of start_nodes.
                Used for BFS/DFS where start_nodes are starting points, not filters.

        Returns:
            Self for method chaining.
        """
        # Apply node filter from start_nodes
        if not include_all_nodes and query.start_nodes is not None:
            self._nodes = set(query.start_nodes)

        # Apply node filter from query.node_filter
        if query.node_filter and query.node_filter.node_types:
            self._node_types = query.node_filter.node_types

        # Apply edge filter from query.edge_filter
        if query.edge_filter:
            if query.edge_filter.edge_types:
                self._edge_types = query.edge_filter.edge_types
            self._min_weight = query.edge_filter.min_weight
            self._max_weight = query.edge_filter.max_weight

        return self

    def build(self) -> nx.DiGraph[str]:
        """Build the filtered subgraph.

        Applies all configured filters and returns a new DiGraph.

        Returns:
            A new NetworkX DiGraph containing only filtered nodes and edges.
        """
        # Start with nodes to include
        nodes = self._filter_nodes()

        # Build subgraph with filtered nodes
        subgraph: nx.DiGraph[str] = cast("nx.DiGraph[str]", self._graph.subgraph(nodes).copy())

        # Remove edges that don't match filter
        self._filter_edges(subgraph)

        return subgraph

    def _filter_nodes(self) -> set[str]:
        """Apply node filters and return matching node IDs."""
        # Start with specified nodes or all nodes
        nodes = self._nodes.copy() if self._nodes is not None else set(self._graph.nodes)

        # Filter by node type
        if self._node_types is not None:
            nodes = {
                n
                for n in nodes
                if n in self._graph.nodes
                and self._graph.nodes[n].get("_node_type") in self._node_types
            }

        return nodes

    def _filter_edges(self, subgraph: nx.DiGraph[str]) -> None:
        """Remove edges that don't match filters (modifies subgraph in place)."""
        edges_to_remove: list[tuple[str, str]] = []

        for u, v, data in subgraph.edges(data=True):
            if self._should_remove_edge(data):
                edges_to_remove.append((u, v))

        subgraph.remove_edges_from(edges_to_remove)

    def _should_remove_edge(self, data: dict[str, object]) -> bool:
        """Check if an edge should be removed based on filters.

        Args:
            data: Edge attribute dictionary.

        Returns:
            True if edge should be removed, False if it passes all filters.
        """
        # Check edge type filter
        if self._edge_types is not None and data.get("_edge_type") not in self._edge_types:
            return True

        # Check minimum weight
        if self._min_weight is not None:
            weight = data.get("weight", 0.0)
            if isinstance(weight, (int, float)) and weight < self._min_weight:
                return True

        # Check maximum weight
        if self._max_weight is not None:
            weight = data.get("weight", 0.0)
            if isinstance(weight, (int, float)) and weight > self._max_weight:
                return True

        return False
