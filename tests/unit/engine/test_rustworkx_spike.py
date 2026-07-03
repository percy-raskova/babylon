"""Capability spike pinning rustworkx 0.17 behaviors the migration relies on.

Each test is an executable assertion for a VERIFY item from the
NetworkX -> rustworkx migration (constitution Amendment L, ADR052).
The BabylonGraph adapter design depends on these exact semantics; if a
rustworkx upgrade changes any of them, this suite fails before the
adapter silently misbehaves.

Discovered against rustworkx 0.17.1 on 2026-07-03:

* ``add_edge`` on an existing pair REPLACES the payload (wrapper must merge).
* Node indices are REUSED after removal (wrapper must own an id<->index map).
* ``subgraph``/``copy`` SHARE payload dicts (wrapper must copy explicitly).
* ``dfs_edges`` has no ``depth_limit`` (wrapper needs a bounded-DFS shim).
* There is no ``density`` function (inline formula shim).
"""

from __future__ import annotations

import inspect
import math
from typing import Any

import pytest
import rustworkx as rx

pytestmark = [pytest.mark.unit, pytest.mark.topology]


class TestEdgeSemantics:
    """Edge identity semantics underpinning BabylonGraph's merge logic."""

    def test_add_edge_on_existing_pair_replaces_payload(self) -> None:
        """multigraph=False: second add_edge REPLACES the payload, no merge."""
        graph: rx.PyDiGraph[dict[str, Any], dict[str, Any]] = rx.PyDiGraph(multigraph=False)
        a = graph.add_node({"id": "a"})
        b = graph.add_node({"id": "b"})
        graph.add_edge(a, b, {"w": 1, "keep": True})
        graph.add_edge(a, b, {"w": 2})

        assert graph.num_edges() == 1
        # REPLACE semantics: "keep" is gone. BabylonGraph must merge explicitly.
        assert graph.get_edge_data(a, b) == {"w": 2}

    def test_multigraph_false_flag_is_respected(self) -> None:
        graph: rx.PyDiGraph[dict[str, Any], dict[str, Any]] = rx.PyDiGraph(multigraph=False)
        assert graph.multigraph is False


class TestIndexSemantics:
    """Node-index lifecycle that mandates the insertion-ordered bimap."""

    def test_node_indices_are_reused_after_removal(self) -> None:
        graph: rx.PyDiGraph[dict[str, Any], dict[str, Any]] = rx.PyDiGraph()
        graph.add_nodes_from([{"n": i} for i in range(5)])

        graph.remove_node(2)
        new_index = graph.add_node({"n": "new"})

        # The freed index is handed back out: raw index order is NOT
        # insertion order after churn. BabylonGraph iteration must never
        # walk raw index order.
        assert new_index == 2
        assert list(graph.node_indices()) == [0, 1, 2, 3, 4]

    def test_subgraph_and_copy_share_payload_dicts(self) -> None:
        """rx copy/subgraph are shallow w.r.t. payloads (unlike nx copy)."""
        graph: rx.PyDiGraph[dict[str, Any], dict[str, Any]] = rx.PyDiGraph()
        payload = {"mut": 0}
        i0 = graph.add_node(payload)
        i1 = graph.add_node({"other": 1})
        graph.add_edge(i0, i1, {"e": 1})

        sub = graph.subgraph([i0, i1])
        cop = graph.copy()
        payload["mut"] = 99

        assert sub[0]["mut"] == 99
        assert cop[i0]["mut"] == 99


