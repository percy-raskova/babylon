"""MOBILIZE Verb Resolution Module (Spec 047).

Implements the backend resolution logic for the MOBILIZE verb, interfacing
with the simulation graph and processing mobilization dynamics like turnout,
solidarity amplification, heat generation, strike outcomes, and backfire.
"""

from functools import reduce
from operator import mul
from typing import Any


def resolve_mobilize(
    action: Any,
    graph: Any,
    hypergraph: Any,
    defines: Any,
) -> dict[str, Any]:
    """Resolve player mobilize action against targets.

    1. Validate Resources: Ensure acting organization has required CL.
    2. Solidarity Multiplication: Determine edge multipliers for turnout.
    3. Turnout Calculation: Compute final turnout based on committed SL and multipliers.
    4. Effect Application: Apply effects based on whether target is BUSINESS (strike)
       or territory (protest). Account for George Floyd backfire dynamics.

    Args:
        action: The submitted MOBILIZE action parameters (dict).
                Expected keys: 'org_id', 'target_id', 'params' -> 'sl_committed'
        graph: The active NetworkX Graph (DiGraph) representing the simulation state.
        hypergraph: Additional relational topologies (e.g., xgi.Hypergraph).
        defines: Configuration settings (MobilizeDefines).

    Returns:
        dict: VerbResult indicating success/failure and associated SimulationEvents.
    """
    if not isinstance(action, dict):
        # Fallback if action is some object instead of a dict
        org_id = getattr(action, "org_id", None)
        target_id = getattr(action, "target_id", None)
        params = getattr(action, "params", {})
    else:
        org_id = action.get("org_id")
        target_id = action.get("target_id")
        params = action.get("params", {})

    if not org_id or not target_id:
        return {"success": False, "reason": "Missing org_id or target_id"}

    sl_invested = (
        params.get("sl_committed", 0.0)
        if isinstance(params, dict)
        else getattr(params, "sl_committed", 0.0)
    )

    if org_id not in graph.nodes or target_id not in graph.nodes:
        return {"success": False, "reason": "Org or target node not found in graph"}

    org_node = graph.nodes[org_id]
    target_node = graph.nodes[target_id]

    current_cl = org_node.get("consciousness", 0.0)
    if current_cl < defines.mobilize_cl_cost:
        return {"success": False, "reason": "Insufficient CL to mobilize"}

    # 1. Solidarity Multiplication
    solidarity_edges = [
        edge
        for edge in graph.in_edges(org_id, data=True)
        if edge[2].get("edge_type", "").upper() == "SOLIDARITY"
    ]

    edge_multipliers = [1.0 + defines.solidarity_amplification_per_edge] * len(solidarity_edges)

    # For future extension: check hypergraph for shared class-struggle events
    hyper_multiplier = 1.0
    if hypergraph and hasattr(hypergraph, "nodes") and target_id in hypergraph.nodes and any(org_id in edge for edge in hypergraph.edges(target_id)):
        hyper_multiplier = 1.5

    total_multiplier = reduce(mul, edge_multipliers, 1.0) * hyper_multiplier

    # 2. Turnout Calculation
    base_turnout = sl_invested * defines.turnout_per_sl
    final_turnout = base_turnout * total_multiplier

    # 3. Apply Effects based on Target Type
    events = []
    heat_generated = final_turnout * defines.heat_generation_per_demonstrator

    # Check for backfire
    if final_turnout > defines.max_demonstrators_before_backfire:
        heat_generated *= defines.backfire_heat_multiplier

        # George Floyd Dynamic: Over-repression sparks reverse agitation
        new_agitation = target_node.get("agitation", 0.0) + defines.backfire_agitation_gain
        graph.nodes[target_id]["agitation"] = new_agitation

        events.append(
            {
                "type": "MOBILIZATION_BACKFIRE",
                "target": target_id,
                "heat_generated": heat_generated,
                "agitation_sparked": defines.backfire_agitation_gain,
            }
        )
    else:
        # Standard success
        if (
            target_node.get("type", "").upper() == "BUSINESS"
            or target_node.get("org_type", "").upper() == "BUSINESS"
        ):
            # Strike effect: Disrupt value extraction
            value_flow = target_node.get("extraction_flow", 0.0)
            disrupted = value_flow * defines.strike_value_disruption_factor
            graph.nodes[target_id]["extraction_flow"] = max(0.0, value_flow - disrupted)

            events.append(
                {"type": "MOBILIZATION_STRIKE", "target": target_id, "value_disrupted": disrupted}
            )
        else:
            # Protest effect: Route practice into agitation
            new_agitation = target_node.get("agitation", 0.0) + defines.base_agitation_gain
            graph.nodes[target_id]["agitation"] = new_agitation

            events.append(
                {
                    "type": "MOBILIZATION_PROTEST",
                    "target": target_id,
                    "agitation_added": defines.base_agitation_gain,
                }
            )

    # Apply Heat and CL Cost
    new_heat = target_node.get("heat", 0.0) + heat_generated
    graph.nodes[target_id]["heat"] = new_heat
    graph.nodes[org_id]["consciousness"] = current_cl - defines.mobilize_cl_cost

    return {"success": True, "events": events}
