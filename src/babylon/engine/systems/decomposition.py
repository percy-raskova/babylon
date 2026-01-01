"""Decomposition system for class breakdown during terminal crisis.

Implements LA decomposition during SUPERWAGE_CRISIS:
- 30% of Labor Aristocracy becomes CARCERAL_ENFORCER (guards, cops)
- 70% falls into INTERNAL_PROLETARIAT (precariat, unemployed)

This models the shift from productive jobs to carceral jobs as the imperial
economy contracts. The carceral state expands to manage the surplus population.

See ai-docs/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

# Decomposition ratios from user specification
ENFORCER_FRACTION = 0.3  # 30% become guards/cops
PROLETARIAT_FRACTION = 0.7  # 70% fall into precariat


def _find_entity_by_role(
    graph: nx.DiGraph[str],
    role: SocialRole,
    *,
    include_inactive: bool = False,
) -> tuple[str, dict[str, Any]] | None:
    """Find the first entity with the specified social role.

    Args:
        graph: The simulation graph
        role: The SocialRole to search for
        include_inactive: If True, include inactive entities

    Returns:
        Tuple of (node_id, node_data) or None if not found
    """
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "territory":
            continue

        # Skip inactive unless explicitly requested
        if not include_inactive and not data.get("active", True):
            continue

        node_role = data.get("role")
        if isinstance(node_role, str):
            try:
                node_role = SocialRole(node_role)
            except ValueError:
                continue

        if node_role == role:
            return (node_id, data)

    return None


class DecompositionSystem:
    """Handles class decomposition during terminal crisis.

    The Labor Aristocracy decomposes when super-wages can't be paid:
    - Checks event bus history for SUPERWAGE_CRISIS events
    - Splits LA population: 30% enforcer / 70% internal proletariat
    - Transfers wealth proportionally
    - Emits CLASS_DECOMPOSITION event

    Must run AFTER ImperialRentSystem (which emits SUPERWAGE_CRISIS).
    """

    name = "Decomposition"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Check for SUPERWAGE_CRISIS and execute LA decomposition.

        Scans event bus history for SUPERWAGE_CRISIS events emitted by
        ImperialRentSystem earlier in this tick.
        """
        tick = context.get("tick", 0)

        # Check event bus history for SUPERWAGE_CRISIS events this tick
        crisis_events = [
            e for e in services.event_bus.get_history() if e.type == EventType.SUPERWAGE_CRISIS
        ]

        if not crisis_events:
            return

        # Process each crisis (typically just one)
        for crisis_event in crisis_events:
            self._execute_decomposition(graph, services, crisis_event, tick)

    def _execute_decomposition(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        crisis_event: Event,
        tick: int,
    ) -> None:
        """Execute LA decomposition: 30% enforcer / 70% proletariat.

        Args:
            graph: The simulation graph
            services: Service container
            crisis_event: The triggering SUPERWAGE_CRISIS event
            tick: Current simulation tick
        """
        # Find Labor Aristocracy
        la = _find_entity_by_role(graph, SocialRole.LABOR_ARISTOCRACY)
        if la is None:
            return  # No LA to decompose (or already decomposed)

        la_id, la_data = la

        # Get LA population and wealth
        la_population = la_data.get("population", 0)
        la_wealth = la_data.get("wealth", 0.0)

        if la_population <= 0:
            return  # Nothing to decompose

        # Calculate splits
        enforcer_pop_gain = int(la_population * ENFORCER_FRACTION)
        proletariat_pop = int(la_population * PROLETARIAT_FRACTION)
        enforcer_wealth_gain = la_wealth * ENFORCER_FRACTION
        proletariat_wealth = la_wealth * PROLETARIAT_FRACTION

        # Find target entities
        enforcer = _find_entity_by_role(graph, SocialRole.CARCERAL_ENFORCER, include_inactive=True)
        internal_proletariat = _find_entity_by_role(
            graph, SocialRole.INTERNAL_PROLETARIAT, include_inactive=True
        )

        # Transfer to CARCERAL_ENFORCER
        if enforcer is not None:
            enforcer_id, enforcer_data = enforcer
            current_pop = enforcer_data.get("population", 0)
            current_wealth = enforcer_data.get("wealth", 0.0)
            graph.nodes[enforcer_id]["population"] = current_pop + enforcer_pop_gain
            graph.nodes[enforcer_id]["wealth"] = current_wealth + enforcer_wealth_gain

        # Transfer to INTERNAL_PROLETARIAT
        if internal_proletariat is not None:
            ip_id, _ = internal_proletariat
            graph.nodes[ip_id]["population"] = proletariat_pop
            graph.nodes[ip_id]["wealth"] = proletariat_wealth
            graph.nodes[ip_id]["active"] = True  # Activate dormant entity

        # Deactivate Labor Aristocracy (decomposed)
        graph.nodes[la_id]["active"] = False

        # Emit CLASS_DECOMPOSITION event
        services.event_bus.publish(
            Event(
                type=EventType.CLASS_DECOMPOSITION,
                tick=tick,
                payload={
                    "source_class": la_id,
                    "source_population": la_population,
                    "source_wealth": la_wealth,
                    "enforcer_fraction": ENFORCER_FRACTION,
                    "proletariat_fraction": PROLETARIAT_FRACTION,
                    "population_transferred": {
                        "to_enforcer": enforcer_pop_gain,
                        "to_proletariat": proletariat_pop,
                    },
                    "wealth_transferred": {
                        "to_enforcer": enforcer_wealth_gain,
                        "to_proletariat": proletariat_wealth,
                    },
                    "trigger_event": crisis_event.type,
                    "narrative_hint": (
                        "CLASS DECOMPOSITION: Labor aristocracy collapses. "
                        f"{enforcer_pop_gain} become guards/cops. "
                        f"{proletariat_pop} fall into the precariat."
                    ),
                },
            )
        )
