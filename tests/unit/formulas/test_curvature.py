"""Tests for Ollivier-Ricci curvature computation (Feature 002 - US6).

Validates against analytically known topologies:
- K4 (complete graph): positive curvature (well-connected)
- Barbell (two cliques + bridge): negative curvature at bridge (bottleneck)
- C6 (cycle): all edges have same curvature by symmetry

Reference: FR-005 (Ollivier-Ricci curvature)
Reference: R-004 (scipy LP for Wasserstein-1)
"""

from __future__ import annotations

import pytest

from babylon.formulas.curvature import compute_ollivier_ricci
from babylon.topology.graph import BabylonUGraph


def _complete_graph(n: int) -> BabylonUGraph:
    """K_n on string ids "0".."n-1"."""
    graph = BabylonUGraph()
    nodes = [str(i) for i in range(n)]
    graph.add_nodes_from(nodes)
    graph.add_edges_from(
        [(a, b) for i, a in enumerate(nodes) for b in nodes[i + 1 :]],
    )
    return graph


def _cycle_graph(n: int) -> BabylonUGraph:
    """C_n on string ids "0".."n-1"."""
    graph = BabylonUGraph()
    nodes = [str(i) for i in range(n)]
    graph.add_nodes_from(nodes)
    graph.add_edges_from([(nodes[i], nodes[(i + 1) % n]) for i in range(n)])
    return graph


def _barbell_graph() -> BabylonUGraph:
    """Two K3s joined by a bridge: K3(0,1,2) --- bridge(2,3) --- K3(3,4,5)."""
    graph = BabylonUGraph()
    graph.add_edges_from([("0", "1"), ("0", "2"), ("1", "2")])
    graph.add_edges_from([("3", "4"), ("3", "5"), ("4", "5")])
    graph.add_edge("2", "3")
    return graph


@pytest.mark.math
class TestOllivierRicciAnalytical:
    """Test curvature against analytically known topologies."""

    def test_complete_graph_k4_positive_curvature(self) -> None:
        """K4 (complete graph on 4 nodes) has positive curvature on all edges."""
        graph = _complete_graph(4)
        alpha = 0.5

        for u, v in graph.edges():
            kappa = compute_ollivier_ricci(graph, u, v, alpha=alpha)
            assert kappa > 0, f"K4 edge ({u},{v}) should have positive curvature, got {kappa}"

    def test_barbell_graph_negative_at_bridge(self) -> None:
        """Barbell graph (two K3 + bridge) has negative curvature at bridge.

        The bridge edge connects two cliques with no shared neighbors,
        creating a bottleneck — the hallmark of negative curvature.
        """
        graph = _barbell_graph()
        alpha = 0.5

        # Bridge edge (2,3) should have negative curvature
        kappa = compute_ollivier_ricci(graph, "2", "3", alpha=alpha)
        assert kappa < 0, f"Barbell bridge edge (2,3) should have negative curvature, got {kappa}"

    def test_curvature_in_valid_range(self) -> None:
        """Curvature should not exceed 1.0."""
        graph = _cycle_graph(6)
        alpha = 0.5

        for u, v in graph.edges():
            kappa = compute_ollivier_ricci(graph, u, v, alpha=alpha)
            assert kappa <= 1.0 + 1e-9, f"Curvature {kappa} exceeds 1.0"

    def test_cycle_graph_symmetry(self) -> None:
        """C6 (cycle on 6 nodes) — all edges have same curvature by symmetry."""
        graph = _cycle_graph(6)
        alpha = 0.5

        curvatures = [compute_ollivier_ricci(graph, u, v, alpha=alpha) for u, v in graph.edges()]

        for kappa in curvatures:
            assert kappa == pytest.approx(curvatures[0], abs=1e-9)

    def test_self_loop_returns_zero(self) -> None:
        """Self-loop (u == v) returns 0.0 curvature."""
        graph = _complete_graph(4)
        kappa = compute_ollivier_ricci(graph, "0", "0", alpha=0.5)
        assert kappa == 0.0

    def test_returns_float(self) -> None:
        """Curvature returns a float for any valid edge."""
        graph = _complete_graph(4)
        kappa = compute_ollivier_ricci(graph, "0", "1", alpha=0.5)
        assert isinstance(kappa, float)

    def test_invalid_node_raises(self) -> None:
        """Non-existent node raises ValueError."""
        graph = _complete_graph(4)
        with pytest.raises(ValueError, match="not in graph"):
            compute_ollivier_ricci(graph, "0", "99", alpha=0.5)
