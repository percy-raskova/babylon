"""MOBILIZE verb resolver (verb-dispatch engine).

Public demonstration / strike (``ActionType.PROTEST``). Ports the spec-047
mobilize dynamics (solidarity-amplified turnout, heat generation, George-Floyd
backfire) onto the uniform resolver signature, returning an
:class:`~babylon.ooda.types.ActionResult` and writing ONLY round-trip-safe
graph fields:

* ``heat`` on a Territory / Organization target (a model field of both);
* ``ideology.agitation`` on a SocialClass target via copy-modify-writeback of
  the nested ``ideology`` dict (top-level ``agitation`` does NOT round-trip).

Backfire emits :class:`~babylon.models.enums.EventType.EXCESSIVE_FORCE` (the
George-Floyd spark); the standard path emits ``ORGANIZATIONAL_ACTION``. There
is no ``MobilizeDefines``, so the coefficients are module constants.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action

#: Demonstrators mobilized per unit of committed sympathizer labor.
_TURNOUT_PER_SL = 10.0
#: Turnout multiplier bonus per incoming SOLIDARITY/SOLIDARISTIC edge.
_SOLIDARITY_AMP_PER_EDGE = 0.1
#: State attention generated per demonstrator.
_HEAT_PER_DEMONSTRATOR = 0.001
#: Turnout above which over-policing backfires (the George-Floyd dynamic).
_BACKFIRE_TURNOUT_THRESHOLD = 100.0
#: Heat multiplier applied when a demonstration backfires.
_BACKFIRE_HEAT_MULT = 2.0
#: Agitation routed into a SocialClass target on the standard path.
_BASE_AGITATION_GAIN = 0.1
#: Agitation routed into a SocialClass target when repression backfires.
_BACKFIRE_AGITATION_GAIN = 0.2
#: Edge-type values that count as solidarity ties amplifying turnout.
_SOLIDARITY_EDGE_TYPES: frozenset[str] = frozenset({"solidarity", "solidaristic"})


def _count_solidarity_edges(graph: BabylonGraph, org_id: str) -> int:
    """Count incoming SOLIDARITY/SOLIDARISTIC edges to the acting org."""
    if graph.nodes.get(org_id) is None:
        return 0
    count = 0
    for _source, _target, data in graph.in_edges(org_id, data=True):
        raw = data.get("edge_type", "")
        value = raw.value if hasattr(raw, "value") else str(raw)
        if value.lower() in _SOLIDARITY_EDGE_TYPES:
            count += 1
    return count


def _route_target_effect(
    graph: BabylonGraph,
    target_id: str,
    target_node: dict[str, Any],
    heat_generated: float,
    agitation_gain: float,
) -> dict[str, Any]:
    """Apply heat (Territory/Org) or agitation (SocialClass) to the target.

    Returns a dict describing what was applied (empty writes recorded, never
    a non-round-trip attribute).
    """
    node_type = str(target_node.get("_node_type", ""))
    applied: dict[str, Any] = {}

    if node_type in {"territory", "organization"}:
        heat = float(target_node.get("heat", 0.0))
        new_heat = min(1.0, heat + heat_generated)
        graph.update_node(target_id, heat=new_heat)
        applied["heat_delta"] = new_heat - heat
    elif node_type == "social_class":
        ideology = dict(target_node.get("ideology") or {})
        if ideology:
            ideology["agitation"] = float(ideology.get("agitation", 0.0)) + agitation_gain
            graph.update_node(target_id, ideology=ideology)
            applied["agitation_delta"] = agitation_gain

    return applied


def resolve_mobilize(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — turnout is driven by params/edges
    graph: BabylonGraph,
    services: ServicesProtocol,  # noqa: ARG001 — no MobilizeDefines yet
) -> ActionResult:
    """Resolve a player MOBILIZE action: turnout, heat, and backfire.

    Args:
        action: The MOBILIZE action (``action_type == ActionType.PROTEST``).
        org_attrs: Acting organization's node attributes (unused).
        graph: World graph (mutated on the target node).
        services: ServicesProtocol (unused; no MobilizeDefines exist yet).

    Returns:
        :class:`~babylon.ooda.types.ActionResult`; ``success=False`` when the
        target node is absent.
    """
    target_node = graph.nodes.get(action.target_id)
    if target_node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="MOBILIZE target not found in graph",
        )

    sl = float(action.params.get("sl_committed", 1.0))
    n_solidarity = _count_solidarity_edges(graph, action.org_id)
    multiplier = 1.0 + _SOLIDARITY_AMP_PER_EDGE * n_solidarity
    turnout = sl * _TURNOUT_PER_SL * multiplier

    heat_generated = turnout * _HEAT_PER_DEMONSTRATOR
    backfire = turnout > _BACKFIRE_TURNOUT_THRESHOLD
    if backfire:
        heat_generated *= _BACKFIRE_HEAT_MULT
        agitation_gain = _BACKFIRE_AGITATION_GAIN
        event = EventType.EXCESSIVE_FORCE.value
    else:
        agitation_gain = _BASE_AGITATION_GAIN
        event = EventType.ORGANIZATIONAL_ACTION.value

    applied = _route_target_effect(
        graph, action.target_id, target_node, heat_generated, agitation_gain
    )

    effects: dict[str, Any] = {
        "turnout": turnout,
        "heat_generated": heat_generated,
        "solidarity_edges": n_solidarity,
        "backfire": backfire,
        **applied,
    }

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[event],
    )


__all__ = ["resolve_mobilize"]
