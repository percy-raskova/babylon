"""Tests for DefaultCounterTendencyCalculator.

Feature: 024-capital-volume-iii (US5, FR-010, FR-011)
TDD Red Phase: Tests define expected behavior for counter-tendency computation.

DefaultCounterTendencyCalculator: Computes CounterTendencyStrength from
economic indicator values and provides correlation analysis.
"""

from __future__ import annotations

import pytest

from babylon.economics.counter_tendencies.calculator import (
    DefaultCounterTendencyCalculator,
)
from babylon.economics.counter_tendencies.types import CounterTendencyStrength

from .conftest import CounterTendencyInputs

# =============================================================================
# compute_counter_tendencies
# =============================================================================


@pytest.mark.unit
class TestComputeCounterTendencies:
    """DefaultCounterTendencyCalculator.compute_counter_tendencies."""

    def test_returns_counter_tendency_strength(
        self,
        default_ct_inputs: CounterTendencyInputs,
    ) -> None:
        """Returns CounterTendencyStrength from indicator values."""
        calc = DefaultCounterTendencyCalculator()
        result = calc.compute_counter_tendencies(
            year=2020,
            exploitation_rate_current=default_ct_inputs.exploitation_rate_current,
            exploitation_rate_previous=default_ct_inputs.exploitation_rate_previous,
            productivity_growth=default_ct_inputs.productivity_growth,
            wage_growth=default_ct_inputs.wage_growth,
            capital_goods_price_change=default_ct_inputs.capital_goods_price_change,
            u6_unemployment=default_ct_inputs.u6_unemployment,
            imperial_rent_flow=default_ct_inputs.imperial_rent_flow,
            financial_profit_share=default_ct_inputs.financial_profit_share,
        )
        assert isinstance(result, CounterTendencyStrength)
        assert result.year == 2020

    def test_exploitation_rate_change_computed(
        self,
        default_ct_inputs: CounterTendencyInputs,
    ) -> None:
        """exploitation_rate_change = current - previous."""
        calc = DefaultCounterTendencyCalculator()
        result = calc.compute_counter_tendencies(
            year=2020,
            exploitation_rate_current=default_ct_inputs.exploitation_rate_current,
            exploitation_rate_previous=default_ct_inputs.exploitation_rate_previous,
            productivity_growth=default_ct_inputs.productivity_growth,
            wage_growth=default_ct_inputs.wage_growth,
            capital_goods_price_change=default_ct_inputs.capital_goods_price_change,
            u6_unemployment=default_ct_inputs.u6_unemployment,
            imperial_rent_flow=default_ct_inputs.imperial_rent_flow,
            financial_profit_share=default_ct_inputs.financial_profit_share,
        )
        assert isinstance(result, CounterTendencyStrength)
        expected = (
            default_ct_inputs.exploitation_rate_current
            - default_ct_inputs.exploitation_rate_previous
        )
        assert result.exploitation_rate_change == pytest.approx(expected)

    def test_wage_suppression_computed(
        self,
        default_ct_inputs: CounterTendencyInputs,
    ) -> None:
        """wage_suppression = max(0, productivity_growth - wage_growth)."""
        calc = DefaultCounterTendencyCalculator()
        result = calc.compute_counter_tendencies(
            year=2020,
            exploitation_rate_current=default_ct_inputs.exploitation_rate_current,
            exploitation_rate_previous=default_ct_inputs.exploitation_rate_previous,
            productivity_growth=default_ct_inputs.productivity_growth,
            wage_growth=default_ct_inputs.wage_growth,
            capital_goods_price_change=default_ct_inputs.capital_goods_price_change,
            u6_unemployment=default_ct_inputs.u6_unemployment,
            imperial_rent_flow=default_ct_inputs.imperial_rent_flow,
            financial_profit_share=default_ct_inputs.financial_profit_share,
        )
        assert isinstance(result, CounterTendencyStrength)
        expected = max(
            0.0,
            default_ct_inputs.productivity_growth - default_ct_inputs.wage_growth,
        )
        assert result.wage_suppression == pytest.approx(expected)

    def test_wage_suppression_zero_when_wages_outpace_productivity(self) -> None:
        """wage_suppression is 0.0 when wages grow faster than productivity."""
        calc = DefaultCounterTendencyCalculator()
        result = calc.compute_counter_tendencies(
            year=2020,
            exploitation_rate_current=1.5,
            exploitation_rate_previous=1.4,
            productivity_growth=0.01,
            wage_growth=0.03,  # Wages outpace productivity
            capital_goods_price_change=-0.03,
            u6_unemployment=0.08,
            imperial_rent_flow=500_000_000_000.0,
            financial_profit_share=0.25,
        )
        assert isinstance(result, CounterTendencyStrength)
        assert result.wage_suppression == pytest.approx(0.0)

    def test_positive_net_when_counter_tendencies_strong(
        self,
        default_ct_inputs: CounterTendencyInputs,
    ) -> None:
        """Positive net when exploitation rising, wages suppressed, etc."""
        calc = DefaultCounterTendencyCalculator()
        result = calc.compute_counter_tendencies(
            year=2020,
            exploitation_rate_current=default_ct_inputs.exploitation_rate_current,
            exploitation_rate_previous=default_ct_inputs.exploitation_rate_previous,
            productivity_growth=default_ct_inputs.productivity_growth,
            wage_growth=default_ct_inputs.wage_growth,
            capital_goods_price_change=default_ct_inputs.capital_goods_price_change,
            u6_unemployment=default_ct_inputs.u6_unemployment,
            imperial_rent_flow=default_ct_inputs.imperial_rent_flow,
            financial_profit_share=default_ct_inputs.financial_profit_share,
        )
        assert isinstance(result, CounterTendencyStrength)
        assert result.net_counter_tendency > 0.0

    def test_negative_net_when_counter_tendencies_weak(self) -> None:
        """Negative net when counter-tendencies weakening.

        Uses explicit values where imperial rent is zero (core cannot
        extract from periphery) and other indicators are weak, producing
        a genuinely negative net counter-tendency.
        """
        calc = DefaultCounterTendencyCalculator()
        result = calc.compute_counter_tendencies(
            year=2020,
            exploitation_rate_current=1.3,
            exploitation_rate_previous=1.5,  # Exploitation DECLINING (-0.2)
            productivity_growth=0.01,
            wage_growth=0.02,  # Wages outpace productivity -> suppression=0
            capital_goods_price_change=0.05,  # Capital getting MORE expensive
            u6_unemployment=0.03,  # Low unemployment
            imperial_rent_flow=0.0,  # No imperial rent extraction
            financial_profit_share=0.05,  # Small financial sector
        )
        assert isinstance(result, CounterTendencyStrength)
        # exploitation: 0.20 * (-0.2) = -0.04
        # wage_supp: 0.15 * 0.0 = 0.0
        # capital: 0.15 * (-0.05) = -0.0075
        # reserve: 0.15 * 0.03 = 0.0045
        # imperial: 0.20 * 0.0 = 0.0
        # fictitious: 0.15 * 0.05 = 0.0075
        # net = -0.04 + 0 + (-0.0075) + 0.0045 + 0 + 0.0075 = -0.0355
        assert result.net_counter_tendency < 0.0


