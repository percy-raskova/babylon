"""Spec-102 SLICE B: ScheduledBlocShock model + timeline-build/apply helpers.

RED phase: ``ScheduledBlocShock`` and the shock-timeline helpers do not
exist yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.engine.headless_runner.models import ScheduledBlocShock, SimulationRunConfig
from babylon.engine.headless_runner.runner import (
    _apply_due_shocks,
    _build_shock_timeline,
    _effective_external_nodes_phi,
)


class TestScheduledBlocShockModel:
    def test_valid_shock_constructs(self) -> None:
        shock = ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0)
        assert shock.tick == 52
        assert shock.bloc == "china"
        assert shock.phi_multiplier == 2.0

    def test_frozen(self) -> None:
        shock = ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0)
        with pytest.raises(ValidationError):
            shock.tick = 100  # type: ignore[misc]

    def test_unknown_bloc_rejected(self) -> None:
        with pytest.raises(ValidationError, match="bloc"):
            ScheduledBlocShock(tick=52, bloc="atlantis", phi_multiplier=2.0)

    def test_non_positive_multiplier_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=0.0)

    def test_negative_tick_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScheduledBlocShock(tick=-1, bloc="china", phi_multiplier=2.0)


class TestSimulationRunConfigShockScheduleDefault:
    def test_default_shock_schedule_is_empty(self) -> None:
        config = SimulationRunConfig(
            scope_fips=frozenset({"26163"}),
            output_dir="/tmp/x",  # noqa: S108
        )
        assert config.shock_schedule == ()


class TestBuildShockTimeline:
    def test_empty_schedule_yields_empty_timeline(self) -> None:
        assert _build_shock_timeline(()) == {}

    def test_groups_by_tick(self) -> None:
        shocks = (
            ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),
            ScheduledBlocShock(tick=52, bloc="canada", phi_multiplier=0.5),
            ScheduledBlocShock(tick=104, bloc="eu", phi_multiplier=3.0),
        )
        timeline = _build_shock_timeline(shocks)
        assert set(timeline.keys()) == {52, 104}
        assert len(timeline[52]) == 2
        assert len(timeline[104]) == 1

    def test_same_tick_sorted_by_bloc_deterministically(self) -> None:
        shocks = (
            ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),
            ScheduledBlocShock(tick=52, bloc="canada", phi_multiplier=0.5),
        )
        timeline = _build_shock_timeline(shocks)
        assert [s.bloc for s in timeline[52]] == ["canada", "china"]


class TestApplyDueShocks:
    def test_no_shocks_this_tick_leaves_multipliers_unchanged(self) -> None:
        timeline = _build_shock_timeline(
            (ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),)
        )
        active: dict[str, float] = {"china": 1.0}
        _apply_due_shocks(tick=10, shock_timeline=timeline, active_multipliers=active)
        assert active == {"china": 1.0}

    def test_shock_at_tick_updates_multiplier(self) -> None:
        timeline = _build_shock_timeline(
            (ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),)
        )
        active: dict[str, float] = {}
        _apply_due_shocks(tick=52, shock_timeline=timeline, active_multipliers=active)
        assert active == {"china": 2.0}

    def test_multiplier_persists_after_scheduled_tick(self) -> None:
        """Level-set semantics: the multiplier stays active on later ticks."""
        timeline = _build_shock_timeline(
            (ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),)
        )
        active: dict[str, float] = {}
        _apply_due_shocks(tick=52, shock_timeline=timeline, active_multipliers=active)
        _apply_due_shocks(tick=53, shock_timeline=timeline, active_multipliers=active)
        assert active == {"china": 2.0}

    def test_later_shock_replaces_earlier_for_same_bloc(self) -> None:
        timeline = _build_shock_timeline(
            (
                ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),
                ScheduledBlocShock(tick=104, bloc="china", phi_multiplier=0.1),
            )
        )
        active: dict[str, float] = {}
        _apply_due_shocks(tick=52, shock_timeline=timeline, active_multipliers=active)
        _apply_due_shocks(tick=104, shock_timeline=timeline, active_multipliers=active)
        assert active == {"china": 0.1}


class TestEffectiveExternalNodesPhi:
    def test_no_active_multipliers_returns_base_unchanged(self) -> None:
        base = {"china": 100.0, "canada": 50.0}
        result = _effective_external_nodes_phi(base_external_nodes_phi=base, active_multipliers={})
        assert result == base

    def test_active_multiplier_scales_that_bloc_only(self) -> None:
        base = {"china": 100.0, "canada": 50.0}
        result = _effective_external_nodes_phi(
            base_external_nodes_phi=base, active_multipliers={"china": 2.0}
        )
        assert result == {"china": 200.0, "canada": 50.0}

    def test_does_not_mutate_base_map(self) -> None:
        base = {"china": 100.0}
        _effective_external_nodes_phi(
            base_external_nodes_phi=base, active_multipliers={"china": 2.0}
        )
        assert base == {"china": 100.0}
