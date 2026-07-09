"""Tests for OODA core data types (Feature 032).

Verifies construction, defaults, constraints, and immutability of all
frozen Pydantic models in babylon.ooda.types.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import ActionType, DecisionMode
from babylon.ooda.types import (
    Action,
    ActionCostModifier,
    ActionResult,
    InitiativeScore,
    OODAProfile,
    TurnResolution,
)
from tests.unit.ooda.conftest import make_action, make_ooda_profile


class TestOODAProfile:
    """OODAProfile construction, defaults, and constraints."""

    def test_default_construction(self) -> None:
        profile = OODAProfile()
        assert profile.sensor_latency == 1
        assert profile.ideological_coherence == 0.5
        assert profile.analytical_capacity == 0.5
        assert profile.decision_mode == DecisionMode.DEMOCRATIC
        assert profile.bureaucratic_depth == 0.3
        assert profile.action_points == 3
        assert profile.coordination_range == 1
        assert profile.autonomy == 0.5

    def test_custom_construction(self) -> None:
        profile = make_ooda_profile(
            sensor_latency=3,
            decision_mode=DecisionMode.AUTOCRATIC,
            action_points=5,
        )
        assert profile.sensor_latency == 3
        assert profile.decision_mode == DecisionMode.AUTOCRATIC
        assert profile.action_points == 5

    def test_frozen_immutability(self) -> None:
        profile = OODAProfile()
        with pytest.raises(ValidationError):
            profile.sensor_latency = 5  # type: ignore[misc]

    def test_sensor_latency_bounds(self) -> None:
        OODAProfile(sensor_latency=0)
        OODAProfile(sensor_latency=10)
        with pytest.raises(ValidationError):
            OODAProfile(sensor_latency=-1)
        with pytest.raises(ValidationError):
            OODAProfile(sensor_latency=11)

    def test_ideological_coherence_bounds(self) -> None:
        OODAProfile(ideological_coherence=0.0)
        OODAProfile(ideological_coherence=1.0)
        with pytest.raises(ValidationError):
            OODAProfile(ideological_coherence=-0.1)
        with pytest.raises(ValidationError):
            OODAProfile(ideological_coherence=1.1)

    def test_action_points_bounds(self) -> None:
        OODAProfile(action_points=0)
        OODAProfile(action_points=20)
        with pytest.raises(ValidationError):
            OODAProfile(action_points=-1)
        with pytest.raises(ValidationError):
            OODAProfile(action_points=21)

    def test_bureaucratic_depth_bounds(self) -> None:
        OODAProfile(bureaucratic_depth=0.0)
        OODAProfile(bureaucratic_depth=1.0)
        with pytest.raises(ValidationError):
            OODAProfile(bureaucratic_depth=-0.1)

    def test_autonomy_bounds(self) -> None:
        OODAProfile(autonomy=0.0)
        OODAProfile(autonomy=1.0)
        with pytest.raises(ValidationError):
            OODAProfile(autonomy=1.1)


class TestAction:
    """Action construction and constraints."""

    def test_default_construction(self) -> None:
        action = make_action()
        assert action.org_id == "org_1"
        assert action.action_type == ActionType.EDUCATE
        assert action.target_id == "community_1"
        assert action.action_point_cost == 1
        assert action.cadre_labor_cost == 0.0
        assert action.sympathizer_labor_cost == 0.0
        assert action.budget_cost == 0.0

    def test_frozen_immutability(self) -> None:
        action = make_action()
        with pytest.raises(ValidationError):
            action.org_id = "other"  # type: ignore[misc]

    def test_org_id_min_length(self) -> None:
        with pytest.raises(ValidationError):
            Action(org_id="", action_type=ActionType.EDUCATE, target_id="t1")

    def test_target_id_min_length(self) -> None:
        with pytest.raises(ValidationError):
            Action(org_id="o1", action_type=ActionType.EDUCATE, target_id="")

    def test_action_point_cost_minimum(self) -> None:
        with pytest.raises(ValidationError):
            make_action(action_point_cost=0)

    def test_all_action_types(self) -> None:
        for at in ActionType:
            action = make_action(action_type=at)
            assert action.action_type == at


class TestActionResult:
    """ActionResult construction."""

    def test_success_result(self) -> None:
        action = make_action()
        result = ActionResult(action=action, success=True)
        assert result.success is True
        assert result.consciousness_delta is None
        assert result.direct_effects == {}
        assert result.events_generated == []
        assert result.failure_reason is None

    def test_failure_result(self) -> None:
        action = make_action()
        result = ActionResult(
            action=action,
            success=False,
            failure_reason="Insufficient AP",
        )
        assert result.success is False
        assert result.failure_reason == "Insufficient AP"

    def test_frozen_immutability(self) -> None:
        action = make_action()
        result = ActionResult(action=action, success=True)
        with pytest.raises(ValidationError):
            result.success = False  # type: ignore[misc]


class TestInitiativeScore:
    """InitiativeScore construction and invariants."""

    def test_construction(self) -> None:
        score = InitiativeScore(
            org_id="fbi",
            score=5.508,
            speed_component=0.408,
            institutional_component=5.0,
            counterintel_component=0.0,
            embeddedness_component=0.0,
            momentum_component=0.1,
        )
        assert score.org_id == "fbi"
        assert score.score == 5.508

    def test_frozen_immutability(self) -> None:
        score = InitiativeScore(
            org_id="fbi",
            score=5.0,
            speed_component=1.0,
            institutional_component=3.0,
            counterintel_component=0.5,
            embeddedness_component=0.3,
            momentum_component=0.2,
        )
        with pytest.raises(ValidationError):
            score.score = 10.0  # type: ignore[misc]


class TestActionCostModifier:
    """ActionCostModifier construction."""

    def test_discount(self) -> None:
        mod = ActionCostModifier(
            base_cost=2,
            modifier=0.7,
            effective_cost=2,
            reason="embedded org discount",
        )
        assert mod.modifier < 1.0

    def test_surcharge(self) -> None:
        mod = ActionCostModifier(
            base_cost=2,
            modifier=1.5,
            effective_cost=3,
            reason="outsider surcharge",
        )
        assert mod.effective_cost == 3

    def test_effective_cost_minimum(self) -> None:
        with pytest.raises(ValidationError):
            ActionCostModifier(
                base_cost=1,
                modifier=0.1,
                effective_cost=0,
                reason="below minimum",
            )


class TestTurnResolution:
    """TurnResolution construction."""

    def test_empty_tick(self) -> None:
        resolution = TurnResolution(tick=0)
        assert resolution.tick == 0
        assert resolution.layer0_results == []
        assert resolution.initiative_order == []
        assert resolution.action_phase_results == []
        assert resolution.layer3_effects == {}

    def test_tick_minimum(self) -> None:
        with pytest.raises(ValidationError):
            TurnResolution(tick=-1)


class TestDecisionModeEnum:
    """DecisionMode enum completeness."""

    def test_has_four_values(self) -> None:
        assert len(DecisionMode) == 4

    def test_values(self) -> None:
        assert DecisionMode.AUTOCRATIC == "autocratic"
        assert DecisionMode.DELEGATE == "delegate"
        assert DecisionMode.DEMOCRATIC == "democratic"
        assert DecisionMode.CONSENSUS == "consensus"


class TestActionTypeEnum:
    """ActionType enum completeness."""

    def test_has_26_values(self) -> None:
        # 21 base (Feature 032) + MOVE (verb-dispatch engine) + 4 fascist
        # verbs (spec-071).
        assert len(ActionType) == 26

    def test_all_categories_present(self) -> None:
        values = {at.value for at in ActionType}
        # Recruitment
        assert "recruit" in values
        # Consciousness
        assert "educate" in values
        assert "agitate" in values
        assert "propagandize" in values
        # Resources
        assert "organize" in values
        assert "fundraise" in values
        assert "provide_service" in values
        assert "employ" in values
        # Conflict
        assert "protest" in values
        assert "strike" in values
        assert "expropriate" in values
        assert "repress" in values
        assert "attack_infrastructure" in values
        # Intelligence
        assert "surveil" in values
        assert "infiltrate" in values
        assert "counter_intel" in values
        assert "map_network" in values
        # Diplomacy
        assert "propose_alliance" in values
        assert "denounce" in values
        # Infrastructure
        assert "build_infrastructure" in values
        assert "assimilate" in values
