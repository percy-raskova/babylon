"""Tests for DefaultWagePressureCalculator (Feature 021, US1)."""

from __future__ import annotations

from babylon.config.defines import ReserveArmyDefines
from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator


class TestDefaultWagePressureCalculator:
    """Tests for bounded sigmoid wage pressure computation."""

    def test_zero_ratio_zero_pressure(self) -> None:
        """Zero reserve ratio produces zero wage pressure."""
        calc = DefaultWagePressureCalculator()
        assert calc.compute_wage_pressure(0.0) == 0.0

    def test_negative_ratio_zero_pressure(self) -> None:
        """Negative reserve ratio (invalid) produces zero wage pressure."""
        calc = DefaultWagePressureCalculator()
        assert calc.compute_wage_pressure(-0.1) == 0.0

    def test_monotonically_increasing(self) -> None:
        """Higher reserve ratios produce higher wage pressure."""
        calc = DefaultWagePressureCalculator()
        pressures = [calc.compute_wage_pressure(r) for r in [0.01, 0.05, 0.10, 0.20, 0.50]]
        for i in range(len(pressures) - 1):
            assert pressures[i] < pressures[i + 1], (
                f"Not monotonic at {i}: {pressures[i]} >= {pressures[i + 1]}"
            )

    def test_saturates_at_ceiling(self) -> None:
        """Wage pressure saturates at the configured ceiling."""
        defines = ReserveArmyDefines(wage_pressure_ceiling=0.5)
        calc = DefaultWagePressureCalculator(defines)
        # At very high ratios, pressure should approach but not exceed ceiling
        pressure = calc.compute_wage_pressure(0.99)
        assert pressure <= 0.5
        assert pressure > 0.4  # Should be close to ceiling

    def test_sigmoid_midpoint(self) -> None:
        """At r0 (midpoint), wage pressure is roughly ceiling/2."""
        defines = ReserveArmyDefines(sigmoid_r0=0.08, wage_pressure_ceiling=0.5)
        calc = DefaultWagePressureCalculator(defines)
        pressure = calc.compute_wage_pressure(0.08)
        # Due to normalization, it won't be exactly ceiling/2 but should be in range
        assert 0.1 < pressure < 0.4

    def test_custom_defines(self) -> None:
        """Custom defines change sigmoid behavior."""
        steep = ReserveArmyDefines(sigmoid_k=50.0, sigmoid_r0=0.05)
        gentle = ReserveArmyDefines(sigmoid_k=5.0, sigmoid_r0=0.05)
        steep_calc = DefaultWagePressureCalculator(steep)
        gentle_calc = DefaultWagePressureCalculator(gentle)

        # Steep sigmoid should produce higher pressure than gentle at 0.10
        steep_pressure = steep_calc.compute_wage_pressure(0.10)
        gentle_pressure = gentle_calc.compute_wage_pressure(0.10)
        assert steep_pressure > gentle_pressure

    def test_extreme_ratio_does_not_overflow(self) -> None:
        """Extreme reserve ratio (near 1.0) doesn't cause math overflow."""
        calc = DefaultWagePressureCalculator()
        pressure = calc.compute_wage_pressure(1.0)
        assert 0.0 <= pressure <= 0.5

    def test_very_small_ratio(self) -> None:
        """Very small reserve ratio produces near-zero pressure."""
        calc = DefaultWagePressureCalculator()
        pressure = calc.compute_wage_pressure(0.001)
        assert pressure < 0.05  # Very small

    def test_output_range(self) -> None:
        """All outputs are in [0, ceiling] for any valid input."""
        calc = DefaultWagePressureCalculator()
        for r in [0.0, 0.01, 0.05, 0.08, 0.15, 0.30, 0.50, 0.80, 1.0]:
            pressure = calc.compute_wage_pressure(r)
            assert 0.0 <= pressure <= 0.5, f"Out of range at r={r}: {pressure}"

    def test_wayne_county_scenario(self) -> None:
        """Wayne County 2009 scenario: high unemployment → strong wage pressure."""
        # Wayne County had ~18% U-6 in 2009
        calc = DefaultWagePressureCalculator()
        pressure = calc.compute_wage_pressure(0.18)
        # Should produce meaningful wage pressure
        assert pressure > 0.2
        assert pressure <= 0.5

    def test_oakland_county_scenario(self) -> None:
        """Oakland County scenario: lower unemployment → weaker wage pressure."""
        calc = DefaultWagePressureCalculator()
        pressure_oakland = calc.compute_wage_pressure(0.08)
        pressure_wayne = calc.compute_wage_pressure(0.18)
        # Wayne should have stronger pressure
        assert pressure_wayne > pressure_oakland
