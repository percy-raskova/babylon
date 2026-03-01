"""Layer 3: Consequence propagation (Feature 032).

Aggregates action results and propagates effects to communities:
consciousness, heat, edge transitions, infrastructure, contestation.

See Also:
    ``specs/032-ooda-loop-system/contracts/consciousness-effect-contract.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, EdgeType
from babylon.ooda.types import ActionResult
from babylon.organizations.consciousness import aggregate_consciousness_effects
from babylon.organizations.types import ConsciousnessDelta

if TYPE_CHECKING:
    import networkx as nx


def process_layer3(
    action_results: list[ActionResult],
    graph: nx.DiGraph[str],
    defines: OODADefines,
) -> dict[str, Any]:
    """Propagate action consequences to communities.

    Five sub-processors update community state in the graph:
    1. Consciousness aggregation (CI delta)
    2. Heat propagation (REPRESS/SURVEIL)
    3. Edge transitions (ORGANIZE)
    4. Infrastructure effects (BUILD/ATTACK)
    5. Contestation stacking (AGITATE)

    Args:
        action_results: All resolved ActionResults from the tick.
        graph: World graph (mutated in place).
        defines: OODADefines coefficients.

    Returns:
        Summary dict with counts of effects applied.
    """
    summary: dict[str, Any] = {}

    summary["consciousness"] = _propagate_consciousness(action_results, graph)
    summary["heat_updates"] = _propagate_heat(action_results, graph, defines)
    summary["edge_transitions"] = _propagate_edge_transitions(action_results, graph)
    summary["infrastructure_updates"] = _propagate_infrastructure(action_results, graph, defines)
    summary["contestation_updates"] = _propagate_contestation(action_results, graph)

    return summary


def _propagate_consciousness(
    results: list[ActionResult],
    graph: nx.DiGraph[str],
) -> int:
    """Aggregate consciousness deltas per community and update CI.

    Args:
        results: Action results with optional consciousness_delta.
        graph: World graph (mutated).

    Returns:
        Number of communities updated.
    """
    # Group deltas by target community
    community_deltas: dict[str, list[ConsciousnessDelta]] = {}
    max_results = 1000
    for idx, result in enumerate(results):
        if result.consciousness_delta is not None:
            target = result.action.target_id
            if target not in community_deltas:
                community_deltas[target] = []
            community_deltas[target].append(result.consciousness_delta)
        if idx >= max_results:
            break

    # Apply aggregated effects
    updates = 0
    for community_id, deltas in community_deltas.items():
        node_data = graph.nodes.get(community_id)
        if node_data is None:
            continue

        current_ci = float(node_data.get("collective_identity", 0.0))
        aggregated = aggregate_consciousness_effects(deltas, current_ci)
        graph.nodes[community_id]["collective_identity"] = aggregated.new_ci
        updates += 1

    return updates


def _propagate_heat(
    results: list[ActionResult],
    graph: nx.DiGraph[str],
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
    graph: nx.DiGraph[str],
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
    graph: nx.DiGraph[str],
    defines: OODADefines,
) -> int:
    """Apply BUILD/ATTACK_INFRASTRUCTURE effects to communities.

    Args:
        results: Action results.
        graph: World graph (mutated).
        defines: OODADefines with infrastructure delta coefficients.

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

        if idx >= max_results:
            break

    return updates


def _propagate_contestation(
    results: list[ActionResult],
    graph: nx.DiGraph[str],
) -> int:
    """Stack contestation from AGITATE actions.

    Args:
        results: Action results with contestation_delta in direct_effects.
        graph: World graph (mutated).

    Returns:
        Number of contestation updates.
    """
    # Aggregate contestation deltas per community
    community_contestation: dict[str, float] = {}
    max_results = 1000
    for idx, result in enumerate(results):
        if result.action.action_type != ActionType.AGITATE:
            if idx >= max_results:
                break
            continue

        effects = result.direct_effects or {}
        delta = float(effects.get("contestation_delta", 0.0))
        if delta != 0.0:
            target = result.action.target_id
            community_contestation[target] = community_contestation.get(target, 0.0) + delta

        if idx >= max_results:
            break

    # Apply
    updates = 0
    for community_id, total_delta in community_contestation.items():
        node_data = graph.nodes.get(community_id)
        if node_data is None:
            continue

        current = float(node_data.get("ideological_contestation", 0.0))
        graph.nodes[community_id]["ideological_contestation"] = max(
            0.0, min(1.0, current + total_delta)
        )
        updates += 1

    return updates


__all__ = ["process_layer3"]
