"""Event Template System - Data-Driven Event Evaluation.

This system evaluates EventTemplates against the current WorldState
and applies matching resolutions. It runs LAST in the system order
to evaluate against the final tick state.

Sprint: Event Template System
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.engine.event_evaluator import (
    evaluate_template,
    get_matching_nodes_for_resolution,
)
from babylon.engine.systems.protocol import ContextType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer
    from babylon.models.entities.event_template import (
        EventTemplate,
        Resolution,
        TemplateEffect,
    )

logger = logging.getLogger(__name__)


class EventTemplateSystem:
    """System that evaluates and applies EventTemplates.

    EventTemplates are data-driven definitions of recurring game events.
    This system evaluates templates against the current WorldState graph,
    selects the appropriate resolution, and applies effects.

    The system runs after all other systems to evaluate against the
    final state of each tick.

    Attributes:
        name: The identifier of the system.
    """

    name = "Event Template"

    def __init__(self, templates: list[EventTemplate] | None = None) -> None:
        """Initialize with optional list of templates.

        Args:
            templates: Templates to evaluate. If None, starts with empty list.
        """
        self._templates: list[EventTemplate] = templates or []

    def add_template(self, template: EventTemplate) -> None:
        """Add a template to the system.

        Args:
            template: The EventTemplate to add.
        """
        self._templates.append(template)

    def add_templates(self, templates: list[EventTemplate]) -> None:
        """Add multiple templates to the system.

        Args:
            templates: List of EventTemplates to add.
        """
        self._templates.extend(templates)

    @property
    def templates(self) -> list[EventTemplate]:
        """Get the current list of templates.

        Returns:
            List of EventTemplates registered with this system.
        """
        return list(self._templates)

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Evaluate templates and apply matching resolutions.

        Args:
            graph: Mutable NetworkX graph representing WorldState.
            services: ServiceContainer with config, formulas, event_bus, database.
            context: TickContext or dict with 'tick' (int) and optional metadata.
        """
        # Extract tick from context
        tick = context.tick if hasattr(context, "tick") else context.get("tick", 0)

        # Sort by priority (higher first)
        sorted_templates = sorted(
            self._templates,
            key=lambda t: t.priority,
            reverse=True,
        )

        for template in sorted_templates:
            resolution = evaluate_template(template, graph, tick)
            if resolution is not None:
                self._apply_resolution(template, resolution, graph, services, tick)
                template.mark_triggered(tick)
                logger.debug(
                    "Template %s triggered resolution %s at tick %d",
                    template.id,
                    resolution.id,
                    tick,
                )

    def _apply_resolution(
        self,
        template: EventTemplate,
        resolution: Resolution,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        tick: int,
    ) -> None:
        """Apply effects and emit events for a resolution.

        Args:
            template: The triggered EventTemplate.
            resolution: The selected Resolution.
            graph: NetworkX graph to modify.
            services: ServiceContainer with event_bus.
            tick: Current simulation tick.
        """
        # Get matching nodes for ${node_id} substitution
        matching_nodes = get_matching_nodes_for_resolution(template, graph)

        # Apply effects
        for effect in resolution.effects:
            self._apply_effect(effect, graph, matching_nodes)

        # Emit event if specified
        if resolution.emit_event is not None:
            event_type = resolution.emit_event.event_type
            payload = dict(resolution.emit_event.payload_template)

            # Add template metadata to payload
            payload["template_id"] = template.id
            payload["resolution_id"] = resolution.id
            payload["matching_nodes"] = matching_nodes

            services.event_bus.publish(
                Event(
                    type=event_type,
                    tick=tick,
                    payload=payload,
                )
            )

    def _apply_effect(
        self,
        effect: TemplateEffect,
        graph: nx.DiGraph[str],
        matching_nodes: list[str],
    ) -> None:
        """Apply a single effect to the graph.

        Args:
            effect: The TemplateEffect to apply.
            graph: NetworkX graph to modify.
            matching_nodes: Nodes matching template preconditions.
        """
        # Handle ${node_id} substitution
        if effect.target_id == "${node_id}":
            # Apply to all matching nodes
            for node_id in matching_nodes:
                self._apply_effect_to_node(effect, graph, node_id)
        else:
            # Apply to specific target
            self._apply_effect_to_node(effect, graph, effect.target_id)

    def _apply_effect_to_node(
        self,
        effect: TemplateEffect,
        graph: nx.DiGraph[str],
        node_id: str,
    ) -> None:
        """Apply an effect to a specific node.

        Args:
            effect: The TemplateEffect to apply.
            graph: NetworkX graph containing the node.
            node_id: ID of the node to modify.
        """
        if node_id not in graph.nodes:
            logger.warning("Effect target node %s not found in graph", node_id)
            return

        node_data = graph.nodes[node_id]

        # Handle nested attribute paths (e.g., ideology.class_consciousness)
        path_parts = effect.attribute.split(".")

        if len(path_parts) == 1:
            # Simple attribute
            current = node_data.get(effect.attribute, 0.0)
            new_value = effect.apply_to(float(current))
            graph.nodes[node_id][effect.attribute] = new_value
        else:
            # Nested attribute - navigate to parent, then modify leaf
            parent_path = ".".join(path_parts[:-1])
            leaf_key = path_parts[-1]

            # Get or create parent dict
            parent = self._get_or_create_nested_dict(node_data, parent_path)
            if parent is not None:
                current = parent.get(leaf_key, 0.0)
                new_value = effect.apply_to(float(current))
                parent[leaf_key] = new_value

    def _get_or_create_nested_dict(
        self,
        data: dict[str, Any],
        path: str,
    ) -> dict[str, Any] | None:
        """Navigate to a nested dict, creating intermediate dicts if needed.

        Args:
            data: Root dictionary.
            path: Dot-notation path to the nested dict.

        Returns:
            The nested dictionary, or None if path is invalid.
        """
        keys = path.split(".")
        current: Any = data

        for key in keys:
            if isinstance(current, dict):
                if key not in current:
                    current[key] = {}
                current = current[key]
            else:
                return None

        return current if isinstance(current, dict) else None
