"""FieldDerivativeSystem — System #20 in materialist causality order.

Dialectical Field Topology (Feature 002): Computes spatial derivatives
(gradient on edges, Laplacian on nodes), temporal derivatives (df/dt,
d2f/dt2), principal-field identification, and continuity residuals.

Its ``principal_field`` graph attr is the field-stack's fastest-developing
contradiction FIELD — deliberately distinct from ContradictionSystem @18's
Maoist principal OPPOSITION, so the two never fight (E0 rename).

Reference: FR-003 (gradient), FR-004 (Laplacian)
Reference: FR-006 (temporal derivatives)
Reference: FR-008 (principal contradiction)
Reference: FR-009 (continuity residuals)
Reference: R-006 (system ordering — position 20)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.enums import EventType

logger = logging.getLogger(__name__)


class FieldDerivativeSystem(SystemBase):
    """Compute spatial and temporal derivatives for contradiction fields.

    Execution Order: 20 (after ContradictionFieldSystem)

    Reads contradiction_fields from nodes (written by System #19),
    computes gradients on edges, Laplacian at nodes, and temporal
    derivatives from the rolling history in persistent_data.
    """

    name: ClassVar[str] = "field_derivative"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Compute all spatial and temporal derivatives.

        Args:
            graph: Mutable graph (NetworkX or GraphProtocol).
            services: ServicesProtocol with field_registry.
            context: TickContext or dict with tick and persistent_data.
        """

        # E0: no field_registry in production. The field stack is sourced from
        # the opposition layer (System #19), so derive the field names from the
        # node attrs it wrote this tick rather than early-returning.
        registry = services.field_registry
        if registry is not None:
            field_names = registry.get_field_names()
        else:
            field_names = _discover_field_names(graph)
        if not field_names:
            return

        persistent_data = self._get_persistent_data(context)
        history: dict[str, dict[str, list[float]]] = persistent_data.get(
            "contradiction_history", {}
        )

        # Extract tick for event emission
        tick: int = 0
        if hasattr(context, "tick"):
            tick = context.tick
        elif isinstance(context, dict):
            tick_val = context.get("tick", 0)
            tick = int(tick_val) if tick_val is not None else 0

        # ─── Phase 1: Spatial gradients on edges ────────────────────
        _compute_edge_gradients(graph, field_names)

        # ─── Phase 2: Laplacian + temporal derivatives on nodes ─────
        _compute_node_derivatives(graph, field_names, history)

        # ─── Phase 3: Principal contradiction identification ────────
        _identify_principal_contradiction(graph, field_names, persistent_data, services, tick)

        # ─── Phase 4: Field-stack snapshot (facade round-trip carry) ─
        # WorldState.to_graph()/from_graph() otherwise loses the per-node
        # (contradiction_fields/field_derivatives) and per-edge
        # (field_gradients) attrs this step just wrote, plus the
        # graph-level principal_field/dialectical_regime attrs — the
        # "altitude gap" get_field_state's docstring documents
        # (web/game/engine_bridge.py). This ONE graph attr is the carrier
        # WorldState round-trips and re-stamps from (Wave 3 Round 1).
        graph.set_graph_attr("field_stack", _build_field_stack(graph))


def _discover_field_names(graph: GraphProtocol) -> list[str]:
    """Union of contradiction-field names present on social_class nodes, sorted.

    Used when no ``field_registry`` is wired (production): the field stack is
    sourced from the opposition layer (E0), so the field names are whatever
    ContradictionFieldSystem @19 wrote onto the nodes this tick.

    Args:
        graph: Graph whose social_class nodes may carry ``contradiction_fields``.

    Returns:
        Sorted list of distinct field names (empty when no node carries fields).
    """
    names: set[str] = set()
    for node in graph.query_nodes(node_type="social_class"):
        fields = node.attributes.get("contradiction_fields", {})
        if isinstance(fields, dict):
            names.update(fields.keys())
    return sorted(names)


def _compute_edge_gradients(
    graph: GraphProtocol,
    field_names: list[str],
) -> None:
    """Compute gradient = f(target) - f(source) on every edge.

    Args:
        graph: Graph with contradiction_fields on nodes.
        field_names: List of field names to compute gradients for.
    """
    for edge in graph.query_edges():
        src_node = graph.get_node(edge.source_id)
        tgt_node = graph.get_node(edge.target_id)

        if src_node is None or tgt_node is None:
            continue

        src_fields: dict[str, float] = src_node.attributes.get("contradiction_fields", {})
        tgt_fields: dict[str, float] = tgt_node.attributes.get("contradiction_fields", {})

        # Skip edges where nodes don't have field data
        if not src_fields or not tgt_fields:
            continue

        gradients: dict[str, float] = {}
        for field_name in field_names:
            src_val = src_fields.get(field_name, 0.0)
            tgt_val = tgt_fields.get(field_name, 0.0)
            gradients[field_name] = tgt_val - src_val

        graph.update_edge(
            edge.source_id,
            edge.target_id,
            edge.edge_type,
            field_gradients=gradients,
        )


def _compute_node_derivatives(
    graph: GraphProtocol,
    field_names: list[str],
    history: dict[str, dict[str, list[float]]],
    edge_weight_attr: str | None = None,
) -> None:
    """Compute Laplacian and temporal derivatives at each node.

    When ``edge_weight_attr`` is provided, computes a weighted Laplacian:
    ``sum(w_j * (f(j) - f(i)))`` instead of ``sum(f(j) - f(i))``.

    Args:
        graph: Graph with contradiction_fields on nodes.
        field_names: List of field names.
        history: contradiction_history from persistent_data.
        edge_weight_attr: Optional edge attribute name for weights.
            None = unweighted (all weights 1.0), preserving backward compat.
    """
    for node in graph.query_nodes(node_type="social_class"):
        node_id = node.id
        node_fields: dict[str, float] = node.attributes.get("contradiction_fields", {})
        if not node_fields:
            continue

        node_history = history.get(node_id, {})

        # Collect neighbor field values and edge weights
        neighbor_fields, edge_weights = _collect_neighbor_fields(
            graph,
            node_id,
            field_names,
            edge_weight_attr=edge_weight_attr,
        )

        field_derivatives: dict[str, dict[str, float | None]] = {}
        for field_name in field_names:
            my_val = node_fields.get(field_name, 0.0)

            # Laplacian: sum_j(w_j * (f(j) - f(i)))
            neighbor_vals = neighbor_fields.get(field_name, [])
            if neighbor_vals:
                laplacian = sum(
                    w * (nv - my_val) for w, nv in zip(edge_weights, neighbor_vals, strict=True)
                )
            else:
                laplacian = 0.0
                if not neighbor_vals:
                    logger.debug(
                        "EC-002: Isolated node %s, Laplacian=0.0 for %s",
                        node_id,
                        field_name,
                    )

            # Temporal derivatives from history
            field_hist = node_history.get(field_name, [])
            df_dt: float | None = None
            d2f_dt2: float | None = None

            if len(field_hist) >= 2:
                # df/dt = f(t) - f(t-1)
                df_dt = field_hist[-1] - field_hist[-2]

            if len(field_hist) >= 3:
                # d2f/dt2 = f(t) - 2*f(t-1) + f(t-2)
                d2f_dt2 = field_hist[-1] - 2.0 * field_hist[-2] + field_hist[-3]

            field_derivatives[field_name] = {
                "laplacian": laplacian,
                "df_dt": df_dt,
                "d2f_dt2": d2f_dt2,
            }

        graph.update_node(node_id, field_derivatives=field_derivatives)


def _collect_neighbor_fields(
    graph: GraphProtocol,
    node_id: str,
    field_names: list[str],
    edge_weight_attr: str | None = None,
) -> tuple[dict[str, list[float]], list[float]]:
    """Collect field values and edge weights from all neighbors of a node.

    Considers both incoming and outgoing edges to ensure full
    Laplacian computation on the undirected graph structure.

    Args:
        graph: Graph protocol instance.
        node_id: Node to collect neighbors for.
        field_names: Field names to collect.
        edge_weight_attr: Optional edge attribute name for weights.
            None = all weights 1.0 (backward compatible).

    Returns:
        Tuple of (field_name -> neighbor values list, edge weights list).
        Edge weights list is parallel to each field's neighbor values list
        (one weight per neighbor, same order).
    """
    result: dict[str, list[float]] = {name: [] for name in field_names}
    weights: list[float] = []

    # Collect unique neighbor IDs and their edge weights from both directions
    neighbor_weights: dict[str, float] = {}

    for edge in graph.query_edges():
        nid: str | None = None
        if edge.source_id == node_id:
            nid = edge.target_id
        elif edge.target_id == node_id:
            nid = edge.source_id

        if nid is not None and nid not in neighbor_weights:
            if edge_weight_attr is not None:
                w = float(edge.attributes.get(edge_weight_attr, 1.0))
            else:
                w = 1.0
            neighbor_weights[nid] = w

    for nid, w in neighbor_weights.items():
        neighbor_node = graph.get_node(nid)
        if neighbor_node is None:
            continue
        n_fields: dict[str, float] = neighbor_node.attributes.get("contradiction_fields", {})
        has_fields = False
        for field_name in field_names:
            if field_name in n_fields:
                result[field_name].append(n_fields[field_name])
                has_fields = True
        if has_fields:
            weights.append(w)

    return result, weights


def _build_field_stack(graph: GraphProtocol) -> dict[str, Any]:
    """Compose this tick's field-stack snapshot for the graph-attr carry.

    Reads back exactly what :func:`_compute_edge_gradients` and
    :func:`_compute_node_derivatives` wrote onto the graph earlier this
    same ``step()`` call (``contradiction_fields``/``field_derivatives`` on
    social_class nodes, ``field_gradients`` on edges) and assembles ONE
    deterministic graph-level snapshot. :meth:`WorldState.to_graph`/
    ``from_graph`` (``babylon.models.world_state``) carry this attr across
    the round trip the facade (``simulation_engine.step``) otherwise loses,
    and re-stamp the node/edge attrs from it — closing the altitude gap
    documented on ``EngineBridge.get_field_state``.

    Honest omission (Constitution III.11): a node the engine did not
    compute any field for this tick is OMITTED from ``nodes`` entirely
    (never a fabricated empty entry); an edge with no gradients is
    likewise omitted from ``edges``. All dict/list ordering is rebuilt
    from ``sorted()`` iteration (Constitution III.7 determinism) regardless
    of the upstream write order — e.g. the opposition-source path
    (:meth:`ContradictionFieldSystem._step_from_oppositions`) inserts
    ``contradiction_fields`` as ``{"exploitation": ..., "atomization": ...}``,
    not alphabetically.

    The per-node ``"fields"``/``"field_derivatives"`` sub-dicts are
    verbatim copies (re-sorted, not reshaped) of the node's
    ``contradiction_fields``/``field_derivatives`` attrs specifically so
    :meth:`WorldState._restamp_field_stack` can re-stamp them onto a
    reloaded graph with a plain merge — no reassembly.

    Args:
        graph: Graph with this tick's ``contradiction_fields``/
            ``field_derivatives``/``field_gradients`` already written.

    Returns:
        ``{"nodes": {node_id: {"fields": {...}, "field_derivatives": {...}}},
        "edges": [{"source", "target", "field", "gradient"}, ...]}``, both
        collections present (possibly empty) whenever this system runs with
        at least one registered field name.
    """
    raw_nodes: dict[str, dict[str, Any]] = {}
    for node in graph.query_nodes(node_type="social_class"):
        fields: dict[str, float] = node.attributes.get("contradiction_fields", {})
        derivs: dict[str, dict[str, float | None]] = node.attributes.get("field_derivatives", {})
        if not fields and not derivs:
            continue
        entry: dict[str, Any] = {}
        if fields:
            entry["fields"] = {name: fields[name] for name in sorted(fields)}
        if derivs:
            entry["field_derivatives"] = {name: derivs[name] for name in sorted(derivs)}
        raw_nodes[node.id] = entry
    nodes = {node_id: raw_nodes[node_id] for node_id in sorted(raw_nodes)}

    edges: list[dict[str, Any]] = []
    for edge in graph.query_edges():
        gradients: dict[str, float] = edge.attributes.get("field_gradients", {})
        if not gradients:
            continue
        for field_name in sorted(gradients):
            edges.append(
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "field": field_name,
                    "gradient": gradients[field_name],
                }
            )
    edges.sort(key=lambda entry: (entry["source"], entry["target"], entry["field"]))

    return {"nodes": nodes, "edges": edges}


