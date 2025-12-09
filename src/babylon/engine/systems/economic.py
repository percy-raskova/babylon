"""Economic systems for the Babylon simulation - The Base."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EdgeType, EventType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


class ImperialRentSystem:
    """Phase 1: Economic Base - Value extraction."""

    name = "Imperial Rent"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Apply imperial rent extraction to all exploitation edges."""
        # Get formula from registry
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
            worker_ideology = worker_data.get("ideology", 0.0)

            # Map ideology [-1, 1] to consciousness [0, 1]
            consciousness = (1.0 - worker_ideology) / 2.0

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
