"""ATTACK verb resolver (verb-dispatch engine).

Attack infrastructure (``ActionType.ATTACK_INFRASTRUCTURE``). The infrastructure
decrement on the *target* is applied by the already-wired layer-3 consequence
pass (``ooda.layer3._propagate_infrastructure``), which fires because this
resolver returns an ``ActionResult`` carrying an ATTACK_INFRASTRUCTURE action.
The resolver's own material effect is to raise the *acting* org's ``heat``
(state attention — a round-trip Organization field) and record the collateral
backfire in ``direct_effects``.

.. note::

    Layer 3 writes ``infrastructure`` onto the target node. That attr is not a
    Territory model field; the verb-dispatch engine marks it transient in
    ``TERRITORY_EXCLUDED_FIELDS`` so the from_graph round-trip survives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.services import ServiceContainer
    from babylon.ooda.types import Action

#: State attention the acting org draws for a sabotage action.
_ATTACK_SELF_HEAT_GAIN = 0.1


def resolve_attack(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — heat read live from the graph
    graph: BabylonGraph,
    services: ServiceContainer,  # noqa: ARG001 — layer3 owns the infra delta
) -> ActionResult:
    """Resolve a player ATTACK action: acting-org heat + layer-3 infra decay.

    Args:
        action: The ATTACK action (``action_type == ActionType.ATTACK_INFRASTRUCTURE``).
        org_attrs: Acting organization's node attributes (unused; heat is read
            live from the graph so concurrent same-tick writes are respected).
        graph: World graph (mutated in place on the acting org node).
        services: ServiceContainer (unused; layer 3 sources the infra delta).

    Returns:
        :class:`~babylon.ooda.types.ActionResult` carrying the ATTACK action so
        layer 3 applies the infrastructure decrement to the target.
    """
    org_node = graph.nodes.get(action.org_id)
    heat_self_delta = 0.0
    if org_node is not None and org_node.get("_node_type") == "organization":
        heat = float(org_node.get("heat", 0.0))
        new_heat = min(1.0, heat + _ATTACK_SELF_HEAT_GAIN)
        graph.update_node(action.org_id, heat=new_heat)
        heat_self_delta = new_heat - heat

    effects: dict[str, Any] = {
        "heat_self_delta": heat_self_delta,
        "target_id": action.target_id,
    }

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_attack"]
