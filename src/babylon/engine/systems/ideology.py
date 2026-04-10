"""Ideology systems for the Babylon simulation - The Superstructure.

Sprint 3.4.2b: Extended with Fascist Bifurcation mechanic.
Sprint 3.4.3: George Jackson Refactor - Multi-dimensional consciousness model.

When wages FALL, crisis creates "agitation energy" that channels into:
- Class Consciousness (if solidarity_pressure > 0) - Revolutionary Path
- National Identity (if solidarity_pressure = 0) - Fascist Path via loss aversion
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.formulas.consciousness_routing import (
    compute_agitation_delta,
    route_agitation_to_ternary,
)
from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

# Context keys for storing previous values between ticks
PREVIOUS_WAGES_KEY = "previous_wages"
PREVIOUS_WEALTH_KEY = "previous_wealth"


def _get_ideology_profile_from_node(
    node_data: dict[str, Any],
) -> dict[str, float]:  # pragma: no mutate — graph accessor
    """Extract IdeologicalProfile values from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Dict with class_consciousness, national_identity, agitation keys
    """
    ideology = node_data.get("ideology")  # pragma: no mutate

    if ideology is None:  # pragma: no mutate
        # No ideology data - return defaults
        return {  # pragma: no mutate
            "class_consciousness": 0.0,  # pragma: no mutate
            "national_identity": 0.5,  # pragma: no mutate
            "agitation": 0.0,  # pragma: no mutate
        }  # pragma: no mutate

    if isinstance(ideology, dict):  # pragma: no mutate
        # IdeologicalProfile format
        return {  # pragma: no mutate
            "class_consciousness": ideology.get("class_consciousness", 0.0),  # pragma: no mutate
            "national_identity": ideology.get("national_identity", 0.5),  # pragma: no mutate
            "agitation": ideology.get("agitation", 0.0),  # pragma: no mutate
        }  # pragma: no mutate

    # Unknown format - return defaults
    return {  # pragma: no mutate
        "class_consciousness": 0.0,  # pragma: no mutate
        "national_identity": 0.5,  # pragma: no mutate
        "agitation": 0.0,  # pragma: no mutate
    }  # pragma: no mutate


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
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply consciousness drift to all entities with bifurcation routing."""
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

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

        # Initialize or retrieve previous wealth tracking from persistent storage
        # Periphery Dynamics Extension: Track wealth extraction between ticks
        if PREVIOUS_WEALTH_KEY not in persistent:
            persistent[PREVIOUS_WEALTH_KEY] = {}
        previous_wealth: dict[str, float] = persistent[PREVIOUS_WEALTH_KEY]

        # Track current wages and wealth for next tick comparison
        current_wages: dict[str, float] = {}
        current_wealth_map: dict[str, float] = {}

        for node in graph.query_nodes(node_type="social_class"):
            attrs = node.attributes

            # Skip inactive (dead) entities - dead can't develop consciousness
            if not attrs.get("active", True):
                continue

            # Calculate wages received (sum of incoming WAGES edges)
            core_wages = 0.0
            for edge in graph.query_edges(edge_type=EdgeType.WAGES):
                if edge.target_id == node.id:
                    core_wages += edge.attributes.get("value_flow", 0.0)

            # Store current wages for next tick
            current_wages[node.id] = core_wages

            # Calculate wage_change for bifurcation mechanic
            prev_wage = previous_wages.get(node.id, core_wages)
            wage_change = core_wages - prev_wage

            # Periphery Dynamics Extension: Calculate wealth_change for extraction detection
            # Periphery workers have wealth extracted via EXPLOITATION edges, not wage cuts
            current_wealth = float(attrs.get("wealth", 0.0))
            # Default to current wealth if first tick (no previous baseline)
            prev_wealth = previous_wealth.get(node.id, current_wealth)
            wealth_change = current_wealth - prev_wealth
            current_wealth_map[node.id] = current_wealth

            # Calculate solidarity_pressure from incoming SOLIDARITY edges
            # Sum of solidarity_strength from all incoming SOLIDARITY edges
            solidarity_pressure = 0.0
            activation_threshold = services.defines.solidarity.activation_threshold

            for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
                if edge.target_id == node.id:
                    # Get solidarity_strength from edge
                    strength = edge.attributes.get("solidarity_strength", 0.0)
                    if strength > 0:
                        # Only count if source has revolutionary consciousness
                        src_node = graph.get_node(edge.source_id)
                        src_attrs = src_node.attributes if src_node else {}
                        source_profile = _get_ideology_profile_from_node(src_attrs)
                        source_consciousness = source_profile["class_consciousness"]
                        if source_consciousness > activation_threshold:
                            solidarity_pressure += strength

            # Get current ideological profile
            current_profile = _get_ideology_profile_from_node(attrs)

            # Apply consciousness routing (Spec 043 - Value Transparency)
            # Convert wage/wealth changes to agitation via tensor pipeline
            agitation_increment = compute_agitation_delta(
                exploitation_rate_delta=abs(wage_change) if wage_change < 0 else 0.0,
                imperial_rent_delta=wealth_change,  # Wealth decline ~ rent decline
                visibility_delta=0.0,  # g₃₃ changes handled in community system
            )
            new_agitation = current_profile["agitation"] + agitation_increment

            # Route agitation through solidarity → class/nation split
            delta_r, delta_l, _delta_f = route_agitation_to_ternary(
                agitation=new_agitation,
                solidarity_factor=min(1.0, solidarity_pressure),
                education_pressure=0.0,  # Education pressure handled in community system
            )
            new_class = min(1.0, current_profile["class_consciousness"] + delta_r)
            new_nation = min(1.0, current_profile["national_identity"] + abs(delta_l))
            # Decay agitation after routing
            decay_rate = services.defines.consciousness.agitation_decay_rate
            new_agitation = max(0.0, new_agitation * (1.0 - decay_rate))

            # Update the ideology in the graph as a dict (IdeologicalProfile format)
            graph.update_node(
                node.id,
                ideology={
                    "class_consciousness": new_class,
                    "national_identity": new_nation,
                    "agitation": new_agitation,
                },
            )

        # Update previous wages and wealth for next tick in persistent storage
        persistent[PREVIOUS_WAGES_KEY] = current_wages
        persistent[PREVIOUS_WEALTH_KEY] = current_wealth_map
