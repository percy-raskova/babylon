"""Contradiction systems for the Babylon simulation - The Rupture."""

from __future__ import annotations

from typing import Any

import networkx as nx

from babylon.models.config import SimulationConfig


class ContradictionSystem:
    """Phase 4: Accumulation of Tension and Ruptures."""

    name = "Contradiction Tension"

    def step(
        self,
        graph: nx.DiGraph[str],
        config: SimulationConfig,
        context: dict[str, Any],
    ) -> None:
        """Update tension on edges based on wealth gaps."""
        events: list[str] = context.get("events", [])
        tick: int = context.get("tick", 0)

        for source_id, target_id, data in graph.edges(data=True):
            source_wealth = graph.nodes[source_id].get("wealth", 0.0)
            target_wealth = graph.nodes[target_id].get("wealth", 0.0)

            wealth_gap = abs(target_wealth - source_wealth)
            tension_delta = wealth_gap * config.tension_accumulation_rate

            current_tension = data.get("tension", 0.0)
            new_tension = min(1.0, current_tension + tension_delta)

            graph.edges[source_id, target_id]["tension"] = new_tension

            if new_tension >= 1.0 and current_tension < 1.0:
                events.append(f"Tick {tick + 1}: RUPTURE on edge {source_id}->{target_id}")
