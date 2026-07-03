"""Iteration-order contract for BabylonGraph (constitution III.7).

The determinism hash depends on graph iteration order: NetworkX iterates
nodes in insertion order and edges in source-insertion-then-adjacency
order, and the engine's event stream inherits that. These tests pin
BabylonGraph to the same contract under the churn patterns the live
systems produce (collapse_transition removes AND adds nodes mid-tick;
struggle removes edges), using ``nx.DiGraph`` itself as the differential
oracle — including a Hypothesis model test over arbitrary bounded
add/remove interleavings.

Also pinned here: nx-parity add_edge merge semantics, payload reference
semantics through the rustworkx core, and the copy/subgraph
isolation/sharing matrix.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.graph import BabylonGraph

pytestmark = [pytest.mark.unit, pytest.mark.topology]


def _nx_reference() -> nx.DiGraph[str]:
    return nx.DiGraph()


class TestNodeOrder:
    """Node iteration order under collapse_transition-style churn."""

    def test_insertion_order_preserved(self) -> None:
        graph = BabylonGraph()
        for node_id in ("C003", "C001", "C002"):
            graph.add_node(node_id, "social_class")
        assert list(graph.nodes) == ["C003", "C001", "C002"]

    def test_order_after_remove_and_readd(self) -> None:
        """Remove-then-add churn: rx reuses the freed index; order must not."""
        graph = BabylonGraph()
        oracle = _nx_reference()
        for node_id in ("A", "B", "C", "D", "E"):
            graph.add_node(node_id, "social_class")
            oracle.add_node(node_id, _node_type="social_class")
        for node_id in ("B", "D"):
            graph.remove_node(node_id)
            oracle.remove_node(node_id)
        for node_id in ("F", "G", "B"):
            graph.add_node(node_id, "territory")
            oracle.add_node(node_id, _node_type="territory")

        assert list(graph.nodes) == list(oracle.nodes) == ["A", "C", "E", "F", "G", "B"]
        # Index reuse happened under the hood but is invisible id-side.
        assert graph.id_of(graph.index_of("F")) == "F"

    def test_nodes_data_pairs_match_oracle(self) -> None:
        graph = BabylonGraph()
        oracle = _nx_reference()
        graph.add_node("X", "territory", heat=0.3)
        graph.add_node("Y", "territory", heat=0.1)
        oracle.add_node("X", _node_type="territory", heat=0.3)
        oracle.add_node("Y", _node_type="territory", heat=0.1)
        assert graph.nodes(data=True) == [(n, dict(oracle.nodes[n])) for n in oracle.nodes]


class TestEdgeOrder:
    """Edge iteration order: sources by node insertion, targets by adjacency."""

    def test_interleaved_edge_insertion_matches_networkx(self) -> None:
        graph = BabylonGraph()
        oracle = _nx_reference()
        edges = [("A", "B"), ("C", "D"), ("A", "E"), ("C", "A"), ("B", "C")]
        for source, target in edges:
            graph.add_edge(source, target, "WAGES", weight=1.0)
            oracle.add_edge(source, target, _edge_type="WAGES", weight=1.0)

        assert graph.edges() == list(oracle.edges())
        assert list(graph.edges()) == [("A", "B"), ("A", "E"), ("B", "C"), ("C", "D"), ("C", "A")]

    def test_order_after_struggle_style_edge_removal(self) -> None:
        """Removing an edge then re-adding it moves it to adjacency end."""
        graph = BabylonGraph()
        oracle = _nx_reference()
        for source, target in (("A", "B"), ("A", "C"), ("A", "D")):
            graph.add_edge(source, target, "SOLIDARITY")
            oracle.add_edge(source, target, _edge_type="SOLIDARITY", weight=1.0)

        graph.remove_edge("A", "C")
        oracle.remove_edge("A", "C")
        graph.add_edge("A", "C", "SOLIDARITY")
        oracle.add_edge("A", "C", _edge_type="SOLIDARITY", weight=1.0)

        assert graph.edges() == list(oracle.edges()) == [("A", "B"), ("A", "D"), ("A", "C")]


class TestEdgeMergeSemantics:
    """add_edge on an existing pair merges attributes (nx parity)."""

    def test_second_add_edge_merges_not_replaces(self) -> None:
        graph = BabylonGraph()
        graph.add_edge("A", "B", "WAGES", weight=0.5, keep=True)
        graph.add_edge("A", "B", "WAGES", weight=0.9)

        payload = graph.edges[("A", "B")]
        assert payload["keep"] is True  # rx alone would have dropped this
        assert payload["weight"] == 0.9
        assert graph.number_of_edges() == 1

    def test_authoring_style_type_keys_are_normalized(self) -> None:
        """Node type folds to _node_type; edge types stay DUAL-keyed.

        Edge payloads keep the public ``edge_type`` alongside ``_edge_type``
        because ~25 raw call sites (ooda, bifurcation, persistence,
        from_graph) read the public key — the wrap()-era production layout.
        """
        graph = BabylonGraph()
        graph.add_node("T1", heat=0.2, node_type="territory")
        graph.add_edge("T1", "T2", tension=0.4, edge_type="ADJACENCY")
        graph.add_edge("T2", "T1", "SOLIDARITY", weight=0.7)

        assert graph.nodes["T1"]["_node_type"] == "territory"
        assert "node_type" not in graph.nodes["T1"]
        authored = graph.edges[("T1", "T2")]
        assert authored["_edge_type"] == "ADJACENCY"
        assert authored["edge_type"] == "ADJACENCY"
        protocol = graph.edges[("T2", "T1")]
        assert protocol["_edge_type"] == protocol["edge_type"] == "SOLIDARITY"
        assert protocol["weight"] == 0.7


class TestPayloadReferenceSemantics:
    """Mirror dicts and rustworkx payloads are the same objects."""

    def test_node_mutation_visible_through_core(self) -> None:
        graph = BabylonGraph()
        graph.add_node("A", "social_class", wealth=1.0)
        graph.nodes["A"]["wealth"] = 42.0

        assert graph.core[graph.index_of("A")]["wealth"] == 42.0
        node = graph.get_node("A")
        assert node is not None
        assert node.attributes["wealth"] == 42.0

    def test_edge_mutation_visible_through_core(self) -> None:
        graph = BabylonGraph()
        graph.add_edge("A", "B", "WAGES", weight=1.0)
        graph.edges[("A", "B")]["weight"] = 7.0

        core_payload = graph.core.get_edge_data(graph.index_of("A"), graph.index_of("B"))
        assert core_payload["weight"] == 7.0


class TestCopySubgraphMatrix:
    """copy() isolates payloads; subgraph() shares them (nx-view parity)."""

    def test_copy_is_isolated(self) -> None:
        graph = BabylonGraph()
        graph.add_node("A", "social_class", wealth=1.0)
        graph.add_edge("A", "B", "WAGES", tension=0.1)
        clone = graph.copy()

        graph.nodes["A"]["wealth"] = 99.0
        graph.edges[("A", "B")]["tension"] = 0.9

        assert clone.nodes["A"]["wealth"] == 1.0
        assert clone.edges[("A", "B")]["tension"] == 0.1

    def test_subgraph_shares_payloads(self) -> None:
        graph = BabylonGraph()
        graph.add_node("A", "social_class", wealth=1.0)
        graph.add_node("B", "social_class", wealth=2.0)
        graph.add_edge("A", "B", "WAGES", tension=0.1)
        view = graph.subgraph(["A", "B"])

        view.nodes["A"]["wealth"] = 50.0
        view.edges[("A", "B")]["tension"] = 0.5

        assert graph.nodes["A"]["wealth"] == 50.0
        assert graph.edges[("A", "B")]["tension"] == 0.5

    def test_graph_attrs_roundtrip(self) -> None:
        graph = BabylonGraph()
        graph.graph["tick"] = 5
        assert graph.get_graph_attr("tick") == 5
        graph.set_graph_attr("base_year", 2010)
        assert graph.graph["base_year"] == 2010
        assert graph.copy().graph == {"tick": 5, "base_year": 2010}


# ─── Hypothesis model test ────────────────────────────────────────────────

_POOL = [f"n{i}" for i in range(6)]

_ops = st.lists(
    st.one_of(
        st.tuples(st.just("add_node"), st.sampled_from(_POOL)),
        st.tuples(st.just("remove_node"), st.sampled_from(_POOL)),
        st.tuples(st.just("add_edge"), st.sampled_from(_POOL), st.sampled_from(_POOL)),
        st.tuples(st.just("remove_edge"), st.sampled_from(_POOL), st.sampled_from(_POOL)),
    ),
    max_size=40,
)


class TestIterationOrderModel:
    """Arbitrary bounded churn: BabylonGraph order == NetworkX order."""

    @settings(max_examples=100, deadline=None)
    @given(ops=_ops)
    def test_order_matches_networkx_under_churn(self, ops: list[tuple[Any, ...]]) -> None:
        graph = BabylonGraph()
        oracle = _nx_reference()

        for op in ops:
            if op[0] == "add_node":
                graph.add_node(op[1], "social_class", w=1.0)
                oracle.add_node(op[1], _node_type="social_class", w=1.0)
            elif op[0] == "remove_node":
                if op[1] in oracle:
                    graph.remove_node(op[1])
                    oracle.remove_node(op[1])
            elif op[0] == "add_edge":
                graph.add_edge(op[1], op[2], "E", weight=1.0)
                # Oracle mirrors the production payload layout: public
                # edge_type (to_graph) + internal _edge_type (wrap()).
                oracle.add_edge(op[1], op[2], _edge_type="E", edge_type="E", weight=1.0)
            elif op[0] == "remove_edge":
                if oracle.has_edge(op[1], op[2]):
                    graph.remove_edge(op[1], op[2])
                    oracle.remove_edge(op[1], op[2])

        assert list(graph.nodes) == list(oracle.nodes)
        assert graph.nodes(data=True) == [
            (node_id, dict(oracle.nodes[node_id])) for node_id in oracle.nodes
        ]
        assert graph.edges(data=True) == [(u, v, dict(d)) for u, v, d in oracle.edges(data=True)]
        assert graph.number_of_nodes() == oracle.number_of_nodes()
        assert graph.number_of_edges() == oracle.number_of_edges()
