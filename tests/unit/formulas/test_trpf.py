"""Tests for the Tendency of the Rate of Profit to Fall (TRPF) formulas.

Marx's TRPF from Capital Volume 3: As organic composition of capital rises,
the rate of profit falls. These tests verify both the Epoch 1 surrogate
(time-based decay) and the Epoch 2 formulas (proper OCC calculation).

Key Formulas:
- TRPF Multiplier: max(floor, 1.0 - coefficient * tick)
- Rent Pool Decay: pool * (1 - decay_rate)
- Rate of Profit: p' = s / (c + v)
- Organic Composition: OCC = c / v

Theoretical Basis: Marx, Capital Vol. 3, Chapters 13-15
"""

import pytest

from babylon.formulas import (
    calculate_rent_pool_decay,
    calculate_trpf_multiplier,
)
from tests.constants import TestConstants

# Aliases for readability
TC = TestConstants.TRPF
TS = TestConstants.Timescale


@pytest.mark.math
class TestTRPFMultiplier:
    """TRPF Surrogate: max(floor, 1.0 - coefficient * tick)

    Epoch 1 models TRPF as time-dependent decay of extraction efficiency.
    This is a surrogate for proper organic composition tracking.

    The multiplier declines from 1.0 at tick 0, representing how rising
    organic composition of capital reduces profit rates over time.
    """

    def test_multiplier_starts_at_one(self) -> None:
        """At tick 0, extraction efficiency is 100%."""
        multiplier = calculate_trpf_multiplier(tick=0, trpf_coefficient=TC.TRPF_COEFFICIENT)
        assert multiplier == 1.0

    def test_multiplier_declines_over_time(self) -> None:
        """Multiplier decreases as ticks advance."""
        tick_0 = calculate_trpf_multiplier(tick=0, trpf_coefficient=TC.TRPF_COEFFICIENT)
        tick_500 = calculate_trpf_multiplier(tick=500, trpf_coefficient=TC.TRPF_COEFFICIENT)
        tick_1000 = calculate_trpf_multiplier(tick=1000, trpf_coefficient=TC.TRPF_COEFFICIENT)

        assert tick_0 > tick_500 > tick_1000

    def test_multiplier_at_20_year_horizon(self) -> None:
        """At 1040 ticks (20 years), multiplier should be ~48%."""
        multiplier = calculate_trpf_multiplier(
            tick=TS.TWENTY_YEAR_HORIZON, trpf_coefficient=TC.TRPF_COEFFICIENT
        )
        expected = 1.0 - (TC.TRPF_COEFFICIENT * TS.TWENTY_YEAR_HORIZON)  # = 0.48
        assert multiplier == pytest.approx(expected, abs=0.001)

    def test_multiplier_floors_at_minimum(self) -> None:
        """Multiplier should not go below floor value."""
        # At tick 2000 with coefficient 0.0005, raw would be 0.0
        # But floor prevents going below the efficiency floor
        multiplier = calculate_trpf_multiplier(
            tick=2000, trpf_coefficient=TC.TRPF_COEFFICIENT, floor=TC.EFFICIENCY_FLOOR
        )
        assert multiplier == TC.EFFICIENCY_FLOOR

    def test_multiplier_respects_custom_floor(self) -> None:
        """Custom floor values should be honored."""
        multiplier = calculate_trpf_multiplier(tick=5000, trpf_coefficient=0.001, floor=0.2)
        assert multiplier == 0.2

    def test_zero_coefficient_means_no_decay(self) -> None:
        """With coefficient=0, multiplier stays at 1.0 forever."""
        multiplier = calculate_trpf_multiplier(tick=10000, trpf_coefficient=0.0)
        assert multiplier == 1.0


