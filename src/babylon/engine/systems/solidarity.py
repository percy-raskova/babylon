"""Solidarity system for the Babylon simulation - Proletarian Internationalism.

Sprint 3.4.2: The Counterforce to Imperial Rent Bribery.

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


class SolidaritySystem:
    """Proletarian Internationalism - Consciousness Transmission System.

    Implements consciousness transmission via SOLIDARITY edges:
    - Unidirectional flow (Periphery -> Core)
    - solidarity_strength stored on edge (key for Fascist Bifurcation)
    - Emits CONSCIOUSNESS_TRANSMISSION and MASS_AWAKENING events
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
        4. Apply delta to target consciousness
        5. Emit events for narrative layer
        """
        # Get formula from registry
        calculate_solidarity_transmission = services.formulas.get("solidarity_transmission")

        # Get config thresholds
        activation_threshold = services.config.solidarity_activation_threshold
        mass_awakening_threshold = services.config.mass_awakening_threshold

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

            # Get source consciousness (convert from ideology)
            source_ideology = graph.nodes[source_id].get("ideology", 0.0)
            source_consciousness = (1.0 - source_ideology) / 2.0

            # Check activation threshold
            if source_consciousness <= activation_threshold:
                continue  # Source not in active struggle

            # Get target consciousness
            target_ideology = graph.nodes[target_id].get("ideology", 0.0)
            target_consciousness = (1.0 - target_ideology) / 2.0
            old_consciousness = target_consciousness

            # Calculate transmission delta
            delta = calculate_solidarity_transmission(
                source_consciousness=source_consciousness,
                target_consciousness=target_consciousness,
                solidarity_strength=solidarity_strength,
                activation_threshold=activation_threshold,
            )

            # Skip negligible transmissions
            if abs(delta) < 0.01:
                continue

            # Apply delta to target
            new_consciousness = target_consciousness + delta
            new_consciousness = max(0.0, min(1.0, new_consciousness))

            # Convert back to ideology
            new_ideology = 1.0 - 2.0 * new_consciousness
            new_ideology = max(-1.0, min(1.0, new_ideology))

            graph.nodes[target_id]["ideology"] = new_ideology

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
