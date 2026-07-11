"""EDUCATE verb resolver (verb-dispatch engine).

Consciousness-raising through education. Thin delegate to the Feature-032
effects machinery (:func:`babylon.ooda.action_effects.resolve_action`),
which computes a five-factor :class:`~babylon.domain.organizations.types.ConsciousnessDelta`
(plus the AGITATE-coupled EDUCATE contestation bonus). No direct graph writes.

See Also:
    :func:`babylon.ooda.action_effects.compute_consciousness_delta`: the
    pure five-factor formula this verb composes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.ooda.action_effects import resolve_action

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action, ActionResult
    from babylon.topology.graph import BabylonGraph


def resolve_educate(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player EDUCATE action into a real consciousness effect.

    Args:
        action: The EDUCATE action (``action_type == ActionType.EDUCATE``).
        org_attrs: Acting organization's node attributes.
        graph: World graph (read-only for this verb).
        services: ServicesProtocol providing the OODA/organization/reactionary
            defines.

    Returns:
        :class:`~babylon.ooda.types.ActionResult` carrying the five-factor
        ``consciousness_delta`` (non-None for EDUCATE, whose action base is
        nonzero).
    """
    return resolve_action(
        action,
        org_attrs,
        graph,
        services.defines.ooda,
        services.defines.organization,
        services.defines.reactionary,
    )


__all__ = ["resolve_educate"]
