"""Unit tests for player observability layer (Feature 039, T084).

See Also:
    :mod:`babylon.ooda.state_ai.observability`: Implementation.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.state_apparatus_ai import (
    FactionBalance,
    StateAction,
    StateBudget,
)
from babylon.models.enums import StateActionType, StateFaction
from babylon.ooda.state_ai.decision import RuleBasedStateAI
from babylon.ooda.state_ai.observability import (
    create_observable_action,
    create_territory_observables,
    resolve_counter_intel,
)


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_balance(
    fc: float = 0.45,
    ss: float = 0.30,
    sp: float = 0.25,
) -> FactionBalance:
    return FactionBalance(
        finance_capital=fc,
        security_state=ss,
        settler_populist=sp,
        stability=0.8,
        legitimacy=0.7,
    )


def _make_action(**overrides: Any) -> StateAction:
    defaults: dict[str, Any] = {
        "verb": StateActionType.CO_OPT,
        "sub_verb": StateActionType.PROPAGANDIZE,
        "target_id": "territory_001",
        "budget_cost": 5.0,
        "thread_cost": 0,
        "legitimacy_cost": -0.01,
        "faction_alignment": StateFaction.FINANCE_CAPITAL,
    }
    defaults.update(overrides)
    return StateAction(**defaults)


def _make_budget() -> StateBudget:
    return StateBudget(
        revenue=100.0,
        available=80.0,
        allocated={StateActionType.CO_OPT: 30.0},
        imperial_rent_pool=50.0,
    )


# ===========================================================================
# God Mode Debug Toggle (T078)
# ===========================================================================


class TestGodModeDebug:
    """Tests for RuleBasedStateAI.get_debug_state (T078)."""

    def test_god_mode_disabled_returns_none(self) -> None:
        defines = _make_defines(god_mode_enabled=False)
        ai = RuleBasedStateAI()
        result = ai.get_debug_state(defines)
        assert result is None

    def test_god_mode_enabled_returns_dict(self) -> None:
        defines = _make_defines(god_mode_enabled=True)
        ai = RuleBasedStateAI()
        result = ai.get_debug_state(defines)
        assert result is not None
        assert result["god_mode"] is True

    def test_god_mode_includes_faction_balance(self) -> None:
        defines = _make_defines(god_mode_enabled=True)
        balance = _make_balance()
        ai = RuleBasedStateAI()
        result = ai.get_debug_state(defines, faction_balance=balance)
        assert result is not None
        assert "faction_balance" in result
        assert result["faction_balance"]["finance_capital"] == pytest.approx(0.45)

    def test_god_mode_includes_budget(self) -> None:
        defines = _make_defines(god_mode_enabled=True)
        budget = _make_budget()
        ai = RuleBasedStateAI()
        result = ai.get_debug_state(defines, budget=budget)
        assert result is not None
        assert "budget" in result
        assert result["budget"]["available"] == 80.0

    def test_god_mode_includes_last_actions(self) -> None:
        defines = _make_defines(god_mode_enabled=True)
        actions = [_make_action()]
        ai = RuleBasedStateAI()
        result = ai.get_debug_state(defines, last_actions=actions)
        assert result is not None
        assert "last_actions" in result
        assert len(result["last_actions"]) == 1
        assert result["last_actions"][0]["verb"] == str(StateActionType.CO_OPT)


# ===========================================================================
# Observable Action (T084)
# ===========================================================================


class TestCreateObservableAction:
    """Tests for create_observable_action."""

    def test_includes_verb_and_target(self) -> None:
        action = _make_action()
        result = create_observable_action(action, territory_heat=0.5)
        assert result["verb"] == str(StateActionType.CO_OPT)
        assert result["target_id"] == "territory_001"

    def test_includes_visible_intensity(self) -> None:
        action = _make_action(budget_cost=10.0)
        result = create_observable_action(action, territory_heat=0.5)
        assert "visible_intensity" in result
        assert 0.0 <= result["visible_intensity"] <= 1.0

    def test_higher_budget_more_visible(self) -> None:
        low_cost = create_observable_action(_make_action(budget_cost=1.0), 0.0)
        high_cost = create_observable_action(_make_action(budget_cost=15.0), 0.0)
        assert high_cost["visible_intensity"] > low_cost["visible_intensity"]


# ===========================================================================
# Territory Observables (T084)
# ===========================================================================


class TestCreateTerritoryObservables:
    """Tests for create_territory_observables."""

    def test_includes_public_fields(self) -> None:
        territory: dict[str, Any] = {
            "property_value_proxy": 1.5,
            "infrastructure_quality": 0.7,
            "heat": 0.3,
            "population": 500,
            "collective_identity": 0.6,
            "state_investment": 100.0,  # Should NOT be in output
            "secret_field": "hidden",  # Should NOT be in output
        }
        result = create_territory_observables(territory)
        assert result["property_value_proxy"] == 1.5
        assert result["heat"] == 0.3
        assert "state_investment" not in result
        assert "secret_field" not in result

    def test_missing_fields_default_to_zero(self) -> None:
        result = create_territory_observables({})
        assert result["property_value_proxy"] == 0.0
        assert result["population"] == 0


# ===========================================================================
# COUNTER_INTEL (T084)
# ===========================================================================


class TestResolveCounterIntel:
    """Tests for resolve_counter_intel."""

    def test_low_intel_basic_info_only(self) -> None:
        defines = _make_defines()
        balance = _make_balance()
        actions = [_make_action()]
        result = resolve_counter_intel(0.1, balance, actions, defines)
        assert "visible_actions" in result
        assert "faction_balance" not in result

    def test_medium_intel_reveals_faction_balance(self) -> None:
        defines = _make_defines()
        balance = _make_balance()
        actions = [_make_action()]
        result = resolve_counter_intel(0.4, balance, actions, defines)
        assert "faction_balance" in result
        assert "action_details" not in result

    def test_high_intel_reveals_action_details(self) -> None:
        defines = _make_defines()
        balance = _make_balance()
        actions = [_make_action()]
        result = resolve_counter_intel(0.7, balance, actions, defines)
        assert "action_details" in result
        assert "full_state" not in result

    def test_full_intel_reveals_everything(self) -> None:
        defines = _make_defines()
        balance = _make_balance()
        actions = [_make_action()]
        result = resolve_counter_intel(0.9, balance, actions, defines)
        assert "faction_balance" in result
        assert "action_details" in result
        assert "full_state" in result

    def test_intel_level_included(self) -> None:
        defines = _make_defines()
        result = resolve_counter_intel(0.5, _make_balance(), [], defines)
        assert result["intel_level"] == 0.5
