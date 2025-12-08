"""Survival systems for the Babylon simulation - The Calculus of Living."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


class SurvivalSystem:
    """Phase 3: Survival Calculus (P(S|A) vs P(S|R))."""

    name = "Survival Calculus"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        _context: dict[str, Any],
    ) -> None:
        """Update P(S|A) and P(S|R) for all entities."""
        # Get formulas from registry
        calculate_acquiescence_probability = services.formulas.get("acquiescence_probability")
        calculate_revolution_probability = services.formulas.get("revolution_probability")
        survival_steepness = services.config.survival_steepness
        default_subsistence = services.config.subsistence_threshold

        for node_id, data in graph.nodes(data=True):
            wealth = data.get("wealth", 0.0)
            organization = data.get("organization", 0.1)
            repression = data.get("repression_faced", 0.5)
            subsistence = data.get("subsistence_threshold", default_subsistence)

            p_acq = calculate_acquiescence_probability(
                wealth=wealth,
                subsistence_threshold=subsistence,
                steepness_k=survival_steepness,
            )

            p_rev = calculate_revolution_probability(
                cohesion=organization,
                repression=repression,
            )

            graph.nodes[node_id]["p_acquiescence"] = p_acq
            graph.nodes[node_id]["p_revolution"] = p_rev
