"""NEGOTIATE verb resolver (verb-dispatch engine).

Bilateral edge state machine (``ActionType.PROPOSE_ALLIANCE``). Success is
gated on the acting org's leverage (``cohesion + cadre_level``). On success:

* an existing antagonistic-class edge (exploitation / competition / repression
  / antagonistic) is flipped to ``TRANSACTIONAL``;
* otherwise a fresh ``TRANSACTIONAL`` edge is created between the two parties.

Only the round-trip edge field ``edge_type`` (mirrored to the internal
``_edge_type`` key) is written, matching the layer-3 ORGANIZE flip precedent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EdgeType, EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action

#: Minimum ``cohesion + cadre_level`` to bring a counterparty to the table.
_LEVERAGE_THRESHOLD = 0.1
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
    services: ServicesProtocol,  # noqa: ARG001 — no NegotiateDefines yet
) -> ActionResult:
    """Resolve a player NEGOTIATE action: flip or forge a TRANSACTIONAL edge.

    Args:
        action: The NEGOTIATE action (``action_type == ActionType.PROPOSE_ALLIANCE``).
        org_attrs: Acting organization's node attributes (leverage source).
        graph: World graph (mutated in place on the org→target edge).
        services: ServicesProtocol (unused; no NegotiateDefines exist yet).

    Returns:
        :class:`~babylon.ooda.types.ActionResult`; ``success=False`` when the
        counterparty is missing or the org lacks leverage.
    """
    org_id = action.org_id
    target_id = action.target_id
    if graph.nodes.get(target_id) is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="NEGOTIATE counterparty not found in graph",
        )

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


__all__ = ["resolve_negotiate"]
