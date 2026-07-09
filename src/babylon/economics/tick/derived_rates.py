"""Derived economic indicator computation for the tick dynamics pipeline.

Feature: 017-simulation-tick-dynamics

Computes derived rates (profit rate, organic composition, exploitation rate)
and aggregate imperial rent from county-level state.

See Also:
    :mod:`babylon.economics.tick.types`: DerivedRates, TickSummary
    :mod:`babylon.economics.tick.system`: Pipeline integration (Step 8)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.economics.tick.types import DerivedRates
from babylon.formulas.constants import HOURS_PER_YEAR as ANNUAL_HOURS_PER_WORKER

if TYPE_CHECKING:
    from babylon.economics.tick.types import CountyEconomicState, NationalTickParameters


class DerivedRateCalculator:
    """Compute derived economic indicators from county state.

    Formulas:
        - Profit rate: r = s / (K + v)
        - Organic composition: OCC = c / v (K as proxy for c)
        - Exploitation rate: e = s / v
        - Phi aggregate: sum(phi_hour * employment * 2080)

    Division by zero yields None (mathematically undefined).

    Example:
        >>> calc = DerivedRateCalculator()
        >>> rates = calc.compute_county_rates(county, params)
    """

    def compute_county_rates(
        self,
        county: CountyEconomicState,
        params: NationalTickParameters,
    ) -> DerivedRates:
        """Compute derived rates for a single county.

        Args:
            county: County economic state.
            params: National parameters (provides tau, v_reproduction).

        Returns:
            DerivedRates with computed indicators (None for division-by-zero).
        """
        # Total labor-hours per year for this county
        annual_hours = county.employment * ANNUAL_HOURS_PER_WORKER

        # Variable capital: v = v_reproduction * annual_hours
        v = params.v_reproduction * annual_hours

        # Total value produced: tau * annual_hours
        total_value = params.tau * annual_hours

        # Surplus value: s = total_value - v
        s = total_value - v

        # Capital stock as proxy for constant capital
        k = county.capital_stock

        # Profit rate: r = s / (K + v)
        profit_rate: float | None = None
        denominator_r = k + v
        if denominator_r > 0:
            profit_rate = s / denominator_r

        # Organic composition: OCC = c / v (using K as proxy for c)
        organic_composition: float | None = None
        if v > 0:
            organic_composition = k / v

        # Exploitation rate: e = s / v
        exploitation_rate: float | None = None
        if v > 0:
            exploitation_rate = s / v

        return DerivedRates(
            fips=county.fips,
            year=county.year,
            profit_rate=profit_rate,
            organic_composition=organic_composition,
            exploitation_rate=exploitation_rate,
            phi_hour=county.phi_hour,
        )

    def compute_phi_aggregate(
        self,
        county_states: dict[str, CountyEconomicState],
    ) -> float:
        """Compute total national imperial rent.

        Args:
            county_states: All county states.

        Returns:
            Phi_aggregate = sum(phi_hour * employment * 2080).
        """
        total: float = 0.0
        for county in county_states.values():
            total += county.phi_hour * county.employment * ANNUAL_HOURS_PER_WORKER
        return total


__all__ = ["DerivedRateCalculator"]
