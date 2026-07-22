"""The field-state read-model — ``project_field_state``, the Weather Layer.

Port of ``web/game/engine_bridge.py::EngineBridge.get_field_state`` (and its
``_build_field_state_nodes``/``_build_field_state_edges`` helpers) into a
pure projection: same read logic — ContradictionFieldSystem @19's
``contradiction_fields``, FieldDerivativeSystem @20's ``field_derivatives``
(``laplacian``/``df_dt`` sub-keys only, ``d2f_dt2`` excluded, matching the
ported endpoint's own declared contract) and ``field_gradients``,
FascistFactionSystem's ``fascist_alignment``, plus the graph-level
``principal_field``/``dialectical_regime`` attrs — never a redesign.
Transport-neutral by construction — no Django, no engine imports, no
database connection; callers hand in the graph they already hold.

**Read the LIVE graph, never a round trip.** ``WorldState.from_graph()``
drops every ``tick_``/``flow_`` node attr via its wildcard filter and the
graph-level ``principal_field``/``dialectical_regime`` attrs outright
(``world_state.py``); the ``field_stack`` graph attr exists specifically to
survive THAT round trip (``FieldDerivativeSystem._build_field_stack`` +
``WorldState._restamp_field_stack``) for callers who only have a
reconstructed graph. This module never reads ``field_stack`` — the vault
tick-baker (``ArchiveTickBaker.on_tick_committed``) always hands this
projection the SAME live graph object the engine just ticked, exactly like
every other projection in this package, so the direct per-node/edge/graph
reads below are always the freshest available.

**One producer per field** (mirrors the WO-3 ruling
:mod:`babylon.projection.county` records):

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``nodes``
     - Every ``social_class`` node carrying ``contradiction_fields``
       (ContradictionFieldSystem @19), ``field_derivatives``
       (FieldDerivativeSystem @20), or ``fascist_alignment``
       (FascistFactionSystem), sorted by node id. A node carrying none of
       the three is omitted entirely (never a fabricated empty entry).
   * - ``edges``
     - Every ``(edge, field)`` pair with a ``field_gradients`` entry
       (FieldDerivativeSystem @20's ``_compute_edge_gradients``),
       territory-anchored via the live TENANCY edges (the same Occupant ->
       Territory link ``ProductionSystem._find_tenancy_target`` reads),
       sorted by ``(source, target, field)``.
   * - ``principal_field``
     - The ``principal_field`` graph attribute
       (``FieldDerivativeSystem._identify_principal_contradiction``),
       hydrated verbatim.
   * - ``dialectical_regime``
     - The ``dialectical_regime`` graph attribute
       (``ContradictionSystem._classify_regime`` @18), hydrated verbatim.

Absence discipline (Constitution III.11): every quantity above projects as
``None`` when its own graph input is absent this tick — never a defaulted
zero. A present-but-malformed source value fails loud through the relevant
Pydantic validation (:class:`~babylon.projection.view_models.
FieldStateNodeView`/:class:`~babylon.projection.view_models.
FieldStateEdgeView`/the constrained field types) — only a *missing* value is
absence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.view_models import (
    DialecticalRegimeView,
    FieldStateEdgeView,
    FieldStateNodeView,
    FieldStateView,
    PrincipalFieldView,
)

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol

__all__ = ["project_field_state"]


def _node_field_derivatives(
    raw: Mapping[str, object],
) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    """Split a node's ``field_derivatives`` dict into laplacian/df_dt sub-maps.

    ``d2f_dt2`` is deliberately never read — out of this dossier's declared
    contract, matching the ported ``_build_field_state_nodes`` endpoint.

    :param raw: One node's ``field_derivatives`` attribute
        (``{field_name: {"laplacian": ..., "df_dt": ..., "d2f_dt2": ...}}``).
    :returns: ``(laplacian, df_dt)``, each ``None`` when no field carries
        that sub-key (a ``None`` sub-value — under 2/3 ticks of history — is
        excluded from its map, not zero-filled).
    """
    laplacian: dict[str, float] = {}
    df_dt: dict[str, float] = {}
    for field_name, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("laplacian") is not None:
            laplacian[field_name] = float(entry["laplacian"])
        if entry.get("df_dt") is not None:
            df_dt[field_name] = float(entry["df_dt"])
    return (laplacian or None, df_dt or None)


def _field_state_nodes(graph: GraphProtocol) -> tuple[FieldStateNodeView, ...] | None:
    """Every social_class node's field-stack reading, sorted by id.

    :param graph: The post-tick graph.
    :returns: Sorted node readings, or ``None`` when no social_class node
        carries ``contradiction_fields``, ``field_derivatives``, or
        ``fascist_alignment`` this tick.
    """
    entries: list[FieldStateNodeView] = []
    for node in graph.query_nodes(node_type=NodeType.SOCIAL_CLASS):
        attrs = node.attributes

        fields_raw = attrs.get("contradiction_fields")
        fields = (
            {name: float(value) for name, value in fields_raw.items()}
            if isinstance(fields_raw, dict) and fields_raw
            else None
        )

        derivatives_raw = attrs.get("field_derivatives")
        laplacian, df_dt = (
            _node_field_derivatives(derivatives_raw)
            if isinstance(derivatives_raw, dict) and derivatives_raw
            else (None, None)
        )

        fascist_alignment = attrs.get("fascist_alignment")
        fascist_alignment_value = (
            float(fascist_alignment) if fascist_alignment is not None else None
        )

        if (
            fields is None
            and laplacian is None
            and df_dt is None
            and fascist_alignment_value is None
        ):
            continue

        entries.append(
            FieldStateNodeView(
                node_id=node.id,
                name=str(attrs.get("name", node.id)),
                fields=fields,
                laplacian=laplacian,
                df_dt=df_dt,
                fascist_alignment=fascist_alignment_value,
            )
        )

    entries.sort(key=lambda entry: entry.node_id)
    return tuple(entries) if entries else None


def _class_territory(graph: GraphProtocol) -> dict[str, str]:
    """social_class node id -> territory node id, via TENANCY edges.

    Deterministic tie-break: TENANCY edges are visited sorted by
    ``(territory, class)``, so the lexicographically smallest territory wins
    if a class somehow carries TENANCY edges into more than one territory.

    :param graph: The post-tick graph.
    :returns: Map of social_class node id to its resolved territory. A class
        with no live TENANCY edge is simply absent — callers must treat a
        missing entry as unresolved, never a fabricated territory.
    """
    edges = sorted(
        graph.query_edges(edge_type=EdgeType.TENANCY),
        key=lambda edge: (edge.target_id, edge.source_id),
    )
    mapping: dict[str, str] = {}
    for edge in edges:
        mapping.setdefault(edge.source_id, edge.target_id)
    return mapping


def _field_state_edges(
    graph: GraphProtocol, class_territory: Mapping[str, str]
) -> tuple[FieldStateEdgeView, ...] | None:
    """Every ``(edge, field)`` gradient entry, territory-anchored, sorted.

    :param graph: The post-tick graph.
    :param class_territory: :func:`_class_territory`'s result.
    :returns: Sorted gradient entries, or ``None`` when no edge carries a
        ``field_gradients`` entry this tick.
    """
    entries: list[FieldStateEdgeView] = []
    for edge in graph.query_edges():
        gradients = edge.attributes.get("field_gradients")
        if not isinstance(gradients, dict) or not gradients:
            continue
        source_territory = class_territory.get(edge.source_id)
        target_territory = class_territory.get(edge.target_id)
        for field_name in sorted(gradients):
            entries.append(
                FieldStateEdgeView(
                    source=edge.source_id,
                    target=edge.target_id,
                    source_territory=source_territory,
                    target_territory=target_territory,
                    field=field_name,
                    gradient=float(gradients[field_name]),
                )
            )
    entries.sort(key=lambda entry: (entry.source, entry.target, entry.field))
    return tuple(entries) if entries else None


def _principal_field(graph: GraphProtocol) -> PrincipalFieldView | None:
    """The ``principal_field`` graph attribute, hydrated verbatim.

    :param graph: The post-tick graph.
    :returns: The hydrated reading, or ``None`` when the attribute is absent
        (FieldDerivativeSystem never ran with a nonempty field registry).
    :raises pydantic.ValidationError: if a present attribute is malformed.
    """
    raw = graph.get_graph_attr("principal_field", None)
    if raw is None:
        return None
    return PrincipalFieldView(**raw)


def _dialectical_regime(graph: GraphProtocol) -> DialecticalRegimeView | None:
    """The ``dialectical_regime`` graph attribute, hydrated verbatim.

    :param graph: The post-tick graph.
    :returns: The hydrated reading, or ``None`` when the attribute is absent
        (no ``capital_labor``/principal opposition state existed yet).
    :raises pydantic.ValidationError: if a present attribute is malformed.
    """
    raw = graph.get_graph_attr("dialectical_regime", None)
    if raw is None:
        return None
    return DialecticalRegimeView(**raw)


def project_field_state(
    field_state_id: str,
    *,
    graph: GraphProtocol,
    tick: int,
) -> FieldStateView:
    """Project the post-tick field stack into a :class:`FieldStateView`.

    Read strictly *post-tick*, exactly like :func:`~babylon.projection.
    county.project_county`. Takes no ``world`` parameter — every field this
    dossier carries is read straight off the graph (matching the ported
    ``get_field_state``, which never consults a ``WorldState`` either).

    :param field_state_id: The dossier's identity (``"USA"`` today, the
        singleton the field stack is national-scale by construction).
    :param graph: The committed post-tick graph.
    :param tick: The committed tick this dossier is projected from.
    :returns: The frozen, validated field-state dossier.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    class_territory = _class_territory(graph)
    return FieldStateView(
        field_state_id=field_state_id,
        verified_tick=tick,
        nodes=_field_state_nodes(graph),
        edges=_field_state_edges(graph, class_territory),
        principal_field=_principal_field(graph),
        dialectical_regime=_dialectical_regime(graph),
    )
