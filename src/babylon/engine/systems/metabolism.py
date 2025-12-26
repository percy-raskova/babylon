"""MetabolismSystem - The Metabolic Rift.

Slice 1.4: Track the widening rift between extraction and regeneration.

This system implements the ecological limits of capital accumulation:
- Biocapacity regeneration and depletion
- ECOLOGICAL_OVERSHOOT event emission when consumption > biocapacity

Key formulas (from src/babylon/systems/formulas.py):
- calculate_biocapacity_delta: ΔB = R - (E × η)
- calculate_overshoot_ratio: O = C / B
"""

from __future__ import annotations

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.protocol import ContextType
from babylon.models.enums import EventType
from babylon.systems.formulas import (
    calculate_biocapacity_delta,
    calculate_overshoot_ratio,
)


class MetabolismSystem:
    """System tracking the metabolic rift between extraction and regeneration.

    The metabolic rift is the core dynamic of imperial accumulation:
    extraction systematically exceeds regeneration because profit requires
    externalizing regeneration costs.

    Key formulas (from src/babylon/systems/formulas.py):
    - calculate_biocapacity_delta: ΔB = R - (E × η)
    - calculate_overshoot_ratio: O = C / B

    Events emitted:
    - ECOLOGICAL_OVERSHOOT: When overshoot_ratio > 1.0
    """

    @property
    def name(self) -> str:
        """The identifier of this system."""
        return "Metabolism"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply metabolic rift logic to the world graph.

        Updates each territory's biocapacity based on regeneration and extraction,
        then checks if global consumption exceeds global biocapacity (overshoot).

        Args:
            graph: Mutable NetworkX graph with territory and social_class nodes.
            services: ServiceContainer with config, formulas, event_bus, database.
            context: Dict or TickContext with 'tick' (int) key.
        """
        # Get metabolism parameters from GameDefines
        entropy_factor = services.defines.metabolism.entropy_factor
        overshoot_threshold = services.defines.metabolism.overshoot_threshold

        # Phase 1: Update each territory's biocapacity
        for node_id, data in graph.nodes(data=True):
            if data.get("_node_type") != "territory":
                continue

            # Calculate biocapacity change using formula
            delta = calculate_biocapacity_delta(
                regeneration_rate=data.get("regeneration_rate", 0.02),
                max_biocapacity=data.get("max_biocapacity", 100.0),
                extraction_intensity=data.get("extraction_intensity", 0.0),
                current_biocapacity=data.get("biocapacity", 100.0),
                entropy_factor=entropy_factor,
            )

            # Calculate new biocapacity with clamping
            current = data.get("biocapacity", 100.0)
            max_cap = data.get("max_biocapacity", 100.0)
            new_biocapacity = max(0.0, min(max_cap, current + delta))

            # Mutate graph node in place
            graph.nodes[node_id]["biocapacity"] = new_biocapacity

        # Phase 2: Calculate global aggregates (after biocapacity updates)
        total_biocapacity = sum(
            data.get("biocapacity", 0.0)
            for _, data in graph.nodes(data=True)
            if data.get("_node_type") == "territory"
        )

        total_consumption = sum(
            data.get("s_bio", 0.0) + data.get("s_class", 0.0)
            for _, data in graph.nodes(data=True)
            if data.get("_node_type") == "social_class"
        )

        # Phase 3: Check overshoot and emit event if ratio exceeds threshold
        ratio = calculate_overshoot_ratio(
            total_consumption,
            total_biocapacity,
            max_ratio=services.defines.metabolism.max_overshoot_ratio,
        )

        if ratio > overshoot_threshold:
            tick = context.get("tick", 0) if isinstance(context, dict) else context.tick
            services.event_bus.publish(
                Event(
                    type=EventType.ECOLOGICAL_OVERSHOOT,
                    tick=tick,
                    payload={
                        "overshoot_ratio": ratio,
                        "total_consumption": total_consumption,
                        "total_biocapacity": total_biocapacity,
                    },
                )
            )
