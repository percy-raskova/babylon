"""Contradiction systems for the Babylon simulation - The Rupture."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


class ContradictionSystem:
    """Phase 4: Accumulation of Tension and Ruptures."""

    name = "Contradiction Tension"

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Update tension on edges based on wealth gaps."""
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        tick: int = context.get("tick", 0)
        tension_accumulation_rate = services.defines.tension.accumulation_rate

        for edge in graph.query_edges():
            # Read source and target nodes once
            src_node = graph.get_node(edge.source_id)
            tgt_node = graph.get_node(edge.target_id)

            # Skip edges involving inactive (dead) entities
            if src_node and not src_node.attributes.get("active", True):
                continue
            if tgt_node and not tgt_node.attributes.get("active", True):
                continue

            source_wealth = src_node.attributes.get("wealth", 0.0) if src_node else 0.0
            target_wealth = tgt_node.attributes.get("wealth", 0.0) if tgt_node else 0.0

            wealth_gap = abs(target_wealth - source_wealth)
            tension_delta = wealth_gap * tension_accumulation_rate

            current_tension = edge.attributes.get("tension", 0.0)
            new_tension = min(1.0, current_tension + tension_delta)

            graph.update_edge(edge.source_id, edge.target_id, edge.edge_type, tension=new_tension)

            if new_tension >= 1.0 and current_tension < 1.0:
                services.event_bus.publish(
                    Event(
                        type=EventType.RUPTURE,
                        tick=tick,
                        payload={"edge": f"{edge.source_id}->{edge.target_id}"},
                    )
                )
