"""Layer 3: Consequence propagation (Feature 032).

Aggregates action results and propagates effects to communities:
consciousness, heat, edge transitions, infrastructure, contestation.

See Also:
    ``specs/032-ooda-loop-system/contracts/consciousness-effect-contract.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.config.defines import OODADefines
from babylon.domain.geography.corridor_mesh import apply_uniform_territory_splash
from babylon.models.enums import ActionType, EdgeType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.config.defines import TransportDefines
    from babylon.domain.geography.corridor_mesh import CorridorMesh
    from babylon.topology.graph import BabylonGraph


def process_layer3(
    action_results: list[ActionResult],
    graph: BabylonGraph,
    defines: OODADefines,
    corridor_mesh: CorridorMesh | None = None,
    transport_defines: TransportDefines | None = None,
) -> dict[str, Any]:
    """Propagate action consequences to communities.

    Five sub-processors update community state in the graph:
    1. Consciousness aggregation (CI delta)
    2. Heat propagation (REPRESS/SURVEIL)
    3. Edge transitions (ORGANIZE)
    4. Infrastructure effects (BUILD/ATTACK) — plus, when ``corridor_mesh``/
       ``transport_defines`` are supplied, the spec-108 uniform territory
       splash (ADR165 Director ruling 4): every corridor-mesh edge touching
       the target territory is degraded/repaired uniformly alongside the
       community-scoped ``infrastructure`` float.
    5. Contestation stacking (AGITATE)

    Args:
        action_results: All resolved ActionResults from the tick.
        graph: World graph (mutated in place).
        defines: OODADefines coefficients.
        corridor_mesh: Optional spec-108 corridor mesh (default ``None`` —
            byte-identical to pre-U5e behavior when omitted, e.g. no
            campaign has composed a mesh yet).
        transport_defines: Optional ``TransportDefines`` supplying the
            uniform-splash magnitudes (``attack_splash_condition_damage``/
            ``build_splash_condition_repair``). Both this and
            ``corridor_mesh`` must be present for the splash to fire.

    Returns:
        Summary dict with counts of effects applied.
    """
    summary: dict[str, Any] = {}

    # Feature 034: consciousness and contestation are now derived quantities
    # computed from org landscape in CommunitySystem, not direct writes.
    summary["consciousness"] = 0
    summary["heat_updates"] = _propagate_heat(action_results, graph, defines)
    summary["edge_transitions"] = _propagate_edge_transitions(action_results, graph)
    summary["infrastructure_updates"] = _propagate_infrastructure(
        action_results, graph, defines, corridor_mesh, transport_defines
    )
    summary["contestation_updates"] = 0

    return summary


def _propagate_heat(
    results: list[ActionResult],
    graph: BabylonGraph,
    defines: OODADefines,
) -> int:
    """Increase community heat from REPRESS/SURVEIL actions.

    Args:
        results: Action results.
        graph: World graph (mutated).
        defines: OODADefines with heat delta coefficients.

    Returns:
        Number of heat updates.
    """
    updates = 0
    max_results = 1000
    for idx, result in enumerate(results):
        action_type = result.action.action_type
        if action_type not in {ActionType.REPRESS, ActionType.SURVEIL}:
            if idx >= max_results:
                break
            continue

        target = result.action.target_id
        node_data = graph.nodes.get(target)
        if node_data is None:
            if idx >= max_results:
                break
            continue

        heat_delta = (
            defines.repress_heat_delta
            if action_type == ActionType.REPRESS
            else defines.surveil_heat_delta
        )
        current_heat = float(node_data.get("heat", 0.0))
        graph.nodes[target]["heat"] = min(1.0, current_heat + heat_delta)
        updates += 1

        if idx >= max_results:
            break

    return updates


def _propagate_edge_transitions(
    results: list[ActionResult],
    graph: BabylonGraph,
) -> int:
    """Transition edges from TRANSACTIONAL to SOLIDARISTIC on ORGANIZE.

    Args:
        results: Action results.
        graph: World graph (mutated).

    Returns:
        Number of edge transitions.
    """
    transitions = 0
    max_results = 1000
    for idx, result in enumerate(results):
        if result.action.action_type != ActionType.ORGANIZE:
            if idx >= max_results:
                break
            continue

        org_id = result.action.org_id
        target_id = result.action.target_id

        if graph.has_edge(org_id, target_id):
            edge_data = graph.edges[org_id, target_id]
            edge_type = edge_data.get("edge_type", "")
            if edge_type == EdgeType.TRANSACTIONAL.value or edge_type == EdgeType.TRANSACTIONAL:
                graph.edges[org_id, target_id]["edge_type"] = EdgeType.SOLIDARISTIC.value
                transitions += 1

        if idx >= max_results:
            break

    return transitions


def _propagate_infrastructure(
    results: list[ActionResult],
    graph: BabylonGraph,
    defines: OODADefines,
    corridor_mesh: CorridorMesh | None,
    transport_defines: TransportDefines | None,
) -> int:
    """Apply BUILD/ATTACK_INFRASTRUCTURE effects to communities.

    Args:
        results: Action results.
        graph: World graph (mutated).
        defines: OODADefines with infrastructure delta coefficients.
        corridor_mesh: Optional spec-108 corridor mesh — when present
            (alongside ``transport_defines``), every BUILD/ATTACK also
            triggers the ADR165 Director ruling 4 uniform territory splash.
        transport_defines: Optional TransportDefines supplying the splash
            magnitudes.

    Returns:
        Number of infrastructure updates.
    """
    updates = 0
    max_results = 1000
    for idx, result in enumerate(results):
        action_type = result.action.action_type
        if action_type == ActionType.BUILD_INFRASTRUCTURE:
            delta = defines.build_infrastructure_delta
        elif action_type == ActionType.ATTACK_INFRASTRUCTURE:
            delta = -defines.attack_infrastructure_delta
        else:
            if idx >= max_results:
                break
            continue

        target = result.action.target_id
        node_data = graph.nodes.get(target)
        if node_data is None:
            if idx >= max_results:
                break
            continue

        current = float(node_data.get("infrastructure", 0.5))
        graph.nodes[target]["infrastructure"] = max(0.0, min(1.0, current + delta))
        updates += 1

        # ADR165 Director ruling 4 (spec-108 T6): the SAME BUILD/ATTACK
        # delta that just adjusted the community-scoped `infrastructure`
        # float ALSO degrades/restores every corridor-mesh edge touching
        # this territory, uniformly — never edge-targeted in slice 1.
        if corridor_mesh is not None and transport_defines is not None:
            splash_delta = (
                transport_defines.build_splash_condition_repair
                if action_type == ActionType.BUILD_INFRASTRUCTURE
                else -transport_defines.attack_splash_condition_damage
            )
            apply_uniform_territory_splash(corridor_mesh, target, splash_delta)

        if idx >= max_results:
            break

    return updates


__all__ = ["process_layer3"]
