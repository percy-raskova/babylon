"""VitalitySystem - The Reaper.

Material Reality Refactor: Entities die when wealth < consumption_needs.

This system runs at the START of each tick, before production or extraction.
When an entity cannot meet its metabolic requirements (s_bio + s_class),
it is marked as inactive and an ENTITY_DEATH event is emitted.

Historical Materialist Principle:
    Life requires material sustenance. No wealth = no life.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


class VitalitySystem:
    """Phase 0: Death check - The Reaper.

    Checks all active entities for starvation.
    If wealth < consumption_needs (s_bio + s_class), entity dies.

    Args:
        graph: Mutable world graph with entity nodes.
        services: ServiceContainer for event publishing.
        context: TickContext with current tick number.

    Events:
        ENTITY_DEATH: Emitted when an entity starves.
            payload: {entity_id, wealth, consumption_needs, tick}
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "vitality"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Check for entity deaths due to starvation.

        Iterates all social_class nodes. If an active entity has
        wealth < consumption_needs, it dies (active=False) and
        an ENTITY_DEATH event is emitted.
        """
        tick: int = context.get("tick", 0)

        for node_id, data in graph.nodes(data=True):
            # Skip non-entity nodes (territories, etc.)
            if data.get("_node_type") != "social_class":
                continue

            # Skip already-dead entities
            if not data.get("active", True):
                continue

            # Calculate consumption needs: s_bio + s_class
            s_bio = data.get("s_bio", 0.0)
            s_class = data.get("s_class", 0.0)
            consumption_needs = s_bio + s_class

            wealth = data.get("wealth", 0.0)

            # Death check: wealth < consumption_needs
            if wealth < consumption_needs:
                # Mark as dead
                graph.nodes[node_id]["active"] = False

                # Emit death event for narrative layer
                services.event_bus.publish(
                    Event(
                        type=EventType.ENTITY_DEATH,
                        tick=tick,
                        payload={
                            "entity_id": node_id,
                            "wealth": wealth,
                            "consumption_needs": consumption_needs,
                            "s_bio": s_bio,
                            "s_class": s_class,
                        },
                    )
                )
