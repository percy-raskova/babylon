"""Tests for weighted curvature computation (Feature 036, T025).

Tests verify:
- Backward compatibility: no weight_attr = uniform probability measure
- Weighted probability measure: proportional to edge weights
- Weighted shortest paths in graph distance
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.graph import BabylonUGraph
from babylon.formulas.curvature import (
    _graph_distance,
    _probability_measure,
    compute_ollivier_ricci,
)


def _make_weighted_graph() -> nx.Graph:  # type: ignore[type-arg]
    """Create a small weighted graph for curvature tests."""
    g = BabylonUGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_node("C")
    g.add_node("D")

    # A-B: weight 2.0, A-C: weight 1.0, B-D: weight 1.0, C-D: weight 3.0
    g.add_edge("A", "B", infrastructure_weight=2.0)
    g.add_edge("A", "C", infrastructure_weight=1.0)
    g.add_edge("B", "D", infrastructure_weight=1.0)
    g.add_edge("C", "D", infrastructure_weight=3.0)

    return g


@pytest.mark.unit
class TestWeightedProbabilityMeasure:
    """Tests for _probability_measure with weights."""

    def test_unweighted_uniform(self) -> None:
        """Without weight_attr, neighbors get uniform probability."""
        g = BabylonUGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")

        measure = _probability_measure(g, "A", alpha=0.5)

        # alpha=0.5 on self, 0.25 each on B and C
        assert measure["A"] == pytest.approx(0.5)
        assert measure["B"] == pytest.approx(0.25)
        assert measure["C"] == pytest.approx(0.25)

    def test_weighted_proportional(self) -> None:
        """With weight_attr, (1-alpha) distributed proportional to weights."""
        g = _make_weighted_graph()

        measure = _probability_measure(
            g,
            "A",
            alpha=0.5,
            weight_attr="infrastructure_weight",
        )

        # A has neighbors B (w=2) and C (w=1), total=3
        # P(A)=0.5, P(B)=0.5*(2/3), P(C)=0.5*(1/3)
        assert measure["A"] == pytest.approx(0.5)
        assert measure["B"] == pytest.approx(0.5 * 2 / 3)
        assert measure["C"] == pytest.approx(0.5 * 1 / 3)

    def test_isolated_node(self) -> None:
        """Isolated node gets all mass on self, weighted or not."""
        g = BabylonUGraph()
        g.add_node("X")

        measure = _probability_measure(g, "X", alpha=0.5)
        assert measure["X"] == pytest.approx(1.0)


@pytest.mark.unit
class TestWeightedGraphDistance:
    """Tests for _graph_distance with weight_attr."""

    def test_unweighted_hop_count(self) -> None:
        """Without weight_attr, distance is hop count."""
        g = _make_weighted_graph()
        d = _graph_distance(g, "A", "D")
        assert d == pytest.approx(2.0)  # A-B-D or A-C-D, both 2 hops

    def test_weighted_shortest_path(self) -> None:
        """With weight_attr, distance uses edge weights."""
        g = _make_weighted_graph()
        d = _graph_distance(g, "A", "D", weight_attr="infrastructure_weight")
        # A-B (2) + B-D (1) = 3
        # A-C (1) + C-D (3) = 4
        # Shortest = 3
        assert d == pytest.approx(3.0)

    def test_same_node_zero(self) -> None:
        """Distance from node to itself is 0."""
        g = _make_weighted_graph()
        assert _graph_distance(g, "A", "A") == 0.0


@pytest.mark.unit
class TestWeightedOllivierRicci:
    """Tests for compute_ollivier_ricci with weight_attr."""

    def test_backward_compat(self) -> None:
        """Without weight_attr, curvature computation is unchanged."""
        g = BabylonUGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "C")

        kappa = compute_ollivier_ricci(g, "A", "B", alpha=0.5)
        assert isinstance(kappa, float)
        # Triangle: positive curvature
        assert kappa > 0

    def test_weighted_curvature(self) -> None:
        """With weight_attr, curvature uses weighted measures and distances."""
        g = _make_weighted_graph()

        kappa = compute_ollivier_ricci(
            g,
            "A",
            "B",
            alpha=0.5,
            weight_attr="infrastructure_weight",
        )
        assert isinstance(kappa, float)

    def test_different_weights_different_curvature(self) -> None:
        """Different weight distributions produce different curvatures."""
        g1 = BabylonUGraph()
        g1.add_edge("A", "B", w=1.0)
        g1.add_edge("A", "C", w=1.0)
        g1.add_edge("B", "C", w=1.0)

        g2 = BabylonUGraph()
        g2.add_edge("A", "B", w=10.0)
        g2.add_edge("A", "C", w=1.0)
        g2.add_edge("B", "C", w=1.0)

        k1 = compute_ollivier_ricci(g1, "A", "B", alpha=0.5, weight_attr="w")
        k2 = compute_ollivier_ricci(g2, "A", "B", alpha=0.5, weight_attr="w")

        # Different weights should produce different curvatures
        assert k1 != pytest.approx(k2, abs=1e-6)
