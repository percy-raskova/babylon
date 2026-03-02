"""Unit tests for StateApparatusAIDefines (Feature 039, T022).

Tests GameDefines integration, default values, and field constraints.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines, StateApparatusAIDefines


class TestStateApparatusAIDefines:
    """T022: StateApparatusAIDefines sub-model."""

    def test_default_construction(self) -> None:
        defines = StateApparatusAIDefines()
        assert defines.max_faction_shift_per_tick == 0.05
        assert defines.minimum_effect_floor == 0.02
        assert defines.fascist_security_threshold == 0.4
        assert defines.actions_per_tick == 1

    def test_registered_in_game_defines(self) -> None:
        gd = GameDefines()
        assert hasattr(gd, "state_ai")
        assert isinstance(gd.state_ai, StateApparatusAIDefines)

    def test_fascist_thresholds(self) -> None:
        defines = StateApparatusAIDefines()
        assert defines.fascist_security_threshold == 0.4
        assert defines.fascist_settler_ci_threshold == 0.6
        assert defines.fascist_finance_ceiling == 0.25
        assert defines.convergence_confirmation_ticks == 2

    def test_reversion_thresholds(self) -> None:
        defines = StateApparatusAIDefines()
        assert defines.reversion_ss_threshold == 0.25
        assert defines.reversion_ci_threshold == 0.30

    def test_thread_pool_params(self) -> None:
        defines = StateApparatusAIDefines()
        assert defines.thread_pool_base == 5
        assert defines.thread_pool_max == 8
        assert "dormant_to_monitoring" in defines.thread_escalation_thresholds
        assert defines.thread_escalation_thresholds["dormant_to_monitoring"] == 0.1

    def test_escalation_ladder_ordered(self) -> None:
        defines = StateApparatusAIDefines()
        assert len(defines.escalation_ladder) >= 10
        assert defines.escalation_ladder[0] == "propagandize"
        assert defines.escalation_ladder[-1] == "scorched_earth"

    def test_territory_effect_params(self) -> None:
        defines = StateApparatusAIDefines()
        assert defines.develop_infrastructure_boost == 0.1
        assert defines.neglect_infrastructure_decay == 0.05
        assert defines.displace_population_fraction == 0.1

    def test_god_mode_default_off(self) -> None:
        defines = StateApparatusAIDefines()
        assert defines.god_mode_enabled is False

    def test_frozen(self) -> None:
        gd = GameDefines()
        assert gd.state_ai.max_faction_shift_per_tick == 0.05
