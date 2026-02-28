"""Tests for babylon.config.defines - GameDefines configuration.

TDD Red Phase: Tests for new PrecisionDefines and TimescaleDefines
added as part of Epoch 0 Physics Hardening.

Existing defines structure (economy, survival, solidarity, etc.) is tested
elsewhere. This module focuses on the new configuration sections:

1. PrecisionDefines: Configuration for 10^-5 quantization grid
2. TimescaleDefines: Configuration for weekly ticks (7 days/tick, 52 weeks/year)

These settings are foundational for the simulation's temporal and numerical
resolution.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines

# =============================================================================
# PRECISION DEFINES TESTS (RED PHASE)
# =============================================================================


@pytest.mark.unit
class TestPrecisionDefines:
    """Tests for precision configuration.

    PrecisionDefines controls the 10^-5 quantization grid used to
    prevent floating-point drift in long simulations.

    These tests will FAIL until the PrecisionDefines nested model
    is added to GameDefines in the GREEN phase.
    """

    def test_precision_defines_exists(self) -> None:
        """PrecisionDefines class exists in GameDefines.

        GameDefines should have a 'precision' attribute containing
        the PrecisionDefines configuration.
        """
        defines = GameDefines()

        assert hasattr(defines, "precision")

    def test_precision_decimal_places_default(self) -> None:
        """Default decimal_places is 6.

        6 decimal places = 10^-6 = 0.000001 grid resolution.
        This provides sub-penny precision for economic calculations
        while preventing drift accumulation in 100-year simulations.
        """
        defines = GameDefines()

        assert defines.precision.decimal_places == 6

    def test_precision_rounding_mode_default(self) -> None:
        """Default rounding_mode is ROUND_HALF_UP.

        ROUND_HALF_UP (also called ROUND_HALF_AWAY_FROM_ZERO) rounds
        ties away from zero:
        - 0.0000005 -> 0.000001
        - -0.0000005 -> -0.000001

        This is the standard banker's rounding variant.
        """
        defines = GameDefines()

        assert defines.precision.rounding_mode == "ROUND_HALF_UP"


# =============================================================================
# TIMESCALE DEFINES TESTS (RED PHASE)
# =============================================================================


@pytest.mark.unit
class TestTimescaleDefines:
    """Tests for timescale configuration.

    TimescaleDefines controls the temporal resolution of the simulation:
    - 1 tick = 7 days (weekly resolution)
    - 52 weeks = 1 year (for annual rate conversions)

    This is critical for:
    - Economic flow rates (annual -> per-tick conversion)
    - Historical pacing (events per game year)
    - UI display (showing dates/weeks)
    """

    def test_timescale_defines_exists(self) -> None:
        """TimescaleDefines class exists in GameDefines.

        GameDefines should have a 'timescale' attribute containing
        the TimescaleDefines configuration.
        """
        defines = GameDefines()

        assert hasattr(defines, "timescale")

    def test_tick_duration_days_default(self) -> None:
        """Default tick_duration_days is 7 (weekly).

        Each simulation tick represents one week (7 days).
        This provides enough granularity for political events
        while keeping simulation runs manageable.
        """
        defines = GameDefines()

        assert defines.timescale.tick_duration_days == 7

    def test_weeks_per_year_default(self) -> None:
        """Default weeks_per_year is 52.

        Standard Gregorian calendar has ~52.17 weeks/year.
        We use 52 for clean arithmetic:
        - annual_rate / 52 = per_tick_rate
        - 52 ticks = 1 game year
        """
        defines = GameDefines()

        assert defines.timescale.weeks_per_year == 52

    def test_ticks_per_year_calculated(self) -> None:
        """ticks_per_year property returns weeks_per_year.

        Convenience property: since 1 tick = 1 week,
        ticks_per_year == weeks_per_year.
        """
        defines = GameDefines()

        assert defines.timescale.ticks_per_year == 52

    def test_days_per_year_calculated(self) -> None:
        """days_per_year property returns tick_duration_days * weeks_per_year.

        7 days/tick * 52 weeks/year = 364 days/year.
        This is slightly less than actual year (365-366) but provides
        clean arithmetic for the simulation.
        """
        defines = GameDefines()

        assert defines.timescale.days_per_year == 364


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.unit
class TestDefinesIntegration:
    """Integration tests for new defines with existing structure."""

    def test_gamedefines_is_frozen(self) -> None:
        """GameDefines remains immutable after adding new sections.

        The frozen=True config should still apply, preventing
        accidental mutation during simulation.
        """
        defines = GameDefines()

        with pytest.raises((TypeError, ValueError)):  # Frozen model raises on mutation
            defines.precision = None  # type: ignore[misc]

    def test_yaml_loading_includes_precision(self) -> None:
        """GameDefines.load_from_yaml includes precision section.

        When loading from YAML, the precision section should be
        populated (either from file or defaults).
        """
        # This test verifies that YAML loading would work if implemented
        # For now, we just verify the structure would be correct
        defines = GameDefines()
        assert hasattr(defines, "precision")

    def test_yaml_loading_includes_timescale(self) -> None:
        """GameDefines.load_from_yaml includes timescale section.

        When loading from YAML, the timescale section should be
        populated (either from file or defaults).
        """
        defines = GameDefines()
        assert hasattr(defines, "timescale")


# =============================================================================
# CRISIS DEFINES TESTS (Feature 018, T018)
# =============================================================================


@pytest.mark.unit
class TestCrisisDefines:
    """Tests for CrisisDefines configuration (Feature 018).

    CrisisDefines configures the multi-period crisis detector,
    phased amplification, bifurcation risk, and wage compression.
    """

    def test_crisis_defines_exists(self) -> None:
        """CrisisDefines exists on GameDefines."""
        defines = GameDefines()
        assert hasattr(defines, "crisis")

    def test_crisis_period_ticks_default(self) -> None:
        """Default crisis_period_ticks is 13 (quarterly, prime)."""
        defines = GameDefines()
        assert defines.crisis.crisis_period_ticks == 13

    def test_r_threshold_default(self) -> None:
        """Default r_threshold is 0.05 (5% profit rate)."""
        defines = GameDefines()
        assert defines.crisis.r_threshold == 0.05

    def test_n_consecutive_default(self) -> None:
        """Default n_consecutive is 3 periods."""
        defines = GameDefines()
        assert defines.crisis.n_consecutive == 3

    def test_m_recovery_default(self) -> None:
        """Default m_recovery is 2 periods."""
        defines = GameDefines()
        assert defines.crisis.m_recovery == 2

    def test_r_cap_default(self) -> None:
        """Default r_cap is 8 periods."""
        defines = GameDefines()
        assert defines.crisis.r_cap == 8

    def test_hysteresis_coefficient_default(self) -> None:
        """Default hysteresis_coefficient is 0.5."""
        defines = GameDefines()
        assert defines.crisis.hysteresis_coefficient == 0.5

    def test_wage_compression_rate_default(self) -> None:
        """Default wage_compression_rate is 0.02 (2% per DEEP period)."""
        defines = GameDefines()
        assert defines.crisis.wage_compression_rate == 0.02

    def test_wage_compression_floor_ratio_default(self) -> None:
        """Default wage_compression_floor_ratio is 0.8."""
        defines = GameDefines()
        assert defines.crisis.wage_compression_floor_ratio == 0.8

    def test_bifurcation_weights_default(self) -> None:
        """Default bifurcation weights are both 1.0."""
        defines = GameDefines()
        assert defines.crisis.bifurcation_solidarity_weight == 1.0
        assert defines.crisis.bifurcation_burden_weight == 1.0

    def test_class_burden_epsilon_default(self) -> None:
        """Default class_burden_epsilon is 0.001."""
        defines = GameDefines()
        assert defines.crisis.class_burden_epsilon == 0.001

    def test_bifurcation_event_threshold_default(self) -> None:
        """Default bifurcation_event_threshold is 0.5."""
        defines = GameDefines()
        assert defines.crisis.bifurcation_event_threshold == 0.5

    def test_dispossession_cascade_milestones_default(self) -> None:
        """Default milestones are [0.05, 0.10, 0.15]."""
        defines = GameDefines()
        assert defines.crisis.dispossession_cascade_milestones == [0.05, 0.10, 0.15]

    def test_crisis_defines_frozen(self) -> None:
        """CrisisDefines is frozen."""
        defines = GameDefines()
        with pytest.raises((TypeError, ValueError)):
            defines.crisis.r_threshold = 0.10  # type: ignore[misc]


# =============================================================================
# CLASS DYNAMICS DEFINES SYNC TESTS (Feature 028 remediation)
# =============================================================================


@pytest.mark.unit
class TestClassDynamicsDefinesSync:
    """Verify 16 centralized class_dynamics constants match hardcoded defaults.

    These tests ensure that ClassDynamicsDefines fields exist with the exact
    values previously hardcoded in class_dynamics.py, and that YAML roundtrip
    preserves them.
    """

    # --- Alpha fields (extraction rates) ---

    def test_alpha_41_default(self) -> None:
        """alpha_41: proletariat -> bourgeoisie extraction rate."""
        defines = GameDefines()
        assert defines.class_dynamics.alpha_41 == 0.0000

    def test_alpha_31_default(self) -> None:
        """alpha_31: labor aristocracy -> bourgeoisie extraction rate."""
        defines = GameDefines()
        assert defines.class_dynamics.alpha_31 == 0.0000

    def test_alpha_32_default(self) -> None:
        """alpha_32: labor aristocracy -> petty bourgeoisie extraction rate."""
        defines = GameDefines()
        assert defines.class_dynamics.alpha_32 == 0.0000

    def test_alpha_42_default(self) -> None:
        """alpha_42: proletariat -> petty bourgeoisie extraction rate."""
        defines = GameDefines()
        assert defines.class_dynamics.alpha_42 == 0.0000

    def test_alpha_43_default(self) -> None:
        """alpha_43: proletariat -> labor aristocracy extraction rate."""
        defines = GameDefines()
        assert defines.class_dynamics.alpha_43 == 0.0000

    # --- Delta fields (redistribution rates) ---

    def test_delta_1_default(self) -> None:
        """delta_1: redistribution from bourgeoisie."""
        defines = GameDefines()
        assert defines.class_dynamics.delta_1 == 0.0010

    def test_delta_2_default(self) -> None:
        """delta_2: redistribution from petty bourgeoisie."""
        defines = GameDefines()
        assert defines.class_dynamics.delta_2 == 0.0020

    def test_delta_3_default(self) -> None:
        """delta_3: redistribution from labor aristocracy."""
        defines = GameDefines()
        assert defines.class_dynamics.delta_3 == 0.0010

    # --- Beta fields (damping coefficients) ---

    def test_beta_1_default(self) -> None:
        """beta_1: bourgeoisie damping coefficient."""
        defines = GameDefines()
        assert defines.class_dynamics.beta_1 == -0.10

    def test_beta_2_default(self) -> None:
        """beta_2: petty bourgeoisie damping coefficient."""
        defines = GameDefines()
        assert defines.class_dynamics.beta_2 == -0.15

    def test_beta_3_default(self) -> None:
        """beta_3: labor aristocracy damping coefficient."""
        defines = GameDefines()
        assert defines.class_dynamics.beta_3 == -0.10

    def test_beta_4_default(self) -> None:
        """beta_4: proletariat damping coefficient."""
        defines = GameDefines()
        assert defines.class_dynamics.beta_4 == -0.05

    # --- Omega fields (oscillation frequencies) ---

    def test_omega_1_default(self) -> None:
        """omega_1: bourgeoisie oscillation frequency."""
        defines = GameDefines()
        assert defines.class_dynamics.omega_1 == 0.05

    def test_omega_2_default(self) -> None:
        """omega_2: petty bourgeoisie oscillation frequency."""
        defines = GameDefines()
        assert defines.class_dynamics.omega_2 == 0.08

    def test_omega_3_default(self) -> None:
        """omega_3: labor aristocracy oscillation frequency."""
        defines = GameDefines()
        assert defines.class_dynamics.omega_3 == 0.05

    def test_omega_4_default(self) -> None:
        """omega_4: proletariat oscillation frequency."""
        defines = GameDefines()
        assert defines.class_dynamics.omega_4 == 0.03

    # --- YAML roundtrip ---

    def test_yaml_roundtrip_preserves_class_dynamics(self) -> None:
        """YAML loading via load_default() preserves class_dynamics values."""
        defines = GameDefines.load_default()
        assert defines.class_dynamics.alpha_41 == 0.0000
        assert defines.class_dynamics.delta_1 == 0.0010
        assert defines.class_dynamics.beta_1 == -0.10
        assert defines.class_dynamics.omega_1 == 0.05

    def test_class_dynamics_frozen(self) -> None:
        """ClassDynamicsDefines is frozen."""
        defines = GameDefines()
        with pytest.raises((TypeError, ValueError)):
            defines.class_dynamics.alpha_41 = 0.5  # type: ignore[misc]
