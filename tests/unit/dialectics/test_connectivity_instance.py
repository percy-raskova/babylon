"""Tests for the Phase-B connectivity cylinder instance.

Three concerns, per ``project/06-lawverian-dialectics.md`` §4:

- Instance semantics: :func:`pieces` (Pi_0), :func:`atomization_index`,
  and :func:`connectivity_cylinder` (the Delta-dashv-Gamma-dashv-nabla
  adjoint string) on the production ``nx.Graph[str]`` carrier.
- The TopologyMonitor compatibility class: pins
  :func:`babylon.engine.topology_monitor.calculate_component_metrics`'s
  new Pi_0-based computation against an independent reference that
  reproduces its pre-Phase-B body verbatim, so this test now guards the
  re-grounding rather than merely documenting it.
- The SolidaritySystem operator reading documented in that module's
  docstring: a SOLIDARITY edge bridging two components strictly
  decreases atomization and strictly increases cylinder balance.
"""

from __future__ import annotations

import networkx as nx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.dialectics.instances.connectivity import (
    atomization_index,
    connectivity_cylinder,
    pieces,
)
from babylon.engine.graph import BabylonGraph, BabylonUGraph
from babylon.engine.topology_monitor import calculate_component_metrics, extract_solidarity_subgraph
from babylon.models.enums import EdgeType

pytestmark = [pytest.mark.unit, pytest.mark.topology]


@st.composite
def _graphs(draw: st.DrawFn, max_nodes: int = 8) -> nx.Graph[str]:
    """Small undirected graphs on string node ids "0".."max_nodes-1"."""
    node_count = draw(st.integers(min_value=0, max_value=max_nodes))
    nodes = [str(i) for i in range(node_count)]
    possible = [(nodes[i], nodes[j]) for i in range(node_count) for j in range(i + 1, node_count)]
    edges = draw(st.sets(st.sampled_from(possible))) if possible else set()
    graph = BabylonUGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    return graph


# =============================================================================
# INSTANCE SEMANTICS
# =============================================================================


class TestPieces:
    """Pi_0: connected components, deterministically ordered by min element."""

    def test_empty_graph_has_no_pieces(self) -> None:
        assert pieces(BabylonUGraph()) == ()

    def test_single_isolated_node_is_one_piece(self) -> None:
        g = BabylonUGraph()
        g.add_node("a")
        assert pieces(g) == (frozenset({"a"}),)

    def test_ordered_by_minimum_element(self) -> None:
        g = BabylonUGraph()
        g.add_nodes_from(["z", "b", "a", "c"])
        g.add_edge("b", "c")
        # Components {a}, {b, c}, {z}; ordered "a" < "b" < "z".
        assert pieces(g) == (frozenset({"a"}), frozenset({"b", "c"}), frozenset({"z"}))

    def test_deterministic_regardless_of_insertion_order(self) -> None:
        g1 = BabylonUGraph()
        g1.add_nodes_from(["a", "b", "c"])
        g1.add_edge("a", "b")

        g2 = BabylonUGraph()
        g2.add_nodes_from(["c", "b", "a"])
        g2.add_edge("b", "a")

        assert pieces(g1) == pieces(g2)

    def test_fully_connected_graph_is_one_piece(self) -> None:
        g = BabylonUGraph()
        g.add_nodes_from(["a", "b", "c", "d"])
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "d")])
        assert len(pieces(g)) == 1


class TestAtomizationIndex:
    """(|Pi_0|-1)/(|Gamma|-1); degenerate (0.0) at n<=1 nodes."""

    def test_empty_graph_is_zero(self) -> None:
        assert atomization_index(BabylonUGraph()) == 0.0

    def test_single_node_is_zero(self) -> None:
        g = BabylonUGraph()
        g.add_node("a")
        assert atomization_index(g) == 0.0

    def test_fully_atomized_graph_is_one(self) -> None:
        g = BabylonUGraph()
        g.add_nodes_from(["a", "b", "c", "d"])
        assert atomization_index(g) == 1.0

    def test_fully_connected_graph_is_zero(self) -> None:
        g = BabylonUGraph()
        g.add_nodes_from(["a", "b", "c", "d"])
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "d")])
        assert atomization_index(g) == 0.0

    def test_partial_atomization_matches_worked_example(self) -> None:
        # 6 nodes, 3 components ({a,b,c}, {d,e}, {f}) -> (3-1)/(6-1) = 0.4
        g = BabylonUGraph()
        g.add_nodes_from(["a", "b", "c", "d", "e", "f"])
        g.add_edges_from([("a", "b"), ("b", "c"), ("d", "e")])
        assert atomization_index(g) == pytest.approx(0.4)

    @pytest.mark.property
    @given(graph=_graphs())
    @settings(max_examples=100)
    def test_matches_formula_for_random_graphs(self, graph: nx.Graph[str]) -> None:
        """atomization_index always equals (|pieces|-1)/(n-1) directly."""
        n = graph.number_of_nodes()
        if n <= 1:
            assert atomization_index(graph) == 0.0
            return
        expected = (len(pieces(graph)) - 1) / (n - 1)
        assert atomization_index(graph) == pytest.approx(expected)


