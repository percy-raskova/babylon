"""Reserve Army of Labor system (Feature 021, System #17).

Reads unemployment data for each territory, computes reserve army
composition, and applies wage pressure to territory median_wage.
Publishes RESERVE_ARMY_PRESSURE events via the event bus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Union

import networkx as nx

from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator
from babylon.engine.event_bus import Event
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.engine.context import TickContext
    from babylon.engine.services import ServiceContainer

ContextType = Union[dict[str, Any], "TickContext"]


class ReserveArmySystem:
    """Computes reserve army composition and applies wage pressure.

    For each territory node in the graph, reads the reserve_ratio
    (if available) and computes a wage_pressure coefficient that
    reduces median_wage. Stores the computed values on graph nodes
    and publishes events.

    Position: #17 in _DEFAULT_SYSTEMS (after TickDynamicsSystem).
    """

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    @property
    def name(self) -> str:
        """System identifier."""
        return "reserve_army"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply reserve army wage pressure to all territories.

        Args:
            graph: Mutable world graph with territory nodes.
            services: Service container with defines and event_bus.
            context: Tick context with current tick number.
        """
        tick = context["tick"] if isinstance(context, dict) else context.tick
        defines = services.defines.reserve_army
        calculator = DefaultWagePressureCalculator(defines)

        for node_id in list(graph.nodes):
            data = graph.nodes[node_id]

            # Only process territory nodes
            if data.get("_node_type") != "Territory":
                continue

            # Read reserve_ratio from node (set by data loader or prior system)
            reserve_ratio = data.get("reserve_ratio", 0.0)
            if not isinstance(reserve_ratio, (int, float)):
                continue

            reserve_ratio = float(reserve_ratio)
            if reserve_ratio <= 0.0:
                continue

            # Compute wage pressure
            wage_pressure = calculator.compute_wage_pressure(reserve_ratio)
            if wage_pressure <= 0.0:
                continue

            # Apply wage pressure to median_wage
            current_wage = data.get("median_wage", 0.0)
            if isinstance(current_wage, (int, float)) and current_wage > 0.0:
                # Wage pressure reduces median_wage multiplicatively
                adjusted_wage = float(current_wage) * (1.0 - wage_pressure)
                graph.nodes[node_id]["median_wage"] = adjusted_wage

            # Store computed values on node for downstream systems
            graph.nodes[node_id]["wage_pressure"] = wage_pressure
            graph.nodes[node_id]["reserve_ratio"] = reserve_ratio

            # Publish event
            services.event_bus.publish(
                Event(
                    type=EventType.RESERVE_ARMY_PRESSURE,
                    tick=tick,
                    payload={
                        "territory": node_id,
                        "reserve_ratio": reserve_ratio,
                        "wage_pressure": wage_pressure,
                        "median_wage": graph.nodes[node_id].get("median_wage", 0.0),
                    },
                )
            )
