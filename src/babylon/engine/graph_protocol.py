"""Graph Protocol definition for backend-agnostic graph operations.

Slice 1.7: The Graph Bridge

The GraphProtocol is a typing.Protocol that defines the abstract interface
for all graph operations. Systems interact with the simulation graph ONLY
through this protocol. The concrete implementation (NetworkX, DuckDB) is
hidden behind the adapter.

Design Principles:
    - Backend-agnostic: Works with NetworkX now, DuckDB later
    - Set-oriented: Think in tables, not just objects (DuckDB-ready)
    - Minimal but complete: Just enough methods to cover all System needs
    - Lazy evaluation: Return iterators/generators, not materialized lists

Protocol Methods (18 total):
    Node CRUD: add_node, get_node, update_node, remove_node
    Edge CRUD: add_edge, get_edge, update_edge, remove_edge
    Traversal: get_neighborhood, execute_traversal, shortest_path
    Set Ops: query_nodes, query_edges, count_nodes, count_edges, aggregate
    Graph Attrs: get_graph_attr, set_graph_attr
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.models.graph import (
        GraphEdge,
        GraphNode,
        TraversalQuery,
        TraversalResult,
    )


@runtime_checkable
class GraphProtocol(Protocol):
    """Protocol for backend-agnostic graph operations.

    Systems interact with the simulation graph ONLY through this protocol.
    The concrete implementation (NetworkX, DuckDB) is hidden behind adapters.

    This protocol is runtime_checkable, enabling isinstance() checks for
    protocol compliance.

    Example:
        >>> class MyAdapter:
        ...     def add_node(self, node_id: str, node_type: str, **attrs: Any) -> None:
        ...         pass
        ...     # ... implement all 16 methods
        >>> adapter = MyAdapter()
        >>> isinstance(adapter, GraphProtocol)
        True
    """

    # ─────────────────────────────────────────────────────────────────────
    # NODE OPERATIONS (CRUD)
    # ─────────────────────────────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        node_type: str,
        **attributes: Any,
    ) -> None:
        """Add a node with type marker and arbitrary attributes.

        Args:
            node_id: Unique identifier for the node.
            node_type: Discriminator for polymorphism (e.g., 'social_class').
            **attributes: Type-specific attributes to store on the node.
        """
        ...

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve node by ID.

        Args:
            node_id: The node identifier to look up.

        Returns:
            GraphNode model if found, None otherwise.
        """
        ...

    def update_node(self, node_id: str, **attributes: Any) -> None:
        """Partial update of node attributes (merge, not replace).

        Args:
            node_id: The node identifier to update.
            **attributes: Attributes to update (merged with existing).

        Raises:
            KeyError: If node does not exist.
        """
        ...

    def remove_node(self, node_id: str) -> None:
        """Remove node and all incident edges.

        Args:
            node_id: The node identifier to remove.

        Raises:
            KeyError: If node does not exist.
        """
        ...

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
        """Add directed edge with type, weight, and attributes.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Edge category (e.g., 'SOLIDARITY', 'EXPLOITATION').
            weight: Generic weight (default 1.0).
            **attributes: Type-specific attributes to store on the edge.
        """
        ...

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
            GraphEdge model if found, None otherwise.
        """
        ...

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
            **attributes: Attributes to update (merged with existing).

        Raises:
            KeyError: If edge does not exist.
        """
        ...

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
            KeyError: If edge does not exist.
        """
        ...

    # ─────────────────────────────────────────────────────────────────────
    # TRAVERSAL OPERATIONS
    # ─────────────────────────────────────────────────────────────────────

    def get_neighborhood(
        self,
        node_id: str,
        radius: int = 1,
        edge_types: set[str] | None = None,
        direction: Literal["out", "in", "both"] = "out",
    ) -> Any:
        """Get all nodes within radius hops of the source node.

        Args:
            node_id: Center node for neighborhood.
            radius: Maximum hop distance (1 = immediate neighbors).
            edge_types: Filter to specific edge types (None = all).
            direction: Which edges to follow: outgoing, incoming, or both.

        Returns:
            SubgraphView or equivalent containing nodes in neighborhood.

        Raises:
            KeyError: If node does not exist.
        """
        ...

    def execute_traversal(self, query: TraversalQuery) -> TraversalResult:
        """Execute a generic traversal query.

        This is the hook for complex operations like percolation analysis,
        pathfinding, and component detection.

        Args:
            query: TraversalQuery specifying the traversal.

        Returns:
            TraversalResult with nodes, edges, paths, or aggregates.

        Raises:
            ValueError: If query_type is not supported.
        """
        ...

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
        ...

    # ─────────────────────────────────────────────────────────────────────
    # SET-ORIENTED QUERIES (DuckDB-Ready)
    # ─────────────────────────────────────────────────────────────────────

    def query_nodes(
        self,
        node_type: str | None = None,
        predicate: Callable[[GraphNode], bool] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[GraphNode]:
        """Query nodes with optional filtering.

        Returns an iterator for DuckDB compatibility (lazy evaluation).

        Args:
            node_type: Filter by node type (None = all types).
            predicate: Python callable for complex filtering.
            attributes: Attribute equality filter (DuckDB-translatable).

        Returns:
            Iterator of matching GraphNode models.
        """
        ...

    def query_edges(
        self,
        edge_type: str | None = None,
        predicate: Callable[[GraphEdge], bool] | None = None,
        min_weight: float | None = None,
        max_weight: float | None = None,
    ) -> Iterator[GraphEdge]:
        """Query edges with optional filtering.

        Returns an iterator for DuckDB compatibility (lazy evaluation).

        Args:
            edge_type: Filter by edge type.
            predicate: Python callable for complex filtering.
            min_weight: Minimum weight threshold.
            max_weight: Maximum weight threshold.

        Returns:
            Iterator of matching GraphEdge models.
        """
        ...

    def count_nodes(self, node_type: str | None = None) -> int:
        """Count nodes, optionally by type.

        Args:
            node_type: Filter by node type (None = count all).

        Returns:
            Number of matching nodes.
        """
        ...

    def count_edges(self, edge_type: str | None = None) -> int:
        """Count edges, optionally by type.

        Args:
            edge_type: Filter by edge type (None = count all).

        Returns:
            Number of matching edges.
        """
        ...

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

        Example:
            >>> graph.aggregate("nodes", group_by="type")
            {"social_class": 4, "territory": 2}
        """
        ...

    # ─────────────────────────────────────────────────────────────────────
    # GRAPH-LEVEL ATTRIBUTES
    # ─────────────────────────────────────────────────────────────────────

    def get_graph_attr(self, key: str, default: Any = None) -> Any:
        """Retrieve a graph-level attribute.

        Graph attributes store global metadata (e.g., economy state,
        base_year, tick_dynamics). Maps to a metadata table in DuckDB.

        Args:
            key: Attribute name to retrieve.
            default: Value to return if attribute not present.

        Returns:
            The attribute value or default.
        """
        ...

    def set_graph_attr(self, key: str, value: Any) -> None:
        """Set a graph-level attribute.

        Args:
            key: Attribute name to set.
            value: Value to store.
        """
        ...

    # ─────────────────────────────────────────────────────────────────────
    # SPEC-070 BALKANIZATION EXTENSIONS
    # See specs/070-balkanization/contracts/graph_protocol_extensions.md
    # ─────────────────────────────────────────────────────────────────────

    def query_faction_influence_by_territory(
        self,
        territory_id: str,
    ) -> list[tuple[str, float, str]]:
        """Return all INFLUENCES edges pointing at a Territory.

        Spec-070 FR-021 winning-faction resolution. Each row is
        ``(faction_id, influence_level, support_type)``. Sorted by
        ``influence_level`` descending, lex-ID ascending on ties.

        Args:
            territory_id: Target Territory node ID.

        Returns:
            Deterministic list of influencing factions; empty if none.
        """
        ...

    def query_sovereign_claims(
        self,
        sovereign_id: str,
    ) -> list[tuple[str, float, str]]:
        """Return all CLAIMS edges originating from a Sovereign.

        Each row is ``(territory_id, control_level, legal_status)``.
        Sorted by ``control_level`` descending, lex-ID ascending on
        ties. Used by SovereigntySystem + CollapseTransitionSystem.

        Args:
            sovereign_id: Sovereign node ID.

        Returns:
            Deterministic list of claims; empty if none.
        """
        ...

    def query_territory_claims(
        self,
        territory_id: str,
    ) -> list[tuple[str, float, str]]:
        """Return all CLAIMS edges pointing at a Territory.

        Each row is ``(sovereign_id, control_level, legal_status)``.
        Sorted by ``control_level`` descending, lex-ID ascending on
        ties. Used by SovereigntySystem for dual-power detection
        (FR-035) and effective-controller resolution (FR-020).

        Args:
            territory_id: Target Territory node ID.

        Returns:
            Deterministic list of claimants; empty if none.
        """
        ...

    def query_adjacent_territories(self, territory_id: str) -> list[str]:
        """Return sorted list of Territory IDs adjacent via
        :attr:`EdgeType.ADJACENCY`.

        ADJACENCY edges are conceptually bidirectional; this method
        abstracts the in/out edge direction. Output is sorted
        lexicographically for determinism.

        Args:
            territory_id: Anchor Territory node ID.

        Returns:
            Sorted list of adjacent Territory IDs; empty if isolated.
        """
        ...

    def bulk_partition_claims(
        self,
        from_sovereign_id: str,
        to_sovereign_id: str,
        territories: set[str],
    ) -> int:
        """Atomically rewire CLAIMS edges from one Sovereign to another
        for the given Territory set (spec-070 FR-027).

        Performance requirement (FR-018 / SC-004): MUST be implementable
        in ``O(K)`` where ``K = len(territories)`` — NOT ``O(N)`` in the
        unchanged-territory count.

        Args:
            from_sovereign_id: Current owner Sovereign.
            to_sovereign_id: New owner Sovereign.
            territories: Set of Territory IDs to migrate.

        Returns:
            Count of edges actually rewired.
        """
        ...

    def query_contiguous_component_under_predicate(
        self,
        territory_seed: str,
        predicate: Callable[[str], bool],
    ) -> set[str]:
        """BFS over :attr:`EdgeType.ADJACENCY` from ``territory_seed``,
        collecting Territories satisfying ``predicate``.

        Bounded by the predicate-satisfying contiguous region size, not
        global graph size (per FR-018).

        Args:
            territory_seed: BFS start node.
            predicate: ``(territory_id) -> bool``; only matching nodes
                are included and traversed through.

        Returns:
            Set of Territory IDs in the contiguous predicate-satisfying
            component containing ``territory_seed`` (empty if the seed
            itself fails the predicate).
        """
        ...
