"""Contradiction systems for the Babylon simulation - The Rupture."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


class ContradictionSystem:
    """Phase 4: Accumulation of Tension and Ruptures."""

    name = "Contradiction Tension"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Update tension on edges based on wealth gaps."""
        tick: int = context.get("tick", 0)
        tension_accumulation_rate = services.defines.tension.accumulation_rate

        for source_id, target_id, data in graph.edges(data=True):
            # Skip edges involving inactive (dead) entities
            if not graph.nodes[source_id].get("active", True):
                continue
            if not graph.nodes[target_id].get("active", True):
                continue

            source_wealth = graph.nodes[source_id].get("wealth", 0.0)
            target_wealth = graph.nodes[target_id].get("wealth", 0.0)

            wealth_gap = abs(target_wealth - source_wealth)
            tension_delta = wealth_gap * tension_accumulation_rate

            current_tension = data.get("tension", 0.0)
            new_tension = min(1.0, current_tension + tension_delta)

            graph.edges[source_id, target_id]["tension"] = new_tension

            if new_tension >= 1.0 and current_tension < 1.0:
                services.event_bus.publish(
                    Event(
                        type=EventType.RUPTURE,
                        tick=tick,
                        payload={"edge": f"{source_id}->{target_id}"},
                    )
                )
