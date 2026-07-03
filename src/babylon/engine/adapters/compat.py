"""Structural typing seam shared by graph backends.

``CompatGraph`` is the read/write surface the adapter mixins and
subgraph helpers require of a backing graph.
It is satisfied structurally by BOTH ``networkx.DiGraph`` and
:class:`babylon.engine.graph.BabylonGraph`, which is what lets
``QueryMixin`` / ``AggregationMixin`` / ``SubgraphFilterBuilder`` /
``SubgraphView`` run unchanged on either backend during the Amendment L
substrate migration.

Verb members (``add_edge``, ``remove_node``, ...) are typed as
``Any``-returning properties rather than methods: the two backends'
call-compatible signatures differ in parameter *names* (NetworkX uses
``u_of_edge``/``node_for_adding``), which strict structural method
matching would reject. A property read of a bound method satisfies the
member; calls go through as ``Any``.
"""

from __future__ import annotations

from typing import Any, Protocol


class CompatGraph(Protocol):
    """Backing-graph surface required by the adapter layer.

    ``nodes`` supports iteration over ids and ``nodes[id]`` payload access;
    ``edges`` supports the nx call form ``edges(data=True)``.
    """

    @property
    def nodes(self) -> Any:
        """Node view: iterable of ids, indexable to attribute dicts."""
        ...

    @property
    def edges(self) -> Any:
        """Edge view: callable as ``edges(data=True)`` yielding triples."""
        ...

    @property
    def graph(self) -> Any:
        """Graph-level attribute dict."""
        ...

    @property
    def add_node(self) -> Any:
        """``add_node(node_id, **attributes)``."""
        ...

    @property
    def remove_node(self) -> Any:
        """``remove_node(node_id)``."""
        ...

    @property
    def add_edge(self) -> Any:
        """``add_edge(source, target, **attributes)``."""
        ...

    @property
    def remove_edge(self) -> Any:
        """``remove_edge(source, target)``."""
        ...

    @property
    def has_edge(self) -> Any:
        """``has_edge(source, target) -> bool``."""
        ...

    @property
    def successors(self) -> Any:
        """``successors(node_id)`` iterator of out-neighbors."""
        ...

    @property
    def predecessors(self) -> Any:
        """``predecessors(node_id)`` iterator of in-neighbors."""
        ...

    @property
    def in_edges(self) -> Any:
        """``in_edges(node_id, data=...)`` incoming edge tuples."""
        ...

    @property
    def out_edges(self) -> Any:
        """``out_edges(node_id, data=...)`` outgoing edge tuples."""
        ...

    def __contains__(self, node_id: object) -> bool:
        """Node membership test."""
        ...

    def number_of_nodes(self) -> int:
        """Total node count."""
        ...

    def number_of_edges(self) -> int:
        """Total edge count."""
        ...

    def subgraph(self, nodes: Any) -> Any:
        """Induced subgraph on ``nodes`` (shared attribute dicts)."""
        ...

    def edge_subgraph(self, edges: Any) -> Any:
        """Subgraph induced by the given edges."""
        ...

    def copy(self) -> Any:
        """Independent copy with copied attribute dicts."""
        ...

    def remove_edges_from(self, edges: Any, /) -> None:
        """Bulk edge removal; missing edges are ignored."""
        ...
