"""Tests for OODA profile constraints (Feature 032).

Verifies AP enforcement, coordination range limits, and
autonomy-effectiveness tradeoff.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType
from babylon.ooda.constraints import (
    apply_autonomy_modifier,
    enforce_action_points,
    enforce_coordination_range,
)
from babylon.ooda.types import Action, OODAProfile


def _make_action(target: str = "t1", cost: int = 1) -> Action:
    return Action(
        org_id="org_1",
        action_type=ActionType.EDUCATE,
        target_id=target,
        action_point_cost=cost,
    )


class TestEnforceActionPoints:
    """Greedy AP acceptance."""

    def test_all_accepted_within_budget(self) -> None:
        profile = OODAProfile(action_points=5)
        actions = [_make_action(cost=1), _make_action(cost=2)]
        accepted, rejected = enforce_action_points(actions, profile)
        assert len(accepted) == 2
        assert len(rejected) == 0

    def test_fourth_action_rejected(self) -> None:
        """4 actions with 3 AP: 4th rejected."""
        profile = OODAProfile(action_points=3)
        actions = [_make_action(cost=1) for _ in range(4)]
        accepted, rejected = enforce_action_points(actions, profile)
        assert len(accepted) == 3
        assert len(rejected) == 1
        assert rejected[0].success is False
        assert "Insufficient AP" in (rejected[0].failure_reason or "")

    def test_zero_ap_rejects_all(self) -> None:
        profile = OODAProfile(action_points=0)
        actions = [_make_action(cost=1)]
        accepted, rejected = enforce_action_points(actions, profile)
        assert len(accepted) == 0
        assert len(rejected) == 1

    def test_expensive_action_skipped_cheap_accepted(self) -> None:
        """Greedy: expensive first, cheap second — expensive rejected, cheap still accepted."""
        profile = OODAProfile(action_points=2)
        actions = [_make_action(cost=3), _make_action(cost=1)]
        accepted, rejected = enforce_action_points(actions, profile)
        assert len(accepted) == 1
        assert accepted[0].action_point_cost == 1
        assert len(rejected) == 1

    def test_exact_budget(self) -> None:
        profile = OODAProfile(action_points=3)
        actions = [_make_action(cost=3)]
        accepted, rejected = enforce_action_points(actions, profile)
        assert len(accepted) == 1
        assert len(rejected) == 0

    def test_empty_actions(self) -> None:
        profile = OODAProfile(action_points=5)
        accepted, rejected = enforce_action_points([], profile)
        assert accepted == []
        assert rejected == []


class TestEnforceCoordinationRange:
    """Coordination range limits distinct target territories."""

    def test_within_range(self) -> None:
        profile = OODAProfile(coordination_range=3)
        actions = [_make_action(target="t1"), _make_action(target="t2")]
        accepted, rejected = enforce_coordination_range(actions, profile)
        assert len(accepted) == 2
        assert len(rejected) == 0

    def test_out_of_range_rejected(self) -> None:
        """Range 1 with 2 distinct targets: second rejected."""
        profile = OODAProfile(coordination_range=1)
        actions = [_make_action(target="t1"), _make_action(target="t2")]
        accepted, rejected = enforce_coordination_range(actions, profile)
        assert len(accepted) == 1
        assert len(rejected) == 1
        assert "Coordination range exceeded" in (rejected[0].failure_reason or "")

    def test_same_target_not_counted_twice(self) -> None:
        """Multiple actions on same target only count as 1."""
        profile = OODAProfile(coordination_range=1)
        actions = [_make_action(target="t1"), _make_action(target="t1")]
        accepted, rejected = enforce_coordination_range(actions, profile)
        assert len(accepted) == 2
        assert len(rejected) == 0

    def test_range_zero_rejects_all(self) -> None:
        profile = OODAProfile(coordination_range=0)
        actions = [_make_action(target="t1")]
        accepted, rejected = enforce_coordination_range(actions, profile)
        assert len(accepted) == 0
        assert len(rejected) == 1

    def test_empty_actions(self) -> None:
        profile = OODAProfile(coordination_range=1)
        accepted, rejected = enforce_coordination_range([], profile)
        assert accepted == []
        assert rejected == []


class TestAutonomyModifier:
    """Autonomy-effectiveness tradeoff."""

    def test_single_target_full_effectiveness(self) -> None:
        defines = OODADefines()
        assert apply_autonomy_modifier(1, autonomy=0.5, defines=defines) == 1.0

    def test_zero_targets_full_effectiveness(self) -> None:
        defines = OODADefines()
        assert apply_autonomy_modifier(0, autonomy=1.0, defines=defines) == 1.0

    def test_high_autonomy_reduces_effectiveness(self) -> None:
        defines = OODADefines()
        result = apply_autonomy_modifier(5, autonomy=1.0, defines=defines)
        assert result < 1.0

    def test_low_autonomy_preserves_effectiveness(self) -> None:
        defines = OODADefines()
        result = apply_autonomy_modifier(5, autonomy=0.0, defines=defines)
        assert result == 1.0

    def test_effectiveness_floor(self) -> None:
        """Effectiveness never goes below 0.1."""
        defines = OODADefines()
        result = apply_autonomy_modifier(100, autonomy=1.0, defines=defines)
        assert result >= 0.1

    def test_concentration_vs_spread(self) -> None:
        """More targets with same autonomy = lower effectiveness."""
        defines = OODADefines()
        few = apply_autonomy_modifier(2, autonomy=0.8, defines=defines)
        many = apply_autonomy_modifier(10, autonomy=0.8, defines=defines)
        assert few > many

    @pytest.mark.parametrize("num_targets", [2, 5, 10, 50])
    def test_always_bounded(self, num_targets: int) -> None:
        defines = OODADefines()
        result = apply_autonomy_modifier(num_targets, autonomy=0.5, defines=defines)
        assert 0.1 <= result <= 1.0