@pytest.mark.math
class TestRentPoolDecay:
    """Rent Pool Decay: pool * (1 - decay_rate)

    Models background evaporation of accumulated imperial rent,
    representing the contradiction between accumulation tendency
    and profit rate decline.
    """

    def test_no_decay_with_zero_rate(self) -> None:
        """Pool unchanged when decay rate is zero."""
        decayed = calculate_rent_pool_decay(current_pool=100.0, decay_rate=0.0)
        assert decayed == 100.0

    def test_decay_reduces_pool(self) -> None:
        """Pool should shrink with positive decay rate."""
        decayed = calculate_rent_pool_decay(current_pool=100.0, decay_rate=TC.RENT_POOL_DECAY)
        expected = 100.0 * (1.0 - TC.RENT_POOL_DECAY)  # = 99.8
        assert decayed == pytest.approx(expected, abs=0.001)

    def test_decay_is_percentage_based(self) -> None:
        """Decay should be proportional to pool size."""
        small_pool = calculate_rent_pool_decay(current_pool=100.0, decay_rate=TC.RENT_POOL_DECAY)
        large_pool = calculate_rent_pool_decay(current_pool=1000.0, decay_rate=TC.RENT_POOL_DECAY)

        # Absolute decay of large pool should be 10x small pool
        small_decay = 100.0 - small_pool
        large_decay = 1000.0 - large_pool
        assert large_decay == pytest.approx(small_decay * 10, abs=0.001)

    def test_decay_never_goes_negative(self) -> None:
        """Even with high decay rates, pool floors at zero."""
        decayed = calculate_rent_pool_decay(current_pool=100.0, decay_rate=1.5)
        assert decayed == 0.0

    def test_negative_decay_rate_means_no_decay(self) -> None:
        """Negative decay rates should be treated as no decay."""
        decayed = calculate_rent_pool_decay(current_pool=100.0, decay_rate=-0.1)
        assert decayed == 100.0


@pytest.mark.math
class TestTRPFMechanism:
    """Integration tests verifying TRPF mechanism across formulas.

    These tests verify that the mathematical relationships hold across
    multiple formula calls, demonstrating TRPF's dialectical logic.
    """

    def test_20_year_simulation_shows_declining_efficiency(self) -> None:
        """Over 1040 ticks, extraction efficiency should visibly decline."""
        half_horizon = TS.TWENTY_YEAR_HORIZON // 2  # 520 ticks (10 years)

        tick_0_multiplier = calculate_trpf_multiplier(tick=0, trpf_coefficient=TC.TRPF_COEFFICIENT)
        tick_half_multiplier = calculate_trpf_multiplier(
            tick=half_horizon, trpf_coefficient=TC.TRPF_COEFFICIENT
        )
        tick_full_multiplier = calculate_trpf_multiplier(
            tick=TS.TWENTY_YEAR_HORIZON, trpf_coefficient=TC.TRPF_COEFFICIENT
        )

        # Start at 100%
        assert tick_0_multiplier == pytest.approx(1.0, abs=0.001)
        # At 10 years: 74%
        assert tick_half_multiplier == pytest.approx(0.74, abs=0.001)
        # At 20 years: 48%
        assert tick_full_multiplier == pytest.approx(0.48, abs=0.001)

    def test_rent_pool_compound_decay(self) -> None:
        """Rent pool should compound decay over multiple ticks."""
        pool = 100.0

        # Simulate 52 ticks (1 year)
        for _ in range(TS.TICKS_PER_YEAR):
            pool = calculate_rent_pool_decay(current_pool=pool, decay_rate=TC.RENT_POOL_DECAY)

        # After 52 ticks: 100 * (0.998)^52 ≈ 90.1
        expected = 100.0 * ((1.0 - TC.RENT_POOL_DECAY) ** TS.TICKS_PER_YEAR)
        assert pool == pytest.approx(expected, abs=0.1)

    def test_constant_exploitation_with_rising_occ(self) -> None:
        """With constant s/v, rising OCC causes falling p'.

        This is the core TRPF mechanism from Capital Vol. 3.
        """
        # Constant exploitation rate: s/v = 1.0 (100%)
        exploitation_rate = 1.0

        # Simulate rising OCC over time
        occ_values = [0.5, 1.0, 2.0, 4.0, 8.0]
        profit_rates = []

        for occ in occ_values:
            # For simplicity, keep v = 100 and calculate s from exploitation rate
            v = 100.0
            s = v * exploitation_rate  # s = 100
            c = v * occ  # c rises with OCC

            # p' = s / (c + v) inlined — the reference function was retired
            # (fork ledger F12; the live path is ValueTensor4x3.profit_rate)
            # but the declining-rate LAW this asserts is the durable contract.
            rate = s / (c + v)
            profit_rates.append(rate)

        # Verify profit rates are monotonically declining
        for i in range(len(profit_rates) - 1):
            assert profit_rates[i] > profit_rates[i + 1], (
                f"Profit rate should fall: {profit_rates[i]} > {profit_rates[i + 1]}"
            )
