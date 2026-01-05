"""Verify TestConstants stays in sync with GameDefines.

This test ensures that the YAML-first constants architecture is working correctly.
TestConstants values should be loaded from GameDefines, which loads from defines.yaml.

If this test fails, it means:
1. A value was changed in defines.yaml but not in TestConstants
2. A new constant was added to GameDefines but not exposed in TestConstants
3. The import path has changed
"""

from __future__ import annotations

import pytest
from tests.constants import TestConstants

from babylon.config.defines import GameDefines
from babylon.systems.formulas.constants import EPSILON, LOSS_AVERSION_COEFFICIENT

TC = TestConstants


@pytest.mark.unit
class TestConstantsSync:
    """Verify TestConstants matches GameDefines values."""

    def test_pool_thresholds_match(self) -> None:
        """Pool ratio thresholds should match GameDefines.economy."""
        defines = GameDefines.load_default()

        assert defines.economy.pool_high_threshold == TC.Canon.POOL_HIGH
        assert defines.economy.pool_low_threshold == TC.Canon.POOL_LOW
        assert defines.economy.pool_critical_threshold == TC.Canon.POOL_CRITICAL

    def test_economic_baselines_match(self) -> None:
        """Economic baseline values should match GameDefines."""
        defines = GameDefines.load_default()

        assert defines.economy.initial_rent_pool == TC.Canon.INITIAL_RENT_POOL
        assert defines.survival.default_repression == TC.Canon.DEFAULT_REPRESSION
        assert defines.economy.extraction_efficiency == TC.Canon.DEFAULT_EXTRACTION

    def test_behavioral_constants_match(self) -> None:
        """Behavioral economics constants should match GameDefines."""
        defines = GameDefines.load_default()

        assert defines.behavioral.loss_aversion_lambda == TC.Behavioral.LOSS_AVERSION

    def test_solidarity_constants_match(self) -> None:
        """Solidarity constants should match GameDefines."""
        defines = GameDefines.load_default()

        assert defines.solidarity.activation_threshold == TC.Solidarity.ACTIVATION_THRESHOLD
        assert defines.solidarity.mass_awakening_threshold == TC.Solidarity.MASS_AWAKENING_THRESHOLD

    def test_bourgeoisie_decision_constants_match(self) -> None:
        """Bourgeoisie decision constants should match GameDefines.economy."""
        defines = GameDefines.load_default()

        assert (
            defines.economy.bribery_tension_threshold
            == TC.BourgeoisieDecision.BRIBERY_TENSION_THRESHOLD
        )
        assert (
            defines.economy.iron_fist_tension_threshold
            == TC.BourgeoisieDecision.IRON_FIST_TENSION_THRESHOLD
        )
        assert defines.economy.bribery_wage_delta == TC.BourgeoisieDecision.BRIBERY_WAGE_DELTA
        assert defines.economy.austerity_wage_delta == TC.BourgeoisieDecision.AUSTERITY_WAGE_DELTA
        assert (
            defines.economy.iron_fist_repression_delta
            == TC.BourgeoisieDecision.IRON_FIST_REPRESSION_DELTA
        )
        assert defines.economy.crisis_wage_delta == TC.BourgeoisieDecision.CRISIS_WAGE_DELTA
        assert (
            defines.economy.crisis_repression_delta
            == TC.BourgeoisieDecision.CRISIS_REPRESSION_DELTA
        )

    def test_trpf_constants_match(self) -> None:
        """TRPF constants should match GameDefines.economy."""
        defines = GameDefines.load_default()

        assert defines.economy.trpf_coefficient == TC.TRPF.TRPF_COEFFICIENT
        assert defines.economy.rent_pool_decay == TC.TRPF.RENT_POOL_DECAY
        assert defines.economy.trpf_efficiency_floor == TC.TRPF.EFFICIENCY_FLOOR

    def test_timescale_constants_match(self) -> None:
        """Timescale constants should match GameDefines.timescale."""
        defines = GameDefines.load_default()

        assert defines.timescale.weeks_per_year == TC.Timescale.TICKS_PER_YEAR
        assert defines.timescale.tick_duration_days == TC.Timescale.DAYS_PER_TICK

    def test_metabolic_rift_constants_match(self) -> None:
        """Metabolic rift constants should match GameDefines.metabolism."""
        defines = GameDefines.load_default()

        assert defines.metabolism.entropy_factor == TC.MetabolicRift.ENTROPY_FACTOR
        assert defines.metabolism.max_overshoot_ratio == TC.MetabolicRift.MAX_OVERSHOOT_RATIO

    def test_quantization_constants_match(self) -> None:
        """Quantization constants should match GameDefines.precision."""
        defines = GameDefines.load_default()

        assert defines.precision.decimal_places == TC.Quantization.DECIMAL_PLACES
        assert defines.precision.epsilon == TC.Quantization.EPSILON
        assert 10 ** (-defines.precision.decimal_places) == TC.Quantization.GRID_PRECISION


@pytest.mark.unit
class TestFormulasConstantsSync:
    """Verify formulas/constants.py matches GameDefines."""

    def test_epsilon_matches_game_defines(self) -> None:
        """EPSILON in formulas should match GameDefines.precision.epsilon."""
        defines = GameDefines.load_default()
        assert defines.precision.epsilon == EPSILON

    def test_loss_aversion_matches_game_defines(self) -> None:
        """LOSS_AVERSION_COEFFICIENT should match GameDefines.behavioral."""
        defines = GameDefines.load_default()
        assert defines.behavioral.loss_aversion_lambda == LOSS_AVERSION_COEFFICIENT
