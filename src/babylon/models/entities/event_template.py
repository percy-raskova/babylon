"""Event Template model for declarative game events.

An EventTemplate defines a recurring game event with:
- Preconditions: Material conditions that enable the event
- Resolutions: Deterministic outcomes based on current state
- Effects: State modifications to apply
- Narrative: Hooks for AI observer narrative generation

This implements the Paradox Pattern for events - data-driven definitions
that the EventTemplateSystem evaluates against WorldState.

Sprint: Event Template System
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

from babylon.models.enums import EdgeType, SocialRole

if TYPE_CHECKING:
    pass


class NodeFilter(BaseModel):
    """Filter to select which nodes a condition applies to.

    Used to restrict condition evaluation to specific node types,
    roles, or ID patterns. All specified filters must match (AND logic).

    Attributes:
        role: Filter by SocialRole values.
        node_type: Filter by _node_type attribute (social_class or territory).
        id_pattern: Regex pattern for node IDs.
    """

    role: list[SocialRole] | None = Field(
        default=None,
        description="Filter by SocialRole values",
    )
    node_type: Literal["social_class", "territory"] | None = Field(
        default=None,
        description="Filter by _node_type attribute",
    )
    id_pattern: str | None = Field(
        default=None,
        description="Regex pattern for node IDs",
    )

    model_config = {"extra": "forbid"}

    def matches(self, node_id: str, node_data: dict[str, Any]) -> bool:
        """Check if a node matches this filter.

        Args:
            node_id: The node's identifier.
            node_data: The node's data dictionary.

        Returns:
            True if all specified criteria match, False otherwise.
        """
        # Check node_type
        if self.node_type is not None and node_data.get("_node_type") != self.node_type:
            return False

        # Check role
        if self.role is not None:
            role = node_data.get("role")
            if role not in [r.value for r in self.role]:
                return False

        # Check id_pattern
        if self.id_pattern is not None:
            return bool(re.match(self.id_pattern, node_id))

        return True


class NodeCondition(BaseModel):
    """Condition on node attributes with optional filtering and aggregation.

    Evaluates a dot-notation path on nodes, optionally filtered by NodeFilter,
    then aggregates results and compares to threshold.

    Attributes:
        path: Dot-notation path to node attribute (e.g., ideology.agitation).
        operator: Comparison operator.
        threshold: Value to compare against.
        node_filter: Optional filter to select which nodes to check.
        aggregation: How to aggregate across matched nodes.
    """

    path: str = Field(..., description="Dot-notation path to attribute")
    operator: Literal[">=", "<=", ">", "<", "==", "!="] = Field(
        ..., description="Comparison operator"
    )
    threshold: float = Field(..., description="Value to compare against")
    node_filter: NodeFilter | None = Field(
        default=None, description="Optional filter for node selection"
    )
    aggregation: Literal["any", "all", "count", "sum", "avg", "max", "min"] = Field(
        default="any",
        description="How to aggregate across matched nodes",
    )

    model_config = {"extra": "forbid"}


class EdgeCondition(BaseModel):
    """Condition on edge types/counts with optional node filtering.

    Counts or aggregates edges of a specific type, optionally restricted
    to edges connected to nodes matching the filter.

    Attributes:
        edge_type: Type of edge to check.
        metric: What to measure (count, sum_strength, avg_strength).
        operator: Comparison operator.
        threshold: Value to compare against.
        node_filter: Optional filter to select nodes whose edges to count.
    """

    edge_type: EdgeType = Field(..., description="Type of edge to check")
    metric: Literal["count", "sum_strength", "avg_strength"] = Field(
        default="count",
        description="What to measure about the edges",
    )
    operator: Literal[">=", "<=", ">", "<", "==", "!="] = Field(
        ..., description="Comparison operator"
    )
    threshold: float = Field(..., description="Value to compare against")
    node_filter: NodeFilter | None = Field(
        default=None,
        description="Filter to select nodes whose edges to count",
    )

    model_config = {"extra": "forbid"}


class GraphCondition(BaseModel):
    """Condition on graph-level aggregate metrics.

    Evaluates aggregate properties of the entire graph rather than
    individual nodes or edges.

    Attributes:
        metric: Graph-level metric to evaluate.
        operator: Comparison operator.
        threshold: Value to compare against.
    """

    metric: Literal[
        "solidarity_density",
        "exploitation_density",
        "average_agitation",
        "average_consciousness",
        "total_wealth",
        "gini_coefficient",
    ] = Field(..., description="Graph-level metric to evaluate")
    operator: Literal[">=", "<=", ">", "<", "==", "!="] = Field(
        ..., description="Comparison operator"
    )
    threshold: float = Field(..., description="Value to compare against")

    model_config = {"extra": "forbid"}


class PreconditionSet(BaseModel):
    """A set of conditions that must be satisfied for an event to trigger.

    Combines node, edge, and graph-level conditions with specified logic.

    Attributes:
        node_conditions: Conditions on node attributes.
        edge_conditions: Conditions on edge types/counts.
        graph_conditions: Conditions on graph-level metrics.
        logic: How to combine conditions (all = AND, any = OR).
    """

    node_conditions: list[NodeCondition] = Field(default_factory=list)
    edge_conditions: list[EdgeCondition] = Field(default_factory=list)
    graph_conditions: list[GraphCondition] = Field(default_factory=list)
    logic: Literal["all", "any"] = Field(
        default="all",
        description="Logic for combining conditions: all (AND) or any (OR)",
    )

    model_config = {"extra": "forbid"}

    def is_empty(self) -> bool:
        """Check if precondition set has no conditions.

        Returns:
            True if no conditions are defined, False otherwise.
        """
        return (
            len(self.node_conditions) == 0
            and len(self.edge_conditions) == 0
            and len(self.graph_conditions) == 0
        )


class NarrativeHooks(BaseModel):
    """Hooks for AI observer narrative generation.

    Provides context for Persephone to generate narrative around events.

    Attributes:
        motif: Narrative motif key (e.g., bifurcation, betrayal).
        historical_echoes: References to historical parallels.
        flavor_text_key: Key for localized flavor text lookup.
        entity_refs: Entity IDs to reference in narrative.
    """

    motif: str | None = Field(default=None, description="Narrative motif key for AI observer")
    historical_echoes: list[str] = Field(
        default_factory=list,
        description="Historical parallel references",
    )
    flavor_text_key: str | None = Field(default=None, description="Key for localized flavor text")
    entity_refs: list[str] = Field(default_factory=list, description="Entity IDs for narrative")

    model_config = {"extra": "forbid"}


class EventEmission(BaseModel):
    """Specification for emitting an EventBus event.

    Defines what event to emit when a resolution is selected.

    Attributes:
        event_type: EventType name to emit.
        payload_template: Template for event payload with ${var} substitution.
    """

    event_type: str = Field(..., description="EventType name to emit")
    payload_template: dict[str, Any] = Field(
        default_factory=dict,
        description="Payload template with ${var} substitution",
    )

    model_config = {"extra": "forbid"}


class TemplateEffect(BaseModel):
    """Effect specification within an event template.

    Similar to the Effect model but supports ${var} substitution
    for dynamic target resolution at runtime.

    Attributes:
        target_id: Entity ID to modify (supports ${node_id} substitution).
        attribute: Attribute name to change.
        operation: How to modify the value.
        magnitude: Amount of change.
        description: Human-readable explanation.
    """

    target_id: str = Field(..., description="Entity ID to modify (${node_id} for dynamic)")
    attribute: str = Field(..., description="Attribute name to change")
    operation: Literal["increase", "decrease", "set", "multiply"] = Field(
        ..., description="Operation to perform"
    )
    magnitude: float = Field(..., description="Amount of change")
    description: str = Field(default="", description="Why this effect occurs")

    model_config = {"extra": "forbid"}

    def apply_to(self, current_value: float) -> float:
        """Calculate the new value after applying this effect.

        Args:
            current_value: The current value of the attribute.

        Returns:
            The new value after the effect is applied.
        """
        if self.operation == "increase":
            return current_value + self.magnitude
        elif self.operation == "decrease":
            return current_value - self.magnitude
        elif self.operation == "set":
            return self.magnitude
        elif self.operation == "multiply":
            return current_value * self.magnitude
        else:
            msg = f"Unknown operation: {self.operation}"
            raise ValueError(msg)


class Resolution(BaseModel):
    """A resolution path with condition and effects.

    When an EventTemplate's preconditions are met, resolutions are
    evaluated in order. The first resolution whose condition matches
    (or has no condition) is selected.

    Attributes:
        id: Resolution identifier (snake_case).
        name: Human-readable name.
        condition: Optional condition for this resolution path.
        effects: Effects to apply when this resolution is selected.
        emit_event: Optional event to emit.
        narrative: Narrative hooks specific to this resolution.
    """

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    name: str | None = Field(default=None, description="Human-readable name")
    condition: PreconditionSet | None = Field(
        default=None, description="Condition for this resolution"
    )
    effects: list[TemplateEffect] = Field(default_factory=list)
    emit_event: EventEmission | None = Field(default=None, description="Event to emit")
    narrative: NarrativeHooks | None = Field(
        default=None, description="Resolution-specific narrative"
    )

    model_config = {"extra": "forbid"}


class EventTemplate(BaseModel):
    """A declarative template for recurring game events.

    EventTemplates are the Paradox Pattern for events - data-driven
    definitions that the EventTemplateSystem evaluates against WorldState.

    When preconditions are satisfied, the first matching resolution's
    effects are applied and events are emitted for the narrative layer.

    Attributes:
        id: Unique identifier (EVT_* pattern).
        name: Human-readable name.
        description: Detailed explanation.
        category: System domain category.
        preconditions: Conditions that must be met to trigger.
        resolutions: Ordered list of resolution paths.
        narrative: Hooks for AI narrative generation.
        cooldown_ticks: Minimum ticks between activations.
        priority: Higher priority templates evaluate first.
    """

    id: str = Field(..., pattern=r"^EVT_[a-z][a-z0-9_]*$")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Detailed explanation")
    category: Literal["economic", "consciousness", "struggle", "contradiction", "territory"] = (
        Field(..., description="System domain category")
    )
    preconditions: PreconditionSet = Field(..., description="Conditions to trigger")
    resolutions: list[Resolution] = Field(..., min_length=1, description="Resolution paths")
    narrative: NarrativeHooks | None = Field(default=None, description="Narrative hooks")
    cooldown_ticks: int = Field(default=0, ge=0, description="Minimum ticks between activations")
    priority: int = Field(default=100, ge=0, description="Higher priority evaluates first")

    # Runtime state (not serialized to JSON)
    last_triggered_tick: int | None = Field(
        default=None, exclude=True, description="Last tick this was triggered"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_resolutions_have_effects_or_events(self) -> EventTemplate:
        """Ensure each resolution has at least one effect or event emission."""
        for resolution in self.resolutions:
            if not resolution.effects and resolution.emit_event is None:
                msg = f"Resolution '{resolution.id}' must have at least one effect or emit_event"
                raise ValueError(msg)
        return self

    def is_on_cooldown(self, current_tick: int) -> bool:
        """Check if this template is on cooldown.

        Args:
            current_tick: The current simulation tick.

        Returns:
            True if still on cooldown, False otherwise.
        """
        if self.last_triggered_tick is None:
            return False
        return current_tick - self.last_triggered_tick < self.cooldown_ticks

    def mark_triggered(self, tick: int) -> None:
        """Mark this template as having been triggered.

        Args:
            tick: The tick at which this was triggered.
        """
        self.last_triggered_tick = tick
