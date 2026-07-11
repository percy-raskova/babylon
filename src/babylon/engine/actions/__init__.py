"""Player-verb resolver registry (verb-dispatch engine — Design A).

Maps engine :class:`~babylon.models.enums.ActionType` members to resolver
callables. The uniform signature is::

    resolve_<verb>(action, org_attrs, graph, services) -> ActionResult

A missing resolver returns ``ActionResult(success=False, failure_reason=...)``
— loud, never a silent success. The nine canonical player verbs each have a
registered resolver; every other ActionType (NPC/state verbs resolved by the
Feature-032 machinery, or auto-triggered verbs) has none and fails loud if a
player action is ever dispatched for it.

See Also:
    :func:`babylon.ooda.action_effects.resolve_action`: the effects machinery
    the consciousness-class resolvers (educate / campaign / aid) compose.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from babylon.engine.actions.aid import resolve_aid
from babylon.engine.actions.attack import resolve_attack
from babylon.engine.actions.campaign import resolve_campaign
from babylon.engine.actions.educate import resolve_educate
from babylon.engine.actions.investigate import resolve_investigate
from babylon.engine.actions.mobilize import resolve_mobilize
from babylon.engine.actions.move import resolve_move
from babylon.engine.actions.negotiate import resolve_negotiate
from babylon.engine.actions.reproduce import resolve_reproduce
from babylon.models.enums import ActionType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph


class VerbResolver(Protocol):
    """Structural type for a player-verb resolver."""

    def __call__(
        self,
        action: Action,
        org_attrs: dict[str, Any],
        graph: BabylonGraph,
        services: ServicesProtocol,
    ) -> ActionResult:
        """Resolve one player action into an :class:`ActionResult`."""
        ...


#: The single source of truth mapping ActionType -> resolver. The web bridge's
#: ``VERB_TO_ACTION_TYPE`` maps player verb strings onto exactly these keys;
#: the contract suite pins ``set(VERB_TO_ACTION_TYPE.values()) == keys``.
VERB_RESOLVERS: dict[ActionType, VerbResolver] = {
    ActionType.EDUCATE: resolve_educate,
    ActionType.RECRUIT: resolve_reproduce,
    ActionType.ATTACK_INFRASTRUCTURE: resolve_attack,
    ActionType.PROTEST: resolve_mobilize,
    ActionType.PROPAGANDIZE: resolve_campaign,
    ActionType.PROVIDE_SERVICE: resolve_aid,
    ActionType.MAP_NETWORK: resolve_investigate,
    ActionType.MOVE: resolve_move,
    ActionType.PROPOSE_ALLIANCE: resolve_negotiate,
}


def resolve_player_action(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Dispatch one player action to its registered resolver.

    Args:
        action: The player action to resolve.
        org_attrs: Acting organization's node attributes.
        graph: World graph.
        services: ServicesProtocol providing defines.

    Returns:
        The resolver's :class:`ActionResult`, or — when no resolver is
        registered for ``action.action_type`` — a loud failure result
        (``success=False`` with a ``failure_reason``). Never raises, never
        silently succeeds.
    """
    resolver = VERB_RESOLVERS.get(action.action_type)
    if resolver is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason=(f"No resolver registered for action_type '{action.action_type.value}'"),
        )
    return resolver(action=action, org_attrs=org_attrs, graph=graph, services=services)


__all__ = [
    "VERB_RESOLVERS",
    "VerbResolver",
    "resolve_player_action",
]
