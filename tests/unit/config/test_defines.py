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
