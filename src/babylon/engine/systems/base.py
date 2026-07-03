"""SystemBase — abstract base class for simulation Systems (ADR-003).

Lifts the shared scaffolding that the 22 System implementations duplicate:
- name declaration (ClassVar)
- the auto-wrap of raw nx.DiGraph → GraphProtocol
- the read-node-attribute pattern with required=True diagnostics
- the publish-via-event-bus shorthand

The companion ``System`` Protocol in
:mod:`babylon.engine.systems.protocol` is preserved for structural typing
(tests, mocks). PEP 544 explicitly supports this dual-export pattern.

Per ADR-003 (Bundle 2 / Spec 059) and research.md D1 (22 Systems, not 23).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.event_bus import Event
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType
    from babylon.models.graph import GraphNode


class SystemBase(ABC):
    """Abstract base for all simulation Systems.

    Subclasses MUST set the ``name`` ClassVar and implement :meth:`step`.

    Helpers:
        :meth:`_wrap_graph` — auto-wrap raw nx.DiGraph as GraphProtocol if needed.
        :meth:`_read` — read a node attribute, raising ``KeyError`` when
            ``required=True`` and the attribute is absent (surfaces schema bugs
            at the read site, per CLAUDE.md "Common Gotchas").
        :meth:`_publish` — publish an event via the service container's bus.
    """

    name: ClassVar[str]
    creates_value: ClassVar[bool] = False

    @abstractmethod
    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply system logic to the world graph (in-place mutation).

        The signature matches :class:`babylon.engine.systems.protocol.System`
        exactly. In production the engine passes a
        :class:`~babylon.engine.graph.BabylonGraph` (which satisfies
        ``GraphProtocol``); legacy fixtures may pass a raw ``nx.DiGraph``.
        """

    @staticmethod
    def _wrap_graph(graph: nx.DiGraph[str] | GraphProtocol) -> GraphProtocol:
        """Return ``graph`` as a :class:`GraphProtocol`.

        Wraps a raw NetworkX DiGraph via :class:`NetworkXAdapter` if the input
        is not already a :class:`GraphProtocol`. Idempotent (BabylonGraph and
        already-wrapped adapters pass through unchanged).
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            return NetworkXAdapter.wrap(graph)
        return graph

    @staticmethod
    def _compat_graph(
        graph: nx.DiGraph[str] | GraphProtocol,
    ) -> BabylonGraph | nx.DiGraph[str]:
        """Narrow a ``step()`` graph argument to the nx-compat world surface.

        Transitional helper (Amendment L) for systems whose subsystem helpers
        still read/write raw payload dicts (``graph.nodes(data=True)``,
        ``graph.edges[u, v][...]``) rather than protocol methods. Both
        BabylonGraph and nx.DiGraph provide that surface; a wrapped
        NetworkXAdapter is unwrapped to its backing graph.

        Raises:
            TypeError: If the backend exposes neither surface.
        """
        from babylon.engine.graph import BabylonGraph

        if isinstance(graph, BabylonGraph):
            return graph
        import networkx as nx  # local: TYPE_CHECKING-only at module level

        if isinstance(graph, nx.DiGraph):
            return graph
        from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

        if isinstance(graph, NetworkXAdapter):
            return graph.underlying_graph
        raise TypeError(f"Unsupported graph backend: {type(graph).__name__}")

    @staticmethod
    def _read(
        source: GraphNode | dict[str, Any],
        key: str,
        *,
        required: bool = False,
        default: Any = None,
    ) -> Any:
        """Read attribute ``key`` from a :class:`GraphNode` or attribute dict.

        Args:
            source: Either a :class:`GraphNode` (read ``source.attributes``)
                or a raw attribute ``dict`` (e.g., the ``data`` dict held by a
                :class:`networkx.DiGraph` node, or ``GraphNode.attributes``
                already unwrapped).
            key: The attribute name.
            required: If True, raise :class:`KeyError` when the attribute is
                absent — surfaces schema bugs at the read site instead of
                silently substituting ``default`` (CLAUDE.md "Common Gotchas":
                ``data.get("s_bio", 0.0)`` masks missing-field bugs).
            default: Value returned when the attribute is absent and
                ``required`` is False.

        Returns:
            The attribute value, or ``default`` when absent (and ``required``
            is False).

        Raises:
            KeyError: When ``required`` is True and ``key`` is absent. The
                diagnostic names the attribute and (when available) the node
                id, per ADR-003.
        """
        if isinstance(source, dict):
            attrs = source
            node_id = source.get("_node_id") or source.get("id") or "<dict>"
        else:
            attrs = source.attributes
            node_id = source.id
        if required and key not in attrs:
            raise KeyError(f"Required attribute '{key}' missing on graph node '{node_id}'")
        return attrs.get(key, default)

    @staticmethod
    def _publish(services: ServiceContainer, event: Event) -> None:
        """Publish an event via ``services.event_bus``."""
        services.event_bus.publish(event)
