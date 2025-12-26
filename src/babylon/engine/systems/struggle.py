"""Struggle system for the Babylon simulation - The Agency Layer.

Implements the "George Floyd Dynamic": State Violence (The Spark) +
Accumulated Agitation (The Fuel) = Insurrection (The Explosion).

This system solves the "Spectator Problem" where entities suffer but don't react.
It gives political agency to oppressed classes by modeling:

1. The Spark: Police brutality (EXCESSIVE_FORCE) is a stochastic function of Repression
2. The Combustion: A spark becomes an UPRISING if population is agitated and hopeless
3. The Result: Uprisings destroy wealth but permanently increase solidarity infrastructure

Key Insight: The explosion is what builds the solidarity bridges that enable
consciousness transmission in subsequent ticks. Revolution is built through
shared struggle, not spontaneous awakening.

Target Social Roles:
- PERIPHERY_PROLETARIAT: Exploited workers in the global periphery
- LUMPENPROLETARIAT: Outside formal economy, precarious existence

These classes face the highest repression and have the most agency in
creating revolutionary conditions through collective action.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EdgeType, EventType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

# Social roles that can participate in struggle/uprising
_STRUGGLING_ROLES: frozenset[SocialRole] = frozenset(
    {
        SocialRole.PERIPHERY_PROLETARIAT,
        SocialRole.LUMPENPROLETARIAT,
    }
)


def _get_agitation_from_node(node_data: dict[str, Any]) -> float:
    """Extract agitation value from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Agitation value in [0, inf), defaults to 0.0
    """
    ideology = node_data.get("ideology")

    if ideology is None:
        return 0.0

    if isinstance(ideology, dict):
        return float(ideology.get("agitation", 0.0))

    return 0.0


def _get_class_consciousness_from_node(node_data: dict[str, Any]) -> float:
    """Extract class_consciousness value from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Class consciousness value in [0, 1], defaults to 0.0
    """
    ideology = node_data.get("ideology")

    if ideology is None:
        return 0.0

    if isinstance(ideology, dict):
        return float(ideology.get("class_consciousness", 0.0))

    return 0.0


def _update_class_consciousness(
    node_data: dict[str, Any],
    delta: float,
) -> dict[str, float]:
    """Update class_consciousness by delta, clamping to [0, 1].

    Args:
        node_data: Current graph node data
        delta: Amount to add to class consciousness

    Returns:
        Updated IdeologicalProfile as dict
    """
    ideology = node_data.get("ideology")

    if isinstance(ideology, dict):
        current = ideology.get("class_consciousness", 0.0)
        new_value = max(0.0, min(1.0, current + delta))
        return {
            "class_consciousness": new_value,
            "national_identity": ideology.get("national_identity", 0.5),
            "agitation": ideology.get("agitation", 0.0),
        }

    # Create new profile with updated consciousness
    return {
        "class_consciousness": max(0.0, min(1.0, delta)),
        "national_identity": 0.5,
        "agitation": 0.0,
    }


class StruggleSystem:
    """Agency Layer - The Struggle System ("George Floyd Dynamic").

    This system runs AFTER SurvivalSystem (needs P values) and BEFORE
    ContradictionSystem. It gives agency to oppressed classes through
    the Stochastic Riot mechanic:

    1. Calculate EXCESSIVE_FORCE probability: ``spark_prob = repression * spark_scale``
    2. Roll for spark occurrence
    3. Check uprising condition: ``(Spark OR P(S|R) > P(S|A)) AND agitation > threshold``
    4. Execute uprising:

       - Economic damage: ``wealth *= (1 - destruction_rate)``
       - Solidarity gain: Increase solidarity_strength on incoming SOLIDARITY edges
       - Class consciousness gain: All nodes in uprising gain consciousness

    5. Emit events for narrative layer

    The solidarity built in Tick N enables SolidaritySystem transmission in Tick N+1.
    """

    name = "Struggle"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply struggle dynamics to all eligible entities.

        Processes PERIPHERY_PROLETARIAT and LUMPENPROLETARIAT nodes,
        checking for spark events and uprising conditions.
        """
        # Get defines
        spark_scale = services.defines.struggle.spark_probability_scale
        resistance_threshold = services.defines.struggle.resistance_threshold
        wealth_destruction = services.defines.struggle.wealth_destruction_rate
        solidarity_gain = services.defines.struggle.solidarity_gain_per_uprising

        tick = context.get("tick", 0)

        # Track uprisings for potential multi-node coordination
        uprising_nodes: list[str] = []

        for node_id, data in graph.nodes(data=True):
            # Skip non-social-class nodes (territories)
            if data.get("_node_type") == "territory":
                continue

            # Check if this is a struggling class
            role_str = data.get("role", "")
            try:
                role = SocialRole(role_str) if isinstance(role_str, str) else role_str
            except ValueError:
                continue

            if role not in _STRUGGLING_ROLES:
                continue

            # Get relevant attributes
            repression = data.get("repression_faced", services.defines.DEFAULT_REPRESSION_FACED)
            agitation = _get_agitation_from_node(data)
            p_acq = data.get("p_acquiescence", 0.5)
            p_rev = data.get("p_revolution", 0.0)

            # Step 1: Calculate and roll for EXCESSIVE_FORCE spark
            spark_probability = repression * spark_scale
            spark_occurred = random.random() < spark_probability

            if spark_occurred:
                # Emit EXCESSIVE_FORCE event (The Spark)
                services.event_bus.publish(
                    Event(
                        type=EventType.EXCESSIVE_FORCE,
                        tick=tick,
                        payload={
                            "node_id": node_id,
                            "repression": repression,
                            "spark_probability": spark_probability,
                        },
                    )
                )

            # Step 2: Check uprising condition
            # Trigger if: (Spark OR P(S|R) > P(S|A)) AND agitation > resistance_threshold
            revolutionary_pressure = p_rev > p_acq
            uprising_condition = (spark_occurred or revolutionary_pressure) and (
                agitation > resistance_threshold
            )

            if not uprising_condition:
                continue

            # Step 3: Execute Uprising
            uprising_nodes.append(node_id)

            # Economic damage: wealth *= (1 - destruction_rate)
            current_wealth = data.get("wealth", 0.0)
            new_wealth = current_wealth * (1.0 - wealth_destruction)
            graph.nodes[node_id]["wealth"] = new_wealth

            # Solidarity infrastructure gain: increase solidarity_strength on edges
            solidarity_gained = 0.0
            edges_updated = 0

            for source_id, _target_id, edge_data in graph.in_edges(node_id, data=True):
                edge_type = edge_data.get("edge_type")
                if isinstance(edge_type, str):
                    edge_type = EdgeType(edge_type)

                if edge_type == EdgeType.SOLIDARITY:
                    current_strength = edge_data.get("solidarity_strength", 0.0)
                    new_strength = min(1.0, current_strength + solidarity_gain)
                    graph.edges[source_id, node_id]["solidarity_strength"] = new_strength
                    solidarity_gained += new_strength - current_strength
                    edges_updated += 1

            # Class consciousness boost from shared struggle
            consciousness_before = _get_class_consciousness_from_node(data)
            consciousness_boost = solidarity_gain * 0.5  # Half of solidarity gain
            graph.nodes[node_id]["ideology"] = _update_class_consciousness(
                data, consciousness_boost
            )
            consciousness_after = _get_class_consciousness_from_node(graph.nodes[node_id])

            # Emit UPRISING event
            services.event_bus.publish(
                Event(
                    type=EventType.UPRISING,
                    tick=tick,
                    payload={
                        "node_id": node_id,
                        "trigger": "spark" if spark_occurred else "revolutionary_pressure",
                        "agitation": agitation,
                        "repression": repression,
                        "p_acquiescence": p_acq,
                        "p_revolution": p_rev,
                        "wealth_before": current_wealth,
                        "wealth_after": new_wealth,
                        "solidarity_gained": solidarity_gained,
                        "edges_updated": edges_updated,
                        "consciousness_before": consciousness_before,
                        "consciousness_after": consciousness_after,
                    },
                )
            )

            # Emit SOLIDARITY_SPIKE if solidarity was gained
            if solidarity_gained > 0:
                services.event_bus.publish(
                    Event(
                        type=EventType.SOLIDARITY_SPIKE,
                        tick=tick,
                        payload={
                            "node_id": node_id,
                            "solidarity_gained": solidarity_gained,
                            "edges_affected": edges_updated,
                            "triggered_by": "uprising",
                        },
                    )
                )
