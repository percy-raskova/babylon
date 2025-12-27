"""Tests for babylon.engine.adapters.inmemory_adapter - NetworkX graph adapter.

TDD Red Phase: These tests define the contract for the NetworkXAdapter.
The tests WILL FAIL initially because the implementations do not exist yet.
This is the correct Red phase outcome.

Slice 1.7: The Graph Bridge

The NetworkXAdapter is the reference implementation of GraphProtocol using NetworkX.
It wraps nx.DiGraph and provides the standard interface for all graph operations.

Key Behaviors:
- Node types stored as '_node_type' attribute
- Edge types stored as '_edge_type' attribute
- Supports all 16 GraphProtocol methods
- Thread-safe for read operations (NetworkX is NOT thread-safe for writes)

This adapter is the MVP implementation for Epoch 1 and 2.
DuckDB adapter will be added in Epoch 3 for 1000+ node graphs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
_adapter_module = pytest.importorskip(
    "babylon.engine.adapters.inmemory_adapter",
    reason="babylon.engine.adapters.inmemory_adapter not yet implemented (RED phase)",
)

# Import types from the modules after successful import
GraphProtocol = _protocol_module.GraphProtocol
NetworkXAdapter = _adapter_module.NetworkXAdapter
GraphNode = _graph_module.GraphNode
GraphEdge = _graph_module.GraphEdge
EdgeFilter = _graph_module.EdgeFilter
TraversalQuery = _graph_module.TraversalQuery
TraversalResult = _graph_module.TraversalResult


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def adapter() -> NetworkXAdapter:
    """Create a fresh NetworkXAdapter for each test."""
    return NetworkXAdapter()


@pytest.fixture
def populated_adapter() -> NetworkXAdapter:
    """Create an adapter with sample nodes and edges.

    Graph structure:
        C001 (proletariat) --SOLIDARITY--> C002 (proletariat)
        C001 --SOLIDARITY--> C003 (proletariat)
        C003 --EXPLOITATION--> C004 (bourgeoisie)
        T001 (territory) --ADJACENCY--> T002 (territory)
    """
    adapter = NetworkXAdapter()

    # Add social class nodes
    adapter.add_node("C001", "social_class", wealth=100.0, consciousness=0.5)
    adapter.add_node("C002", "social_class", wealth=80.0, consciousness=0.6)
    adapter.add_node("C003", "social_class", wealth=50.0, consciousness=0.7)
    adapter.add_node("C004", "social_class", wealth=500.0, consciousness=0.2)

    # Add territory nodes
    adapter.add_node("T001", "territory", heat=0.3, name="Oakland")
    adapter.add_node("T002", "territory", heat=0.1, name="San Francisco")

    # Add edges
    adapter.add_edge("C001", "C002", "SOLIDARITY", weight=0.8, solidarity_strength=0.8)
    adapter.add_edge("C001", "C003", "SOLIDARITY", weight=0.6, solidarity_strength=0.6)
    adapter.add_edge("C003", "C004", "EXPLOITATION", weight=0.9, value_flow=50.0)
    adapter.add_edge("T001", "T002", "ADJACENCY", weight=1.0)

    return adapter


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterProtocolCompliance:
    """Test that NetworkXAdapter implements GraphProtocol."""

    def test_adapter_implements_graph_protocol(self, adapter: NetworkXAdapter) -> None:
        """NetworkXAdapter must implement GraphProtocol.

        This is the fundamental contract - all adapters must satisfy the protocol.
        """
        assert isinstance(adapter, GraphProtocol)

    def test_adapter_uses_networkx_digraph(self, adapter: NetworkXAdapter) -> None:
        """NetworkXAdapter uses nx.DiGraph internally.

        This verifies the implementation choice for Epoch 1.
        """
        import networkx as nx

        assert hasattr(adapter, "_graph")
        assert isinstance(adapter._graph, nx.DiGraph)


# =============================================================================
# NODE CRUD TESTS
# =============================================================================


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterAddNode:
    """Test NetworkXAdapter.add_node method."""

    def test_add_node_creates_node(self, adapter: NetworkXAdapter) -> None:
        """add_node creates a node in the graph."""
        adapter.add_node("C001", "social_class")

        node = adapter.get_node("C001")
        assert node is not None
        assert node.id == "C001"
        assert node.node_type == "social_class"

    def test_add_node_stores_type(self, adapter: NetworkXAdapter) -> None:
        """add_node stores node_type as internal attribute."""
        adapter.add_node("C001", "social_class")

        # Verify internal storage
        assert adapter._graph.nodes["C001"]["_node_type"] == "social_class"

    def test_add_node_stores_attributes(self, adapter: NetworkXAdapter) -> None:
        """add_node stores arbitrary attributes."""
        adapter.add_node("C001", "social_class", wealth=100.0, consciousness=0.5)

        node = adapter.get_node("C001")
        assert node is not None
        assert node.attributes["wealth"] == 100.0
        assert node.attributes["consciousness"] == 0.5

    def test_add_node_overwrites_existing(self, adapter: NetworkXAdapter) -> None:
        """add_node overwrites an existing node (NetworkX behavior)."""
        adapter.add_node("C001", "social_class", wealth=100.0)
        adapter.add_node("C001", "social_class", wealth=200.0)

        node = adapter.get_node("C001")
        assert node is not None
        assert node.attributes["wealth"] == 200.0


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterGetNode:
    """Test NetworkXAdapter.get_node method."""

    def test_get_node_returns_graphnode(self, adapter: NetworkXAdapter) -> None:
        """get_node returns GraphNode model."""
        adapter.add_node("C001", "social_class", wealth=100.0)

        node = adapter.get_node("C001")
        assert isinstance(node, GraphNode)

    def test_get_node_returns_none_for_missing(self, adapter: NetworkXAdapter) -> None:
        """get_node returns None if node does not exist."""
        node = adapter.get_node("MISSING")
        assert node is None

    def test_get_node_excludes_internal_attributes(self, adapter: NetworkXAdapter) -> None:
        """get_node excludes internal attributes like _node_type.

        Internal attributes (prefixed with _) should not appear in user-facing data.
        """
        adapter.add_node("C001", "social_class", wealth=100.0)

        node = adapter.get_node("C001")
        assert node is not None
        assert "_node_type" not in node.attributes


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterUpdateNode:
    """Test NetworkXAdapter.update_node method."""

    def test_update_node_modifies_attributes(self, adapter: NetworkXAdapter) -> None:
        """update_node modifies existing node attributes."""
        adapter.add_node("C001", "social_class", wealth=100.0)
        adapter.update_node("C001", wealth=200.0)

        node = adapter.get_node("C001")
        assert node is not None
        assert node.attributes["wealth"] == 200.0

    def test_update_node_adds_new_attributes(self, adapter: NetworkXAdapter) -> None:
        """update_node can add new attributes."""
        adapter.add_node("C001", "social_class", wealth=100.0)
        adapter.update_node("C001", consciousness=0.7)

        node = adapter.get_node("C001")
        assert node is not None
        assert node.attributes["consciousness"] == 0.7
        assert node.attributes["wealth"] == 100.0  # Preserved

    def test_update_node_raises_keyerror_for_missing(self, adapter: NetworkXAdapter) -> None:
        """update_node raises KeyError if node does not exist."""
        with pytest.raises(KeyError):
            adapter.update_node("MISSING", wealth=100.0)


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterRemoveNode:
    """Test NetworkXAdapter.remove_node method."""

    def test_remove_node_deletes_node(self, adapter: NetworkXAdapter) -> None:
        """remove_node deletes the node from graph."""
        adapter.add_node("C001", "social_class")
        adapter.remove_node("C001")

        assert adapter.get_node("C001") is None

    def test_remove_node_deletes_incident_edges(self, adapter: NetworkXAdapter) -> None:
        """remove_node also removes all edges connected to the node."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        adapter.remove_node("C001")

        # Edge should be gone
        assert adapter.get_edge("C001", "C002", "SOLIDARITY") is None

    def test_remove_node_raises_keyerror_for_missing(self, adapter: NetworkXAdapter) -> None:
        """remove_node raises KeyError if node does not exist."""
        with pytest.raises(KeyError):
            adapter.remove_node("MISSING")


