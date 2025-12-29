"""TDD tests for AggregationMixin extraction.

RED phase: These tests define the expected behavior of the extracted mixin.
"""

from __future__ import annotations

import pytest

# Import will fail until we implement the mixin (RED)
try:
    from babylon.engine.adapters.aggregation_mixin import AggregationMixin
except ImportError:
    AggregationMixin = None  # type: ignore[misc, assignment]

import networkx as nx


class TestAggregationMixinExists:
    """RED: Verify the mixin exists and can be imported."""

    def test_aggregation_mixin_can_be_imported(self) -> None:
        """The AggregationMixin should be importable."""
        assert AggregationMixin is not None, "AggregationMixin not yet implemented"


@pytest.fixture
def graph_with_data() -> nx.DiGraph[str]:
    """Create a test graph with nodes and edges."""
    g: nx.DiGraph[str] = nx.DiGraph()
    # Add nodes with types and wealth
    g.add_node("C001", _node_type="social_class", wealth=100.0, consciousness=0.3)
    g.add_node("C002", _node_type="social_class", wealth=50.0, consciousness=0.5)
    g.add_node("C003", _node_type="social_class", wealth=200.0, consciousness=0.1)
    g.add_node("T001", _node_type="territory", heat=0.5)
    # Add edges
    g.add_edge("C001", "C002", _edge_type="SOLIDARITY", weight=0.8)
    g.add_edge("C001", "C003", _edge_type="EXPLOITATION", weight=0.5)
    g.add_edge("C002", "C003", _edge_type="EXPLOITATION", weight=0.3)
    return g


@pytest.mark.skipif(AggregationMixin is None, reason="AggregationMixin not yet implemented")
class TestAggregationMixinNodeAggregation:
    """Tests for node aggregation functionality."""

    def test_aggregate_nodes_count_all(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Count all nodes without grouping."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("nodes", agg_func="count")
        assert result == {"_all": 4.0}

    def test_aggregate_nodes_count_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Count nodes grouped by type."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("nodes", group_by="type", agg_func="count")
        assert result == {"social_class": 3.0, "territory": 1.0}

    def test_aggregate_nodes_sum_wealth_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Sum wealth attribute grouped by type."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("nodes", group_by="type", agg_func="sum", agg_attr="wealth")
        assert result["social_class"] == 350.0  # 100 + 50 + 200
        assert result["territory"] == 0.0  # no wealth attr

    def test_aggregate_nodes_avg_consciousness(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Average consciousness across all social_class nodes."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("nodes", agg_func="avg", agg_attr="consciousness")
        # (0.3 + 0.5 + 0.1 + 0) / 4 = 0.225
        assert abs(result["_all"] - 0.225) < 0.001


@pytest.mark.skipif(AggregationMixin is None, reason="AggregationMixin not yet implemented")
class TestAggregationMixinEdgeAggregation:
    """Tests for edge aggregation functionality."""

    def test_aggregate_edges_count_all(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Count all edges without grouping."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("edges", agg_func="count")
        assert result == {"_all": 3.0}

    def test_aggregate_edges_count_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Count edges grouped by type."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("edges", group_by="type", agg_func="count")
        assert result == {"SOLIDARITY": 1.0, "EXPLOITATION": 2.0}

    def test_aggregate_edges_sum_weight_by_type(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Sum edge weights grouped by type."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("edges", group_by="type", agg_func="sum", agg_attr="weight")
        assert result["SOLIDARITY"] == 0.8
        assert result["EXPLOITATION"] == 0.8  # 0.5 + 0.3

    def test_aggregate_edges_max_weight(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Find max weight across all edges."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("edges", agg_func="max", agg_attr="weight")
        assert result["_all"] == 0.8

    def test_aggregate_edges_min_weight(self, graph_with_data: nx.DiGraph[str]) -> None:
        """Find min weight across all edges."""

        class TestAdapter(AggregationMixin):
            def __init__(self, graph: nx.DiGraph[str]) -> None:
                self._graph = graph

        adapter = TestAdapter(graph_with_data)
        result = adapter.aggregate("edges", agg_func="min", agg_attr="weight")
        assert result["_all"] == 0.3


@pytest.mark.skipif(AggregationMixin is None, reason="AggregationMixin not yet implemented")
class TestAggregationMixinUnifiedImplementation:
    """Tests verifying the unified _aggregate_items implementation."""

    def test_aggregate_items_method_exists(self) -> None:
        """The mixin should have a unified _aggregate_items method."""
        assert hasattr(AggregationMixin, "_aggregate_items")

    def test_apply_agg_func_exists(self) -> None:
        """The mixin should have _apply_agg_func helper."""
        assert hasattr(AggregationMixin, "_apply_agg_func")
