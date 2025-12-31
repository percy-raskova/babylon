"""VitalitySystem - The Drain and The Reaper.

ADR032: Materialist Causality System Order

This system runs FIRST in the materialist causality chain, implementing:
1. Phase 1 - The Drain: Linear subsistence burn (cost = base_subsistence * multiplier)
2. Phase 2 - The Reaper: Death check (wealth < consumption_needs → die)

Historical Materialist Principle:
    Life requires material sustenance. Living costs wealth. No wealth = no life.
    Elites with higher subsistence multipliers burn faster when cut off from
    imperial rent flows - modeling the "Principal Contradiction" where
    bourgeoisie depends on extraction to maintain their standard of living.
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
    """Phase 1: The Drain + The Reaper (ADR032).

    Two-phase vitality check for all active entities:

    Phase 1 - The Drain (Subsistence Burn):
        cost = base_subsistence × subsistence_multiplier
        wealth = max(0, wealth - cost)

    Phase 2 - The Reaper (Death Check):
        If wealth < consumption_needs (s_bio + s_class), entity dies.

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
        """Execute two-phase vitality check.

        Phase 1 - The Drain: Burn wealth based on subsistence cost.
        Phase 2 - The Reaper: Mark dead those who can't afford to live.
        """
        tick: int = context.get("tick", 0)
        base_subsistence = services.defines.economy.base_subsistence

        for node_id, data in graph.nodes(data=True):
            # Skip non-entity nodes (territories, etc.)
            if data.get("_node_type") != "social_class":
                continue

            # Skip already-dead entities
            if not data.get("active", True):
                continue

            # Phase 1: The Drain (Subsistence Burn)
            if base_subsistence > 0:
                wealth = data.get("wealth", 0.0)
                multiplier = data.get("subsistence_multiplier", 1.0)
                cost = base_subsistence * multiplier
                graph.nodes[node_id]["wealth"] = max(0.0, wealth - cost)

            # Phase 2: The Reaper (Death Check)
            # Calculate consumption needs: s_bio + s_class
            s_bio = data.get("s_bio", 0.0)
            s_class = data.get("s_class", 0.0)
            consumption_needs = s_bio + s_class

            wealth = graph.nodes[node_id].get("wealth", 0.0)

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
