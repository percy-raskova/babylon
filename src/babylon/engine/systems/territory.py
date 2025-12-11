"""Territory systems for the Babylon simulation - Layer 0.

Sprint 3.5.4: The Territorial Substrate.
Sprint 3.7: The Carceral Geography - Necropolitical Triad.

TerritorySystem manages:
1. Heat dynamics: HIGH_PROFILE gains heat, LOW_PROFILE decays heat
2. Eviction pipeline: triggered when heat >= threshold, routes to sink nodes
3. Heat spillover: via ADJACENCY edges
4. Necropolitics: CONCENTRATION_CAMP elimination, PENAL_COLONY suppression
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.models.enums import EdgeType, OperationalProfile, TerritoryType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


class TerritorySystem:
    """Territory Dynamic System - Layer 0 spatial dynamics.

    Implements the territorial substrate mechanics:
    - Heat dynamics based on operational profile
    - Eviction pipeline when heat exceeds threshold
    - Heat spillover between adjacent territories
    - Necropolitics for sink nodes (Sprint 3.7)

    "Legibility over Stealth" - The State knows where you are.
    The game is about staying below the repression threshold.

    Sprint 3.7 additions:
    - Population transfers to sink nodes during eviction
    - CONCENTRATION_CAMP population decay (elimination)
    - PENAL_COLONY organization suppression (atomization)
    """

    name = "Territory"

    # Priority order for sink node selection (highest to lowest)
    _SINK_PRIORITY: list[TerritoryType] = [
        TerritoryType.CONCENTRATION_CAMP,
        TerritoryType.PENAL_COLONY,
        TerritoryType.RESERVATION,
    ]

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply territorial dynamics to the graph.

        Phases execute in sequence:
        1. Heat dynamics (profile-based accumulation/decay)
        2. Eviction pipeline (triggered at threshold, routes to sinks)
        3. Heat spillover (via adjacency edges)
        4. Necropolitics (sink node effects)
        """
        _ = context  # Unused but kept for API consistency
        self._process_heat_dynamics(graph, services)
        self._process_eviction_pipeline(graph, services)
        self._process_spillover(graph, services)
        self._process_necropolitics(graph, services)

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

    def _find_sink_node(
        self,
        source_node_id: str,
        graph: nx.DiGraph[str],
    ) -> str | None:
        """Find a sink node connected to the source via ADJACENCY edge.

        Sprint 3.7: The Carceral Geography.
        Sink nodes are territories where displaced populations flow.
        Priority: CONCENTRATION_CAMP > PENAL_COLONY > RESERVATION

        Args:
            source_node_id: The territory being evicted from
            graph: The simulation graph

        Returns:
            The node ID of the highest-priority adjacent sink, or None
        """
        # Collect all adjacent sink nodes
        adjacent_sinks: dict[TerritoryType, str] = {}

        for _, target_id, edge_data in graph.out_edges(source_node_id, data=True):
            edge_type = edge_data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.ADJACENCY:
                continue

            target_data = graph.nodes.get(target_id, {})
            if target_data.get("_node_type") != "territory":
                continue

            territory_type = target_data.get("territory_type")
            if isinstance(territory_type, str):
                territory_type = TerritoryType(territory_type)

            # Check if it's a sink node type
            if territory_type in self._SINK_PRIORITY:
                adjacent_sinks[territory_type] = target_id

        # Return highest priority sink
        for sink_type in self._SINK_PRIORITY:
            if sink_type in adjacent_sinks:
                return adjacent_sinks[sink_type]

        return None

    def _process_eviction_pipeline(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
    ) -> None:
        """Process eviction pipeline for territories.

        Sprint 3.7: The Carceral Geography.
        If heat >= eviction_heat_threshold:
        - Set under_eviction = True
        - If already under_eviction: rent spikes, population displaced

        Displaced population is transferred to connected sink nodes.
        If no sink node is connected, population "disappears" (original behavior).
        """
        eviction_threshold = services.config.eviction_heat_threshold
        rent_spike_multiplier = services.config.rent_spike_multiplier
        displacement_rate = services.config.displacement_rate

        # Collect population transfers (to avoid order-dependent updates)
        transfers: dict[str, int] = {}

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
                displaced_pop = int(current_pop * displacement_rate)
                new_pop = current_pop - displaced_pop
                graph.nodes[node_id]["population"] = new_pop

                # Find sink node for population transfer
                if displaced_pop > 0:
                    sink_id = self._find_sink_node(node_id, graph)
                    if sink_id is not None:
                        if sink_id not in transfers:
                            transfers[sink_id] = 0
                        transfers[sink_id] += displaced_pop

        # Apply population transfers to sink nodes
        for sink_id, incoming_pop in transfers.items():
            current_pop = graph.nodes[sink_id].get("population", 0)
            graph.nodes[sink_id]["population"] = current_pop + incoming_pop

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

    def _process_necropolitics(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
    ) -> None:
        """Process necropolitical effects on sink nodes.

        Sprint 3.7: The Carceral Geography - Necropolitical Triad.

        Sink nodes apply special effects each tick:
        - CONCENTRATION_CAMP: population *= (1 - decay_rate) [elimination]
        - PENAL_COLONY: connected SocialClass.organization = 0.0 [suppression]

        RESERVATION territories have no additional effects - they only
        warehouse population (containment without active elimination).
        """
        decay_rate = services.config.concentration_camp_decay_rate

        for node_id, data in graph.nodes(data=True):
            # Only process territory nodes
            if data.get("_node_type") != "territory":
                continue

            territory_type = data.get("territory_type")
            if isinstance(territory_type, str):
                territory_type = TerritoryType(territory_type)

            # CONCENTRATION_CAMP: population decay (elimination)
            if territory_type == TerritoryType.CONCENTRATION_CAMP:
                current_pop = data.get("population", 0)
                new_pop = int(current_pop * (1.0 - decay_rate))
                graph.nodes[node_id]["population"] = new_pop

            # PENAL_COLONY: suppress organization of connected classes
            elif territory_type == TerritoryType.PENAL_COLONY:
                self._suppress_organization(node_id, graph)

    def _suppress_organization(
        self,
        territory_id: str,
        graph: nx.DiGraph[str],
    ) -> None:
        """Suppress organization of SocialClass nodes connected to a territory.

        Sprint 3.7: The Carceral Geography.
        Classes connected via TENANCY edge to a penal colony have their
        organization set to 0.0 (atomization via incarceration).

        Args:
            territory_id: The penal colony territory node ID
            graph: The simulation graph
        """
        # Find all SocialClass nodes with TENANCY edge to this territory
        for source_id, _target_id, edge_data in graph.in_edges(territory_id, data=True):
            edge_type = edge_data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.TENANCY:
                continue

            source_data = graph.nodes.get(source_id, {})
            if source_data.get("_node_type") != "social_class":
                continue

            # Suppress organization
            graph.nodes[source_id]["organization"] = 0.0
