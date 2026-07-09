"""ContradictionFieldSystem — System #19 in materialist causality order.

Dialectical Field Topology (Feature 002): Computes named contradiction
fields at every social-class node per tick. When a ``field_registry`` is
wired (tests), fields come from its registered calculators; in production —
where no registry is wired (the §5.3 dormant plumbing) — the fields are
sourced from the Lawverian opposition layer instead (E0 repoint): the
``"exploitation"`` field is the mean fresh edge ``tension`` written by
ContradictionSystem @18, and ``"atomization"`` is the global atomization
opposition gap.

Reference: FR-001 (extensible field computation)
Reference: FR-002 (tick-keyed history persistence)
Reference: FR-011 (reads from economic outputs, no duplication)
Reference: R-003 (storage architecture)
Reference: R-006 (system ordering — position 19)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.base import SystemBase
from babylon.engine.systems.protocol import ContextType
from babylon.models.enums import EdgeType

logger = logging.getLogger(__name__)

# Maximum history window size (per spec FR-006)
_MAX_HISTORY_WINDOW = 3

#: Edge types whose fresh ``tension`` feeds the local ``exploitation`` field
#: when no ``field_registry`` is wired (E0 opposition-source path).
_FIELD_EDGE_TYPES: tuple[EdgeType, ...] = (
    EdgeType.EXPLOITATION,
    EdgeType.WAGES,
    EdgeType.TENANCY,
)

#: Field names populated by the opposition-source path, in deterministic order.
_OPPOSITION_FIELD_NAMES: tuple[str, ...] = ("exploitation", "atomization")


class ContradictionFieldSystem(SystemBase):
    """Compute contradiction fields for all social-class nodes.

    Execution Order: 19 (after the material-base and action systems)

    For each social-class node, computes normalized contradiction field values
    — from the ``field_registry`` calculators when one is wired, else from the
    opposition layer (E0). Stores field values on nodes and maintains a rolling
    history window in persistent_data for temporal derivative computation by
    System #20.
    """

    name = "contradiction_field"

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Compute contradiction fields for all social-class nodes.

        Args:
            graph: Mutable graph (NetworkX or GraphProtocol).
            services: ServiceContainer with field_registry.
            context: TickContext or dict with tick and persistent_data.
        """

        # No field registry in production: source fields from the opposition
        # layer instead of early-returning (E0 — the §5.3 dormant-stack repoint).
        registry = services.field_registry
        if registry is None:
            self._step_from_oppositions(graph, services, context)
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

    def _step_from_oppositions(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Source contradiction_fields from the opposition layer (E0 repoint).

        Production wires no ``field_registry``, so the Feature-002 field stack
        was dormant. The Lawverian rewire makes the opposition layer its source:
        for each social_class node the ``"exploitation"`` field is the mean fresh
        ``tension`` over its incident EXPLOITATION/WAGES/TENANCY edges (the
        per-edge gaps ContradictionSystem @18 wrote this tick), and the
        ``"atomization"`` field is the global atomization opposition gap (uniform
        per node this phase). The 3-tick rolling history machinery is identical
        to the registry path so System #20 reads the same shape.

        Args:
            graph: Mutable GraphProtocol.
            services: ServiceContainer (for field bounds).
            context: TickContext or dict with persistent_data.
        """
        persistent_data = _get_persistent_data(context)
        history: dict[str, dict[str, list[float]]] = persistent_data.setdefault(
            "contradiction_history", {}
        )
        field_min = services.defines.contradiction_field.field_min
        field_max = services.defines.contradiction_field.field_max
        atomization = self._atomization_gap(graph)
        tension_index = self._build_tension_index(graph)

        for node in graph.query_nodes(node_type="social_class"):
            node_id = node.id
            tensions = tension_index.get(node_id)
            exploitation = sum(tensions) / len(tensions) if tensions else 0.0
            raw = {
                "exploitation": exploitation,
                "atomization": atomization,
            }
            contradiction_fields = {
                name: max(field_min, min(field_max, value)) for name, value in raw.items()
            }
            graph.update_node(node_id, contradiction_fields=contradiction_fields)

            node_history = history.setdefault(node_id, {})
            for field_name in _OPPOSITION_FIELD_NAMES:
                field_history = node_history.setdefault(field_name, [])
                field_history.append(contradiction_fields[field_name])
                while len(field_history) > _MAX_HISTORY_WINDOW:
                    field_history.pop(0)

    @staticmethod
    def _build_tension_index(graph: GraphProtocol) -> dict[str, list[float]]:
        """Build ``{node_id: [tension, ...]}`` in a single pass over field edges.

        Replaces the O(N x M) per-node scan (``_incident_tension_mean`` called
        once per social_class node, each call rescanning all M field edges of
        3 types) with an O(N + M) single pass: iterate each field edge type
        ONCE, appending each edge's fresh ``tension`` to both endpoints' lists.
        Per-node lookup is then O(1).

        Order preservation (R-PROOF / ADR033 determinism): tensions land in
        each node's list in the SAME order as ``_incident_tension_mean`` would
        have produced — outer loop over ``_FIELD_EDGE_TYPES`` (fixed tuple
        order), inner loop over ``query_edges`` (insertion order) — so
        ``sum(tensions) / len(tensions)`` is bit-identical to the per-node
        scan and the tick determinism hash is unchanged. A self-loop
        (``source_id == target_id``) is counted once, matching the original
        ``node_id in (source_id, target_id)`` membership semantics.

        Args:
            graph: Mutable GraphProtocol carrying @18's fresh edge tensions.

        Returns:
            Dict mapping each incident node id to its ordered tension list.
            Nodes with no incident field edges are absent; callers treat
            missing keys as 0.0.
        """
        index: dict[str, list[float]] = {}
        for edge_type in _FIELD_EDGE_TYPES:
            for edge in graph.query_edges(edge_type=edge_type):
                raw = edge.attributes.get("tension")
                if not isinstance(raw, (int, float)):
                    continue
                tension = float(raw)
                source_id = edge.source_id
                target_id = edge.target_id
                index.setdefault(source_id, []).append(tension)
                if target_id != source_id:
                    index.setdefault(target_id, []).append(tension)
        return index

    @staticmethod
    def _atomization_gap(graph: GraphProtocol) -> float:
        """Global atomization opposition gap from the @18 snapshot (0.0 if absent).

        Args:
            graph: Mutable GraphProtocol carrying the ``opposition_states`` attr.

        Returns:
            The atomization opposition's ``gap`` this tick, or 0.0 when the
            snapshot or key is absent.
        """
        states = graph.get_graph_attr("opposition_states", {}) or {}
        atomization = states.get("atomization", {})
        raw = atomization.get("gap", 0.0)
        return float(raw) if isinstance(raw, (int, float)) else 0.0


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
