"""Core data types for the OODA Loop System (Feature 032).

All models are frozen (immutable) Pydantic BaseModels. These types are
computed per-tick and never stored permanently — they flow through the
turn resolution pipeline and are discarded after Layer 3 propagation.

See Also:
    ``specs/032-ooda-loop-system/data-model.md``: Entity definitions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import ActionType, DecisionMode
from babylon.organizations.types import ConsciousnessDelta


class OODAProfile(BaseModel):
    """OODA loop profile stored on organization graph nodes.

    Determines how quickly an organization can cycle through
    Observe-Orient-Decide-Act, how many actions it can take per tick,
    and the effectiveness-breadth tradeoff.

    Attributes:
        sensor_latency: Ticks of observation delay [0, 10].
        ideological_coherence: How unified the org's worldview is [0, 1].
        analytical_capacity: Ability to process information [0, 1].
        decision_mode: How decisions are made (affects cycle time).
        bureaucratic_depth: Layers of bureaucracy [0, 1].
        action_points: Actions available per tick [0, 20].
        coordination_range: Distinct territories targetable per tick [0, 100].
        autonomy: Effectiveness-breadth tradeoff [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    sensor_latency: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Ticks of observation delay",
    )
    ideological_coherence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How unified the org's worldview is",
    )
    analytical_capacity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Ability to process information",
    )
    decision_mode: DecisionMode = Field(
        default=DecisionMode.DEMOCRATIC,
        description="How decisions are made",
    )
    bureaucratic_depth: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Layers of bureaucracy",
    )
    action_points: int = Field(
        default=3,
        ge=0,
        le=20,
        description="Actions available per tick",
    )
    coordination_range: int = Field(
        default=1,
        ge=0,
        le=100,
        description="Distinct territories targetable per tick",
    )
    autonomy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Effectiveness-breadth tradeoff",
    )


class Action(BaseModel):
    """A single organizational action for a tick.

    Attributes:
        org_id: Acting organization ID.
        action_type: What action to perform.
        target_id: Target community, organization, or territory ID.
        action_point_cost: AP cost after modifiers (minimum 1).
        cadre_labor_cost: Forward-compatible: cadre hours required.
        sympathizer_labor_cost: Forward-compatible: sympathizer hours.
        budget_cost: Forward-compatible: monetary cost.
        params: Verb-specific parameters carried from the web bridge's
            ``params_json`` (e.g. ``transfer_amount`` for AID, ``mode``
            for REPRODUCE/MOVE, ``scan_type`` for INVESTIGATE). Consumed
            by the verb resolvers; empty for engine-internal NPC actions.
    """

    model_config = ConfigDict(frozen=True)

    org_id: str = Field(
        min_length=1,
        description="Acting organization ID",
    )
    action_type: ActionType = Field(
        description="What action to perform",
    )
    target_id: str = Field(
        min_length=1,
        description="Target community, organization, or territory ID",
    )
    action_point_cost: int = Field(
        default=1,
        ge=1,
        description="AP cost after modifiers",
    )
    cadre_labor_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Forward-compatible: cadre hours required",
    )
    sympathizer_labor_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Forward-compatible: sympathizer hours",
    )
    budget_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Forward-compatible: monetary cost",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Verb-specific parameters (bridge params_json passthrough)",
    )


class ActionResult(BaseModel):
    """Outcome of executing one action.

    Attributes:
        action: The action that was executed.
        success: Whether the action succeeded.
        consciousness_delta: Consciousness effect on target (None if no effect).
        direct_effects: Action-type-specific effects.
        events_generated: EventType values emitted.
        failure_reason: Why the action failed (None if success).
    """

    model_config = ConfigDict(frozen=True)

    action: Action = Field(
        description="The action that was executed",
    )
    success: bool = Field(
        description="Whether the action succeeded",
    )
    consciousness_delta: ConsciousnessDelta | None = Field(
        default=None,
        description="Consciousness effect on target community",
    )
    direct_effects: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-type-specific effects",
    )
    events_generated: list[str] = Field(
        default_factory=list,
        description="EventType values emitted",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Why the action failed (None if success)",
    )


class InitiativeScore(BaseModel):
    """Computed per-tick ordering value for an organization.

    Invariant: score = speed + institutional + counterintel + embeddedness + momentum.

    Attributes:
        org_id: Organization ID.
        score: Composite initiative score.
        speed_component: Contribution from OODA cycle time.
        institutional_component: Institutional bonus (state advantage).
        counterintel_component: Counter-intelligence capability.
        embeddedness_component: Community embeddedness.
        momentum_component: Recent success momentum.
    """

    model_config = ConfigDict(frozen=True)

    org_id: str = Field(
        min_length=1,
        description="Organization ID",
    )
    score: float = Field(
        description="Composite initiative score",
    )
    speed_component: float = Field(
        description="Contribution from OODA cycle time",
    )
    institutional_component: float = Field(
        description="Institutional bonus (state advantage)",
    )
    counterintel_component: float = Field(
        description="Counter-intelligence capability",
    )
    embeddedness_component: float = Field(
        description="Community embeddedness",
    )
    momentum_component: float = Field(
        description="Recent success momentum",
    )


class ActionCostModifier(BaseModel):
    """Cost adjustment for an action based on org-community relationship.

    Attributes:
        base_cost: Action type's default AP cost.
        modifier: Multiplier (< 1.0 = discount, > 1.0 = surcharge).
        effective_cost: ceil(base_cost * modifier), minimum 1.
        reason: Human-readable explanation.
    """

    model_config = ConfigDict(frozen=True)

    base_cost: int = Field(
        ge=1,
        description="Action type's default AP cost",
    )
    modifier: float = Field(
        description="Multiplier (< 1.0 = discount, > 1.0 = surcharge)",
    )
    effective_cost: int = Field(
        ge=1,
        description="ceil(base_cost * modifier), minimum 1",
    )
    reason: str = Field(
        description="Human-readable explanation",
    )


class TurnResolution(BaseModel):
    """Complete processing of one tick's OODA resolution.

    Attributes:
        tick: Which tick was resolved.
        layer0_results: Automatic metabolism results.
        initiative_order: Sorted initiative scores (descending).
        action_phase_results: All action results in execution order.
        layer3_effects: Aggregated consequence propagation.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(
        ge=0,
        description="Which tick was resolved",
    )
    layer0_results: list[ActionResult] = Field(
        default_factory=list,
        description="Automatic metabolism results",
    )
    initiative_order: list[InitiativeScore] = Field(
        default_factory=list,
        description="Sorted initiative scores (descending)",
    )
    action_phase_results: list[ActionResult] = Field(
        default_factory=list,
        description="All action results in execution order",
    )
    layer3_effects: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated consequence propagation",
    )
