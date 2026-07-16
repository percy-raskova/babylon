"""Mutation-killing tests for EventTemplateSystem.

Targets 158 untested mutations in event_template.py covering:
- System initialization and template management
- step() evaluation with priority ordering and context types
- _apply_resolution with effect application and event emission
- _apply_effect with ${node_id} substitution vs specific targets
- _apply_effect_to_node for simple/nested attributes and missing nodes
- _get_or_create_nested_dict navigation and creation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.event_template import EventTemplateSystem
from babylon.kernel.event_bus import Event, EventBus
from babylon.models.entities.event_template import (
    EventEmission,
    EventTemplate,
    NodeCondition,
    PreconditionSet,
    Resolution,
    TemplateEffect,
)
from babylon.topology.graph import BabylonGraph

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_effect(
    target_id: str = "worker",
    attribute: str = "wealth",
    operation: str = "increase",
    magnitude: float = 10.0,
) -> TemplateEffect:
    return TemplateEffect(
        target_id=target_id,
        attribute=attribute,
        operation=operation,
        magnitude=magnitude,
    )


def _make_resolution(
    resolution_id: str = "default_res",
    effects: list[TemplateEffect] | None = None,
    emit_event: EventEmission | None = None,
    condition: PreconditionSet | None = None,
) -> Resolution:
    return Resolution(
        id=resolution_id,
        effects=effects or [_make_effect()],
        emit_event=emit_event,
        condition=condition,
    )


def _make_template(
    template_id: str = "EVT_test",
    priority: int = 100,
    cooldown_ticks: int = 0,
    preconditions: PreconditionSet | None = None,
    resolutions: list[Resolution] | None = None,
) -> EventTemplate:
    return EventTemplate(
        id=template_id,
        name="Test Template",
        category="economic",
        preconditions=preconditions or PreconditionSet(),
        resolutions=resolutions or [_make_resolution()],
        priority=priority,
        cooldown_ticks=cooldown_ticks,
    )


def _make_graph(*nodes: tuple[str, dict[str, Any]]) -> BabylonGraph:
    g = BabylonGraph()
    for node_id, data in nodes:
        g.add_node(node_id, **data)
    return g


# ---------------------------------------------------------------------------
# Init & template management
# ---------------------------------------------------------------------------


class TestEventTemplateSystemInit:
    """Constructor and template management methods."""

    def test_init_no_templates(self) -> None:
        """Default constructor starts with empty template list."""
        system = EventTemplateSystem()
        assert system.templates == []

    def test_init_with_templates(self) -> None:
        """Constructor accepts a template list."""
        t = _make_template()
        system = EventTemplateSystem(templates=[t])
        assert len(system.templates) == 1
        assert system.templates[0].id == "EVT_test"

    def test_init_none_treated_as_empty(self) -> None:
        """Passing None explicitly gives empty list (not error)."""
        system = EventTemplateSystem(templates=None)
        assert system.templates == []

    def test_add_template(self) -> None:
        """add_template appends to internal list."""
        system = EventTemplateSystem()
        t = _make_template()
        system.add_template(t)
        assert len(system.templates) == 1

    def test_add_templates_extends(self) -> None:
        """add_templates extends (not replaces) internal list."""
        system = EventTemplateSystem(templates=[_make_template("EVT_first")])
        system.add_templates([_make_template("EVT_second"), _make_template("EVT_third")])
        assert len(system.templates) == 3

    def test_templates_property_returns_copy(self) -> None:
        """templates property returns a copy — mutating it doesn't affect internals."""
        system = EventTemplateSystem(templates=[_make_template()])
        copy = system.templates
        copy.clear()
        assert len(system.templates) == 1

    def test_name_attribute(self) -> None:
        """System has correct name identifier."""
        system = EventTemplateSystem()
        assert system.name == "Event Template"


# ---------------------------------------------------------------------------
# step() — template evaluation
# ---------------------------------------------------------------------------


