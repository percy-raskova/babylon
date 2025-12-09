"""Territory systems for the Babylon simulation - Layer 0.

Sprint 3.5.4: The Territorial Substrate.

TerritorySystem manages:
1. Heat dynamics: HIGH_PROFILE gains heat, LOW_PROFILE decays heat
2. Eviction pipeline: triggered when heat >= threshold
3. Heat spillover: via ADJACENCY edges
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.models.enums import EdgeType, OperationalProfile

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


class TerritorySystem:
    """Territory Dynamic System - Layer 0 spatial dynamics.

    Implements the territorial substrate mechanics:
    - Heat dynamics based on operational profile
    - Eviction pipeline when heat exceeds threshold
    - Heat spillover between adjacent territories

    "Legibility over Stealth" - The State knows where you are.
    The game is about staying below the repression threshold.
    """

    name = "Territory"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply territorial dynamics to the graph.

        Phases execute in sequence:
        1. Heat dynamics (profile-based accumulation/decay)
        2. Eviction pipeline (triggered at threshold)
        3. Heat spillover (via adjacency edges)
        """
        _ = context  # Unused but kept for API consistency
        self._process_heat_dynamics(graph, services)
        self._process_eviction_pipeline(graph, services)
        self._process_spillover(graph, services)

    def _process_heat_dynamics(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
    ) -> None:
        """Process heat accumulation/decay based on operational profile.

        HIGH_PROFILE: heat += high_profile_heat_gain
        LOW_PROFILE: heat *= (1 - heat_decay_rate)
        """
        heat_decay_rate = services.config.heat_decay_rate
        high_profile_heat_gain = services.config.high_profile_heat_gain

        for node_id, data in graph.nodes(data=True):
            # Only process territory nodes
            if data.get("_node_type") != "territory":
                continue

            profile = data.get("profile")
            # Convert string to enum if needed
            if isinstance(profile, str):
                profile = OperationalProfile(profile)

            current_heat = data.get("heat", 0.0)

            if profile == OperationalProfile.HIGH_PROFILE:
                # High profile gains heat
                new_heat = current_heat + high_profile_heat_gain
            else:
                # Low profile decays heat
                new_heat = current_heat * (1.0 - heat_decay_rate)

            # Clamp to [0, 1]
            graph.nodes[node_id]["heat"] = max(0.0, min(1.0, new_heat))

    def _process_eviction_pipeline(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
    ) -> None:
        """Process eviction pipeline for territories.

        If heat >= eviction_heat_threshold:
        - Set under_eviction = True
        - If already under_eviction: rent spikes, population displaced
        """
        eviction_threshold = services.config.eviction_heat_threshold
        rent_spike_multiplier = services.config.rent_spike_multiplier
        displacement_rate = services.config.displacement_rate

        for node_id, data in graph.nodes(data=True):
            # Only process territory nodes
            if data.get("_node_type") != "territory":
                continue

            current_heat = data.get("heat", 0.0)
            under_eviction = data.get("under_eviction", False)

            # Check if eviction should start
            if current_heat >= eviction_threshold and not under_eviction:
                graph.nodes[node_id]["under_eviction"] = True
                under_eviction = True

            # Process ongoing eviction effects
            if under_eviction:
                # Rent spike
                current_rent = data.get("rent_level", 1.0)
                graph.nodes[node_id]["rent_level"] = current_rent * rent_spike_multiplier

                # Population displacement
                current_pop = data.get("population", 0)
                new_pop = int(current_pop * (1.0 - displacement_rate))
                graph.nodes[node_id]["population"] = new_pop

    def _process_spillover(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
    ) -> None:
        """Process heat spillover via ADJACENCY edges.

        Heat spills from high-heat territories to adjacent ones.
        Formula: adjacent.heat += source.heat * heat_spillover_rate
        """
        spillover_rate = services.config.heat_spillover_rate

        # Collect spillover amounts first (to avoid order-dependent updates)
        spillover_amounts: dict[str, float] = {}

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.ADJACENCY:
                continue

            # Verify both nodes are territories
            source_data = graph.nodes.get(source_id, {})
            target_data = graph.nodes.get(target_id, {})

            if source_data.get("_node_type") != "territory":
                continue
            if target_data.get("_node_type") != "territory":
                continue

            # Calculate spillover
            source_heat = source_data.get("heat", 0.0)
            spillover = source_heat * spillover_rate

            # Accumulate spillover for target
            if target_id not in spillover_amounts:
                spillover_amounts[target_id] = 0.0
            spillover_amounts[target_id] += spillover

        # Apply accumulated spillover
        for node_id, spillover in spillover_amounts.items():
            current_heat = graph.nodes[node_id].get("heat", 0.0)
            new_heat = min(1.0, current_heat + spillover)
            graph.nodes[node_id]["heat"] = new_heat
