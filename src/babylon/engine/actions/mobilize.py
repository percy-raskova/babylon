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

**Mobilize(Canvass) sub-verb (P25 U11, ADR137):** ``params["sub_mode"] =
"canvass"`` routes the same turnout into a weighted org -> class MEMBERSHIP edge
instead of heat, gated on an acquired stance whose
:class:`~babylon.models.entities.doctrine.DoctrineCapability` authorises minting
``membership`` edges. It is the engine's only MEMBERSHIP producer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.engine.actions._capability import grants_edge_type
from babylon.models.enums import EdgeType, EventType, NodeType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.config.defines.politics import PoliticsDefines
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph

#: Mobilize sub-mode: electoral fieldwork that mints membership, not heat.
_SUB_MODE_CANVASS = "canvass"

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
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player MOBILIZE action: turnout, heat, and backfire.

    Args:
        action: The MOBILIZE action (``action_type == ActionType.PROTEST``).
            A ``sub_mode`` param of ``canvass`` selects the Mobilize(Canvass)
            sub-verb (P25 U11, ADR137).
        org_attrs: Acting organization's node attributes (read for the
            doctrine-capability gate on the canvass sub-verb).
        graph: World graph (mutated on the target node).
        services: ServicesProtocol (read for the politics defines on the
            canvass sub-verb; no MobilizeDefines exist for the base path).

    Returns:
        :class:`~babylon.ooda.types.ActionResult`; ``success=False`` when the
        target node is absent or the org has not acquired the sub-mode.
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

    sub_mode = str(action.params.get("sub_mode", "")).strip()
    if sub_mode:
        if sub_mode != _SUB_MODE_CANVASS:
            return ActionResult(
                action=action,
                success=False,
                failure_reason=f"MOBILIZE: unknown sub_mode {sub_mode!r}",
            )
        if not grants_edge_type(org_attrs, EdgeType.MEMBERSHIP.value):
            return ActionResult(
                action=action,
                success=False,
                failure_reason=(
                    "MOBILIZE(canvass): no acquired doctrine stance authorises "
                    f"minting {EdgeType.MEMBERSHIP.value!r} edges"
                ),
            )
        return _resolve_canvass(action, graph, target_node, turnout, services.defines.politics)

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


def _resolve_canvass(
    action: Action,
    graph: BabylonGraph,
    target_node: dict[str, Any],
    turnout: float,
    politics: PoliticsDefines,
) -> ActionResult:
    """Mobilize(Canvass): the surge is real, the power is not.

    Electoral fieldwork converts the same turnout into an org -> class
    MEMBERSHIP edge rather than heat and agitation. The edge is deliberately
    weighted by ``politics.entryism_membership_weight`` (< 1): Organization —
    the P(S|R) numerator — is weighted edge density, not headcount, so a
    canvass-built paper membership reads as far less power than its raw numbers
    suggest. This is the only MEMBERSHIP producer in the engine.
    """
    if target_node.get("_node_type") != NodeType.SOCIAL_CLASS.value:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="MOBILIZE(canvass): membership is only minted on a social_class",
        )

    weight = float(politics.entryism_membership_weight)
    minted = turnout * weight
    org_id = action.org_id
    target_id = action.target_id

    existing = graph.get_edge(org_id, target_id, EdgeType.MEMBERSHIP.value)
    if existing is not None:
        current = float(existing.attributes.get("membership_weight", 0.0))
        graph.update_edge(
            org_id,
            target_id,
            EdgeType.MEMBERSHIP.value,
            membership_weight=current + minted,
        )
        created = False
    elif not graph.has_edge(org_id, target_id):
        graph.add_edge(
            org_id,
            target_id,
            edge_type=EdgeType.MEMBERSHIP.value,
            membership_weight=minted,
        )
        created = True
    else:
        # The pair already holds a DIFFERENT edge type; skipping is the honest
        # failure mode (the house idiom -- see _mass_work.apply_mass_work_solidarity).
        return ActionResult(
            action=action,
            success=False,
            direct_effects={"turnout": turnout, "sub_mode": _SUB_MODE_CANVASS},
            failure_reason=(
                "MOBILIZE(canvass): the org->target pair already carries a "
                "different edge type; refusing to clobber it"
            ),
        )

    return ActionResult(
        action=action,
        success=True,
        direct_effects={
            "sub_mode": _SUB_MODE_CANVASS,
            "turnout": turnout,
            "membership_minted": minted,
            "membership_weight": weight,
            "edge_created": created,
        },
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_mobilize"]
