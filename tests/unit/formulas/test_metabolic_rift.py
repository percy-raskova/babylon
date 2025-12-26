"""Tests for the Metabolic Rift formulas (Slice 1.4).

The ecological limits of capital accumulation: biocapacity tracking
and overshoot detection. These tests verify the deterministic formulas
that model the metabolic relationship between economy and environment.

Key Formulas:
- Biocapacity Delta: ΔB = R - (E × η) - regeneration minus entropic extraction
- Overshoot Ratio: O = C / B - consumption over biocapacity
"""

import pytest

from babylon.systems.formulas import (
    calculate_biocapacity_delta,
    calculate_overshoot_ratio,
)


@pytest.mark.math
class TestBiocapacityDelta:
    """ΔB = R - (E × η)

    The core metabolic formula. Biocapacity changes based on:
    - Regeneration: fraction of max_biocapacity restored per tick
    - Extraction: current_biocapacity * extraction_intensity * entropy_factor

    Variables:
        R: regeneration_rate * max_biocapacity (regeneration term)
        E: extraction_intensity * current_biocapacity (raw extraction)
        η (eta): entropy_factor (waste/inefficiency multiplier, default 1.2)
    """

    def test_pure_regeneration_no_extraction(self) -> None:
        """When extraction = 0, delta equals pure regeneration.

        No human activity means nature regenerates at its natural rate.
        """
        delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            current_biocapacity=50.0,
        )

        expected = 0.02 * 100.0  # 2.0
        assert delta == pytest.approx(expected, abs=0.001)

    def test_no_regeneration_at_max_capacity(self) -> None:
        """When at max capacity, regeneration is zero.

        Ecosystems cannot exceed their carrying capacity.
        """
        delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            current_biocapacity=100.0,  # At max
        )

        assert delta == 0.0

    def test_no_regeneration_above_max_capacity(self) -> None:
        """When above max capacity, still no regeneration.

        Edge case: temporary overshoot doesn't generate negative regeneration.
        """
        delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            current_biocapacity=120.0,  # Above max (edge case)
        )

        assert delta == 0.0

    def test_extraction_with_entropy_penalty(self) -> None:
        """Extraction costs more than raw value due to entropy.

        The entropy factor (η) encodes thermodynamic waste.
        """
        delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.05,
            current_biocapacity=50.0,
            entropy_factor=1.2,  # Default
        )

        regeneration = 0.02 * 100.0  # 2.0
        raw_extraction = 0.05 * 50.0  # 2.5
        ecological_cost = raw_extraction * 1.2  # 3.0
        expected = regeneration - ecological_cost  # 2.0 - 3.0 = -1.0

        assert delta == pytest.approx(expected, abs=0.001)

    def test_sustainable_extraction_rate(self) -> None:
        """Low extraction can be balanced by regeneration.

        Sustainable development: extraction <= regeneration.
        """
        delta = calculate_biocapacity_delta(
            regeneration_rate=0.05,  # 5% regeneration
            max_biocapacity=100.0,
            extraction_intensity=0.02,  # 2% extraction
            current_biocapacity=100.0,
            entropy_factor=1.2,
        )

        # At max capacity: no regeneration
        # Extraction: 0.02 * 100 * 1.2 = 2.4
        expected = 0.0 - 2.4
        assert delta == pytest.approx(expected, abs=0.001)

        # Below max capacity: regeneration kicks in
        delta_below_max = calculate_biocapacity_delta(
            regeneration_rate=0.05,
            max_biocapacity=100.0,
            extraction_intensity=0.02,
            current_biocapacity=50.0,
            entropy_factor=1.2,
        )

        regeneration = 0.05 * 100.0  # 5.0
        extraction = 0.02 * 50.0 * 1.2  # 1.2
        expected_below = regeneration - extraction  # 3.8
        assert delta_below_max == pytest.approx(expected_below, abs=0.001)

    def test_high_entropy_factor_increases_damage(self) -> None:
        """Higher entropy factor means more ecological damage.

        Industrial vs artisanal extraction: different entropy coefficients.
        """
        base_delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.05,
            current_biocapacity=50.0,
            entropy_factor=1.0,  # No waste
        )

        high_entropy_delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.05,
            current_biocapacity=50.0,
            entropy_factor=2.0,  # High waste
        )

        # Higher entropy should mean more negative delta
        assert high_entropy_delta < base_delta

    def test_zero_extraction_intensity_no_ecological_cost(self) -> None:
        """When extraction intensity is zero, no ecological cost.

        Edge case for unoccupied or protected territories.
        """
        delta = calculate_biocapacity_delta(
            regeneration_rate=0.02,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            current_biocapacity=50.0,
            entropy_factor=999.0,  # Irrelevant when no extraction
        )

        expected = 0.02 * 100.0  # Pure regeneration
        assert delta == pytest.approx(expected, abs=0.001)


@pytest.mark.math
class TestOvershootRatio:
    """O = C / B

    The ecological overshoot ratio measures consumption against biocapacity.
    When O > 1.0, we're in ecological overshoot (consuming more than nature
    can regenerate).

    Variables:
        C: total_consumption - aggregate consumption needs
        B: total_biocapacity - aggregate biocapacity available
    """

    def test_sustainable_ratio_below_one(self) -> None:
        """When consumption < biocapacity, ratio < 1 (sustainable)."""
        ratio = calculate_overshoot_ratio(
            total_consumption=50.0,
            total_biocapacity=100.0,
        )

        assert ratio == pytest.approx(0.5, abs=0.001)

    def test_exact_balance_ratio_one(self) -> None:
        """When consumption = biocapacity, ratio = 1 (knife edge)."""
        ratio = calculate_overshoot_ratio(
            total_consumption=100.0,
            total_biocapacity=100.0,
        )

        assert ratio == pytest.approx(1.0, abs=0.001)

    def test_overshoot_ratio_above_one(self) -> None:
        """When consumption > biocapacity, ratio > 1 (overshoot)."""
        ratio = calculate_overshoot_ratio(
            total_consumption=200.0,
            total_biocapacity=100.0,
        )

        assert ratio == pytest.approx(2.0, abs=0.001)

    def test_zero_biocapacity_returns_max_ratio(self) -> None:
        """When biocapacity is depleted, return capped high value.

        Avoids division by zero while signaling ecological collapse.
        """
        ratio = calculate_overshoot_ratio(
            total_consumption=100.0,
            total_biocapacity=0.0,
        )

        assert ratio == 999.0

    def test_negative_biocapacity_returns_max_ratio(self) -> None:
        """Negative biocapacity (edge case) also returns max ratio."""
        ratio = calculate_overshoot_ratio(
            total_consumption=100.0,
            total_biocapacity=-50.0,
        )

        assert ratio == 999.0

    def test_zero_consumption_zero_ratio(self) -> None:
        """When consumption is zero, ratio is zero (no demand)."""
        ratio = calculate_overshoot_ratio(
            total_consumption=0.0,
            total_biocapacity=100.0,
        )

        assert ratio == 0.0

    def test_ratio_scales_linearly(self) -> None:
        """Overshoot ratio scales linearly with consumption."""
        ratio_1x = calculate_overshoot_ratio(100.0, 100.0)
        ratio_2x = calculate_overshoot_ratio(200.0, 100.0)
        ratio_3x = calculate_overshoot_ratio(300.0, 100.0)

        assert ratio_1x == pytest.approx(1.0, abs=0.001)
        assert ratio_2x == pytest.approx(2.0, abs=0.001)
        assert ratio_3x == pytest.approx(3.0, abs=0.001)
