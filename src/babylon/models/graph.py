"""Graph abstraction layer data models.

Slice 1.7: The Graph Bridge

These Pydantic models define the type-safe boundary between Systems and the graph
backend. All models are frozen (immutable) for thread safety.

Models:
    EdgeFilter: Filter specification for edge traversal
    NodeFilter: Filter specification for node inclusion
    GraphNode: Frozen Pydantic model for node representation
    GraphEdge: Frozen Pydantic model for edge representation
    TraversalQuery: Generic traversal query specification
    TraversalResult: Result of traversal query execution

Design Principles:
    - Backend-agnostic: Works with NetworkX now, DuckDB later
    - Set-oriented: Think in tables, not just objects (DuckDB-ready)
    - Minimal but complete: Just enough to cover all System needs
    - Lazy evaluation: Return iterators/generators where possible
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EdgeFilter(BaseModel):
    """Filter specification for edge traversal.

    Used to select which edges to traverse during graph operations.
    All fields are optional - None means no filter (match all).

    Attributes:
        edge_types: Set of edge types to include (None = all types).
        min_weight: Minimum weight threshold (inclusive).
        max_weight: Maximum weight threshold (inclusive).

    Example:
        >>> f = EdgeFilter(edge_types={"SOLIDARITY"}, min_weight=0.5)
        >>> f.edge_types
        {'SOLIDARITY'}
    """

    model_config = ConfigDict(frozen=True)

    edge_types: set[str] | None = Field(
        default=None,
        description="Edge types to include (None = all)",
    )
    min_weight: float | None = Field(
        default=None,
        description="Minimum weight threshold (inclusive)",
    )
    max_weight: float | None = Field(
        default=None,
        description="Maximum weight threshold (inclusive)",
    )


class NodeFilter(BaseModel):
    """Filter specification for node inclusion.

    Used to select which nodes to include during graph operations.
    All fields are optional - None means no filter (match all).

    Attributes:
        node_types: Set of node types to include (None = all types).
        attribute_predicates: Dict of attribute equality filters.

    Example:
        >>> f = NodeFilter(node_types={"social_class"})
        >>> f.node_types
        {'social_class'}
    """

    model_config = ConfigDict(frozen=True)

    node_types: set[str] | None = Field(
        default=None,
        description="Node types to include (None = all)",
    )
    attribute_predicates: dict[str, Any] | None = Field(
        default=None,
        description="Attribute equality filters",
    )


class GraphNode(BaseModel):
    """Type-safe graph node representation.

    Frozen Pydantic model for node data at the protocol boundary.
    Adapters convert to/from their internal representation.

    Attributes:
        id: Unique node identifier.
        node_type: Discriminator for polymorphism (e.g., 'social_class', 'territory').
        attributes: Type-specific attributes stored as dict.

    Example:
        >>> node = GraphNode(id="C001", node_type="social_class", attributes={"wealth": 100.0})
        >>> node.wealth
        100.0
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        min_length=1,
        description="Unique node identifier",
    )
    node_type: str = Field(
        ...,
        min_length=1,
        description="Discriminator for polymorphism",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific attributes",
    )

    def get_attr(self, key: str, default: Any = None) -> Any:
        """Get attribute with default.

        Args:
            key: Attribute name to retrieve.
            default: Value to return if attribute not present.

        Returns:
            The attribute value or default.
        """
        return self.attributes.get(key, default)

    @property
    def wealth(self) -> float:
        """Convenience accessor for wealth attribute.

        Returns:
            Wealth value or 0.0 if not present.
        """
        return float(self.attributes.get("wealth", 0.0))


