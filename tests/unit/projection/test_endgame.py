"""Contract tests for the Archive-side endgame status fold (WO-39).

The century-horizon recognition logic relocates out of the legacy web
bridge so the TUI determines game-over independently of it: patterns are
RECOGNIZED, never adjudicated (owner ruling 2026-07-17, spec-116); the
game ends only at the fixed horizon, with ``GameOutcome.UNRESOLVED`` when
no pattern is held at that tick. Pure fold over detector OUTPUTS — the
``EndgameDetector`` itself stays engine-side; projection never imports the
engine (import-linter contract).
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.models.enums.events import GameOutcome
from babylon.projection.endgame import campaign_horizon_tick, endgame_status


def _defines() -> GameDefines:
    return GameDefines()


class TestHorizon:
    def test_horizon_is_campaign_years_times_weeks_per_year(self) -> None:
        defines = _defines()
        assert campaign_horizon_tick(defines) == (
            defines.endgame.campaign_horizon_years * defines.timescale.weeks_per_year
        )


class TestEndgameStatus:
    def test_before_the_horizon_with_no_pattern_the_game_runs_on(self) -> None:
        status = endgame_status(tick=10, pattern=None, since_tick=None, defines=_defines())
        assert not status.game_over
        assert status.outcome is GameOutcome.UNRESOLVED
        assert status.pattern is None
        assert not status.locked

    def test_a_recognized_pattern_does_not_end_the_game(self) -> None:
        status = endgame_status(
            tick=10,
            pattern=GameOutcome.REVOLUTIONARY_VICTORY,
            since_tick=5,
            defines=_defines(),
        )
        assert not status.game_over
        assert status.outcome is GameOutcome.REVOLUTIONARY_VICTORY

    def test_at_the_horizon_the_held_pattern_is_the_outcome(self) -> None:
        defines = _defines()
        horizon = campaign_horizon_tick(defines)
        status = endgame_status(
            tick=horizon,
            pattern=GameOutcome.FASCIST_CONSOLIDATION,
            since_tick=horizon - 3,
            defines=defines,
        )
        assert status.game_over
        assert status.outcome is GameOutcome.FASCIST_CONSOLIDATION

    def test_at_the_horizon_with_no_pattern_the_outcome_is_unresolved(self) -> None:
        defines = _defines()
        status = endgame_status(
            tick=campaign_horizon_tick(defines), pattern=None, since_tick=None, defines=defines
        )
        assert status.game_over
        assert status.outcome is GameOutcome.UNRESOLVED

    def test_lock_window_arithmetic_matches_the_bridge(self) -> None:
        """locked iff the pattern has been held >= pattern_lock_ticks
        (inclusive window: tick - since + 1)."""
        defines = _defines()
        lock = defines.endgame.pattern_lock_ticks
        held_exactly = endgame_status(
            tick=lock - 1 + 5,
            pattern=GameOutcome.RED_OGV,
            since_tick=5,
            defines=defines,
        )
        assert held_exactly.locked
        held_one_short = endgame_status(
            tick=lock - 2 + 5,
            pattern=GameOutcome.RED_OGV,
            since_tick=5,
            defines=defines,
        )
        assert not held_one_short.locked

    def test_force_game_over_ends_it_early_with_the_held_outcome(self) -> None:
        status = endgame_status(
            tick=1,
            pattern=GameOutcome.ECOLOGICAL_COLLAPSE,
            since_tick=1,
            defines=_defines(),
            force_game_over=True,
        )
        assert status.game_over
        assert status.outcome is GameOutcome.ECOLOGICAL_COLLAPSE