# =============================================================================
# EDGE CRUD TESTS
# =============================================================================


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterAddEdge:
    """Test NetworkXAdapter.add_edge method."""

    def test_add_edge_creates_edge(self, adapter: NetworkXAdapter) -> None:
        """add_edge creates a directed edge in the graph."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert edge is not None
        assert edge.source_id == "C001"
        assert edge.target_id == "C002"
        assert edge.edge_type == "SOLIDARITY"

    def test_add_edge_default_weight(self, adapter: NetworkXAdapter) -> None:
        """add_edge defaults weight to 1.0."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert edge is not None
        assert edge.weight == 1.0

    def test_add_edge_custom_weight(self, adapter: NetworkXAdapter) -> None:
        """add_edge accepts custom weight."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY", weight=0.75)

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert edge is not None
        assert edge.weight == 0.75

    def test_add_edge_stores_attributes(self, adapter: NetworkXAdapter) -> None:
        """add_edge stores arbitrary attributes."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "EXPLOITATION", tension=0.5, value_flow=100.0)

        edge = adapter.get_edge("C001", "C002", "EXPLOITATION")
        assert edge is not None
        assert edge.attributes["tension"] == 0.5
        assert edge.attributes["value_flow"] == 100.0


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterGetEdge:
    """Test NetworkXAdapter.get_edge method."""

    def test_get_edge_returns_graphedge(self, adapter: NetworkXAdapter) -> None:
        """get_edge returns GraphEdge model."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert isinstance(edge, GraphEdge)

    def test_get_edge_returns_none_for_missing_edge(self, adapter: NetworkXAdapter) -> None:
        """get_edge returns None if edge does not exist."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert edge is None

    def test_get_edge_returns_none_for_wrong_type(self, adapter: NetworkXAdapter) -> None:
        """get_edge returns None if edge exists but type doesn't match."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        edge = adapter.get_edge("C001", "C002", "EXPLOITATION")
        assert edge is None

    def test_get_edge_excludes_internal_attributes(self, adapter: NetworkXAdapter) -> None:
        """get_edge excludes internal attributes like _edge_type."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert edge is not None
        assert "_edge_type" not in edge.attributes


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterUpdateEdge:
    """Test NetworkXAdapter.update_edge method."""

    def test_update_edge_modifies_attributes(self, adapter: NetworkXAdapter) -> None:
        """update_edge modifies existing edge attributes."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "EXPLOITATION", tension=0.3)

        adapter.update_edge("C001", "C002", "EXPLOITATION", tension=0.8)

        edge = adapter.get_edge("C001", "C002", "EXPLOITATION")
        assert edge is not None
        assert edge.attributes["tension"] == 0.8

    def test_update_edge_modifies_weight(self, adapter: NetworkXAdapter) -> None:
        """update_edge can modify edge weight."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY", weight=0.5)

        adapter.update_edge("C001", "C002", "SOLIDARITY", weight=0.9)

        edge = adapter.get_edge("C001", "C002", "SOLIDARITY")
        assert edge is not None
        assert edge.weight == 0.9

    def test_update_edge_raises_keyerror_for_missing(self, adapter: NetworkXAdapter) -> None:
        """update_edge raises KeyError if edge does not exist."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")

        with pytest.raises(KeyError):
            adapter.update_edge("C001", "C002", "SOLIDARITY", tension=0.5)


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterRemoveEdge:
    """Test NetworkXAdapter.remove_edge method."""

    def test_remove_edge_deletes_edge(self, adapter: NetworkXAdapter) -> None:
        """remove_edge deletes the edge from graph."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        adapter.remove_edge("C001", "C002", "SOLIDARITY")

        assert adapter.get_edge("C001", "C002", "SOLIDARITY") is None

    def test_remove_edge_preserves_nodes(self, adapter: NetworkXAdapter) -> None:
        """remove_edge does not delete connected nodes."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        adapter.add_edge("C001", "C002", "SOLIDARITY")

        adapter.remove_edge("C001", "C002", "SOLIDARITY")

        assert adapter.get_node("C001") is not None
        assert adapter.get_node("C002") is not None

    def test_remove_edge_raises_keyerror_for_missing(self, adapter: NetworkXAdapter) -> None:
        """remove_edge raises KeyError if edge does not exist."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")

        with pytest.raises(KeyError):
            adapter.remove_edge("C001", "C002", "SOLIDARITY")


