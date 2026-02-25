"""Falsification criteria tests for Capital Volume I (Feature 021).

SC-001: Reserve army wage pressure produces negative correlation with
subsequent wage growth (BLS data for Wayne/Oakland/Macomb, 2005-2020).

SC-007: Wayne County dispossession intensity exceeds Oakland County
by at least 3x during 2008-2012 crisis period.

These tests validate against simulation logic (not yet against loaded
empirical data — that requires the full data pipeline to be wired).
"""

from __future__ import annotations

from babylon.economics.dispossession.intensity import DispossessionIntensityCalculator
from babylon.economics.dispossession.types import TerritoryDispossessionState
from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator


class TestSC001WagePressureCorrelation:
    """SC-001: Higher reserve ratio → lower wage growth.

    Verifies the monotonic relationship between reserve_ratio and
    wage_pressure that produces the negative correlation.
    """

    def test_wage_pressure_monotonically_increasing(self) -> None:
        """Higher reserve ratios produce strictly higher wage pressure."""
        calc = DefaultWagePressureCalculator()
        ratios = [0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30]
        pressures = [calc.compute_wage_pressure(r) for r in ratios]

        for i in range(len(pressures) - 1):
            assert pressures[i] < pressures[i + 1], (
                f"Monotonicity violated: P({ratios[i]})={pressures[i]} >= "
                f"P({ratios[i + 1]})={pressures[i + 1]}"
            )

    def test_detroit_metro_relative_pressure(self) -> None:
        """Wayne (high unemployment) gets more pressure than Oakland (low)."""
        calc = DefaultWagePressureCalculator()
        # Approximate 2009 crisis reserve ratios
        wayne_2009 = calc.compute_wage_pressure(0.18)
        oakland_2009 = calc.compute_wage_pressure(0.09)
        macomb_2009 = calc.compute_wage_pressure(0.12)

        assert wayne_2009 > macomb_2009 > oakland_2009

    def test_pressure_produces_negative_wage_impact(self) -> None:
        """Wage pressure coefficient > 0 means wages decrease."""
        calc = DefaultWagePressureCalculator()
        for ratio in [0.05, 0.10, 0.15, 0.20]:
            pressure = calc.compute_wage_pressure(ratio)
            assert pressure > 0.0, f"Expected positive pressure at ratio={ratio}"
            # Wage after = wage_before * (1 - pressure), so wage decreases
            wage_after_fraction = 1.0 - pressure
            assert 0.0 < wage_after_fraction < 1.0


class TestSC007DispossessionIntensityRatio:
    """SC-007: Wayne dispossession intensity >= 3x Oakland during crisis.

    Verifies that the intensity calculator produces the expected
    disparity between Wayne and Oakland counties during 2008-2012.
    """

    def test_wayne_exceeds_oakland_3x_crisis(self) -> None:
        """Wayne County intensity is at least 3x Oakland during crisis."""
        calc = DispossessionIntensityCalculator()

        # Wayne County 2009 crisis: high foreclosure, eviction, displacement
        wayne = TerritoryDispossessionState(
            fips_code="26163",
            year=2009,
            foreclosure_rate=0.08,
            eviction_rate=0.05,
            displacement_rate=0.04,
            concentrated_ownership=0.15,
            absentee_landlord_share=0.25,
        )

        # Oakland County 2009: suburban, much lower rates
        oakland = TerritoryDispossessionState(
            fips_code="26125",
            year=2009,
            foreclosure_rate=0.02,
            eviction_rate=0.01,
            displacement_rate=0.005,
            concentrated_ownership=0.05,
            absentee_landlord_share=0.08,
        )

        wayne_intensity = calc.compute_intensity(wayne)
        oakland_intensity = calc.compute_intensity(oakland)

        assert wayne_intensity > 0.0
        assert oakland_intensity > 0.0
        ratio = wayne_intensity / oakland_intensity
        assert ratio >= 3.0, (
            f"Wayne/Oakland ratio {ratio:.1f}x < 3x required. "
            f"Wayne={wayne_intensity:.4f}, Oakland={oakland_intensity:.4f}"
        )

    def test_intensity_difference_persists_across_crisis(self) -> None:
        """Wayne > Oakland disparity holds for each year 2008-2012."""
        calc = DispossessionIntensityCalculator()

        # Simplified: use same rates for each year (actual calibration later)
        for year in range(2008, 2013):
            wayne = TerritoryDispossessionState(
                fips_code="26163",
                year=year,
                foreclosure_rate=0.07,
                eviction_rate=0.04,
                displacement_rate=0.03,
                concentrated_ownership=0.12,
                absentee_landlord_share=0.22,
            )
            oakland = TerritoryDispossessionState(
                fips_code="26125",
                year=year,
                foreclosure_rate=0.02,
                eviction_rate=0.01,
                displacement_rate=0.005,
                concentrated_ownership=0.05,
                absentee_landlord_share=0.08,
            )

            wayne_i = calc.compute_intensity(wayne)
            oakland_i = calc.compute_intensity(oakland)
            assert wayne_i > oakland_i, f"Wayne should exceed Oakland in {year}"