class TestConnectivityCylinder:
    """Factory wiring: full faithfulness + poles, on the production instance."""

    def test_retracts_for_arbitrary_node_set(self) -> None:
        cyl = connectivity_cylinder()
        assert cyl.retracts(frozenset({"a", "b", "c"}))

    def test_balance_at_skeleton_and_sheaf_poles(self) -> None:
        cyl = connectivity_cylinder()
        g = BabylonUGraph()
        g.add_nodes_from(["a", "b", "c"])
        g.add_edge("a", "b")

        assert cyl.balance(cyl.skeleton(g)) == 0.0
        assert cyl.balance(cyl.sheaf(g)) == 1.0

    @pytest.mark.property
    @given(nodes=st.frozensets(st.integers(0, 15).map(str), max_size=8))
    @settings(max_examples=100)
    def test_embeddings_are_sections(self, nodes: frozenset[str]) -> None:
        """Full faithfulness on the production instance (cf. test_cylinder_laws.py)."""
        assert connectivity_cylinder().retracts(nodes)


# =============================================================================
# TOPOLOGY MONITOR COMPATIBILITY (guards the Phase-B re-grounding)
# =============================================================================


def _old_component_metrics(
    solidarity_graph: nx.Graph[str],
    total_social_classes: int,
) -> tuple[int, int, float]:
    """Independent reference reproducing the pre-Phase-B function body.

    ``calculate_component_metrics`` now computes components via
    :func:`pieces` (Pi_0 of the connectivity cylinder). This helper keeps
    the ORIGINAL direct ``nx.connected_components`` computation alive,
    solely so the tests below can pin the new computation against it.
    """
    if total_social_classes == 0:
        return (0, 0, 0.0)
    # Rebuild a DELIBERATELY-NetworkX reference graph from the carrier's
    # node/edge lists: this helper is the differential oracle pinning the
    # rx-native Pi_0 against nx.connected_components (Amendment L).
    reference: nx.Graph[str] = nx.Graph()
    reference.add_nodes_from(solidarity_graph.nodes())
    reference.add_edges_from(solidarity_graph.edges())
    components = list(nx.connected_components(reference))
    num_components = len(components)
    max_component_size = 0 if num_components == 0 else max(len(c) for c in components)
    percolation_ratio = max_component_size / total_social_classes
    percolation_ratio = max(0.0, min(1.0, percolation_ratio))
    return (num_components, max_component_size, percolation_ratio)


class TestTopologyMonitorCompatibility:
    """calculate_component_metrics's new Pi_0 computation == the old one."""

    @pytest.mark.property
    @given(graph=_graphs())
    @settings(max_examples=100)
    def test_matches_old_computation_on_random_graphs(self, graph: nx.Graph[str]) -> None:
        n = graph.number_of_nodes()
        assert calculate_component_metrics(graph, n) == _old_component_metrics(graph, n)

    def test_matches_old_computation_star_topology(self) -> None:
        """Fragile hub-and-spoke shape, as TopologyMonitor's resilience test uses."""
        g = BabylonUGraph()
        g.add_node("C_HUB")
        for i in range(5):
            node_id = f"C00{i}"
            g.add_node(node_id)
            g.add_edge("C_HUB", node_id)
        assert calculate_component_metrics(g, 6) == _old_component_metrics(g, 6)

    def test_matches_old_computation_multi_component(self) -> None:
        """Three components (3+2+1 nodes), as TopologyMonitor's own fixtures use."""
        g = BabylonUGraph()
        g.add_edges_from([("C001", "C002"), ("C002", "C003"), ("C004", "C005")])
        g.add_node("C006")
        assert calculate_component_metrics(g, 6) == _old_component_metrics(g, 6)

    def test_matches_old_computation_via_real_extraction_pipeline(self) -> None:
        """End-to-end: raw DiGraph -> extract_solidarity_subgraph -> metrics."""
        raw = BabylonGraph()
        raw.add_node("C001", _node_type="social_class")
        raw.add_node("C002", _node_type="social_class")
        raw.add_node("C003", _node_type="social_class")
        raw.add_node("T001", _node_type="territory")
        raw.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
        raw.add_edge("C002", "C003", edge_type=EdgeType.EXPLOITATION, value_flow=0.5)
        raw.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)

        subgraph = extract_solidarity_subgraph(raw)
        assert calculate_component_metrics(subgraph, 3) == _old_component_metrics(subgraph, 3)


# =============================================================================
# SOLIDARITY SYSTEM OPERATOR READING
# =============================================================================


class TestSolidarityEdgeMovesTowardUnity:
    """Documented in solidarity.py's module docstring; characterized here.

    A SOLIDARITY edge that bridges two previously separate components is
    exactly the case where atomization strictly falls: an edge added
    *inside* an already-connected component leaves the component count
    (and thus atomization_index) unchanged, even though it still raises
    edge density (and thus cylinder balance). Bridging two components is
    what "building solidarity infrastructure" means categorically.
    """

    def test_bridging_edge_decreases_atomization_increases_balance(self) -> None:
        # Two isolated pairs {a,b} and {c,d}: 2 components over 4 nodes.
        before = BabylonUGraph()
        before.add_edges_from([("a", "b"), ("c", "d")])

        # A SOLIDARITY edge b-c bridges the two components into one.
        after = before.copy()
        after.add_edge("b", "c")

        assert atomization_index(after) < atomization_index(before)

        cyl = connectivity_cylinder()
        assert cyl.balance(after) > cyl.balance(before)