# =============================================================================
# TRAVERSAL TESTS
# =============================================================================


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterGetNeighborhood:
    """Test NetworkXAdapter.get_neighborhood method."""

    def test_get_neighborhood_returns_immediate_neighbors(
        self, populated_adapter: NetworkXAdapter
    ) -> None:
        """get_neighborhood with radius=1 returns immediate neighbors."""
        neighborhood = populated_adapter.get_neighborhood("C001", radius=1)

        # Should include C001 (center) and C002, C003 (neighbors)
        node_ids = {n.id for n in neighborhood.nodes()}
        assert "C001" in node_ids
        assert "C002" in node_ids
        assert "C003" in node_ids
        assert "C004" not in node_ids  # 2 hops away

    def test_get_neighborhood_respects_radius(self, populated_adapter: NetworkXAdapter) -> None:
        """get_neighborhood respects radius parameter."""
        neighborhood = populated_adapter.get_neighborhood("C001", radius=2)

        # Should now include C004 (2 hops)
        node_ids = {n.id for n in neighborhood.nodes()}
        assert "C004" in node_ids

    def test_get_neighborhood_filters_by_edge_type(
        self, populated_adapter: NetworkXAdapter
    ) -> None:
        """get_neighborhood filters edges by type."""
        neighborhood = populated_adapter.get_neighborhood(
            "C001", radius=2, edge_types={"SOLIDARITY"}
        )

        # Should NOT reach C004 (connected via EXPLOITATION)
        node_ids = {n.id for n in neighborhood.nodes()}
        assert "C001" in node_ids
        assert "C002" in node_ids
        assert "C003" in node_ids
        assert "C004" not in node_ids

    def test_get_neighborhood_direction_out(self, populated_adapter: NetworkXAdapter) -> None:
        """get_neighborhood with direction='out' follows outgoing edges only."""
        neighborhood = populated_adapter.get_neighborhood("C001", radius=1, direction="out")

        node_ids = {n.id for n in neighborhood.nodes()}
        assert "C002" in node_ids  # Outgoing from C001
        assert "C003" in node_ids  # Outgoing from C001

    def test_get_neighborhood_raises_keyerror_for_missing(self, adapter: NetworkXAdapter) -> None:
        """get_neighborhood raises KeyError if node does not exist."""
        with pytest.raises(KeyError):
            adapter.get_neighborhood("MISSING")


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterShortestPath:
    """Test NetworkXAdapter.shortest_path method."""

    def test_shortest_path_returns_path(self, populated_adapter: NetworkXAdapter) -> None:
        """shortest_path returns list of node IDs."""
        path = populated_adapter.shortest_path("C001", "C004")

        assert path is not None
        assert path[0] == "C001"
        assert path[-1] == "C004"

    def test_shortest_path_returns_none_for_no_path(self, adapter: NetworkXAdapter) -> None:
        """shortest_path returns None when no path exists."""
        adapter.add_node("C001", "social_class")
        adapter.add_node("C002", "social_class")
        # No edge between them

        path = adapter.shortest_path("C001", "C002")
        assert path is None

    def test_shortest_path_filters_by_edge_type(self, populated_adapter: NetworkXAdapter) -> None:
        """shortest_path respects edge_types filter."""
        # Path via SOLIDARITY only should not reach C004
        path = populated_adapter.shortest_path("C001", "C004", edge_types={"SOLIDARITY"})
        assert path is None


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterExecuteTraversal:
    """Test NetworkXAdapter.execute_traversal method."""

    def test_execute_traversal_bfs(self, populated_adapter: NetworkXAdapter) -> None:
        """execute_traversal with query_type='bfs' performs BFS."""
        query = TraversalQuery(
            query_type="bfs",
            start_nodes=["C001"],
            max_depth=2,
        )

        result = populated_adapter.execute_traversal(query)

        assert isinstance(result, TraversalResult)
        assert "C001" in result.nodes
        assert "C002" in result.nodes

    def test_execute_traversal_connected_components(self, adapter: NetworkXAdapter) -> None:
        """execute_traversal with query_type='connected_components' finds components."""
        # Create two disconnected components
        adapter.add_node("A1", "social_class")
        adapter.add_node("A2", "social_class")
        adapter.add_edge("A1", "A2", "SOLIDARITY")

        adapter.add_node("B1", "social_class")
        adapter.add_node("B2", "social_class")
        adapter.add_edge("B1", "B2", "SOLIDARITY")

        query = TraversalQuery(
            query_type="connected_components",
            collect=["components", "component_sizes"],
        )

        result = adapter.execute_traversal(query)

        assert len(result.components) == 2
        assert result.component_sizes == [2, 2]

    def test_execute_traversal_percolation(self, populated_adapter: NetworkXAdapter) -> None:
        """execute_traversal with query_type='percolation' computes percolation metrics."""
        query = TraversalQuery(
            query_type="percolation",
            edge_filter=EdgeFilter(edge_types={"SOLIDARITY"}),
            collect=["component_sizes"],
        )

        result = populated_adapter.execute_traversal(query)

        # Should find solidarity component size
        assert len(result.component_sizes) > 0

    def test_execute_traversal_raises_for_invalid_type(self, adapter: NetworkXAdapter) -> None:
        """execute_traversal raises ValueError for unsupported query type."""
        query = TraversalQuery(query_type="invalid_type")  # type: ignore[arg-type]

        with pytest.raises(ValueError):
            adapter.execute_traversal(query)


