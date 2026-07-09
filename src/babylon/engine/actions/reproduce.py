"""REPRODUCE verb resolver (verb-dispatch engine).

Organizational expansion (``ActionType.RECRUIT``) via two modes selected by
``params["mode"]``:

* ``cadre_training`` (default): raises ``cadre_level`` and ``cohesion``.
* ``mass_recruitment``: spends ``budget`` and dilutes ``cohesion``.

Only round-trip Organization model fields are written (``cadre_level``,
``cohesion``, ``budget``); the sympathizer/cadre pool bookkeeping from the
original spec-048 pseudo-code is recorded in ``direct_effects`` (there is no
``ReproduceDefines``, so the increments are module constants).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.services import ServiceContainer
    from babylon.ooda.types import Action

#: cadre_training: leadership-quality gain per action.
_CADRE_TRAINING_CADRE_GAIN = 0.05
#: cadre_training: cohesion gain per action (tight cadre => more unity).
_CADRE_TRAINING_COHESION_GAIN = 0.02
#: mass_recruitment: budget spent to onboard a wave of sympathizers.
_MASS_RECRUITMENT_BUDGET_COST = 5.0
#: mass_recruitment: cohesion diluted by rapid, shallow growth.
_MASS_RECRUITMENT_COHESION_LOSS = 0.05


def resolve_reproduce(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — org state read live from graph
    graph: BabylonGraph,
    services: ServiceContainer,  # noqa: ARG001 — no ReproduceDefines yet
) -> ActionResult:
    """Resolve a player REPRODUCE action (cadre training or mass recruitment).

    Args:
        action: The REPRODUCE action (``action_type == ActionType.RECRUIT``).
        org_attrs: Acting organization's node attributes.
        graph: World graph (mutated in place on the acting org node).
        services: ServiceContainer (unused; no ReproduceDefines exist yet).

    Returns:
        :class:`~babylon.ooda.types.ActionResult`; ``success=False`` when the
        org node is missing or mass recruitment cannot afford its budget cost.
    """
    org_id = action.org_id
    node = graph.nodes.get(org_id)
    if node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="REPRODUCE acting org node not found in graph",
        )

    mode = str(action.params.get("mode", "cadre_training"))
    cohesion = float(node.get("cohesion", 0.0))

    if mode == "mass_recruitment":
        budget = float(node.get("budget", 0.0))
        if budget < _MASS_RECRUITMENT_BUDGET_COST:
            return ActionResult(
                action=action,
                success=False,
                direct_effects={"mode": mode, "available_budget": budget},
                failure_reason="insufficient budget for mass recruitment",
            )
        new_cohesion = max(0.0, cohesion - _MASS_RECRUITMENT_COHESION_LOSS)
        graph.update_node(
            org_id,
            budget=budget - _MASS_RECRUITMENT_BUDGET_COST,
            cohesion=new_cohesion,
        )
        effects: dict[str, Any] = {
            "mode": mode,
            "budget_spent": _MASS_RECRUITMENT_BUDGET_COST,
            "cohesion_delta": new_cohesion - cohesion,
        }
    else:
        cadre = float(node.get("cadre_level", 0.0))
        new_cadre = min(1.0, cadre + _CADRE_TRAINING_CADRE_GAIN)
        new_cohesion = min(1.0, cohesion + _CADRE_TRAINING_COHESION_GAIN)
        graph.update_node(org_id, cadre_level=new_cadre, cohesion=new_cohesion)
        effects = {
            "mode": "cadre_training",
            "cadre_delta": new_cadre - cadre,
            "cohesion_delta": new_cohesion - cohesion,
        }

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_reproduce"]
