"""TDD RED phase: Tests for the SublationRule abstraction.

SublationRule formalizes the Aufhebung lifecycle as a composable,
reusable pattern:

1. **Threshold predicate**: when does sublation trigger?
2. **Successor factory**: what gets created?
3. **Governance hook**: how does the successor govern the sublated?

This replaces the ad-hoc sublate() overrides scattered across 5+
dialectics with a declarative, testable, composable structure.

Validates:
- SublationRule is a composable protocol/dataclass
- threshold_met(dialectic) returns bool
- create_successor(dialectic) returns the successor with parent_id wired
- govern(dialectic, successor, world) returns a governed delta
- Dialectic with a SublationRule attached uses it in sublate()
- tick() still handles sublation events correctly
- A dialectic can declare multiple SublationRules (phase transitions)
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.dialectics.base import (
    Dialectic,
    EmptyPole,
    TickInputs,
    WorldView,
)
from babylon.engine.dialectics.sublation import SublationRule
from babylon.engine.dialectics.tick import tick
from babylon.engine.dialectics.world import World

# ===========================================================================
# Concrete test dialectics
# ===========================================================================


class _CrisisPole(EmptyPole):
    """Marker pole for a crisis successor."""

    pass


class _TestDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Test dialectic that uses SublationRule."""

    type_tag: str = "_TestDialectic"

    sublation_rules: tuple[SublationRule, ...] = ()

    def step(self, inputs: TickInputs, world: WorldView) -> _TestDialectic:
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Delegate to the first matching SublationRule."""
        for rule in self.sublation_rules:
            if rule.threshold_met(self):
                return rule.create_successor(self)
        return None


class _CrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Crisis dialectic produced by sublation."""

    type_tag: str = "_CrisisDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> _CrisisDialectic:
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})


class _HigherDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Higher-order dialectic produced by sublation (like Party)."""

    type_tag: str = "_HigherDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> _HigherDialectic:
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        obs = super().observe()
        obs["governance_directive"] = 0.5  # example directive
        return obs


# ===========================================================================
# SublationRule construction
# ===========================================================================


class TestSublationRuleConstruction:
    """SublationRule can be constructed with threshold and factory."""

    def test_construct_with_weight_threshold(self) -> None:
        """SublationRule with a weight threshold predicate."""
        rule = SublationRule(
            name="crisis_threshold",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        assert rule.name == "crisis_threshold"

    def test_construct_with_custom_predicate(self) -> None:
        """SublationRule with a custom predicate (not just weight)."""
        rule = SublationRule(
            name="custom_condition",
            threshold=lambda d: d.tick_updated > 10,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        assert rule.name == "custom_condition"


# ===========================================================================
# threshold_met
# ===========================================================================


class TestSublationThreshold:
    """SublationRule.threshold_met() evaluates the predicate."""

    def test_below_threshold_returns_false(self) -> None:
        rule = SublationRule(
            name="weight_gate",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert rule.threshold_met(d) is False

    def test_above_threshold_returns_true(self) -> None:
        rule = SublationRule(
            name="weight_gate",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
        )
        assert rule.threshold_met(d) is True


# ===========================================================================
# create_successor
# ===========================================================================


class TestSublationSuccessorFactory:
    """SublationRule.create_successor() produces the successor."""

    def test_successor_has_parent_id(self) -> None:
        rule = SublationRule(
            name="crisis",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
        )
        successor = rule.create_successor(d)
        assert successor.parent_id == d.id

    def test_successor_type_matches(self) -> None:
        rule = SublationRule(
            name="crisis",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
        )
        successor = rule.create_successor(d)
        assert isinstance(successor, _CrisisDialectic)
        assert successor.type_tag == "_CrisisDialectic"


# ===========================================================================
# Dialectic delegates to SublationRule in sublate()
# ===========================================================================


class TestDialecticDelegatesToRule:
    """A Dialectic with SublationRules delegates sublate() to them."""

    def test_no_rules_returns_none(self) -> None:
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
            sublation_rules=(),
        )
        assert d.sublate() is None

    def test_rule_triggers_sublation(self) -> None:
        rule = SublationRule(
            name="crisis",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
            sublation_rules=(rule,),
        )
        successor = d.sublate()
        assert successor is not None
        assert successor.parent_id == d.id

    def test_first_matching_rule_wins(self) -> None:
        """When multiple rules could trigger, the first match wins."""
        rule_a = SublationRule(
            name="crisis_a",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=-0.5,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        rule_b = SublationRule(
            name="higher_b",
            threshold=lambda d: d.weight >= 0.5,
            successor_type="_HigherDialectic",
            successor_factory=lambda d: _HigherDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
            sublation_rules=(rule_a, rule_b),
        )
        successor = d.sublate()
        assert successor is not None
        # rule_a should win (it's first and threshold met)
        assert isinstance(successor, _CrisisDialectic)
        assert successor.weight == pytest.approx(-0.5)


# ===========================================================================
# Integration: tick() with SublationRule
# ===========================================================================


class TestSublationRuleInTick:
    """SublationRules work correctly through the tick() machinery."""

    def test_tick_triggers_sublation_via_rule(self) -> None:
        rule = SublationRule(
            name="crisis",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
            sublation_rules=(rule,),
        )
        w = World(tick=0, dialectics={d.id: d})
        w1, events = tick(w, [])

        sublation_events = [e for e in events if e.event_type == "sublation"]
        assert len(sublation_events) == 1
        assert sublation_events[0].payload["successor_type"] == "_CrisisDialectic"

    def test_sublated_dialectic_still_stepped_with_rule(self) -> None:
        rule = SublationRule(
            name="crisis",
            threshold=lambda d: d.weight >= 0.8,
            successor_type="_CrisisDialectic",
            successor_factory=lambda d: _CrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=d.id,
                tick_created=d.tick_updated,
                tick_updated=d.tick_updated,
            ),
        )
        d = _TestDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.9,
            tick_created=0,
            tick_updated=0,
            sublation_rules=(rule,),
        )
        w = World(tick=0, dialectics={d.id: d})
        w1, _ = tick(w, [])
        w2, _ = tick(w1, [])

        # Sublated dialectic still stepped
        assert w2.dialectics[d.id].tick_updated == 2
