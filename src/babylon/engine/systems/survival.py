"""Survival systems for the Babylon simulation - The Calculus of Living.

Sprint 3.4.2: Fixed Bug 1 - Organization is now dynamic based on SOLIDARITY edges.
P(S|R) = (base_organization + solidarity_bonus) / repression

The solidarity_bonus is the sum of incoming SOLIDARITY edge weights (solidarity_strength).
This makes organization a function of class solidarity infrastructure, not just a static value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


def _calculate_solidarity_multiplier(
    graph: nx.DiGraph[str],
    node_id: str,
) -> float:
    """Calculate organization multiplier from incoming SOLIDARITY edges.

    Solidarity acts as a MULTIPLIER on base organization, not an additive bonus.
    This ensures P(S|R) = org/repression produces meaningful differentiation:
    - Low solidarity (0.2) = 1.2x multiplier
    - High solidarity (0.8) = 1.8x multiplier

    With base_org=0.1:
    - Low solidarity: effective_org = 0.1 * 1.2 = 0.12
    - High solidarity: effective_org = 0.1 * 1.8 = 0.18

    Args:
        graph: The simulation graph
        node_id: ID of the node to calculate solidarity multiplier for

    Returns:
        Multiplier value >= 1.0 (1.0 + sum of incoming solidarity_strength)
    """
    solidarity_sum = 0.0

    # Sum incoming SOLIDARITY edge weights
    for _source_id, _target_id, data in graph.in_edges(node_id, data=True):
        edge_type = data.get("edge_type")
        if isinstance(edge_type, str):
            edge_type = EdgeType(edge_type)

        if edge_type == EdgeType.SOLIDARITY:
            solidarity_strength = data.get("solidarity_strength", 0.0)
            solidarity_sum += solidarity_strength

    # Return as multiplier: 1.0 = no solidarity, 1.8 = high solidarity
    return 1.0 + solidarity_sum


class SurvivalSystem:
    """Phase 3: Survival Calculus (P(S|A) vs P(S|R)).

    Bug Fix (Sprint 3.4.2): Organization is now DYNAMIC.
    organization = base_organization + solidarity_bonus

    Where solidarity_bonus = sum of incoming SOLIDARITY edge weights.
    This ensures that High Solidarity scenarios produce higher P(S|R).
    """

    name = "Survival Calculus"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        _context: dict[str, Any],
    ) -> None:
        """Update P(S|A) and P(S|R) for all entities.

        Organization is calculated as:
            effective_org = base_org + solidarity_bonus

        Where solidarity_bonus = sum(solidarity_strength for incoming SOLIDARITY edges)
        """
        # Get formulas from registry
        calculate_acquiescence_probability = services.formulas.get("acquiescence_probability")
        calculate_revolution_probability = services.formulas.get("revolution_probability")
        survival_steepness = services.config.survival_steepness
        default_subsistence = services.config.subsistence_threshold

        for node_id, data in graph.nodes(data=True):
            wealth = data.get("wealth", 0.0)
            base_organization = data.get("organization", services.defines.DEFAULT_ORGANIZATION)
            repression = data.get("repression_faced", services.defines.DEFAULT_REPRESSION_FACED)
            subsistence = data.get("subsistence_threshold", default_subsistence)

            # Bug Fix: Calculate solidarity MULTIPLIER from incoming SOLIDARITY edges
            # Multiplicative (not additive) to preserve scale for P(S|R) formula
            solidarity_multiplier = _calculate_solidarity_multiplier(graph, node_id)

            # Effective organization = base * solidarity_multiplier (capped at 1.0)
            # NOTE: We do NOT persist effective_organization back to graph.
            # Base organization is intrinsic; solidarity bonus is situational.
            effective_organization = min(1.0, base_organization * solidarity_multiplier)

            p_acq = calculate_acquiescence_probability(
                wealth=wealth,
                subsistence_threshold=subsistence,
                steepness_k=survival_steepness,
            )

            p_rev = calculate_revolution_probability(
                cohesion=effective_organization,
                repression=repression,
            )

            graph.nodes[node_id]["p_acquiescence"] = p_acq
            graph.nodes[node_id]["p_revolution"] = p_rev
