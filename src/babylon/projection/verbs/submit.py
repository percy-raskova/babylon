"""Structured verb submission — the ONE write the read side owns (WO-39).

A verb submission is a row in the runtime action queue (``game_turn``) and
nothing else: no direct graph mutation — the engine's OODASystem folds the
queue into the next tick's action phase and adjudicates (Ruling R4,
Article V atomicity). Ported from the legacy bridge's ``submit_action``;
the affordability gate is the same :func:`check_can_afford` the plate
shows, so a plate note can never disagree with a rejection.

The legacy bridge's in-memory ``_session_action_history`` (trap-detection
cache) deliberately does NOT port: it is a per-process web artifact; the
queue table itself is the durable history a TUI-side trap reader consults.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from babylon.models.vanguard_resources import VanguardResources, check_can_afford
from babylon.projection.verbs.preview import CANONICAL_VERBS, VERB_TO_ACTION_TYPE
from babylon.topology import BabylonGraph

#: ATTACK's mode-specific labor costs (legacy bridge parity; the AP check is
#: bypassed for ATTACK since over-budget AP resolves with degraded
#: effectiveness rather than rejection).
_ATTACK_TARGETED_CADRE_LABOR: float = 4.0
_ATTACK_MASS_SYMPATHIZER_LABOR: float = 15.0


class TurnSink(Protocol):
    """Structural seam for the runtime queue's ``submit_turn``.

    Satisfied by the Postgres runtime persistence without projection
    importing a concrete backend; tests satisfy it with a journal stub.
    """

    def submit_turn(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """Persist one queued turn row and return its integer id."""
        ...


def _check_affordability(
    org_data: dict[str, Any], verb: str, params_json: dict[str, Any] | None
) -> None:
    """Raise ``ValueError`` when the org cannot afford ``verb``.

    Verbatim port of the bridge gate: ATTACK charges mode-specific labor
    pools; every other verb goes through :func:`check_can_afford`.

    :param org_data: The acting org's graph attributes.
    :param verb: The canonical verb.
    :param params_json: Submission params (ATTACK reads ``mode``).
    :raises ValueError: With the player-facing rejection message.
    """
    resources = VanguardResources.from_organization(
        cadre_level=float(org_data.get("cadre_level", 0.0)),
        cohesion=float(org_data.get("cohesion", 0.0)),
        budget=float(org_data.get("budget", 0.0)),
        heat=float(org_data.get("heat", 0.0)),
        territory_count=len(org_data.get("territory_ids", [])),
    )
    if verb == "attack":
        mode = (params_json or {}).get("mode", "targeted")
        if mode == "targeted":
            if resources.cadre_labor < _ATTACK_TARGETED_CADRE_LABOR:
                raise ValueError(
                    f"Cannot afford 'attack' (targeted): Need "
                    f"{_ATTACK_TARGETED_CADRE_LABOR} CL, have {resources.cadre_labor:.1f}"
                )
        elif resources.sympathizer_labor < _ATTACK_MASS_SYMPATHIZER_LABOR:
            raise ValueError(
                f"Cannot afford 'attack' (mass): Need "
                f"{_ATTACK_MASS_SYMPATHIZER_LABOR} SL, have {resources.sympathizer_labor:.1f}"
            )
        return
    can_afford, reason = check_can_afford(resources, verb)
    if not can_afford:
        raise ValueError(f"Cannot afford '{verb}': {reason}")


def submit_verb(
    persistence: TurnSink,
    *,
    session_id: UUID,
    tick: int,
    org_id: str,
    verb: str,
    graph: BabylonGraph,
    action_type: str | None = None,
    target_id: str | None = None,
    target_community: str | None = None,
    params_json: dict[str, Any] | None = None,
) -> int:
    """Queue one structured verb for the given tick.

    :param persistence: The runtime queue (structural :class:`TurnSink`).
    :param session_id: The campaign session UUID.
    :param tick: The tick this action applies to.
    :param org_id: The acting organization.
    :param verb: One of the nine canonical player verbs.
    :param graph: Current world graph — read only for the affordability
        gate; an org absent from the graph skips the gate (legacy parity:
        persistence owns the integrity error).
    :param action_type: Optional action-type classification passthrough.
    :param target_id: Optional target node id.
    :param target_community: Optional target community id.
    :param params_json: Optional verb parameters.
    :returns: The integer turn id from the queue.
    :raises ValueError: When ``verb`` is not canonical, or the org cannot
        afford it (player-facing message, same copy as the plate note).
    """
    if verb not in CANONICAL_VERBS:
        raise ValueError(
            f"{verb!r} is not a canonical verb (expected one of {sorted(CANONICAL_VERBS)})"
        )
    if org_id in graph.nodes:
        _check_affordability(dict(graph.nodes[org_id]), verb, params_json)
    return persistence.submit_turn(
        session_id=session_id,
        tick=tick,
        org_id=org_id,
        verb=verb,
        action_type=action_type,
        target_id=target_id,
        target_community=target_community,
        params_json=params_json,
    )


def build_player_actions(
    pending: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Fold pending queue rows into the engine's injection shape.

    Verbatim port of the bridge's pre-step fold: the engine's OODASystem
    reads ``persistent_context["player_actions"]`` as ``org_id -> [action
    dicts]`` with engine ``ActionType`` values.

    :param pending: Unresolved ``game_turn`` rows for the tick.
    :returns: The ``player_actions`` mapping, empty when nothing is queued.
    """
    player_actions: dict[str, list[dict[str, Any]]] = {}
    for action in pending:
        org_id = action["org_id"]
        verb = action.get("verb", "")
        action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
        action_type_val = action_type_enum.value if action_type_enum else verb
        player_actions.setdefault(org_id, []).append(
            {
                "action_type": action_type_val,
                "target_id": action.get("target_id", org_id) or org_id,
                "org_id": org_id,
                "action_point_cost": 1,
                # `or {}`, not a .get default: a submit without params
                # persists params_json as JSON null, and .get's default only
                # covers an ABSENT key — None fails Action's params dict
                # validation and kills the whole resolve.
                "params": action.get("params_json") or {},
            }
        )
    return player_actions
