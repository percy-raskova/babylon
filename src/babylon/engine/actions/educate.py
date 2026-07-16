"""EDUCATE verb resolver (verb-dispatch engine).

Consciousness-raising through education. Thin delegate to the Feature-032
effects machinery (:func:`babylon.ooda.action_effects.resolve_action`),
which computes a five-factor :class:`~babylon.domain.organizations.types.ConsciousnessDelta`
(plus the AGITATE-coupled EDUCATE contestation bonus).

**Educate(Doctrine) sub-verb (DoctrineSystem Unit 7b, ADR073):** a
``doctrine_node_id`` param turns EDUCATE into a standing STUDY order — the org
directs its theoretical labor toward a specific Doctrine Tree node, which the
DoctrineSystem honors each tick (save-toward-target instead of greedy
auto-acquire). This is a target type of the existing Educate verb, exactly as
Investigate carries Territory/Org/Edge sub-verbs — the Article V nine-verb
roster is untouched. Unlike the consciousness path, the sub-verb writes the
order onto the acting org's node directly (the mobilize/aid/move precedent).

See Also:
    :func:`babylon.ooda.action_effects.compute_consciousness_delta`: the
    pure five-factor formula the consciousness path composes.
    :func:`babylon.engine.systems.doctrine.step_organization`: the per-tick
    consumer of the standing study order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.action_effects import resolve_action
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph


def resolve_educate(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player EDUCATE action.

    Args:
        action: The EDUCATE action (``action_type == ActionType.EDUCATE``).
            A ``doctrine_node_id`` param selects the Educate(Doctrine)
            sub-verb (standing study order); otherwise the classic
            consciousness path runs.
        org_attrs: Acting organization's node attributes.
        graph: World graph (written only by the Doctrine sub-verb).
        services: ServicesProtocol providing the OODA/organization/reactionary
            defines.

    Returns:
        :class:`~babylon.ooda.types.ActionResult` — five-factor
        ``consciousness_delta`` on the classic path, or
        ``direct_effects["study_target_id"]`` on the Doctrine sub-verb.
    """
    doctrine_node_id = action.params.get("doctrine_node_id")
    if doctrine_node_id:
        return _resolve_study_order(action, org_attrs, graph, str(doctrine_node_id))
    return resolve_action(
        action,
        org_attrs,
        graph,
        services.defines.ooda,
        services.defines.organization,
        services.defines.reactionary,
    )


def _resolve_study_order(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    node_id: str,
) -> ActionResult:
    """Set (or loudly refuse) a standing doctrine study order (III.11)."""
    # Lazy import: only study orders pay the tree load; also keeps the
    # module import graph flat for the non-doctrine educate path.
    from babylon.domain.doctrine import load_doctrine_tree

    tree = load_doctrine_tree()
    node = tree.nodes.get(node_id)
    if node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason=f"EDUCATE(Doctrine): unknown doctrine node {node_id!r}",
        )
    if node.is_trap:
        return ActionResult(
            action=action,
            success=False,
            failure_reason=(
                f"EDUCATE(Doctrine): {node_id!r} is a trap ending — "
                "it is fallen into, never studied"
            ),
        )
    acquired = tuple(org_attrs.get("acquired_doctrine_ids", ()))
    if node_id in acquired:
        return ActionResult(
            action=action,
            success=False,
            failure_reason=f"EDUCATE(Doctrine): {node_id!r} is already acquired",
        )

    graph.update_node(action.org_id, study_target_id=node_id)
    return ActionResult(
        action=action,
        success=True,
        direct_effects={"study_target_id": node_id},
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_educate"]
