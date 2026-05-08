"""Contradiction systems for the Babylon simulation - The Rupture."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

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

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

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

        self._update_edge_tensions(graph, services, context)
        self._evaluate_contradiction_frames(graph, services, context)

    def _calculate_macro_aspect_metrics(
        self,
        graph: GraphProtocol,
        aspect: str | object,
    ) -> tuple[float, float]:
        """Return (total_mass, avg_centrality) for a given aspect.

        Args:
            graph: The simulation state graph.
            aspect: The string or enum representing the structural aspect.

        Returns:
            Tuple of (total_economic_mass, average_centrality).
        """
        total_mass = 0.0
        total_centrality = 0.0
        count = 0
        aspect_val = getattr(aspect, "value", str(aspect))

        for node in graph.query_nodes():
            attrs = node.attributes
            if not attrs.get("active", True):
                continue

            role = attrs.get("role", "")
            role_val = getattr(role, "value", str(role))

            memberships = attrs.get("community_memberships", [])
            comm_types = []
            for m in memberships:
                c_type = (
                    getattr(m, "community_type", m.get("community_type", ""))
                    if isinstance(m, dict)
                    else getattr(m, "community_type", "")
                )
                comm_types.append(getattr(c_type, "value", str(c_type)))

            is_match = (
                role_val == aspect_val
                or aspect_val in comm_types
                or attrs.get("naics_2digit") == aspect_val
            )

            if is_match:
                # Mass = wealth OR (total_wages for industries)
                mass = float(attrs.get("wealth", attrs.get("total_wages", 0.0)))
                centrality = float(attrs.get("centrality", 0.5))
                total_mass += mass
                total_centrality += centrality
                count += 1

        if count == 0:
            return (0.0, 0.5)
        return (total_mass, total_centrality / count)

    def _update_edge_tensions(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Update individual edge tensions based on modes."""
        tick: int = context.get("tick", 0)
        tension_accumulation_rate = services.defines.tension.accumulation_rate

        for edge in graph.query_edges():
            src_node = graph.get_node(edge.source_id)
            tgt_node = graph.get_node(edge.target_id)

            if src_node and not src_node.attributes.get("active", True):
                continue
            if tgt_node and not tgt_node.attributes.get("active", True):
                continue

            source_wealth = src_node.attributes.get("wealth", 0.0) if src_node else 0.0
            target_wealth = tgt_node.attributes.get("wealth", 0.0) if tgt_node else 0.0

            wealth_gap = abs(target_wealth - source_wealth)

            src_centrality = float(src_node.attributes.get("centrality", 0.5)) if src_node else 0.5
            tgt_centrality = float(tgt_node.attributes.get("centrality", 0.5)) if tgt_node else 0.5

            from babylon.formulas.contradiction import calculate_contradiction_intensity

            tension_delta = calculate_contradiction_intensity(
                divergence=wealth_gap,
                centrality_a=src_centrality,
                centrality_b=tgt_centrality,
                sensitivity=tension_accumulation_rate,
            )

            current_tension = float(edge.attributes.get("tension", 0.0))
            edge_mode = edge.attributes.get("edge_mode")
            mode_value = getattr(edge_mode, "value", edge_mode)

            if mode_value == "extractive":
                new_tension = min(1.0, current_tension + tension_delta)
            elif mode_value == "co_optive":
                concession_flow = float(edge.attributes.get("value_flow", 0.0))
                concession_threshold = (
                    float(src_node.attributes.get("consumption_needs", 1.0)) if src_node else 1.0
                )

                if concession_flow >= concession_threshold:
                    new_tension = max(0.0, current_tension - (tension_accumulation_rate * 0.1))
                else:
                    new_tension = min(1.0, current_tension + (tension_delta * 1.5))
                    if new_tension >= 0.8 and current_tension < 0.8:
                        services.event_bus.publish(
                            Event(
                                type=EventType.CO_OPTIVE_BREAKDOWN,
                                tick=tick,
                                payload={"edge": f"{edge.source_id}->{edge.target_id}"},
                            )
                        )
            else:
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

    def _evaluate_contradiction_frames(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Evaluate dialectical progression in contradiction frames."""
        tick: int = context.get("tick", 0)
        tension_accumulation_rate = services.defines.tension.accumulation_rate

        if hasattr(graph, "get_graph_attr"):
            frames_data = graph.get_graph_attr("contradiction_frames", {})
        else:
            frames_data = getattr(graph, "graph", {}).get("contradiction_frames", {})

        if not frames_data:
            from babylon.engine.factories import create_contradiction_frame

            global_frame = create_contradiction_frame("global")
            frames_data = {"global": global_frame.model_dump()}
            if hasattr(graph, "set_graph_attr"):
                graph.set_graph_attr("contradiction_frames", frames_data)
            else:
                getattr(graph, "graph", {})["contradiction_frames"] = frames_data

        from babylon.formulas.contradiction import calculate_contradiction_intensity
        from babylon.models.entities.contradiction import Contradiction, ContradictionFrame

        aspect_flip_threshold = getattr(services.defines.tension, "aspect_flip_threshold", 1.0)
        antagonistic_threshold = getattr(
            services.defines.tension, "antagonistic_intensity_threshold", 0.8
        )

        for scope, frame_dict in frames_data.items():
            frame = ContradictionFrame(**frame_dict)

            # Spec 056 / III.7: Contradiction + ContradictionFrame are frozen.
            # We accumulate field updates and produce new instances via
            # model_copy() rather than mutating in place.
            updated_slots: dict[str, Contradiction] = {}
            for slot, contradiction in (
                ("principal", frame.principal),
                ("secondary", frame.secondary),
            ):
                mass_a, cent_a = self._calculate_macro_aspect_metrics(graph, contradiction.aspect_a)
                mass_b, cent_b = self._calculate_macro_aspect_metrics(graph, contradiction.aspect_b)

                total_mass = mass_a + mass_b
                if total_mass > 0:
                    divergence = abs(mass_a - mass_b) / total_mass
                    balance_shift = (mass_b - mass_a) / total_mass
                else:
                    divergence = 0.0
                    balance_shift = 0.0

                intensity_delta = calculate_contradiction_intensity(
                    divergence=divergence,
                    centrality_a=cent_a,
                    centrality_b=cent_b,
                    sensitivity=tension_accumulation_rate * 0.05,
                )

                new_intensity = min(
                    1.0,
                    max(0.0, float(contradiction.intensity + intensity_delta)),
                )
                new_balance = min(
                    1.0,
                    max(
                        -1.0,
                        float(
                            contradiction.aspect_balance
                            + balance_shift * 0.01 * tension_accumulation_rate
                        ),
                    ),
                )

                # Antagonistic transition (one-way: False → True)
                new_is_antagonistic = contradiction.is_antagonistic
                if not contradiction.is_antagonistic and new_intensity >= antagonistic_threshold:
                    new_is_antagonistic = True
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

                # Aspect-flip on balance threshold
                new_aspect_a = contradiction.aspect_a
                new_aspect_b = contradiction.aspect_b
                new_balance_after_flip = new_balance
                if abs(new_balance) >= aspect_flip_threshold:
                    new_aspect_a, new_aspect_b = (
                        contradiction.aspect_b,
                        contradiction.aspect_a,
                    )
                    new_balance_after_flip = 0.0
                    services.event_bus.publish(
                        Event(
                            type=EventType.ASPECT_REVERSAL,
                            tick=tick,
                            payload={"scope": scope, "contradiction": contradiction.id},
                        )
                    )

                updated_slots[slot] = contradiction.model_copy(
                    update={
                        "intensity": new_intensity,
                        "aspect_balance": new_balance_after_flip,
                        "is_antagonistic": new_is_antagonistic,
                        "aspect_a": new_aspect_a,
                        "aspect_b": new_aspect_b,
                    }
                )

            new_principal = updated_slots["principal"]
            new_secondary = updated_slots["secondary"]

            # Principal/secondary swap when secondary's intensity exceeds principal's
            if new_secondary.intensity > new_principal.intensity:
                new_principal, new_secondary = new_secondary, new_principal
                services.event_bus.publish(
                    Event(
                        type=EventType.PRINCIPAL_CONTRADICTION_SHIFT,
                        tick=tick,
                        payload={"scope": scope, "new_principal": new_principal.id},
                    )
                )

            new_frame = frame.model_copy(
                update={"principal": new_principal, "secondary": new_secondary}
            )
            frames_data[scope] = new_frame.model_dump()
