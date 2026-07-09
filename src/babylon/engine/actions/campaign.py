"""CAMPAIGN verb resolver (verb-dispatch engine).

Broadcast propaganda (``ActionType.PROPAGANDIZE``). Thin delegate to the
Feature-032 effects machinery — same five-factor consciousness pathway as
EDUCATE, but scaled by the propagandize action base (symmetric inverse of
EDUCATE; less precise than education). No direct graph writes.

See Also:
    :func:`babylon.engine.actions.educate.resolve_educate`: the sibling
    consciousness-class resolver.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.ooda.action_effects import resolve_action

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.services import ServiceContainer
    from babylon.ooda.types import Action, ActionResult


def resolve_campaign(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServiceContainer,
) -> ActionResult:
    """Resolve a player CAMPAIGN action into a real consciousness effect.

    Args:
        action: The CAMPAIGN action (``action_type == ActionType.PROPAGANDIZE``).
        org_attrs: Acting organization's node attributes.
        graph: World graph (read-only for this verb).
        services: ServiceContainer providing the OODA/organization/reactionary
            defines.

    Returns:
        :class:`~babylon.ooda.types.ActionResult` carrying the five-factor
        ``consciousness_delta`` (non-None for PROPAGANDIZE).
    """
    return resolve_action(
        action,
        org_attrs,
        graph,
        services.defines.ooda,
        services.defines.organization,
        services.defines.reactionary,
    )


__all__ = ["resolve_campaign"]
