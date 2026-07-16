"""INVESTIGATE verb resolver (verb-dispatch engine).

Intelligence gathering (``ActionType.MAP_NETWORK``). Investigate mutates NO
MATERIAL graph state — it resolves against the information/fog-of-war layer
(the consciousness simplex and the economy are untouched). It returns a
``direct_effects`` payload naming which attributes of the target were
revealed; the bridge/UI consumes it from the persisted result.

EH Phase 2 (Wave 5): when the PLAYER org investigates a TERRITORY, the
resolver additionally writes ``investigation_intel`` onto the territory node
— information-layer state that ``compute_epistemic_horizon`` adds into
``intel_confidence`` (the corpus's "Investigate is the tactical supplement;
mass work is the strategic base"). The boost persists until Phase 3 lands
intel decay (documented limitation, not an oversight). Non-player
investigations reveal to their actor via ``direct_effects`` but never raise
the PLAYER's I_c.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph

#: Attribute names revealed per target node type (the "fog of war" lift).
_REVEAL_BY_NODE_TYPE: dict[str, list[str]] = {
    "territory": ["heat", "rent_level", "population", "under_eviction"],
    "social_class": ["wealth", "organization", "repression_faced"],
    "organization": ["cohesion", "cadre_level", "heat", "budget"],
}
_REVEAL_DEFAULT: list[str] = ["heat"]


def resolve_investigate(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — no acting-org state consumed
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player INVESTIGATE action (information-layer only).

    Args:
        action: The INVESTIGATE action (``action_type == ActionType.MAP_NETWORK``).
        org_attrs: Acting organization's node attributes (unused).
        graph: World graph. Material state is never mutated; the one write is
            the information-layer ``investigation_intel`` territory attr
            (player org + territory target only — EH Phase 2).
        services: ServicesProtocol (``defines.epistemic_horizon
            .investigate_intel_boost``).

    Returns:
        :class:`~babylon.ooda.types.ActionResult` with ``direct_effects``
        naming revealed attributes; ``success=False`` if the target is absent.
    """
    target_node = graph.nodes.get(action.target_id)
    if target_node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="INVESTIGATE target not found in graph",
        )

    node_type = str(target_node.get("_node_type", ""))
    revealed = _REVEAL_BY_NODE_TYPE.get(node_type, _REVEAL_DEFAULT)
    scan_type = str(action.params.get("scan_type", "territory_scan"))

    # EH Phase 2: the player's investigation of a territory earns I_c.
    # Player identity comes from graph metadata (WorldState.player_org_id,
    # EH ruling 6); absent metadata (synthetics, NPC-only flows) => no write.
    metadata = getattr(graph, "graph", None)
    player_org_id = metadata.get("player_org_id") if isinstance(metadata, dict) else None
    if node_type == "territory" and player_org_id is not None and action.org_id == player_org_id:
        boost = services.defines.epistemic_horizon.investigate_intel_boost
        existing = float(target_node.get("investigation_intel", 0.0))
        graph.update_node(
            action.target_id,
            investigation_intel=min(1.0, existing + boost),
        )

    return ActionResult(
        action=action,
        success=True,
        direct_effects={
            "scan_type": scan_type,
            "revealed": {action.target_id: revealed},
        },
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


__all__ = ["resolve_investigate"]
