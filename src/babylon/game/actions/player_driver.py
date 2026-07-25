"""Player driver — the keyboard write-path, closing the dead ``submit_verb`` seam.

The TUI verb plate is render-only; this module is the caller it names. It gates an action
against the registry (agent-type + LIVE status) then delegates to the existing
:func:`babylon.projection.verbs.submit.submit_verb` — which keeps the affordability gate and
canonical-verb check — feeding the ``TurnSink`` → ``game_turn`` queue. Lives in ``babylon.game``
(not ``tui``) to respect the projection-only import contract.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from babylon.game.actions.registry import ACTION_REGISTRY
from babylon.projection.verbs.submit import TurnSink, submit_verb
from babylon.topology import BabylonGraph


class ActionNotPermitted(RuntimeError):
    """Raised when an agent type may not issue the requested action."""


class ActionNotLive(RuntimeError):
    """Raised when a registered action is a STUB (no wired effect yet)."""


def issue_action(
    action_id: str,
    agent_type: str,
    org_id: str,
    sink: TurnSink,
    *,
    session_id: UUID,
    tick: int,
    graph: BabylonGraph,
    target_id: str | None = None,
    target_community: str | None = None,
    params_json: dict[str, Any] | None = None,
) -> int:
    """Gate ``action_id`` for ``agent_type`` then enqueue it; return the turn id.

    :raises KeyError: Unknown action id (loud failure).
    :raises ActionNotPermitted: ``agent_type`` is not in the spec's ``agent_types``.
    :raises ActionNotLive: The spec is a STUB with no wired effect.
    :raises ValueError: Propagated from ``submit_verb`` (non-canonical verb or
        the affordability gate).
    """
    spec = ACTION_REGISTRY[action_id]  # KeyError = unknown action (loud)
    if agent_type not in spec.agent_types:
        raise ActionNotPermitted(f"{agent_type!r} may not issue {action_id!r}")
    if spec.status != "LIVE":
        raise ActionNotLive(f"{action_id!r} is a STUB; no wired effect")
    return submit_verb(
        sink,
        session_id=session_id,
        tick=tick,
        org_id=org_id,
        verb=spec.id,
        graph=graph,
        action_type=spec.effect_ref,
        target_id=target_id,
        target_community=target_community,
        params_json=params_json,
    )
