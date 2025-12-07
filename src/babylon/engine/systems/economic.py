"""Economic systems for the Babylon simulation - The Base."""

from __future__ import annotations

from typing import Any

import networkx as nx

from babylon.models.config import SimulationConfig
from babylon.models.enums import EdgeType
from babylon.systems.formulas import calculate_imperial_rent


class ImperialRentSystem:
    """Phase 1: Economic Base - Value extraction."""

    name = "Imperial Rent"

    def step(
        self,
        graph: nx.DiGraph[str],
        config: SimulationConfig,
        _context: dict[str, Any],
    ) -> None:
        """Apply imperial rent extraction to all exploitation edges."""
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
                alpha=config.extraction_efficiency,
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
