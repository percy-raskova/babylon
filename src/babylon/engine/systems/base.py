"""SystemBase — abstract base class for simulation Systems (ADR-003).

Lifts the shared scaffolding that the 22 System implementations duplicate:
- name declaration (ClassVar)
- the GraphProtocol narrowing guard (raw nx graphs rejected per Amendment L)
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
        :meth:`_wrap_graph` — assert the graph satisfies GraphProtocol.
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
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply system logic to the world graph (in-place mutation).

        The signature matches :class:`babylon.engine.systems.protocol.System`
        exactly. The engine (and all test fixtures) pass a
        :class:`~babylon.engine.graph.BabylonGraph`, which satisfies
        ``GraphProtocol``.
        """

    @staticmethod
    def _wrap_graph(graph: GraphProtocol) -> GraphProtocol:
        """Return ``graph`` unchanged if it satisfies :class:`GraphProtocol`.

        Raw NetworkX graphs are no longer supported — the NetworkXAdapter
        seam closed when Amendment L made BabylonGraph the sole
        implementation. Construct a
        :class:`~babylon.engine.graph.BabylonGraph` instead.

        Raises:
            TypeError: If ``graph`` does not satisfy :class:`GraphProtocol`.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            raise TypeError(
                "raw networkx graphs are no longer supported; construct "
                f"babylon.engine.graph.BabylonGraph (got {type(graph).__name__})"
            )
        return graph

    @staticmethod
    def _compat_graph(
        graph: GraphProtocol,
    ) -> BabylonGraph:
        """Narrow a ``step()`` graph argument to the nx-compat world surface.

        Helper (Amendment L) for systems whose subsystem helpers read/write
        raw payload dicts (``graph.nodes(data=True)``,
        ``graph.edges[u, v][...]``) rather than protocol methods —
        BabylonGraph's permanent authoring surface (constitution II.12).

        Raises:
            TypeError: If the backend does not expose that surface.
        """
        from babylon.engine.graph import BabylonGraph

        if isinstance(graph, BabylonGraph):
            return graph
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
                or a raw attribute ``dict`` (e.g., a node payload dict from
                ``graph.nodes[id]``, or ``GraphNode.attributes`` already
                unwrapped).
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
