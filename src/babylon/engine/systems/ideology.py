"""Ideology systems for the Babylon simulation - The Superstructure.

Sprint 3.4.2b: Extended with Fascist Bifurcation mechanic.
Sprint 3.4.3: George Jackson Refactor - Multi-dimensional consciousness model.

When wages FALL, crisis creates "agitation energy" that channels into:
- Class Consciousness (if solidarity_pressure > 0) - Revolutionary Path
- National Identity (if solidarity_pressure = 0) - Fascist Path via loss aversion
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.models.enums import EdgeType
from babylon.systems.formulas import calculate_ideological_routing

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

# Context key for storing previous wages between ticks
PREVIOUS_WAGES_KEY = "previous_wages"


def _get_ideology_profile_from_node(node_data: dict[str, Any]) -> dict[str, float]:
    """Extract IdeologicalProfile values from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Dict with class_consciousness, national_identity, agitation keys
    """
    ideology = node_data.get("ideology")

    if ideology is None:
        # No ideology data - return defaults
        return {
            "class_consciousness": 0.0,
            "national_identity": 0.5,
            "agitation": 0.0,
        }

    if isinstance(ideology, dict):
        # IdeologicalProfile format
        return {
            "class_consciousness": ideology.get("class_consciousness", 0.0),
            "national_identity": ideology.get("national_identity", 0.5),
            "agitation": ideology.get("agitation", 0.0),
        }

    # Unknown format - return defaults
    return {
        "class_consciousness": 0.0,
        "national_identity": 0.5,
        "agitation": 0.0,
    }


class ConsciousnessSystem:
    """Phase 2: Consciousness Drift based on material conditions.

    Sprint 3.4.3 (George Jackson Refactor): Uses multi-dimensional IdeologicalProfile.
    - class_consciousness: Relationship to Capital [0=False, 1=Revolutionary]
    - national_identity: Relationship to State/Tribe [0=Internationalist, 1=Fascist]
    - agitation: Raw political energy from crisis (falling wages)

    Extended with Fascist Bifurcation mechanic:
    - Reads incoming SOLIDARITY edges to calculate solidarity_pressure
    - Tracks wage changes between ticks to detect crisis conditions
    - Routes agitation to either class_consciousness or national_identity
    """

    name = "Consciousness Drift"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply consciousness drift to all entities with bifurcation routing."""
        # Handle both TickContext (with persistent_data) and raw dict
        # TickContext stores persistent data in .persistent_data attribute
        # Raw dict stores persistent data directly
        if hasattr(context, "persistent_data"):
            persistent: dict[str, Any] = context.persistent_data
        else:
            persistent = context

        # Initialize or retrieve previous wages tracking from persistent storage
        if PREVIOUS_WAGES_KEY not in persistent:
            persistent[PREVIOUS_WAGES_KEY] = {}
        previous_wages: dict[str, float] = persistent[PREVIOUS_WAGES_KEY]

        # Track current wages for next tick comparison
        current_wages: dict[str, float] = {}

        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]

            # Skip non-social-class nodes (e.g., territories)
            if node_data.get("_node_type") == "territory":
                continue

            # Calculate wages received (sum of incoming WAGES edges)
            core_wages = 0.0
            for _, _, data in graph.in_edges(node_id, data=True):
                edge_type = data.get("edge_type")
                if isinstance(edge_type, str):
                    edge_type = EdgeType(edge_type)
                if edge_type == EdgeType.WAGES:
                    core_wages += data.get("value_flow", 0.0)

            # Store current wages for next tick
            current_wages[node_id] = core_wages

            # Calculate wage_change for bifurcation mechanic
            prev_wage = previous_wages.get(node_id, core_wages)
            wage_change = core_wages - prev_wage

            # Calculate solidarity_pressure from incoming SOLIDARITY edges
            # Sum of solidarity_strength from all incoming SOLIDARITY edges
            solidarity_pressure = 0.0
            activation_threshold = getattr(services.config, "solidarity_activation_threshold", 0.3)

            for source_id, _, data in graph.in_edges(node_id, data=True):
                edge_type = data.get("edge_type")
                if isinstance(edge_type, str):
                    edge_type = EdgeType(edge_type)
                if edge_type == EdgeType.SOLIDARITY:
                    # Get solidarity_strength from edge
                    strength = data.get("solidarity_strength", 0.0)
                    if strength > 0:
                        # Only count if source has revolutionary consciousness
                        source_profile = _get_ideology_profile_from_node(graph.nodes[source_id])
                        source_consciousness = source_profile["class_consciousness"]
                        if source_consciousness > activation_threshold:
                            solidarity_pressure += strength

            # Get current ideological profile
            current_profile = _get_ideology_profile_from_node(node_data)

            # Apply ideological routing formula (Sprint 3.4.3)
            new_class, new_nation, new_agitation = calculate_ideological_routing(
                wage_change=wage_change,
                solidarity_pressure=solidarity_pressure,
                current_class_consciousness=current_profile["class_consciousness"],
                current_national_identity=current_profile["national_identity"],
                current_agitation=current_profile["agitation"],
            )

            # Update the ideology in the graph as a dict (IdeologicalProfile format)
            graph.nodes[node_id]["ideology"] = {
                "class_consciousness": new_class,
                "national_identity": new_nation,
                "agitation": new_agitation,
            }

        # Update previous wages for next tick in persistent storage
        persistent[PREVIOUS_WAGES_KEY] = current_wages
