"""Dispossession Event system (Feature 021, System #18).

Computes aggregate dispossession events per territory-tick, tracks
value transfers between territories, and feeds rates to existing
class transition engine. Publishes DISPOSSESSION_EVENT and
VALUE_TRANSFER events via the event bus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Union

import networkx as nx

from babylon.economics.dispossession.intensity import DispossessionIntensityCalculator
from babylon.engine.event_bus import Event
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.engine.context import TickContext
    from babylon.engine.services import ServiceContainer

ContextType = Union[dict[str, Any], "TickContext"]


class DispossessionEventSystem:
    """Computes aggregate dispossession and tracks value transfers.

    For each territory node, reads dispossession rates (foreclosure_rate,
    eviction_rate, displacement_rate, etc.), computes composite intensity,
    and publishes events. Value transfers are clamped to available wealth.

    Position: #18 in _DEFAULT_SYSTEMS (after ImperialRentSystem).
    """

    # Spec 053 INV-001: DispossessionEventSystem mutates territory wealth via
    # value-transfer clamping (`territory_wealth - transfer_amount`).
    # Default-deny while audit pending; flip to False once conservation proven.
    creates_value: ClassVar[bool] = True

    @property
    def name(self) -> str:
        """System identifier."""
        return "dispossession_events"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Process dispossession events for all territories.

        Args:
            graph: Mutable world graph with territory nodes.
            services: Service container with defines and event_bus.
            context: Tick context with current tick number.
        """
        tick = context["tick"] if isinstance(context, dict) else context.tick
        defines = services.defines.dispossession
        calculator = DispossessionIntensityCalculator(defines)

        for node_id in list(graph.nodes):
            data = graph.nodes[node_id]

            # Only process territory nodes
            if data.get("_node_type") != "Territory":
                continue

            # Read dispossession rates from node
            foreclosure_rate = _get_float(data, "foreclosure_rate")
            eviction_rate = _get_float(data, "eviction_rate")
            displacement_rate = _get_float(data, "displacement_rate")

            # Check if any dispossession activity exists
            if foreclosure_rate <= 0.0 and eviction_rate <= 0.0 and displacement_rate <= 0.0:
                continue

            # Build a lightweight state for intensity computation
            from babylon.economics.dispossession.types import TerritoryDispossessionState

            state = TerritoryDispossessionState(
                fips_code=str(data.get("fips_code", "00000"))[:5].ljust(5, "0"),
                year=int(data.get("year", 2010)),
                foreclosure_rate=min(foreclosure_rate, 1.0),
                eviction_rate=min(eviction_rate, 1.0),
                displacement_rate=min(displacement_rate, 1.0),
                concentrated_ownership=min(_get_float(data, "concentrated_ownership"), 1.0),
                absentee_landlord_share=min(_get_float(data, "absentee_landlord_share"), 1.0),
            )

            intensity = calculator.compute_intensity(state)

            # Compute value transfer (clamped to available wealth)
            territory_wealth = _get_float(data, "wealth")
            transfer_amount = territory_wealth * intensity * defines.transfer_scale
            transfer_amount = min(transfer_amount, territory_wealth)  # Clamp

            if transfer_amount > 0.0:
                net_received, deadweight = calculator.compute_value_transfer(transfer_amount)
                # Reduce territory wealth
                graph.nodes[node_id]["wealth"] = territory_wealth - transfer_amount

                # Publish value transfer event
                services.event_bus.publish(
                    Event(
                        type=EventType.VALUE_TRANSFER,
                        tick=tick,
                        payload={
                            "territory": node_id,
                            "total_transferred": transfer_amount,
                            "net_received": net_received,
                            "deadweight_loss": deadweight,
                        },
                    )
                )

            # Store intensity on node
            graph.nodes[node_id]["dispossession_intensity"] = intensity

            # Publish dispossession event
            services.event_bus.publish(
                Event(
                    type=EventType.DISPOSSESSION_EVENT,
                    tick=tick,
                    payload={
                        "territory": node_id,
                        "intensity": intensity,
                        "foreclosure_rate": foreclosure_rate,
                        "eviction_rate": eviction_rate,
                        "displacement_rate": displacement_rate,
                    },
                )
            )


def _get_float(data: dict[str, Any], key: str) -> float:
    """Safely extract a float value from node data."""
    val = data.get(key, 0.0)
    if isinstance(val, (int, float)):
        return max(float(val), 0.0)
    return 0.0
