"""MOVE verb resolver (verb-dispatch engine).

Relocate an organization's spatial presence (``ActionType.MOVE``). Validates
the target is an existing ``territory`` node, then rewrites the acting org's
``territory_ids`` (a round-trip Organization model field):

* ``relocate`` (default): ``territory_ids = [target]`` and ``headquarters_id
  = target`` (keeps the ``headquarters_id in territory_ids`` invariant).
* ``expand``: append the target to the existing ``territory_ids``.

An invalid target fails loud (``success=False``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph


def resolve_move(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — org state read live from graph
    graph: BabylonGraph,
    services: ServicesProtocol,  # noqa: ARG001 — no MoveDefines yet
) -> ActionResult:
    """Resolve a player MOVE action: relocate or expand org presence.

    Args:
        action: The MOVE action (``action_type == ActionType.MOVE``).
        org_attrs: Acting organization's node attributes.
        graph: World graph (mutated in place on the acting org node).
        services: ServicesProtocol (unused; no MoveDefines exist yet).

    Returns:
        :class:`~babylon.ooda.types.ActionResult`; ``success=False`` when the
        target is missing / not a territory, or the acting org node is absent.
    """
    target_node = graph.nodes.get(action.target_id)
    if target_node is None or target_node.get("_node_type") != "territory":
        return ActionResult(
            action=action,
            success=False,
            failure_reason="MOVE target is not an existing territory node",
        )

    org_node = graph.nodes.get(action.org_id)
    if org_node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="MOVE acting org node not found in graph",
        )

    mode = str(action.params.get("mode", "relocate"))
    current: list[str] = list(org_node.get("territory_ids", []))

    if mode == "expand":
        new_ids = current if action.target_id in current else [*current, action.target_id]
        graph.update_node(action.org_id, territory_ids=new_ids)
        effects: dict[str, Any] = {"mode": mode, "territory_ids": new_ids}
    else:
        graph.update_node(
            action.org_id,
            territory_ids=[action.target_id],
            headquarters_id=action.target_id,
        )
        effects = {"mode": "relocate", "territory_ids": [action.target_id]}

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_move"]
