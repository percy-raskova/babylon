"""Ideology systems for the Babylon simulation - The Superstructure.

Sprint 3.4.2b: Extended with Fascist Bifurcation mechanic.
When wages FALL, crisis creates "agitation energy" that channels into:
- Revolution (if solidarity_pressure > 0)
- Fascism (if solidarity_pressure = 0) via loss aversion
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

# Context key for storing previous wages between ticks
PREVIOUS_WAGES_KEY = "previous_wages"


class ConsciousnessSystem:
    """Phase 2: Consciousness Drift based on material conditions.

    Extended with Fascist Bifurcation mechanic (Sprint 3.4.2b):
    - Reads incoming SOLIDARITY edges to calculate solidarity_pressure
    - Tracks wage changes between ticks to detect crisis conditions
    - Passes solidarity_pressure and wage_change to consciousness drift formula
    """

    name = "Consciousness Drift"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply consciousness drift to all entities with bifurcation logic."""
        # Get formula from registry
        calculate_consciousness_drift = services.formulas.get("consciousness_drift")
        sensitivity_k = services.config.consciousness_sensitivity
        decay_lambda = services.config.consciousness_decay_lambda

        # Initialize or retrieve previous wages tracking from context
        if PREVIOUS_WAGES_KEY not in context:
            context[PREVIOUS_WAGES_KEY] = {}
        previous_wages: dict[str, float] = context[PREVIOUS_WAGES_KEY]

        # Track current wages for next tick comparison
        current_wages: dict[str, float] = {}

        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]

            # Calculate value_produced (sum of outgoing EXPLOITATION edges)
            value_produced = 0.0
            for _, _, data in graph.out_edges(node_id, data=True):
                edge_type = data.get("edge_type")
                if isinstance(edge_type, str):
                    edge_type = EdgeType(edge_type)
                if edge_type == EdgeType.EXPLOITATION:
                    value_produced += data.get("value_flow", 0.0)

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
            for source_id, _, data in graph.in_edges(node_id, data=True):
                edge_type = data.get("edge_type")
                if isinstance(edge_type, str):
                    edge_type = EdgeType(edge_type)
                if edge_type == EdgeType.SOLIDARITY:
                    # Get solidarity_strength from edge (key for Fascist Bifurcation)
                    strength = data.get("solidarity_strength", 0.0)
                    if strength > 0:
                        # Only count if source has revolutionary consciousness
                        source_ideology = graph.nodes[source_id].get("ideology", 0.0)
                        source_consciousness = (1.0 - source_ideology) / 2.0
                        activation_threshold = getattr(
                            services.config, "solidarity_activation_threshold", 0.3
                        )
                        if source_consciousness > activation_threshold:
                            solidarity_pressure += strength

            # Skip nodes with no value produced (nothing to be conscious about)
            # But for bifurcation test, we need to process all workers
            # So we set a minimum value_produced if wages exist
            if value_produced <= 0:
                if core_wages > 0 or wage_change != 0:
                    # Labor aristocrat receiving wages without direct exploitation
                    # Use wealth as proxy for value (they produce SOMETHING)
                    value_produced = max(
                        node_data.get("wealth", 1.0),
                        core_wages * 0.5,  # Assume W > V (labor aristocrat)
                        1.0,  # Minimum to avoid division by zero
                    )
                else:
                    continue

            current_ideology = node_data.get("ideology", 0.0)
            current_consciousness = (1.0 - current_ideology) / 2.0

            # Apply consciousness drift with bifurcation parameters
            drift = calculate_consciousness_drift(
                core_wages=core_wages,
                value_produced=value_produced,
                current_consciousness=current_consciousness,
                sensitivity_k=sensitivity_k,
                decay_lambda=decay_lambda,
                solidarity_pressure=solidarity_pressure,
                wage_change=wage_change,
            )

            new_consciousness = max(0.0, min(1.0, current_consciousness + drift))
            new_ideology = max(-1.0, min(1.0, 1.0 - 2.0 * new_consciousness))

            graph.nodes[node_id]["ideology"] = new_ideology

        # Update previous wages for next tick
        context[PREVIOUS_WAGES_KEY] = current_wages
