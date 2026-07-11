"""Counter-tendency strength computation.

Feature: 024-capital-volume-iii (US5, FR-010, FR-011)

Computes the aggregate strength of six counter-tendencies to the tendency
of the rate of profit to fall (TRPF). Provides correlation analysis against
observed profit rate trends.

See Also:
    :class:`CounterTendencyStrength`: Data model for counter-tendency indicators.
    :data:`COUNTER_TENDENCY_WEIGHTS`: Weights for the six indicators.
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.counter_tendencies.types import CounterTendencyStrength


class CounterTendencyCalculator(Protocol):
    """Protocol for counter-tendency computation.

    Implementations transform raw economic indicators into a
    CounterTendencyStrength model and provide correlation analysis.
    """

    def compute_counter_tendencies(
        self,
        year: int,
        exploitation_rate_current: float,
        exploitation_rate_previous: float,
        productivity_growth: float,
        wage_growth: float,
        capital_goods_price_change: float,
        u6_unemployment: float,
        imperial_rent_flow: float,
        financial_profit_share: float,
    ) -> CounterTendencyStrength:
        """Compute counter-tendency strength from economic indicators.

        Args:
            year: Calendar year.
            exploitation_rate_current: Current year s/v ratio.
            exploitation_rate_previous: Previous year s/v ratio.
            productivity_growth: Year-over-year productivity growth rate.
            wage_growth: Year-over-year real wage growth rate.
            capital_goods_price_change: Year-over-year capital goods price change.
            u6_unemployment: U-6 unemployment rate [0, 1].
            imperial_rent_flow: Net unequal exchange Phi (dollars).
            financial_profit_share: Financial sector share of total profits [0, 1].

        Returns:
            CounterTendencyStrength with computed net_counter_tendency.
        """
        ...

    def correlates_with_profit_rate(
        self, net_counter_tendency: float, profit_rate_trend: float
    ) -> bool:
        """Check whether counter-tendency direction matches profit rate trend.

        Args:
            net_counter_tendency: Computed net counter-tendency value.
            profit_rate_trend: Observed profit rate change (positive = rising).

        Returns:
            True if signs match or either value is zero (neutral).
        """
        ...


class DefaultCounterTendencyCalculator:
    """Default implementation of counter-tendency computation.

    Transforms raw economic indicators into CounterTendencyStrength
    fields:

    - exploitation_rate_change = current - previous
    - wage_suppression = max(0, productivity_growth - wage_growth)
    - constant_capital_cheapening = capital_goods_price_change (passthrough)
    - reserve_army_size = u6_unemployment (passthrough)
    - imperial_rent_flow = passthrough
    - fictitious_profit_share = financial_profit_share (passthrough)
    """

    def compute_counter_tendencies(
        self,
        year: int,
        exploitation_rate_current: float,
        exploitation_rate_previous: float,
        productivity_growth: float,
        wage_growth: float,
        capital_goods_price_change: float,
        u6_unemployment: float,
        imperial_rent_flow: float,
        financial_profit_share: float,
    ) -> CounterTendencyStrength:
        """Compute counter-tendency strength from economic indicators.

        Args:
            year: Calendar year.
            exploitation_rate_current: Current year s/v ratio.
            exploitation_rate_previous: Previous year s/v ratio.
            productivity_growth: Year-over-year productivity growth rate.
            wage_growth: Year-over-year real wage growth rate.
            capital_goods_price_change: Year-over-year capital goods price change.
            u6_unemployment: U-6 unemployment rate [0, 1].
            imperial_rent_flow: Net unequal exchange Phi (dollars).
            financial_profit_share: Financial sector share of total profits [0, 1].

        Returns:
            CounterTendencyStrength with computed net_counter_tendency.
        """
        return CounterTendencyStrength(
            year=year,
            exploitation_rate_change=exploitation_rate_current - exploitation_rate_previous,
            wage_suppression=max(0.0, productivity_growth - wage_growth),
            constant_capital_cheapening=capital_goods_price_change,
            reserve_army_size=u6_unemployment,
            imperial_rent_flow=imperial_rent_flow,
            fictitious_profit_share=financial_profit_share,
        )

    def correlates_with_profit_rate(
        self, net_counter_tendency: float, profit_rate_trend: float
    ) -> bool:
        """Check whether counter-tendency direction matches profit rate trend.

        Neutral values (zero) always count as correlated since they
        indicate no directional movement.

        Args:
            net_counter_tendency: Computed net counter-tendency value.
            profit_rate_trend: Observed profit rate change (positive = rising).

        Returns:
            True if signs match or either value is zero (neutral).
        """
        if net_counter_tendency == 0.0 or profit_rate_trend == 0.0:
            return True
        return (net_counter_tendency > 0) == (profit_rate_trend > 0)