# =============================================================================
# correlates_with_profit_rate
# =============================================================================


@pytest.mark.unit
class TestCorrelatesWithProfitRate:
    """DefaultCounterTendencyCalculator.correlates_with_profit_rate."""

    def test_positive_net_positive_trend_correlates(self) -> None:
        """Positive counter-tendency + positive profit trend = correlated."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(0.1, 0.05) is True

    def test_negative_net_negative_trend_correlates(self) -> None:
        """Negative counter-tendency + negative profit trend = correlated."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(-0.1, -0.05) is True

    def test_positive_net_negative_trend_no_correlation(self) -> None:
        """Positive counter-tendency + negative profit trend = not correlated."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(0.1, -0.05) is False

    def test_negative_net_positive_trend_no_correlation(self) -> None:
        """Negative counter-tendency + positive profit trend = not correlated."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(-0.1, 0.05) is False

    def test_zero_net_always_correlated(self) -> None:
        """Zero net counter-tendency counts as correlated (neutral)."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(0.0, 0.05) is True
        assert calc.correlates_with_profit_rate(0.0, -0.05) is True

    def test_zero_trend_always_correlated(self) -> None:
        """Zero profit rate trend counts as correlated (neutral)."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(0.1, 0.0) is True
        assert calc.correlates_with_profit_rate(-0.1, 0.0) is True

    def test_both_zero_correlated(self) -> None:
        """Both zero = neutral = correlated."""
        calc = DefaultCounterTendencyCalculator()
        assert calc.correlates_with_profit_rate(0.0, 0.0) is True
