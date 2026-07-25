"""Deterministic CPU ActionPolicy — the generalized npc_stub.

Non-human agents (state, corporations, institutions) decide via this deterministic policy over
the shared ActionSpec registry, seated in-tick and part of the hash (design §A: "opponents ARE
the physics"). Ordering reuses :data:`babylon.ooda.npc_stub._NPC_PRIORITIES` — the per-OrgType
priority table — with a stable id tiebreak for unlisted actions; no LLM, no wall-clock, no
randomness.

Follow-up (flagged in the design, out of this task): route the selected actions through the
SAME game_turn queue player verbs use, so human and CPU actions are adjudicated identically —
today npc_stub writes engine state directly. That unification is an engine refactor.
"""

from __future__ import annotations

from collections.abc import Mapping

from babylon.game.actions.registry import ActionSpec, actions_for
from babylon.models.enums import OrgType
from babylon.ooda.npc_stub import _NPC_PRIORITIES

#: Registry agent types → the engine OrgType whose npc_stub priority list orders them.
_AGENT_TYPE_TO_ORG_TYPE: dict[str, str] = {
    "organizer": OrgType.POLITICAL_FACTION.value,
    "state": OrgType.STATE_APPARATUS.value,
    "corporation": OrgType.BUSINESS.value,
}


def _priority_key(spec: ActionSpec, priorities: list[str]) -> tuple[int, str]:
    """Sort key: position in the org-type priority table, then stable id tiebreak."""
    try:
        rank = priorities.index(spec.effect_ref)
    except ValueError:
        rank = len(priorities)
    return (rank, spec.id)


def select_actions(
    agent_type: str,
    budget: int,
    observed: Mapping[str, float],  # noqa: ARG001 — the precondition feed, evaluated at wiring
) -> tuple[str, ...]:
    """Greedily select LIVE actions for ``agent_type`` until ``budget`` is spent.

    Deterministic: same inputs → same output tuple. ``observed`` is the agent's
    projected observation, reserved for the registry's named preconditions —
    the selection itself is priority-table-driven.
    """
    org_type = _AGENT_TYPE_TO_ORG_TYPE.get(agent_type, "")
    priorities = [a.value for a in _NPC_PRIORITIES.get(org_type, [])]
    chosen: list[str] = []
    remaining = budget
    for spec in sorted(actions_for(agent_type), key=lambda s: _priority_key(s, priorities)):
        if spec.status != "LIVE":
            continue
        if spec.cost <= remaining:
            chosen.append(spec.id)
            remaining -= spec.cost
    return tuple(chosen)