# =============================================================================
# SET OPERATION TESTS
# =============================================================================


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterQueryNodes:
    """Test NetworkXAdapter.query_nodes method."""

    def test_query_nodes_returns_iterator(self, populated_adapter: NetworkXAdapter) -> None:
        """query_nodes returns an Iterator of GraphNode."""
        result = populated_adapter.query_nodes()
        assert hasattr(result, "__iter__")

        nodes = list(result)
        assert all(isinstance(n, GraphNode) for n in nodes)

    def test_query_nodes_filters_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """query_nodes filters by node_type."""
        nodes = list(populated_adapter.query_nodes(node_type="territory"))

        assert len(nodes) == 2
        assert all(n.node_type == "territory" for n in nodes)

    def test_query_nodes_filters_by_attributes(self, populated_adapter: NetworkXAdapter) -> None:
        """query_nodes filters by attribute equality."""
        nodes = list(
            populated_adapter.query_nodes(
                node_type="social_class",
                attributes={"wealth": 100.0},
            )
        )

        assert len(nodes) == 1
        assert nodes[0].id == "C001"

    def test_query_nodes_filters_by_predicate(self, populated_adapter: NetworkXAdapter) -> None:
        """query_nodes filters by predicate function."""
        nodes = list(
            populated_adapter.query_nodes(
                predicate=lambda n: n.wealth > 100.0,
            )
        )

        assert len(nodes) == 1
        assert nodes[0].id == "C004"


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterQueryEdges:
    """Test NetworkXAdapter.query_edges method."""

    def test_query_edges_returns_iterator(self, populated_adapter: NetworkXAdapter) -> None:
        """query_edges returns an Iterator of GraphEdge."""
        result = populated_adapter.query_edges()
        assert hasattr(result, "__iter__")

        edges = list(result)
        assert all(isinstance(e, GraphEdge) for e in edges)

    def test_query_edges_filters_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """query_edges filters by edge_type."""
        edges = list(populated_adapter.query_edges(edge_type="SOLIDARITY"))

        assert len(edges) == 2
        assert all(e.edge_type == "SOLIDARITY" for e in edges)

    def test_query_edges_filters_by_weight_range(self, populated_adapter: NetworkXAdapter) -> None:
        """query_edges filters by weight range."""
        edges = list(
            populated_adapter.query_edges(
                min_weight=0.7,
                max_weight=0.9,
            )
        )

        assert all(0.7 <= e.weight <= 0.9 for e in edges)


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterCountNodes:
    """Test NetworkXAdapter.count_nodes method."""

    def test_count_nodes_returns_total(self, populated_adapter: NetworkXAdapter) -> None:
        """count_nodes with no filter returns total node count."""
        count = populated_adapter.count_nodes()
        assert count == 6  # 4 social_class + 2 territory

    def test_count_nodes_filters_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """count_nodes filters by node_type."""
        count = populated_adapter.count_nodes(node_type="social_class")
        assert count == 4

    def test_count_nodes_empty_graph(self, adapter: NetworkXAdapter) -> None:
        """count_nodes returns 0 for empty graph."""
        count = adapter.count_nodes()
        assert count == 0


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterCountEdges:
    """Test NetworkXAdapter.count_edges method."""

    def test_count_edges_returns_total(self, populated_adapter: NetworkXAdapter) -> None:
        """count_edges with no filter returns total edge count."""
        count = populated_adapter.count_edges()
        assert count == 4

    def test_count_edges_filters_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """count_edges filters by edge_type."""
        count = populated_adapter.count_edges(edge_type="SOLIDARITY")
        assert count == 2

    def test_count_edges_empty_graph(self, adapter: NetworkXAdapter) -> None:
        """count_edges returns 0 for empty graph."""
        count = adapter.count_edges()
        assert count == 0


