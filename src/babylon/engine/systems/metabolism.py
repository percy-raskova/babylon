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

from babylon.formulas import (
    calculate_biocapacity_delta,
    calculate_hysteresis_damage,
    calculate_overshoot_ratio,
)
from babylon.kernel.event_bus import Event
from babylon.kernel.services import ServicesProtocol
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol


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
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Apply metabolic rift logic to the world graph.

        Updates each territory's biocapacity based on regeneration and extraction,
        then checks if global consumption exceeds global biocapacity (overshoot).

        Args:
            graph: Graph via GraphProtocol.
            services: ServicesProtocol with config, formulas, event_bus, database.
            context: Dict or TickContext with 'tick' (int) key.
        """

        # Get metabolism parameters from GameDefines
        entropy_factor = services.defines.metabolism.entropy_factor
        overshoot_threshold = services.defines.metabolism.overshoot_threshold
        hysteresis_rate = services.defines.metabolism.hysteresis_rate

        # Spec-070 FR-043: apply Sovereign-driven metabolic_impact additive
        # term to territory.habitability BEFORE the biocapacity update.
        # Read-only from SovereigntySystem's persistent_data write.
        if isinstance(context, dict):
            persistent = context.get("persistent_data", {})
        else:
            persistent = getattr(context, "persistent_data", {}) or {}
        sovereign_impact = persistent.get("balkanization.metabolic_impact_by_territory", {})
        for territory_id, impact in sovereign_impact.items():
            node = graph.get_node(territory_id)
            if node is None:
                continue
            current_hab = float(node.attributes.get("habitability", 1.0))
            new_hab = max(0.0, min(1.0, current_hab + float(impact)))
            graph.update_node(territory_id, habitability=new_hab)

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

            current = attrs.get("biocapacity", 100.0)
            max_cap = attrs.get("max_biocapacity", 100.0)

            # Hysteresis ratchet (Epoch 1 "The Earth Remembers"): extraction
            # PERMANENTLY lowers the ceiling — recovery clamps to the NEW max.
            damage = calculate_hysteresis_damage(
                extraction_intensity=attrs.get("extraction_intensity", 0.0),
                current_biocapacity=current,
                hysteresis_rate=hysteresis_rate,
            )
            new_max = max(0.0, max_cap - damage)

            # Calculate new biocapacity with clamping to the ratcheted ceiling
            new_biocapacity = max(0.0, min(new_max, current + delta))

            graph.update_node(node.id, biocapacity=new_biocapacity, max_biocapacity=new_max)

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
