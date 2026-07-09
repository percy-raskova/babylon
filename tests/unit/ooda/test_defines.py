"""Tests for OODADefines configuration (Feature 032).

Verifies OODADefines construction, defaults, get_base_cost() for all
21 action types, get_action_base() for consciousness-affecting actions,
and GameDefines integration.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines, OODADefines
from babylon.models.enums import ActionType


class TestOODADefinesConstruction:
    """OODADefines construction and defaults."""

    def test_default_construction(self) -> None:
        defines = OODADefines()
        assert defines.base_observe_time == 1.0
        assert defines.base_orient_time == 2.0
        assert defines.base_act_time == 1.0
        assert defines.latency_weight == 0.5
        assert defines.coherence_weight == 0.6
        assert defines.depth_weight == 0.4

    def test_decision_mode_base_times(self) -> None:
        defines = OODADefines()
        assert defines.decision_mode_base_autocratic == 1.0
        assert defines.decision_mode_base_delegate == 2.0
        assert defines.decision_mode_base_democratic == 3.0
        assert defines.decision_mode_base_consensus == 5.0

    def test_initiative_weights(self) -> None:
        defines = OODADefines()
        assert defines.initiative_weight_speed == 2.0
        assert defines.initiative_weight_institutional == 1.0
        assert defines.initiative_weight_counterintel == 1.5
        assert defines.initiative_weight_embeddedness == 1.0
        assert defines.initiative_weight_momentum == 0.5

    def test_institutional_bonuses(self) -> None:
        defines = OODADefines()
        assert defines.institutional_bonus_federal == 5.0
        assert defines.institutional_bonus_state == 3.0
        assert defines.institutional_bonus_local == 1.5
        assert defines.institutional_bonus_nonstate == 0.0

    def test_momentum_parameters(self) -> None:
        defines = OODADefines()
        assert defines.momentum_decay == 0.8
        assert defines.momentum_success_bonus == 0.2

    def test_cost_modifiers(self) -> None:
        defines = OODADefines()
        assert defines.embeddedness_discount == 0.5
        assert defines.contradiction_cost_multiplier == 2.5
        assert defines.outsider_cost_multiplier == 1.5
        assert defines.min_cost_modifier == 0.5

    def test_consciousness_limits(self) -> None:
        defines = OODADefines()
        assert defines.max_ci_delta_per_tick == 0.05

    def test_frozen_immutability(self) -> None:
        defines = OODADefines()
        with pytest.raises(ValidationError):
            defines.base_observe_time = 2.0  # type: ignore[misc]


class TestGetBaseCost:
    """get_base_cost() returns AP cost for all 21 action types."""

    @pytest.mark.parametrize(
        ("action_type", "expected_cost"),
        [
            (ActionType.RECRUIT, 2),
            (ActionType.ORGANIZE, 2),
            (ActionType.EDUCATE, 1),
            (ActionType.AGITATE, 1),
            (ActionType.PROPAGANDIZE, 2),
            (ActionType.FUNDRAISE, 1),
            (ActionType.PROVIDE_SERVICE, 2),
            (ActionType.EMPLOY, 1),
            (ActionType.REPRESS, 2),
            (ActionType.PROTEST, 2),
            (ActionType.STRIKE, 3),
            (ActionType.EXPROPRIATE, 3),
            (ActionType.SURVEIL, 1),
            (ActionType.INFILTRATE, 3),
            (ActionType.COUNTER_INTEL, 2),
            (ActionType.MAP_NETWORK, 1),
            (ActionType.PROPOSE_ALLIANCE, 1),
            (ActionType.DENOUNCE, 1),
            (ActionType.BUILD_INFRASTRUCTURE, 3),
            (ActionType.ATTACK_INFRASTRUCTURE, 2),
            (ActionType.ASSIMILATE, 2),
            (ActionType.MOVE, 1),
        ],
    )
    def test_base_cost(self, action_type: ActionType, expected_cost: int) -> None:
        defines = OODADefines()
        assert defines.get_base_cost(action_type.value) == expected_cost

    def test_all_action_types_have_cost(self) -> None:
        defines = OODADefines()
        for action_type in ActionType:
            cost = defines.get_base_cost(action_type.value)
            assert cost >= 1

    def test_unknown_action_raises_key_error(self) -> None:
        defines = OODADefines()
        with pytest.raises(KeyError, match="Unknown action type"):
            defines.get_base_cost("nonexistent")


class TestGetActionBase:
    """get_action_base() returns consciousness multipliers."""

    def test_consciousness_affecting_actions(self) -> None:
        defines = OODADefines()
        assert defines.get_action_base("educate") == 1.2
        assert defines.get_action_base("provide_service") == 0.6
        assert defines.get_action_base("recruit") == 0.3
        assert defines.get_action_base("organize") == 0.5
        assert defines.get_action_base("propagandize") == 0.8
        assert defines.get_action_base("repress") == 0.8
        assert defines.get_action_base("surveil") == 0.2
        assert defines.get_action_base("assimilate") == 1.0

    def test_agitate_has_zero_ci_effect(self) -> None:
        defines = OODADefines()
        assert defines.get_action_base("agitate") == 0.0

    def test_non_ci_actions_return_zero(self) -> None:
        defines = OODADefines()
        non_ci_actions = [
            "fundraise",
            "employ",
            "protest",
            "strike",
            "expropriate",
            "infiltrate",
            "counter_intel",
            "map_network",
            "propose_alliance",
            "denounce",
            "build_infrastructure",
            "attack_infrastructure",
        ]
        for action in non_ci_actions:
            assert defines.get_action_base(action) == 0.0


class TestGameDefinesIntegration:
    """GameDefines.ooda field exists and is an OODADefines instance."""

    def test_ooda_field_exists(self) -> None:
        gd = GameDefines()
        assert hasattr(gd, "ooda")
        assert isinstance(gd.ooda, OODADefines)

    def test_ooda_field_defaults(self) -> None:
        gd = GameDefines()
        assert gd.ooda.base_observe_time == 1.0
        assert gd.ooda.max_ci_delta_per_tick == 0.05