class TestStepEvaluation:
    """step() evaluates templates in priority order."""

    def test_step_dict_context(self) -> None:
        """step() accepts dict context with 'tick' key."""
        graph = _make_graph(("worker", {"wealth": 5.0}))
        system = EventTemplateSystem(templates=[_make_template()])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == 15.0

    def test_step_tick_context_object(self) -> None:
        """step() accepts object context with .tick attribute."""
        graph = _make_graph(("worker", {"wealth": 5.0}))
        system = EventTemplateSystem(templates=[_make_template()])
        services = ServiceContainer.create()

        ctx = MagicMock()
        ctx.tick = 1
        system.step(graph, services, ctx)

        assert graph.nodes["worker"]["wealth"] == 15.0

    def test_step_dict_context_missing_tick_defaults_to_zero(self) -> None:
        """dict context without 'tick' defaults to 0."""
        graph = _make_graph(("worker", {"wealth": 0.0}))
        system = EventTemplateSystem(templates=[_make_template()])
        services = ServiceContainer.create()

        system.step(graph, services, {})

        assert graph.nodes["worker"]["wealth"] == 10.0

    def test_step_priority_ordering(self) -> None:
        """Higher priority templates evaluate first."""
        # High-priority sets wealth to 100, low-priority increases by 10
        high = _make_template(
            template_id="EVT_high",
            priority=200,
            resolutions=[
                _make_resolution(effects=[_make_effect(operation="set", magnitude=100.0)])
            ],
        )
        low = _make_template(
            template_id="EVT_low",
            priority=50,
            resolutions=[
                _make_resolution(
                    resolution_id="low_res",
                    effects=[_make_effect(operation="increase", magnitude=10.0)],
                )
            ],
        )

        graph = _make_graph(("worker", {"wealth": 5.0}))
        system = EventTemplateSystem(templates=[low, high])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        # High runs first (set 100), then low (increase 10) → 110
        assert graph.nodes["worker"]["wealth"] == pytest.approx(110.0)

    def test_step_marks_triggered(self) -> None:
        """step() marks triggered templates with the current tick.

        Spec 056 / III.7: EventTemplate is frozen; mark_triggered returns
        a new instance. Read from system.templates (the post-step list).
        """
        t = _make_template()
        graph = _make_graph(("worker", {"wealth": 0.0}))
        system = EventTemplateSystem(templates=[t])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 5})

        assert system.templates[0].last_triggered_tick == 5

    def test_step_respects_cooldown(self) -> None:
        """Template on cooldown is skipped.

        Spec 056 / III.7: mark_triggered now returns a new instance;
        rebind the local variable before passing to the system.
        """
        t = _make_template(cooldown_ticks=3)
        t = t.mark_triggered(1)

        graph = _make_graph(("worker", {"wealth": 0.0}))
        system = EventTemplateSystem(templates=[t])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 3})

        # tick 3 - last_triggered 1 = 2 < 3 (cooldown), so not triggered
        assert graph.nodes["worker"]["wealth"] == 0.0

    def test_step_triggers_after_cooldown(self) -> None:
        """Template triggers after cooldown expires."""
        t = _make_template(cooldown_ticks=3)
        t = t.mark_triggered(1)

        graph = _make_graph(("worker", {"wealth": 0.0}))
        system = EventTemplateSystem(templates=[t])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 4})

        # tick 4 - last_triggered 1 = 3 >= 3, cooldown expired
        assert graph.nodes["worker"]["wealth"] == 10.0

    def test_step_no_templates(self) -> None:
        """step() with empty template list is a no-op."""
        graph = _make_graph(("worker", {"wealth": 5.0}))
        system = EventTemplateSystem()
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == 5.0

    def test_step_precondition_not_met_skips(self) -> None:
        """Template with unmet preconditions is not triggered."""
        preconditions = PreconditionSet(
            node_conditions=[NodeCondition(path="wealth", operator=">=", threshold=1000.0)]
        )
        t = _make_template(preconditions=preconditions)

        graph = _make_graph(("worker", {"wealth": 5.0}))
        system = EventTemplateSystem(templates=[t])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == 5.0


# ---------------------------------------------------------------------------
# _apply_resolution — effects + event emission
# ---------------------------------------------------------------------------


