"""Ideology systems for the Babylon simulation - The Superstructure."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


class ConsciousnessSystem:
    """Phase 2: Consciousness Drift based on material conditions."""

    name = "Consciousness Drift"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        _context: dict[str, Any],
    ) -> None:
        """Apply consciousness drift to all entities."""
        # Get formula from registry
        calculate_consciousness_drift = services.formulas.get("consciousness_drift")
        sensitivity_k = services.config.consciousness_sensitivity
        decay_lambda = services.config.consciousness_decay_lambda

        for node_id in graph.nodes():
            # Calculate value_produced (sum of outgoing exploitation)
            value_produced = 0.0
            for _, _, data in graph.out_edges(node_id, data=True):
                edge_type = data.get("edge_type")
                if isinstance(edge_type, str):
                    edge_type = EdgeType(edge_type)
                if edge_type == EdgeType.EXPLOITATION:
                    value_produced += data.get("value_flow", 0.0)

            if value_produced <= 0:
                continue

            node_data = graph.nodes[node_id]
            current_ideology = node_data.get("ideology", 0.0)
            current_consciousness = (1.0 - current_ideology) / 2.0

            # W/V ratio calculation (W=0 in pure extraction)
            core_wages = 0.0

            drift = calculate_consciousness_drift(
                core_wages=core_wages,
                value_produced=value_produced,
                current_consciousness=current_consciousness,
                sensitivity_k=sensitivity_k,
                decay_lambda=decay_lambda,
            )

            new_consciousness = max(0.0, min(1.0, current_consciousness + drift))
            new_ideology = max(-1.0, min(1.0, 1.0 - 2.0 * new_consciousness))

            graph.nodes[node_id]["ideology"] = new_ideology
