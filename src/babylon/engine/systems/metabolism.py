"""MetabolismSystem - The Metabolic Rift.

Slice 1.4: Track the widening rift between extraction and regeneration.

This system implements the ecological limits of capital accumulation:
- Biocapacity regeneration and depletion
- ECOLOGICAL_OVERSHOOT event emission when consumption > biocapacity

Key formulas (from src/babylon/formulas/formulas):
- calculate_biocapacity_delta: ΔB = R - (E × η)
- calculate_overshoot_ratio: O = C / B
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from babylon.engine.event_bus import Event
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.base import SystemBase
from babylon.engine.systems.protocol import ContextType
from babylon.formulas import (
    calculate_biocapacity_delta,
    calculate_overshoot_ratio,
)
from babylon.models.enums import EventType

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol


class MetabolismSystem(SystemBase):
    """System tracking the metabolic rift between extraction and regeneration.

    The metabolic rift is the core dynamic of imperial accumulation:
    extraction systematically exceeds regeneration because profit requires
    externalizing regeneration costs.

    Key formulas (from src/babylon/formulas/formulas):
    - calculate_biocapacity_delta: ΔB = R - (E × η)
    - calculate_overshoot_ratio: O = C / B

    Events emitted:
    - ECOLOGICAL_OVERSHOOT: When overshoot_ratio > 1.0
    """

    name: ClassVar[str] = "Metabolism"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply metabolic rift logic to the world graph.

        Updates each territory's biocapacity based on regeneration and extraction,
        then checks if global consumption exceeds global biocapacity (overshoot).

        Args:
            graph: Graph via GraphProtocol or raw nx.DiGraph (auto-wrapped).
            services: ServiceContainer with config, formulas, event_bus, database.
            context: Dict or TickContext with 'tick' (int) key.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        # Get metabolism parameters from GameDefines
        entropy_factor = services.defines.metabolism.entropy_factor
        overshoot_threshold = services.defines.metabolism.overshoot_threshold

        # Phase 1: Update each territory's biocapacity
        for node in graph.query_nodes(node_type="territory"):
            attrs = node.attributes

            # Calculate biocapacity change using formula
            delta = calculate_biocapacity_delta(
                regeneration_rate=attrs.get("regeneration_rate", 0.02),
                max_biocapacity=attrs.get("max_biocapacity", 100.0),
                extraction_intensity=attrs.get("extraction_intensity", 0.0),
                current_biocapacity=attrs.get("biocapacity", 100.0),
                entropy_factor=entropy_factor,
            )

            # Calculate new biocapacity with clamping
            current = attrs.get("biocapacity", 100.0)
            max_cap = attrs.get("max_biocapacity", 100.0)
            new_biocapacity = max(0.0, min(max_cap, current + delta))

            graph.update_node(node.id, biocapacity=new_biocapacity)

        # Phase 2: Calculate global aggregates (after biocapacity updates)
        total_biocapacity = sum(
            node.attributes.get("biocapacity", 0.0)
            for node in graph.query_nodes(node_type="territory")
        )

        # Mass Line: Scale consumption by population, skip inactive (dead) entities
        total_consumption = sum(
            (node.attributes.get("s_bio", 0.0) + node.attributes.get("s_class", 0.0))
            * node.attributes.get("population", 1)
            for node in graph.query_nodes(node_type="social_class")
            if node.attributes.get("active", True)
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