class TestApplyResolution:
    """_apply_resolution applies effects and emits events."""

    def test_emits_event_with_metadata(self) -> None:
        """Resolution with emit_event publishes event to bus."""
        event_bus = EventBus()
        received: list[Event] = []
        event_bus.subscribe("TEST_EVENT", received.append)

        services = ServiceContainer.create()
        services.event_bus = event_bus

        emission = EventEmission(
            event_type="TEST_EVENT",
            payload_template={"key": "value"},
        )
        resolution = _make_resolution(emit_event=emission)
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 0.0}))
        system = EventTemplateSystem(templates=[template])
        system.step(graph, services, {"tick": 7})

        assert len(received) == 1
        assert received[0].type == "TEST_EVENT"
        assert received[0].tick == 7
        assert received[0].payload["template_id"] == "EVT_test"
        assert received[0].payload["resolution_id"] == "default_res"
        assert received[0].payload["key"] == "value"

    def test_no_event_emission_when_none(self) -> None:
        """Resolution without emit_event does not emit."""
        event_bus = EventBus()
        received: list[Event] = []
        event_bus.subscribe("TEST_EVENT", received.append)

        services = ServiceContainer.create()
        services.event_bus = event_bus

        resolution = _make_resolution(emit_event=None)
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 0.0}))
        system = EventTemplateSystem(templates=[template])
        system.step(graph, services, {"tick": 1})

        assert len(received) == 0

    def test_multiple_effects_applied(self) -> None:
        """Resolution with multiple effects applies all of them."""
        effects = [
            _make_effect(
                target_id="worker", attribute="wealth", operation="increase", magnitude=5.0
            ),
            _make_effect(target_id="worker", attribute="agitation", operation="set", magnitude=0.9),
        ]
        resolution = _make_resolution(effects=effects)
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0, "agitation": 0.1}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == pytest.approx(15.0)
        assert graph.nodes["worker"]["agitation"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# _apply_effect — target resolution
# ---------------------------------------------------------------------------


class TestApplyEffect:
    """_apply_effect resolves ${node_id} vs specific target IDs."""

    def test_node_id_substitution(self) -> None:
        """${node_id} applies effect to all matching nodes."""
        # Precondition: wealth >= 0 (matches both workers)
        preconditions = PreconditionSet(
            node_conditions=[NodeCondition(path="wealth", operator=">=", threshold=0.0)]
        )
        effect = _make_effect(
            target_id="${node_id}",
            attribute="wealth",
            operation="increase",
            magnitude=5.0,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(preconditions=preconditions, resolutions=[resolution])

        graph = _make_graph(
            ("worker_a", {"wealth": 10.0}),
            ("worker_b", {"wealth": 20.0}),
        )
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker_a"]["wealth"] == pytest.approx(15.0)
        assert graph.nodes["worker_b"]["wealth"] == pytest.approx(25.0)

    def test_specific_target_id(self) -> None:
        """Specific target_id applies effect only to that node."""
        effect = _make_effect(
            target_id="worker_a",
            attribute="wealth",
            operation="increase",
            magnitude=5.0,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(
            ("worker_a", {"wealth": 10.0}),
            ("worker_b", {"wealth": 20.0}),
        )
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker_a"]["wealth"] == pytest.approx(15.0)
        assert graph.nodes["worker_b"]["wealth"] == pytest.approx(20.0)

    def test_missing_node_is_no_op(self) -> None:
        """Effect targeting a nonexistent node does nothing (no crash)."""
        effect = _make_effect(
            target_id="nonexistent",
            attribute="wealth",
            operation="set",
            magnitude=999.0,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == 10.0


# ---------------------------------------------------------------------------
# _apply_effect_to_node — attribute operations
# ---------------------------------------------------------------------------


class TestApplyEffectToNode:
    """Tests for attribute operations (increase, decrease, set, multiply)."""

    def test_increase_operation(self) -> None:
        """'increase' adds magnitude to current value."""
        effect = _make_effect(operation="increase", magnitude=7.5)
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == pytest.approx(17.5)

    def test_decrease_operation(self) -> None:
        """'decrease' subtracts magnitude from current value."""
        effect = _make_effect(operation="decrease", magnitude=3.0)
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == pytest.approx(7.0)

    def test_set_operation(self) -> None:
        """'set' replaces current value with magnitude."""
        effect = _make_effect(operation="set", magnitude=42.0)
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == pytest.approx(42.0)

    def test_multiply_operation(self) -> None:
        """'multiply' multiplies current value by magnitude."""
        effect = _make_effect(operation="multiply", magnitude=2.5)
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["wealth"] == pytest.approx(25.0)

    def test_default_value_zero_when_attribute_missing(self) -> None:
        """Missing attribute defaults to 0.0 before applying effect."""
        effect = _make_effect(
            target_id="worker",
            attribute="agitation",
            operation="increase",
            magnitude=0.5,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["agitation"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Nested attribute paths
# ---------------------------------------------------------------------------


class TestNestedAttributePaths:
    """Tests for dot-notation nested attribute handling."""

    def test_nested_attribute_modify(self) -> None:
        """Nested path 'ideology.agitation' modifies the correct leaf."""
        effect = _make_effect(
            target_id="worker",
            attribute="ideology.agitation",
            operation="increase",
            magnitude=0.3,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"ideology": {"agitation": 0.5}}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["ideology"]["agitation"] == pytest.approx(0.8)

    def test_nested_attribute_creates_missing_parent(self) -> None:
        """Missing intermediate dicts are created automatically."""
        effect = _make_effect(
            target_id="worker",
            attribute="ideology.agitation",
            operation="set",
            magnitude=0.9,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["ideology"]["agitation"] == pytest.approx(0.9)

    def test_deep_nested_path(self) -> None:
        """Three-level nested path works correctly."""
        effect = _make_effect(
            target_id="worker",
            attribute="state.mood.anger",
            operation="set",
            magnitude=0.7,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"state": {"mood": {"anger": 0.1}}}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["state"]["mood"]["anger"] == pytest.approx(0.7)

    def test_nested_path_non_dict_parent_is_noop(self) -> None:
        """If intermediate path is not a dict, effect is silently skipped."""
        effect = _make_effect(
            target_id="worker",
            attribute="wealth.sub_field",
            operation="set",
            magnitude=999.0,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        # wealth is a float, not a dict
        graph = _make_graph(("worker", {"wealth": 10.0}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        # wealth remains unchanged — sub_field can't be set on a float
        assert graph.nodes["worker"]["wealth"] == 10.0

    def test_nested_leaf_defaults_to_zero(self) -> None:
        """Missing leaf in existing parent dict defaults to 0.0."""
        effect = _make_effect(
            target_id="worker",
            attribute="ideology.new_field",
            operation="increase",
            magnitude=0.4,
        )
        resolution = _make_resolution(effects=[effect])
        template = _make_template(resolutions=[resolution])

        graph = _make_graph(("worker", {"ideology": {"agitation": 0.5}}))
        system = EventTemplateSystem(templates=[template])
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker"]["ideology"]["new_field"] == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# TemplateEffect.apply_to — pure function
# ---------------------------------------------------------------------------


class TestTemplateEffectApplyTo:
    """Direct tests for TemplateEffect.apply_to method."""

    def test_increase(self) -> None:
        effect = _make_effect(operation="increase", magnitude=5.0)
        assert effect.apply_to(10.0) == pytest.approx(15.0)

    def test_decrease(self) -> None:
        effect = _make_effect(operation="decrease", magnitude=3.0)
        assert effect.apply_to(10.0) == pytest.approx(7.0)

    def test_set(self) -> None:
        effect = _make_effect(operation="set", magnitude=42.0)
        assert effect.apply_to(10.0) == pytest.approx(42.0)

    def test_multiply(self) -> None:
        effect = _make_effect(operation="multiply", magnitude=2.0)
        assert effect.apply_to(10.0) == pytest.approx(20.0)

    def test_multiply_by_zero(self) -> None:
        effect = _make_effect(operation="multiply", magnitude=0.0)
        assert effect.apply_to(10.0) == pytest.approx(0.0)

    def test_decrease_below_zero(self) -> None:
        effect = _make_effect(operation="decrease", magnitude=20.0)
        assert effect.apply_to(10.0) == pytest.approx(-10.0)
