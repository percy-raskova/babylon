"""Economic systems for the Babylon simulation - The Base.

Sprint 3.4.1: Imperial Circuit - 4-node value flow model.

The Imperial Circuit has four phases:
1. EXPLOITATION: P_w -> P_c (imperial rent extraction)
2. TRIBUTE: P_c -> C_b (comprador keeps 15% cut)
3. WAGES: C_b -> C_w (20% as super-wages to labor aristocracy)
4. CLIENT_STATE: C_b -> P_c (subsidy when unstable, converts to repression)
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


class ImperialRentSystem:
    """Imperial Circuit Economic System - 4-phase value extraction.

    Implements the MLM-TW model of value flow:
    - Phase 1: Extraction (P_w -> P_c via EXPLOITATION)
    - Phase 2: Tribute (P_c -> C_b via TRIBUTE, minus comprador cut)
    - Phase 3: Wages (C_b -> C_w via WAGES, super-wages to labor aristocracy)
    - Phase 4: Subsidy (C_b -> P_c via CLIENT_STATE, stabilization subsidy)
    """

    name = "Imperial Rent"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply the 4-phase Imperial Circuit to the graph.

        Phases execute in sequence, as each depends on the previous:
        1. Extraction must happen before tribute (P_c needs wealth to send)
        2. Tribute must happen before wages (C_b needs wealth to pay)
        3. Wages must happen before subsidy (determines C_b available funds)
        4. Subsidy is the "Iron Lung" that stabilizes client states
        """
        self._process_extraction_phase(graph, services, context)
        self._process_tribute_phase(graph, services, context)
        self._process_wages_phase(graph, services, context)
        self._process_subsidy_phase(graph, services, context)

    def _process_extraction_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Phase 1: Imperial rent extraction via EXPLOITATION edges."""
        calculate_imperial_rent = services.formulas.get("imperial_rent")
        extraction_efficiency = services.config.extraction_efficiency

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.EXPLOITATION:
                continue

            # Get source (worker) data
            worker_data = graph.nodes[source_id]
            worker_wealth = worker_data.get("wealth", 0.0)

            # Extract class consciousness (handles both IdeologicalProfile and legacy)
            consciousness = _get_class_consciousness_from_node(worker_data)

            # Calculate imperial rent
            rent = calculate_imperial_rent(
                alpha=extraction_efficiency,
                periphery_wages=worker_wealth,
                periphery_consciousness=consciousness,
            )

            # Cap rent at available wealth
            rent = min(rent, worker_wealth)

            # Transfer wealth
            graph.nodes[source_id]["wealth"] = max(0.0, worker_wealth - rent)
            graph.nodes[target_id]["wealth"] = graph.nodes[target_id].get("wealth", 0.0) + rent

            # Record value flow
            graph.edges[source_id, target_id]["value_flow"] = rent

            # Emit event for AI narrative layer (ignore floating point noise)
            if rent > 0.01:
                tick = context.get("tick", 0)
                services.event_bus.publish(
                    Event(
                        type=EventType.SURPLUS_EXTRACTION,
                        tick=tick,
                        payload={
                            "source_id": source_id,
                            "target_id": target_id,
                            "amount": rent,
                            "mechanism": "imperial_rent",
                        },
                    )
                )

    def _process_tribute_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],  # noqa: ARG002 - API consistency with other phases
    ) -> None:
        """Phase 2: Comprador tribute via TRIBUTE edges.

        The comprador class keeps a cut (default 15%) and sends the rest
        as tribute to the core bourgeoisie.
        """
        _ = context  # Unused but kept for API consistency
        comprador_cut = services.config.comprador_cut

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.TRIBUTE:
                continue

            # Get comprador wealth
            comprador_wealth = graph.nodes[source_id].get("wealth", 0.0)

            if comprador_wealth <= 0:
                continue

            # Comprador keeps their cut
            cut_amount = comprador_wealth * comprador_cut
            tribute_amount = comprador_wealth - cut_amount

            # Transfer tribute (comprador keeps only the cut)
            graph.nodes[source_id]["wealth"] = cut_amount
            graph.nodes[target_id]["wealth"] = (
                graph.nodes[target_id].get("wealth", 0.0) + tribute_amount
            )

            # Record value flow
            graph.edges[source_id, target_id]["value_flow"] = tribute_amount

    def _process_wages_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],  # noqa: ARG002 - API consistency with other phases
    ) -> None:
        """Phase 3: Super-wages via WAGES edges.

        The core bourgeoisie pays a fraction of their wealth as super-wages
        to the labor aristocracy (core workers). This is the bribe that
        prevents revolution in the core.
        """
        _ = context  # Unused but kept for API consistency
        super_wage_rate = services.config.super_wage_rate

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.WAGES:
                continue

            # Get bourgeoisie wealth
            bourgeoisie_wealth = graph.nodes[source_id].get("wealth", 0.0)

            if bourgeoisie_wealth <= 0:
                continue

            # Calculate super-wages
            wages = bourgeoisie_wealth * super_wage_rate

            # Transfer wages
            graph.nodes[source_id]["wealth"] = bourgeoisie_wealth - wages
            graph.nodes[target_id]["wealth"] = graph.nodes[target_id].get("wealth", 0.0) + wages

            # Record value flow
            graph.edges[source_id, target_id]["value_flow"] = wages

    def _process_subsidy_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Phase 4: Imperial subsidy via CLIENT_STATE edges (The Iron Lung).

        When a client state becomes unstable (P(S|R) >= threshold * P(S|A)),
        the core provides a subsidy that converts to repression capacity.

        This is the mechanism by which imperial wealth is used to suppress
        revolution in the periphery. Wealth is NOT conserved - it converts
        to suppression (military aid, police training, etc.).
        """
        subsidy_trigger_threshold = services.config.subsidy_trigger_threshold
        subsidy_conversion_rate = services.config.subsidy_conversion_rate

        # Get survival probability formulas
        calculate_acquiescence = services.formulas.get("acquiescence_probability")
        calculate_revolution = services.formulas.get("revolution_probability")

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.CLIENT_STATE:
                continue

            # Get target (client state) data
            target_data = graph.nodes[target_id]
            target_wealth = target_data.get("wealth", 0.0)
            target_organization = target_data.get("organization", 0.1)
            target_repression = target_data.get("repression_faced", 0.5)
            target_subsistence = target_data.get("subsistence_threshold", 0.3)

            # Get source (core bourgeoisie) wealth
            source_wealth = graph.nodes[source_id].get("wealth", 0.0)

            # Get subsidy cap from edge data
            subsidy_cap = data.get("subsidy_cap", 0.0)

            # Calculate survival probabilities for target
            p_acquiescence = calculate_acquiescence(
                wealth=target_wealth,
                subsistence_threshold=target_subsistence,
                steepness_k=services.config.survival_steepness,
            )
            p_revolution = calculate_revolution(
                cohesion=target_organization,
                repression=target_repression,
            )

            # Check if subsidy is triggered (client state becoming unstable)
            # Subsidy triggers when P(S|R) >= threshold * P(S|A)
            # This means revolution is becoming a rational survival strategy
            if p_acquiescence > 0:
                stability_ratio = p_revolution / p_acquiescence
            else:
                # If P(S|A) = 0, the client state is in crisis
                stability_ratio = 1.0 if p_revolution > 0 else 0.0

            if stability_ratio < subsidy_trigger_threshold:
                # Client state is stable, no subsidy needed
                continue

            # Calculate subsidy amount
            # Limited by: subsidy_cap, source wealth, and conversion rate
            max_subsidy = min(subsidy_cap, source_wealth * subsidy_conversion_rate)

            if max_subsidy <= 0.01:
                # Negligible subsidy
                continue

            # Apply subsidy: wealth converts to repression capacity
            # Source loses wealth
            graph.nodes[source_id]["wealth"] = source_wealth - max_subsidy

            # Target gains repression capacity (NOT wealth)
            # Wealth converts at the subsidy_conversion_rate
            repression_boost = max_subsidy * subsidy_conversion_rate
            new_repression = min(1.0, target_repression + repression_boost)
            graph.nodes[target_id]["repression_faced"] = new_repression

            # Record subsidy in edge
            graph.edges[source_id, target_id]["value_flow"] = max_subsidy

            # Emit event for AI narrative layer
            tick = context.get("tick", 0)
            services.event_bus.publish(
                Event(
                    type=EventType.IMPERIAL_SUBSIDY,
                    tick=tick,
                    payload={
                        "source_id": source_id,
                        "target_id": target_id,
                        "amount": max_subsidy,
                        "repression_boost": repression_boost,
                        "mechanism": "client_state_subsidy",
                        "stability_ratio": stability_ratio,
                    },
                )
            )
