"""Insertion-ordered node/edge views for BabylonGraph's nx-compat surface.

These views reproduce the exact NetworkX read contract the codebase uses:
``graph.nodes`` iterates node IDs in insertion order and indexes into live
payload dicts; ``graph.edges`` iterates sources in node-insertion order,
then targets in per-source adjacency insertion order. That iteration
contract is what keeps event ordering byte-identical across the
NetworkX -> rustworkx substrate swap (constitution III.7, Amendment L).

See Also:
    :class:`babylon.engine.graph.BabylonGraph`: The host graph.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Literal, overload

if TYPE_CHECKING:
    from babylon.engine.graph import _GraphCore


class NodesView:
    """nx-style ``graph.nodes`` view.

    Supports iteration (insertion order), ``nodes[id]`` live-payload access,
    ``nodes(data=True)`` pairs, membership, ``len()``, and ``.get()`` —
    the complete node read surface the babylon codebase uses.

    Example:
        >>> from babylon.engine.graph import BabylonGraph
        >>> g = BabylonGraph()
        >>> g.add_node("C001", "social_class", wealth=10.0)
        >>> list(g.nodes)
        ['C001']
        >>> g.nodes["C001"]["wealth"]
        10.0
    """

    __slots__ = ("_host",)

    def __init__(self, host: _GraphCore) -> None:
        """Bind the view to its host graph.

        Args:
            host: The graph whose nodes this view exposes.
        """
        self._host = host

    def __iter__(self) -> Iterator[str]:
        return iter(self._host._ids)

    def __getitem__(self, node_id: str) -> dict[str, Any]:
        return self._host._node_payload[node_id]

    def __contains__(self, node_id: object) -> bool:
        return node_id in self._host._ids

    def __len__(self) -> int:
        return len(self._host._ids)

    @overload
    def get(self, node_id: str) -> dict[str, Any] | None: ...

    @overload
    def get(self, node_id: str, default: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, node_id: str, default: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Return the live payload dict for ``node_id``, or ``default``."""
        return self._host._node_payload.get(node_id, default)

    @overload
    def __call__(self, data: Literal[False] = ...) -> list[str]: ...

    @overload
    def __call__(self, data: Literal[True]) -> list[tuple[str, dict[str, Any]]]: ...

    def __call__(self, data: bool = False) -> list[str] | list[tuple[str, dict[str, Any]]]:
        """nx-style call form: ``nodes()`` ids or ``nodes(data=True)`` pairs."""
        if not data:
            return list(self._host._ids)
        payloads = self._host._node_payload
        return [(node_id, payloads[node_id]) for node_id in self._host._ids]


class EdgesView:
    """nx-style ``graph.edges`` view.

    Directed hosts iterate sources in node-insertion order, then targets in
    per-source adjacency insertion order — NetworkX's exact contract.
    Undirected hosts iterate stored edges in edge-insertion order (analytics
    graphs are never round-tripped, so their order carries no determinism
    hash exposure).

    Example:
        >>> from babylon.engine.graph import BabylonGraph
        >>> g = BabylonGraph()
        >>> g.add_edge("A", "B", "SOLIDARITY", weight=0.5)
        >>> g.edges[("A", "B")]["weight"]
        0.5
    """

    __slots__ = ("_host",)

    def __init__(self, host: _GraphCore) -> None:
        """Bind the view to its host graph.

        Args:
            host: The graph whose edges this view exposes.
        """
        self._host = host

    def __iter__(self) -> Iterator[tuple[str, str]]:
        return self._host._iter_edge_pairs()

    def __getitem__(self, key: tuple[str, str]) -> dict[str, Any]:
        return self._host._edge_payload_of(key[0], key[1])

    def __contains__(self, key: object) -> bool:
        if not (isinstance(key, tuple) and len(key) == 2):
            return False
        return self._host._stored_edge_key(key[0], key[1]) is not None

    def __len__(self) -> int:
        return self._host.number_of_edges()

    @overload
    def __call__(self, data: Literal[False] = ...) -> list[tuple[str, str]]: ...

    @overload
    def __call__(self, data: Literal[True]) -> list[tuple[str, str, dict[str, Any]]]: ...

    def __call__(
        self, data: bool = False
    ) -> list[tuple[str, str]] | list[tuple[str, str, dict[str, Any]]]:
        """nx-style call form: ``edges()`` pairs or ``edges(data=True)`` triples."""
        pairs = list(self._host._iter_edge_pairs())
        if not data:
            return pairs
        payload_of = self._host._edge_payload_of
        return [(source, target, payload_of(source, target)) for source, target in pairs]
