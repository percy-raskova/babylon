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

        # Evaluate Contradiction Frames
        if hasattr(graph, "get_graph_attr"):
            frames_data = graph.get_graph_attr("contradiction_frames", {})
        else:
            frames_data = getattr(graph, "graph", {}).get("contradiction_frames", {})

        if not frames_data:
            from babylon.engine.factories import create_contradiction_frame

            # Initialize default global frame if none exists
            global_frame = create_contradiction_frame("global")
            frames_data = {"global": global_frame.model_dump()}
            if hasattr(graph, "set_graph_attr"):
                graph.set_graph_attr("contradiction_frames", frames_data)
            else:
                getattr(graph, "graph", {})["contradiction_frames"] = frames_data

        from babylon.models.entities.contradiction import ContradictionFrame

        aspect_flip_threshold = getattr(services.defines.tension, "aspect_flip_threshold", 1.0)
        antagonistic_threshold = getattr(
            services.defines.tension, "antagonistic_intensity_threshold", 0.8
        )

        for scope, frame_dict in frames_data.items():
            frame = ContradictionFrame(**frame_dict)

            # Simulate dialectical movement based on tension accumulation
            for contradiction in [frame.principal, frame.secondary]:
                contradiction.aspect_balance += 0.005 * tension_accumulation_rate
                contradiction.intensity += 0.001 * tension_accumulation_rate

                # Check for antagonistic transition
                if (
                    not contradiction.is_antagonistic
                    and contradiction.intensity >= antagonistic_threshold
                ):
                    contradiction.is_antagonistic = True
                    services.event_bus.publish(
                        Event(
                            type=EventType.EDGE_MODE_TRANSITION,
                            tick=tick,
                            payload={
                                "scope": scope,
                                "contradiction": contradiction.id,
                                "mode": "antagonistic",
                            },
                        )
                    )

            # Check for aspect flip
            for contradiction in [frame.principal, frame.secondary]:
                if abs(contradiction.aspect_balance) >= aspect_flip_threshold:
                    # Aspect Flip!
                    temp = contradiction.aspect_a
                    contradiction.aspect_a = contradiction.aspect_b
                    contradiction.aspect_b = temp
                    contradiction.aspect_balance = 0.0  # reset accumulation after flip

                    services.event_bus.publish(
                        Event(
                            type=EventType.ASPECT_REVERSAL,
                            tick=tick,
                            payload={"scope": scope, "contradiction": contradiction.id},
                        )
                    )

            # Check for principal/secondary swap (Maoist structural crisis)
            if frame.secondary.intensity > frame.principal.intensity:
                temp_c = frame.principal
                frame.principal = frame.secondary
                frame.secondary = temp_c

                services.event_bus.publish(
                    Event(
                        type=EventType.PRINCIPAL_CONTRADICTION_SHIFT,
                        tick=tick,
                        payload={"scope": scope, "new_principal": frame.principal.id},
                    )
                )

            # Persist changes
            frames_data[scope] = frame.model_dump()
