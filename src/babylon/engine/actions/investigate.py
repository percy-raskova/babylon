"""INVESTIGATE verb resolver (verb-dispatch engine).

Intelligence gathering (``ActionType.MAP_NETWORK``). Investigate is the one
canonical verb that mutates NO material graph state — it resolves against the
information/fog-of-war layer. It returns a ``direct_effects`` payload naming
which attributes of the target were revealed; the bridge/UI consumes it from
the persisted result. No graph writes (the consciousness simplex is untouched).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph

#: Attribute names revealed per target node type (the "fog of war" lift).
_REVEAL_BY_NODE_TYPE: dict[str, list[str]] = {
    "territory": ["heat", "rent_level", "population", "under_eviction"],
    "social_class": ["wealth", "organization", "repression_faced"],
    "organization": ["cohesion", "cadre_level", "heat", "budget"],
}
_REVEAL_DEFAULT: list[str] = ["heat"]


def resolve_investigate(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — no acting-org state consumed
    graph: BabylonGraph,
    services: ServicesProtocol,  # noqa: ARG001 — no InvestigateDefines yet
) -> ActionResult:
    """Resolve a player INVESTIGATE action (information-layer only).

    Args:
        action: The INVESTIGATE action (``action_type == ActionType.MAP_NETWORK``).
        org_attrs: Acting organization's node attributes (unused).
        graph: World graph (read-only — no mutation).
        services: ServicesProtocol (unused; no InvestigateDefines exist yet).

    Returns:
        :class:`~babylon.ooda.types.ActionResult` with ``direct_effects``
        naming revealed attributes; ``success=False`` if the target is absent.
    """
    target_node = graph.nodes.get(action.target_id)
    if target_node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="INVESTIGATE target not found in graph",
        )

    node_type = str(target_node.get("_node_type", ""))
    revealed = _REVEAL_BY_NODE_TYPE.get(node_type, _REVEAL_DEFAULT)
    scan_type = str(action.params.get("scan_type", "territory_scan"))

    return ActionResult(
        action=action,
        success=True,
        direct_effects={
            "scan_type": scan_type,
            "revealed": {action.target_id: revealed},
        },
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_investigate"]
