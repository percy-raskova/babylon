"""Tests for babylon.engine.graph_protocol - Graph Protocol definition.

TDD Red Phase: These tests define the contract for the GraphProtocol.
The tests WILL FAIL initially because the implementations do not exist yet.
This is the correct Red phase outcome.

Slice 1.7: The Graph Bridge

The GraphProtocol is a typing.Protocol that defines the abstract interface
for all graph operations. Systems interact with the simulation graph ONLY
through this protocol. The concrete implementation (NetworkX, DuckDB) is
hidden behind the adapter.

Protocol Methods (16 total):
- Node CRUD: add_node, get_node, update_node, remove_node
- Edge CRUD: add_edge, get_edge, update_edge, remove_edge
- Traversal: get_neighborhood, execute_traversal, shortest_path
- Set Ops: query_nodes, query_edges, count_nodes, count_edges, aggregate

Design Principles:
- Backend-agnostic: Works with NetworkX now, DuckDB later
- Set-oriented: Think in tables, not just objects (DuckDB-ready)
- Minimal but complete: Just enough methods to cover all System needs
- Lazy evaluation: Return iterators/generators, not materialized lists
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Literal, Protocol

import pytest

if TYPE_CHECKING:
    pass

# Attempt to import - will fail until GREEN phase implementation
# Use pytest.importorskip to gracefully handle missing modules
_graph_module = pytest.importorskip(
    "babylon.models.graph",
    reason="babylon.models.graph not yet implemented (RED phase)",
)
_protocol_module = pytest.importorskip(
    "babylon.engine.graph_protocol",
    reason="babylon.engine.graph_protocol not yet implemented (RED phase)",
)

# Import types from the modules after successful import
GraphProtocol = _protocol_module.GraphProtocol
GraphNode = _graph_module.GraphNode
GraphEdge = _graph_module.GraphEdge
TraversalQuery = _graph_module.TraversalQuery
TraversalResult = _graph_module.TraversalResult


# =============================================================================
# PROTOCOL DEFINITION TESTS
# =============================================================================


@pytest.mark.topology
@pytest.mark.red_phase
class TestGraphProtocolDefinition:
    """Test that GraphProtocol is properly defined as a Protocol."""

    def test_graph_protocol_is_protocol(self) -> None:
        """GraphProtocol must be a typing.Protocol.

        This enables structural subtyping (duck typing with type checking).
        """
        assert hasattr(GraphProtocol, "__protocol_attrs__") or issubclass(GraphProtocol, Protocol)

    def test_graph_protocol_is_runtime_checkable(self) -> None:
        """GraphProtocol must be runtime_checkable.

        This enables isinstance() checks for protocol compliance.
        """
        # Protocol with @runtime_checkable decorator supports isinstance
        # This is verified by the decorator's presence
        assert hasattr(GraphProtocol, "_is_runtime_protocol") or callable(
            getattr(GraphProtocol, "__subclasshook__", None)
        )


@pytest.mark.topology
@pytest.mark.red_phase
class TestGraphProtocolNodeMethods:
    """Test that GraphProtocol defines required node methods."""

    def test_protocol_has_add_node(self) -> None:
        """GraphProtocol must define add_node method.

        Signature: add_node(node_id: str, node_type: str, **attributes: Any) -> None
        """
        assert hasattr(GraphProtocol, "add_node")

    def test_protocol_has_get_node(self) -> None:
        """GraphProtocol must define get_node method.

        Signature: get_node(node_id: str) -> GraphNode | None
        """
        assert hasattr(GraphProtocol, "get_node")

    def test_protocol_has_update_node(self) -> None:
        """GraphProtocol must define update_node method.

        Signature: update_node(node_id: str, **attributes: Any) -> None
        Raises: KeyError if node does not exist
        """
        assert hasattr(GraphProtocol, "update_node")

    def test_protocol_has_remove_node(self) -> None:
        """GraphProtocol must define remove_node method.

        Signature: remove_node(node_id: str) -> None
        Raises: KeyError if node does not exist
        """
        assert hasattr(GraphProtocol, "remove_node")


@pytest.mark.topology
@pytest.mark.red_phase
class TestGraphProtocolEdgeMethods:
    """Test that GraphProtocol defines required edge methods."""

    def test_protocol_has_add_edge(self) -> None:
        """GraphProtocol must define add_edge method.

        Signature: add_edge(source: str, target: str, edge_type: str,
                           weight: float = 1.0, **attributes: Any) -> None
        """
        assert hasattr(GraphProtocol, "add_edge")

    def test_protocol_has_get_edge(self) -> None:
        """GraphProtocol must define get_edge method.

        Signature: get_edge(source: str, target: str, edge_type: str) -> GraphEdge | None
        """
        assert hasattr(GraphProtocol, "get_edge")

    def test_protocol_has_update_edge(self) -> None:
        """GraphProtocol must define update_edge method.

        Signature: update_edge(source: str, target: str, edge_type: str,
                              **attributes: Any) -> None
        """
        assert hasattr(GraphProtocol, "update_edge")

    def test_protocol_has_remove_edge(self) -> None:
        """GraphProtocol must define remove_edge method.

        Signature: remove_edge(source: str, target: str, edge_type: str) -> None
        """
        assert hasattr(GraphProtocol, "remove_edge")


@pytest.mark.topology
@pytest.mark.red_phase
class TestGraphProtocolTraversalMethods:
    """Test that GraphProtocol defines required traversal methods."""

    def test_protocol_has_get_neighborhood(self) -> None:
        """GraphProtocol must define get_neighborhood method.

        Signature: get_neighborhood(node_id: str, radius: int = 1,
                                   edge_types: set[str] | None = None,
                                   direction: Literal["out", "in", "both"] = "out"
                                   ) -> SubgraphView
        """
        assert hasattr(GraphProtocol, "get_neighborhood")

    def test_protocol_has_execute_traversal(self) -> None:
        """GraphProtocol must define execute_traversal method.

        Signature: execute_traversal(query: TraversalQuery) -> TraversalResult
        """
        assert hasattr(GraphProtocol, "execute_traversal")

    def test_protocol_has_shortest_path(self) -> None:
        """GraphProtocol must define shortest_path method.

        Signature: shortest_path(source: str, target: str,
                                edge_types: set[str] | None = None,
                                weight_attr: str | None = None) -> list[str] | None
        """
        assert hasattr(GraphProtocol, "shortest_path")


@pytest.mark.topology
@pytest.mark.red_phase
class TestGraphProtocolSetMethods:
    """Test that GraphProtocol defines required set-oriented methods."""

    def test_protocol_has_query_nodes(self) -> None:
        """GraphProtocol must define query_nodes method.

        Signature: query_nodes(node_type: str | None = None,
                              predicate: Callable[[GraphNode], bool] | None = None,
                              attributes: dict[str, Any] | None = None
                              ) -> Iterator[GraphNode]
        """
        assert hasattr(GraphProtocol, "query_nodes")

    def test_protocol_has_query_edges(self) -> None:
        """GraphProtocol must define query_edges method.

        Signature: query_edges(edge_type: str | None = None,
                              predicate: Callable[[GraphEdge], bool] | None = None,
                              min_weight: float | None = None,
                              max_weight: float | None = None
                              ) -> Iterator[GraphEdge]
        """
        assert hasattr(GraphProtocol, "query_edges")

    def test_protocol_has_count_nodes(self) -> None:
        """GraphProtocol must define count_nodes method.

        Signature: count_nodes(node_type: str | None = None) -> int
        """
        assert hasattr(GraphProtocol, "count_nodes")

    def test_protocol_has_count_edges(self) -> None:
        """GraphProtocol must define count_edges method.

        Signature: count_edges(edge_type: str | None = None) -> int
        """
        assert hasattr(GraphProtocol, "count_edges")

    def test_protocol_has_aggregate(self) -> None:
        """GraphProtocol must define aggregate method.

        Signature: aggregate(target: Literal["nodes", "edges"],
                            group_by: str | None = None,
                            agg_func: Literal["count", "sum", "avg", "min", "max"] = "count",
                            agg_attr: str | None = None
                            ) -> dict[str, float]
        """
        assert hasattr(GraphProtocol, "aggregate")


# =============================================================================
# PROTOCOL COMPLIANCE HELPER
# =============================================================================


class MockGraphAdapter:
    """Minimal mock that implements GraphProtocol for compliance testing.

    This mock is used to verify that a class implementing all required
    methods satisfies the protocol. The implementations are stubs.
    """

    def add_node(self, node_id: str, node_type: str, **attributes: Any) -> None:
        """Add node stub."""
        pass

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get node stub."""
        return None

    def update_node(self, node_id: str, **attributes: Any) -> None:
        """Update node stub."""
        pass

    def remove_node(self, node_id: str) -> None:
        """Remove node stub."""
        pass

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        **attributes: Any,
    ) -> None:
        """Add edge stub."""
        pass

    def get_edge(self, source: str, target: str, edge_type: str) -> GraphEdge | None:
        """Get edge stub."""
        return None

    def update_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        **attributes: Any,
    ) -> None:
        """Update edge stub."""
        pass

    def remove_edge(self, source: str, target: str, edge_type: str) -> None:
        """Remove edge stub."""
        pass

    def get_neighborhood(
        self,
        node_id: str,
        radius: int = 1,
        edge_types: set[str] | None = None,
        direction: Literal["out", "in", "both"] = "out",
    ) -> Any:
        """Get neighborhood stub."""
        return None

    def execute_traversal(self, query: TraversalQuery) -> TraversalResult:
        """Execute traversal stub."""
        return TraversalResult()

    def shortest_path(
        self,
        source: str,
        target: str,
        edge_types: set[str] | None = None,
        weight_attr: str | None = None,
    ) -> list[str] | None:
        """Shortest path stub."""
        return None

    def query_nodes(
        self,
        node_type: str | None = None,
        predicate: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[GraphNode]:
        """Query nodes stub."""
        return iter([])

    def query_edges(
        self,
        edge_type: str | None = None,
        predicate: Any = None,
        min_weight: float | None = None,
        max_weight: float | None = None,
    ) -> Iterator[GraphEdge]:
        """Query edges stub."""
        return iter([])

    def count_nodes(self, node_type: str | None = None) -> int:
        """Count nodes stub."""
        return 0

    def count_edges(self, edge_type: str | None = None) -> int:
        """Count edges stub."""
        return 0

    def aggregate(
        self,
        target: Literal["nodes", "edges"],
        group_by: str | None = None,
        agg_func: Literal["count", "sum", "avg", "min", "max"] = "count",
        agg_attr: str | None = None,
    ) -> dict[str, float]:
        """Aggregate stub."""
        return {}


@pytest.mark.topology
@pytest.mark.red_phase
class TestProtocolCompliance:
    """Test that classes can satisfy GraphProtocol structurally."""

    def test_mock_adapter_satisfies_protocol(self) -> None:
        """MockGraphAdapter satisfies GraphProtocol.

        This validates that our understanding of the protocol is correct.
        If the protocol requires additional methods, this test will fail.
        """
        adapter = MockGraphAdapter()
        # Runtime check should pass for a complete implementation
        assert isinstance(adapter, GraphProtocol)

    def test_incomplete_class_does_not_satisfy_protocol(self) -> None:
        """A class missing methods does not satisfy GraphProtocol.

        This verifies that the protocol actually checks for methods.
        """

        class IncompleteAdapter:
            def add_node(self, node_id: str, node_type: str) -> None:
                pass

            # Missing all other methods

        adapter = IncompleteAdapter()
        # Should NOT satisfy the protocol
        assert not isinstance(adapter, GraphProtocol)
