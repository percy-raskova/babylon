"""Tests for Feature 024 financial state integration into tick pipeline.

Feature: 024-capital-volume-iii
Tasks: T079-T086

Tests NationalFinancialParameters and extended CountyEconomicState
financial fields.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.counter_tendencies.types import CounterTendencyStrength
from babylon.domain.economics.credit.types import (
    CreditCyclePhase,
    CreditState,
    FictitiousCapitalStock,
    InterestRateState,
)
from babylon.domain.economics.distribution.types import DebtAccumulation, SurplusValueDistribution
from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.financial_crisis.types import FinancialCrisisAssessment
from babylon.domain.economics.monetary.types import MonetaryAdjustment
from babylon.domain.economics.rent.types import HousingValueDecomposition, RentExtraction
from babylon.domain.economics.tick.types import (
    CountyEconomicState,
    NationalFinancialParameters,
)

# =============================================================================
# T084: NationalFinancialParameters Tests
# =============================================================================


class TestNationalFinancialParameters:
    """Tests for NationalFinancialParameters frozen model (Feature 024, T084)."""

    def test_empty_factory(self) -> None:
        """Verify .empty() returns all-None state."""
        params = NationalFinancialParameters.empty()
        assert params.interest_rate_state is None
        assert params.credit_state is None
        assert params.fictitious_capital is None
        assert params.counter_tendencies is None
        assert params.monetary_adjustment is None

    def test_default_construction_matches_empty(self) -> None:
        """Verify default construction is equivalent to .empty()."""
        params = NationalFinancialParameters()
        empty = NationalFinancialParameters.empty()
        assert params == empty

    def test_frozen_immutability(self) -> None:
        """Verify NationalFinancialParameters is frozen."""
        params = NationalFinancialParameters.empty()
        with pytest.raises(ValidationError):
            params.interest_rate_state = None  # type: ignore[misc]

    def test_with_interest_rate_state(self) -> None:
        """Verify construction with InterestRateState."""
        irs = InterestRateState(
            year=2015,
            base_rate=0.25,
            treasury_10y=2.27,
            baa_spread=2.64,
        )
        params = NationalFinancialParameters(interest_rate_state=irs)
        assert params.interest_rate_state is not None
        assert params.interest_rate_state.base_rate == 0.25
        assert params.interest_rate_state.effective_rate == 0.25 + 2.64

    def test_with_credit_state(self) -> None:
        """Verify construction with CreditState."""
        cs = CreditState(
            year=2015,
            total_credit=60_000_000_000_000.0,
            credit_expansion_rate=0.05,
            default_rate=0.01,
            spread_to_treasuries=2.0,
            phase=CreditCyclePhase.EXPANSION,
        )
        params = NationalFinancialParameters(credit_state=cs)
        assert params.credit_state is not None
        assert params.credit_state.phase == CreditCyclePhase.EXPANSION

    def test_with_fictitious_capital(self) -> None:
        """Verify construction with FictitiousCapitalStock."""
        fc = FictitiousCapitalStock(
            year=2015,
            government_debt=18e12,
            corporate_equity=20e12,
            corporate_debt=8e12,
            household_debt=14e12,
        )
        params = NationalFinancialParameters(fictitious_capital=fc)
        assert params.fictitious_capital is not None
        assert params.fictitious_capital.total_claims == 60e12

    def test_with_counter_tendencies(self) -> None:
        """Verify construction with CounterTendencyStrength."""
        ct = CounterTendencyStrength(year=2015, reserve_army_size=0.10)
        params = NationalFinancialParameters(counter_tendencies=ct)
        assert params.counter_tendencies is not None
        assert params.counter_tendencies.reserve_army_size == 0.10

    def test_with_monetary_adjustment(self) -> None:
        """Verify construction with MonetaryAdjustment."""
        ma = MonetaryAdjustment(
            year=2015,
            cpi_index=237.0,
            gdp_deflator=110.0,
            snlt_per_dollar=0.016,
            base_year=2012,
        )
        params = NationalFinancialParameters(monetary_adjustment=ma)
        assert params.monetary_adjustment is not None
        assert params.monetary_adjustment.snlt_per_dollar == 0.016

    def test_fully_populated(self) -> None:
        """Verify construction with all fields populated."""
        params = NationalFinancialParameters(
            interest_rate_state=InterestRateState(
                year=2015,
                base_rate=0.25,
                treasury_10y=2.27,
                baa_spread=2.64,
            ),
            credit_state=CreditState(
                year=2015,
                total_credit=60e12,
                phase=CreditCyclePhase.EXPANSION,
            ),
            fictitious_capital=FictitiousCapitalStock(
                year=2015,
                government_debt=18e12,
                corporate_equity=20e12,
                corporate_debt=8e12,
                household_debt=14e12,
            ),
            counter_tendencies=CounterTendencyStrength(year=2015),
            monetary_adjustment=MonetaryAdjustment(
                year=2015,
                cpi_index=237.0,
                gdp_deflator=110.0,
                snlt_per_dollar=0.016,
                base_year=2012,
            ),
        )
        assert params.interest_rate_state is not None
        assert params.credit_state is not None
        assert params.fictitious_capital is not None
        assert params.counter_tendencies is not None
        assert params.monetary_adjustment is not None


# =============================================================================
# T085: CountyEconomicState Financial Fields Tests
# =============================================================================


def _make_class_distribution() -> ClassDistribution:
    """Create standard class distribution for test reuse."""
    return ClassDistribution(
        fips="26163",
        year=2015,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )


def _make_county_state(**kwargs: object) -> CountyEconomicState:
    """Create county state with standard defaults, overridable via kwargs."""
    defaults: dict[str, object] = {
        "fips": "26163",
        "year": 2015,
        "capital_stock": 1e9,
        "throughput_position": 0.9,
        "supply_chain_depth": 2.1,
        "unemployment_rate": 0.053,
        "u6_rate": 0.10,
        "pter_rate": 0.04,
        "nilf_rate": 0.06,
        "median_wage": 21.0,
        "employment": 500000.0,
        "class_distribution": _make_class_distribution(),
        "phi_hour": 3.50,
    }
    defaults.update(kwargs)
    return CountyEconomicState(**defaults)  # type: ignore[arg-type]


class TestCountyEconomicStateFinancialFields:
    """Tests for Feature 024 financial fields on CountyEconomicState (T085)."""

    def test_default_financial_fields_are_none(self) -> None:
        """Verify all Feature 024 fields default to None."""
        state = _make_county_state()
        assert state.surplus_distribution is None
        assert state.rent_extraction is None
        assert state.housing_decomposition is None
        assert state.debt_accumulation is None
        assert state.financial_crisis is None

    def test_with_surplus_distribution(self) -> None:
        """Verify CountyEconomicState accepts SurplusValueDistribution."""
        svd = SurplusValueDistribution(
            fips_code="26163",
            year=2015,
            total_surplus_produced=1000.0,
            interest_payments=200.0,
            ground_rent=100.0,
            taxes_on_surplus=50.0,
        )
        state = _make_county_state(surplus_distribution=svd)
        assert state.surplus_distribution is not None
        assert state.surplus_distribution.profit_of_enterprise == 650.0

    def test_with_rent_extraction(self) -> None:
        """Verify CountyEconomicState accepts RentExtraction."""
        rent = RentExtraction(
            fips_code="26163",
            year=2015,
            agricultural_rent=50.0,
            resource_rent=30.0,
            urban_rent=200.0,
        )
        state = _make_county_state(rent_extraction=rent)
        assert state.rent_extraction is not None
        assert state.rent_extraction.total_rent == 280.0

    def test_with_housing_decomposition(self) -> None:
        """Verify CountyEconomicState accepts HousingValueDecomposition."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2015,
            construction_value=100000.0,
            ground_rent_capitalized=50000.0,
            speculative_premium=30000.0,
        )
        state = _make_county_state(housing_decomposition=housing)
        assert state.housing_decomposition is not None
        assert state.housing_decomposition.market_price == 180000.0

    def test_with_debt_accumulation(self) -> None:
        """Verify CountyEconomicState accepts DebtAccumulation."""
        debt = DebtAccumulation(
            fips_code="26163",
            year=2015,
            accumulated_debt=500.0,
            consecutive_deficit_ticks=3,
        )
        state = _make_county_state(debt_accumulation=debt)
        assert state.debt_accumulation is not None
        assert state.debt_accumulation.accumulated_debt == 500.0

    def test_with_financial_crisis(self) -> None:
        """Verify CountyEconomicState accepts FinancialCrisisAssessment."""
        crisis = FinancialCrisisAssessment(
            fips_code="26163",
            year=2015,
            profit_squeeze=True,
            claims_exceed_surplus=True,
        )
        state = _make_county_state(financial_crisis=crisis)
        assert state.financial_crisis is not None
        assert state.financial_crisis.active_signals == 2
