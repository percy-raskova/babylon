"""CAMPAIGN verb resolver (verb-dispatch engine).

Broadcast propaganda (``ActionType.PROPAGANDIZE``). Thin delegate to the
Feature-032 effects machinery — same five-factor consciousness pathway as
EDUCATE, but scaled by the propagandize action base (symmetric inverse of
EDUCATE; less precise than education).

**Mass-work SOLIDARITY (Unit 6 write side, ADR087):** PROPAGANDIZE is one of
the three mass-work verbs that create-or-strengthen an org -> class
SOLIDARITY edge when targeting a ``social_class`` node, amplified by the
org's MASS_LINK doctrine tag — the one direct graph write this resolver makes.

See Also:
    :func:`babylon.engine.actions.educate.resolve_educate`: the sibling
    consciousness-class resolver.
    :func:`babylon.engine.actions._mass_work.apply_mass_work_solidarity`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.engine.actions._mass_work import apply_mass_work_solidarity
from babylon.ooda.action_effects import resolve_action

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action, ActionResult
    from babylon.topology.graph import BabylonGraph


def resolve_campaign(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player CAMPAIGN action into a real consciousness effect.

    Args:
        action: The CAMPAIGN action (``action_type == ActionType.PROPAGANDIZE``).
        org_attrs: Acting organization's node attributes.
        graph: World graph (written by the mass-work SOLIDARITY producer).
        services: ServicesProtocol providing the OODA/organization/reactionary
            defines.

    Returns:
        :class:`~babylon.ooda.types.ActionResult` carrying the five-factor
        ``consciousness_delta`` (non-None for PROPAGANDIZE).
    """
    apply_mass_work_solidarity(
        graph, action.org_id, org_attrs, action.target_id, services.defines.doctrine
    )
    return resolve_action(
        action,
        org_attrs,
        graph,
        services.defines.ooda,
        services.defines.organization,
        services.defines.reactionary,
        doctrine=services.defines.doctrine,
    )


__all__ = ["resolve_campaign"]
