"""Territory systems for the Babylon simulation - Layer 0.

Sprint 3.5.4: The Territorial Substrate.
Sprint 3.7: The Carceral Geography - Necropolitical Triad.
Sprint 3.7.1: Dynamic Displacement Priority Modes.

TerritorySystem manages:
1. Heat dynamics: HIGH_PROFILE gains heat, LOW_PROFILE decays heat
2. Eviction pipeline: triggered when heat >= threshold, routes to sink nodes
3. Heat spillover: via ADJACENCY edges
4. Necropolitics: CONCENTRATION_CAMP elimination, PENAL_COLONY suppression

Displacement Priority Modes (Sprint 3.7.1):
- EXTRACTION: Prison > Reservation > Camp (labor valuable, default)
- CONTAINMENT: Reservation > Prison > Camp (crisis/transition)
- ELIMINATION: Camp > Prison > Reservation (late fascism)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from babylon.models.enums import (
    DisplacementPriorityMode,
    EdgeType,
    OperationalProfile,
    TerritoryType,
)

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


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

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False
    # Priority order for sink node selection by displacement mode
    # Sprint 3.7.1: Dynamic Displacement Priority Modes
    _PRIORITY_BY_MODE: ClassVar[dict[DisplacementPriorityMode, list[TerritoryType]]] = {
        DisplacementPriorityMode.EXTRACTION: [
            TerritoryType.PENAL_COLONY,
            TerritoryType.RESERVATION,
            TerritoryType.CONCENTRATION_CAMP,
        ],
        DisplacementPriorityMode.CONTAINMENT: [
            TerritoryType.RESERVATION,
            TerritoryType.PENAL_COLONY,
            TerritoryType.CONCENTRATION_CAMP,
        ],
        DisplacementPriorityMode.ELIMINATION: [
            TerritoryType.CONCENTRATION_CAMP,
            TerritoryType.PENAL_COLONY,
            TerritoryType.RESERVATION,
        ],
    }

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply territorial dynamics to the graph.

        Phases execute in sequence:
        1. Heat dynamics (profile-based accumulation/decay)
        2. Eviction pipeline (triggered at threshold, routes to sinks)
        3. Heat spillover (via adjacency edges)
        4. Necropolitics (sink node effects)

        Sprint 3.7.1: Context can contain 'displacement_mode' to override
        the default EXTRACTION mode for sink node routing.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        self._process_heat_dynamics(graph, services)
        self._process_eviction_pipeline(graph, services, context)
        self._process_spillover(graph, services)
        self._process_necropolitics(graph, services)

    def _process_heat_dynamics(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
    ) -> None:
        """Process heat accumulation/decay based on operational profile.

        HIGH_PROFILE: heat += high_profile_heat_gain
        LOW_PROFILE: heat *= (1 - heat_decay_rate)
        """
        heat_decay_rate = services.defines.territory.heat_decay_rate
        high_profile_heat_gain = services.defines.territory.high_profile_heat_gain

        for node in graph.query_nodes(node_type="territory"):
            attrs = node.attributes

            profile = attrs.get("profile")
            # Convert string to enum if needed
            if isinstance(profile, str):
                profile = OperationalProfile(profile)

            current_heat = attrs.get("heat", 0.0)

            if profile == OperationalProfile.HIGH_PROFILE:
                # High profile gains heat
                new_heat = current_heat + high_profile_heat_gain
            else:
                # Low profile decays heat
                new_heat = current_heat * (1.0 - heat_decay_rate)

            # Clamp to [0, 1]
            graph.update_node(node.id, heat=max(0.0, min(1.0, new_heat)))

    def _find_sink_node(
        self,
        source_node_id: str,
        graph: nx.DiGraph[str] | GraphProtocol,
        mode: DisplacementPriorityMode,
    ) -> str | None:
        """Find a sink node connected to the source via ADJACENCY edge.

        Sprint 3.7: The Carceral Geography.
        Sprint 3.7.1: Dynamic Displacement Priority Modes.

        Sink nodes are territories where displaced populations flow.
        Priority depends on mode:
        - EXTRACTION: PENAL_COLONY > RESERVATION > CONCENTRATION_CAMP
        - CONTAINMENT: RESERVATION > PENAL_COLONY > CONCENTRATION_CAMP
        - ELIMINATION: CONCENTRATION_CAMP > PENAL_COLONY > RESERVATION

        Args:
            source_node_id: The territory being evicted from
            graph: The simulation graph
            mode: The displacement priority mode determining sink selection

        Returns:
            The node ID of the highest-priority adjacent sink, or None
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)
        # Get priority order for the given mode
        priority_order = self._PRIORITY_BY_MODE.get(
            mode, self._PRIORITY_BY_MODE[DisplacementPriorityMode.EXTRACTION]
        )

        # Collect all adjacent sink nodes
        adjacent_sinks: dict[TerritoryType, str] = {}

        for edge in graph.query_edges(edge_type=EdgeType.ADJACENCY):
            if edge.source_id != source_node_id:
                continue

            target_node = graph.get_node(edge.target_id)
            if target_node is None or target_node.node_type != "territory":
                continue

            territory_type = target_node.attributes.get("territory_type")
            if isinstance(territory_type, str):
                territory_type = TerritoryType(territory_type)

            # Check if it's a sink node type
            if territory_type in priority_order:
                adjacent_sinks[territory_type] = edge.target_id

        # Return highest priority sink based on mode
        for sink_type in priority_order:
            if sink_type in adjacent_sinks:
                return adjacent_sinks[sink_type]

        return None

    def _process_eviction_pipeline(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Process eviction pipeline for territories.

        Sprint 3.7: The Carceral Geography.
        Sprint 3.7.1: Dynamic Displacement Priority Modes.

        If heat >= eviction_heat_threshold:
        - Set under_eviction = True
        - If already under_eviction: rent spikes, population displaced

        Displaced population is transferred to connected sink nodes.
        If no sink node is connected, population "disappears" (original behavior).

        Args:
            graph: The simulation graph
            services: Service container with config
            context: Context dict, may contain 'displacement_mode' override
        """
        eviction_threshold = services.defines.territory.eviction_heat_threshold
        rent_spike_multiplier = services.defines.territory.rent_spike_multiplier
        displacement_rate = services.defines.territory.displacement_rate

        # Get displacement mode from context or default to EXTRACTION
        mode = context.get("displacement_mode", DisplacementPriorityMode.EXTRACTION)

        # Collect population transfers (to avoid order-dependent updates)
        transfers: dict[str, int] = {}

        for node in graph.query_nodes(node_type="territory"):
            attrs = node.attributes

            current_heat = attrs.get("heat", 0.0)
            under_eviction = attrs.get("under_eviction", False)

            # Check if eviction should start
            if current_heat >= eviction_threshold and not under_eviction:
                graph.update_node(node.id, under_eviction=True)
                under_eviction = True

            # Process ongoing eviction effects
            if under_eviction:
                # Rent spike
                current_rent = attrs.get("rent_level", 1.0)
                # Population displacement
                current_pop = attrs.get("population", 0)
                displaced_pop = int(current_pop * displacement_rate)
                new_pop = current_pop - displaced_pop

                graph.update_node(
                    node.id,
                    rent_level=current_rent * rent_spike_multiplier,
                    population=new_pop,
                )

                # Find sink node for population transfer
                if displaced_pop > 0:
                    sink_id = self._find_sink_node(node.id, graph, mode)
                    if sink_id is not None:
                        if sink_id not in transfers:
                            transfers[sink_id] = 0
                        transfers[sink_id] += displaced_pop

        # Apply population transfers to sink nodes
        for sink_id, incoming_pop in transfers.items():
            sink_node = graph.get_node(sink_id)
            current_pop = sink_node.attributes.get("population", 0) if sink_node else 0
            graph.update_node(sink_id, population=current_pop + incoming_pop)

    def _process_spillover(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
    ) -> None:
        """Process heat spillover via ADJACENCY edges.

        Heat spills from high-heat territories to adjacent ones.
        Formula: adjacent.heat += source.heat * heat_spillover_rate
        """
        spillover_rate = services.defines.territory.heat_spillover_rate

        # Collect spillover amounts first (to avoid order-dependent updates)
        spillover_amounts: dict[str, float] = {}

        for edge in graph.query_edges(edge_type=EdgeType.ADJACENCY):
            # Verify both nodes are territories
            source_node = graph.get_node(edge.source_id)
            target_node = graph.get_node(edge.target_id)

            if source_node is None or source_node.node_type != "territory":
                continue
            if target_node is None or target_node.node_type != "territory":
                continue

            # Calculate spillover
            source_heat = source_node.attributes.get("heat", 0.0)
            spillover = source_heat * spillover_rate

            # Accumulate spillover for target
            if edge.target_id not in spillover_amounts:
                spillover_amounts[edge.target_id] = 0.0
            spillover_amounts[edge.target_id] += spillover

        # Apply accumulated spillover
        for node_id, spillover in spillover_amounts.items():
            node = graph.get_node(node_id)
            current_heat = node.attributes.get("heat", 0.0) if node else 0.0
            new_heat = min(1.0, current_heat + spillover)
            graph.update_node(node_id, heat=new_heat)

    def _process_necropolitics(
        self,
        graph: GraphProtocol,
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
        decay_rate = services.defines.territory.concentration_camp_decay_rate

        for node in graph.query_nodes(node_type="territory"):
            attrs = node.attributes

            territory_type = attrs.get("territory_type")
            if isinstance(territory_type, str):
                territory_type = TerritoryType(territory_type)

            # CONCENTRATION_CAMP: population decay (elimination)
            if territory_type == TerritoryType.CONCENTRATION_CAMP:
                current_pop = attrs.get("population", 0)
                new_pop = int(current_pop * (1.0 - decay_rate))
                graph.update_node(node.id, population=new_pop)

            # PENAL_COLONY: suppress organization of connected classes
            elif territory_type == TerritoryType.PENAL_COLONY:
                self._suppress_organization(node.id, graph)

    def _suppress_organization(
        self,
        territory_id: str,
        graph: GraphProtocol,
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
        for edge in graph.query_edges(edge_type=EdgeType.TENANCY):
            if edge.target_id != territory_id:
                continue

            source_node = graph.get_node(edge.source_id)
            if source_node is None or source_node.node_type != "social_class":
                continue

            # Suppress organization
            graph.update_node(edge.source_id, organization=0.0)