class GraphEdge(BaseModel):
    """Type-safe graph edge representation.

    Frozen Pydantic model for edge data at the protocol boundary.
    Adapters convert to/from their internal representation.

    Attributes:
        source_id: Origin node ID.
        target_id: Destination node ID.
        edge_type: Edge category (e.g., 'SOLIDARITY', 'EXPLOITATION').
        weight: Generic weight (default 1.0).
        attributes: Type-specific attributes stored as dict.

    Example:
        >>> edge = GraphEdge(source_id="C001", target_id="C002", edge_type="SOLIDARITY")
        >>> edge.weight
        1.0
    """

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(
        ...,
        min_length=1,
        description="Origin node ID",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Destination node ID",
    )
    edge_type: str = Field(
        ...,
        min_length=1,
        description="Edge category",
    )
    weight: float = Field(
        default=1.0,
        description="Generic weight",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific attributes",
    )

    @property
    def tension(self) -> float:
        """Convenience accessor for tension attribute.

        Returns:
            Tension value or 0.0 if not present.
        """
        return float(self.attributes.get("tension", 0.0))

    @property
    def value_flow(self) -> float:
        """Convenience accessor for value_flow attribute.

        Returns:
            Value flow or 0.0 if not present.
        """
        return float(self.attributes.get("value_flow", 0.0))


class TraversalQuery(BaseModel):
    """Generic traversal query specification.

    Specifies what traversal to execute and what to collect.
    This is the generic hook for complex operations like percolation
    analysis, pathfinding, and component detection.

    Attributes:
        query_type: Type of traversal algorithm to use.
        start_nodes: Starting node IDs (None = all nodes).
        target_nodes: Target node IDs (for shortest_path, reachability).
        edge_filter: Filter which edges to traverse.
        node_filter: Filter which nodes to include.
        max_depth: Maximum traversal depth.
        collect: What to include in result.

    Example:
        >>> query = TraversalQuery(query_type="bfs", start_nodes=["C001"])
        >>> query.query_type
        'bfs'
    """

    model_config = ConfigDict(frozen=True)

    query_type: Literal[
        "bfs", "dfs", "shortest_path", "connected_components", "percolation", "reachability"
    ] = Field(
        ...,
        description="Type of traversal to execute",
    )
    start_nodes: list[str] | None = Field(
        default=None,
        description="Starting node IDs (None = all nodes)",
    )
    target_nodes: list[str] | None = Field(
        default=None,
        description="Target node IDs (for shortest_path, reachability)",
    )
    edge_filter: EdgeFilter | None = Field(
        default=None,
        description="Filter which edges to traverse",
    )
    node_filter: NodeFilter | None = Field(
        default=None,
        description="Filter which nodes to include",
    )
    max_depth: int | None = Field(
        default=None,
        description="Maximum traversal depth",
    )
    collect: list[str] = Field(
        default=["nodes"],
        description="What to include in result",
    )


class TraversalResult(BaseModel):
    """Result of traversal query execution.

    Contains all data collected during traversal based on query.collect.

    Attributes:
        nodes: Node IDs in traversal result.
        edges: Edge tuples (source, target, type) in result.
        paths: Paths found (for shortest_path queries).
        components: Connected components (for component queries).
        component_sizes: Sizes of connected components (sorted descending).
        metadata: Query-specific metadata.

    Example:
        >>> result = TraversalResult(component_sizes=[10, 5, 3])
        >>> result.largest_component_size
        10
    """

    model_config = ConfigDict(frozen=True)

    nodes: list[str] = Field(
        default_factory=list,
        description="Node IDs in traversal result",
    )
    edges: list[tuple[str, str, str]] = Field(
        default_factory=list,
        description="Edge tuples (source, target, type)",
    )
    paths: list[list[str]] = Field(
        default_factory=list,
        description="Paths found (for shortest_path queries)",
    )
    components: list[list[str]] = Field(
        default_factory=list,
        description="Connected components",
    )
    component_sizes: list[int] = Field(
        default_factory=list,
        description="Sizes of connected components (sorted descending)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Query-specific metadata",
    )

    @property
    def largest_component_size(self) -> int:
        """Size of the largest (giant) component.

        Returns:
            Size of first component or 0 if no components.
        """
        return self.component_sizes[0] if self.component_sizes else 0

    @property
    def percolation_ratio(self) -> float:
        """Fraction of nodes in the largest component.

        This is the key metric for phase transition detection.
        A ratio near 1.0 indicates full percolation (connectivity).

        Returns:
            Ratio of largest_component_size to total nodes, or 0.0 if empty.
        """
        total = sum(self.component_sizes) if self.component_sizes else 0
        if total == 0:
            return 0.0
        return self.largest_component_size / total
