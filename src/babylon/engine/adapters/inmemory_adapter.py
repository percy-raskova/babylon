"""NetworkX-based in-memory graph adapter.

Slice 1.7: The Graph Bridge

The NetworkXAdapter is the reference implementation of GraphProtocol using
NetworkX. It wraps nx.DiGraph and provides the standard interface for all
graph operations.

Key Implementation Details:
    - Node types stored as '_node_type' attribute (internal)
    - Edge types stored as '_edge_type' attribute (internal)
    - Internal attributes (prefixed with '_') are excluded from user-facing data
    - Thread-safe for read operations (NetworkX is NOT thread-safe for writes)

This adapter is the MVP implementation for Epoch 1 and 2.
DuckDB adapter will be added in Epoch 3 for 1000+ node graphs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Literal, cast

import networkx as nx

from babylon.models.graph import (
    GraphEdge,
    GraphNode,
    TraversalQuery,
    TraversalResult,
)

if TYPE_CHECKING:
    pass


class SubgraphView:
    """Read-only view of a subgraph.

    Provides iteration over nodes in a subgraph returned by neighborhood queries.
    Wraps the underlying NetworkX subgraph to provide GraphNode iteration.

    Attributes:
        _subgraph: The underlying NetworkX subgraph.
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


class NetworkXAdapter:
    """Reference implementation of GraphProtocol using NetworkX.

    Wraps nx.DiGraph and provides all 16 GraphProtocol methods.
    Node types are stored as '_node_type' attribute, edge types as '_edge_type'.

    Example:
        >>> adapter = NetworkXAdapter()
        >>> adapter.add_node("C001", "social_class", wealth=100.0)
        >>> node = adapter.get_node("C001")
        >>> node.wealth
        100.0
    """

    def __init__(self) -> None:
        """Initialize with empty DiGraph."""
        self._graph: nx.DiGraph[str] = nx.DiGraph()

    # ─────────────────────────────────────────────────────────────────────
    # NODE OPERATIONS (CRUD)
    # ─────────────────────────────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        node_type: str,
        **attributes: Any,
    ) -> None:
        """Add a node with type marker and attributes.

        Args:
            node_id: Unique identifier for the node.
            node_type: Discriminator for polymorphism.
            **attributes: Type-specific attributes to store.
        """
        self._graph.add_node(node_id, _node_type=node_type, **attributes)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve node by ID.

        Args:
            node_id: The node identifier to look up.

        Returns:
            GraphNode model if found, None otherwise.
        """
        if node_id not in self._graph:
            return None
        data = dict(self._graph.nodes[node_id])
        node_type = data.pop("_node_type", "unknown")
        return GraphNode(id=node_id, node_type=node_type, attributes=data)

    def update_node(self, node_id: str, **attributes: Any) -> None:
        """Partial update of node attributes (merge, not replace).

        Args:
            node_id: The node identifier to update.
            **attributes: Attributes to update.

        Raises:
            KeyError: If node does not exist.
        """
        if node_id not in self._graph:
            raise KeyError(f"Node '{node_id}' does not exist")
        self._graph.nodes[node_id].update(attributes)

    def remove_node(self, node_id: str) -> None:
        """Remove node and all incident edges.

        Args:
            node_id: The node identifier to remove.

        Raises:
            KeyError: If node does not exist.
        """
        if node_id not in self._graph:
            raise KeyError(f"Node '{node_id}' does not exist")
        self._graph.remove_node(node_id)

    # ─────────────────────────────────────────────────────────────────────
    # EDGE OPERATIONS (CRUD)
    # ─────────────────────────────────────────────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        **attributes: Any,
    ) -> None:
        """Add directed edge with type and weight.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Edge category.
            weight: Generic weight (default 1.0).
            **attributes: Type-specific attributes.
        """
        self._graph.add_edge(
            source,
            target,
            _edge_type=edge_type,
            weight=weight,
            **attributes,
        )

    def get_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
    ) -> GraphEdge | None:
        """Retrieve specific edge by source, target, and type.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Edge type to match.

        Returns:
            GraphEdge model if found and type matches, None otherwise.
        """
        if not self._graph.has_edge(source, target):
            return None
        data = dict(self._graph.edges[source, target])
        if data.get("_edge_type") != edge_type:
            return None
        data.pop("_edge_type", None)
        weight = data.pop("weight", 1.0)
        return GraphEdge(
            source_id=source,
            target_id=target,
            edge_type=edge_type,
            weight=weight,
            attributes=data,
        )

    def update_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        **attributes: Any,
    ) -> None:
        """Partial update of edge attributes.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Edge type to match.
            **attributes: Attributes to update.

        Raises:
            KeyError: If edge does not exist or type doesn't match.
        """
        if not self._graph.has_edge(source, target):
            raise KeyError(f"Edge ({source}, {target}) does not exist")
        if self._graph.edges[source, target].get("_edge_type") != edge_type:
            raise KeyError(f"Edge ({source}, {target}) exists but type is not '{edge_type}'")
        self._graph.edges[source, target].update(attributes)

    def remove_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
    ) -> None:
        """Remove specific edge.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Edge type to match.

        Raises:
            KeyError: If edge does not exist or type doesn't match.
        """
        if not self._graph.has_edge(source, target):
            raise KeyError(f"Edge ({source}, {target}) does not exist")
        if self._graph.edges[source, target].get("_edge_type") != edge_type:
            raise KeyError(f"Edge ({source}, {target}) exists but type is not '{edge_type}'")
        self._graph.remove_edge(source, target)

    # ─────────────────────────────────────────────────────────────────────
    # TRAVERSAL OPERATIONS
    # ─────────────────────────────────────────────────────────────────────

    def get_neighborhood(
        self,
        node_id: str,
        radius: int = 1,
        edge_types: set[str] | None = None,
        direction: Literal["out", "in", "both"] = "out",
    ) -> SubgraphView:
        """Get all nodes within radius hops of the source node.

        Args:
            node_id: Center node for neighborhood.
            radius: Maximum hop distance (1 = immediate neighbors).
            edge_types: Filter to specific edge types (None = all).
            direction: Which edges to follow: outgoing, incoming, or both.

        Returns:
            SubgraphView containing nodes in neighborhood.

        Raises:
            KeyError: If node does not exist.
        """
        if node_id not in self._graph:
            raise KeyError(f"Node '{node_id}' does not exist")

        # BFS with depth limit
        nodes: set[str] = {node_id}
        frontier: set[str] = {node_id}

        for _ in range(radius):
            new_frontier: set[str] = set()
            for n in frontier:
                # Get neighbors based on direction
                if direction in ("out", "both"):
                    for neighbor in self._graph.successors(n):
                        edge_data = self._graph.edges[n, neighbor]
                        if edge_types is None or edge_data.get("_edge_type") in edge_types:
                            new_frontier.add(neighbor)
                if direction in ("in", "both"):
                    for neighbor in self._graph.predecessors(n):
                        edge_data = self._graph.edges[neighbor, n]
                        if edge_types is None or edge_data.get("_edge_type") in edge_types:
                            new_frontier.add(neighbor)
            nodes |= new_frontier
            frontier = new_frontier

        return SubgraphView(self._graph.subgraph(nodes))

    def execute_traversal(self, query: TraversalQuery) -> TraversalResult:
        """Execute generic traversal query.

        Args:
            query: TraversalQuery specifying the traversal.

        Returns:
            TraversalResult with nodes, edges, paths, or aggregates.

        Raises:
            ValueError: If query_type is not supported.
        """
        if query.query_type == "connected_components":
            return self._execute_components_query(query)
        elif query.query_type == "percolation":
            return self._execute_percolation_query(query)
        elif query.query_type == "shortest_path":
            return self._execute_shortest_path_query(query)
        elif query.query_type == "bfs":
            return self._execute_bfs_query(query)
        elif query.query_type == "dfs":
            return self._execute_dfs_query(query)
        elif query.query_type == "reachability":
            return self._execute_reachability_query(query)
        else:
            raise ValueError(f"Unsupported query type: {query.query_type}")

    def _build_filtered_subgraph(
        self, query: TraversalQuery, include_all_nodes: bool = False
    ) -> nx.DiGraph[str]:
        """Build subgraph matching query filters.

        Args:
            query: TraversalQuery with filters to apply.
            include_all_nodes: If True, include all nodes regardless of start_nodes.
                              Used for BFS/DFS where start_nodes are starting points,
                              not node filters.

        Returns:
            NetworkX DiGraph with filtered nodes and edges.
        """
        # Start with all nodes, or filter by start_nodes for component-style queries
        if include_all_nodes or query.start_nodes is None:
            nodes = set(self._graph.nodes)
        else:
            nodes = set(query.start_nodes)

        # Apply node filter
        if query.node_filter and query.node_filter.node_types:
            nodes = {
                n
                for n in nodes
                if self._graph.nodes[n].get("_node_type") in query.node_filter.node_types
            }

        # Build subgraph with edge filtering
        # Note: copy() preserves the graph type (DiGraph), but mypy doesn't infer this
        subgraph: nx.DiGraph[str] = cast("nx.DiGraph[str]", self._graph.subgraph(nodes).copy())

        # Remove edges that don't match filter
        if query.edge_filter:
            edges_to_remove: list[tuple[str, str]] = []
            for u, v, data in subgraph.edges(data=True):
                if (
                    query.edge_filter.edge_types
                    and data.get("_edge_type") not in query.edge_filter.edge_types
                ):
                    edges_to_remove.append((u, v))
                    continue
                if (
                    query.edge_filter.min_weight is not None
                    and data.get("weight", 0) < query.edge_filter.min_weight
                ):
                    edges_to_remove.append((u, v))
                    continue
                if (
                    query.edge_filter.max_weight is not None
                    and data.get("weight", 0) > query.edge_filter.max_weight
                ):
                    edges_to_remove.append((u, v))
                    continue
            subgraph.remove_edges_from(edges_to_remove)

        return subgraph

    def _execute_components_query(self, query: TraversalQuery) -> TraversalResult:
        """Find connected components.

        Args:
            query: TraversalQuery for component detection.

        Returns:
            TraversalResult with components and component_sizes.
        """
        filtered = self._build_filtered_subgraph(query)

        # Find components (undirected)
        components = list(nx.connected_components(filtered.to_undirected()))
        components.sort(key=len, reverse=True)  # Largest first

        return TraversalResult(
            nodes=[n for c in components for n in c],
            components=[list(c) for c in components],
            component_sizes=[len(c) for c in components],
        )

    def _execute_percolation_query(self, query: TraversalQuery) -> TraversalResult:
        """Execute percolation analysis.

        Args:
            query: TraversalQuery for percolation.

        Returns:
            TraversalResult with percolation metrics.
        """
        # Percolation is essentially connected_components with filtering
        return self._execute_components_query(query)

    def _execute_shortest_path_query(self, query: TraversalQuery) -> TraversalResult:
        """Find shortest path.

        Args:
            query: TraversalQuery for pathfinding.

        Returns:
            TraversalResult with paths.
        """
        if not query.start_nodes or not query.target_nodes:
            return TraversalResult()

        # For shortest_path, include all nodes - start/target are endpoints
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        paths: list[list[str]] = []

        for source in query.start_nodes:
            for target in query.target_nodes:
                try:
                    path = nx.shortest_path(filtered, source, target)
                    paths.append(path)
                except nx.NetworkXNoPath:
                    continue
                except nx.NodeNotFound:
                    continue

        all_nodes = set()
        for path in paths:
            all_nodes.update(path)

        return TraversalResult(
            nodes=list(all_nodes),
            paths=paths,
        )

    def _execute_bfs_query(self, query: TraversalQuery) -> TraversalResult:
        """Execute BFS traversal.

        Args:
            query: TraversalQuery for BFS.

        Returns:
            TraversalResult with visited nodes.
        """
        if not query.start_nodes:
            return TraversalResult()

        # For BFS, include all nodes - start_nodes are starting points, not filters
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        visited: set[str] = set()

        for start in query.start_nodes:
            if start in filtered:
                if query.max_depth is not None:
                    lengths = nx.single_source_shortest_path_length(
                        filtered, start, cutoff=query.max_depth
                    )
                    visited.update(lengths.keys())
                else:
                    reachable = nx.descendants(filtered, start)
                    reachable.add(start)
                    visited.update(reachable)

        return TraversalResult(nodes=list(visited))

    def _execute_dfs_query(self, query: TraversalQuery) -> TraversalResult:
        """Execute DFS traversal.

        Args:
            query: TraversalQuery for DFS.

        Returns:
            TraversalResult with visited nodes.
        """
        if not query.start_nodes:
            return TraversalResult()

        # For DFS, include all nodes - start_nodes are starting points, not filters
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        visited: set[str] = set()

        for start in query.start_nodes:
            if start in filtered:
                if query.max_depth is not None:
                    edges = nx.dfs_edges(filtered, start, depth_limit=query.max_depth)
                    visited.add(start)
                    for _u, v in edges:
                        visited.add(v)
                else:
                    reachable = nx.descendants(filtered, start)
                    reachable.add(start)
                    visited.update(reachable)

        return TraversalResult(nodes=list(visited))

    def _execute_reachability_query(self, query: TraversalQuery) -> TraversalResult:
        """Check reachability between nodes.

        Args:
            query: TraversalQuery for reachability.

        Returns:
            TraversalResult with reachable paths.
        """
        if not query.start_nodes or not query.target_nodes:
            return TraversalResult()

        # For reachability, include all nodes - start_nodes/target_nodes are endpoints
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        reachable_targets: list[str] = []

        for source in query.start_nodes:
            for target in query.target_nodes:
                if (
                    source in filtered
                    and target in filtered
                    and nx.has_path(filtered, source, target)
                    and target not in reachable_targets
                ):
                    reachable_targets.append(target)

        return TraversalResult(
            nodes=reachable_targets,
            metadata={"reachable_count": len(reachable_targets)},
        )

    def shortest_path(
        self,
        source: str,
        target: str,
        edge_types: set[str] | None = None,
        weight_attr: str | None = None,
    ) -> list[str] | None:
        """Find shortest path between two nodes.

        Args:
            source: Start node ID.
            target: End node ID.
            edge_types: Filter to specific edge types.
            weight_attr: Attribute to use as weight (None = hop count).

        Returns:
            List of node IDs in path, or None if no path exists.
        """
        if source not in self._graph or target not in self._graph:
            return None

        # Build filtered view if edge_types specified
        if edge_types:
            # Create subgraph with only matching edges
            edges_to_keep = [
                (u, v)
                for u, v, data in self._graph.edges(data=True)
                if data.get("_edge_type") in edge_types
            ]
            subgraph = self._graph.edge_subgraph(edges_to_keep)
        else:
            subgraph = self._graph

        try:
            if weight_attr:
                path = nx.shortest_path(subgraph, source, target, weight=weight_attr)
            else:
                path = nx.shortest_path(subgraph, source, target)
            return list(path)
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

    # ─────────────────────────────────────────────────────────────────────
    # SET-ORIENTED QUERIES
    # ─────────────────────────────────────────────────────────────────────

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
            return self._aggregate_nodes(group_by, agg_func, agg_attr)
        else:
            return self._aggregate_edges(group_by, agg_func, agg_attr)

    def _aggregate_nodes(
        self,
        group_by: str | None,
        agg_func: str,
        agg_attr: str | None,
    ) -> dict[str, float]:
        """Aggregate over nodes.

        Args:
            group_by: Attribute to group by.
            agg_func: Aggregation function.
            agg_attr: Attribute to aggregate.

        Returns:
            Dict mapping group keys to aggregated values.
        """
        groups: dict[str, list[float]] = defaultdict(list)

        for node_id in self._graph.nodes:
            data = self._graph.nodes[node_id]

            # Determine group key
            if group_by == "type":
                key = data.get("_node_type", "unknown")
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

    def _aggregate_edges(
        self,
        group_by: str | None,
        agg_func: str,
        agg_attr: str | None,
    ) -> dict[str, float]:
        """Aggregate over edges.

        Args:
            group_by: Attribute to group by.
            agg_func: Aggregation function.
            agg_attr: Attribute to aggregate.

        Returns:
            Dict mapping group keys to aggregated values.
        """
        groups: dict[str, list[float]] = defaultdict(list)

        for _, _, data in self._graph.edges(data=True):
            # Determine group key
            if group_by == "type":
                key = data.get("_edge_type", "unknown")
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
