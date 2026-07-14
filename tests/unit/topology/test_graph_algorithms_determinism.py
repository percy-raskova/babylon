"""W1.8 determinism hardening: centrality dicts must be key-sorted.

rustworkx's betweenness/closeness centrality parallelize via rayon above
``parallel_threshold`` (default 50 nodes), and every centrality mapping is
keyed by internal node index — so the id-keyed dict :func:`_centrality_ids`
builds otherwise inherits index-insertion order, which downstream consumers
(sparrow hub ranking, bifurcation resilience) iterate. Sorting by node id
makes that iteration order a property of the DATA, not of rustworkx
internals (Constitution III.7). The rayon thread pin itself is guarded in
``tests/unit/test_blas_thread_cap.py``.
"""

from __future__ import annotations

import pytest

from babylon.topology.graph import BabylonUGraph
from babylon.topology.graph_algorithms import (
    betweenness_centrality,
    closeness_centrality,
    degree_centrality,
)

pytestmark = pytest.mark.unit


def _unsorted_star() -> BabylonUGraph:
    """A star whose node ids are deliberately inserted in non-sorted order,
    so index order and sorted-id order disagree."""
    graph = BabylonUGraph()
    for node_id in ("zeta", "alpha", "mu", "hub", "beta"):
        graph.add_node(node_id)
    for leaf in ("zeta", "alpha", "mu", "beta"):
        graph.add_edge("hub", leaf)
    return graph


@pytest.mark.parametrize(
    "centrality",
    [degree_centrality, betweenness_centrality, closeness_centrality],
    ids=["degree", "betweenness", "closeness"],
)
def test_centrality_dict_is_key_sorted(centrality) -> None:  # type: ignore[no-untyped-def]
    graph = _unsorted_star()

    result = centrality(graph)

    assert list(result) == sorted(result), (
        "centrality mapping follows rustworkx index-insertion order, not sorted node ids — "
        "downstream iteration order then depends on graph-build history instead of the data"
    )


def test_centrality_values_survive_the_sort() -> None:
    """Sorting must reorder, never alter: the hub of a 4-leaf star has
    degree centrality 1.0 and every leaf 0.25."""
    graph = _unsorted_star()

    result = degree_centrality(graph)

    assert result["hub"] == pytest.approx(1.0)
    assert all(result[leaf] == pytest.approx(0.25) for leaf in ("alpha", "beta", "mu", "zeta"))
