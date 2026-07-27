"""The unified, agent-type-gated action registry.

One action algebra: the player's nine Article V verbs and the institutional macro-actions are
all :class:`ActionSpec` rows, gated by ``agent_types``. Intersections are actions available to
several types. ``status`` marks whether the effect is wired (``LIVE``) or an honest placeholder
(``STUB``). See ``project/research/24-the-archive/PLAYER_INTERFACE_SHELL_design.md`` §D.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from babylon.projection.verbs.preview import CANONICAL_VERBS, VERB_TO_ACTION_TYPE

ActionStatus = Literal["LIVE", "STUB"]

TargetShape = Literal["self", "target"]
"""Whether an action always targets the acting agent itself (``"self"``) or
requires an explicit target entity (``"target"``) — unit "verb-targeting"
(shell-interconnect). Static, declared metadata about the ACTION's own
semantics — contrast :attr:`~babylon.projection.verbs.view_models.VerbRow.
candidate_target_ids`, the dynamic, graph-state-dependent set of WHICH real
entities are valid targets right now. A future per-verb picker widget reads
``target_shape`` first (should it even prompt for a target at all?) before
ever consulting ``candidate_target_ids`` (what would it offer?)."""


class ActionSpec(BaseModel):
    """A single action any qualifying agent may issue.

    :param id: stable action key (a verb name or macro-action slug).
    :param label: human-facing label for the action bar / dossier.
    :param agent_types: the agent types permitted to issue it.
    :param cost: action-point cost.
    :param preconditions: named precondition keys (evaluated by the driver).
    :param effect_ref: the engine ``ActionType`` (or macro-effect slug) this maps to.
    :param status: ``LIVE`` if the effect is wired, ``STUB`` for an honest placeholder.
    :param target_shape: ``"self"`` or ``"target"`` (see :data:`TargetShape`).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    label: str
    agent_types: frozenset[str]
    cost: int = Field(ge=0)
    preconditions: tuple[str, ...] = ()
    effect_ref: str
    status: ActionStatus
    target_shape: TargetShape


_ORGANIZER = frozenset({"organizer"})
_STATE_CORP = frozenset({"state", "corporation"})

# The nine Article V verbs — LIVE, organizer-gated, mapped to real engine ActionTypes.
_VERB_LABELS = {
    "educate": "Educate",
    "reproduce": "Reproduce",
    "attack": "Attack",
    "mobilize": "Mobilize",
    "campaign": "Campaign",
    "aid": "Aid",
    "investigate": "Investigate",
    "move": "Move",
    "negotiate": "Negotiate",
}

#: "reproduce" always targets the acting org itself (build_verb_plate's own
#: "reproduce": True eligibility row comment, ``projection/verbs/plate.py``)
#: — every other canonical verb requires an explicit target entity.
_SELF_TARGETING_VERBS: frozenset[str] = frozenset({"reproduce"})

# Institutional macro-actions — STUB for v1.0 (mechanics gated on Vol I+II and beyond).
_STUB_MACRO = (
    ("construct", "Invest in construction"),
    ("fund_research", "Fund scientific research"),
    ("guide_tech", "Guide technology research"),
    ("procure_military", "Procure military equipment"),
    ("police", "Direct policing"),
    ("public_health", "Fund public health"),
    ("courts", "Direct the courts"),
    ("trade", "Conduct trade"),
    ("logistics", "Direct freight & logistics"),
)


def _build_registry() -> dict[str, ActionSpec]:
    registry: dict[str, ActionSpec] = {}
    for verb in sorted(CANONICAL_VERBS):
        registry[verb] = ActionSpec(
            id=verb,
            label=_VERB_LABELS[verb],
            agent_types=_ORGANIZER,
            cost=1,
            effect_ref=VERB_TO_ACTION_TYPE[verb],
            status="LIVE",
            target_shape="self" if verb in _SELF_TARGETING_VERBS else "target",
        )
    for slug, label in _STUB_MACRO:
        registry[slug] = ActionSpec(
            id=slug,
            label=label,
            agent_types=_STATE_CORP,
            cost=1,
            effect_ref=f"macro.{slug}",
            status="STUB",
            # Institutional macro-actions have no wired-effect target concept
            # yet (STUB, mechanics gated on Vol I+II and beyond — module
            # docstring) — "self" is the honest placeholder rather than
            # inventing a target shape for mechanics that don't exist yet.
            target_shape="self",
        )
    return registry


ACTION_REGISTRY: dict[str, ActionSpec] = _build_registry()


def actions_for(agent_type: str) -> tuple[ActionSpec, ...]:
    """Return the actions a given agent type may issue, id-sorted for determinism."""
    return tuple(
        spec for _, spec in sorted(ACTION_REGISTRY.items()) if agent_type in spec.agent_types
    )
