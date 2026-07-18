"""Spec-116 FR-116-1: fixed-horizon + recognizer defines exist and load from YAML."""

import pytest

from babylon.config.defines import GameDefines


@pytest.mark.unit
def test_campaign_horizon_and_pattern_defines_exist() -> None:
    defines = GameDefines.load_default()
    assert defines.endgame.campaign_horizon_years == 100
    assert defines.endgame.pattern_lock_ticks == 26
    # Spec-116 Task 6 pacing calibration (2026-07-17): raised 0.75 -> 0.9 —
    # see EndgameDefines.fascist_majority_fraction's docstring and
    # reports/pacing-calibration-2026-07-17.md for the granularity rationale.
    assert defines.endgame.fascist_majority_fraction == 0.9


@pytest.mark.unit
def test_balkanization_is_composed_into_game_defines() -> None:
    defines = GameDefines.load_default()
    assert defines.balkanization.red_ogv_habitability_floor == 0.4
    assert defines.balkanization.fragmented_collapse_min_sovereigns == 3


@pytest.mark.unit
def test_horizon_ticks_derivation() -> None:
    defines = GameDefines.load_default()
    horizon = defines.endgame.campaign_horizon_years * defines.timescale.weeks_per_year
    assert horizon == 5200
