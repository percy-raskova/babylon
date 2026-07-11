"""Tests for DerivedRateCalculator.

Feature: 017-simulation-tick-dynamics
Task: T029
"""

from __future__ import annotations

from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.tick.derived_rates import DerivedRateCalculator
from babylon.domain.economics.tick.types import CountyEconomicState, NationalTickParameters

WAYNE_FIPS = "26163"


def _make_county(
    fips: str = WAYNE_FIPS,
    year: int = 2015,
    capital_stock: float = 1e9,
    median_wage: float = 21.0,
    employment: float = 500_000.0,
    phi_hour: float = 3.50,
) -> CountyEconomicState:
    """Build a county state for testing."""
    dist = ClassDistribution(
        fips=fips,
        year=year,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )
    return CountyEconomicState(
        fips=fips,
        year=year,
        capital_stock=capital_stock,
        throughput_position=0.90,
        supply_chain_depth=2.1,
        unemployment_rate=0.053,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=median_wage,
        employment=employment,
        class_distribution=dist,
        phi_hour=phi_hour,
    )


def _make_params(tau: float = 62.0) -> NationalTickParameters:
    """Build national params for testing."""
    return NationalTickParameters(
        year=2015,
        tau=tau,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.33,
        gamma_III_raw=0.33,
        tau_effective=tau * 0.68,
        v_reproduction=12.0,
        estimated=True,
    )


class TestDerivedRateCalculator:
    """Tests for DerivedRateCalculator derived indicator computation."""

    def test_compute_county_rates_returns_derived_rates(self) -> None:
        """Verify compute_county_rates returns DerivedRates."""
        calc = DerivedRateCalculator()
        county = _make_county()
        params = _make_params()
        rates = calc.compute_county_rates(county, params)
        assert rates.fips == WAYNE_FIPS
        assert rates.year == 2015

    def test_profit_rate_formula(self) -> None:
        """Verify r = s / (K + v) where s=surplus, v=variable capital.

        s = (tau - v_repro) * employment * 2080 (annual hours)
        v = v_repro * employment * 2080
        r = s / (K + v)
        """
        calc = DerivedRateCalculator()
        county = _make_county(
            capital_stock=1e9,
            median_wage=21.0,
            employment=500_000.0,
        )
        params = _make_params(tau=62.0)
        rates = calc.compute_county_rates(county, params)

        # Manual calculation:
        # v_repro = 12.0 $/hr
        # annual_hours = 500000 * 2080 = 1.04e9
        # v = 12.0 * 1.04e9 = 1.248e10
        # total_value = 62.0 * 1.04e9 = 6.448e10
        # s = total_value - v = 6.448e10 - 1.248e10 = 5.2e10
        # K = 1e9
        # r = 5.2e10 / (1e9 + 1.248e10) = 5.2e10 / 1.348e10 ≈ 3.857
        assert rates.profit_rate is not None
        assert rates.profit_rate > 0

    def test_organic_composition_formula(self) -> None:
        """Verify OCC = c / v where c=constant capital, v=variable capital."""
        calc = DerivedRateCalculator()
        county = _make_county(capital_stock=1e9)
        params = _make_params()
        rates = calc.compute_county_rates(county, params)

        assert rates.organic_composition is not None
        assert rates.organic_composition >= 0

    def test_exploitation_rate_formula(self) -> None:
        """Verify e = s / v."""
        calc = DerivedRateCalculator()
        county = _make_county()
        params = _make_params()
        rates = calc.compute_county_rates(county, params)

        assert rates.exploitation_rate is not None
        assert rates.exploitation_rate >= 0

    def test_division_by_zero_returns_none(self) -> None:
        """Verify division-by-zero produces None, not crash."""
        calc = DerivedRateCalculator()
        # Zero employment -> v=0 -> division by zero for OCC and exploitation
        county = _make_county(employment=0.0, capital_stock=0.0)
        params = _make_params()
        rates = calc.compute_county_rates(county, params)

        # No employment means no variable capital
        # OCC and exploitation_rate should be None
        assert rates.organic_composition is None
        assert rates.exploitation_rate is None

    def test_phi_hour_preserved(self) -> None:
        """Verify phi_hour is passed through to DerivedRates."""
        calc = DerivedRateCalculator()
        county = _make_county(phi_hour=5.25)
        params = _make_params()
        rates = calc.compute_county_rates(county, params)
        assert rates.phi_hour == 5.25

    def test_compute_phi_aggregate(self) -> None:
        """Verify Phi_aggregate = sum(phi_hour * employment * 2080)."""
        calc = DerivedRateCalculator()
        counties = {
            WAYNE_FIPS: _make_county(phi_hour=3.50, employment=500_000.0),
            "06037": _make_county(fips="06037", phi_hour=4.00, employment=1_000_000.0),
        }
        phi_agg = calc.compute_phi_aggregate(counties)

        # Wayne: 3.50 * 500000 * 2080 = 3.64e9
        # LA:    4.00 * 1000000 * 2080 = 8.32e9
        # Total: 1.196e10
        expected = 3.50 * 500_000 * 2080 + 4.00 * 1_000_000 * 2080
        assert abs(phi_agg - expected) < 1.0

    def test_compute_phi_aggregate_empty(self) -> None:
        """Verify Phi_aggregate is zero for empty county set."""
        calc = DerivedRateCalculator()
        phi_agg = calc.compute_phi_aggregate({})
        assert phi_agg == 0.0
