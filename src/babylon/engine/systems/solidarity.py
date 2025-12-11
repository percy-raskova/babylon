"""Solidarity system for the Babylon simulation - Proletarian Internationalism.

Sprint 3.4.2: The Counterforce to Imperial Rent Bribery.
Sprint 3.4.3: Updated for IdeologicalProfile (multi-dimensional consciousness).

When periphery workers are in revolutionary struggle (consciousness >= threshold),
their consciousness transmits through SOLIDARITY edges to core workers, awakening
class consciousness that counters the super-wage bribery.

Key Design Decision: solidarity_strength is a PERSISTENT ATTRIBUTE ON THE EDGE,
NOT auto-calculated from source organization. This enables the Fascist Bifurcation
scenario where periphery revolts but core workers remain passive due to lack of
built solidarity infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EdgeType, EventType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


def _get_class_consciousness_from_node(node_data: dict[str, Any]) -> float:
    """Extract class_consciousness from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Class consciousness value in [0, 1]
    """
    ideology = node_data.get("ideology")

    if ideology is None:
        return 0.0

    if isinstance(ideology, dict):
        # IdeologicalProfile format
        return float(ideology.get("class_consciousness", 0.0))

    return 0.0


def _update_ideology_class_consciousness(
    node_data: dict[str, Any],
    new_class_consciousness: float,
) -> dict[str, float]:
    """Update class_consciousness in ideology profile.

    Returns a new IdeologicalProfile dict with updated class_consciousness.

    Args:
        node_data: Current graph node data
        new_class_consciousness: New class consciousness value

    Returns:
        Updated IdeologicalProfile as dict
    """
    ideology = node_data.get("ideology")

    if isinstance(ideology, dict):
        # Already IdeologicalProfile format - update class_consciousness
        return {
            "class_consciousness": new_class_consciousness,
            "national_identity": ideology.get("national_identity", 0.5),
            "agitation": ideology.get("agitation", 0.0),
        }

    # Legacy or missing - create new profile
    return {
        "class_consciousness": new_class_consciousness,
        "national_identity": 0.5,
        "agitation": 0.0,
    }


class SolidaritySystem:
    """Proletarian Internationalism - Consciousness Transmission System.

    Implements consciousness transmission via SOLIDARITY edges:
    - Unidirectional flow (Periphery -> Core)
    - solidarity_strength stored on edge (key for Fascist Bifurcation)
    - Emits CONSCIOUSNESS_TRANSMISSION and MASS_AWAKENING events

    Sprint 3.4.3: Updated to work with IdeologicalProfile, affecting
    only the class_consciousness dimension.
    """

    name = "Solidarity"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply solidarity transmission to all SOLIDARITY edges.

        For each SOLIDARITY edge:
        1. Check if source consciousness > activation_threshold
        2. Check if solidarity_strength > 0
        3. Calculate transmission delta
        4. Apply delta to target class_consciousness
        5. Emit events for narrative layer
        """
        # Get formula from registry
        calculate_solidarity_transmission = services.formulas.get("solidarity_transmission")

        # Get defines thresholds
        activation_threshold = services.defines.solidarity.activation_threshold
        mass_awakening_threshold = services.defines.solidarity.mass_awakening_threshold

        # Process all SOLIDARITY edges
        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.SOLIDARITY:
                continue

            # Get solidarity_strength from edge (NOT auto-calculated!)
            solidarity_strength = data.get("solidarity_strength", 0.0)

            if solidarity_strength <= 0:
                continue  # Fascist Bifurcation: no infrastructure, no transmission

            # Get source consciousness (from IdeologicalProfile)
            source_consciousness = _get_class_consciousness_from_node(graph.nodes[source_id])

            # Check activation threshold
            if source_consciousness <= activation_threshold:
                continue  # Source not in active struggle

            # Get target consciousness
            target_consciousness = _get_class_consciousness_from_node(graph.nodes[target_id])
            old_consciousness = target_consciousness

            # Calculate transmission delta
            delta = calculate_solidarity_transmission(
                source_consciousness=source_consciousness,
                target_consciousness=target_consciousness,
                solidarity_strength=solidarity_strength,
                activation_threshold=activation_threshold,
            )

            # Skip negligible transmissions
            if abs(delta) < services.defines.NEGLIGIBLE_TRANSMISSION:
                continue

            # Apply delta to target class_consciousness
            new_consciousness = target_consciousness + delta
            new_consciousness = max(0.0, min(1.0, new_consciousness))

            # Update ideology profile with new class_consciousness
            graph.nodes[target_id]["ideology"] = _update_ideology_class_consciousness(
                graph.nodes[target_id],
                new_consciousness,
            )

            # Emit CONSCIOUSNESS_TRANSMISSION event
            tick = context.get("tick", 0)
            services.event_bus.publish(
                Event(
                    type=EventType.CONSCIOUSNESS_TRANSMISSION,
                    tick=tick,
                    payload={
                        "source_id": source_id,
                        "target_id": target_id,
                        "delta": delta,
                        "solidarity_strength": solidarity_strength,
                        "source_consciousness": source_consciousness,
                        "old_target_consciousness": old_consciousness,
                        "new_target_consciousness": new_consciousness,
                    },
                )
            )

            # Check for MASS_AWAKENING event
            if old_consciousness < mass_awakening_threshold <= new_consciousness:
                services.event_bus.publish(
                    Event(
                        type=EventType.MASS_AWAKENING,
                        tick=tick,
                        payload={
                            "target_id": target_id,
                            "old_consciousness": old_consciousness,
                            "new_consciousness": new_consciousness,
                            "triggering_source": source_id,
                        },
                    )
                )
