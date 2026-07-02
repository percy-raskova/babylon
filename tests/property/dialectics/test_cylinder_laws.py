"""Law tests for :class:`babylon.dialectics.core.cylinder.AdjointCylinder`.

The fixture is the connectivity cylinder over small undirected graphs —
the Phase-A test double of the production instance (Phase B grounds
solidarity/atomization on it):

- base carrier S = frozenset of node ids (structureless individuals)
- ambient carrier X = ``nx.Graph`` (the social space)
- ``embed_left``  = Δ, the edgeless (fully atomized) graph
- ``embed_right`` = ∇, the complete (totally unified) graph
- ``project``     = Γ, the underlying node set
- metric = size of the edge-set symmetric difference

Lawvere's UIAO laws verified: the embeddings are sections of the
projection (full faithfulness), □/○ are idempotent, □○=□ and ○□=○,
balance lies in [0,1] with balance(□x)=0 and balance(○x)=1, and adding
a solidarity edge strictly increases balance (organizing moves the
social graph toward the unity pole).
"""

from __future__ import annotations

from itertools import combinations

import networkx as nx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.dialectics.core.cylinder import AdjointCylinder

pytestmark = [pytest.mark.property, pytest.mark.topology]

NodeSet = frozenset[int]


def _edgeless(nodes: NodeSet) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(nodes)
    return g


def _complete(nodes: NodeSet) -> nx.Graph:
    g = _edgeless(nodes)
    g.add_edges_from(combinations(sorted(nodes), 2))
    return g


def _nodes(g: nx.Graph) -> NodeSet:
    return frozenset(g.nodes())


def _edge_set(g: nx.Graph) -> frozenset[frozenset[int]]:
    return frozenset(frozenset(e) for e in g.edges())


def _edge_distance(g1: nx.Graph, g2: nx.Graph) -> float:
    return float(len(_edge_set(g1) ^ _edge_set(g2)))


def _graph_eq(g1: nx.Graph, g2: nx.Graph) -> bool:
    return _nodes(g1) == _nodes(g2) and _edge_set(g1) == _edge_set(g2)


def _connectivity_cylinder() -> AdjointCylinder[NodeSet, nx.Graph]:
    return AdjointCylinder(
        embed_left=_edgeless,
        project=_nodes,
        embed_right=_complete,
        metric=_edge_distance,
    )


@st.composite
def _graphs(draw: st.DrawFn, min_nodes: int = 0, max_nodes: int = 8) -> nx.Graph:
    nodes = frozenset(draw(st.sets(st.integers(0, 15), min_size=min_nodes, max_size=max_nodes)))
    possible = sorted(combinations(sorted(nodes), 2))
    edges = draw(st.sets(st.sampled_from(possible))) if possible else set()
    g = _edgeless(nodes)
    g.add_edges_from(edges)
    return g


@given(nodes=st.frozensets(st.integers(0, 15), max_size=8))
@settings(max_examples=100)
def test_embeddings_are_sections(nodes: NodeSet) -> None:
    """Full faithfulness: project ∘ embed_left = id = project ∘ embed_right."""
    assert _connectivity_cylinder().retracts(nodes)


@given(x=_graphs())
@settings(max_examples=100)
def test_skeleton_and_sheaf_idempotent(x: nx.Graph) -> None:
    """□□ = □ and ○○ = ○."""
    cyl = _connectivity_cylinder()
    assert _graph_eq(cyl.skeleton(cyl.skeleton(x)), cyl.skeleton(x))
    assert _graph_eq(cyl.sheaf(cyl.sheaf(x)), cyl.sheaf(x))


@given(x=_graphs())
@settings(max_examples=100)
def test_modalities_absorb(x: nx.Graph) -> None:
    """□○ = □ and ○□ = ○ (both factor through the same projection)."""
    cyl = _connectivity_cylinder()
    assert _graph_eq(cyl.skeleton(cyl.sheaf(x)), cyl.skeleton(x))
    assert _graph_eq(cyl.sheaf(cyl.skeleton(x)), cyl.sheaf(x))


@given(x=_graphs())
@settings(max_examples=100)
def test_balance_bounded(x: nx.Graph) -> None:
    """balance(x) ∈ [0, 1] always."""
    b = _connectivity_cylinder().balance(x)
    assert 0.0 <= b <= 1.0


@given(x=_graphs(min_nodes=2))
@settings(max_examples=100)
def test_balance_poles(x: nx.Graph) -> None:
    """At the atomized pole balance=0; at the unity pole balance=1 (span>0)."""
    cyl = _connectivity_cylinder()
    assert cyl.span(x) > 0.0
    assert cyl.balance(cyl.skeleton(x)) == 0.0
    assert cyl.balance(cyl.sheaf(x)) == 1.0


@given(nodes=st.frozensets(st.integers(0, 15), max_size=1))
@settings(max_examples=20)
def test_balance_degenerate_span(nodes: NodeSet) -> None:
    """With at most one node the interval collapses; balance defaults to 0.5."""
    cyl = _connectivity_cylinder()
    assert cyl.balance(_edgeless(nodes)) == 0.5


@given(x=_graphs(min_nodes=2))
@settings(max_examples=100)
def test_organizing_increases_balance(x: nx.Graph) -> None:
    """Adding one solidarity edge strictly increases balance."""
    cyl = _connectivity_cylinder()
    missing = sorted(e for e in combinations(sorted(x.nodes()), 2) if not x.has_edge(*e))
    if not missing:
        return  # already at the unity pole
    before = cyl.balance(x)
    y = x.copy()
    y.add_edge(*missing[0])
    assert cyl.balance(y) > before
