"""Tests for DispossessionIntensityCalculator (Feature 021, US2)."""

from __future__ import annotations

import pytest

from babylon.config.defines import DispossessionDefines
from babylon.economics.dispossession.intensity import DispossessionIntensityCalculator
from babylon.economics.dispossession.types import TerritoryDispossessionState


def _make_state(
    foreclosure_rate: float = 0.0,
    eviction_rate: float = 0.0,
    displacement_rate: float = 0.0,
    concentrated_ownership: float = 0.0,
    absentee_landlord_share: float = 0.0,
) -> TerritoryDispossessionState:
    """Helper to construct a TerritoryDispossessionState."""
    return TerritoryDispossessionState(
        fips_code="26163",
        year=2010,
        foreclosure_rate=foreclosure_rate,
        eviction_rate=eviction_rate,
        displacement_rate=displacement_rate,
        concentrated_ownership=concentrated_ownership,
        absentee_landlord_share=absentee_landlord_share,
    )


class TestDispossessionIntensityCalculator:
    """Tests for weighted sum dispossession intensity computation."""

    def test_zero_rates_zero_intensity(self) -> None:
        """All zero rates produce zero intensity."""
        calc = DispossessionIntensityCalculator()
        state = _make_state()
        assert calc.compute_intensity(state) == 0.0

    def test_foreclosure_dominant_weight(self) -> None:
        """Foreclosure has the highest weight (0.40)."""
        calc = DispossessionIntensityCalculator()
        foreclosure_state = _make_state(foreclosure_rate=0.10)
        eviction_state = _make_state(eviction_rate=0.10)
        assert calc.compute_intensity(foreclosure_state) > calc.compute_intensity(eviction_state)

    def test_weighted_sum_computation(self) -> None:
        """Intensity is weighted sum of rate components."""
        defines = DispossessionDefines(
            weight_foreclosure=0.40,
            weight_eviction=0.30,
            weight_displacement=0.15,
            weight_tax_sale=0.05,
            weight_eminent_domain=0.02,
        )
        calc = DispossessionIntensityCalculator(defines)
        state = _make_state(
            foreclosure_rate=0.10,
            eviction_rate=0.05,
        )
        expected = 0.40 * 0.10 + 0.30 * 0.05
        assert calc.compute_intensity(state) == pytest.approx(expected, abs=1e-6)

    def test_intensity_clamped_at_one(self) -> None:
        """Intensity is clamped to [0, 1]."""
        # Use high weights and rates
        defines = DispossessionDefines(
            weight_foreclosure=1.0,
            weight_eviction=1.0,
        )
        calc = DispossessionIntensityCalculator(defines)
        state = _make_state(foreclosure_rate=0.9, eviction_rate=0.9)
        assert calc.compute_intensity(state) <= 1.0

    def test_custom_defines(self) -> None:
        """Custom defines change intensity computation."""
        equal_weight = DispossessionDefines(
            weight_foreclosure=0.5,
            weight_eviction=0.5,
            weight_displacement=0.0,
        )
        calc = DispossessionIntensityCalculator(equal_weight)
        state = _make_state(foreclosure_rate=0.10, eviction_rate=0.10)
        expected = 0.5 * 0.10 + 0.5 * 0.10
        assert calc.compute_intensity(state) == pytest.approx(expected, abs=1e-6)

    def test_wayne_county_crisis_scenario(self) -> None:
        """Wayne County 2009: high foreclosure + eviction → high intensity."""
        calc = DispossessionIntensityCalculator()
        state = _make_state(
            foreclosure_rate=0.08,
            eviction_rate=0.05,
            displacement_rate=0.03,
        )
        intensity = calc.compute_intensity(state)
        assert intensity > 0.0
        assert intensity < 1.0


class TestValueTransfer:
    """Tests for value transfer computation with deadweight loss."""

    def test_zero_value_zero_transfer(self) -> None:
        """Zero total value produces zero transfer."""
        calc = DispossessionIntensityCalculator()
        received, deadweight = calc.compute_value_transfer(0.0)
        assert received == 0.0
        assert deadweight == 0.0

    def test_negative_value_zero_transfer(self) -> None:
        """Negative total value produces zero transfer."""
        calc = DispossessionIntensityCalculator()
        received, deadweight = calc.compute_value_transfer(-100.0)
        assert received == 0.0
        assert deadweight == 0.0

    def test_value_balance(self) -> None:
        """Net received + deadweight loss == total value."""
        calc = DispossessionIntensityCalculator()
        total = 1000.0
        received, deadweight = calc.compute_value_transfer(total)
        assert received + deadweight == pytest.approx(total)

    def test_default_deadweight_fraction(self) -> None:
        """Default deadweight fraction is 0.05 (5%)."""
        calc = DispossessionIntensityCalculator()
        received, deadweight = calc.compute_value_transfer(1000.0)
        assert deadweight == pytest.approx(50.0)
        assert received == pytest.approx(950.0)

    def test_custom_deadweight_fraction(self) -> None:
        """Custom deadweight fraction overrides defines."""
        calc = DispossessionIntensityCalculator()
        received, deadweight = calc.compute_value_transfer(1000.0, deadweight_fraction=0.10)
        assert deadweight == pytest.approx(100.0)
        assert received == pytest.approx(900.0)
