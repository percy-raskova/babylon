"""Tests for weighted Laplacian in FieldDerivativeSystem (Feature 036, T024).

Tests verify:
- Backward compatibility: None = unweighted (all weights 1.0)
- Weighted Laplacian: sum(w * (f(j) - f(i)))
- Zero-weight edge produces no contribution
"""

from __future__ import annotations

from unittest.mock import MagicMock

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.systems.field_derivative import (
    _collect_neighbor_fields,
    _compute_node_derivatives,
)


def _make_graph_protocol(g: nx.DiGraph) -> MagicMock:  # type: ignore[type-arg]
    """Wrap a NetworkX DiGraph in a minimal GraphProtocol mock."""
    from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

    return NetworkXAdapter.wrap(g)


def _make_triangle_graph(
    field_values: dict[str, float],
    edge_weights: dict[tuple[str, str], float] | None = None,
) -> nx.DiGraph:  # type: ignore[type-arg]
    """Create a 3-node triangle graph with contradiction fields.

    Args:
        field_values: node_id -> field value for "exploitation" field.
        edge_weights: (src, tgt) -> weight. If None, no weights.

    Returns:
        NetworkX DiGraph.
    """
    g = BabylonGraph()
    for node_id, val in field_values.items():
        g.add_node(
            node_id,
            _node_type="social_class",
            contradiction_fields={"exploitation": val},
        )

    edges = [("A", "B"), ("B", "A"), ("B", "C"), ("C", "B"), ("A", "C"), ("C", "A")]
    for src, tgt in edges:
        attrs: dict[str, object] = {"edge_type": "SOLIDARITY"}
        if edge_weights is not None:
            key = (src, tgt) if (src, tgt) in edge_weights else (tgt, src)
            if key in edge_weights:
                attrs["infrastructure_weight"] = edge_weights[key]
        g.add_edge(src, tgt, **attrs)

    return g


@pytest.mark.unit
class TestWeightedLaplacian:
    """Tests for weighted Laplacian computation."""

    def test_unweighted_backward_compat(self) -> None:
        """With edge_weight_attr=None, Laplacian is unweighted sum(f(j)-f(i))."""
        field_values = {"A": 1.0, "B": 2.0, "C": 3.0}
        g = _make_triangle_graph(field_values)
        graph = _make_graph_protocol(g)
        history: dict[str, dict[str, list[float]]] = {}

        _compute_node_derivatives(graph, ["exploitation"], history)

        # Node A: Laplacian = (2-1) + (3-1) = 3.0
        node_a = graph.get_node("A")
        assert node_a is not None
        derivs = node_a.attributes.get("field_derivatives", {})
        assert derivs["exploitation"]["laplacian"] == pytest.approx(3.0)

    def test_unweighted_symmetric(self) -> None:
        """Laplacian of constant field is zero."""
        field_values = {"A": 5.0, "B": 5.0, "C": 5.0}
        g = _make_triangle_graph(field_values)
        graph = _make_graph_protocol(g)
        history: dict[str, dict[str, list[float]]] = {}

        _compute_node_derivatives(graph, ["exploitation"], history)

        for node_id in ["A", "B", "C"]:
            node = graph.get_node(node_id)
            assert node is not None
            derivs = node.attributes.get("field_derivatives", {})
            assert derivs["exploitation"]["laplacian"] == pytest.approx(0.0)

    def test_weighted_laplacian(self) -> None:
        """Weighted Laplacian: sum(w * (f(j) - f(i)))."""
        field_values = {"A": 0.0, "B": 1.0, "C": 2.0}
        weights = {("A", "B"): 2.0, ("B", "C"): 3.0, ("A", "C"): 1.0}
        g = _make_triangle_graph(field_values, edge_weights=weights)
        graph = _make_graph_protocol(g)
        history: dict[str, dict[str, list[float]]] = {}

        _compute_node_derivatives(
            graph,
            ["exploitation"],
            history,
            edge_weight_attr="infrastructure_weight",
        )

        # Node A: w_AB*(1-0) + w_AC*(2-0) = 2*1 + 1*2 = 4.0
        node_a = graph.get_node("A")
        assert node_a is not None
        derivs_a = node_a.attributes.get("field_derivatives", {})
        assert derivs_a["exploitation"]["laplacian"] == pytest.approx(4.0)

    def test_zero_weight_no_contribution(self) -> None:
        """Edge with weight=0 contributes nothing to Laplacian."""
        field_values = {"A": 0.0, "B": 10.0, "C": 10.0}
        weights = {("A", "B"): 0.0, ("B", "C"): 1.0, ("A", "C"): 0.0}
        g = _make_triangle_graph(field_values, edge_weights=weights)
        graph = _make_graph_protocol(g)
        history: dict[str, dict[str, list[float]]] = {}

        _compute_node_derivatives(
            graph,
            ["exploitation"],
            history,
            edge_weight_attr="infrastructure_weight",
        )

        # Node A: 0*(10-0) + 0*(10-0) = 0.0
        node_a = graph.get_node("A")
        assert node_a is not None
        derivs_a = node_a.attributes.get("field_derivatives", {})
        assert derivs_a["exploitation"]["laplacian"] == pytest.approx(0.0)


@pytest.mark.unit
class TestCollectNeighborFields:
    """Tests for _collect_neighbor_fields with weights."""

    def test_returns_fields_and_weights(self) -> None:
        """When edge_weight_attr set, returns both fields and weights."""
        field_values = {"A": 1.0, "B": 2.0, "C": 3.0}
        weights = {("A", "B"): 0.5, ("A", "C"): 1.5}
        g = _make_triangle_graph(field_values, edge_weights=weights)
        graph = _make_graph_protocol(g)

        fields, edge_weights = _collect_neighbor_fields(
            graph,
            "A",
            ["exploitation"],
            edge_weight_attr="infrastructure_weight",
        )

        assert len(fields["exploitation"]) == 2
        assert len(edge_weights) == 2

    def test_returns_unit_weights_when_no_attr(self) -> None:
        """When edge_weight_attr is None, all weights are 1.0."""
        field_values = {"A": 1.0, "B": 2.0, "C": 3.0}
        g = _make_triangle_graph(field_values)
        graph = _make_graph_protocol(g)

        fields, edge_weights = _collect_neighbor_fields(
            graph,
            "A",
            ["exploitation"],
        )

        assert all(w == 1.0 for w in edge_weights)
