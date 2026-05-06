"""ContradictionFieldSystem — System #14 in materialist causality order.

Dialectical Field Topology (Feature 002): Computes named contradiction
fields at every social-class node per tick from existing economic
calculator outputs (wealth, subsistence, unearned_increment, population).

Reference: FR-001 (extensible field computation)
Reference: FR-002 (tick-keyed history persistence)
Reference: FR-011 (reads from economic outputs, no duplication)
Reference: R-003 (storage architecture)
Reference: R-006 (system ordering — position 14)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

logger = logging.getLogger(__name__)

# Maximum history window size (per spec FR-006)
_MAX_HISTORY_WINDOW = 3


class ContradictionFieldSystem:
    """Compute contradiction fields for all social-class nodes.

    Execution Order: 14 (after all 13 existing economic/consciousness systems)

    For each social-class node, computes normalized contradiction field values
    using the registered field computation callables from the FieldRegistry.
    Stores field values on nodes and maintains a rolling history window
    in persistent_data for temporal derivative computation by System #15.
    """

    name = "contradiction_field"

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Compute contradiction fields for all social-class nodes.

        Args:
            graph: Mutable graph (NetworkX or GraphProtocol).
            services: ServiceContainer with field_registry.
            context: TickContext or dict with tick and persistent_data.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        # Skip if no field registry configured
        registry = services.field_registry
        if registry is None:
            return

        field_names = registry.get_field_names()
        if not field_names:
            return

        # Access persistent_data for history and previous values
        persistent_data = _get_persistent_data(context)
        history: dict[str, dict[str, list[float]]] = persistent_data.setdefault(
            "contradiction_history", {}
        )
        previous_wealth: dict[str, float] = persistent_data.setdefault("_field_previous_wealth", {})
        previous_population: dict[str, float] = persistent_data.setdefault(
            "_field_previous_population", {}
        )

        # Get defines for bounds
        field_min = services.defines.contradiction_field.field_min
        field_max = services.defines.contradiction_field.field_max

        # Process all social_class nodes
        for node in graph.query_nodes(node_type="social_class"):
            node_id = node.id
            attrs = dict(node.attributes)

            # Inject previous values for derivative-based fields
            attrs["_previous_wealth"] = previous_wealth.get(node_id, attrs.get("wealth", 0.0))
            attrs["_previous_population"] = previous_population.get(
                node_id, attrs.get("population", 1)
            )

            # Compute fields
            contradiction_fields: dict[str, float] = {}
            for field_name in field_names:
                raw = registry.compute(field_name, attrs)
                normalized = registry.normalize(field_name, raw)
                # EC-007: Clamp to [field_min, field_max]
                clamped = max(field_min, min(field_max, normalized))
                if normalized != clamped:
                    logger.warning(
                        "Field %s at node %s clamped: %.4f -> %.4f",
                        field_name,
                        node_id,
                        normalized,
                        clamped,
                    )
                contradiction_fields[field_name] = clamped

            # Write to graph
            graph.update_node(node_id, contradiction_fields=contradiction_fields)

            # Update history (rolling window)
            node_history = history.setdefault(node_id, {})
            for field_name in field_names:
                field_history = node_history.setdefault(field_name, [])
                field_history.append(contradiction_fields[field_name])
                # Trim to max window size
                while len(field_history) > _MAX_HISTORY_WINDOW:
                    field_history.pop(0)

            # Store current values for next tick's derivative computation
            previous_wealth[node_id] = float(attrs.get("wealth", 0.0))
            previous_population[node_id] = float(attrs.get("population", 1))


def _get_persistent_data(context: ContextType) -> dict[str, Any]:
    """Extract persistent_data from context (TickContext or dict).

    Args:
        context: TickContext or dict with persistent_data key.

    Returns:
        Mutable persistent_data dict.
    """
    if hasattr(context, "persistent_data"):
        result: dict[str, Any] = context.persistent_data
        return result
    if isinstance(context, dict):
        data: dict[str, Any] = context.setdefault("persistent_data", {})
        return data
    return {}
