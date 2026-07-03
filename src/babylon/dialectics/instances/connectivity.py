"""The connectivity cylinder: Babylon's Phase-B adjoint-cylinder instance.

Grounds :class:`babylon.dialectics.core.cylinder.AdjointCylinder` in the
solidarity subgraph that
:func:`babylon.engine.topology_monitor.extract_solidarity_subgraph`
extracts from ``WorldState``: an undirected graph of ``social_class``
nodes joined by SOLIDARITY edges. This specializes Lawvere's cohesion
quadruple :math:`\\Pi_0 \\dashv \\Delta \\dashv \\Gamma \\dashv \\nabla`
(pieces/discrete/points/codiscrete) to graphs on a fixed node set:

- :math:`\\Delta` (``embed_left``) — the edgeless graph: every node its
  own piece, full atomization, the skeleton pole :math:`\\Box`.
- :math:`\\Gamma` (``project``) — the underlying node set, forgetting
  every edge.
- :math:`\\nabla` (``embed_right``) — the complete graph: every pair of
  nodes joined, total unity, the sheaf pole :math:`\\bigcirc`.
- :math:`\\Pi_0` (:func:`pieces`) — connected components. This is a
  DIFFERENT functor from :math:`\\Gamma`: it quotients by connectivity
  rather than forgetting edges outright, so it lives outside
  :class:`~babylon.dialectics.core.cylinder.AdjointCylinder` (which only
  carries the :math:`\\Delta \\dashv \\Gamma \\dashv \\nabla` half of the
  quadruple) as its own function, computed rustworkx-native — originally
  NetworkX connected_components per the design contract
  (``project/06-lawverian-dialectics.md`` §4, pre-Amendment L).

:func:`atomization_index` reports the fraction of the graph's possible
splits that are realized, :math:`(|\\Pi_0(x)| - 1)/(|\\Gamma(x)| - 1)`:
1.0 when every node is its own component (full atomization), 0.0 when
one component spans every node (total unity) — the same poles the
cylinder's :meth:`balance
<babylon.dialectics.core.cylinder.AdjointCylinder.balance>` measures,
but read off :math:`\\Pi_0` (component count) rather than the
edge-symmetric-difference metric (edge density): the two move together
but are not the same number (a bridging edge between two components
moves both; a redundant edge inside one component moves only balance).

.. warning::
    "Cohesion" already means organizational cohesion elsewhere in
    Babylon; this package says "connectivity cylinder" / "atomization"
    instead (see :mod:`babylon.dialectics.core.cylinder`).

See Also:
    :func:`babylon.engine.topology_monitor.calculate_component_metrics`:
    the engine consumer re-grounded on :func:`pieces` (Phase B).
    :class:`babylon.engine.systems.solidarity.SolidaritySystem`: the
    system whose consciousness transmission drives the graph toward the
    sheaf pole (documented, not re-implemented, in Phase B).
"""

from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

import rustworkx as rx

from babylon.dialectics.core.cylinder import AdjointCylinder

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonUGraph

__all__ = ["atomization_index", "connectivity_cylinder", "pieces"]

NodeSet = frozenset[str]


def _edgeless(nodes: NodeSet) -> BabylonUGraph:
    """:math:`\\Delta` — the edgeless graph on ``nodes`` (skeleton pole)."""
    from babylon.engine.graph import BabylonUGraph

    graph = BabylonUGraph()
    graph.add_nodes_from(sorted(nodes))
    return graph


def _complete(nodes: NodeSet) -> BabylonUGraph:
    """:math:`\\nabla` — the complete graph on ``nodes`` (sheaf pole)."""
    graph = _edgeless(nodes)
    graph.add_edges_from(combinations(sorted(nodes), 2))
    return graph


def _nodes(graph: BabylonUGraph) -> NodeSet:
    """:math:`\\Gamma` — the underlying node set, forgetting edges."""
    return frozenset(graph.nodes())


def _edge_set(graph: BabylonUGraph) -> frozenset[frozenset[str]]:
    """Every edge of ``graph``, normalized to an unordered pair."""
    return frozenset(frozenset(edge) for edge in graph.edges())


def _edge_symmetric_difference(left: BabylonUGraph, right: BabylonUGraph) -> float:
    """The cylinder metric: size of the edge-set symmetric difference."""
    return float(len(_edge_set(left) ^ _edge_set(right)))


def connectivity_cylinder() -> AdjointCylinder[NodeSet, BabylonUGraph]:
    """Build the production connectivity cylinder over solidarity graphs.

    Returns:
        An :class:`AdjointCylinder` with base carrier ``S`` = frozenset
        of node ids and ambient carrier ``X`` = undirected
        :class:`~babylon.engine.graph.BabylonUGraph`: ``embed_left`` is the edgeless graph
        (:math:`\\Delta`), ``embed_right`` is the complete graph
        (:math:`\\nabla`), ``project`` is the node set (:math:`\\Gamma`),
        and ``metric`` is the size of the edge-set symmetric difference.

    Example:
        >>> cyl = connectivity_cylinder()
        >>> cyl.retracts(frozenset({"a", "b", "c"}))
        True
    """
    return AdjointCylinder(
        embed_left=_edgeless,
        project=_nodes,
        embed_right=_complete,
        metric=_edge_symmetric_difference,
    )


def pieces(graph: BabylonUGraph) -> tuple[NodeSet, ...]:
    """:math:`\\Pi_0(x)` — connected components, deterministically ordered.

    Computed rustworkx-native on :class:`BabylonUGraph` (Amendment L).
    The min-element ordering contract makes the result independent of
    the library's traversal order.

    Args:
        graph: An undirected graph, typically a solidarity subgraph from
            :func:`babylon.engine.topology_monitor.extract_solidarity_subgraph`.

    Returns:
        Each connected component as a ``frozenset`` of node ids, ordered
        by the component's minimum element — stable regardless of
        traversal or insertion order.

    Example:
        >>> from babylon.engine.graph import BabylonUGraph
        >>> g = BabylonUGraph()
        >>> g.add_nodes_from(["b", "a", "c"])
        >>> g.add_edge("b", "c")
        >>> pieces(g) == (frozenset({"a"}), frozenset({"b", "c"}))
        True
    """
    components = (
        frozenset(graph.id_of(index) for index in component)
        for component in rx.connected_components(graph.core)
    )
    return tuple(sorted(components, key=lambda piece: min(piece)))


def atomization_index(graph: BabylonUGraph) -> float:
    """Fraction of possible splits realized: :math:`(|\\Pi_0|-1)/(|\\Gamma|-1)`.

    1.0 means every node is its own component (full atomization, the
    skeleton pole); 0.0 means a single component spans every node (total
    unity, the sheaf pole). Degenerate at 0 or 1 nodes, where there is
    nothing left to split — defined as 0.0 per the design contract.

    Args:
        graph: An undirected graph, typically a solidarity subgraph.

    Returns:
        The atomization index in [0, 1].

    Example:
        >>> from babylon.engine.graph import BabylonUGraph
        >>> g = BabylonUGraph()
        >>> g.add_nodes_from(["a", "b", "c"])
        >>> atomization_index(g)
        1.0
    """
    total_nodes = graph.number_of_nodes()
    if total_nodes <= 1:
        return 0.0
    num_pieces = len(pieces(graph))
    return (num_pieces - 1) / (total_nodes - 1)
