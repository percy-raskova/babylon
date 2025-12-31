"""Tests for babylon.models.graph - Graph abstraction layer data models.

TDD Red Phase: These tests define the contract for the Graph Bridge data models.
The tests WILL FAIL initially because the implementations do not exist yet.
This is the correct Red phase outcome.

Slice 1.7: The Graph Bridge

The graph abstraction layer provides backend-agnostic graph operations.
These data models are the type-safe boundary between Systems and the graph backend:

1. GraphNode - Frozen Pydantic model for node representation
2. GraphEdge - Frozen Pydantic model for edge representation
3. EdgeFilter - Filter specification for edge traversal
4. NodeFilter - Filter specification for node inclusion
5. TraversalQuery - Generic traversal query specification
6. TraversalResult - Result of traversal query execution

Design Principles:
- All models are frozen (immutable) for thread safety
- Models use Pydantic v2 ConfigDict(frozen=True)
- Attributes are stored as dict[str, Any] for flexibility
- Convenience properties for common attributes (wealth, tension, value_flow)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

if TYPE_CHECKING:
    pass

TC = TestConstants

# Attempt to import - will fail until GREEN phase implementation
# Use pytest.importorskip to gracefully handle missing module
_graph_module = pytest.importorskip(
    "babylon.models.graph",
    reason="babylon.models.graph not yet implemented (RED phase)",
)

# Import types from the module after successful import
GraphNode = _graph_module.GraphNode
GraphEdge = _graph_module.GraphEdge
EdgeFilter = _graph_module.EdgeFilter
NodeFilter = _graph_module.NodeFilter
TraversalQuery = _graph_module.TraversalQuery
TraversalResult = _graph_module.TraversalResult

# =============================================================================
# GRAPHNODE TESTS
# =============================================================================


@pytest.mark.math
class TestGraphNodeCreation:
    """Test GraphNode instantiation and validation."""

    def test_graphnode_requires_id(self) -> None:
        """GraphNode must have a non-empty id field.

        The id uniquely identifies the node in the graph.
        """
        with pytest.raises(ValidationError):
            GraphNode(node_type="social_class")  # type: ignore[call-arg]

    def test_graphnode_requires_node_type(self) -> None:
        """GraphNode must have a non-empty node_type field.

        The node_type is the discriminator for polymorphism.
        """
        with pytest.raises(ValidationError):
            GraphNode(id="C001")  # type: ignore[call-arg]

    def test_graphnode_rejects_empty_id(self) -> None:
        """GraphNode rejects empty string as id.

        Empty IDs would break graph lookups.
        """
        with pytest.raises(ValidationError):
            GraphNode(id="", node_type="social_class")

    def test_graphnode_rejects_empty_node_type(self) -> None:
        """GraphNode rejects empty string as node_type.

        Empty node_type would break type-based queries.
        """
        with pytest.raises(ValidationError):
            GraphNode(id="C001", node_type="")

    def test_graphnode_creates_with_required_fields(self) -> None:
        """GraphNode can be created with just id and node_type.

        Attributes default to empty dict.
        """
        node = GraphNode(id="C001", node_type="social_class")
        assert node.id == "C001"
        assert node.node_type == "social_class"
        assert node.attributes == {}

    def test_graphnode_accepts_attributes_dict(self) -> None:
        """GraphNode accepts arbitrary attributes dict.

        Attributes are type-specific and validated by application logic.
        """
        attrs = {
            "wealth": TC.Wealth.SIGNIFICANT,
            "consciousness": TC.Consciousness.NEUTRAL_IDENTITY,
            "name": "Workers",
        }
        node = GraphNode(id="C001", node_type="social_class", attributes=attrs)
        assert node.attributes == attrs

    def test_graphnode_is_frozen(self) -> None:
        """GraphNode instances are immutable (frozen).

        Immutability ensures thread safety and prevents accidental mutation.
        """
        node = GraphNode(id="C001", node_type="social_class")
        with pytest.raises(ValidationError):
            node.id = "C002"  # type: ignore[misc]


@pytest.mark.math
class TestGraphNodeProperties:
    """Test GraphNode convenience properties."""

    def test_graphnode_get_attr_returns_value(self) -> None:
        """get_attr returns attribute value when present.

        Convenience method for safe attribute access.
        """
        node = GraphNode(
            id="C001",
            node_type="social_class",
            attributes={"wealth": TC.Wealth.SIGNIFICANT},
        )
        assert node.get_attr("wealth") == TC.Wealth.SIGNIFICANT

    def test_graphnode_get_attr_returns_default(self) -> None:
        """get_attr returns default when attribute not present.

        Default is None if not specified.
        """
        node = GraphNode(id="C001", node_type="social_class")
        assert node.get_attr("missing") is None
        assert node.get_attr("missing", 0.0) == 0.0

    def test_graphnode_wealth_property(self) -> None:
        """wealth property returns wealth from attributes.

        Convenience accessor for common attribute.
        """
        node = GraphNode(
            id="C001",
            node_type="social_class",
            attributes={"wealth": 250.5},
        )
        assert node.wealth == 250.5

    def test_graphnode_wealth_property_defaults_to_zero(self) -> None:
        """wealth property returns 0.0 when not present.

        Default ensures safe numeric operations.
        """
        node = GraphNode(id="C001", node_type="social_class")
        assert node.wealth == 0.0


@pytest.mark.math
class TestGraphNodeSerialization:
    """Test GraphNode JSON serialization."""

    def test_graphnode_serializes_to_json(self) -> None:
        """GraphNode serializes to JSON correctly.

        Required for network transfer and persistence.
        """
        node = GraphNode(
            id="C001",
            node_type="social_class",
            attributes={"wealth": TC.Wealth.SIGNIFICANT},
        )
        json_str = node.model_dump_json()
        assert "C001" in json_str
        assert "social_class" in json_str

    def test_graphnode_round_trip(self) -> None:
        """GraphNode survives JSON round-trip.

        Validates serialization/deserialization integrity.
        """
        original = GraphNode(
            id="C001",
            node_type="social_class",
            attributes={"wealth": TC.Wealth.SIGNIFICANT, "name": "Workers"},
        )
        json_str = original.model_dump_json()
        restored = GraphNode.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.node_type == original.node_type
        assert restored.attributes == original.attributes


# =============================================================================
# GRAPHEDGE TESTS
# =============================================================================


@pytest.mark.math
class TestGraphEdgeCreation:
    """Test GraphEdge instantiation and validation."""

    def test_graphedge_requires_source_id(self) -> None:
        """GraphEdge must have a source_id field.

        The source is the origin of the directed edge.
        """
        with pytest.raises(ValidationError):
            GraphEdge(target_id="C002", edge_type="SOLIDARITY")  # type: ignore[call-arg]

    def test_graphedge_requires_target_id(self) -> None:
        """GraphEdge must have a target_id field.

        The target is the destination of the directed edge.
        """
        with pytest.raises(ValidationError):
            GraphEdge(source_id="C001", edge_type="SOLIDARITY")  # type: ignore[call-arg]

    def test_graphedge_requires_edge_type(self) -> None:
        """GraphEdge must have an edge_type field.

        The edge_type categorizes the relationship.
        """
        with pytest.raises(ValidationError):
            GraphEdge(source_id="C001", target_id="C002")  # type: ignore[call-arg]

    def test_graphedge_rejects_empty_source_id(self) -> None:
        """GraphEdge rejects empty string as source_id."""
        with pytest.raises(ValidationError):
            GraphEdge(source_id="", target_id="C002", edge_type="SOLIDARITY")

    def test_graphedge_rejects_empty_target_id(self) -> None:
        """GraphEdge rejects empty string as target_id."""
        with pytest.raises(ValidationError):
            GraphEdge(source_id="C001", target_id="", edge_type="SOLIDARITY")

    def test_graphedge_rejects_empty_edge_type(self) -> None:
        """GraphEdge rejects empty string as edge_type."""
        with pytest.raises(ValidationError):
            GraphEdge(source_id="C001", target_id="C002", edge_type="")

    def test_graphedge_creates_with_required_fields(self) -> None:
        """GraphEdge can be created with required fields.

        Weight defaults to 1.0, attributes to empty dict.
        """
        edge = GraphEdge(source_id="C001", target_id="C002", edge_type="SOLIDARITY")
        assert edge.source_id == "C001"
        assert edge.target_id == "C002"
        assert edge.edge_type == "SOLIDARITY"
        assert edge.weight == 1.0
        assert edge.attributes == {}

    def test_graphedge_accepts_weight(self) -> None:
        """GraphEdge accepts custom weight value."""
        edge = GraphEdge(
            source_id="C001",
            target_id="C002",
            edge_type="SOLIDARITY",
            weight=0.75,
        )
        assert edge.weight == 0.75

    def test_graphedge_accepts_attributes(self) -> None:
        """GraphEdge accepts arbitrary attributes dict."""
        attrs = {"tension": TC.Probability.MIDPOINT, "value_flow": TC.Wealth.SIGNIFICANT}
        edge = GraphEdge(
            source_id="C001",
            target_id="C002",
            edge_type="EXPLOITATION",
            attributes=attrs,
        )
        assert edge.attributes == attrs

    def test_graphedge_is_frozen(self) -> None:
        """GraphEdge instances are immutable (frozen)."""
        edge = GraphEdge(source_id="C001", target_id="C002", edge_type="SOLIDARITY")
        with pytest.raises(ValidationError):
            edge.source_id = "C003"  # type: ignore[misc]


@pytest.mark.math
class TestGraphEdgeProperties:
    """Test GraphEdge convenience properties."""

    def test_graphedge_tension_property(self) -> None:
        """tension property returns tension from attributes."""
        edge = GraphEdge(
            source_id="C001",
            target_id="C002",
            edge_type="EXPLOITATION",
            attributes={"tension": TC.Probability.HIGH},
        )
        assert edge.tension == TC.Probability.HIGH

    def test_graphedge_tension_defaults_to_zero(self) -> None:
        """tension property returns 0.0 when not present."""
        edge = GraphEdge(source_id="C001", target_id="C002", edge_type="EXPLOITATION")
        assert edge.tension == 0.0

    def test_graphedge_value_flow_property(self) -> None:
        """value_flow property returns value_flow from attributes."""
        edge = GraphEdge(
            source_id="C001",
            target_id="C002",
            edge_type="EXPLOITATION",
            attributes={"value_flow": TC.Wealth.HIGH},
        )
        assert edge.value_flow == TC.Wealth.HIGH

    def test_graphedge_value_flow_defaults_to_zero(self) -> None:
        """value_flow property returns 0.0 when not present."""
        edge = GraphEdge(source_id="C001", target_id="C002", edge_type="EXPLOITATION")
        assert edge.value_flow == 0.0


# =============================================================================
# EDGEFILTER TESTS
# =============================================================================


@pytest.mark.math
class TestEdgeFilter:
    """Test EdgeFilter specification model."""

    def test_edgefilter_defaults_to_no_filter(self) -> None:
        """EdgeFilter with no parameters matches all edges."""
        f = EdgeFilter()
        assert f.edge_types is None
        assert f.min_weight is None
        assert f.max_weight is None

    def test_edgefilter_accepts_edge_types(self) -> None:
        """EdgeFilter can filter by edge type set."""
        f = EdgeFilter(edge_types={"SOLIDARITY", "EXPLOITATION"})
        assert f.edge_types == {"SOLIDARITY", "EXPLOITATION"}

    def test_edgefilter_accepts_min_weight(self) -> None:
        """EdgeFilter can filter by minimum weight."""
        f = EdgeFilter(min_weight=TC.Probability.MIDPOINT)
        assert f.min_weight == TC.Probability.MIDPOINT

    def test_edgefilter_accepts_max_weight(self) -> None:
        """EdgeFilter can filter by maximum weight."""
        f = EdgeFilter(max_weight=TC.Probability.EXTREME)
        assert f.max_weight == TC.Probability.EXTREME

    def test_edgefilter_accepts_weight_range(self) -> None:
        """EdgeFilter can filter by weight range."""
        f = EdgeFilter(min_weight=TC.Probability.MODERATE, max_weight=TC.Probability.VERY_HIGH)
        assert f.min_weight == TC.Probability.MODERATE
        assert f.max_weight == TC.Probability.VERY_HIGH


# =============================================================================
# NODEFILTER TESTS
# =============================================================================


@pytest.mark.math
class TestNodeFilter:
    """Test NodeFilter specification model."""

    def test_nodefilter_defaults_to_no_filter(self) -> None:
        """NodeFilter with no parameters matches all nodes."""
        f = NodeFilter()
        assert f.node_types is None
        assert f.attribute_predicates is None

    def test_nodefilter_accepts_node_types(self) -> None:
        """NodeFilter can filter by node type set."""
        f = NodeFilter(node_types={"social_class", "territory"})
        assert f.node_types == {"social_class", "territory"}

    def test_nodefilter_accepts_attribute_predicates(self) -> None:
        """NodeFilter can filter by attribute predicates."""
        predicates = {
            "wealth": TC.Wealth.SIGNIFICANT,
            "consciousness": TC.Consciousness.NEUTRAL_IDENTITY,
        }
        f = NodeFilter(attribute_predicates=predicates)
        assert f.attribute_predicates == predicates


# =============================================================================
# TRAVERSALQUERY TESTS
# =============================================================================


@pytest.mark.math
class TestTraversalQueryCreation:
    """Test TraversalQuery instantiation and validation."""

    def test_traversalquery_requires_query_type(self) -> None:
        """TraversalQuery must have a query_type field.

        The query_type determines the algorithm used.
        """
        with pytest.raises(ValidationError):
            TraversalQuery()  # type: ignore[call-arg]

    def test_traversalquery_accepts_valid_query_types(self) -> None:
        """TraversalQuery accepts all valid query types.

        Valid types: bfs, dfs, shortest_path, connected_components, percolation, reachability
        """
        valid_types = [
            "bfs",
            "dfs",
            "shortest_path",
            "connected_components",
            "percolation",
            "reachability",
        ]
        for qtype in valid_types:
            query = TraversalQuery(query_type=qtype)  # type: ignore[arg-type]
            assert query.query_type == qtype

    def test_traversalquery_rejects_invalid_query_type(self) -> None:
        """TraversalQuery rejects invalid query types."""
        with pytest.raises(ValidationError):
            TraversalQuery(query_type="invalid_type")  # type: ignore[arg-type]

    def test_traversalquery_defaults(self) -> None:
        """TraversalQuery has sensible defaults.

        start_nodes, target_nodes, filters default to None.
        collect defaults to ['nodes'].
        """
        query = TraversalQuery(query_type="bfs")
        assert query.start_nodes is None
        assert query.target_nodes is None
        assert query.edge_filter is None
        assert query.node_filter is None
        assert query.max_depth is None
        assert query.collect == ["nodes"]


@pytest.mark.math
class TestTraversalQueryParameters:
    """Test TraversalQuery parameter handling."""

    def test_traversalquery_accepts_start_nodes(self) -> None:
        """TraversalQuery accepts start_nodes list."""
        query = TraversalQuery(query_type="bfs", start_nodes=["C001", "C002"])
        assert query.start_nodes == ["C001", "C002"]

    def test_traversalquery_accepts_target_nodes(self) -> None:
        """TraversalQuery accepts target_nodes list."""
        query = TraversalQuery(
            query_type="shortest_path",
            start_nodes=["C001"],
            target_nodes=["C005"],
        )
        assert query.target_nodes == ["C005"]

    def test_traversalquery_accepts_edge_filter(self) -> None:
        """TraversalQuery accepts EdgeFilter."""
        ef = EdgeFilter(edge_types={"SOLIDARITY"})
        query = TraversalQuery(query_type="bfs", edge_filter=ef)
        assert query.edge_filter is not None
        assert query.edge_filter.edge_types == {"SOLIDARITY"}

    def test_traversalquery_accepts_node_filter(self) -> None:
        """TraversalQuery accepts NodeFilter."""
        nf = NodeFilter(node_types={"social_class"})
        query = TraversalQuery(query_type="connected_components", node_filter=nf)
        assert query.node_filter is not None
        assert query.node_filter.node_types == {"social_class"}

    def test_traversalquery_accepts_max_depth(self) -> None:
        """TraversalQuery accepts max_depth limit."""
        query = TraversalQuery(query_type="bfs", max_depth=3)
        assert query.max_depth == 3

    def test_traversalquery_accepts_collect_options(self) -> None:
        """TraversalQuery accepts collect specification.

        Valid options: nodes, edges, paths, component_sizes
        """
        query = TraversalQuery(
            query_type="connected_components",
            collect=["nodes", "edges", "component_sizes"],
        )
        assert "nodes" in query.collect
        assert "component_sizes" in query.collect


# =============================================================================
# TRAVERSALRESULT TESTS
# =============================================================================


@pytest.mark.math
class TestTraversalResultCreation:
    """Test TraversalResult instantiation."""

    def test_traversalresult_creates_with_defaults(self) -> None:
        """TraversalResult can be created with all defaults.

        Empty result is valid for queries that find nothing.
        """
        result = TraversalResult()
        assert result.nodes == []
        assert result.edges == []
        assert result.paths == []
        assert result.components == []
        assert result.component_sizes == []
        assert result.metadata == {}

    def test_traversalresult_accepts_nodes(self) -> None:
        """TraversalResult accepts list of node IDs."""
        result = TraversalResult(nodes=["C001", "C002", "C003"])
        assert result.nodes == ["C001", "C002", "C003"]

    def test_traversalresult_accepts_edges(self) -> None:
        """TraversalResult accepts list of edge tuples."""
        edges = [("C001", "C002", "SOLIDARITY"), ("C002", "C003", "SOLIDARITY")]
        result = TraversalResult(edges=edges)
        assert result.edges == edges

    def test_traversalresult_accepts_paths(self) -> None:
        """TraversalResult accepts list of path lists."""
        paths = [["C001", "C002", "C003"], ["C001", "C004", "C003"]]
        result = TraversalResult(paths=paths)
        assert result.paths == paths

    def test_traversalresult_accepts_components(self) -> None:
        """TraversalResult accepts list of component lists."""
        components = [["C001", "C002"], ["C003", "C004", "C005"]]
        result = TraversalResult(components=components)
        assert result.components == components

    def test_traversalresult_accepts_component_sizes(self) -> None:
        """TraversalResult accepts sorted list of component sizes."""
        sizes = [5, 3, 2]  # Sorted descending
        result = TraversalResult(component_sizes=sizes)
        assert result.component_sizes == sizes

    def test_traversalresult_accepts_metadata(self) -> None:
        """TraversalResult accepts metadata dict."""
        meta = {"algorithm": "bfs", "visited_count": 10}
        result = TraversalResult(metadata=meta)
        assert result.metadata == meta


@pytest.mark.math
class TestTraversalResultProperties:
    """Test TraversalResult convenience properties."""

    def test_largest_component_size_returns_first(self) -> None:
        """largest_component_size returns first (largest) component size.

        component_sizes is sorted descending by convention.
        """
        result = TraversalResult(component_sizes=[10, 5, 3, 2])
        assert result.largest_component_size == 10

    def test_largest_component_size_returns_zero_when_empty(self) -> None:
        """largest_component_size returns 0 when no components."""
        result = TraversalResult()
        assert result.largest_component_size == 0

    def test_percolation_ratio_computes_correctly(self) -> None:
        """percolation_ratio = largest_component / total_nodes.

        This is the key metric for phase transition detection.
        """
        # Total = 10 + 5 + 3 + 2 = 20, largest = 10
        # Ratio = 10/20 = 0.5
        result = TraversalResult(component_sizes=[10, 5, 3, 2])
        assert result.percolation_ratio == pytest.approx(0.5)

    def test_percolation_ratio_returns_zero_when_empty(self) -> None:
        """percolation_ratio returns 0.0 when no components."""
        result = TraversalResult()
        assert result.percolation_ratio == 0.0

    def test_percolation_ratio_is_one_for_single_component(self) -> None:
        """percolation_ratio is 1.0 when all nodes in one component.

        Full percolation means complete connectivity.
        """
        result = TraversalResult(component_sizes=[15])
        assert result.percolation_ratio == 1.0
