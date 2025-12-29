"""TDD tests for QueryMixin extraction.

RED phase: These tests define the expected behavior of the extracted mixin.
"""

from __future__ import annotations

import pytest

# Import will fail until we implement the mixin (RED)
try:
    from babylon.engine.adapters.query_mixin import QueryMixin
except ImportError:
    QueryMixin = None  # type: ignore[misc, assignment]

import networkx as nx


class TestQueryMixinExists:
    """RED: Verify the mixin exists and can be imported."""

    def test_query_mixin_can_be_imported(self) -> None:
        """The QueryMixin should be importable."""
        assert QueryMixin is not None, "QueryMixin not yet implemented"


@pytest.fixture
def graph_with_data() -> nx.DiGraph[str]:
    """Create a test graph with nodes and edges."""
    g: nx.DiGraph[str] = nx.DiGraph()
    # Add nodes with types and attributes
    g.add_node("C001", _node_type="social_class", wealth=100.0, consciousness=0.3)
    g.add_node("C002", _node_type="social_class", wealth=50.0, consciousness=0.5)
    g.add_node("C003", _node_type="social_class", wealth=200.0, consciousness=0.1)
    g.add_node("T001", _node_type="territory", heat=0.5)
    g.add_node("T002", _node_type="territory", heat=0.8)
    # Add edges
    g.add_edge("C001", "C002", _edge_type="SOLIDARITY", weight=0.8)
    g.add_edge("C001", "C003", _edge_type="EXPLOITATION", weight=0.5)
    g.add_edge("C002", "C003", _edge_type="EXPLOITATION", weight=0.3)
    g.add_edge("T001", "T002", _edge_type="ADJACENCY", weight=1.0)
    return g


@pytest.mark.skipif(QueryMixin is None, reason="QueryMixin not yet implemented")
class TestQueryMixinNodeQueries:
    """Tests for node query functionality."""

    def test_query_nodes_returns_iterator(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_nodes should return an iterator."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.query_nodes()
        assert hasattr(result, "__iter__")
        nodes = list(result)
        assert len(nodes) == 5

    def test_query_nodes_filters_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_nodes should filter by node_type."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        nodes = list(adapter.query_nodes(node_type="social_class"))
        assert len(nodes) == 3
        assert all(n.node_type == "social_class" for n in nodes)

    def test_query_nodes_filters_by_attributes(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_nodes should filter by attribute equality."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        nodes = list(adapter.query_nodes(attributes={"wealth": 100.0}))
        assert len(nodes) == 1
        assert nodes[0].id == "C001"

    def test_query_nodes_filters_by_predicate(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_nodes should filter by custom predicate."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        nodes = list(adapter.query_nodes(predicate=lambda n: n.attributes.get("wealth", 0) > 75))
        assert len(nodes) == 2  # C001 (100) and C003 (200)

    def test_count_nodes_returns_total(self, graph_with_data: nx.DiGraph[str]) -> None:
        """count_nodes should return total node count."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        assert adapter.count_nodes() == 5

    def test_count_nodes_filters_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """count_nodes should filter by node_type."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        assert adapter.count_nodes(node_type="social_class") == 3
        assert adapter.count_nodes(node_type="territory") == 2


@pytest.mark.skipif(QueryMixin is None, reason="QueryMixin not yet implemented")
class TestQueryMixinEdgeQueries:
    """Tests for edge query functionality."""

    def test_query_edges_returns_iterator(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_edges should return an iterator."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.query_edges()
        assert hasattr(result, "__iter__")
        edges = list(result)
        assert len(edges) == 4

    def test_query_edges_filters_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_edges should filter by edge_type."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        edges = list(adapter.query_edges(edge_type="EXPLOITATION"))
        assert len(edges) == 2
        assert all(e.edge_type == "EXPLOITATION" for e in edges)

    def test_query_edges_filters_by_weight_range(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_edges should filter by weight range."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        edges = list(adapter.query_edges(min_weight=0.5, max_weight=0.9))
        assert len(edges) == 2  # SOLIDARITY (0.8) and EXPLOITATION (0.5)

    def test_query_edges_filters_by_predicate(self, graph_with_data: nx.DiGraph[str]) -> None:
        """query_edges should filter by custom predicate."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        edges = list(adapter.query_edges(predicate=lambda e: e.weight >= 1.0))
        assert len(edges) == 1  # ADJACENCY (1.0)

    def test_count_edges_returns_total(self, graph_with_data: nx.DiGraph[str]) -> None:
        """count_edges should return total edge count."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        assert adapter.count_edges() == 4

    def test_count_edges_filters_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """count_edges should filter by edge_type."""

        class TestAdapter(QueryMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        assert adapter.count_edges(edge_type="EXPLOITATION") == 2
        assert adapter.count_edges(edge_type="SOLIDARITY") == 1
        assert adapter.count_edges(edge_type="ADJACENCY") == 1
