"""Reserve Army of Labor system (Feature 021, System #5).

Reads unemployment data for each territory, computes reserve army
composition, and applies wage pressure to territory median_wage.
Publishes RESERVE_ARMY_PRESSURE events via the event bus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Union

from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator
from babylon.engine.event_bus import Event
from babylon.engine.systems.base import SystemBase
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.engine.context import TickContext
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

ContextType = Union[dict[str, Any], "TickContext"]


class ReserveArmySystem(SystemBase):
    """Computes reserve army composition and applies wage pressure.

    For each territory node in the graph, reads the reserve_ratio
    (if available) and computes a wage_pressure coefficient that
    reduces median_wage. Stores the computed values on graph nodes
    and publishes events.

    Position: #5 in _DEFAULT_SYSTEMS (after TickDynamicsSystem).
    """

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    name: ClassVar[str] = "reserve_army"

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply reserve army wage pressure to all territories.

        Args:
            graph: Mutable world graph with territory nodes.
            services: Service container with defines and event_bus.
            context: Tick context with current tick number.
        """
        protocol = self._wrap_graph(graph)
        tick = context["tick"] if isinstance(context, dict) else context.tick
        defines = services.defines.reserve_army
        calculator = DefaultWagePressureCalculator(defines)

        # Lowercase per WorldState.to_graph (_node_type="territory") — the
        # capitalized "Territory" filter matched ZERO nodes in production.
        for node in list(protocol.query_nodes(node_type="territory")):
            data = node.attributes

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

            # Store computed values on node for downstream systems; wage
            # pressure reduces median_wage multiplicatively when present.
            updates: dict[str, Any] = {
                "wage_pressure": wage_pressure,
                "reserve_ratio": reserve_ratio,
            }
            current_wage = data.get("median_wage", 0.0)
            if isinstance(current_wage, (int, float)) and current_wage > 0.0:
                updates["median_wage"] = float(current_wage) * (1.0 - wage_pressure)
            protocol.update_node(node.id, **updates)

            # Publish event (median_wage mirrors the post-update node value)
            services.event_bus.publish(
                Event(
                    type=EventType.RESERVE_ARMY_PRESSURE,
                    tick=tick,
                    payload={
                        "territory": node.id,
                        "reserve_ratio": reserve_ratio,
                        "wage_pressure": wage_pressure,
                        "median_wage": updates.get("median_wage", data.get("median_wage", 0.0)),
                    },
                )
            )