def _identify_principal_contradiction(
    graph: GraphProtocol,
    field_names: list[str],
    persistent_data: dict[str, Any],
    services: ServicesProtocol,
    tick: int,
) -> None:
    """Identify the principal contradiction from temporal derivatives.

    The principal contradiction is the field with the maximum |df/dt|
    across all nodes. Tie-breaking: total magnitude, then exploitation
    preferred (EC-004).

    Args:
        graph: Graph with field_derivatives on nodes.
        field_names: Registered field names.
        persistent_data: For tracking previous principal.
        services: ServicesProtocol for event_bus access.
        tick: Current tick number.
    """
    # Collect max |df/dt| per field across all nodes
    field_max_abs_df_dt: dict[str, float] = dict.fromkeys(field_names, 0.0)
    field_total_magnitude: dict[str, float] = dict.fromkeys(field_names, 0.0)

    for node in graph.query_nodes(node_type="social_class"):
        derivs: dict[str, dict[str, float | None]] = node.attributes.get("field_derivatives", {})
        for field_name in field_names:
            field_deriv = derivs.get(field_name, {})
            df_dt = field_deriv.get("df_dt")
            if df_dt is not None:
                abs_val = abs(df_dt)
                if abs_val > field_max_abs_df_dt[field_name]:
                    field_max_abs_df_dt[field_name] = abs_val
                field_total_magnitude[field_name] += abs_val

    # Find the field with maximum |df/dt|
    principal_field: str | None = None
    max_df_dt = 0.0

    # Sort by: max |df/dt| desc, total magnitude desc, exploitation preferred
    candidates = sorted(
        field_names,
        key=lambda f: (
            field_max_abs_df_dt[f],
            field_total_magnitude[f],
            1.0 if f == "exploitation" else 0.0,
        ),
        reverse=True,
    )

    if candidates and field_max_abs_df_dt[candidates[0]] > 0.0:
        principal_field = candidates[0]
        max_df_dt = field_max_abs_df_dt[candidates[0]]

    # Check if principal changed from previous tick
    previous_principal: str | None = persistent_data.get("_previous_principal_field")
    changed = principal_field != previous_principal

    # Write to graph-level attribute. Named ``principal_field`` (not
    # ``principal_contradiction``) so it never collides with ContradictionSystem
    # @18's Maoist principal OPPOSITION — this is the field-stack's principal
    # FIELD (max |df/dt|), a distinct notion (E0 rename).
    graph.set_graph_attr(
        "principal_field",
        {
            "field_name": principal_field,
            "max_abs_df_dt": max_df_dt,
            "changed": changed,
        },
    )

    # Emit event if principal changed and we have a real principal
    if changed and principal_field is not None:
        services.event_bus.publish(
            Event(
                type=EventType.PRINCIPAL_CONTRADICTION_SHIFT,
                tick=tick,
                payload={
                    "previous_field": previous_principal,
                    "new_field": principal_field,
                    "max_abs_df_dt": max_df_dt,
                },
            )
        )

    # Store for next tick comparison
    persistent_data["_previous_principal_field"] = principal_field
