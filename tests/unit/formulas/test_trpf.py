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
from tests.constants import TestConstants

from babylon.systems.formulas import (
    calculate_organic_composition,
    calculate_rate_of_profit,
    calculate_rent_pool_decay,
    calculate_trpf_multiplier,
)

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
class TestRateOfProfit:
    """Rate of Profit: p' = s / (c + v)

    Marx's fundamental formula from Capital Vol. 3.
    Epoch 2 placeholder - currently implemented for formula completeness.
    """

    def test_marxs_first_example(self) -> None:
        """Marx's example: c=50, v=100, s=100 -> p'=66.67%.

        From Capital Vol. 3, Chapter 13.
        """
        rate = calculate_rate_of_profit(
            surplus_value=100.0, constant_capital=50.0, variable_capital=100.0
        )
        expected = 100.0 / 150.0  # = 0.6666...
        assert rate == pytest.approx(expected, abs=0.001)

    def test_marxs_second_example(self) -> None:
        """Marx's example: c=100, v=100, s=100 -> p'=50%."""
        rate = calculate_rate_of_profit(
            surplus_value=100.0, constant_capital=100.0, variable_capital=100.0
        )
        expected = 100.0 / 200.0  # = 0.5
        assert rate == pytest.approx(expected, abs=0.001)

    def test_marxs_third_example(self) -> None:
        """Marx's example: c=400, v=100, s=100 -> p'=20%.

        Shows TRPF: as OCC rises (c/v from 0.5 to 4.0),
        profit rate falls (from 66.67% to 20%).
        """
        rate = calculate_rate_of_profit(
            surplus_value=100.0, constant_capital=400.0, variable_capital=100.0
        )
        expected = 100.0 / 500.0  # = 0.2
        assert rate == pytest.approx(expected, abs=0.001)

    def test_zero_total_capital_returns_zero(self) -> None:
        """If no capital invested, rate of profit is 0 (not infinity)."""
        rate = calculate_rate_of_profit(
            surplus_value=100.0, constant_capital=0.0, variable_capital=0.0
        )
        assert rate == 0.0

    def test_higher_occ_means_lower_profit_rate(self) -> None:
        """Verify TRPF: as OCC rises, p' falls (with constant s/v)."""
        # All have same surplus value and variable capital
        s = 100.0
        v = 100.0

        # Different constant capital levels (rising OCC)
        rate_low_occ = calculate_rate_of_profit(
            surplus_value=s, constant_capital=50.0, variable_capital=v
        )
        rate_mid_occ = calculate_rate_of_profit(
            surplus_value=s, constant_capital=200.0, variable_capital=v
        )
        rate_high_occ = calculate_rate_of_profit(
            surplus_value=s, constant_capital=500.0, variable_capital=v
        )

        assert rate_low_occ > rate_mid_occ > rate_high_occ


@pytest.mark.math
class TestOrganicComposition:
    """Organic Composition of Capital: OCC = c / v

    The ratio of 'dead labor' (machinery) to 'living labor' (wages).
    As capitalism develops, OCC tends to rise.
    """

    def test_marxs_first_example(self) -> None:
        """OCC = 50/100 = 0.5 (early capitalism, labor-intensive)."""
        occ = calculate_organic_composition(constant_capital=50.0, variable_capital=100.0)
        assert occ == pytest.approx(0.5, abs=0.001)

    def test_marxs_third_example(self) -> None:
        """OCC = 400/100 = 4.0 (advanced capitalism, capital-intensive)."""
        occ = calculate_organic_composition(constant_capital=400.0, variable_capital=100.0)
        assert occ == pytest.approx(4.0, abs=0.001)

    def test_balanced_composition(self) -> None:
        """OCC = 1.0 when c = v."""
        occ = calculate_organic_composition(constant_capital=100.0, variable_capital=100.0)
        assert occ == pytest.approx(1.0, abs=0.001)

    def test_zero_variable_capital_returns_zero(self) -> None:
        """If no wages paid, return 0 (not infinity).

        This represents a fully automated process - theoretically
        impossible under Marx's value theory (no value created).
        """
        occ = calculate_organic_composition(constant_capital=500.0, variable_capital=0.0)
        assert occ == 0.0

    def test_rising_occ_with_automation(self) -> None:
        """Automation raises c relative to v, increasing OCC."""
        # Initial state
        c, v = 100.0, 100.0
        occ_before = calculate_organic_composition(constant_capital=c, variable_capital=v)

        # After automation: c increases by 100, v decreases by 50
        # (automation investment partially displaces labor)
        c_after = c + 100.0
        v_after = v - 50.0
        occ_after = calculate_organic_composition(
            constant_capital=c_after, variable_capital=v_after
        )

        assert occ_after > occ_before


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

            rate = calculate_rate_of_profit(surplus_value=s, constant_capital=c, variable_capital=v)
            profit_rates.append(rate)

        # Verify profit rates are monotonically declining
        for i in range(len(profit_rates) - 1):
            assert profit_rates[i] > profit_rates[i + 1], (
                f"Profit rate should fall: {profit_rates[i]} > {profit_rates[i + 1]}"
            )