@pytest.mark.topology
@pytest.mark.red_phase
class TestNetworkXAdapterAggregate:
    """Test NetworkXAdapter.aggregate method."""

    def test_aggregate_count_nodes_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """aggregate counts nodes grouped by type."""
        result = populated_adapter.aggregate("nodes", group_by="type")

        assert result["social_class"] == 4
        assert result["territory"] == 2

    def test_aggregate_sum_wealth_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """aggregate sums attribute grouped by type."""
        result = populated_adapter.aggregate(
            "nodes",
            group_by="type",
            agg_func="sum",
            agg_attr="wealth",
        )

        # C001=100 + C002=80 + C003=50 + C004=500 = 730
        assert result["social_class"] == 730.0

    def test_aggregate_avg_wealth(self, populated_adapter: NetworkXAdapter) -> None:
        """aggregate computes average."""
        result = populated_adapter.aggregate(
            "nodes",
            group_by="type",
            agg_func="avg",
            agg_attr="wealth",
        )

        # (100 + 80 + 50 + 500) / 4 = 182.5
        assert result["social_class"] == pytest.approx(182.5)

    def test_aggregate_edges_by_type(self, populated_adapter: NetworkXAdapter) -> None:
        """aggregate counts edges grouped by type."""
        result = populated_adapter.aggregate("edges", group_by="type")

        assert result["SOLIDARITY"] == 2
        assert result["EXPLOITATION"] == 1
        assert result["ADJACENCY"] == 1
