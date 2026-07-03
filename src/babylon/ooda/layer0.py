"""Layer 0: Automatic metabolism recording (Feature 032).

Business organizations auto-record economic activity as ActionResults
before the initiative-ordered action phase begins. This captures the
continuous economic metabolism that happens regardless of deliberate
organizational action.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import ActionType, EventType, OrgType
from babylon.ooda.types import Action, ActionResult

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.services import ServiceContainer


def process_layer0(
    graph: BabylonGraph,
    services: ServiceContainer,  # noqa: ARG001 — reserved for future event_bus usage
) -> list[ActionResult]:
    """Record automatic metabolism for Business organizations.

    Business orgs auto-generate EMPLOY ActionResults representing their
    ongoing economic activity. This runs before initiative ordering.

    Args:
        graph: World graph containing organization nodes.
        services: ServiceContainer (for event_bus).

    Returns:
        List of ActionResult from auto-metabolism.
    """
    results: list[ActionResult] = []
    max_orgs = 1000  # Upper bound for loop safety

    org_nodes: list[tuple[str, dict[str, Any]]] = []
    for node_id, data in graph.nodes(data=True):
        if (
            data.get("_node_type") == "organization"
            and data.get("org_type") == OrgType.BUSINESS.value
        ):
            org_nodes.append((node_id, data))
        if len(org_nodes) >= max_orgs:
            break

    for org_id, org_data in org_nodes:
        # Find primary territory for target
        territory_ids: list[str] = org_data.get("territory_ids", [])
        target_id = territory_ids[0] if territory_ids else org_id

        action = Action(
            org_id=org_id,
            action_type=ActionType.EMPLOY,
            target_id=target_id,
        )

        result = ActionResult(
            action=action,
            success=True,
            direct_effects={"auto_metabolism": True},
            events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
        )
        results.append(result)

    return results


__all__ = ["process_layer0"]
