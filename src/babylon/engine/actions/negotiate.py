"""NEGOTIATE verb resolver (verb-dispatch engine).

Bilateral edge state machine (``ActionType.PROPOSE_ALLIANCE``). Success is
gated on the acting org's leverage (``cohesion + cadre_level``). On success:

* an existing antagonistic-class edge (exploitation / competition / repression
  / antagonistic) is flipped to ``TRANSACTIONAL``;
* otherwise a fresh ``TRANSACTIONAL`` edge is created between the two parties.

Only the round-trip edge field ``edge_type`` (mirrored to the internal
``_edge_type`` key) is written, matching the layer-3 ORGANIZE flip precedent.

**Negotiate(Coalition) sub-verb (P25 U11, ADR137):** an org holding a stance
whose :class:`~babylon.models.entities.doctrine.DoctrineCapability` declares
``negotiate:coalition`` (entryism) may pass ``params["mode"] = "coalition"`` to
enter a host machine WITHOUT the leverage gate — and pay for the seat in
``CO_OPTIVE`` dependence instead. That is the material trade the stance makes,
and the dependence feeds straight back into the doctrine practice environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.engine.actions._capability import grants_verb_mode
from babylon.models.enums import EdgeMode, EdgeType, EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.config.defines.politics import PoliticsDefines
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph

#: Minimum ``cohesion + cadre_level`` to bring a counterparty to the table.
_LEVERAGE_THRESHOLD = 0.1
#: Negotiate(Coalition) sub-mode: enter a host machine as a subordinate bloc.
_MODE_COALITION = "coalition"
#: Capability key a stance must declare to unlock the coalition sub-mode.
_COALITION_CAPABILITY = "negotiate:coalition"
#: Antagonistic-class edge types a successful negotiation defuses.
_ANTAGONISTIC_EDGE_TYPES: frozenset[str] = frozenset(
    {
        EdgeType.EXPLOITATION.value,
        EdgeType.COMPETITION.value,
        EdgeType.REPRESSION.value,
        EdgeType.ANTAGONISTIC.value,
    }
)


def _edge_type_value(raw: Any) -> str:
    """Return the string value of a stored edge_type (enum or str)."""
    return raw.value if hasattr(raw, "value") else str(raw)


def resolve_negotiate(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player NEGOTIATE action: flip or forge a TRANSACTIONAL edge.

    Args:
        action: The NEGOTIATE action (``action_type == ActionType.PROPOSE_ALLIANCE``).
            An optional ``mode`` param selects the Negotiate(Coalition) sub-verb.
        org_attrs: Acting organization's node attributes (leverage source).
        graph: World graph (mutated in place on the org→target edge).
        services: ServicesProtocol (read for the politics defines on the
            coalition sub-verb; no NegotiateDefines exist for the base path).

    Returns:
        :class:`~babylon.ooda.types.ActionResult`; ``success=False`` when the
        counterparty is missing, the org lacks leverage, or the org has not
        acquired the requested sub-mode.
    """
    org_id = action.org_id
    target_id = action.target_id
    if graph.nodes.get(target_id) is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="NEGOTIATE counterparty not found in graph",
        )

    mode = str(action.params.get("mode", "")).strip()
    if mode:
        if mode != _MODE_COALITION:
            return ActionResult(
                action=action,
                success=False,
                failure_reason=f"NEGOTIATE: unknown mode {mode!r}",
            )
        if not grants_verb_mode(org_attrs, _COALITION_CAPABILITY):
            return ActionResult(
                action=action,
                success=False,
                failure_reason=(
                    f"NEGOTIATE(coalition): no acquired doctrine stance grants "
                    f"{_COALITION_CAPABILITY!r}"
                ),
            )
        return _resolve_coalition(action, graph, services.defines.politics)

    leverage = float(org_attrs.get("cohesion", 0.0)) + float(org_attrs.get("cadre_level", 0.0))
    if leverage < _LEVERAGE_THRESHOLD:
        return ActionResult(
            action=action,
            success=False,
            direct_effects={"leverage": leverage},
            failure_reason="insufficient leverage to open negotiations",
        )

    edge = graph.get_edge_data(org_id, target_id)
    if edge is None:
        graph.add_edge(org_id, target_id, edge_type=EdgeType.TRANSACTIONAL.value)
        effects: dict[str, Any] = {"edge_created": True, "leverage": leverage}
    else:
        current = _edge_type_value(edge.get("edge_type", ""))
        if current in _ANTAGONISTIC_EDGE_TYPES:
            edge["edge_type"] = EdgeType.TRANSACTIONAL.value
            edge["_edge_type"] = EdgeType.TRANSACTIONAL.value
            effects = {"edge_flipped": True, "from": current, "to": EdgeType.TRANSACTIONAL.value}
        else:
            effects = {"edge_flipped": False, "edge_type": current, "leverage": leverage}

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


def _resolve_coalition(
    action: Action,
    graph: BabylonGraph,
    politics: PoliticsDefines,
) -> ActionResult:
    """Negotiate(Coalition): enter the host machine, and owe it.

    Entryism does not need leverage — that is the whole point of it. An org
    without the strength to negotiate as an equal enters as a subordinate bloc
    and buys its seat with dependence. The edge is stamped ``CO_OPTIVE``
    (concessions for quiescence), which is precisely the mode
    :func:`~babylon.engine.systems.doctrine._practice_env` counts into
    ``CO_OPTIVE_SHARE`` — so every coalition entry walks the org one step
    toward the liquidationism absorbing state without any punitive tag delta.
    """
    org_id = action.org_id
    target_id = action.target_id
    accrual = float(politics.entryism_cooptation_rate)

    edge = graph.get_edge_data(org_id, target_id)
    if edge is None:
        graph.add_edge(
            org_id,
            target_id,
            edge_type=EdgeType.TRANSACTIONAL.value,
            edge_mode=EdgeMode.CO_OPTIVE.value,
            co_optive_dependence=accrual,
        )
        dependence = accrual
        created = True
    else:
        dependence = min(1.0, float(edge.get("co_optive_dependence", 0.0)) + accrual)
        edge["edge_mode"] = EdgeMode.CO_OPTIVE.value
        edge["co_optive_dependence"] = dependence
        created = False

    return ActionResult(
        action=action,
        success=True,
        direct_effects={
            "mode": _MODE_COALITION,
            "edge_created": created,
            "edge_mode": EdgeMode.CO_OPTIVE.value,
            "co_optive_dependence": dependence,
        },
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_negotiate"]
