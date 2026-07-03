"""BabylonGraph: the rustworkx-backed graph substrate (Amendment L, ADR052).

One class is BOTH the :class:`~babylon.engine.graph_protocol.GraphProtocol`
implementation AND the authoring API (constitution II.12). The rustworkx
core provides Rust-speed algorithms; insertion-ordered Python mirrors
provide NetworkX's exact iteration contract so event ordering — and with
it the determinism hash (constitution III.7) — is byte-identical across
the substrate swap.

Internal structure:

* ``_core`` — ``rx.PyDiGraph(multigraph=False)`` (or ``PyGraph`` for the
  undirected sibling). Consulted ONLY for algorithms; never iterated for
  ordering (rustworkx reuses node indices after removal, so raw index
  order is not insertion order).
* ``_ids`` / ``_index_to_id`` — insertion-ordered str<->int bimap.
* ``_node_payload`` / ``_edge_payload`` — the SAME dict objects held as
  rustworkx payloads, keyed by id: id-keyed CRUD is a native dict hit
  with reference semantics.
* ``_adj`` / ``_pred`` — per-source insertion-ordered adjacency mirrors;
  ``edges(data=True)`` iterates them in NetworkX's exact order.

Normalization: node types live under ``_node_type`` only (no raw reader
of the public key exists outside the graph layer). Edge payloads carry
BOTH ``edge_type`` (public — read raw across ooda/bifurcation/persistence
and ``WorldState.from_graph``) and ``_edge_type`` (internal protocol key),
synced at insert — replacing ``NetworkXAdapter.wrap()``'s per-tick
mirroring sweep. Protocol materialization (``GraphEdge``) strips both.

Discovered rustworkx 0.17 semantics this design compensates for (pinned
in ``tests/unit/engine/test_rustworkx_spike.py``): ``add_edge`` REPLACES
payloads on existing pairs (we merge explicitly, nx semantics); node
indices are REUSED after removal; ``subgraph``/``copy`` SHARE payload
dicts (our ``copy()`` copies them, nx semantics).

See Also:
    :class:`babylon.engine.adapters.inmemory_adapter.NetworkXAdapter`:
        The legacy reference implementation this class replaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, cast, overload

import rustworkx as rx

from babylon.engine.adapters.aggregation_mixin import AggregationMixin
from babylon.engine.adapters.query_mixin import QueryMixin
from babylon.engine.adapters.subgraph_filter import SubgraphFilterBuilder
from babylon.engine.adapters.subgraph_view import SubgraphView
from babylon.engine.graph_views import EdgesView, NodesView
from babylon.models.graph import GraphEdge, GraphNode, TraversalResult

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from babylon.models.graph import TraversalQuery

NodePayload = dict[str, Any]
EdgePayload = dict[str, Any]
RxDiGraph = "rx.PyDiGraph[NodePayload, EdgePayload]"
RxGraph = "rx.PyGraph[NodePayload, EdgePayload]"


class _GraphCore:
    """Shared id-keyed machinery over a rustworkx core.

    Concrete subclasses set ``_DIRECTED`` and gain the full nx-compat
    authoring surface: dual-signature ``add_node``/``add_edge``,
    insertion-ordered ``nodes``/``edges`` views, subgraph/copy, and the
    id<->index accessors algorithm code uses to call rustworkx directly.
    """

    _DIRECTED: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self._core: (
            rx.PyDiGraph[NodePayload, EdgePayload] | rx.PyGraph[NodePayload, EdgePayload]
        ) = rx.PyDiGraph(multigraph=False) if self._DIRECTED else rx.PyGraph(multigraph=False)
        self._ids: dict[str, int] = {}
        self._index_to_id: dict[int, str] = {}
        self._node_payload: dict[str, NodePayload] = {}
        self._edge_payload: dict[tuple[str, str], EdgePayload] = {}
        self._adj: dict[str, dict[str, None]] = {}
        self._pred: dict[str, dict[str, None]] = {}
        self._graph_attrs: dict[str, Any] = {}
        # Compat seam: mixins and legacy `getattr(graph, "_graph", graph)`
        # unwraps reach the backing store through `_graph`; we ARE it.
        self._graph: Any = self

    # ── payload normalization ────────────────────────────────────────────

    @staticmethod
    def _normalize_node_payload(node_type: str | None, attributes: dict[str, Any]) -> NodePayload:
        """Fold type markers into the canonical ``_node_type`` key."""
        payload = dict(attributes)
        public = payload.pop("node_type", None)
        if node_type is not None:
            payload["_node_type"] = node_type
        elif "_node_type" not in payload and public is not None:
            payload["_node_type"] = public
        return payload

    @staticmethod
    def _normalize_edge_payload(
        edge_type: str | None, weight: float | None, attributes: dict[str, Any]
    ) -> EdgePayload:
        """Sync the DUAL edge-type keys and fold in the weight marker.

        Edge payloads carry BOTH ``edge_type`` (public — read raw by ~25
        call sites across ooda/bifurcation/persistence/from_graph) and
        ``_edge_type`` (internal — the protocol lookup key). This mirrors
        today's production reality, where ``to_graph()`` writes the public
        key and ``wrap()`` mirrors it internally each tick.
        """
        payload = dict(attributes)
        if edge_type is not None:
            payload["_edge_type"] = edge_type
            payload["edge_type"] = edge_type
            payload["weight"] = 1.0 if weight is None else weight
            return payload
        if "_edge_type" not in payload and "edge_type" in payload:
            payload["_edge_type"] = payload["edge_type"]
        elif "edge_type" not in payload and "_edge_type" in payload:
            payload["edge_type"] = payload["_edge_type"]
        if weight is not None:
            payload["weight"] = weight
        return payload

    # ── low-level inserts (assume validity; keep all mirrors in sync) ────

    def _insert_node(self, node_id: str, payload: NodePayload) -> None:
        index = self._core.add_node(payload)
        self._ids[node_id] = index
        self._index_to_id[index] = node_id
        self._node_payload[node_id] = payload
        self._adj[node_id] = {}
        self._pred[node_id] = {}

    def _ensure_node(self, node_id: str) -> None:
        if node_id not in self._ids:
            self._insert_node(node_id, {})

    def _insert_edge(self, source: str, target: str, payload: EdgePayload) -> None:
        self._core.add_edge(self._ids[source], self._ids[target], payload)
        self._edge_payload[(source, target)] = payload
        self._adj[source][target] = None
        if self._DIRECTED:
            self._pred[target][source] = None
        else:
            self._adj[target][source] = None

    def _delete_edge(self, key: tuple[str, str]) -> None:
        source, target = key
        del self._edge_payload[key]
        self._adj[source].pop(target, None)
        if self._DIRECTED:
            self._pred[target].pop(source, None)
        else:
            self._adj[target].pop(source, None)
        self._core.remove_edge(self._ids[source], self._ids[target])

    # ── node CRUD (dual signature: protocol positional / nx keyword) ─────

    def add_node(self, node_id: str, node_type: str | None = None, **attributes: Any) -> None:
        """Add (or nx-style merge into) a node.

        Protocol form: ``add_node(id, "social_class", wealth=1.0)``.
        Authoring form: ``add_node(id, wealth=1.0, _node_type="social_class")``.
        Adding an existing node merges attributes (NetworkX semantics).
        """
        payload = self._normalize_node_payload(node_type, attributes)
        existing = self._node_payload.get(node_id)
        if existing is not None:
            existing.update(payload)
            return
        self._insert_node(node_id, payload)

    def add_nodes_from(self, nodes: Iterable[Any]) -> None:
        """nx-style bulk add: plain ids or ``(id, attr_dict)`` pairs."""
        for entry in nodes:
            if isinstance(entry, tuple):
                node_id, attrs = entry
                self.add_node(node_id, **attrs)
            else:
                self.add_node(entry)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all incident edges.

        Raises:
            KeyError: If the node does not exist.
        """
        if node_id not in self._ids:
            raise KeyError(f"Node '{node_id}' does not exist")
        for target in list(self._adj[node_id]):
            key = self._stored_edge_key(node_id, target)
            if key is not None:
                del self._edge_payload[key]
            if self._DIRECTED:
                self._pred[target].pop(node_id, None)
            else:
                self._adj[target].pop(node_id, None)
        if self._DIRECTED:
            for source in list(self._pred[node_id]):
                self._edge_payload.pop((source, node_id), None)
                self._adj[source].pop(node_id, None)
            del self._pred[node_id]
        del self._adj[node_id]
        index = self._ids.pop(node_id)
        del self._index_to_id[index]
        del self._node_payload[node_id]
        self._core.remove_node(index)

    def remove_nodes_from(self, nodes: Iterable[str]) -> None:
        """nx-style bulk removal; silently skips missing nodes."""
        for node_id in nodes:
            if node_id in self._ids:
                self.remove_node(node_id)

    # ── edge CRUD (dual signature) ────────────────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str | None = None,
        weight: float | None = None,
        **attributes: Any,
    ) -> None:
        """Add (or nx-style merge into) a directed edge.

        Protocol form: ``add_edge(u, v, "SOLIDARITY", weight=0.8, ...)``
        (weight defaults to 1.0). Authoring form: ``add_edge(u, v,
        tension=0.2, edge_type="WAGES")`` — the public type key is folded
        into ``_edge_type``. Missing endpoints are auto-created and an
        existing (source, target) pair is merged, both NetworkX semantics.
        """
        payload = self._normalize_edge_payload(edge_type, weight, attributes)
        key = self._stored_edge_key(source, target)
        if key is not None:
            self._edge_payload[key].update(payload)
            return
        self._ensure_node(source)
        self._ensure_node(target)
        self._insert_edge(source, target, payload)

    def add_edges_from(self, edges: Iterable[Any]) -> None:
        """nx-style bulk add: ``(u, v)`` or ``(u, v, attr_dict)`` tuples."""
        for entry in edges:
            if len(entry) == 3:
                source, target, attrs = entry
                self.add_edge(source, target, **attrs)
            else:
                source, target = entry
                self.add_edge(source, target)

    def remove_edge(self, source: str, target: str, edge_type: str | None = None) -> None:
        """Remove an edge; with ``edge_type`` given, verify the type first.

        Raises:
            KeyError: If the edge does not exist, or exists with a
                different type when ``edge_type`` is provided.
        """
        key = self._stored_edge_key(source, target)
        if key is None:
            raise KeyError(f"Edge ({source}, {target}) does not exist")
        if edge_type is not None and self._edge_payload[key].get("_edge_type") != edge_type:
            raise KeyError(f"Edge ({source}, {target}) exists but type is not '{edge_type}'")
        self._delete_edge(key)

    def remove_edges_from(self, edges: Iterable[tuple[str, str]]) -> None:
        """nx-style bulk removal; silently skips missing edges."""
        for source, target in edges:
            key = self._stored_edge_key(source, target)
            if key is not None:
                self._delete_edge(key)

    # ── edge lookups ──────────────────────────────────────────────────────

    def _stored_edge_key(self, source: str, target: str) -> tuple[str, str] | None:
        if (source, target) in self._edge_payload:
            return (source, target)
        if not self._DIRECTED and (target, source) in self._edge_payload:
            return (target, source)
        return None

    def _edge_payload_of(self, source: str, target: str) -> EdgePayload:
        key = self._stored_edge_key(source, target)
        if key is None:
            raise KeyError(f"Edge ({source}, {target}) does not exist")
        return self._edge_payload[key]

    def has_edge(self, source: str, target: str) -> bool:
        """Return True if the edge exists (either orientation if undirected)."""
        return self._stored_edge_key(source, target) is not None

    def get_edge_data(
        self, source: str, target: str, default: EdgePayload | None = None
    ) -> EdgePayload | None:
        """nx-style live edge payload lookup, or ``default`` if absent."""
        key = self._stored_edge_key(source, target)
        if key is None:
            return default
        return self._edge_payload[key]

    def _iter_edge_pairs(self) -> Iterator[tuple[str, str]]:
        """Yield edges in NetworkX's iteration order.

        Directed: sources in node-insertion order, targets in per-source
        adjacency insertion order (the III.7 determinism contract).
        Undirected: stored keys in edge-insertion order.
        """
        if self._DIRECTED:
            for source in self._ids:
                for target in self._adj[source]:
                    yield (source, target)
        else:
            yield from self._edge_payload

    # ── views & dunder surface ────────────────────────────────────────────

    @property
    def nodes(self) -> NodesView:
        """nx-style node view (iteration, ``[id]``, ``(data=True)``)."""
        return NodesView(self)

    @property
    def edges(self) -> EdgesView:
        """nx-style edge view (iteration, ``[(u, v)]``, ``(data=True)``)."""
        return EdgesView(self)

    @property
    def graph(self) -> dict[str, Any]:
        """nx-style graph-level attribute dict (live)."""
        return self._graph_attrs

    def number_of_nodes(self) -> int:
        """Return the node count."""
        return len(self._ids)

    @overload
    def degree(self, node_id: str) -> int: ...

    @overload
    def degree(self, node_id: None = ...) -> list[tuple[str, int]]: ...

    def degree(self, node_id: str | None = None) -> int | list[tuple[str, int]]:
        """nx-style degree: one node's degree, or (node, degree) pairs.

        Directed hosts count in+out degree (nx.DiGraph parity); self-loop
        double-counting on undirected hosts is not reproduced (no
        analytics call site uses self-loops).
        """
        if node_id is not None:
            degree = len(self._adj[node_id])
            if self._DIRECTED:
                degree += len(self._pred[node_id])
            return degree
        return [(node, self.degree(node)) for node in self._ids]

    def number_of_edges(self) -> int:
        """Return the edge count."""
        return len(self._edge_payload)

    def __contains__(self, node_id: object) -> bool:
        return node_id in self._ids

    def __len__(self) -> int:
        return len(self._ids)

    def __iter__(self) -> Iterator[str]:
        return iter(self._ids)

    def index_of(self, node_id: str) -> int:
        """Return the rustworkx index for a node id (algorithm seam)."""
        return self._ids[node_id]

    def id_of(self, index: int) -> str:
        """Return the node id for a rustworkx index (algorithm seam)."""
        return self._index_to_id[index]

    # ── structural copies ─────────────────────────────────────────────────

    def copy(self) -> Self:
        """Return an independent copy (payload dicts copied — nx semantics).

        rustworkx's own ``copy()`` shares payload objects; this one does
        not, matching ``nx.DiGraph.copy()``'s attribute-dict copying.
        """
        clone = type(self)()
        for node_id in self._ids:
            clone._insert_node(node_id, dict(self._node_payload[node_id]))
        for (source, target), payload in self._edge_payload.items():
            clone._insert_edge(source, target, dict(payload))
        clone._graph_attrs = dict(self._graph_attrs)
        return clone

    def subgraph(self, nodes: Iterable[str]) -> Self:
        """Return the induced subgraph SHARING payload dicts (nx-view parity).

        Mutating a node/edge payload through the subgraph is visible in the
        parent, exactly like a NetworkX subgraph view. Call ``.copy()`` on
        the result for isolation.
        """
        keep = {n for n in nodes if n in self._ids}
        view = type(self)()
        for node_id in self._ids:
            if node_id in keep:
                view._insert_node(node_id, self._node_payload[node_id])
        for (source, target), payload in self._edge_payload.items():
            if source in keep and target in keep:
                view._insert_edge(source, target, payload)
        view._graph_attrs = self._graph_attrs
        return view

    def edge_subgraph(self, edges: Iterable[tuple[str, str]]) -> Self:
        """Return the subgraph induced by ``edges`` (shared payloads)."""
        view = type(self)()
        for source, target in edges:
            key = self._stored_edge_key(source, target)
            if key is None:
                continue
            for endpoint in key:
                if endpoint not in view._ids:
                    view._insert_node(endpoint, self._node_payload[endpoint])
            view._insert_edge(key[0], key[1], self._edge_payload[key])
        view._graph_attrs = self._graph_attrs
        return view

    # ── shared algorithm helpers ──────────────────────────────────────────

    def _component_id_sets(self) -> list[list[str]]:
        """Connected components as id lists, in NetworkX discovery order.

        Components are ordered by first-seen node insertion position and
        each component's nodes are listed in insertion order — strictly
        deterministic (NetworkX yields sets, whose order is hash-salted).
        """
        if isinstance(self._core, rx.PyGraph):
            raw = rx.connected_components(self._core)
        else:
            raw = rx.weakly_connected_components(self._core)
        position = {node_id: pos for pos, node_id in enumerate(self._ids)}
        components = [
            sorted((self._index_to_id[index] for index in comp), key=position.__getitem__)
            for comp in raw
        ]
        components.sort(key=lambda ids: position[ids[0]])
        return components

    def _bounded_bfs_nodes(self, start: str, max_depth: int) -> set[str]:
        """Nodes within ``max_depth`` hops of ``start`` (directed out-edges)."""
        visited = {start}
        frontier = [start]
        for _ in range(max_depth):
            next_frontier: list[str] = []
            for node in frontier:
                for neighbor in self._adj[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.append(neighbor)
            if not next_frontier:
                break
            frontier = next_frontier
        return visited

    def _bounded_dfs_nodes(self, start: str, max_depth: int) -> set[str]:
        """Nodes within ``max_depth`` DFS hops of ``start``."""
        visited = {start}
        stack = [(start, 0)]
        # Loop bound: each node is pushed at most once (visited-marked at
        # push), so iterations <= number_of_nodes().
        while stack:
            node, depth = stack.pop()
            if depth >= max_depth:
                continue
            for neighbor in self._adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append((neighbor, depth + 1))
        return visited

    def _bfs_path(self, source: str, target: str) -> list[str] | None:
        """Unweighted shortest path following adjacency insertion order.

        Mirrors NetworkX BFS tie-breaking (adjacency order) so equal-length
        path choice is stable across the substrate swap.
        """
        if source == target:
            return [source]
        parents = {source: source}
        frontier = [source]
        # Loop bound: each node enters `parents` at most once, so total
        # frontier work is <= number_of_nodes() + number_of_edges().
        while frontier:
            next_frontier: list[str] = []
            for node in frontier:
                for neighbor in self._adj[node]:
                    if neighbor in parents:
                        continue
                    parents[neighbor] = node
                    if neighbor == target:
                        path = [target]
                        # Loop bound: parent chain length <= number_of_nodes().
                        while path[-1] != source:
                            path.append(parents[path[-1]])
                        path.reverse()
                        return path
                    next_frontier.append(neighbor)
            frontier = next_frontier
        return None


class BabylonUGraph(_GraphCore):
    """Undirected analytics sibling of :class:`BabylonGraph`.

    Used by the analytics layer (topology monitor, resilience, sparrow,
    curvature) as the ``nx.Graph`` replacement. Algorithms reach the
    rustworkx core through :attr:`core` / :meth:`index_of` / :meth:`id_of`.
    """

    _DIRECTED: ClassVar[bool] = False

    @property
    def core(self) -> rx.PyGraph[NodePayload, EdgePayload]:
        """The rustworkx ``PyGraph`` — the algorithm seam."""
        return cast("rx.PyGraph[NodePayload, EdgePayload]", self._core)

    def neighbors(self, node_id: str) -> Iterator[str]:
        """Iterate neighbors in adjacency insertion order."""
        return iter(self._adj[node_id])


class BabylonGraph(_GraphCore, AggregationMixin, QueryMixin):
    """Directed world graph: GraphProtocol implementation + authoring API.

    ``isinstance(BabylonGraph(), GraphProtocol)`` holds, so
    ``SystemBase._wrap_graph`` passes instances through unchanged — no
    per-tick wrap/normalization sweep. The nx-compat surface (inherited
    from :class:`_GraphCore`) is the permanent authoring API per
    constitution II.12.

    Example:
        >>> g = BabylonGraph()
        >>> g.add_node("C001", "social_class", wealth=100.0)
        >>> g.get_node("C001").wealth
        100.0
    """

    _DIRECTED: ClassVar[bool] = True

    @property
    def core(self) -> rx.PyDiGraph[NodePayload, EdgePayload]:
        """The rustworkx ``PyDiGraph`` — the algorithm seam."""
        return cast("rx.PyDiGraph[NodePayload, EdgePayload]", self._core)

    # ── directed adjacency surface ────────────────────────────────────────

    def successors(self, node_id: str) -> Iterator[str]:
        """Iterate out-neighbors in adjacency insertion order."""
        return iter(self._adj[node_id])

    def predecessors(self, node_id: str) -> Iterator[str]:
        """Iterate in-neighbors in adjacency insertion order."""
        return iter(self._pred[node_id])

    def neighbors(self, node_id: str) -> Iterator[str]:
        """nx.DiGraph parity: neighbors == successors."""
        return self.successors(node_id)

    @overload
    def out_edges(self, node_id: str, data: Literal[False] = ...) -> list[tuple[str, str]]: ...

    @overload
    def out_edges(
        self, node_id: str, data: Literal[True]
    ) -> list[tuple[str, str, EdgePayload]]: ...

    def out_edges(
        self, node_id: str, data: bool = False
    ) -> list[tuple[str, str]] | list[tuple[str, str, EdgePayload]]:
        """Outgoing edges of ``node_id``, optionally with live payloads."""
        if data:
            return [
                (node_id, target, self._edge_payload[(node_id, target)])
                for target in self._adj[node_id]
            ]
        return [(node_id, target) for target in self._adj[node_id]]

    @overload
    def in_edges(self, node_id: str, data: Literal[False] = ...) -> list[tuple[str, str]]: ...

    @overload
    def in_edges(self, node_id: str, data: Literal[True]) -> list[tuple[str, str, EdgePayload]]: ...

    def in_edges(
        self, node_id: str, data: bool = False
    ) -> list[tuple[str, str]] | list[tuple[str, str, EdgePayload]]:
        """Incoming edges of ``node_id``, optionally with live payloads."""
        if data:
            return [
                (source, node_id, self._edge_payload[(source, node_id)])
                for source in self._pred[node_id]
            ]
        return [(source, node_id) for source in self._pred[node_id]]

    def to_undirected(self) -> BabylonUGraph:
        """Undirected projection with copied payload dicts.

        On (u,v)/(v,u) collapse the last-iterated edge's data wins
        (NetworkX parity). Payload copies are shallow (analytics graphs
        are read-mostly), where NetworkX deep-copies.
        """
        undirected = BabylonUGraph()
        for node_id in self._ids:
            undirected._insert_node(node_id, dict(self._node_payload[node_id]))
        for (source, target), payload in self._edge_payload.items():
            key = undirected._stored_edge_key(source, target)
            if key is None:
                undirected._insert_edge(source, target, dict(payload))
            else:
                existing = undirected._edge_payload[key]
                existing.clear()
                existing.update(payload)
        undirected._graph_attrs = dict(self._graph_attrs)
        return undirected

    # ── GraphProtocol: node/edge model materialization ────────────────────

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node as a :class:`GraphNode`, or None if absent."""
        payload = self._node_payload.get(node_id)
        if payload is None:
            return None
        data = dict(payload)
        node_type = data.pop("_node_type", "unknown")
        return GraphNode(id=node_id, node_type=node_type, attributes=data)

    def update_node(self, node_id: str, **attributes: Any) -> None:
        """Merge attributes into an existing node.

        Raises:
            KeyError: If the node does not exist.
        """
        payload = self._node_payload.get(node_id)
        if payload is None:
            raise KeyError(f"Node '{node_id}' does not exist")
        payload.update(attributes)

    def get_edge(self, source: str, target: str, edge_type: str) -> GraphEdge | None:
        """Retrieve an edge as a :class:`GraphEdge` if its type matches."""
        key = self._stored_edge_key(source, target)
        if key is None:
            return None
        data = dict(self._edge_payload[key])
        if data.get("_edge_type") != edge_type:
            return None
        data.pop("_edge_type", None)
        data.pop("edge_type", None)
        weight = data.pop("weight", 1.0)
        return GraphEdge(
            source_id=source,
            target_id=target,
            edge_type=edge_type,
            weight=weight,
            attributes=data,
        )

    def update_edge(self, source: str, target: str, edge_type: str, **attributes: Any) -> None:
        """Merge attributes into an existing edge of the given type.

        Raises:
            KeyError: If the edge does not exist or its type differs.
        """
        key = self._stored_edge_key(source, target)
        if key is None:
            raise KeyError(f"Edge ({source}, {target}) does not exist")
        payload = self._edge_payload[key]
        if payload.get("_edge_type") != edge_type:
            raise KeyError(f"Edge ({source}, {target}) exists but type is not '{edge_type}'")
        payload.update(attributes)

    # ── GraphProtocol: traversal ──────────────────────────────────────────

    def get_neighborhood(
        self,
        node_id: str,
        radius: int = 1,
        edge_types: set[str] | None = None,
        direction: Literal["out", "in", "both"] = "out",
    ) -> SubgraphView:
        """All nodes within ``radius`` hops, as a :class:`SubgraphView`.

        Raises:
            KeyError: If the center node does not exist.
        """
        if node_id not in self._ids:
            raise KeyError(f"Node '{node_id}' does not exist")

        nodes: set[str] = {node_id}
        frontier: set[str] = {node_id}
        for _ in range(radius):
            new_frontier: set[str] = set()
            for node in frontier:
                if direction in ("out", "both"):
                    for neighbor in self._adj[node]:
                        data = self._edge_payload[(node, neighbor)]
                        if edge_types is None or data.get("_edge_type") in edge_types:
                            new_frontier.add(neighbor)
                if direction in ("in", "both"):
                    for neighbor in self._pred[node]:
                        data = self._edge_payload[(neighbor, node)]
                        if edge_types is None or data.get("_edge_type") in edge_types:
                            new_frontier.add(neighbor)
            nodes |= new_frontier
            frontier = new_frontier

        return SubgraphView(self.subgraph(nodes))

    def execute_traversal(self, query: TraversalQuery) -> TraversalResult:
        """Execute a generic traversal query (adapter-parity strategies).

        Raises:
            ValueError: If ``query.query_type`` is not supported.
        """
        strategies: dict[str, Callable[[TraversalQuery], TraversalResult]] = {
            "connected_components": self._execute_components_query,
            "percolation": self._execute_components_query,
            "shortest_path": self._execute_shortest_path_query,
            "bfs": self._execute_bfs_query,
            "dfs": self._execute_dfs_query,
            "reachability": self._execute_reachability_query,
        }
        strategy = strategies.get(query.query_type)
        if strategy is None:
            raise ValueError(f"Unsupported query type: {query.query_type}")
        return strategy(query)

    def _build_filtered_subgraph(
        self, query: TraversalQuery, include_all_nodes: bool = False
    ) -> BabylonGraph:
        built = (
            SubgraphFilterBuilder(self)
            .from_query(query, include_all_nodes=include_all_nodes)
            .build()
        )
        return cast("BabylonGraph", built)

    def _execute_components_query(self, query: TraversalQuery) -> TraversalResult:
        filtered = self._build_filtered_subgraph(query)
        components = filtered._component_id_sets()
        components.sort(key=len, reverse=True)
        return TraversalResult(
            nodes=[node_id for comp in components for node_id in comp],
            components=components,
            component_sizes=[len(comp) for comp in components],
        )

    def _execute_shortest_path_query(self, query: TraversalQuery) -> TraversalResult:
        if not query.start_nodes or not query.target_nodes:
            return TraversalResult()
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        paths: list[list[str]] = []
        for source in query.start_nodes:
            for target in query.target_nodes:
                if source not in filtered._ids or target not in filtered._ids:
                    continue
                path = filtered._bfs_path(source, target)
                if path is not None:
                    paths.append(path)
        all_nodes: set[str] = set()
        for path in paths:
            all_nodes.update(path)
        return TraversalResult(nodes=list(all_nodes), paths=paths)

    def _execute_bfs_query(self, query: TraversalQuery) -> TraversalResult:
        if not query.start_nodes:
            return TraversalResult()
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        visited: set[str] = set()
        for start in query.start_nodes:
            if start not in filtered._ids:
                continue
            if query.max_depth is not None:
                visited.update(filtered._bounded_bfs_nodes(start, query.max_depth))
            else:
                reachable = rx.descendants(filtered.core, filtered._ids[start])
                visited.add(start)
                visited.update(filtered._index_to_id[index] for index in reachable)
        return TraversalResult(nodes=list(visited))

    def _execute_dfs_query(self, query: TraversalQuery) -> TraversalResult:
        if not query.start_nodes:
            return TraversalResult()
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        visited: set[str] = set()
        for start in query.start_nodes:
            if start not in filtered._ids:
                continue
            if query.max_depth is not None:
                visited.update(filtered._bounded_dfs_nodes(start, query.max_depth))
            else:
                reachable = rx.descendants(filtered.core, filtered._ids[start])
                visited.add(start)
                visited.update(filtered._index_to_id[index] for index in reachable)
        return TraversalResult(nodes=list(visited))

    def _execute_reachability_query(self, query: TraversalQuery) -> TraversalResult:
        if not query.start_nodes or not query.target_nodes:
            return TraversalResult()
        filtered = self._build_filtered_subgraph(query, include_all_nodes=True)
        reachable_targets: list[str] = []
        for source in query.start_nodes:
            for target in query.target_nodes:
                if (
                    source in filtered._ids
                    and target in filtered._ids
                    and target not in reachable_targets
                    and rx.has_path(filtered.core, filtered._ids[source], filtered._ids[target])
                ):
                    reachable_targets.append(target)
        return TraversalResult(
            nodes=reachable_targets,
            metadata={"reachable_count": len(reachable_targets)},
        )

    def shortest_path(
        self,
        source: str,
        target: str,
        edge_types: set[str] | None = None,
        weight_attr: str | None = None,
    ) -> list[str] | None:
        """Shortest path between two nodes, or None if no path exists.

        Unweighted paths use insertion-ordered BFS (NetworkX tie parity);
        weighted paths use rustworkx Dijkstra with missing weights read
        as 1.0 (NetworkX parity).
        """
        if source not in self._ids or target not in self._ids:
            return None
        if edge_types:
            pairs = [
                (u, v)
                for u, v in self._iter_edge_pairs()
                if self._edge_payload[(u, v)].get("_edge_type") in edge_types
            ]
            working = self.edge_subgraph(pairs)
            if source not in working._ids or target not in working._ids:
                return None
        else:
            working = self
        if weight_attr is None:
            return working._bfs_path(source, target)
        return working._dijkstra_path(source, target, weight_attr)

    def _dijkstra_path(self, source: str, target: str, weight_attr: str) -> list[str] | None:
        def cost(payload: EdgePayload) -> float:
            return float(payload.get(weight_attr, 1.0))

        target_index = self._ids[target]
        paths = rx.dijkstra_shortest_paths(
            self.core, self._ids[source], target=target_index, weight_fn=cost
        )
        if target_index not in paths:
            return None
        return [self._index_to_id[index] for index in paths[target_index]]

    # ── GraphProtocol: graph-level attributes ─────────────────────────────

    def get_graph_attr(self, key: str, default: Any = None) -> Any:
        """Retrieve a graph-level attribute (or ``default``)."""
        return self._graph_attrs.get(key, default)

    def set_graph_attr(self, key: str, value: Any) -> None:
        """Set a graph-level attribute."""
        self._graph_attrs[key] = value

    # ── Spec-070 balkanization extensions (adapter-parity) ────────────────

    def query_faction_influence_by_territory(
        self, territory_id: str
    ) -> list[tuple[str, float, str]]:
        """INFLUENCES edges at a Territory, influence desc / id asc."""
        if territory_id not in self._ids:
            return []
        rows: list[tuple[str, float, str]] = []
        for source in self._pred[territory_id]:
            data = self._edge_payload[(source, territory_id)]
            if data.get("_edge_type") != "influences":
                continue
            rows.append(
                (
                    source,
                    float(data.get("influence_level", 0.0)),
                    str(data.get("support_type", "ideological")),
                )
            )
        rows.sort(key=lambda row: (-row[1], row[0]))
        return rows

    def query_sovereign_claims(self, sovereign_id: str) -> list[tuple[str, float, str]]:
        """CLAIMS edges from a Sovereign, control desc / id asc."""
        if sovereign_id not in self._ids:
            return []
        rows: list[tuple[str, float, str]] = []
        for target in self._adj[sovereign_id]:
            data = self._edge_payload[(sovereign_id, target)]
            if data.get("_edge_type") != "claims":
                continue
            rows.append(
                (
                    target,
                    float(data.get("control_level", 0.0)),
                    str(data.get("legal_status", "de_jure")),
                )
            )
        rows.sort(key=lambda row: (-row[1], row[0]))
        return rows

    def query_territory_claims(self, territory_id: str) -> list[tuple[str, float, str]]:
        """CLAIMS edges at a Territory, control desc / id asc."""
        if territory_id not in self._ids:
            return []
        rows: list[tuple[str, float, str]] = []
        for source in self._pred[territory_id]:
            data = self._edge_payload[(source, territory_id)]
            if data.get("_edge_type") != "claims":
                continue
            rows.append(
                (
                    source,
                    float(data.get("control_level", 0.0)),
                    str(data.get("legal_status", "de_jure")),
                )
            )
        rows.sort(key=lambda row: (-row[1], row[0]))
        return rows

    def query_adjacent_territories(self, territory_id: str) -> list[str]:
        """Territories adjacent via ADJACENCY edges (direction-abstracted)."""
        if territory_id not in self._ids:
            return []
        neighbors: set[str] = set()
        for target in self._adj[territory_id]:
            if self._edge_payload[(territory_id, target)].get("_edge_type") == "adjacency":
                neighbors.add(target)
        for source in self._pred[territory_id]:
            if self._edge_payload[(source, territory_id)].get("_edge_type") == "adjacency":
                neighbors.add(source)
        return sorted(neighbors)

    def bulk_partition_claims(
        self,
        from_sovereign_id: str,
        to_sovereign_id: str,
        territories: set[str],
    ) -> int:
        """Atomically rewire CLAIMS edges between Sovereigns; O(K) in
        ``len(territories)`` per spec-070 FR-018.

        Raises:
            KeyError: If either sovereign does not exist.
        """
        if from_sovereign_id not in self._ids:
            raise KeyError(f"Sovereign '{from_sovereign_id}' does not exist")
        if to_sovereign_id not in self._ids:
            raise KeyError(f"Sovereign '{to_sovereign_id}' does not exist")
        rewired = 0
        for territory_id in territories:
            key = self._stored_edge_key(from_sovereign_id, territory_id)
            if key is None:
                continue
            edge_data = dict(self._edge_payload[key])
            if edge_data.get("_edge_type") != "claims":
                continue
            self._delete_edge(key)
            self.add_edge(to_sovereign_id, territory_id, **edge_data)
            rewired += 1
        return rewired

    def query_contiguous_component_under_predicate(
        self,
        territory_seed: str,
        predicate: Callable[[str], bool],
    ) -> set[str]:
        """BFS over ADJACENCY edges collecting predicate-satisfying
        Territories, lex-sorted per frontier level (determinism)."""
        if territory_seed not in self._ids:
            return set()
        if not predicate(territory_seed):
            return set()
        visited: set[str] = set()
        frontier: list[str] = [territory_seed]
        # Loop bound: each node enters `visited` at most once, so total
        # frontier work is bounded by the contiguous component size.
        while frontier:
            next_frontier: list[str] = []
            for node in sorted(frontier):
                if node in visited:
                    continue
                visited.add(node)
                for adjacent in sorted(self.query_adjacent_territories(node)):
                    if adjacent in visited:
                        continue
                    if predicate(adjacent):
                        next_frontier.append(adjacent)
            frontier = next_frontier
        return visited


__all__ = ["BabylonGraph", "BabylonUGraph"]
