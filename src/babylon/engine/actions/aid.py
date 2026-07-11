"""AID verb resolver (verb-dispatch engine).

Direct community service provision (``ActionType.PROVIDE_SERVICE``). Combines
two effects:

1. A five-factor consciousness delta via the Feature-032 machinery
   (tendency-split base — revolutionary orgs raise CI, liberal orgs less so).
2. An optional material transfer: ``params["transfer_amount"]`` moves from the
   acting org's ``budget`` to the target's ``wealth`` (both round-trip model
   fields). Insufficient budget fails loud (``success=False``).

See Also:
    :func:`babylon.ooda.action_effects.compute_consciousness_delta`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import ActionType, EventType
from babylon.ooda.action_effects import compute_consciousness_delta
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph

#: Fraction of a transferred amount that reaches the target (rest is overhead).
_AID_EFFICIENCY = 1.0


def resolve_aid(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player AID action: consciousness effect + material transfer.

    Args:
        action: The AID action (``action_type == ActionType.PROVIDE_SERVICE``).
        org_attrs: Acting organization's node attributes.
        graph: World graph (mutated when a transfer occurs).
        services: ServicesProtocol providing defines.

    Returns:
        :class:`~babylon.ooda.types.ActionResult` with the consciousness delta
        and, when a transfer occurs, ``direct_effects`` recording the amounts.
    """
    ci = compute_consciousness_delta(
        org_attrs,
        action.target_id,
        ActionType.PROVIDE_SERVICE,
        graph,
        services.defines.ooda,
        services.defines.organization,
    )

    transfer = float(action.params.get("transfer_amount", 0.0))
    if transfer <= 0.0:
        return ActionResult(
            action=action,
            success=True,
            consciousness_delta=ci,
            events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
        )

    org_node = graph.nodes.get(action.org_id)
    target_node = graph.nodes.get(action.target_id)
    if org_node is None or target_node is None:
        return ActionResult(
            action=action,
            success=False,
            consciousness_delta=ci,
            failure_reason="AID org or target node not found in graph",
        )

    budget = float(org_node.get("budget", 0.0))
    if budget < transfer:
        return ActionResult(
            action=action,
            success=False,
            consciousness_delta=ci,
            direct_effects={"requested_transfer": transfer, "available_budget": budget},
            failure_reason="insufficient budget for AID transfer",
        )

    received = transfer * _AID_EFFICIENCY
    graph.update_node(action.org_id, budget=budget - transfer)
    current_wealth = float(target_node.get("wealth", 0.0))
    graph.update_node(action.target_id, wealth=current_wealth + received)

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=ci,
        direct_effects={
            "amount_transferred": transfer,
            "amount_received": received,
            "efficiency": _AID_EFFICIENCY,
        },
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_aid"]