class TestAlgorithmCoverage:
    """Every nx algorithm the codebase uses has a pinned rx equivalent."""

    def test_component_functions_exist(self) -> None:
        assert hasattr(rx, "connected_components")
        assert hasattr(rx, "number_connected_components")
        assert hasattr(rx, "is_connected")
        assert hasattr(rx, "weakly_connected_components")
        assert hasattr(rx, "articulation_points")
        assert hasattr(rx, "descendants")

    def test_weakly_connected_equals_undirected_components(self) -> None:
        digraph: rx.PyDiGraph[dict[str, Any], dict[str, Any]] = rx.PyDiGraph(multigraph=False)
        n = digraph.add_nodes_from([{} for _ in range(4)])
        digraph.add_edge(n[0], n[1], {})
        digraph.add_edge(n[3], n[2], {})

        weak = {frozenset(c) for c in rx.weakly_connected_components(digraph)}
        undirected = {frozenset(c) for c in rx.connected_components(digraph.to_undirected())}
        assert weak == undirected == {frozenset({0, 1}), frozenset({2, 3})}

    def test_has_path_signature(self) -> None:
        params = inspect.signature(rx.has_path).parameters
        assert list(params) == ["graph", "source", "target", "as_undirected"]

    def test_centralities_match_networkx_normalization(self) -> None:
        """Star graph S4: rx values equal nx's normalized conventions."""
        star = rx.generators.star_graph(5)  # node 0 = hub, 4 leaves

        degree = rx.degree_centrality(star)
        assert degree[0] == pytest.approx(1.0)
        assert degree[1] == pytest.approx(0.25)

        closeness = rx.closeness_centrality(star)
        assert closeness[0] == pytest.approx(1.0)
        assert closeness[1] == pytest.approx(4.0 / 7.0)

        betweenness = rx.betweenness_centrality(star)
        assert betweenness[0] == pytest.approx(1.0)
        assert betweenness[1] == pytest.approx(0.0)

    def test_dfs_edges_has_no_depth_limit(self) -> None:
        """Pins the need for BabylonGraph's bounded-DFS shim."""
        params = inspect.signature(rx.dfs_edges).parameters
        assert "depth_limit" not in params

    def test_generators_needed_by_tests_exist(self) -> None:
        for name in (
            "star_graph",
            "path_graph",
            "cycle_graph",
            "complete_graph",
            "mesh_graph",
            "barbell_graph",
        ):
            assert hasattr(rx.generators, name), name

    def test_stoer_wagner_min_cut_returns_value_and_partition(self) -> None:
        """Global min cut of C4 is 2 edges; result is (cut_value, partition)."""
        cycle = rx.generators.cycle_graph(4)
        cut_value, partition = rx.stoer_wagner_min_cut(cycle)

        assert cut_value == pytest.approx(2.0)
        assert 1 <= len(partition) <= 3

    def test_dijkstra_lengths_goal_and_unreachable(self) -> None:
        """goal= early-exits; unreachable goal yields EMPTY mapping (no raise)."""
        graph: rx.PyGraph[dict[str, Any], dict[str, Any]] = rx.PyGraph()
        n0, n1, n2 = graph.add_nodes_from([{}, {}, {}])
        graph.add_edge(n0, n1, {"weight": 2.0})

        reachable = rx.dijkstra_shortest_path_lengths(
            graph, n0, edge_cost_fn=lambda e: float(e["weight"]), goal=n1
        )
        assert dict(reachable) == {n1: pytest.approx(2.0)}

        unreachable = rx.dijkstra_shortest_path_lengths(
            graph, n0, edge_cost_fn=lambda e: float(e["weight"]), goal=n2
        )
        assert dict(unreachable) == {}
        assert math.isinf(float("inf"))  # curvature maps empty -> inf

    def test_exceptions_exist(self) -> None:
        assert issubclass(rx.NoPathFound, Exception)
        assert issubclass(rx.InvalidNode, Exception)

    def test_no_density_function(self) -> None:
        """Pins the need for the inline density formula shim."""
        assert not hasattr(rx, "density")
        assert not hasattr(rx, "graph_density")


class TestGraphAttrs:
    """Graph-level attribute storage BabylonGraph maps its .graph dict onto."""

    def test_attrs_constructor_roundtrip(self) -> None:
        graph: rx.PyDiGraph[dict[str, Any], dict[str, Any]] = rx.PyDiGraph(attrs={"day": "Fri"})
        assert graph.attrs == {"day": "Fri"}
        graph.attrs["day"] = "Mon"
        assert graph.attrs["day"] == "Mon"
